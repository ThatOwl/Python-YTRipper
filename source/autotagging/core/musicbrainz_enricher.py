import difflib
import importlib
import socket
import time
from contextlib import contextmanager
from typing import Any

from autotagging.core.candidate_resolver import TagCandidate
from autotagging.core.evidence_extractor import SourceEvidenceExtractor


class MusicBrainzEnricher:
    """Background MusicBrainz confirmation/enrichment for weak candidates."""

    def __init__(
        self,
        min_score: int = 75,
        title_similarity_min: float = 0.75,
        title_only_similarity_min: float = 0.85,
        request_delay: float = 1.1,
        request_timeout: float = 5.0,
        max_retries: int = 1,
        retry_delay_delta: float = 0.5,
        max_queries: int = 6,
        evidence_extractor: SourceEvidenceExtractor | None = None,
    ):
        self.min_score = min_score
        self.title_similarity_min = title_similarity_min
        self.title_only_similarity_min = title_only_similarity_min
        self.request_delay = request_delay
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_delay_delta = retry_delay_delta
        self.max_queries = max_queries
        self.evidence_extractor = evidence_extractor or SourceEvidenceExtractor()
        self.last_lookup_details: dict[str, Any] = {"status": "idle"}

    def enrich(self, payload: dict[str, Any], current_candidate: TagCandidate) -> TagCandidate | None:
        self.last_lookup_details = {"status": "not_attempted"}
        client = self._load_client()
        if client is None:
            self.last_lookup_details = {"status": "client_unavailable"}
            return None
        self._configure_client_network_limits()

        source = payload.get("source", {}) or {}
        title_analysis = (payload.get("normalization", {}) or {}).get("title_analysis", {}) or {}
        playlist_title = (payload.get("playlist_title") or "").strip()
        lookup_title = (title_analysis.get("lookup_title") or current_candidate.title or "").strip()

        if not lookup_title:
            self.last_lookup_details = {"status": "missing_lookup_title"}
            return None

        evidence = self.evidence_extractor.extract(
            source=source,
            title_analysis=title_analysis,
            guessed_artist=(title_analysis.get("guessed_artist") or current_candidate.artist or "").strip(),
            guessed_title=(title_analysis.get("guessed_title") or current_candidate.title or "").strip(),
            lookup_title=lookup_title,
        )
        release_hint = self._pick_release_hint(playlist_title, evidence.description_album)

        for query in self._build_query_plan(
            source=source,
            title_analysis=title_analysis,
            current_candidate=current_candidate,
            evidence=evidence,
            lookup_title=lookup_title,
        ):
            hit, error = self._query_best(
                client=client,
                title=query["title"],
                artist=query["artist"],
                album=release_hint,
                required_similarity=self.title_similarity_min,
            )
            if error is not None:
                self.last_lookup_details = {
                    **error,
                    "query_title": query["title"],
                    "query_artist": query["artist"],
                    "query_reason": query["reason"],
                }
                return None
            if hit and self._artists_equivalent(hit["artist"], query["artist"]):
                self.last_lookup_details = {
                    "status": "matched",
                    "source": "musicbrainz_confirmed",
                    "query_title": query["title"],
                    "query_artist": query["artist"],
                    "query_reason": query["reason"],
                    "matched_artist": hit["artist"],
                    "matched_title": hit["title"],
                }
                return TagCandidate(
                    artist=hit["artist"],
                    title=hit["title"],
                    album=hit["album"] or release_hint,
                    source="musicbrainz_confirmed",
                    confidence=0.89,
                    write_allowed=not self.evidence_extractor.looks_like_context_label(hit["artist"]),
                    notes=[f"musicbrainz confirmed candidate via {query['reason']}"],
                )

        title_only_hit, error = self._query_best(
            client=client,
            title=lookup_title,
            artist="",
            album=release_hint,
            required_similarity=self.title_only_similarity_min,
        )
        if error is not None:
            self.last_lookup_details = {
                **error,
                "query_title": lookup_title,
                "query_artist": "",
                "query_reason": "title_only_fallback",
            }
            return None
        if title_only_hit:
            self.last_lookup_details = {
                "status": "matched",
                "source": "musicbrainz_title_only",
                "query_title": lookup_title,
                "query_artist": "",
                "query_reason": "title_only_fallback",
                "matched_artist": title_only_hit["artist"],
                "matched_title": title_only_hit["title"],
            }
            return TagCandidate(
                artist=title_only_hit["artist"],
                title=title_only_hit["title"],
                album=title_only_hit["album"] or release_hint,
                source="musicbrainz_title_only",
                confidence=0.70,
                write_allowed=False,
                notes=["musicbrainz found title-only match; left for manual review"],
            )

        self.last_lookup_details = {"status": "no_match"}
        return None

    def _build_query_plan(
        self,
        *,
        source: dict[str, Any],
        title_analysis: dict[str, Any],
        current_candidate: TagCandidate,
        evidence: Any,
        lookup_title: str,
    ) -> list[dict[str, str]]:
        plan: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        def add_query(title: str, artist: str, reason: str) -> None:
            title_value = (title or "").strip()
            artist_value = (artist or "").strip()
            if not title_value or not artist_value:
                return
            if self.evidence_extractor.looks_like_context_label(artist_value):
                return
            key = (self._normalise_mb_text(title_value).lower(), self._normalise_mb_text(artist_value).lower())
            if key in seen:
                return
            seen.add(key)
            plan.append({"title": title_value, "artist": artist_value, "reason": reason})

        guessed_artist = (title_analysis.get("guessed_artist") or current_candidate.artist or "").strip()
        guessed_title = (title_analysis.get("guessed_title") or current_candidate.title or lookup_title).strip()
        canonical_author = (evidence.canonical_author or "").strip()
        source_author = (source.get("author") or "").strip()

        if current_candidate.artist and current_candidate.title:
            add_query(current_candidate.title, current_candidate.artist, "current candidate")
        if guessed_artist and guessed_title:
            add_query(guessed_title, guessed_artist, "normalized title split")

        for hint in getattr(evidence, "title_hints", []):
            add_query(hint.title, hint.artist, hint.source)

        for artist, reason in (
            (canonical_author, "canonical uploader"),
            (source_author, "raw uploader"),
        ):
            add_query(lookup_title, artist, reason)

        return plan[: self.max_queries]

    def _pick_release_hint(self, playlist_title: str, description_album: str) -> str:
        for value in (description_album, playlist_title):
            cleaned = (value or "").strip()
            if not cleaned:
                continue
            if self.evidence_extractor.looks_like_context_label(cleaned):
                continue
            return cleaned
        return ""

    def _query_best(
        self,
        *,
        client: Any,
        title: str,
        artist: str,
        album: str,
        required_similarity: float,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        kwargs = {"recording": title, "limit": 5}
        if artist:
            kwargs["artist"] = artist
        if album and len(album) > 3:
            kwargs["release"] = album

        try:
            if self.request_delay > 0:
                time.sleep(self.request_delay)
            result = client.search_recordings(**kwargs)
        except Exception as exc:
            return None, self._describe_query_error(exc)

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
            }, None
        return None, None

    def _configure_client_network_limits(self) -> None:
        try:
            mb_module = importlib.import_module("musicbrainzngs.musicbrainz")
        except ImportError:
            return

        configured_key = (
            float(self.request_timeout),
            max(1, int(self.max_retries)),
            max(0.0, float(self.retry_delay_delta)),
        )
        original_safe_read = getattr(mb_module, "_ytripper_original_safe_read", None)
        if original_safe_read is None:
            original_safe_read = getattr(mb_module, "_safe_read", None)
            if not callable(original_safe_read):
                return
            setattr(mb_module, "_ytripper_original_safe_read", original_safe_read)

        if getattr(mb_module, "_ytripper_safe_read_config", None) == configured_key:
            return

        def _safe_read_with_limits(opener, req, body=None, _original=original_safe_read):
            with self._temporary_socket_timeout(self.request_timeout):
                return _original(
                    opener,
                    req,
                    body,
                    max_retries=max(1, int(self.max_retries)),
                    retry_delay_delta=max(0.0, float(self.retry_delay_delta)),
                )

        setattr(mb_module, "_safe_read", _safe_read_with_limits)
        setattr(mb_module, "_ytripper_safe_read_config", configured_key)

    @staticmethod
    def _describe_query_error(exc: Exception) -> dict[str, Any]:
        cause = getattr(exc, "cause", None)
        timeout_like = isinstance(exc, (TimeoutError, socket.timeout)) or isinstance(
            cause,
            (TimeoutError, socket.timeout),
        )
        message = str(cause or exc).strip() or exc.__class__.__name__
        return {
            "status": "query_failed",
            "error": "timeout" if timeout_like else exc.__class__.__name__,
            "message": message,
            "timed_out": timeout_like,
        }

    @staticmethod
    @contextmanager
    def _temporary_socket_timeout(timeout_seconds: float):
        if timeout_seconds <= 0:
            yield
            return

        previous_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout_seconds)
        try:
            yield
        finally:
            socket.setdefaulttimeout(previous_timeout)

    @staticmethod
    def _load_client():
        try:
            import musicbrainzngs
        except ImportError:
            return None

        set_useragent = getattr(musicbrainzngs, "set_useragent", None)
        if not callable(set_useragent):
            return None

        try:
            set_useragent("ytripper-autotag-worker", "1.0", "github.com/ThatOwl")
        except Exception:
            return None

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
