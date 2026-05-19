from autotagging.core.candidate_resolver import CandidateResolver, TagCandidate
from autotagging.core.evidence_extractor import ParsedTitleHint, SourceEvidence, SourceEvidenceExtractor
from autotagging.core.musicbrainz_enricher import MusicBrainzEnricher
from autotagging.core.tag_writer import TagWriteResult, TagWriter
from autotagging.core.title_normalizer import TitleNormalizer

__all__ = [
    "CandidateResolver",
    "MusicBrainzEnricher",
    "ParsedTitleHint",
    "SourceEvidence",
    "SourceEvidenceExtractor",
    "TagCandidate",
    "TagWriteResult",
    "TagWriter",
    "TitleNormalizer",
]
