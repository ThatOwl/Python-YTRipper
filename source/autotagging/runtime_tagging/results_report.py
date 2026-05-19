import csv
import io
from pathlib import Path
from typing import Any

from utility.logger import get_logger
from utility.utils import DownloadResult, sanitize_filename

logger = get_logger(__name__, "tagging_results_report_debug.log")


RESULT_REPORT_FIELDS = [
    "job_id",
    "video_url",
    "playlist_title",
    "source_author",
    "source_title",
    "final_output_path",
    "download_status",
    "download_errors",
    "tag_state",
    "written_artist",
    "written_title",
    "resolved_artist",
    "resolved_title",
    "resolved_album",
    "candidate_source",
    "candidate_confidence",
    "candidate_write_allowed",
    "enrichment_source",
    "tag_reason",
    "candidate_notes",
]


class TaggingResultsReport:
    """Maintain one mutable CSV that downloader seeds and the tagger later updates."""

    def build_report_path(
        self,
        download_dir: str | Path,
        *,
        playlist_name: str | None = None,
        timestamp_label: str,
        batch_mode: bool = False,
    ) -> Path:
        target_dir = Path(download_dir).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)

        if not batch_mode and playlist_name:
            safe_name = sanitize_filename(playlist_name).strip() or "playlist"
            return target_dir / f"{timestamp_label}_{safe_name}_results.csv"

        return target_dir / f"{timestamp_label}_batch_results.csv"

    def upsert_download_results(
        self,
        results: list[DownloadResult],
        *,
        report_path: str | Path,
    ) -> Path:
        path = Path(report_path)
        rows = self._read_rows(path)
        indexed_rows = {self._row_key(row): row for row in rows}

        for result in results:
            row = self._row_from_download_result(result)
            indexed_rows[self._row_key(row)] = row

        self._write_rows(path, indexed_rows.values())
        return path

    def update_from_package(self, payload: dict[str, Any]) -> Path | None:
        report_info = dict(payload.get("result_report", {}) or {})
        report_path = report_info.get("report_path")
        if not report_path:
            return None

        path = Path(str(report_path))
        rows = self._read_rows(path)
        indexed_rows = {self._row_key(row): row for row in rows}
        matched_key = self._find_existing_key(payload, indexed_rows)
        row = self._row_from_package(payload, indexed_rows, matched_key)
        if matched_key and matched_key != self._row_key(row):
            indexed_rows.pop(matched_key, None)
        indexed_rows[self._row_key(row)] = row
        self._write_rows(path, indexed_rows.values())
        return path

    def _read_rows(self, report_path: Path) -> list[dict[str, str]]:
        if not report_path.exists():
            return []

        try:
            with open(report_path, "r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                return [self._normalize_row(dict(row)) for row in reader]
        except Exception as exc:
            logger.warning("Failed to read results report %s: %s", report_path, exc)
            return []

    def _write_rows(self, report_path: Path, rows: Any) -> None:
        normalized_rows = [self._normalize_row(dict(row)) for row in rows]
        normalized_rows.sort(
            key=lambda row: (
                row.get("playlist_title", ""),
                row.get("source_title", ""),
                row.get("video_url", ""),
                row.get("job_id", ""),
            )
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RESULT_REPORT_FIELDS)
            writer.writeheader()
            for row in normalized_rows:
                writer.writerow({field: row.get(field, "") for field in RESULT_REPORT_FIELDS})

    def _row_from_download_result(self, result: DownloadResult) -> dict[str, str]:
        return self._normalize_row(
            {
                "job_id": getattr(result, "tagging_job_id", "") or "",
                "video_url": result.video_url,
                "playlist_title": getattr(result, "playlist_title", "") or "",
                "source_author": getattr(result, "source_author", "") or "",
                "source_title": result.video_title,
                "final_output_path": str(result.output_path or ""),
                "download_status": "downloaded" if result.success else "download_failed",
                "download_errors": "|".join(result.errors),
                "tag_state": getattr(result, "tagging_state", "") or "",
                "written_artist": "",
                "written_title": "",
                "resolved_artist": "",
                "resolved_title": "",
                "resolved_album": "",
                "candidate_source": "",
                "candidate_confidence": "",
                "candidate_write_allowed": "",
                "enrichment_source": "",
                "tag_reason": getattr(result, "tagging_reason", "") or "",
                "candidate_notes": "",
            }
        )

    def _row_from_package(
        self,
        payload: dict[str, Any],
        indexed_rows: dict[str, dict[str, str]],
        matched_key: str | None,
    ) -> dict[str, str]:
        job_id = str(payload.get("job_id", "") or "")
        final_output_path = str(payload.get("final_output_path", "") or "")
        source = dict(payload.get("source", {}) or {})
        resolved_tags = dict(payload.get("resolved_tags", {}) or {})
        enrichment_result = dict(payload.get("enrichment_result", {}) or {})
        write_result = dict(payload.get("write_result", {}) or {})
        existing_row = indexed_rows.get(matched_key or "") or {}
        candidate_notes = resolved_tags.get("notes", [])
        wrote_fields = set(str(field) for field in list(write_result.get("wrote_fields", []) or []))
        state = str(payload.get("state", "") or "")

        row = dict(existing_row)
        row.update(
            self._normalize_row(
                {
                    "job_id": job_id,
                    "video_url": source.get("url", ""),
                    "playlist_title": payload.get("playlist_title", ""),
                    "source_author": source.get("author", ""),
                    "source_title": source.get("title", ""),
                    "final_output_path": final_output_path,
                    "download_status": existing_row.get("download_status", "downloaded") or "downloaded",
                    "download_errors": existing_row.get("download_errors", ""),
                    "tag_state": state,
                    "written_artist": resolved_tags.get("artist", "") if state == "written" and "artist" in wrote_fields else "",
                    "written_title": resolved_tags.get("title", "") if state == "written" and "title" in wrote_fields else "",
                    "resolved_artist": resolved_tags.get("artist", ""),
                    "resolved_title": resolved_tags.get("title", ""),
                    "resolved_album": resolved_tags.get("album", ""),
                    "candidate_source": resolved_tags.get("source", ""),
                    "candidate_confidence": self._stringify_scalar(resolved_tags.get("confidence", "")),
                    "candidate_write_allowed": self._stringify_scalar(resolved_tags.get("write_allowed", "")),
                    "enrichment_source": enrichment_result.get("source", ""),
                    "tag_reason": self._derive_tag_reason(payload),
                    "candidate_notes": self._stringify_list(candidate_notes),
                }
            )
        )
        return row

    @staticmethod
    def _find_existing_key(payload: dict[str, Any], indexed_rows: dict[str, dict[str, str]]) -> str | None:
        job_id = str(payload.get("job_id", "") or "")
        final_output_path = str(payload.get("final_output_path", "") or "")

        if job_id and job_id in indexed_rows:
            return job_id
        if final_output_path and final_output_path in indexed_rows:
            return final_output_path
        return None

    @staticmethod
    def _row_key(row: dict[str, str]) -> str:
        job_id = str(row.get("job_id", "") or "").strip()
        if job_id:
            return job_id

        output_path = str(row.get("final_output_path", "") or "").strip()
        if output_path:
            return output_path

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                row.get("video_url", ""),
                row.get("source_title", ""),
                row.get("playlist_title", ""),
                row.get("download_status", ""),
            ]
        )
        return buffer.getvalue().strip()

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, str]:
        normalized = {field: "" for field in RESULT_REPORT_FIELDS}
        for field in RESULT_REPORT_FIELDS:
            normalized[field] = TaggingResultsReport._stringify_scalar(row.get(field, ""))
        return normalized

    @staticmethod
    def _stringify_list(values: Any) -> str:
        if isinstance(values, (list, tuple, set)):
            return "|".join(str(value) for value in values if str(value).strip())
        return TaggingResultsReport._stringify_scalar(values)

    @staticmethod
    def _stringify_scalar(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _derive_tag_reason(payload: dict[str, Any]) -> str:
        state = str(payload.get("state", "") or "")
        resolved_tags = dict(payload.get("resolved_tags", {}) or {})
        enrichment_result = dict(payload.get("enrichment_result", {}) or {})
        write_result = dict(payload.get("write_result", {}) or {})
        errors = list(payload.get("errors", []) or [])

        if state == "written":
            return "written"
        if state == "skipped":
            if enrichment_result.get("status") == "matched":
                return f"enriched_not_safe:{enrichment_result.get('source', '') or resolved_tags.get('source', '')}"
            return f"candidate_not_safe:{resolved_tags.get('source', '')}"
        if state == "enriched":
            return f"enriched_not_safe:{enrichment_result.get('source', '') or resolved_tags.get('source', '')}"
        if state == "failed":
            if write_result.get("status"):
                return str(write_result.get("status", ""))
            if errors:
                return f"processing_failed:{errors[-1]}"
            return "processing_failed"
        if write_result.get("status"):
            return str(write_result.get("status", ""))
        return ""
