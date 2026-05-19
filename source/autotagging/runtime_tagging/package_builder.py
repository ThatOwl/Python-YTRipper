import json
import re
import uuid
from dataclasses import is_dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import utility.preferences as preferences
from utility.utils import DownloadOptions

from autotagging.runtime_tagging.event_logger import TaggingEventLogger
from autotagging.runtime_tagging.models import TaggingPackage, TaggingSourceSnapshot


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return {k: _json_safe(v) for k, v in value.__dict__.items()}
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]

    for attr_name in ("__dict__",):
        attr_value = getattr(value, attr_name, None)
        if isinstance(attr_value, dict):
            return {str(k): _json_safe(v) for k, v in attr_value.items()}

    return str(value)


def _safe_label(text: str) -> str:
    label = re.sub(r"[^\w\-.]+", "_", (text or "").strip())
    label = re.sub(r"_+", "_", label).strip("._")
    return label or "tagging"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TaggingPackageBuilder:
    """Build a stable JSON-safe tagging package from downloader context."""

    PACKAGE_VERSION = 1
    NORMALIZATION_VERSION = "yt-title-v1"

    def build_package(
        self,
        *,
        final_output_path: Path | str,
        download_directory: Path | str,
        video_obj: Any,
        options: DownloadOptions,
        requested_actions: list[str],
        session_id: str | None = None,
        sequence_no: int = 0,
        playlist_title: str | None = None,
        result_report_path: Path | str | None = None,
    ) -> TaggingPackage:
        final_path = Path(final_output_path)
        download_dir = Path(download_directory)
        created_at = _utc_now_iso()
        active_session_id = session_id or str(uuid.uuid4())

        return TaggingPackage(
            package_version=self.PACKAGE_VERSION,
            job_id=str(uuid.uuid4()),
            session_id=active_session_id,
            sequence_no=sequence_no,
            state="prepared",
            requested_actions=list(requested_actions),
            created_at=created_at,
            final_output_path=str(final_path.resolve(strict=False)),
            download_directory=str(download_dir.resolve(strict=False)),
            container=final_path.suffix.lstrip(".").lower(),
            playlist_title=(playlist_title or "").strip(),
            source=self._build_source_snapshot(video_obj),
            download_options=_json_safe(options.to_dict()),
            result_report={"report_path": str(Path(result_report_path).resolve(strict=False))} if result_report_path else {},
            normalization={"normalization_version": self.NORMALIZATION_VERSION},
            lifecycle={
                "prepared_at": created_at,
                "last_transition_at": created_at,
                "state_history": [{"state": "prepared", "at": created_at}],
            },
        )

    def _build_source_snapshot(self, video_obj: Any) -> TaggingSourceSnapshot:
        captions = self._get_first_present(video_obj, "captions", "caption_tracks")
        metadata = self._get_first_present(video_obj, "metadata", "vid_metadata")
        chapters = getattr(video_obj, "chapters", None)

        return TaggingSourceSnapshot(
            url=str(getattr(video_obj, "watch_url", "") or ""),
            video_id=str(getattr(video_obj, "video_id", "") or ""),
            title=str(getattr(video_obj, "title", "") or ""),
            author=str(getattr(video_obj, "author", "") or ""),
            channel_id=str(getattr(video_obj, "channel_id", "") or ""),
            publish_date=self._stringify_date(getattr(video_obj, "publish_date", None)),
            thumbnail_url=str(getattr(video_obj, "thumbnail_url", "") or ""),
            description=str(getattr(video_obj, "description", "") or ""),
            keywords=self._normalize_keywords(getattr(video_obj, "keywords", None)),
            metadata=_json_safe(metadata),
            captions_available=bool(captions),
            caption_track_count=self._count_if_sized(captions),
            chapters=_json_safe(chapters),
        )

    @staticmethod
    def _get_first_present(obj: Any, *attribute_names: str) -> Any:
        for attribute_name in attribute_names:
            value = getattr(obj, attribute_name, None)
            if value:
                return value
        return None

    @staticmethod
    def _stringify_date(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _normalize_keywords(value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if str(item).strip()]
        return [str(value)]

    @staticmethod
    def _count_if_sized(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return len(value)
        except Exception:
            return None


class TaggingQueueStore:
    """Persist tagging packages into a filesystem-backed queue."""

    STATE_NAMES = ("pending", "processing", "done", "failed")

    def __init__(
        self,
        base_dir: Path | str | None = None,
        event_logger: TaggingEventLogger | None = None,
    ):
        if base_dir is None:
            base_dir = preferences.PROJECT_ROOT / "runtime-tagging"
        self.base_dir = Path(base_dir)
        self.event_logger = event_logger or TaggingEventLogger(self.base_dir / "events.jsonl")

    def ensure_queue_dirs(self) -> dict[str, Path]:
        """Create queue state directories on demand and return their paths."""
        directories = {
            "pending": self.base_dir / "pending",
            "processing": self.base_dir / "processing",
            "done": self.base_dir / "done",
            "failed": self.base_dir / "failed",
        }
        for path in directories.values():
            path.mkdir(parents=True, exist_ok=True)
        return directories

    def write_pending_package(self, package: TaggingPackage) -> Path:
        """Persist a newly prepared package into the pending queue."""
        directories = self.ensure_queue_dirs()
        safe_stem = _safe_label(Path(package.final_output_path).stem)
        created_label = package.created_at.replace(":", "").replace("+00:00", "Z")
        output_path = directories["pending"] / f"{created_label}_{safe_stem}_{package.job_id[:8]}.json"

        payload = package.to_dict()
        self.write_package(output_path, payload)
        self.event_logger.emit_package_event(
            "package_prepared",
            payload,
            queue_path=str(output_path),
        )

        return output_path

    def list_state_files(self, state_name: str) -> list[Path]:
        """Return queue package paths for one state, sorted by filename."""
        directory = self.ensure_queue_dirs()[state_name]
        return sorted(directory.glob("*.json"))

    def move_package(self, package_path: Path | str, state_name: str) -> Path:
        """Move a package JSON into another queue state directory."""
        target_directory = self.ensure_queue_dirs()[state_name]
        source_path = Path(package_path)
        target_path = target_directory / source_path.name
        source_path.replace(target_path)
        return target_path

    def update_state(self, payload: dict[str, Any], state: str) -> dict[str, Any]:
        """Update state and lifecycle timestamps in a package payload."""
        previous_state = payload.get("state", "")
        timestamp = _utc_now_iso()
        payload["state"] = state
        lifecycle = dict(payload.get("lifecycle", {}) or {})
        lifecycle["last_transition_at"] = timestamp
        lifecycle[f"{state}_at"] = timestamp
        history = list(lifecycle.get("state_history", []) or [])
        history.append({"state": state, "at": timestamp})
        lifecycle["state_history"] = history
        payload["lifecycle"] = lifecycle
        self.event_logger.emit_package_event(
            "state_transition",
            payload,
            previous_state=previous_state,
            new_state=state,
        )
        return payload

    def recover_stale_processing(self, max_age_seconds: float = 300.0) -> list[Path]:
        """Move stale processing packages back to pending so a worker can retry them."""
        recovered: list[Path] = []
        now = datetime.now(timezone.utc)
        for package_path in self.list_state_files("processing"):
            payload = self.read_package(package_path)
            lifecycle = dict(payload.get("lifecycle", {}) or {})
            started_at = (
                lifecycle.get("processing_at")
                or lifecycle.get("last_transition_at")
                or payload.get("created_at")
            )
            age_seconds = self._age_seconds(now, started_at)
            if age_seconds is None or age_seconds < max_age_seconds:
                continue

            payload = self.update_state(payload, "prepared")
            lifecycle = dict(payload.get("lifecycle", {}) or {})
            lifecycle["recovered_from_processing_at"] = _utc_now_iso()
            lifecycle["recovery_count"] = int(lifecycle.get("recovery_count", 0) or 0) + 1
            payload["lifecycle"] = lifecycle
            recovered_path = self.move_package(package_path, "pending")
            self.write_package(recovered_path, payload)
            self.event_logger.emit_package_event(
                "package_recovered",
                payload,
                queue_path=str(recovered_path),
                recovered_from="processing",
            )
            recovered.append(recovered_path)
        return recovered

    def list_state_payloads(self, state_name: str) -> list[dict[str, Any]]:
        """Load all packages for one queue state."""
        return [self.read_package(path) for path in self.list_state_files(state_name)]

    def build_queue_snapshot(self, limit_per_state: int = 10) -> dict[str, Any]:
        """Return queue counts plus compact recent-package/session summaries."""
        state_payloads = {
            state_name: self.list_state_payloads(state_name)
            for state_name in self.STATE_NAMES
        }
        recent = {
            state_name: [
                self.summarize_package(payload)
                for payload in self._sort_payloads_desc(payloads)[:limit_per_state]
            ]
            for state_name, payloads in state_payloads.items()
        }

        sessions: dict[str, dict[str, Any]] = {}
        for state_name, payloads in state_payloads.items():
            for payload in payloads:
                session_id = str(payload.get("session_id", "") or "")
                if not session_id:
                    continue
                summary = sessions.setdefault(
                    session_id,
                    {
                        "session_id": session_id,
                        "counts": {name: 0 for name in self.STATE_NAMES},
                        "package_count": 0,
                        "created_at": payload.get("created_at", ""),
                        "last_transition_at": self._payload_last_transition_at(payload),
                    },
                )
                summary["counts"][state_name] += 1
                summary["package_count"] += 1
                summary["created_at"] = min(
                    filter(None, [summary.get("created_at", ""), payload.get("created_at", "")]),
                    default=summary.get("created_at", ""),
                )
                last_transition = self._payload_last_transition_at(payload)
                if last_transition and last_transition > summary.get("last_transition_at", ""):
                    summary["last_transition_at"] = last_transition

        return {
            "counts": {state_name: len(payloads) for state_name, payloads in state_payloads.items()},
            "recent": recent,
            "sessions": sorted(
                sessions.values(),
                key=lambda item: item.get("last_transition_at", ""),
                reverse=True,
            ),
        }

    def build_session_snapshot(self, session_id: str) -> dict[str, Any]:
        """Return a session-focused view across every queue state."""
        packages: list[dict[str, Any]] = []
        counts = {state_name: 0 for state_name in self.STATE_NAMES}

        for state_name in self.STATE_NAMES:
            payloads = [
                payload
                for payload in self.list_state_payloads(state_name)
                if str(payload.get("session_id", "") or "") == session_id
            ]
            counts[state_name] = len(payloads)
            packages.extend(payloads)

        sorted_packages = sorted(
            packages,
            key=lambda payload: (
                int(payload.get("sequence_no", 0) or 0),
                payload.get("created_at", ""),
                payload.get("job_id", ""),
            ),
        )
        return {
            "session_id": session_id,
            "counts": counts,
            "package_count": len(sorted_packages),
            "packages": [self.summarize_package(payload) for payload in sorted_packages],
        }

    def requeue_failed_packages(
        self,
        *,
        session_id: str | None = None,
        job_id: str | None = None,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        """Move failed packages back to pending/prepared for manual retry."""
        return self.requeue_packages(
            source_state="failed",
            session_id=session_id,
            job_id=job_id,
            dry_run=dry_run,
        )

    def requeue_packages(
        self,
        *,
        source_state: str,
        session_id: str | None = None,
        job_id: str | None = None,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        """Move selected retryable package states back to pending/prepared."""
        if source_state == "failed":
            state_dir = "failed"
            state_filter = None
        elif source_state in {"skipped", "enriched"}:
            state_dir = "done"
            state_filter = source_state
        else:
            raise ValueError(f"Unsupported requeue source state: {source_state}")

        results: list[dict[str, Any]] = []
        for package_path in self.list_state_files(state_dir):
            payload = self.read_package(package_path)
            payload_state = str(payload.get("state", "") or "")
            if state_filter and payload_state != state_filter:
                continue
            if session_id and str(payload.get("session_id", "") or "") != session_id:
                continue
            if job_id and str(payload.get("job_id", "") or "") != job_id:
                continue

            result = {
                "job_id": payload.get("job_id", ""),
                "session_id": payload.get("session_id", ""),
                "sequence_no": payload.get("sequence_no", 0),
                "source_state": payload_state,
                "target_state": "prepared",
                "source_queue_path": str(package_path),
                "target_queue_path": str(self.ensure_queue_dirs()["pending"] / package_path.name),
                "final_queue_path": "",
                "final_output_path": payload.get("final_output_path", ""),
                "final_state": "",
                "status": "dry_run" if dry_run else "requeued",
                "worker_processed": False,
            }

            if dry_run:
                results.append(result)
                continue

            payload = self.update_state(payload, "prepared")
            lifecycle = dict(payload.get("lifecycle", {}) or {})
            lifecycle["last_manual_requeue_at"] = _utc_now_iso()
            lifecycle["manual_requeue_count"] = int(lifecycle.get("manual_requeue_count", 0) or 0) + 1
            payload["lifecycle"] = lifecycle

            requeued_path = self.move_package(package_path, "pending")
            self.write_package(requeued_path, payload)
            self.event_logger.emit_package_event(
                "package_requeued",
                payload,
                queue_path=str(requeued_path),
                requeued_from=payload_state,
                requeued_from_queue_state=state_dir,
                requeue_reason="manual_retry",
            )
            result["target_queue_path"] = str(requeued_path)
            results.append(result)
        return results

    def prune_state_files(
        self,
        state_name: str,
        *,
        max_count: int | None = None,
        max_age_seconds: float | None = None,
    ) -> list[Path]:
        """Delete old queue packages for one state by age and/or count budget."""
        records = []
        now = datetime.now(timezone.utc)

        for package_path in self.list_state_files(state_name):
            payload = self.read_package(package_path)
            lifecycle = dict(payload.get("lifecycle", {}) or {})
            ts = (
                lifecycle.get(f"{state_name}_at")
                or lifecycle.get("last_transition_at")
                or payload.get("created_at")
            )
            age_seconds = self._age_seconds(now, ts)
            sort_age = age_seconds if age_seconds is not None else -1.0
            records.append((package_path, age_seconds, sort_age))

        records.sort(key=lambda item: item[2], reverse=True)
        to_delete: dict[str, Path] = {}

        if max_age_seconds is not None:
            for package_path, age_seconds, _ in records:
                if age_seconds is not None and age_seconds > max_age_seconds:
                    to_delete[str(package_path)] = package_path

        if max_count is not None and max_count >= 0 and len(records) > max_count:
            overflow = len(records) - max_count
            for package_path, _, _ in records[:overflow]:
                to_delete[str(package_path)] = package_path

        deleted: list[Path] = []
        for package_path in to_delete.values():
            try:
                payload = self.read_package(package_path)
                package_path.unlink(missing_ok=True)
                self.event_logger.emit_package_event(
                    "package_pruned",
                    payload,
                    pruned_from=state_name,
                    queue_path=str(package_path),
                )
                deleted.append(package_path)
            except Exception:
                continue
        return sorted(deleted)

    def apply_retention_policy(
        self,
        *,
        done_max_count: int | None = None,
        done_max_age_seconds: float | None = None,
        failed_max_count: int | None = None,
        failed_max_age_seconds: float | None = None,
    ) -> dict[str, list[Path]]:
        """Apply retention settings to completed queue states."""
        return {
            "done": self.prune_state_files(
                "done",
                max_count=done_max_count,
                max_age_seconds=done_max_age_seconds,
            ),
            "failed": self.prune_state_files(
                "failed",
                max_count=failed_max_count,
                max_age_seconds=failed_max_age_seconds,
            ),
        }

    @staticmethod
    def read_package(package_path: Path | str) -> dict[str, Any]:
        with open(package_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def write_package(package_path: Path | str, payload: dict[str, Any]) -> None:
        with open(package_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    @staticmethod
    def summarize_package(payload: dict[str, Any]) -> dict[str, Any]:
        """Project a full package payload into a compact UI/log-friendly summary."""
        source = dict(payload.get("source", {}) or {})
        lifecycle = dict(payload.get("lifecycle", {}) or {})
        resolved_tags = dict(payload.get("resolved_tags", {}) or {})
        write_result = dict(payload.get("write_result", {}) or {})
        return {
            "job_id": payload.get("job_id", ""),
            "session_id": payload.get("session_id", ""),
            "sequence_no": payload.get("sequence_no", 0),
            "state": payload.get("state", ""),
            "created_at": payload.get("created_at", ""),
            "last_transition_at": lifecycle.get("last_transition_at", ""),
            "final_output_path": payload.get("final_output_path", ""),
            "playlist_title": payload.get("playlist_title", ""),
            "requested_actions": list(payload.get("requested_actions", []) or []),
            "source_title": source.get("title", ""),
            "source_author": source.get("author", ""),
            "candidate_source": resolved_tags.get("source", ""),
            "candidate_confidence": resolved_tags.get("confidence"),
            "write_allowed": resolved_tags.get("write_allowed"),
            "write_status": write_result.get("status", ""),
        }

    @staticmethod
    def _payload_last_transition_at(payload: dict[str, Any]) -> str:
        lifecycle = dict(payload.get("lifecycle", {}) or {})
        return str(lifecycle.get("last_transition_at", "") or payload.get("created_at", "") or "")

    @classmethod
    def _sort_payloads_desc(cls, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            payloads,
            key=lambda payload: (
                cls._payload_last_transition_at(payload),
                int(payload.get("sequence_no", 0) or 0),
                payload.get("job_id", ""),
            ),
            reverse=True,
        )

    @staticmethod
    def _age_seconds(now: datetime, timestamp: str | None) -> float | None:
        if not timestamp:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return (now - parsed).total_seconds()
