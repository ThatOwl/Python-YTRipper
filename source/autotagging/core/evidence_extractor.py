import re
from dataclasses import dataclass, field


@dataclass
class ParsedTitleHint:
    artist: str = ""
    title: str = ""
    source: str = ""
    confidence: float = 0.0
    artist_supported: bool = False
    title_supported: bool = False
    artist_is_contextual: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class SourceEvidence:
    canonical_author: str = ""
    author_is_topic: bool = False
    author_is_official: bool = False
    description_artist: str = ""
    description_title: str = ""
    description_album: str = ""
    guessed_artist_is_contextual: bool = False
    keyword_support_artist: bool = False
    keyword_support_title: bool = False
    title_hints: list[ParsedTitleHint] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class SourceEvidenceExtractor:
    """Extract structured evidence from author, keywords, and description text."""

    def extract(
        self,
        *,
        source: dict,
        title_analysis: dict,
        guessed_artist: str = "",
        guessed_title: str = "",
        lookup_title: str = "",
    ) -> SourceEvidence:
        author = str(source.get("author", "") or "").strip()
        source_title = str(source.get("title", "") or "").strip()
        description = str(source.get("description", "") or "")
        keywords = list(source.get("keywords", []) or [])
        cleaned_title = str(title_analysis.get("cleaned_title", "") or "").strip()

        evidence = SourceEvidence(
            canonical_author=self._canonicalize_author(author),
            author_is_topic=author.lower().endswith(" - topic"),
            author_is_official=self._looks_official_uploader(author),
            guessed_artist_is_contextual=self.looks_like_context_label(guessed_artist),
        )

        description_match = (
            self._extract_topic_description_release(description)
            or self._extract_official_release_description(description)
            or self._extract_single_album_description(description)
            or self._extract_song_by_artist_description(description)
        )
        if description_match is not None:
            evidence.description_artist = description_match.get("artist", "")
            evidence.description_title = description_match.get("title", "")
            evidence.description_album = description_match.get("album", "")
            evidence.notes.append(description_match.get("note", "description_evidence"))

        artist_for_keywords = guessed_artist or evidence.description_artist or evidence.canonical_author
        title_for_keywords = guessed_title or evidence.description_title or lookup_title
        evidence.keyword_support_artist = self._keywords_support_artist_value(
            keywords,
            artist_for_keywords,
            evidence.canonical_author,
        )
        evidence.keyword_support_title = self._keywords_support_value(keywords, title_for_keywords)
        evidence.title_hints = self._extract_title_hints(
            source_title=source_title,
            cleaned_title=cleaned_title,
            keywords=keywords,
            canonical_author=evidence.canonical_author,
        )
        return evidence

    def looks_like_context_label(self, value: str) -> bool:
        return self._looks_like_context_label(value)

    @staticmethod
    def _canonicalize_author(author: str) -> str:
        value = (author or "").strip()
        value = re.sub(r"\s*-\s*topic\s*$", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+official\s*$", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+vevo\s*$", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+", " ", value).strip(" -:")
        return value

    @staticmethod
    def _looks_official_uploader(author: str) -> bool:
        value = (author or "").strip().lower()
        return value.endswith(" official") or value.endswith("vevo")

    def _extract_official_release_description(self, description: str) -> dict[str, str] | None:
        text = description or ""
        patterns = (
            re.compile(
                r"official\s+(?:audio|music\s+video|video)\s+for\s+(?P<artist>.+?)\s*[-:]\s*[\"“](?P<title>.+?)[\"”]"
                r"(?:\s+from\s+the\s+album\s+[\"'“](?P<album>.+?)[\"'”])?",
                re.IGNORECASE | re.DOTALL,
            ),
            re.compile(
                r"(?P<artist>.+?)'s\s+official\s+(?:audio|music\s+video|video)\s+for\s+[\"“](?P<title>.+?)[\"”]"
                r"(?:,?\s+from\s+the\s+album\s+[\"'“](?P<album>.+?)[\"'”])?",
                re.IGNORECASE | re.DOTALL,
            ),
        )
        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue
            return {
                "artist": self._clean_text(match.group("artist")),
                "title": self._clean_text(match.group("title")),
                "album": self._clean_text(match.groupdict().get("album", "")),
                "note": "description_official_release",
            }
        return None

    def _extract_single_album_description(self, description: str) -> dict[str, str] | None:
        text = description or ""
        single_match = re.search(r"^\s*Single:\s*(?P<title>.+?)\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
        album_match = re.search(r"^\s*From the album:\s*(?P<album>.+?)\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
        if not single_match:
            return None
        return {
            "artist": "",
            "title": self._clean_text(single_match.group("title")),
            "album": self._clean_text(album_match.group("album")) if album_match else "",
            "note": "description_single_album",
        }

    def _extract_song_by_artist_description(self, description: str) -> dict[str, str] | None:
        text = description or ""
        patterns = (
            re.compile(
                r"song:\s*[\"“]?(?P<title>.+?)[\"”]?\s+by\s+(?P<artist>.+?)(?:[.\n]|$)",
                re.IGNORECASE,
            ),
            re.compile(
                r"^\s*(?P<title>.+?)\s+by\s+(?P<artist>.+?)\s*$",
                re.IGNORECASE | re.MULTILINE,
            ),
        )
        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue
            title = self._strip_context_tail(self._clean_text(match.group("title")))
            artist = self._strip_context_tail(self._clean_text(match.group("artist")))
            if not title or not artist or self._looks_like_context_label(artist):
                continue
            return {
                "artist": artist,
                "title": title,
                "album": "",
                "note": "description_song_by_artist",
            }
        return None

    def _extract_topic_description_release(self, description: str) -> dict[str, str] | None:
        lines = [line.strip() for line in (description or "").splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if "provided to youtube by" not in line.lower():
                continue
            for candidate_idx in range(idx + 1, min(idx + 5, len(lines))):
                match = re.match(r"^(?P<title>.+?)\s+·\s+(?P<artist>.+?)$", lines[candidate_idx])
                if not match:
                    continue
                album = ""
                if candidate_idx + 1 < len(lines):
                    next_line = lines[candidate_idx + 1]
                    if not self._looks_non_album_line(next_line):
                        album = self._clean_text(next_line)
                return {
                    "artist": self._clean_text(match.group("artist")),
                    "title": self._clean_text(match.group("title")),
                    "album": album,
                    "note": "description_topic_release",
                }
        return None

    @staticmethod
    def _looks_non_album_line(line: str) -> bool:
        lower = (line or "").strip().lower()
        return (
            not lower
            or lower.startswith("℗")
            or lower.startswith("released on:")
            or lower.startswith("producer:")
            or lower.startswith("engineer:")
            or lower.startswith("composer")
            or lower.startswith("auto-generated")
        )

    def _extract_title_hints(
        self,
        *,
        source_title: str,
        cleaned_title: str,
        keywords: list[str],
        canonical_author: str,
    ) -> list[ParsedTitleHint]:
        raw_title = (source_title or "").strip()
        fallback_title = (cleaned_title or "").strip()
        hints: list[ParsedTitleHint] = []
        seen: set[tuple[str, str, str]] = set()

        def add_hint(artist: str, title: str, source: str, confidence: float, notes: list[str] | None = None) -> None:
            artist_value = self._strip_context_tail(self._clean_text(artist))
            title_value = self._strip_context_tail(self._clean_text(title))
            if not artist_value or not title_value:
                return
            key = (
                self._normalise_compare_text(artist_value),
                self._normalise_compare_text(title_value),
                source,
            )
            if key in seen:
                return
            seen.add(key)
            hints.append(
                ParsedTitleHint(
                    artist=artist_value,
                    title=title_value,
                    source=source,
                    confidence=confidence,
                    artist_supported=self._keywords_support_artist_value(keywords, artist_value, canonical_author),
                    title_supported=self._keywords_support_value(keywords, title_value),
                    artist_is_contextual=self._looks_like_context_label(artist_value),
                    notes=list(notes or []),
                )
            )

        by_pattern = re.search(r"^(?P<title>.+?)\s+by\s+(?P<artist>.+?)(?:\s+-\s+.+)?$", raw_title, flags=re.IGNORECASE)
        if by_pattern:
            add_hint(
                by_pattern.group("artist"),
                by_pattern.group("title"),
                "title_by_pattern",
                0.83,
                ["parsed 'title by artist' pattern from source title"],
            )

        context_paren = re.search(
            r"^(?P<context>.+?)\s+-\s+(?P<title>.+?)\s+\((?P<artist>[^()]+)\)\s*$",
            raw_title,
            flags=re.IGNORECASE,
        )
        if context_paren and self._looks_like_context_label(context_paren.group("context")):
            if not self._looks_like_context_label(context_paren.group("artist")):
                add_hint(
                    context_paren.group("artist"),
                    context_paren.group("title"),
                    "context_parenthetical_artist",
                    0.86,
                    ["parsed contextual title with parenthetical artist"],
                )

        dash_parts = [part.strip() for part in re.split(r"\s+-\s+", raw_title) if part.strip()]
        if len(dash_parts) >= 3 and self._looks_like_context_label(dash_parts[0]):
            middle = dash_parts[1]
            tail = " - ".join(dash_parts[2:])
            add_hint(
                middle,
                tail,
                "context_dash_artist_title",
                0.79,
                ["parsed contextual multi-dash title as artist - title"],
            )
            add_hint(
                dash_parts[-1],
                " - ".join(dash_parts[1:-1]),
                "context_dash_title_artist",
                0.84,
                ["parsed contextual multi-dash title as title - artist"],
            )

        dash_match = re.match(r"^(?P<left>.+?)\s+-\s+(?P<right>.+)$", fallback_title)
        if dash_match:
            left = dash_match.group("left")
            right = dash_match.group("right")
            if self._looks_like_artist_name(right) and self._keywords_support_artist_value(keywords, right, canonical_author):
                add_hint(
                    right,
                    left,
                    "reverse_dash_artist_hint",
                    0.75,
                    ["right side looks like artist name; kept as review/query hint"],
                )

        hints.sort(
            key=lambda hint: (
                hint.artist_is_contextual,
                not hint.artist_supported,
                not hint.title_supported,
                -hint.confidence,
            )
        )
        return hints

    def _keywords_support_value(self, keywords: list[str], value: str) -> bool:
        target = self._normalise_compare_text(value)
        if not target:
            return False
        for keyword in keywords:
            keyword_norm = self._normalise_compare_text(str(keyword))
            if not keyword_norm:
                continue
            if keyword_norm == target:
                return True
            if keyword_norm.startswith(f"{target} "):
                return True
            if f" {target} " in f" {keyword_norm} ":
                return True
        return False

    def _keywords_support_artist_value(self, keywords: list[str], value: str, canonical_author: str) -> bool:
        if self._keywords_support_value(keywords, value):
            return True

        target = self._normalise_compare_text(value)
        canonical = self._normalise_compare_text(canonical_author)
        if not target:
            return False

        parts = [
            self._normalise_compare_text(part)
            for part in re.split(r"\s*(?:,|&| and | x | ft\. | feat\. | with )\s*", value, flags=re.IGNORECASE)
            if self._normalise_compare_text(part)
        ]
        if len(parts) <= 1:
            return self._keywords_cover_tokens(keywords, target)

        for part in parts:
            if canonical and part == canonical:
                continue
            if not (
                any(self._keyword_matches_normalized_value(str(keyword), part) for keyword in keywords)
                or self._keywords_cover_tokens(keywords, part)
            ):
                return False
        return True

    def _keyword_matches_normalized_value(self, keyword: str, target: str) -> bool:
        keyword_norm = self._normalise_compare_text(str(keyword))
        if not keyword_norm or not target:
            return False
        if keyword_norm == target:
            return True
        if keyword_norm.startswith(f"{target} "):
            return True
        return f" {target} " in f" {keyword_norm} "

    def _keywords_cover_tokens(self, keywords: list[str], value: str) -> bool:
        tokens = [token for token in self._normalise_compare_text(value).split() if token]
        if not tokens:
            return False
        keyword_tokens = {
            token
            for keyword in keywords
            for token in self._normalise_compare_text(str(keyword)).split()
            if token
        }
        return all(token in keyword_tokens for token in tokens)

    @staticmethod
    def _clean_text(value: str) -> str:
        cleaned = (value or "").replace("\u201c", '"').replace("\u201d", '"').strip()
        cleaned = cleaned.strip("\"' ")
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"[.,;:]+$", "", cleaned)
        return cleaned

    @staticmethod
    def _normalise_compare_text(text: str) -> str:
        cleaned = (text or "").lower().strip()
        cleaned = cleaned.replace("&", " and ")
        cleaned = re.sub(r"[^a-z0-9äöüß\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def _looks_like_context_label(cls, value: str) -> bool:
        normalized = cls._normalise_compare_text(value)
        if not normalized:
            return False
        context_phrases = (
            "soundtrack",
            "playlist",
            "original trailer",
            "trailer",
            "season ",
            "episode ",
            "with lyrics",
            " lyrics",
            "official soundtrack",
            "ost",
            "radio new vegas",
            "black mountain radio",
            "appalachia radio",
        )
        if any(phrase in normalized for phrase in context_phrases):
            return True
        if normalized.startswith("fallout ") or " fallout " in f" {normalized} ":
            return True
        if normalized.startswith("radio ") and len(normalized.split()) >= 2:
            return True
        return False

    @classmethod
    def _looks_like_artist_name(cls, value: str) -> bool:
        normalized = cls._normalise_compare_text(value)
        if not normalized or cls._looks_like_context_label(value):
            return False
        parts = normalized.split()
        if len(parts) == 0 or len(parts) > 5:
            return False
        if any(any(ch.isdigit() for ch in part) for part in parts):
            return False
        disallowed = {"official", "video", "audio", "lyrics", "soundtrack", "playlist"}
        if any(part in disallowed for part in parts):
            return False
        return True

    @classmethod
    def _strip_context_tail(cls, value: str) -> str:
        cleaned = value or ""
        patterns = (
            r"\bfallout\b.*$",
            r"\b(?:official\s+)?(?:soundtrack|trailer|ost|lyrics?|release)\b.*$",
            r"\bseason\s+\d+\b.*$",
            r"\bepisode\s+\d+\b.*$",
            r"\bappalachia\b.*$",
            r"\bwith\s+lyrics\b.*$",
        )
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip(" -|:")
        return cleaned.strip()
