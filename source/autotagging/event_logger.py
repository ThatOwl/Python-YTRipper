import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utility.logger import get_logger

logger = get_logger(__name__, "tagging_event_logger_debug.log")


class TaggingEventLogger:
    """Append-only JSONL event logger for tagging package lifecycle events."""

    def __init__(self, event_log_path: Path | str):
        self.event_log_path = Path(event_log_path)

    def emit(self, event_type: str, **payload: Any) -> None:
        record = {
            "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "event_type": event_type,
            **payload,
        }
        try:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.event_log_path, "a", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False)
                handle.write("\n")
        except Exception as exc:
            logger.warning("Failed to append tagging event %s: %s", event_type, exc)

    def emit_package_event(
        self,
        event_type: str,
        package_payload: dict[str, Any],
        **extra: Any,
    ) -> None:
        lifecycle = dict(package_payload.get("lifecycle", {}) or {})
        self.emit(
            event_type,
            job_id=package_payload.get("job_id", ""),
            session_id=package_payload.get("session_id", ""),
            sequence_no=package_payload.get("sequence_no", 0),
            state=package_payload.get("state", ""),
            final_output_path=package_payload.get("final_output_path", ""),
            source_url=(package_payload.get("source", {}) or {}).get("url", ""),
            lifecycle_last_transition_at=lifecycle.get("last_transition_at", ""),
            **extra,
        )

    def read_events(
        self,
        *,
        limit: int | None = None,
        session_id: str | None = None,
        job_id: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read recent structured events from the JSONL log with optional filters."""
        if not self.event_log_path.exists():
            return []

        matched: list[dict[str, Any]] = []
        try:
            with open(self.event_log_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if session_id and str(record.get("session_id", "")) != session_id:
                        continue
                    if job_id and str(record.get("job_id", "")) != job_id:
                        continue
                    if event_type and str(record.get("event_type", "")) != event_type:
                        continue
                    matched.append(record)
        except Exception as exc:
            logger.warning("Failed to read tagging events from %s: %s", self.event_log_path, exc)
            return []

        matched.sort(key=lambda record: str(record.get("at", "")), reverse=True)
        if limit is not None and limit >= 0:
            return matched[:limit]
        return matched
