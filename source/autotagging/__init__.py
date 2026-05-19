"""Shared autotagging package preparation primitives."""

from autotagging.candidate_resolver import CandidateResolver, TagCandidate
from autotagging.event_logger import TaggingEventLogger
from autotagging.models import TaggingPackage, TaggingSourceSnapshot
from autotagging.musicbrainz_enricher import MusicBrainzEnricher
from autotagging.package_builder import TaggingPackageBuilder, TaggingQueueStore
from autotagging.reporting import (
    format_events,
    format_queue_snapshot,
    format_repair_plans,
    format_requeue_results,
    format_review_candidates,
    format_session_snapshot,
)
from autotagging.standalone_app import (
    TaggingRepairPlanner,
    TaggingReviewStore,
    TaggingStandaloneCLI,
    TaggingStandaloneService,
)
from autotagging.tag_writer import TagWriteResult, TagWriter
from autotagging.title_normalizer import TitleNormalizer
from autotagging.worker import TaggingWorker

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
