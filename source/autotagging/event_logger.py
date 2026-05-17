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
