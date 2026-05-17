import json
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
from autotagging.runtime.package_builder import TaggingPackageBuilder, TaggingQueueStore
from autotagging.runtime.worker import TaggingWorker
from utility.utils import DownloadOptions


class _DummyVideo:
    title = "ELECTRO SWING  Caro Emerald - Tangled Up (Odd Chap Bootleg) [Official Audio]"
    author = "Caro Emerald"
    description = "test"
    thumbnail_url = "https://img.example/thumb.jpg"
    watch_url = "https://www.youtube.com/watch?v=worker123"
    video_id = "worker123"
    channel_id = "channel-7"
    publish_date = "2026-05-17"
    keywords = ["electro swing"]
    metadata = {}
    captions = []
    chapters = []


class TestTaggingWorker(unittest.TestCase):
    def test_worker_writes_tags_for_high_confidence_autotag_package(self):
        builder = TaggingPackageBuilder()
        options = DownloadOptions(autotag=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            final_output = Path(tmpdir) / "Tangled Up.m4a"
            final_output.write_text("audio", encoding="utf-8")

            package = builder.build_package(
                final_output_path=final_output,
                download_directory=Path(tmpdir),
                video_obj=_DummyVideo(),
                options=options,
                requested_actions=["autotag"],
                playlist_title="Electro Swing",
            )

            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime" / "tagging")
            pending_path = store.write_pending_package(package)

            tag_writer = Mock()
            tag_writer.write_candidate.return_value = TagWriteResult(True, "ok", ["artist", "title", "album"])

            worker = TaggingWorker(
                queue_store=store,
                tag_writer=tag_writer,
                poll_interval=0.01,
                idle_timeout=0.05,
            )
            done_path = worker.process_package_file(pending_path)

            self.assertTrue(done_path.exists())
            self.assertIn("/done/", done_path.as_posix())

            payload = json.loads(done_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "written")
            self.assertIn("normalize_title", payload["completed_actions"])
            self.assertIn("resolve_candidates", payload["completed_actions"])
            self.assertIn("write_tags", payload["completed_actions"])
            analysis = payload["normalization"]["title_analysis"]
            self.assertEqual(analysis["guessed_artist"], "Caro Emerald")
            self.assertEqual(analysis["guessed_title"], "Tangled Up Odd Chap Bootleg")
            self.assertEqual(payload["resolved_tags"]["source"], "title_author_match")
            self.assertEqual(payload["write_result"]["status"], "ok")
            tag_writer.write_candidate.assert_called_once()
            events = [
                json.loads(line)
                for line in (Path(tmpdir) / "runtime" / "tagging" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            event_types = [event["event_type"] for event in events]
            self.assertIn("title_normalized", event_types)
            self.assertIn("candidate_resolved", event_types)
            self.assertIn("tag_write_succeeded", event_types)

    def test_worker_skips_auto_write_for_weak_candidate(self):
        builder = TaggingPackageBuilder()
        options = DownloadOptions(autotag=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            final_output = Path(tmpdir) / "Blaze.m4a"
            final_output.write_text("audio", encoding="utf-8")

            weak_video = _DummyVideo()
            weak_video.title = "Odd Chap, Alanna Lyes - Blaze (Electro Swing)"
            weak_video.author = "Some Other Channel"

            package = builder.build_package(
                final_output_path=final_output,
                download_directory=Path(tmpdir),
                video_obj=weak_video,
                options=options,
                requested_actions=["autotag"],
                playlist_title="Electro Swing",
            )

            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime" / "tagging")
            pending_path = store.write_pending_package(package)

            tag_writer = Mock()
            worker = TaggingWorker(
                queue_store=store,
                tag_writer=tag_writer,
                poll_interval=0.01,
                idle_timeout=0.05,
            )
            done_path = worker.process_package_file(pending_path)

            payload = json.loads(done_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "skipped")
            self.assertFalse(payload["resolved_tags"]["write_allowed"])
            self.assertEqual(
                payload["write_result"]["status"],
                "skipped: candidate not safe for auto-write",
            )
            tag_writer.write_candidate.assert_not_called()
            events = [
                json.loads(line)
                for line in (Path(tmpdir) / "runtime" / "tagging" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            event_types = [event["event_type"] for event in events]
            self.assertIn("candidate_enrichment_missed", event_types)
            self.assertIn("tag_write_skipped", event_types)

    def test_worker_promotes_weak_candidate_via_enrichment_then_writes(self):
        builder = TaggingPackageBuilder()
        options = DownloadOptions(autotag=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            final_output = Path(tmpdir) / "Blaze.m4a"
            final_output.write_text("audio", encoding="utf-8")

            weak_video = _DummyVideo()
            weak_video.title = "Odd Chap, Alanna Lyes - Blaze (Electro Swing)"
            weak_video.author = "Some Other Channel"

            package = builder.build_package(
                final_output_path=final_output,
                download_directory=Path(tmpdir),
                video_obj=weak_video,
                options=options,
                requested_actions=["autotag"],
                playlist_title="Electro Swing",
            )

            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime" / "tagging")
            pending_path = store.write_pending_package(package)

            tag_writer = Mock()
            tag_writer.write_candidate.return_value = TagWriteResult(True, "ok", ["artist", "title"])
            enricher = Mock()
            enricher.enrich.return_value = TagCandidate(
                artist="Odd Chap",
                title="Blaze",
                album="Electro Swing",
                source="musicbrainz_confirmed",
                confidence=0.89,
                write_allowed=True,
                notes=["confirmed in test"],
            )

            worker = TaggingWorker(
                queue_store=store,
                musicbrainz_enricher=enricher,
                tag_writer=tag_writer,
                poll_interval=0.01,
                idle_timeout=0.05,
            )
            done_path = worker.process_package_file(pending_path)

            payload = json.loads(done_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "written")
            self.assertEqual(payload["resolved_tags"]["source"], "musicbrainz_confirmed")
            self.assertEqual(payload["enrichment_result"]["status"], "matched")
            self.assertIn("enrich_candidate", payload["completed_actions"])
            tag_writer.write_candidate.assert_called_once()
            written_candidate = tag_writer.write_candidate.call_args.args[1]
            self.assertEqual(written_candidate.artist, "Odd Chap")
            self.assertEqual(written_candidate.title, "Blaze")

    def test_run_until_idle_emits_worker_lifecycle_events(self):
        builder = TaggingPackageBuilder()
        options = DownloadOptions(autotag=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            final_output = Path(tmpdir) / "Tangled Up.m4a"
            final_output.write_text("audio", encoding="utf-8")

            package = builder.build_package(
                final_output_path=final_output,
                download_directory=Path(tmpdir),
                video_obj=_DummyVideo(),
                options=options,
                requested_actions=["autotag"],
                playlist_title="Electro Swing",
            )

            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime" / "tagging")
            store.write_pending_package(package)

            tag_writer = Mock()
            tag_writer.write_candidate.return_value = TagWriteResult(True, "ok", ["artist", "title"])

            worker = TaggingWorker(
                queue_store=store,
                tag_writer=tag_writer,
                poll_interval=0.01,
                idle_timeout=0.02,
            )

            processed_count = worker.run_until_idle()

            self.assertEqual(processed_count, 1)
            events = [
                json.loads(line)
                for line in (Path(tmpdir) / "runtime" / "tagging" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            event_types = [event["event_type"] for event in events]
            self.assertIn("worker_started", event_types)
            self.assertIn("worker_idle_exit", event_types)
            worker_started = next(event for event in events if event["event_type"] == "worker_started")
            worker_idle_exit = next(event for event in events if event["event_type"] == "worker_idle_exit")
            self.assertEqual(worker_started["queue_snapshot"]["counts"]["pending"], 1)
            self.assertEqual(worker_idle_exit["processed_count"], 1)
            self.assertEqual(worker_idle_exit["queue_snapshot"]["counts"]["done"], 1)


if __name__ == "__main__":
    unittest.main()
