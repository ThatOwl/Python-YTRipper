import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.core.candidate_resolver import TagCandidate
from autotagging.core.tag_writer import TagWriteResult
from autotagging.standalone.local_directory import LocalDirectoryTagger


class TestLocalDirectoryTagger(unittest.TestCase):
    def test_scan_directory_untagged_scope_skips_partially_tagged_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Rammstein"
            root.mkdir(parents=True, exist_ok=True)
            audio_path = root / "Sonne.m4a"
            audio_path.write_text("audio", encoding="utf-8")

            tagger = LocalDirectoryTagger()
            tagger._read_current_tags = lambda _: {"artist": "", "title": "Sonne", "album": ""}  # type: ignore[method-assign]

            summary = tagger.scan_directory(root, enrich=False, scan_scope="untagged")

            self.assertEqual(summary["rows_written"], 0)
            self.assertEqual(summary["already_tagged_skipped"], 1)

    def test_scan_directory_missing_artist_scope_keeps_title_only_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Rammstein"
            root.mkdir(parents=True, exist_ok=True)
            audio_path = root / "Sonne.m4a"
            audio_path.write_text("audio", encoding="utf-8")

            tagger = LocalDirectoryTagger()
            tagger._read_current_tags = lambda _: {"artist": "", "title": "Sonne", "album": ""}  # type: ignore[method-assign]

            summary = tagger.scan_directory(root, enrich=False, scan_scope="missing-artist")

            self.assertEqual(summary["rows_written"], 1)

    def test_scan_directory_promotes_clean_local_dash_split_to_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Best of Rammstein"
            root.mkdir(parents=True, exist_ok=True)
            audio_path = root / "Rammstein - Sonne (Official Video).m4a"
            audio_path.write_text("audio", encoding="utf-8")

            tagger = LocalDirectoryTagger()
            summary = tagger.scan_directory(root, enrich=False)

            report_path = Path(summary["report_csv"])
            with open(report_path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(summary["write_ready_rows"], 1)
            self.assertEqual(rows[0]["artist_to_write"], "Rammstein")
            self.assertEqual(rows[0]["title_to_write"], "Sonne")
            self.assertEqual(rows[0]["suggestion_source"], "local_filename_dash_split")
            self.assertEqual(rows[0]["apply_mode"], "write")

    def test_scan_directory_keeps_playlistish_junk_in_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Besomorph PLAYLIST"
            root.mkdir(parents=True, exist_ok=True)
            audio_path = root / "SHAZAM TOP SONGS 2021 SHAZAM MUSIC PLAYLIST 2021.m4a"
            audio_path.write_text("audio", encoding="utf-8")

            tagger = LocalDirectoryTagger()
            summary = tagger.scan_directory(root, enrich=False)

            report_path = Path(summary["report_csv"])
            with open(report_path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(summary["review_rows"], 1)
            self.assertEqual(rows[0]["apply_mode"], "review")

    def test_scan_directory_writes_csv_with_musicbrainz_backed_suggestion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "Rammstein"
            root.mkdir(parents=True, exist_ok=True)
            audio_path = root / "Sonne.m4a"
            audio_path.write_text("audio", encoding="utf-8")

            enricher = Mock()
            enricher.enrich.return_value = TagCandidate(
                artist="Rammstein",
                title="Sonne",
                album="Mutter",
                source="musicbrainz_confirmed",
                confidence=0.89,
                write_allowed=True,
                notes=["confirmed in test"],
            )

            tagger = LocalDirectoryTagger(musicbrainz_enricher=enricher)
            summary = tagger.scan_directory(root, enrich=True)

            self.assertEqual(summary["files_seen"], 1)
            self.assertEqual(summary["rows_written"], 1)
            self.assertEqual(summary["write_ready_rows"], 1)

            report_path = Path(summary["report_csv"])
            self.assertTrue(report_path.exists())
            with open(report_path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["artist_to_write"], "Rammstein")
            self.assertEqual(rows[0]["title_to_write"], "Sonne")
            self.assertEqual(rows[0]["album_to_write"], "Mutter")
            self.assertEqual(rows[0]["suggestion_source"], "musicbrainz_confirmed")
            self.assertEqual(rows[0]["apply_mode"], "write")

    def test_apply_csv_writes_in_place_and_updates_same_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "Rammstein - Engel.m4a"
            audio_path.write_text("audio", encoding="utf-8")
            csv_path = root / "scan.csv"

            with open(csv_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
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
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "path": str(audio_path),
                        "current_artist": "",
                        "current_title": "",
                        "current_album": "",
                        "artist_to_write": "Rammstein",
                        "title_to_write": "Engel",
                        "album_to_write": "Sehnsucht",
                        "suggestion_source": "csv_reviewed",
                        "suggestion_confidence": "1.0",
                        "suggestion_reason": "reviewed",
                        "apply_mode": "write",
                        "write_status": "",
                        "write_details": "",
                        "written_artist": "",
                        "written_title": "",
                    }
                )

            tag_writer = Mock()
            tag_writer.write_candidate.return_value = TagWriteResult(True, "ok", ["artist", "title", "album"])
            tagger = LocalDirectoryTagger(tag_writer=tag_writer)

            summary = tagger.apply_csv(csv_path)

            self.assertEqual(summary["rows_seen"], 1)
            self.assertEqual(summary["rows_written"], 1)
            tag_writer.write_candidate.assert_called_once()

            with open(csv_path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(rows[0]["write_status"], "written")
            self.assertEqual(rows[0]["written_artist"], "Rammstein")
            self.assertEqual(rows[0]["written_title"], "Engel")

    def test_apply_csv_missing_overwrite_mode_preserves_existing_title(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audio_path = root / "Rammstein - Engel.m4a"
            audio_path.write_text("audio", encoding="utf-8")
            csv_path = root / "scan.csv"

            with open(csv_path, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "path", "current_artist", "current_title", "current_album",
                    "artist_to_write", "title_to_write", "album_to_write",
                    "suggestion_source", "suggestion_confidence", "suggestion_reason",
                    "apply_mode", "write_status", "write_details", "written_artist", "written_title",
                ])
                writer.writeheader()
                writer.writerow({
                    "path": str(audio_path),
                    "current_artist": "",
                    "current_title": "Existing Engel",
                    "current_album": "",
                    "artist_to_write": "Rammstein",
                    "title_to_write": "Engel",
                    "album_to_write": "Sehnsucht",
                    "suggestion_source": "csv_reviewed",
                    "suggestion_confidence": "1.0",
                    "suggestion_reason": "reviewed",
                    "apply_mode": "write",
                    "write_status": "",
                    "write_details": "",
                    "written_artist": "",
                    "written_title": "",
                })

            tag_writer = Mock()
            tag_writer.write_candidate.return_value = TagWriteResult(True, "ok", ["artist", "album"])
            tagger = LocalDirectoryTagger(tag_writer=tag_writer)
            tagger._read_current_tags = lambda _: {"artist": "", "title": "Existing Engel", "album": ""}  # type: ignore[method-assign]

            summary = tagger.apply_csv_with_overwrite_mode(csv_path, overwrite_mode="missing")

            self.assertEqual(summary["rows_written"], 1)
            written_candidate = tag_writer.write_candidate.call_args.args[1]
            self.assertEqual(written_candidate.artist, "Rammstein")
            self.assertEqual(written_candidate.title, "")
            self.assertEqual(written_candidate.album, "Sehnsucht")
