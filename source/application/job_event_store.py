from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import utility.preferences as preferences
from application.state_models import JobEvent
from utility.logger import get_logger

logger = get_logger(__name__, "job_event_store_debug.log")


class JobEventStore:
    """Append-only JSONL store for web job lifecycle events."""

    def __init__(self, event_log_path: Path | str | None = None):
        self.event_log_path = Path(event_log_path or preferences.WEB_GUI_EVENTS_PATH)

    def append(self, event: JobEvent) -> None:
        record = event.to_dict()
        if not record.get("at"):
            record["at"] = self._utc_now_iso()

        try:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.event_log_path, "a", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False)
                handle.write("\n")
        except Exception as exc:
            logger.warning("Failed to append job event %s: %s", record.get("event_type", ""), exc)

    def emit(
        self,
        event_type: str,
        *,
        job_id: str = "",
        session_id: str = "",
        message: str = "",
        payload: dict | None = None,
    ) -> JobEvent:
        event = JobEvent(
            at=self._utc_now_iso(),
            event_type=event_type,
            job_id=job_id,
            session_id=session_id,
            message=message,
            payload=dict(payload or {}),
        )
        self.append(event)
        return event

    def read_events(
        self,
        *,
        limit: int | None = None,
        session_id: str | None = None,
        job_id: str | None = None,
        event_type: str | None = None,
    ) -> list[JobEvent]:
        if not self.event_log_path.exists():
            return []

        matched: list[JobEvent] = []
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

                    event = JobEvent.from_dict(dict(record or {}))
                    if session_id and event.session_id != session_id:
                        continue
                    if job_id and event.job_id != job_id:
                        continue
                    if event_type and event.event_type != event_type:
                        continue
                    matched.append(event)
        except Exception as exc:
            logger.warning("Failed to read job events from %s: %s", self.event_log_path, exc)
            return []

        matched.sort(key=lambda event: event.at, reverse=True)
        if limit is not None and limit >= 0:
            return matched[:limit]
        return matched

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
