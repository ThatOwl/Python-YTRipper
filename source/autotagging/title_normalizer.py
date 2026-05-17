import re
from dataclasses import asdict, dataclass, field


JUNK_PATTERNS = [
    r"^\d{4}(?:_\d{2}){0,2}_",
    r"\(Official.*?\)",
    r"\(Full Album.*?\)",
    r"Full Album",
    r"\(.*?Soundtrack.*?\)",
    r"\(.*?Trailer.*?\)",
    r"\(\d+\)$",
    r"\(Remastered.*?\)",
    r"\(Mono.*?\)",
    r"\(Stereo.*?\)",
    r"\(Live.*?\)",
    r"\(HD.*?\)",
    r"\(debut.*?\)",
    r"\(Audio.*?\)",
    r"\(Video.*?\)",
    r"\(.*?Version.*?\)",
    r"\(.*?Remix.*?\)",
    r"\(.*?Music\)",
    r"\[.*?\]",
    r"\blyrics?\b",
    r"\.wmv$",
    r"\bHQ\b",
]

ALLOWED_CHARS = r"[^a-zA-Z0-9äöüÄÖÜß&',\-\. ]"

LEADING_CONTEXT_LABELS = {
    "electro swing",
    "swing hop",
}

SEARCH_TRIM_PATTERNS = [
    r"\s+Official\s+(?:Music\s+)?(?:Video|Audio|Lyric\s+Video|Visualizer).*$",
    r"\s+Video\s+\w.*$",
    r"\s+Video\b.*$",
    r"\s+Remaster(?:ed)?\b.*$",
    r"\s+(?:4K|HD|HQ)\b.*$",
    r"\s+\d{3,4}p\b.*$",
    r"\s+[Dd]ir\.\s+.*$",
    r"\s+ft\.\s+@\S+.*$",
    r"\s+(?:on|from)\s+[Tt]he\s+.+$",
    r"\s+\d{4}\s+(?:VINYL|LP|Album|EP|Stereo|Mono)\b.*$",
    r"\s+[-–]\s+\d{4}\s*$",
    r"\s+Episode\s+\d.*$",
]


@dataclass
class TitleNormalizationResult:
    raw_title: str
    context_stripped_title: str
    cleaned_title: str
    lookup_title: str
    guessed_artist: str = ""
    guessed_title: str = ""
    split_confidence: str = ""
    removed_markers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class TitleNormalizer:
    """Conservative shared normalizer for YouTube-style titles."""

    def normalize(self, raw_title: str, author: str = "") -> TitleNormalizationResult:
        raw = (raw_title or "").strip()
        context_stripped = self._strip_leading_context_label(raw)
        cleaned = self.clean_string(context_stripped)
        lookup = self.clean_lookup_title(cleaned)
        guessed_artist, guessed_title, split_confidence = self._guess_artist_title(cleaned, author)
        removed_markers = self._collect_removed_markers(raw)

        return TitleNormalizationResult(
            raw_title=raw,
            context_stripped_title=context_stripped,
            cleaned_title=cleaned,
            lookup_title=lookup,
            guessed_artist=guessed_artist,
            guessed_title=guessed_title,
            split_confidence=split_confidence,
            removed_markers=removed_markers,
        )

    def clean_string(self, text: str) -> str:
        cleaned = text or ""
        for pattern in JUNK_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("_", " ")
        cleaned = re.sub(ALLOWED_CHARS, "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def clean_lookup_title(self, title: str) -> str:
        cleaned = title or ""
        for pattern in SEARCH_TRIM_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def strip_artist_from_title(self, title: str, artist: str) -> str:
        if not artist or not title:
            return title
        artist_lower = artist.lower().strip()
        title_text = title.strip()
        title_lower = title_text.lower()

        if title_lower.startswith(artist_lower) and len(title_text) > len(artist_lower):
            suffix = title_text[len(artist):]
            stripped = re.sub(r"^[\s\-]+", "", suffix).strip()
            if stripped:
                return stripped

        if title_lower.endswith(artist_lower) and len(title_text) > len(artist_lower):
            prefix = title_text[: len(title_text) - len(artist)]
            stripped = re.sub(r"[\s\-]+$", "", prefix).strip()
            if stripped:
                return stripped

        return title

    def _strip_leading_context_label(self, text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return raw

        for label in sorted(LEADING_CONTEXT_LABELS, key=len, reverse=True):
            patterns = (
                rf"^\[\s*{re.escape(label)}\s*\]\s+",
                rf"^{re.escape(label)}\s{{2,}}",
            )
            for pattern in patterns:
                stripped = re.sub(pattern, "", raw, count=1, flags=re.IGNORECASE)
                if stripped != raw:
                    return stripped.strip()

        return raw

    def _guess_artist_title(self, cleaned_title: str, author: str) -> tuple[str, str, str]:
        if " - " not in cleaned_title:
            return "", "", ""

        left, right = [part.strip() for part in cleaned_title.split(" - ", 1)]
        if not left or not right:
            return "", "", ""

        author_clean = self.clean_string(author)
        author_key = self._normalise_compare_text(author_clean)
        left_key = self._normalise_compare_text(left)
        right_key = self._normalise_compare_text(right)

        if author_key and left_key == author_key:
            return left, self.strip_artist_from_title(right, left), "author_matched_left"

        if author_key and right_key == author_key:
            return right, self.strip_artist_from_title(left, right), "author_matched_right"

        return left, right, "dash_split"

    def _collect_removed_markers(self, raw_title: str) -> list[str]:
        markers: list[str] = []
        for pattern in JUNK_PATTERNS:
            if re.search(pattern, raw_title or "", flags=re.IGNORECASE):
                markers.append(pattern)
        return markers

    @staticmethod
    def _normalise_compare_text(text: str) -> str:
        cleaned = (text or "").lower().strip()
        cleaned = cleaned.replace("&", " and ")
        cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
