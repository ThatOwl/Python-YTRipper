"""Shared autotagging package preparation primitives."""

from .candidate_resolver import CandidateResolver, TagCandidate
from .event_logger import TaggingEventLogger
from .models import TaggingPackage, TaggingSourceSnapshot
from .musicbrainz_enricher import MusicBrainzEnricher
from .package_builder import TaggingPackageBuilder, TaggingQueueStore
from .reporting import (
    format_events,
    format_queue_snapshot,
    format_repair_plans,
    format_requeue_results,
    format_review_candidates,
    format_session_snapshot,
)
from .standalone_app import TaggingRepairPlanner, TaggingReviewStore, TaggingStandaloneCLI, TaggingStandaloneService
from .tag_writer import TagWriteResult, TagWriter
from .title_normalizer import TitleNormalizer
from .worker import TaggingWorker

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
