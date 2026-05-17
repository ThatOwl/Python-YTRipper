from dataclasses import asdict, dataclass
from typing import Any


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

    def resolve(self, payload: dict[str, Any]) -> TagCandidate:
        source = payload.get("source", {}) or {}
        normalization = payload.get("normalization", {}) or {}
        title_analysis = normalization.get("title_analysis", {}) or {}
        playlist_title = (payload.get("playlist_title") or "").strip()

        metadata_candidate = self._from_youtube_metadata(source.get("metadata"), playlist_title)
        if metadata_candidate is not None:
            return metadata_candidate

        return self._from_title_analysis(title_analysis, source, playlist_title)

    def _from_youtube_metadata(self, metadata: Any, playlist_title: str) -> TagCandidate | None:
        flat = self._flatten_metadata(metadata)
        artist = self._pick_first(flat, ("artist", "artists", "music.artist", "music.artists"))
        title = self._pick_first(flat, ("title", "song", "track", "music.title", "music.song"))
        album = self._pick_first(flat, ("album", "music.album")) or playlist_title
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

    def _from_title_analysis(
        self,
        title_analysis: dict[str, Any],
        source: dict[str, Any],
        playlist_title: str,
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
                album=playlist_title,
                source="title_author_match",
                confidence=0.90,
                write_allowed=True,
                notes=notes,
            )

        if guessed_artist and guessed_title:
            notes.append("dash split found but author did not confirm it")
            return TagCandidate(
                artist=guessed_artist,
                title=guessed_title,
                album=playlist_title,
                source="title_dash_split",
                confidence=0.60,
                write_allowed=False,
                notes=notes,
            )

        if lookup_title and author:
            notes.append("author/title fallback is too weak for auto-write")
            return TagCandidate(
                artist=author,
                title=lookup_title,
                album=playlist_title,
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
