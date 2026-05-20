import sys
import types
import unittest
from pathlib import Path

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
        "AgeRestrictedError",
        "AgeCheckRequiredAccountError",
        "AgeCheckRequiredError",
        "VideoUnavailable",
    ):
        setattr(pytubefix_exceptions_stub, name, type(name, (Exception,), {}))

    sys.modules["pytubefix"] = pytubefix_stub
    sys.modules["pytubefix.exceptions"] = pytubefix_exceptions_stub

import pytubefix.exceptions as ptf_ex

from domain.stream_selector import StreamSelector
from utility.utils import DownloadOptions, StreamSelectionError


class _RestrictedStreams:
    def filter(self, **kwargs):
        raise ptf_ex.AgeCheckRequiredError("restricted")


class _RestrictedVideo:
    streams = _RestrictedStreams()


class _BrokenQuery:
    def order_by(self, *args, **kwargs):
        raise RuntimeError("boom")


class _BrokenStreams:
    def filter(self, **kwargs):
        return _BrokenQuery()


class _BrokenVideo:
    streams = _BrokenStreams()


class TestStreamSelector(unittest.TestCase):
    def test_audio_selection_preserves_age_check_exception(self):
        with self.assertRaises(ptf_ex.AgeCheckRequiredError):
            StreamSelector.select_stream_audio(_RestrictedVideo(), DownloadOptions())

    def test_video_selection_preserves_age_check_exception(self):
        with self.assertRaises(ptf_ex.AgeCheckRequiredError):
            StreamSelector.select_stream_video(_RestrictedVideo(), DownloadOptions())

    def test_audio_selection_still_wraps_non_age_errors(self):
        with self.assertRaises(StreamSelectionError):
            StreamSelector.select_stream_audio(_BrokenVideo(), DownloadOptions())


if __name__ == "__main__":
    unittest.main()
