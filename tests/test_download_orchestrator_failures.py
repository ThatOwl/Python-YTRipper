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
from utility.utils import DownloadOptions


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


if __name__ == "__main__":
    unittest.main()
