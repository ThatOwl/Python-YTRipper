from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Callable

from application.job_event_store import JobEventStore
from application.job_store import JobStore
from application.session_config_service import SessionConfigService
from application.state_models import JobDetail, JobItemStatus, JobSummary
from infrastructure.url_handler import URLHandler
from utility.logger import get_logger
from utility.utils import DownloadOptions, DownloadResult

logger = get_logger(__name__, "download_job_service_debug.log")


class DownloadJobService:
    """Run downloader work in background threads and persist coarse job state."""

    def __init__(
        self,
        *,
        job_store: JobStore | None = None,
        event_store: JobEventStore | None = None,
        config_service: SessionConfigService | None = None,
        url_handler: URLHandler | None = None,
        download_runner: Callable[[str, DownloadOptions], list[DownloadResult]] | None = None,
        session_id: str | None = None,
    ):
        self.job_store = job_store or JobStore()
        self.event_store = event_store or JobEventStore()
        self.config_service = config_service or SessionConfigService()
        self.url_handler = url_handler or URLHandler()
        self._download_runner = download_runner
        self.session_id = session_id or str(uuid.uuid4())
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()

    def start_url_job(self, *, url: str, options: DownloadOptions) -> JobSummary:
        option_snapshot = self.config_service.clone_options(options)
        self.config_service.normalize_options(option_snapshot, apply_runtime=False)
        job_id = str(uuid.uuid4())
        job_kind = "playlist" if self.url_handler.is_youtube_playlist(url) else "single"
        created_at = self._utc_now_iso()
        summary = JobSummary(
            job_id=job_id,
            job_kind=job_kind,
            created_at=created_at,
            status="queued",
            source_label=url,
            download_dir=str(option_snapshot.default_download_directory or ""),
            option_snapshot=option_snapshot.to_dict(),
        )
        detail = JobDetail(summary=summary)

        with self._lock:
            self.job_store.save_detail(detail)
            self.event_store.emit(
                "job_created",
                job_id=job_id,
                session_id=self.session_id,
                message="Download job created",
                payload={"url": url, "job_kind": job_kind},
            )

            thread = threading.Thread(
                target=self._run_url_job,
                args=(job_id, url, option_snapshot),
                daemon=True,
                name=f"download-job-{job_id[:8]}",
            )
            self._threads[job_id] = thread
            thread.start()

        return summary

    def get_job_detail(self, job_id: str) -> JobDetail | None:
        with self._lock:
            return self.job_store.get_detail(job_id)

    def get_job_summary(self, job_id: str) -> JobSummary | None:
        with self._lock:
            return self.job_store.get_summary(job_id)

    def list_jobs(self, *, limit: int | None = None, status: str | None = None) -> list[JobSummary]:
        with self._lock:
            return self.job_store.list_summaries(limit=limit, status=status)

    def wait_for_job(self, job_id: str, timeout: float | None = None) -> bool:
        thread = self._threads.get(job_id)
        if thread is None:
            return True
        thread.join(timeout=timeout)
        return not thread.is_alive()

    def _run_url_job(self, job_id: str, url: str, option_snapshot: DownloadOptions) -> None:
        self._update_status(job_id, "validating", started=True)
        self.event_store.emit(
            "job_started",
            job_id=job_id,
            session_id=self.session_id,
            message="Download job started",
            payload={"url": url},
        )

        try:
            self._update_status(job_id, "running")
            results = self._resolve_download_runner()(url, option_snapshot)
            self._finalize_job(job_id, results)
        except Exception as exc:
            logger.error("Download job %s failed: %s", job_id, exc)
            self._finalize_failure(job_id, str(exc))
        finally:
            with self._lock:
                self._threads.pop(job_id, None)

    def _resolve_download_runner(self) -> Callable[[str, DownloadOptions], list[DownloadResult]]:
        if self._download_runner is not None:
            return self._download_runner

        from application.download_orchestrator import DownloadOrchestrator

        orchestrator = DownloadOrchestrator()
        self._download_runner = lambda url, options: orchestrator.download(url=url, options=options)
        return self._download_runner

    def _update_status(self, job_id: str, status: str, *, started: bool = False) -> None:
        with self._lock:
            detail = self.job_store.get_detail(job_id)
            if detail is None:
                return
            detail.summary.status = status
            if started and not detail.summary.started_at:
                detail.summary.started_at = self._utc_now_iso()
            self.job_store.save_detail(detail)

    def _finalize_job(self, job_id: str, results: list[DownloadResult]) -> None:
        with self._lock:
            detail = self.job_store.get_detail(job_id)
            if detail is None:
                return

            if not results:
                detail.summary.status = "failed"
                detail.summary.finished_at = self._utc_now_iso()
                self.job_store.save_detail(detail)
                self.event_store.emit(
                    "job_failed",
                    job_id=job_id,
                    session_id=self.session_id,
                    message="Download job produced no results",
                )
                return

            detail.items = [self._item_from_result(index, result) for index, result in enumerate(results, start=1)]
            detail.summary.items_total = len(detail.items)
            detail.summary.items_done = len(detail.items)
            detail.summary.items_failed = sum(1 for item in detail.items if item.success is False)
            detail.summary.finished_at = self._utc_now_iso()
            detail.summary.current_item_label = ""

            if detail.summary.items_failed == 0:
                detail.summary.status = "completed"
                event_type = "job_completed"
                message = "Download job completed successfully"
            elif detail.summary.items_failed == detail.summary.items_total:
                detail.summary.status = "failed"
                event_type = "job_failed"
                message = "Download job failed"
            else:
                detail.summary.status = "partial"
                event_type = "job_partial"
                message = "Download job completed with partial failures"

            self.job_store.save_detail(detail)
            self.event_store.emit(
                event_type,
                job_id=job_id,
                session_id=self.session_id,
                message=message,
                payload={
                    "items_total": detail.summary.items_total,
                    "items_failed": detail.summary.items_failed,
                },
            )

    def _finalize_failure(self, job_id: str, error_message: str) -> None:
        with self._lock:
            detail = self.job_store.get_detail(job_id)
            if detail is None:
                return

            detail.summary.status = "failed"
            detail.summary.finished_at = self._utc_now_iso()
            detail.summary.items_total = max(detail.summary.items_total, 1)
            detail.summary.items_failed = max(detail.summary.items_failed, 1)
            detail.summary.current_item_label = ""
            detail.items.append(
                JobItemStatus(
                    item_id="1",
                    label=detail.summary.source_label,
                    source_url=detail.summary.source_label,
                    status="failed",
                    success=False,
                    error=error_message,
                )
            )
            self.job_store.save_detail(detail)
            self.event_store.emit(
                "job_failed",
                job_id=job_id,
                session_id=self.session_id,
                message="Download job raised an exception",
                payload={"error": error_message},
            )

    @staticmethod
    def _item_from_result(index: int, result: DownloadResult) -> JobItemStatus:
        return JobItemStatus(
            item_id=str(index),
            label=result.video_title,
            source_url=result.video_url,
            status="success" if result.success else "failed",
            success=result.success,
            output_path=str(result.output_path or ""),
            error="; ".join(result.errors),
        )

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
