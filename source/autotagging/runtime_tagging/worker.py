import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from utility.logger import get_logger

from autotagging.core.candidate_resolver import CandidateResolver, TagCandidate
from autotagging.core.musicbrainz_enricher import MusicBrainzEnricher
from autotagging.core.tag_writer import TagWriter
from autotagging.core.title_normalizer import TitleNormalizer
from autotagging.runtime_tagging.package_builder import TaggingQueueStore
from autotagging.runtime_tagging.results_report import TaggingResultsReport

logger = get_logger(__name__, "tagging_worker_debug.log")


class TaggingWorker:
    """Filesystem-backed background worker for prepared tagging packages."""

    DEFAULT_DONE_MAX_COUNT = 500
    DEFAULT_DONE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
    DEFAULT_FAILED_MAX_COUNT = 500
    DEFAULT_FAILED_MAX_AGE_SECONDS = 30 * 24 * 60 * 60

    def __init__(
        self,
        queue_store: TaggingQueueStore | None = None,
        title_normalizer: TitleNormalizer | None = None,
        candidate_resolver: CandidateResolver | None = None,
        musicbrainz_enricher: MusicBrainzEnricher | None = None,
        tag_writer: TagWriter | None = None,
        results_report: TaggingResultsReport | None = None,
        poll_interval: float = 1.0,
        idle_timeout: float = 30.0,
        done_max_count: int | None = DEFAULT_DONE_MAX_COUNT,
        done_max_age_seconds: float | None = DEFAULT_DONE_MAX_AGE_SECONDS,
        failed_max_count: int | None = DEFAULT_FAILED_MAX_COUNT,
        failed_max_age_seconds: float | None = DEFAULT_FAILED_MAX_AGE_SECONDS,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.queue_store = queue_store or TaggingQueueStore()
        self.title_normalizer = title_normalizer or TitleNormalizer()
        self.candidate_resolver = candidate_resolver or CandidateResolver()
        self.musicbrainz_enricher = musicbrainz_enricher or MusicBrainzEnricher()
        self.tag_writer = tag_writer or TagWriter()
        self.results_report = results_report or TaggingResultsReport()
        self.poll_interval = poll_interval
        self.idle_timeout = idle_timeout
        self.done_max_count = done_max_count
        self.done_max_age_seconds = done_max_age_seconds
        self.failed_max_count = failed_max_count
        self.failed_max_age_seconds = failed_max_age_seconds
        self.progress_callback = progress_callback

    def run_until_idle(self) -> int:
        processed_count = 0
        deadline = time.monotonic() + self.idle_timeout
        recovered = self.queue_store.recover_stale_processing()
        if recovered:
            logger.info("Recovered %s stale tagging package(s) back to pending", len(recovered))
        self._apply_retention_policy()
        self.queue_store.event_logger.emit(
            "worker_started",
            recovered_count=len(recovered),
            queue_snapshot=self.queue_store.build_queue_snapshot(limit_per_state=3),
        )

        while True:
            processed = self.process_next_pending_package()
            if processed:
                processed_count += 1
                self._apply_retention_policy()
                deadline = time.monotonic() + self.idle_timeout
                continue

            if time.monotonic() >= deadline:
                self._apply_retention_policy()
                self.queue_store.event_logger.emit(
                    "worker_idle_exit",
                    processed_count=processed_count,
                    queue_snapshot=self.queue_store.build_queue_snapshot(limit_per_state=3),
                )
                logger.info("Tagging worker idle timeout reached; processed=%s", processed_count)
                return processed_count

            time.sleep(self.poll_interval)

    def process_next_pending_package(self) -> bool:
        pending_files = self.queue_store.list_state_files("pending")
        if not pending_files:
            return False

        package_path = pending_files[0]
        self.process_package_file(package_path)
        return True

    def process_package_file(self, package_path: Path) -> Path:
        processing_path = self.queue_store.move_package(package_path, "processing")
        payload = self.queue_store.read_package(processing_path)
        payload = self.queue_store.update_state(payload, "processing")
        self.queue_store.write_package(processing_path, payload)
        self._emit_progress(
            event="package_started",
            queue_from="pending",
            queue_to="processing",
            package_path=str(processing_path),
            job_id=str(payload.get("job_id", "") or ""),
            state=str(payload.get("state", "") or ""),
            final_output_path=str(payload.get("final_output_path", "") or ""),
        )

        try:
            payload = self._apply_title_normalization(payload)
            completed_actions = list(payload.get("completed_actions", []))
            if "normalize_title" not in completed_actions:
                completed_actions.append("normalize_title")
            payload = self._resolve_candidates(payload)
            if "resolve_candidates" not in completed_actions:
                completed_actions.append("resolve_candidates")
            payload = self._maybe_apply_playlist_artist_memory(payload)
            payload["completed_actions"] = completed_actions
            payload, was_enriched = self._maybe_enrich_candidate(payload)
            if was_enriched:
                completed_actions = list(payload.get("completed_actions", []))
                if "enrich_candidate" not in completed_actions:
                    completed_actions.append("enrich_candidate")
            payload["completed_actions"] = completed_actions
            payload, final_state = self._maybe_write_tags(payload)
            target_state_dir = "failed" if final_state == "failed" else "done"
            final_path = self.queue_store.move_package(processing_path, target_state_dir)
            payload = self.queue_store.update_state(payload, final_state)
            self.queue_store.write_package(final_path, payload)
            self.results_report.update_from_package(payload)
            self._emit_progress(
                event="package_finished",
                queue_from="pending",
                queue_to=target_state_dir,
                package_path=str(final_path),
                job_id=str(payload.get("job_id", "") or ""),
                state=str(payload.get("state", "") or ""),
                write_status=str((payload.get("write_result", {}) or {}).get("status", "") or ""),
                candidate_source=str((payload.get("resolved_tags", {}) or {}).get("source", "") or ""),
                final_output_path=str(payload.get("final_output_path", "") or ""),
            )
            logger.info("Processed tagging package: %s", final_path)
            return final_path
        except Exception as exc:
            payload = self.queue_store.update_state(payload, "failed")
            errors = list(payload.get("errors", []))
            errors.append(str(exc))
            payload["errors"] = errors
            failed_path = self.queue_store.move_package(processing_path, "failed")
            self.queue_store.write_package(failed_path, payload)
            self.results_report.update_from_package(payload)
            self._emit_progress(
                event="package_finished",
                queue_from="pending",
                queue_to="failed",
                package_path=str(failed_path),
                job_id=str(payload.get("job_id", "") or ""),
                state="failed",
                write_status=str(exc),
                candidate_source=str((payload.get("resolved_tags", {}) or {}).get("source", "") or ""),
                final_output_path=str(payload.get("final_output_path", "") or ""),
            )
            logger.warning("Failed tagging package: %s (%s)", failed_path, exc)
            return failed_path

    def _apply_title_normalization(self, payload: dict[str, Any]) -> dict[str, Any]:
        source = payload.get("source", {}) or {}
        raw_title = source.get("title", "") or ""
        author = source.get("author", "") or ""

        result = self.title_normalizer.normalize(raw_title=raw_title, author=author)
        normalization = dict(payload.get("normalization", {}) or {})
        normalization["title_analysis"] = result.to_dict()
        payload["normalization"] = normalization
        self.queue_store.event_logger.emit_package_event(
            "title_normalized",
            payload,
            guessed_artist=result.guessed_artist,
            guessed_title=result.guessed_title,
            split_confidence=result.split_confidence,
        )
        return payload

    def _maybe_apply_playlist_artist_memory(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidate = TagCandidate.from_dict(dict(payload.get("resolved_tags", {}) or {}))
        if candidate.write_allowed:
            return payload

        playlist_title = str(payload.get("playlist_title", "") or "").strip()
        session_id = str(payload.get("session_id", "") or "").strip()
        title_analysis = (payload.get("normalization", {}) or {}).get("title_analysis", {}) or {}
        dominant_artist = self._detect_dominant_playlist_artist(
            session_id=session_id,
            playlist_title=playlist_title,
        )
        if not dominant_artist:
            return payload

        promoted: TagCandidate | None = None
        guessed_artist = str(title_analysis.get("guessed_artist", "") or "").strip()
        guessed_title = str(title_analysis.get("guessed_title", "") or "").strip()
        split_confidence = str(title_analysis.get("split_confidence", "") or "").strip()

        if candidate.source == "reverse_dash_artist_hint" and self._same_text(candidate.title, dominant_artist):
            promoted = TagCandidate(
                artist=dominant_artist,
                title=candidate.artist,
                album=candidate.album,
                track=candidate.track,
                source="playlist_artist_memory",
                confidence=0.88,
                write_allowed=True,
                notes=[*list(candidate.notes or []), "promoted by dominant playlist artist memory"],
            )
        elif (
            candidate.source == "title_dash_split"
            and guessed_artist
            and guessed_title
            and split_confidence.startswith("author_matched")
            and self._same_text(guessed_artist, dominant_artist)
        ):
            promoted = TagCandidate(
                artist=guessed_artist,
                title=guessed_title,
                album=candidate.album,
                track=candidate.track,
                source="playlist_artist_memory",
                confidence=0.89,
                write_allowed=True,
                notes=[*list(candidate.notes or []), "promoted by dominant playlist artist memory"],
            )

        if promoted is None:
            return payload

        payload["resolved_tags"] = promoted.to_dict()
        self.queue_store.event_logger.emit_package_event(
            "candidate_resolved",
            payload,
            candidate_source=promoted.source,
            candidate_confidence=promoted.confidence,
            candidate_write_allowed=promoted.write_allowed,
            dominant_playlist_artist=dominant_artist,
        )
        return payload

    def _resolve_candidates(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidate = self.candidate_resolver.resolve(payload)
        payload["resolved_tags"] = candidate.to_dict()
        self.queue_store.event_logger.emit_package_event(
            "candidate_resolved",
            payload,
            candidate_source=candidate.source,
            candidate_confidence=candidate.confidence,
            candidate_write_allowed=candidate.write_allowed,
        )
        return payload

    def _maybe_enrich_candidate(self, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        candidate_dict = dict(payload.get("resolved_tags", {}) or {})
        if candidate_dict.get("write_allowed"):
            return payload, False

        current_candidate = self.candidate_resolver.resolve(payload)
        enriched_candidate = self.musicbrainz_enricher.enrich(payload, current_candidate)
        raw_lookup_details = getattr(self.musicbrainz_enricher, "last_lookup_details", {})
        lookup_details = dict(raw_lookup_details) if isinstance(raw_lookup_details, dict) else {}
        if enriched_candidate is None:
            payload["enrichment_result"] = self._build_enrichment_result(lookup_details)
            event_type = "candidate_enrichment_missed"
            if payload["enrichment_result"]["status"] in {"timeout", "error", "client_unavailable"}:
                event_type = "candidate_enrichment_failed"
            self.queue_store.event_logger.emit_package_event(
                event_type,
                payload,
                enrichment_backend="musicbrainz",
                reason=payload["enrichment_result"].get("details", ""),
            )
            return payload, False

        payload["resolved_tags"] = enriched_candidate.to_dict()
        payload["enrichment_result"] = {
            "status": "matched",
            "source": enriched_candidate.source,
            "confidence": enriched_candidate.confidence,
            "write_allowed": enriched_candidate.write_allowed,
        }
        self.queue_store.event_logger.emit_package_event(
            "candidate_enriched",
            payload,
            enrichment_backend="musicbrainz",
            candidate_source=enriched_candidate.source,
            candidate_confidence=enriched_candidate.confidence,
            candidate_write_allowed=enriched_candidate.write_allowed,
        )
        return payload, True

    @staticmethod
    def _build_enrichment_result(details: dict[str, Any]) -> dict[str, Any]:
        status = str(details.get("status", "") or "")
        if status == "query_failed":
            result_status = "timeout" if details.get("timed_out") else "error"
            return {
                "status": result_status,
                "details": str(details.get("message", "") or details.get("error", "") or "").strip(),
            }
        if status == "client_unavailable":
            return {"status": "client_unavailable", "details": ""}
        return {"status": "no_match"}

    def _maybe_write_tags(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        requested_actions = set(payload.get("requested_actions", []) or [])
        candidate = dict(payload.get("resolved_tags", {}) or {})

        if "autotag" not in requested_actions:
            self.queue_store.event_logger.emit_package_event(
                "tag_write_not_requested",
                payload,
            )
            return payload, "done"

        if not candidate.get("write_allowed"):
            payload["write_result"] = {
                "success": False,
                "status": "skipped: candidate not safe for auto-write",
                "wrote_fields": [],
            }
            self.queue_store.event_logger.emit_package_event(
                "tag_write_skipped",
                payload,
                reason=payload["write_result"]["status"],
            )
            if payload.get("enrichment_result", {}).get("status") == "matched":
                return payload, "enriched"
            return payload, "skipped"

        candidate_obj = TagCandidate.from_dict(candidate)
        result = self.tag_writer.write_candidate(payload.get("final_output_path", ""), candidate_obj)
        payload["write_result"] = result.to_dict()
        if result.success:
            completed_actions = list(payload.get("completed_actions", []))
            if "write_tags" not in completed_actions:
                completed_actions.append("write_tags")
            payload["completed_actions"] = completed_actions
            self.queue_store.event_logger.emit_package_event(
                "tag_write_succeeded",
                payload,
                wrote_fields=list(result.wrote_fields),
            )
            return payload, "written"

        self.queue_store.event_logger.emit_package_event(
            "tag_write_failed",
            payload,
            reason=result.status,
        )
        return payload, "failed"

    def _apply_retention_policy(self) -> dict[str, list[Path]]:
        deleted = self.queue_store.apply_retention_policy(
            done_max_count=self.done_max_count,
            done_max_age_seconds=self.done_max_age_seconds,
            failed_max_count=self.failed_max_count,
            failed_max_age_seconds=self.failed_max_age_seconds,
        )
        done_deleted = len(deleted.get("done", []))
        failed_deleted = len(deleted.get("failed", []))
        if done_deleted or failed_deleted:
            logger.info(
                "Pruned tagging queue history: done=%s failed=%s",
                done_deleted,
                failed_deleted,
            )
        return deleted

    def _detect_dominant_playlist_artist(self, *, session_id: str, playlist_title: str) -> str:
        if not playlist_title:
            return ""

        candidate_payloads: list[dict[str, Any]] = []
        for state_name in ("done", "failed"):
            for payload in self.queue_store.list_state_payloads(state_name):
                if str(payload.get("playlist_title", "") or "").strip() != playlist_title:
                    continue
                if session_id and str(payload.get("session_id", "") or "").strip() != session_id:
                    continue
                candidate_payloads.append(payload)

        artists = [
            str((payload.get("resolved_tags", {}) or {}).get("artist", "") or "").strip()
            for payload in candidate_payloads
            if (payload.get("resolved_tags", {}) or {}).get("write_allowed")
        ]
        artists = [artist for artist in artists if artist]
        if len(artists) < 4:
            return ""

        counts = Counter(artists)
        dominant_artist, dominant_count = counts.most_common(1)[0]
        if dominant_count < 4:
            return ""
        if dominant_count / len(artists) < 0.75:
            return ""
        return dominant_artist

    @staticmethod
    def _same_text(left: str, right: str) -> bool:
        def _norm(value: str) -> str:
            return "".join(ch.lower() for ch in str(value) if ch.isalnum())

        return bool(left and right) and _norm(left) == _norm(right)

    def _emit_progress(self, **payload: Any) -> None:
        if self.progress_callback is None:
            return
        try:
            self.progress_callback(payload)
        except Exception:
            return
