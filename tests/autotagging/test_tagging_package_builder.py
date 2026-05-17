import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.package_builder import TaggingPackageBuilder, TaggingQueueStore
from utility.utils import DownloadOptions


class _DummyVideo:
    title = "Odd Chap - Swing Theory (Official Audio)"
    author = "Odd Chap"
    description = "A test description"
    thumbnail_url = "https://img.example.test/thumb.jpg"
    watch_url = "https://www.youtube.com/watch?v=abc123xyz89"
    video_id = "abc123xyz89"
    channel_id = "channel-42"
    publish_date = "2026-05-17"
    keywords = ["electro swing", "odd chap"]
    metadata = {"music": {"artist": "Odd Chap", "title": "Swing Theory"}}
    captions = ["en", "de"]
    chapters = [{"title": "Intro", "start_seconds": 0}]


class TestTaggingPackageBuilder(unittest.TestCase):
    def test_build_package_and_write_pending_json(self):
        builder = TaggingPackageBuilder()
        options = DownloadOptions(audio_only=True, prepare_tagging=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            final_output = Path(tmpdir) / "Odd Chap - Swing Theory.m4a"
            final_output.write_text("placeholder", encoding="utf-8")

            package = builder.build_package(
                final_output_path=final_output,
                download_directory=Path(tmpdir),
                video_obj=_DummyVideo(),
                options=options,
                requested_actions=["prepare_tagging"],
                playlist_title="Electro Swing Queue",
            )

            self.assertEqual(package.state, "prepared")
            self.assertEqual(package.container, "m4a")
            self.assertEqual(package.playlist_title, "Electro Swing Queue")
            self.assertEqual(package.source.video_id, "abc123xyz89")
            self.assertTrue(package.source.captions_available)
            self.assertEqual(package.source.caption_track_count, 2)
            self.assertEqual(package.normalization["normalization_version"], "yt-title-v1")

            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime" / "tagging")
            output_path = store.write_pending_package(package)

            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "prepared")
            self.assertEqual(payload["requested_actions"], ["prepare_tagging"])
            self.assertEqual(payload["source"]["author"], "Odd Chap")
            self.assertEqual(payload["download_options"]["audio_only"], True)


if __name__ == "__main__":
    unittest.main()
