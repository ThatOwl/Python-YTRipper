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
        "AgeCheckRequiredAccountError",
        "AgeCheckRequiredError",
        "VideoUnavailable",
    ):
        setattr(pytubefix_exceptions_stub, name, type(name, (Exception,), {}))

    sys.modules["pytubefix"] = pytubefix_stub
    sys.modules["pytubefix.exceptions"] = pytubefix_exceptions_stub

from application.state_models import UrlInspectionResult
from application.url_inspection_service import UrlInspectionService


class FakeURLHandler:
    def __init__(self):
        self.checked_accessible_urls: list[str] = []

    def is_youtube_url(self, url: str) -> bool:
        return "youtube.com" in url or "youtu.be" in url

    def is_youtube_playlist(self, url: str) -> bool:
        return "list=" in url and "start_radio=1" not in url

    def clean_video_link(self, url: str) -> str | None:
        if "watch?v=" in url:
            video_id = url.split("watch?v=", 1)[1].split("&", 1)[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        return None

    def is_accessible(self, url: str) -> bool:
        self.checked_accessible_urls.append(url)
        return "blocked" not in url


class FakeMediaInfoService:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def get_info_lines(self, url: str) -> list[str]:
        self.calls.append(("get_info_lines", url))
        return [f"info:{url}"]

    def get_video_title(self, url: str) -> str:
        self.calls.append(("get_video_title", url))
        return "Example Video"

    def get_playlist_title(self, url: str) -> str:
        self.calls.append(("get_playlist_title", url))
        return "Example Playlist"

    def get_playlist_video_titles(self, url: str) -> list[str]:
        self.calls.append(("get_playlist_video_titles", url))
        return ["A", "B", "C"]


class TestUrlInspectionService(unittest.TestCase):
    def test_local_inspection_is_fast_and_does_not_remote_check(self):
        handler = FakeURLHandler()
        media_info = FakeMediaInfoService()
        service = UrlInspectionService(url_handler=handler, media_info_service=media_info)

        result = service.inspect_local("https://www.youtube.com/watch?v=abc123&list=RDabc123&start_radio=1")

        self.assertTrue(result.looks_like_youtube_url)
        self.assertFalse(result.is_playlist)
        self.assertEqual(result.cleaned_url, "https://www.youtube.com/watch?v=abc123")
        self.assertFalse(result.remote_checked)
        self.assertEqual(handler.checked_accessible_urls, [])
        self.assertEqual(media_info.calls, [])

    def test_invalid_local_url_skips_remote_and_info_calls(self):
        handler = FakeURLHandler()
        media_info = FakeMediaInfoService()
        service = UrlInspectionService(url_handler=handler, media_info_service=media_info)

        result = service.inspect("https://example.com/not-youtube", remote_check=True, fetch_info=True)

        self.assertFalse(result.looks_like_youtube_url)
        self.assertFalse(result.remote_checked)
        self.assertEqual(handler.checked_accessible_urls, [])
        self.assertEqual(media_info.calls, [])

    def test_remote_check_can_block_info_fetch(self):
        handler = FakeURLHandler()
        media_info = FakeMediaInfoService()
        service = UrlInspectionService(url_handler=handler, media_info_service=media_info)

        result = service.inspect(
            "https://www.youtube.com/watch?v=blocked",
            remote_check=True,
            fetch_info=True,
        )

        self.assertTrue(result.remote_checked)
        self.assertFalse(result.remotely_accessible)
        self.assertFalse(result.info_fetched)
        self.assertEqual(media_info.calls, [])

    def test_fetch_info_populates_video_metadata(self):
        handler = FakeURLHandler()
        media_info = FakeMediaInfoService()
        service = UrlInspectionService(url_handler=handler, media_info_service=media_info)

        result = service.inspect(
            "https://www.youtube.com/watch?v=abc123&list=RDabc123&start_radio=1",
            remote_check=False,
            fetch_info=True,
        )

        self.assertTrue(result.info_fetched)
        self.assertEqual(result.title, "Example Video")
        self.assertEqual(result.item_count, 1)
        self.assertEqual(result.info_lines, ["info:https://www.youtube.com/watch?v=abc123"])

    def test_fetch_info_populates_playlist_metadata(self):
        handler = FakeURLHandler()
        media_info = FakeMediaInfoService()
        service = UrlInspectionService(url_handler=handler, media_info_service=media_info)

        result = service.inspect(
            "https://www.youtube.com/watch?v=abc123&list=PL123",
            remote_check=False,
            fetch_info=True,
        )

        self.assertTrue(result.is_playlist)
        self.assertTrue(result.info_fetched)
        self.assertEqual(result.title, "Example Playlist")
        self.assertEqual(result.item_count, 3)


class TestUrlInspectionResultModel(unittest.TestCase):
    def test_round_trip(self):
        result = UrlInspectionResult(
            url="https://www.youtube.com/watch?v=abc123",
            normalized_url="https://www.youtube.com/watch?v=abc123",
            cleaned_url="https://www.youtube.com/watch?v=abc123",
            looks_like_youtube_url=True,
            remote_checked=True,
            remotely_accessible=True,
            info_fetched=True,
            title="Example Video",
            item_count=1,
            info_lines=["line1"],
        )

        restored = UrlInspectionResult.from_dict(result.to_dict())

        self.assertTrue(restored.looks_like_youtube_url)
        self.assertTrue(restored.remotely_accessible)
        self.assertEqual(restored.title, "Example Video")


if __name__ == "__main__":
    unittest.main()
