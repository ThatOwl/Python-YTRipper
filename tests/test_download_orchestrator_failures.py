import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

if "pytubefix" not in sys.modules:
    pytubefix_stub = types.ModuleType("pytubefix")
    pytubefix_stub.YouTube = type("YouTube", (), {})
    pytubefix_stub.Playlist = type("Playlist", (), {})
    pytubefix_stub.Stream = type("Stream", (), {})

    pytubefix_exceptions_stub = types.ModuleType("pytubefix.exceptions")
    for name in (
        "LiveStreamError",
        "RegexMatchError",
        "VideoPrivate",
        "VideoRegionBlocked",
        "AgeCheckRequiredAccountError",
        "AgeCheckRequiredError",
        "VideoUnavailable",
    ):
        setattr(pytubefix_exceptions_stub, name, type(name, (Exception,), {}))

    sys.modules["pytubefix"] = pytubefix_stub
    sys.modules["pytubefix.exceptions"] = pytubefix_exceptions_stub

if "ffmpeg" not in sys.modules:
    ffmpeg_stub = types.ModuleType("ffmpeg")

    def _ffmpeg_unavailable(*args, **kwargs):
        raise AssertionError("ffmpeg should not be used in this regression test")

    ffmpeg_stub.input = _ffmpeg_unavailable
    ffmpeg_stub.output = _ffmpeg_unavailable
    sys.modules["ffmpeg"] = ffmpeg_stub

from application.download_orchestrator import DownloadOrchestrator
from utility.utils import DownloadOptions, DownloadResult


class _ExplodingVideo:
    watch_url = "https://www.youtube.com/watch?v=boom"

    @property
    def title(self):
        raise RuntimeError("This request was detected as a bot")


class TestDownloadOrchestratorFailures(unittest.TestCase):
    def test_invalid_or_inaccessible_url_returns_failed_result(self):
        url_handler = Mock()
        url_handler.is_youtube_url.return_value = True
        url_handler.is_accessible.return_value = False

        orchestrator = DownloadOrchestrator(
            url_handler=url_handler,
            os_handler=Mock(),
        )

        results = orchestrator.download(
            url="https://www.youtube.com/watch?v=broken",
            options=DownloadOptions(default_download_directory="/tmp/ripper-test"),
        )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertEqual(results[0].video_url, "https://www.youtube.com/watch?v=broken")
        self.assertIn("not a valid YouTube URL or inaccessible", results[0].errors[0])

    def test_download_single_returns_failed_result_when_preparation_raises_after_label_fallback(self):
        media_assembler = Mock()
        media_assembler.expected_extension.side_effect = RuntimeError("prepare failed")
        orchestrator = DownloadOrchestrator(
            os_handler=Mock(),
            media_assembler=media_assembler,
        )

        result = orchestrator.download_single(
            options=DownloadOptions(default_download_directory="/tmp/ripper-test"),
            download_dir=Path("/tmp/ripper-test"),
            video_obj=_ExplodingVideo(),
            playlist_title="Exploding Playlist",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.video_url, "https://www.youtube.com/watch?v=boom")
        self.assertEqual(result.playlist_title, "Exploding Playlist")
        self.assertEqual(result.video_title, "https://www.youtube.com/watch?v=boom")
        self.assertIn("prepare failed", result.errors[0])

    def test_download_playlist_preserves_partial_results_when_later_video_label_raises(self):
        good_video = Mock()
        good_video.title = "First Song"
        good_video.watch_url = "https://www.youtube.com/watch?v=one"

        bad_video = _ExplodingVideo()

        playlist = Mock()
        playlist.title = "Mixed Playlist"
        playlist.video_urls = []

        video_fetcher = Mock()
        video_fetcher.get_playlist_obj.return_value = playlist

        os_handler = Mock()
        os_handler.setup_playlist_dir.return_value = Path("/tmp/ripper-test/Mixed Playlist")

        orchestrator = DownloadOrchestrator(
            os_handler=os_handler,
            vid_fetcher=video_fetcher,
        )
        orchestrator.media_info_service.get_playlist_videos = Mock(return_value=[good_video, bad_video])
        orchestrator.download_single = Mock(
            side_effect=[
                DownloadResult(success=True, errors=[], video_title="First Song", video_url=good_video.watch_url),
                DownloadResult(success=False, errors=["This request was detected as a bot"], video_title=bad_video.watch_url, video_url=bad_video.watch_url),
            ]
        )

        results = orchestrator.download_playlist(
            "https://www.youtube.com/playlist?list=PL123",
            Path("/tmp/ripper-test"),
            DownloadOptions(default_download_directory="/tmp/ripper-test"),
        )

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].success)
        self.assertFalse(results[1].success)


if __name__ == "__main__":
    unittest.main()
