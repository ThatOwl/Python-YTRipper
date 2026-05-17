import time
from pathlib import Path
from typing import Any

from utility.logger import get_logger

from .package_builder import TaggingQueueStore
from .title_normalizer import TitleNormalizer

logger = get_logger(__name__, "tagging_worker_debug.log")


class TaggingWorker:
    """Filesystem-backed background worker for prepared tagging packages."""

    def __init__(
        self,
        queue_store: TaggingQueueStore | None = None,
        title_normalizer: TitleNormalizer | None = None,
        poll_interval: float = 1.0,
        idle_timeout: float = 30.0,
    ):
        self.queue_store = queue_store or TaggingQueueStore()
        self.title_normalizer = title_normalizer or TitleNormalizer()
        self.poll_interval = poll_interval
        self.idle_timeout = idle_timeout

    def run_until_idle(self) -> int:
        processed_count = 0
        deadline = time.monotonic() + self.idle_timeout

        while True:
            processed = self.process_next_pending_package()
            if processed:
                processed_count += 1
                deadline = time.monotonic() + self.idle_timeout
                continue

            if time.monotonic() >= deadline:
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
        payload["state"] = "processing"
        self.queue_store.write_package(processing_path, payload)

        try:
            payload = self._apply_title_normalization(payload)
            payload["state"] = "done"
            completed_actions = list(payload.get("completed_actions", []))
            if "normalize_title" not in completed_actions:
                completed_actions.append("normalize_title")
            payload["completed_actions"] = completed_actions
            done_path = self.queue_store.move_package(processing_path, "done")
            self.queue_store.write_package(done_path, payload)
            logger.info("Processed tagging package: %s", done_path)
            return done_path
        except Exception as exc:
            payload["state"] = "failed"
            errors = list(payload.get("errors", []))
            errors.append(str(exc))
            payload["errors"] = errors
            failed_path = self.queue_store.move_package(processing_path, "failed")
            self.queue_store.write_package(failed_path, payload)
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
        return payload
