import csv
import io
import json
from typing import Any

PACKAGE_SUMMARY_FIELDS = [
    "job_id",
    "session_id",
    "sequence_no",
    "state",
    "created_at",
    "last_transition_at",
    "playlist_title",
    "source_author",
    "source_title",
    "requested_actions",
    "candidate_source",
    "candidate_confidence",
    "write_allowed",
    "write_status",
    "final_output_path",
]

EVENT_FIELDS = [
    "at",
    "event_type",
    "job_id",
    "session_id",
    "sequence_no",
    "state",
    "candidate_source",
    "candidate_confidence",
    "candidate_write_allowed",
    "guessed_artist",
    "guessed_title",
    "split_confidence",
    "enrichment_backend",
    "reason",
    "wrote_fields",
    "queue_path",
    "source_url",
    "final_output_path",
]

REQUEUE_RESULT_FIELDS = [
    "job_id",
    "session_id",
    "sequence_no",
    "source_state",
    "target_state",
    "status",
    "worker_processed",
    "final_state",
    "source_queue_path",
    "target_queue_path",
    "final_queue_path",
    "final_output_path",
]


def format_queue_snapshot(snapshot: dict[str, Any], output_format: str = "csv", view: str = "both") -> str:
    if output_format == "json":
        return json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"

    sections: list[str] = []
    if view in ("counts", "both"):
        count_rows = [
            {"state": state_name, "count": snapshot.get("counts", {}).get(state_name, 0)}
            for state_name in ("pending", "processing", "done", "failed")
        ]
        sections.append(_rows_to_csv(["state", "count"], count_rows))

    if view in ("recent", "both"):
        recent_rows: list[dict[str, Any]] = []
        for state_name in ("pending", "processing", "done", "failed"):
            for payload in snapshot.get("recent", {}).get(state_name, []):
                row = dict(payload)
                row["state"] = row.get("state") or state_name
                recent_rows.append(row)
        sections.append(_rows_to_csv(PACKAGE_SUMMARY_FIELDS, recent_rows))

    return "\n".join(section.rstrip("\n") for section in sections if section) + "\n"


def format_session_snapshot(snapshot: dict[str, Any], output_format: str = "csv") -> str:
    if output_format == "json":
        return json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    return _rows_to_csv(PACKAGE_SUMMARY_FIELDS, snapshot.get("packages", []))


def format_events(events: list[dict[str, Any]], output_format: str = "csv") -> str:
    if output_format == "json":
        return json.dumps(events, indent=2, ensure_ascii=False) + "\n"
    return _rows_to_csv(EVENT_FIELDS, events)


def format_requeue_results(results: list[dict[str, Any]], output_format: str = "csv") -> str:
    if output_format == "json":
        return json.dumps(results, indent=2, ensure_ascii=False) + "\n"
    return _rows_to_csv(REQUEUE_RESULT_FIELDS, results)


def _rows_to_csv(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: _csv_safe(row.get(field, "")) for field in fieldnames})
    return buffer.getvalue()


def _csv_safe(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, set)):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value
