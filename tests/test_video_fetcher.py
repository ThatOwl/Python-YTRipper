import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

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

from domain.video_fetcher import VideoFetcher
from utility.utils import VideoFetchError


class _AgeRestrictedVideo:
    def __init__(self, watch_url: str, *, use_oauth: bool = False):
        self.watch_url = watch_url
        self.use_oauth = use_oauth

    @property
    def title(self) -> str:
        if not self.use_oauth:
            raise ptf_ex.AgeCheckRequiredError(self.watch_url)
        return "OAuth Title"


class _AlwaysRestrictedVideo(_AgeRestrictedVideo):
    @property
    def title(self) -> str:
        raise ptf_ex.AgeCheckRequiredError(self.watch_url)


class TestVideoFetcher(unittest.TestCase):
    def test_retry_from_url_uses_oauth_only_after_age_check(self):
        url = "https://www.youtube.com/watch?v=DX0MwoqBcJc"
        constructor_calls: list[tuple[str, dict]] = []

        def _build_video(video_url: str, **kwargs):
            constructor_calls.append((video_url, kwargs))
            return _AgeRestrictedVideo(video_url, use_oauth=kwargs.get("use_oauth", False))

        with patch("domain.video_fetcher.ptf.YouTube", side_effect=_build_video):
            title = VideoFetcher.run_with_age_restricted_oauth_fallback(
                url,
                lambda video: video.title,
            )

        self.assertEqual(title, "OAuth Title")
        self.assertEqual(constructor_calls[0], (url, {}))
        self.assertEqual(constructor_calls[1][0], url)
        self.assertTrue(constructor_calls[1][1]["use_oauth"])
        self.assertTrue(constructor_calls[1][1]["allow_oauth_cache"])
        self.assertTrue(callable(constructor_calls[1][1]["oauth_verifier"]))

    def test_retry_from_existing_video_rebuilds_same_watch_url_with_oauth(self):
        url = "https://www.youtube.com/watch?v=DX0MwoqBcJc"
        constructor_calls: list[tuple[str, dict]] = []

        def _build_video(video_url: str, **kwargs):
            constructor_calls.append((video_url, kwargs))
            return _AgeRestrictedVideo(video_url, use_oauth=kwargs.get("use_oauth", False))

        restricted_video = _AgeRestrictedVideo(url, use_oauth=False)

        with patch("domain.video_fetcher.ptf.YouTube", side_effect=_build_video):
            title = VideoFetcher.run_with_age_restricted_oauth_fallback(
                restricted_video,
                lambda video: video.title,
            )

        self.assertEqual(title, "OAuth Title")
        self.assertEqual(constructor_calls[0][0], url)
        self.assertTrue(constructor_calls[0][1]["use_oauth"])
        self.assertTrue(constructor_calls[0][1]["allow_oauth_cache"])
        self.assertTrue(callable(constructor_calls[0][1]["oauth_verifier"]))

    def test_oauth_retry_raises_video_fetch_error_if_still_age_restricted(self):
        url = "https://www.youtube.com/watch?v=DX0MwoqBcJc"
        constructor_calls: list[tuple[str, dict]] = []

        def _build_video(video_url: str, **kwargs):
            constructor_calls.append((video_url, kwargs))
            return _AlwaysRestrictedVideo(video_url, use_oauth=kwargs.get("use_oauth", False))

        with patch("domain.video_fetcher.ptf.YouTube", side_effect=_build_video):
            with self.assertRaises(VideoFetchError) as cm:
                VideoFetcher.run_with_age_restricted_oauth_fallback(
                    url,
                    lambda video: video.title,
                )

        self.assertIn(url, str(cm.exception))
        self.assertEqual(constructor_calls[0], (url, {}))
        self.assertEqual(constructor_calls[1][0], url)
        self.assertTrue(constructor_calls[1][1]["use_oauth"])
        self.assertTrue(constructor_calls[1][1]["allow_oauth_cache"])
        self.assertTrue(callable(constructor_calls[1][1]["oauth_verifier"]))

    def test_non_interactive_age_restricted_flow_skips_oauth_retry(self):
        url = "https://www.youtube.com/watch?v=DX0MwoqBcJc"
        constructor_calls: list[tuple[str, dict]] = []

        def _build_video(video_url: str, **kwargs):
            constructor_calls.append((video_url, kwargs))
            return _AgeRestrictedVideo(video_url, use_oauth=kwargs.get("use_oauth", False))

        with patch("domain.video_fetcher.ptf.YouTube", side_effect=_build_video):
            with self.assertRaises(VideoFetchError) as cm:
                VideoFetcher.run_with_age_restricted_oauth_fallback(
                    url,
                    lambda video: video.title,
                    allow_interactive_oauth=False,
                )

        self.assertIn("non-interactive", str(cm.exception))
        self.assertEqual(constructor_calls, [(url, {})])


if __name__ == "__main__":
    unittest.main()
