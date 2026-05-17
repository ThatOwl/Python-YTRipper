"""Shared autotagging package preparation primitives."""

from .models import TaggingPackage, TaggingSourceSnapshot
from .candidate_resolver import CandidateResolver, TagCandidate
from .package_builder import TaggingPackageBuilder, TaggingQueueStore
from .tag_writer import TagWriteResult, TagWriter
from .title_normalizer import TitleNormalizer
from .worker import TaggingWorker

__all__ = [
    "CandidateResolver",
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
