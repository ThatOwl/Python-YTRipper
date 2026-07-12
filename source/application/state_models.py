from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from utility.utils import DownloadOptions


@dataclass
class SessionConfigState:
    """Serializable snapshot of the mutable session config state."""

    preferences: dict[str, Any] = field(default_factory=dict)
    options: DownloadOptions = field(default_factory=DownloadOptions)
    loaded_preset_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferences": dict(self.preferences),
            "options": self.options.to_dict(),
            "loaded_preset_path": str(self.loaded_preset_path) if self.loaded_preset_path else "",
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionConfigState":
        preferences = dict(payload.get("preferences", {}) or {})
        options_payload = dict(payload.get("options", {}) or {})
        loaded_path = str(payload.get("loaded_preset_path", "") or "").strip()
        return cls(
            preferences=preferences,
            options=DownloadOptions.from_preferences(options_payload),
            loaded_preset_path=Path(loaded_path) if loaded_path else None,
        )


@dataclass
class JobEvent:
    at: str = ""
    event_type: str = ""
    job_id: str = ""
    session_id: str = ""
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "at": self.at,
            "event_type": self.event_type,
            "job_id": self.job_id,
            "session_id": self.session_id,
            "message": self.message,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobEvent":
        return cls(
            at=str(payload.get("at", "") or ""),
            event_type=str(payload.get("event_type", "") or ""),
            job_id=str(payload.get("job_id", "") or ""),
            session_id=str(payload.get("session_id", "") or ""),
            message=str(payload.get("message", "") or ""),
            payload=dict(payload.get("payload", {}) or {}),
        )


@dataclass
class JobItemStatus:
    item_id: str = ""
    label: str = ""
    source_url: str = ""
    status: str = "pending"
    success: bool | None = None
    output_path: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "label": self.label,
            "source_url": self.source_url,
            "status": self.status,
            "success": self.success,
            "output_path": self.output_path,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobItemStatus":
        return cls(
            item_id=str(payload.get("item_id", "") or ""),
            label=str(payload.get("label", "") or ""),
            source_url=str(payload.get("source_url", "") or ""),
            status=str(payload.get("status", "pending") or "pending"),
            success=payload.get("success", None),
            output_path=str(payload.get("output_path", "") or ""),
            error=str(payload.get("error", "") or ""),
        )


@dataclass
class JobSummary:
    job_id: str = ""
    job_kind: str = ""
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    status: str = "queued"
    source_label: str = ""
    download_dir: str = ""
    playlist_dir: str = ""
    results_path: str = ""
    items_total: int = 0
    items_done: int = 0
    items_failed: int = 0
    current_item_label: str = ""
    option_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_kind": self.job_kind,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "source_label": self.source_label,
            "download_dir": self.download_dir,
            "playlist_dir": self.playlist_dir,
            "results_path": self.results_path,
            "items_total": self.items_total,
            "items_done": self.items_done,
            "items_failed": self.items_failed,
            "current_item_label": self.current_item_label,
            "option_snapshot": dict(self.option_snapshot),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobSummary":
        return cls(
            job_id=str(payload.get("job_id", "") or ""),
            job_kind=str(payload.get("job_kind", "") or ""),
            created_at=str(payload.get("created_at", "") or ""),
            started_at=str(payload.get("started_at", "") or ""),
            finished_at=str(payload.get("finished_at", "") or ""),
            status=str(payload.get("status", "queued") or "queued"),
            source_label=str(payload.get("source_label", "") or ""),
            download_dir=str(payload.get("download_dir", "") or ""),
            playlist_dir=str(payload.get("playlist_dir", "") or ""),
            results_path=str(payload.get("results_path", "") or ""),
            items_total=int(payload.get("items_total", 0) or 0),
            items_done=int(payload.get("items_done", 0) or 0),
            items_failed=int(payload.get("items_failed", 0) or 0),
            current_item_label=str(payload.get("current_item_label", "") or ""),
            option_snapshot=dict(payload.get("option_snapshot", {}) or {}),
        )


@dataclass
class JobDetail:
    summary: JobSummary = field(default_factory=JobSummary)
    items: list[JobItemStatus] = field(default_factory=list)
    events: list[JobEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobDetail":
        return cls(
            summary=JobSummary.from_dict(dict(payload.get("summary", {}) or {})),
            items=[
                JobItemStatus.from_dict(dict(item or {}))
                for item in list(payload.get("items", []) or [])
            ],
            events=[
                JobEvent.from_dict(dict(event or {}))
                for event in list(payload.get("events", []) or [])
            ],
        )


@dataclass
class UrlInspectionResult:
    url: str = ""
    normalized_url: str = ""
    cleaned_url: str = ""
    looks_like_youtube_url: bool = False
    is_playlist: bool = False
    remote_checked: bool = False
    remotely_accessible: bool | None = None
    info_fetched: bool = False
    title: str = ""
    item_count: int | None = None
    info_lines: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "normalized_url": self.normalized_url,
            "cleaned_url": self.cleaned_url,
            "looks_like_youtube_url": self.looks_like_youtube_url,
            "is_playlist": self.is_playlist,
            "remote_checked": self.remote_checked,
            "remotely_accessible": self.remotely_accessible,
            "info_fetched": self.info_fetched,
            "title": self.title,
            "item_count": self.item_count,
            "info_lines": list(self.info_lines),
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UrlInspectionResult":
        return cls(
            url=str(payload.get("url", "") or ""),
            normalized_url=str(payload.get("normalized_url", "") or ""),
            cleaned_url=str(payload.get("cleaned_url", "") or ""),
            looks_like_youtube_url=bool(payload.get("looks_like_youtube_url", False)),
            is_playlist=bool(payload.get("is_playlist", False)),
            remote_checked=bool(payload.get("remote_checked", False)),
            remotely_accessible=payload.get("remotely_accessible", None),
            info_fetched=bool(payload.get("info_fetched", False)),
            title=str(payload.get("title", "") or ""),
            item_count=(
                None
                if payload.get("item_count", None) is None
                else int(payload.get("item_count", 0) or 0)
            ),
            info_lines=[str(item) for item in list(payload.get("info_lines", []) or [])],
            error=str(payload.get("error", "") or ""),
        )


@dataclass
class HealthCheckItem:
    name: str = ""
    ok: bool = False
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "message": self.message,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HealthCheckItem":
        return cls(
            name=str(payload.get("name", "") or ""),
            ok=bool(payload.get("ok", False)),
            message=str(payload.get("message", "") or ""),
            details=dict(payload.get("details", {}) or {}),
        )


@dataclass
class HealthCheckReport:
    ok: bool = False
    items: list[HealthCheckItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "HealthCheckReport":
        return cls(
            ok=bool(payload.get("ok", False)),
            items=[
                HealthCheckItem.from_dict(dict(item or {}))
                for item in list(payload.get("items", []) or [])
            ],
        )
