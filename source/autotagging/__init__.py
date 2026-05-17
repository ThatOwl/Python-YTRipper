"""Shared autotagging package preparation primitives."""

from .candidate_resolver import CandidateResolver, TagCandidate
from .event_logger import TaggingEventLogger
from .models import TaggingPackage, TaggingSourceSnapshot
from .musicbrainz_enricher import MusicBrainzEnricher
from .package_builder import TaggingPackageBuilder, TaggingQueueStore
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
    "TagWriteResult",
    "TagWriter",
    "TitleNormalizer",
    "TaggingWorker",
]
