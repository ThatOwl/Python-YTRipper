import difflib
import time
from typing import Any

from .candidate_resolver import TagCandidate


class MusicBrainzEnricher:
    """Background MusicBrainz confirmation/enrichment for weak candidates."""

    def __init__(
        self,
        min_score: int = 75,
        title_similarity_min: float = 0.75,
        title_only_similarity_min: float = 0.85,
        request_delay: float = 1.1,
    ):
        self.min_score = min_score
        self.title_similarity_min = title_similarity_min
        self.title_only_similarity_min = title_only_similarity_min
        self.request_delay = request_delay

    def enrich(self, payload: dict[str, Any], current_candidate: TagCandidate) -> TagCandidate | None:
        client = self._load_client()
        if client is None:
            return None

        source = payload.get("source", {}) or {}
        title_analysis = (payload.get("normalization", {}) or {}).get("title_analysis", {}) or {}
        playlist_title = (payload.get("playlist_title") or "").strip()

        lookup_title = (title_analysis.get("lookup_title") or current_candidate.title or "").strip()
        guessed_artist = (current_candidate.artist or "").strip()
        author = (source.get("author") or "").strip()

        if not lookup_title:
            return None

        artist_candidates = []
        for value in (guessed_artist, author):
            if value and value not in artist_candidates:
                artist_candidates.append(value)

        for artist in artist_candidates:
            hit = self._query_best(
                client=client,
                title=lookup_title,
                artist=artist,
                album=playlist_title,
                required_similarity=self.title_similarity_min,
            )
            if hit and self._artists_equivalent(hit["artist"], artist):
                return TagCandidate(
                    artist=hit["artist"],
                    title=hit["title"],
                    album=hit["album"] or playlist_title,
                    source="musicbrainz_confirmed",
                    confidence=0.89,
                    write_allowed=True,
                    notes=[f"musicbrainz confirmed candidate via artist '{artist}'"],
                )

        title_only_hit = self._query_best(
            client=client,
            title=lookup_title,
            artist="",
            album=playlist_title,
            required_similarity=self.title_only_similarity_min,
        )
        if title_only_hit:
            return TagCandidate(
                artist=title_only_hit["artist"],
                title=title_only_hit["title"],
                album=title_only_hit["album"] or playlist_title,
                source="musicbrainz_title_only",
                confidence=0.70,
                write_allowed=False,
                notes=["musicbrainz found title-only match; left for manual review"],
            )

        return None

    def _query_best(
        self,
        *,
        client: Any,
        title: str,
        artist: str,
        album: str,
        required_similarity: float,
    ) -> dict[str, Any] | None:
        kwargs = {"recording": title, "limit": 5}
        if artist:
            kwargs["artist"] = artist
        if album and len(album) > 3:
            kwargs["release"] = album

        try:
            if self.request_delay > 0:
                time.sleep(self.request_delay)
            result = client.search_recordings(**kwargs)
        except Exception:
            return None

        recordings = result.get("recording-list", [])
        for rec in recordings:
            mb_score = int(rec.get("ext:score", 0))
            if mb_score < self.min_score:
                break
            mb_title = self._normalise_mb_text(rec.get("title", ""))
            similarity = self._similarity(title, mb_title)
            if similarity < required_similarity:
                continue
            mb_artist = self._normalise_mb_text(rec.get("artist-credit-phrase", ""))
            releases = rec.get("release-list", [])
            mb_album = self._normalise_mb_text(releases[0].get("title", "") if releases else "")
            return {
                "artist": mb_artist,
                "title": mb_title,
                "album": mb_album,
                "mb_score": mb_score,
            }
        return None

    @staticmethod
    def _load_client():
        try:
            import musicbrainzngs
        except ImportError:
            return None

        musicbrainzngs.set_useragent("ytripper-autotag-worker", "1.0", "github.com/ThatOwl")
        return musicbrainzngs

    @staticmethod
    def _normalise_mb_text(text: str) -> str:
        if not text:
            return ""
        text = text.replace("\u2010", "-").replace("\u2013", "-").replace("\u2014", "-")
        return " ".join(text.split()).strip()

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        left_clean = " ".join((left or "").lower().split())
        right_clean = " ".join((right or "").lower().split())
        return difflib.SequenceMatcher(None, left_clean, right_clean).ratio()

    @staticmethod
    def _artists_equivalent(left: str, right: str) -> bool:
        def _norm(value: str) -> str:
            return "".join(ch.lower() for ch in value if ch.isalnum())

        return bool(left and right) and _norm(left) == _norm(right)
