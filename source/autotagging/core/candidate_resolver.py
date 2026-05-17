from dataclasses import asdict, dataclass
import unicodedata
from typing import Any

from .evidence_extractor import SourceEvidence, SourceEvidenceExtractor


@dataclass
class TagCandidate:
    artist: str = ""
    title: str = ""
    album: str = ""
    track: str = ""
    source: str = ""
    confidence: float = 0.0
    write_allowed: bool = False
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if payload["notes"] is None:
            payload["notes"] = []
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TagCandidate":
        data = dict(payload or {})
        notes = data.get("notes")
        if notes is None:
            data["notes"] = []
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CandidateResolver:
    """Resolve conservative tag candidates from prepared package evidence."""

    def __init__(
        self,
        evidence_extractor: SourceEvidenceExtractor | None = None,
    ):
        self.evidence_extractor = evidence_extractor or SourceEvidenceExtractor()

    def resolve(self, payload: dict[str, Any]) -> TagCandidate:
        source = payload.get("source", {}) or {}
        normalization = payload.get("normalization", {}) or {}
        title_analysis = normalization.get("title_analysis", {}) or {}
        playlist_title = (payload.get("playlist_title") or "").strip()
        guessed_artist = (title_analysis.get("guessed_artist") or "").strip()
        guessed_title = (title_analysis.get("guessed_title") or "").strip()
        lookup_title = (title_analysis.get("lookup_title") or "").strip()

        evidence = self.evidence_extractor.extract(
            source=source,
            title_analysis=title_analysis,
            guessed_artist=guessed_artist,
            guessed_title=guessed_title,
            lookup_title=lookup_title,
        )

        metadata_candidate = self._from_youtube_metadata(source.get("metadata"))
        if metadata_candidate is not None:
            return metadata_candidate

        description_candidate = self._from_description_evidence(
            title_analysis=title_analysis,
            evidence=evidence,
            playlist_title=playlist_title,
        )
        if description_candidate is not None:
            return description_candidate

        enriched_title_candidate = self._from_title_and_evidence(
            title_analysis=title_analysis,
            source=source,
            evidence=evidence,
        )
        if enriched_title_candidate is not None:
            return enriched_title_candidate

        title_hint_candidate = self._from_title_hints(
            title_analysis=title_analysis,
            evidence=evidence,
        )
        if title_hint_candidate is not None:
            return title_hint_candidate

        return self._from_title_analysis(title_analysis, source, evidence)

    def _from_youtube_metadata(self, metadata: Any) -> TagCandidate | None:
        flat = self._flatten_metadata(metadata)
        artist = self._pick_first(flat, ("artist", "artists", "music.artist", "music.artists"))
        title = self._pick_first(flat, ("title", "song", "track", "music.title", "music.song"))
        album = self._pick_first(flat, ("album", "music.album"))
        track = self._pick_first(flat, ("track_number", "tracknumber", "track.no"))

        if artist and title:
            return TagCandidate(
                artist=artist,
                title=title,
                album=album,
                track=track,
                source="youtube_metadata",
                confidence=0.98,
                write_allowed=True,
                notes=["resolved from explicit youtube metadata"],
            )
        return None

    def _from_description_evidence(
        self,
        *,
        title_analysis: dict[str, Any],
        evidence: SourceEvidence,
        playlist_title: str,
    ) -> TagCandidate | None:
        description_artist = (evidence.description_artist or "").strip()
        description_title = (evidence.description_title or "").strip()
        description_album = (evidence.description_album or "").strip()
        lookup_title = (title_analysis.get("lookup_title") or "").strip()
        guessed_artist = (title_analysis.get("guessed_artist") or "").strip()

        if not description_title:
            return None

        if evidence.description_kind == "description_song_by_artist" and not (
            evidence.description_artist_supported and evidence.description_title_supported
        ):
            return None

        resolved_artist = description_artist or evidence.canonical_author or guessed_artist
        if not resolved_artist:
            return None

        notes = [*evidence.notes] or ["resolved from structured description evidence"]
        if lookup_title and self._normalise_compare_text(lookup_title) == self._normalise_compare_text(description_title):
            notes.append("lookup title confirmed by description")
        return TagCandidate(
            artist=resolved_artist,
            title=description_title,
            album=description_album or "",
            source="description_structured",
            confidence=0.96 if description_album else 0.91,
            write_allowed=True,
            notes=notes,
        )

    def _from_title_hints(
        self,
        *,
        title_analysis: dict[str, Any],
        evidence: SourceEvidence,
    ) -> TagCandidate | None:
        split_confidence = (title_analysis.get("split_confidence") or "").strip()
        guessed_artist = (title_analysis.get("guessed_artist") or "").strip()

        for hint in evidence.title_hints:
            if hint.artist_is_contextual:
                continue
            if hint.source == "reverse_dash_artist_hint" and (
                split_confidence.startswith("author_matched")
                or self._artist_mentions_canonical_author(guessed_artist, evidence.canonical_author)
            ):
                continue
            if hint.artist_supported and hint.title_supported and hint.source not in {
                "reverse_dash_artist_hint",
                "context_dash_title_artist",
            }:
                return TagCandidate(
                    artist=hint.artist,
                    title=hint.title,
                    album=evidence.description_album or "",
                    source=hint.source,
                    confidence=max(0.90, hint.confidence),
                    write_allowed=True,
                    notes=[*hint.notes, "fan-upload title pattern confirmed by keywords"],
                )

        for hint in evidence.title_hints:
            if hint.artist_is_contextual:
                continue
            if hint.source == "reverse_dash_artist_hint" and (
                split_confidence.startswith("author_matched")
                or self._artist_mentions_canonical_author(guessed_artist, evidence.canonical_author)
            ):
                continue
            return TagCandidate(
                artist=hint.artist,
                title=hint.title,
                album=evidence.description_album or "",
                source=hint.source,
                confidence=hint.confidence,
                write_allowed=False,
                notes=[*hint.notes, "kept for confirmation because title pattern looks plausible"],
            )

        return None

    def _from_title_and_evidence(
        self,
        *,
        title_analysis: dict[str, Any],
        source: dict[str, Any],
        evidence: SourceEvidence,
    ) -> TagCandidate | None:
        guessed_artist = (title_analysis.get("guessed_artist") or "").strip()
        guessed_title = (title_analysis.get("guessed_title") or "").strip()
        split_confidence = (title_analysis.get("split_confidence") or "").strip()
        lookup_title = (title_analysis.get("lookup_title") or "").strip()

        if guessed_artist and guessed_title:
            if (
                not evidence.guessed_artist_is_contextual
                and not split_confidence.startswith("author_matched")
                and evidence.canonical_author
                and (
                self._values_match(evidence.canonical_author, guessed_artist)
                or (
                    evidence.keyword_support_artist
                    and self._artist_mentions_canonical_author(guessed_artist, evidence.canonical_author)
                )
                or self._artist_mentions_canonical_author(guessed_artist, evidence.canonical_author)
                )
                and self._title_looks_clean(guessed_title)
            ):
                notes = ["artist/title split supported by canonical uploader evidence"]
                if evidence.keyword_support_title:
                    notes.append("title also supported by keywords")
                if self._artist_mentions_canonical_author(guessed_artist, evidence.canonical_author):
                    notes.append("one collaboration artist matches the uploader")
                return TagCandidate(
                    artist=guessed_artist,
                    title=guessed_title,
                    album=evidence.description_album or "",
                    source="title_uploader_match",
                    confidence=0.92 if split_confidence == "dash_split" else 0.94,
                    write_allowed=True,
                    notes=notes,
                )

        if (
            guessed_artist
            and guessed_title
            and not evidence.guessed_artist_is_contextual
            and not split_confidence.startswith("author_matched")
            and evidence.keyword_support_artist
            and evidence.keyword_support_title
            and self._title_looks_clean(guessed_title)
        ):
            return TagCandidate(
                artist=guessed_artist,
                title=guessed_title,
                album=evidence.description_album or "",
                source="title_keyword_match",
                confidence=0.88,
                write_allowed=True,
                notes=["artist/title split supported by source keywords"],
            )

        if lookup_title and evidence.canonical_author and evidence.keyword_support_title:
            if evidence.author_is_topic or evidence.description_album:
                notes = ["lookup title supported by uploader and keywords"]
                if evidence.author_is_topic:
                    notes.append("topic uploader strongly suggests canonical artist")
                if evidence.description_album:
                    notes.append("album extracted from description")
                return TagCandidate(
                    artist=evidence.canonical_author,
                    title=lookup_title,
                    album=evidence.description_album or "",
                    source="author_keyword_match",
                    confidence=0.93 if evidence.description_album else 0.86,
                    write_allowed=bool(evidence.description_album or evidence.author_is_topic),
                    notes=notes,
                )

        return None

    def _from_title_analysis(
        self,
        title_analysis: dict[str, Any],
        source: dict[str, Any],
        evidence: SourceEvidence,
    ) -> TagCandidate:
        guessed_artist = (title_analysis.get("guessed_artist") or "").strip()
        guessed_title = (title_analysis.get("guessed_title") or "").strip()
        split_confidence = (title_analysis.get("split_confidence") or "").strip()
        lookup_title = (title_analysis.get("lookup_title") or "").strip()
        author = (source.get("author") or "").strip()
        notes: list[str] = []

        if guessed_artist and guessed_title and split_confidence.startswith("author_matched"):
            notes.append("resolved from author-matched dash split")
            return TagCandidate(
                artist=guessed_artist,
                title=guessed_title,
                album=evidence.description_album or "",
                source="title_author_match",
                confidence=0.90,
                write_allowed=True,
                notes=notes,
            )

        if guessed_artist and guessed_title and evidence.guessed_artist_is_contextual:
            notes.append("left side of dash split looks like playlist/franchise context")
            return TagCandidate(
                artist="",
                title=guessed_title,
                album=evidence.description_album or "",
                source="contextual_dash_split",
                confidence=0.52,
                write_allowed=False,
                notes=notes,
            )

        if guessed_artist and guessed_title:
            notes.append("dash split found but author did not confirm it")
            return TagCandidate(
                artist=guessed_artist,
                title=guessed_title,
                album=evidence.description_album or "",
                source="title_dash_split",
                confidence=0.60,
                write_allowed=False,
                notes=notes,
            )

        if lookup_title and author:
            notes.append("author/title fallback is too weak for auto-write")
            return TagCandidate(
                artist=evidence.canonical_author or author,
                title=lookup_title,
                album=evidence.description_album or "",
                source="author_lookup_fallback",
                confidence=0.45,
                write_allowed=False,
                notes=notes,
            )

        notes.append("insufficient structured evidence")
        return TagCandidate(
            source="unresolved",
            confidence=0.0,
            write_allowed=False,
            notes=notes,
        )

    def _flatten_metadata(self, value: Any, prefix: str = "") -> dict[str, str]:
        flat: dict[str, str] = {}

        if value is None:
            return flat

        if isinstance(value, dict):
            for key, child in value.items():
                child_prefix = f"{prefix}.{key}" if prefix else str(key)
                flat.update(self._flatten_metadata(child, child_prefix))
            return flat

        if isinstance(value, (list, tuple, set)):
            items = [str(item).strip() for item in value if str(item).strip()]
            if prefix and items:
                flat[prefix] = ", ".join(items)
            return flat

        if prefix:
            flat[prefix] = str(value).strip()
        return flat

    @staticmethod
    def _pick_first(flat: dict[str, str], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = (flat.get(key) or "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _normalise_compare_text(text: str) -> str:
        cleaned = unicodedata.normalize("NFKD", text or "")
        cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch)).lower().strip()
        cleaned = cleaned.replace("&", " and ")
        cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in cleaned)
        cleaned = " ".join(cleaned.split())
        return cleaned

    @classmethod
    def _values_match(cls, left: str, right: str) -> bool:
        return bool(left and right) and cls._normalise_compare_text(left) == cls._normalise_compare_text(right)

    @classmethod
    def _artist_mentions_canonical_author(cls, artist: str, canonical_author: str) -> bool:
        artist_key = cls._normalise_compare_text(artist)
        author_key = cls._normalise_compare_text(canonical_author)
        if not artist_key or not author_key:
            return False
        if artist_key == author_key:
            return True
        return f" {author_key} " in f" {artist_key} "

    @classmethod
    def _title_looks_clean(cls, title: str) -> bool:
        cleaned = cls._normalise_compare_text(title)
        if not cleaned:
            return False
        dirty_terms = (
            "official video",
            "official music video",
            "official audio",
            "lyric video",
            "lyrics",
            "visualizer",
            "performance video",
            "official song clip",
            "out now",
            "letra",
        )
        return not any(term in cleaned for term in dirty_terms)
