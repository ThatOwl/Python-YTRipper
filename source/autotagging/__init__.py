"""Shared autotagging package preparation primitives."""

from autotagging.core.candidate_resolver import CandidateResolver, TagCandidate
from autotagging.core.musicbrainz_enricher import MusicBrainzEnricher
from autotagging.core.tag_writer import TagWriteResult, TagWriter
from autotagging.core.title_normalizer import TitleNormalizer
from autotagging.runtime_tagging.event_logger import TaggingEventLogger
from autotagging.runtime_tagging.models import TaggingPackage, TaggingSourceSnapshot
from autotagging.runtime_tagging.package_builder import TaggingPackageBuilder, TaggingQueueStore
from autotagging.runtime_tagging.worker import TaggingWorker
from autotagging.standalone.app import TaggingStandaloneCLI, TaggingStandaloneService
from autotagging.standalone.repair_planner import TaggingRepairPlanner
from autotagging.standalone.reporting import (
    format_events,
    format_queue_snapshot,
    format_repair_plans,
    format_requeue_results,
    format_review_candidates,
    format_session_snapshot,
)
from autotagging.standalone.review_store import TaggingReviewStore

__all__ = [
    "CandidateResolver",
    "TaggingEventLogger",
    "MusicBrainzEnricher",
    "TagCandidate",
    "TaggingPackage",
    "TaggingSourceSnapshot",
    "TaggingPackageBuilder",
    "TaggingQueueStore",
    "TaggingRepairPlanner",
    "TaggingReviewStore",
    "TaggingStandaloneCLI",
    "TaggingStandaloneService",
    "format_events",
    "format_queue_snapshot",
    "format_repair_plans",
    "format_requeue_results",
    "format_review_candidates",
    "format_session_snapshot",
    "TagWriteResult",
    "TagWriter",
    "TitleNormalizer",
    "TaggingWorker",
]
