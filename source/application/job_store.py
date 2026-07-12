from __future__ import annotations

import json
from pathlib import Path

import utility.preferences as preferences
from application.state_models import JobDetail, JobSummary
from utility.logger import get_logger

logger = get_logger(__name__, "job_store_debug.log")


class JobStore:
    """Filesystem-backed persistent store for web job detail and summaries."""

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir or preferences.WEB_GUI_JOBS_DIR)

    def save_detail(self, detail: JobDetail) -> Path:
        job_id = detail.summary.job_id.strip()
        if not job_id:
            raise ValueError("Job detail must contain a non-empty summary.job_id")

        output_path = self._job_path(job_id)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = detail.to_dict()
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        return output_path

    def save_summary(self, summary: JobSummary) -> Path:
        existing = self.get_detail(summary.job_id)
        if existing is None:
            detail = JobDetail(summary=summary)
        else:
            detail = existing
            detail.summary = summary
        return self.save_detail(detail)

    def get_detail(self, job_id: str) -> JobDetail | None:
        job_path = self._job_path(job_id)
        if not job_path.exists():
            return None

        try:
            with open(job_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return JobDetail.from_dict(dict(payload or {}))
        except Exception as exc:
            logger.warning("Failed to read job detail %s: %s", job_path, exc)
            return None

    def get_summary(self, job_id: str) -> JobSummary | None:
        detail = self.get_detail(job_id)
        return detail.summary if detail is not None else None

    def list_summaries(
        self,
        *,
        limit: int | None = None,
        status: str | None = None,
    ) -> list[JobSummary]:
        if not self.base_dir.exists():
            return []

        summaries: list[JobSummary] = []
        for job_path in sorted(self.base_dir.glob("*.json")):
            try:
                with open(job_path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                summary = JobDetail.from_dict(dict(payload or {})).summary
            except Exception as exc:
                logger.warning("Failed to read job summary from %s: %s", job_path, exc)
                continue

            if status and summary.status != status:
                continue
            summaries.append(summary)

        summaries.sort(
            key=lambda summary: (
                summary.created_at,
                summary.started_at,
                summary.job_id,
            ),
            reverse=True,
        )
        if limit is not None and limit >= 0:
            return summaries[:limit]
        return summaries

    def _job_path(self, job_id: str) -> Path:
        normalized = job_id.strip()
        if not normalized:
            raise ValueError("job_id cannot be empty")
        return self.base_dir / f"{normalized}.json"
