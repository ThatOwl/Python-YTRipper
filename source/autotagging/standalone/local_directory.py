import csv
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.candidate_resolver import CandidateResolver, TagCandidate
from ..core.musicbrainz_enricher import MusicBrainzEnricher
from ..core.tag_writer import TagWriter
from ..core.title_normalizer import TitleNormalizer

SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".m4a", ".mp4")
DEFAULT_SCAN_FIELDS = [
    "path",
    "current_artist",
    "current_title",
    "current_album",
    "artist_to_write",
    "title_to_write",
    "album_to_write",
    "suggestion_source",
    "suggestion_confidence",
    "suggestion_reason",
    "apply_mode",
    "write_status",
    "write_details",
    "written_artist",
    "written_title",
]
GENRE_FOLDERS = {
    "filmmusik",
    "serienmusik",
    "spielemusik",
    "musik",
    "music",
    "soundtracks",
    "soundtrack",
    "loose",
    "various",
    "various artists",
    "compilations",
    "downloads",
    "unsorted",
    "misc",
    "other",
}


@dataclass
class FolderContext:
    artist: str = ""
    album: str = ""


class LocalDirectoryTagger:
    """Scan local audio trees, suggest tags in CSV, and apply reviewed CSV rows in place."""

    def __init__(
        self,
        *,
        title_normalizer: TitleNormalizer | None = None,
        candidate_resolver: CandidateResolver | None = None,
        musicbrainz_enricher: MusicBrainzEnricher | None = None,
        tag_writer: TagWriter | None = None,
    ):
        self.title_normalizer = title_normalizer or TitleNormalizer()
        self.candidate_resolver = candidate_resolver or CandidateResolver()
        self.musicbrainz_enricher = musicbrainz_enricher or MusicBrainzEnricher()
        self.tag_writer = tag_writer or TagWriter()

    def scan_directory(
        self,
        directory: Path | str,
        *,
        report_csv: Path | str | None = None,
        include_tagged: bool = False,
        enrich: bool = True,
        scan_scope: str = "missing-any",
    ) -> dict[str, Any]:
        root = Path(directory).expanduser().resolve(strict=False)
        if not root.is_dir():
            raise ValueError(f"Not a directory: {root}")

        report_path = Path(report_csv).expanduser() if report_csv else self._default_report_path(root)
        rows: list[dict[str, str]] = []
        counts = {
            "files_seen": 0,
            "rows_written": 0,
            "already_tagged_skipped": 0,
            "review_rows": 0,
            "write_ready_rows": 0,
            "no_suggestion_rows": 0,
        }

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
                continue
            counts["files_seen"] += 1
            current_tags = self._read_current_tags(path)
            if not self._should_include_in_scan(current_tags, scan_scope=scan_scope, include_tagged=include_tagged):
                counts["already_tagged_skipped"] += 1
                continue

            row = self._build_scan_row(root=root, path=path, current_tags=current_tags, enrich=enrich)
            rows.append(row)
            counts["rows_written"] += 1
            if row["apply_mode"] == "write":
                counts["write_ready_rows"] += 1
            elif row["apply_mode"] == "review":
                counts["review_rows"] += 1
            else:
                counts["no_suggestion_rows"] += 1

        self._write_rows(report_path, rows)
        return {
            "directory": str(root),
            "report_csv": str(report_path),
            **counts,
        }

    def apply_csv(self, csv_path: Path | str) -> dict[str, Any]:
        return self.apply_csv_with_overwrite_mode(csv_path, overwrite_mode="missing")

    def apply_csv_with_overwrite_mode(
        self,
        csv_path: Path | str,
        *,
        overwrite_mode: str = "missing",
    ) -> dict[str, Any]:
        report_path = Path(csv_path).expanduser().resolve(strict=False)
        if not report_path.is_file():
            raise ValueError(f"CSV not found: {report_path}")

        rows = self._read_rows(report_path)
        counts = {
            "rows_seen": len(rows),
            "rows_written": 0,
            "rows_skipped": 0,
            "rows_errored": 0,
        }

        updated_rows: list[dict[str, str]] = []
        for row in rows:
            updated_rows.append(self._apply_row(row, counts, overwrite_mode=overwrite_mode))

        self._write_rows(report_path, updated_rows)
        return {
            "csv_path": str(report_path),
            **counts,
        }

    def _build_scan_row(
        self,
        *,
        root: Path,
        path: Path,
        current_tags: dict[str, str],
        enrich: bool,
    ) -> dict[str, str]:
        folder_context = self._detect_folder_context(root, path)
        filename_stem = path.stem
        source_title_input = current_tags["title"] or filename_stem
        assumed_author = current_tags["artist"] or folder_context.artist
        normalized = self.title_normalizer.normalize(raw_title=source_title_input, author=assumed_author)
        payload = {
            "source": {
                "title": source_title_input,
                "author": assumed_author,
                "metadata": {},
                "description": "",
                "keywords": [],
            },
            "playlist_title": current_tags["album"] or folder_context.album,
            "normalization": {"title_analysis": normalized.to_dict()},
        }

        candidate = self.candidate_resolver.resolve(payload)
        candidate = self._promote_local_candidate(
            candidate=candidate,
            normalized=normalized,
            folder_context=folder_context,
            current_tags=current_tags,
            filename_stem=filename_stem,
        )
        enriched_candidate: TagCandidate | None = None
        if enrich and (candidate.artist or candidate.title) and not candidate.write_allowed:
            enriched_candidate = self.musicbrainz_enricher.enrich(payload, candidate)
            if enriched_candidate is not None:
                candidate = enriched_candidate

        apply_mode = self._default_apply_mode(candidate, current_tags)
        return {
            "path": str(path),
            "current_artist": current_tags["artist"],
            "current_title": current_tags["title"],
            "current_album": current_tags["album"],
            "artist_to_write": candidate.artist,
            "title_to_write": candidate.title,
            "album_to_write": candidate.album or folder_context.album or current_tags["album"],
            "suggestion_source": candidate.source,
            "suggestion_confidence": self._format_confidence(candidate.confidence),
            "suggestion_reason": self._suggestion_reason(candidate, enriched_candidate, current_tags),
            "apply_mode": apply_mode,
            "write_status": "",
            "write_details": "",
            "written_artist": "",
            "written_title": "",
        }

    def _apply_row(self, row: dict[str, str], counts: dict[str, int], *, overwrite_mode: str) -> dict[str, str]:
        updated = {field: row.get(field, "") for field in DEFAULT_SCAN_FIELDS}
        mode = str(updated.get("apply_mode", "") or "").strip().lower()
        if mode not in {"write", "apply", "yes", "true", "force"}:
            counts["rows_skipped"] += 1
            return updated

        target_path = Path(updated.get("path", "")).expanduser()
        if not target_path.is_file():
            updated["write_status"] = "error"
            updated["write_details"] = "source_not_found"
            counts["rows_errored"] += 1
            return updated

        actual_current_tags = self._read_current_tags(target_path)
        candidate = TagCandidate(
            artist=str(updated.get("artist_to_write", "") or "").strip(),
            title=str(updated.get("title_to_write", "") or "").strip(),
            album=str(updated.get("album_to_write", "") or "").strip(),
            source=str(updated.get("suggestion_source", "") or "csv_reviewed"),
            confidence=self._parse_confidence(updated.get("suggestion_confidence", "")),
            write_allowed=True,
        )
        candidate = self._filter_candidate_by_overwrite_mode(candidate, actual_current_tags, overwrite_mode=overwrite_mode)
        if not candidate.artist and not candidate.title and not candidate.album:
            updated["write_status"] = "skipped"
            updated["write_details"] = f"no_fields_selected:{overwrite_mode}"
            counts["rows_skipped"] += 1
            return updated

        result = self.tag_writer.write_candidate(target_path, candidate)
        if result.success:
            updated["write_status"] = "written"
            updated["write_details"] = "|".join(result.wrote_fields) or result.status
            updated["written_artist"] = candidate.artist if "artist" in result.wrote_fields else ""
            updated["written_title"] = candidate.title if "title" in result.wrote_fields else ""
            counts["rows_written"] += 1
            return updated

        updated["write_status"] = "error"
        updated["write_details"] = result.status
        counts["rows_errored"] += 1
        return updated

    @staticmethod
    def _should_include_in_scan(
        current_tags: dict[str, str],
        *,
        scan_scope: str,
        include_tagged: bool,
    ) -> bool:
        if include_tagged:
            return True

        artist_present = bool(str(current_tags.get("artist", "") or "").strip())
        title_present = bool(str(current_tags.get("title", "") or "").strip())

        if scan_scope == "all":
            return True
        if scan_scope == "untagged":
            return not artist_present and not title_present
        if scan_scope == "missing-artist":
            return not artist_present
        if scan_scope == "missing-title":
            return not title_present
        return not (artist_present and title_present)

    @staticmethod
    def _filter_candidate_by_overwrite_mode(
        candidate: TagCandidate,
        current_tags: dict[str, str],
        *,
        overwrite_mode: str,
    ) -> TagCandidate:
        if overwrite_mode == "all":
            return candidate

        filtered = TagCandidate.from_dict(candidate.to_dict())
        if str(current_tags.get("artist", "") or "").strip():
            filtered.artist = ""
        if str(current_tags.get("title", "") or "").strip():
            filtered.title = ""
        if str(current_tags.get("album", "") or "").strip():
            filtered.album = ""
        return filtered

    def _promote_local_candidate(
        self,
        *,
        candidate: TagCandidate,
        normalized: Any,
        folder_context: FolderContext,
        current_tags: dict[str, str],
        filename_stem: str,
    ) -> TagCandidate:
        candidate = self._clean_local_candidate(candidate)

        scan_safe_candidate = self._promote_scan_specific_candidate(
            candidate=candidate,
            normalized=normalized,
            folder_context=folder_context,
            filename_stem=filename_stem,
        )
        if scan_safe_candidate is not None:
            return scan_safe_candidate

        if candidate.artist and candidate.title and candidate.album:
            return candidate

        if not candidate.artist and folder_context.artist and normalized.lookup_title:
            return TagCandidate(
                artist=folder_context.artist,
                title=self.title_normalizer.strip_artist_from_title(normalized.lookup_title, folder_context.artist),
                album=candidate.album or folder_context.album or current_tags["album"],
                source="folder_artist_fallback",
                confidence=0.68,
                write_allowed=False,
                notes=["derived from folder context only"],
            )

        if candidate.artist and candidate.title and not candidate.album and (folder_context.album or current_tags["album"]):
            promoted = TagCandidate.from_dict(candidate.to_dict())
            promoted.album = folder_context.album or current_tags["album"]
            return promoted

        if not candidate.artist and current_tags["artist"] and candidate.title:
            return TagCandidate(
                artist=current_tags["artist"],
                title=candidate.title,
                album=candidate.album or current_tags["album"] or folder_context.album,
                source="existing_artist_fallback",
                confidence=0.72,
                write_allowed=False,
                notes=["title combined with existing artist tag"],
            )

        return candidate

    def _promote_scan_specific_candidate(
        self,
        *,
        candidate: TagCandidate,
        normalized: Any,
        folder_context: FolderContext,
        filename_stem: str,
    ) -> TagCandidate | None:
        if candidate.write_allowed:
            return None
        if not candidate.artist or not candidate.title:
            return None

        if candidate.source == "title_dash_split" and self._is_locally_safe_dash_split(
            candidate=candidate,
            normalized=normalized,
            folder_context=folder_context,
            filename_stem=filename_stem,
        ):
            promoted = TagCandidate.from_dict(candidate.to_dict())
            promoted.source = "local_filename_dash_split"
            promoted.confidence = max(candidate.confidence, 0.88)
            promoted.write_allowed = True
            promoted.notes = [*list(candidate.notes or []), "promoted by local scan filename policy"]
            return promoted

        if candidate.source == "title_by_pattern" and self._is_locally_safe_title_by_pattern(
            candidate=candidate,
            filename_stem=filename_stem,
        ):
            promoted = TagCandidate.from_dict(candidate.to_dict())
            promoted.source = "local_filename_by_pattern"
            promoted.confidence = max(candidate.confidence, 0.86)
            promoted.write_allowed = True
            promoted.notes = [*list(candidate.notes or []), "promoted by local scan by-artist filename policy"]
            return promoted

        return None

    def _is_locally_safe_dash_split(
        self,
        *,
        candidate: TagCandidate,
        normalized: Any,
        folder_context: FolderContext,
        filename_stem: str,
    ) -> bool:
        if " - " not in filename_stem:
            return False
        if not self._is_reasonable_artist(candidate.artist):
            return False
        if not self._is_reasonable_title(candidate.title):
            return False

        split_confidence = str(getattr(normalized, "split_confidence", "") or "")
        if split_confidence not in {"dash_split", "author_matched_left", "author_matched_right"}:
            return False

        cleaned_filename = self.title_normalizer.clean_string(filename_stem)
        if cleaned_filename and self._looks_like_non_track_filename(cleaned_filename):
            return False

        if folder_context.artist and self._same_text(folder_context.artist, candidate.artist):
            return True

        artist_token_count = len(candidate.artist.split())
        title_token_count = len(candidate.title.split())
        if artist_token_count >= 1 and title_token_count >= 1:
            return True
        return False

    def _is_locally_safe_title_by_pattern(
        self,
        *,
        candidate: TagCandidate,
        filename_stem: str,
    ) -> bool:
        if " by " not in filename_stem.lower():
            return False
        if not self._is_reasonable_artist(candidate.artist):
            return False
        if not self._is_reasonable_title(candidate.title):
            return False
        return not self._looks_like_non_track_filename(self.title_normalizer.clean_string(filename_stem))

    def _clean_local_candidate(self, candidate: TagCandidate) -> TagCandidate:
        if not candidate.title:
            return candidate
        cleaned = TagCandidate.from_dict(candidate.to_dict())
        cleaned.title = self._strip_track_prefix(cleaned.title)
        return cleaned

    @staticmethod
    def _strip_track_prefix(title: str) -> str:
        cleaned = str(title or "")
        cleaned = re.sub(r"^\s*(?:0?\d{1,2}|1\d{2})\s*[\.\-_:)\]]+\s*", "", cleaned)
        cleaned = re.sub(r"^\s*(?:0?\d{1,2}|1\d{2})\s+", "", cleaned)
        return cleaned.strip()

    def _is_reasonable_artist(self, value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        if self._looks_like_non_track_filename(text):
            return False
        if self._looks_like_context_label(text):
            return False
        return True

    def _is_reasonable_title(self, value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        if self._looks_like_non_track_filename(text):
            return False
        return True

    def _looks_like_context_label(self, value: str) -> bool:
        return bool(self.candidate_resolver.evidence_extractor.looks_like_context_label(str(value or "").strip()))

    def _looks_like_non_track_filename(self, value: str) -> bool:
        text = str(value or "").strip().lower()
        if not text:
            return True
        banned_fragments = (
            "top songs",
            "music playlist",
            "best playlist",
            "playlist",
            "full album",
            "full ost",
            "soundtrack",
            "charts",
            "shazam",
            "mix",
            "compilation",
        )
        return any(fragment in text for fragment in banned_fragments)

    @staticmethod
    def _same_text(left: str, right: str) -> bool:
        def _norm(value: str) -> str:
            return "".join(ch.lower() for ch in str(value) if ch.isalnum())

        return bool(left and right) and _norm(left) == _norm(right)

    def _detect_folder_context(self, root: Path, path: Path) -> FolderContext:
        parent = path.parent
        immediate = self._parse_folder_name(parent.name)
        if parent == root:
            return immediate

        grandparent = parent.parent
        if grandparent and grandparent != parent and grandparent != root:
            gp_clean = self.title_normalizer.clean_string(grandparent.name).lower()
            if gp_clean in GENRE_FOLDERS and not immediate.album:
                return FolderContext(artist="", album=self._clean_folder_album(parent.name))
            grandparent_info = self._parse_folder_name(grandparent.name)
            if grandparent_info.artist and not immediate.album:
                return FolderContext(
                    artist=grandparent_info.artist,
                    album=self._clean_folder_album(parent.name),
                )
        return immediate

    def _parse_folder_name(self, folder_name: str) -> FolderContext:
        raw = str(folder_name or "").strip()
        if not raw:
            return FolderContext()
        raw = re.sub(r"^\d{4}(?:_\d{2}){0,2}_(.+)$", r"\1", raw).strip()
        raw_norm = self.title_normalizer.clean_string(raw).lower()
        if raw_norm in GENRE_FOLDERS or raw_norm.startswith("best of "):
            return FolderContext(artist="", album=self._clean_folder_album(raw))

        for separator in (" – ", " — "):
            if separator in raw:
                left, right = raw.split(separator, 1)
                return FolderContext(
                    artist=self.title_normalizer.clean_string(left.strip()),
                    album=self._clean_folder_album(right.strip()),
                )

        dash_pos = raw.find(" - ")
        if dash_pos >= 0:
            left = raw[:dash_pos].strip()
            right = raw[dash_pos + 3 :].strip()
            if re.match(r"^(soundtrack|ost)$", right, re.IGNORECASE):
                return FolderContext(artist="", album=self.title_normalizer.clean_string(left))
            if re.match(r"^\d{4}$", right):
                return FolderContext(artist="", album=self.title_normalizer.clean_string(left))
            return FolderContext(
                artist=self.title_normalizer.clean_string(left),
                album=self._clean_folder_album(right),
            )

        return FolderContext(artist=self.title_normalizer.clean_string(raw), album="")

    def _clean_folder_album(self, text: str) -> str:
        cleaned = re.sub(r"^\d{4}(?:_\d{2}){0,2}_", "", text or "")
        cleaned = cleaned.replace("_", " ")
        cleaned = re.sub(r"\(.*?Soundtrack.*?\)", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\(.*?Album.*?\)", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*-?\s*Album\s*Playlist\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+Full\s+Album\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return self.title_normalizer.clean_string(cleaned).strip()

    @staticmethod
    def _read_current_tags(path: Path) -> dict[str, str]:
        try:
            if path.suffix.lower() == ".mp3":
                from mutagen.mp3 import MP3

                audio = MP3(path)
                return {
                    "title": str(audio.get("TIT2", "")).strip(),
                    "artist": str(audio.get("TPE1", "")).strip(),
                    "album": str(audio.get("TALB", "")).strip(),
                }

            from mutagen.mp4 import MP4

            audio = MP4(path)
            tags = audio.tags or {}
            return {
                "title": str((tags.get("\xa9nam") or [""])[0]).strip(),
                "artist": str((tags.get("\xa9ART") or [""])[0]).strip(),
                "album": str((tags.get("\xa9alb") or [""])[0]).strip(),
            }
        except Exception:
            return {"title": "", "artist": "", "album": ""}

    @staticmethod
    def _default_apply_mode(candidate: TagCandidate, current_tags: dict[str, str]) -> str:
        if current_tags["artist"] and current_tags["title"]:
            return "skip"
        if candidate.artist or candidate.title:
            return "write" if candidate.write_allowed else "review"
        return "skip"

    @staticmethod
    def _suggestion_reason(
        candidate: TagCandidate,
        enriched_candidate: TagCandidate | None,
        current_tags: dict[str, str],
    ) -> str:
        if current_tags["artist"] and current_tags["title"]:
            return "existing_tags_present"
        if enriched_candidate is not None:
            if enriched_candidate.write_allowed:
                return f"musicbrainz_confirmed:{enriched_candidate.source}"
            return f"musicbrainz_review:{enriched_candidate.source}"
        if candidate.artist or candidate.title:
            if candidate.write_allowed:
                return f"local_safe:{candidate.source}"
            return f"review_needed:{candidate.source}"
        return "no_suggestion"

    @staticmethod
    def _format_confidence(value: float) -> str:
        if not value:
            return ""
        return f"{value:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _parse_confidence(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _default_report_path(root: Path) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return root / f"{timestamp}_{root.name or 'scan'}_tag_suggestions.csv"

    @staticmethod
    def _read_rows(csv_path: Path) -> list[dict[str, str]]:
        with open(csv_path, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = []
            for row in reader:
                rows.append({field: str(row.get(field, "") or "") for field in DEFAULT_SCAN_FIELDS})
            return rows

    @staticmethod
    def _write_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=DEFAULT_SCAN_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: str(row.get(field, "") or "") for field in DEFAULT_SCAN_FIELDS})
