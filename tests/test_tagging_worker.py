import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.package_builder import TaggingPackageBuilder, TaggingQueueStore
from autotagging.worker import TaggingWorker
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
    def test_worker_moves_package_to_done_and_adds_title_analysis(self):
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

            worker = TaggingWorker(queue_store=store, poll_interval=0.01, idle_timeout=0.05)
            done_path = worker.process_package_file(pending_path)

            self.assertTrue(done_path.exists())
            self.assertIn("/done/", done_path.as_posix())

            payload = json.loads(done_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "done")
            self.assertIn("normalize_title", payload["completed_actions"])
            analysis = payload["normalization"]["title_analysis"]
            self.assertEqual(analysis["guessed_artist"], "Caro Emerald")
            self.assertEqual(analysis["guessed_title"], "Tangled Up Odd Chap Bootleg")


if __name__ == "__main__":
    unittest.main()
