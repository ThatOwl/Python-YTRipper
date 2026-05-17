import time
from pathlib import Path
from typing import Any

from utility.logger import get_logger

from .candidate_resolver import CandidateResolver
from .musicbrainz_enricher import MusicBrainzEnricher
from .package_builder import TaggingQueueStore
from .tag_writer import TagWriter
from .title_normalizer import TitleNormalizer

logger = get_logger(__name__, "tagging_worker_debug.log")


class TaggingWorker:
    """Filesystem-backed background worker for prepared tagging packages."""

    def __init__(
        self,
        queue_store: TaggingQueueStore | None = None,
        title_normalizer: TitleNormalizer | None = None,
        candidate_resolver: CandidateResolver | None = None,
        musicbrainz_enricher: MusicBrainzEnricher | None = None,
        tag_writer: TagWriter | None = None,
        poll_interval: float = 1.0,
        idle_timeout: float = 30.0,
    ):
        self.queue_store = queue_store or TaggingQueueStore()
        self.title_normalizer = title_normalizer or TitleNormalizer()
        self.candidate_resolver = candidate_resolver or CandidateResolver()
        self.musicbrainz_enricher = musicbrainz_enricher or MusicBrainzEnricher()
        self.tag_writer = tag_writer or TagWriter()
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
            completed_actions = list(payload.get("completed_actions", []))
            if "normalize_title" not in completed_actions:
                completed_actions.append("normalize_title")
            payload = self._resolve_candidates(payload)
            if "resolve_candidates" not in completed_actions:
                completed_actions.append("resolve_candidates")
            payload["completed_actions"] = completed_actions
            payload, was_enriched = self._maybe_enrich_candidate(payload)
            if was_enriched:
                completed_actions = list(payload.get("completed_actions", []))
                if "enrich_candidate" not in completed_actions:
                    completed_actions.append("enrich_candidate")
                payload["completed_actions"] = completed_actions
            payload, final_state = self._maybe_write_tags(payload)
            target_state_dir = "failed" if final_state == "failed" else "done"
            final_path = self.queue_store.move_package(processing_path, target_state_dir)
            payload["state"] = final_state
            self.queue_store.write_package(final_path, payload)
            logger.info("Processed tagging package: %s", final_path)
            return final_path
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

    def _resolve_candidates(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidate = self.candidate_resolver.resolve(payload)
        payload["resolved_tags"] = candidate.to_dict()
        return payload

    def _maybe_enrich_candidate(self, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        candidate_dict = dict(payload.get("resolved_tags", {}) or {})
        if candidate_dict.get("write_allowed"):
            return payload, False

        current_candidate = self.candidate_resolver.resolve(payload)
        enriched_candidate = self.musicbrainz_enricher.enrich(payload, current_candidate)
        if enriched_candidate is None:
            payload["enrichment_result"] = {"status": "no_match"}
            return payload, False

        payload["resolved_tags"] = enriched_candidate.to_dict()
        payload["enrichment_result"] = {
            "status": "matched",
            "source": enriched_candidate.source,
            "confidence": enriched_candidate.confidence,
            "write_allowed": enriched_candidate.write_allowed,
        }
        return payload, True

    def _maybe_write_tags(self, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        requested_actions = set(payload.get("requested_actions", []) or [])
        candidate = dict(payload.get("resolved_tags", {}) or {})

        if "autotag" not in requested_actions:
            return payload, "done"

        if not candidate.get("write_allowed"):
            payload["write_result"] = {
                "success": False,
                "status": "skipped: candidate not safe for auto-write",
                "wrote_fields": [],
            }
            if payload.get("enrichment_result", {}).get("status") == "matched":
                return payload, "enriched"
            return payload, "skipped"

        candidate_obj = self.candidate_resolver.resolve(payload)
        result = self.tag_writer.write_candidate(payload.get("final_output_path", ""), candidate_obj)
        payload["write_result"] = result.to_dict()
        if result.success:
            completed_actions = list(payload.get("completed_actions", []))
            if "write_tags" not in completed_actions:
                completed_actions.append("write_tags")
            payload["completed_actions"] = completed_actions
            return payload, "written"

        return payload, "failed"
