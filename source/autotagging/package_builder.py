import json
import re
import uuid
from dataclasses import is_dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import utility.preferences as preferences
from utility.utils import DownloadOptions

from .models import TaggingPackage, TaggingSourceSnapshot


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
        playlist_title: str | None = None,
    ) -> TaggingPackage:
        final_path = Path(final_output_path)
        download_dir = Path(download_directory)

        return TaggingPackage(
            package_version=self.PACKAGE_VERSION,
            job_id=str(uuid.uuid4()),
            state="prepared",
            requested_actions=list(requested_actions),
            created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            final_output_path=str(final_path.resolve(strict=False)),
            download_directory=str(download_dir.resolve(strict=False)),
            container=final_path.suffix.lstrip(".").lower(),
            playlist_title=(playlist_title or "").strip(),
            source=self._build_source_snapshot(video_obj),
            download_options=_json_safe(options.to_dict()),
            normalization={"normalization_version": self.NORMALIZATION_VERSION},
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

    def __init__(self, base_dir: Path | str | None = None):
        if base_dir is None:
            base_dir = preferences.PROJECT_ROOT / "runtime" / "tagging"
        self.base_dir = Path(base_dir)

    def ensure_queue_dirs(self) -> dict[str, Path]:
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
        directories = self.ensure_queue_dirs()
        safe_stem = _safe_label(Path(package.final_output_path).stem)
        created_label = package.created_at.replace(":", "").replace("+00:00", "Z")
        output_path = directories["pending"] / f"{created_label}_{safe_stem}_{package.job_id[:8]}.json"

        self.write_package(output_path, package.to_dict())

        return output_path

    def list_state_files(self, state_name: str) -> list[Path]:
        directory = self.ensure_queue_dirs()[state_name]
        return sorted(directory.glob("*.json"))

    def move_package(self, package_path: Path | str, state_name: str) -> Path:
        target_directory = self.ensure_queue_dirs()[state_name]
        source_path = Path(package_path)
        target_path = target_directory / source_path.name
        source_path.replace(target_path)
        return target_path

    @staticmethod
    def read_package(package_path: Path | str) -> dict[str, Any]:
        with open(package_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def write_package(package_path: Path | str, payload: dict[str, Any]) -> None:
        with open(package_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
