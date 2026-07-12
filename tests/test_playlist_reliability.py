import sys
import tempfile
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
from application.media_info_service import MediaInfoService, PLAYLIST_VIDEO_REGEX
from utility.utils import DownloadOptions, DownloadResult


class FakeVideo:
    def __init__(self, title: str, url: str, length: int = 120):
        self.title = title
        self.watch_url = url
        self.length = length


class LazyPlaylist:
    def __init__(self):
        self.title = "Lazy Playlist"
        self.video_urls = [
            "https://www.youtube.com/watch?v=one",
            "https://www.youtube.com/watch?v=two",
        ]
        self._video_regex = None
        self.initial_data = {}

    @property
    def videos(self):
        if self._video_regex == PLAYLIST_VIDEO_REGEX:
            return []
        return []


class TestMediaInfoPlaylistReliability(unittest.TestCase):
    def test_get_playlist_videos_falls_back_to_video_urls_when_playlist_videos_are_empty(self):
        playlist = LazyPlaylist()
        video_fetcher = Mock()
        video_fetcher.get_playlist_obj.return_value = playlist
        video_fetcher.get_video_obj.side_effect = [
            FakeVideo("First", playlist.video_urls[0]),
            FakeVideo("Second", playlist.video_urls[1]),
        ]

        service = MediaInfoService(video_fetcher=video_fetcher)

        videos = service.get_playlist_videos("https://www.youtube.com/playlist?list=PL123")

        self.assertEqual([video.title for video in videos], ["First", "Second"])
        self.assertEqual(playlist._video_regex, PLAYLIST_VIDEO_REGEX)
        self.assertEqual(video_fetcher.get_video_obj.call_count, 2)

    def test_playlist_info_uses_resolved_video_count(self):
        playlist = LazyPlaylist()
        video_fetcher = Mock()
        video_fetcher.get_playlist_obj.return_value = playlist
        video_fetcher.get_video_obj.side_effect = [
            FakeVideo("First", playlist.video_urls[0], length=90),
            FakeVideo("Second", playlist.video_urls[1], length=180),
        ]

        service = MediaInfoService(video_fetcher=video_fetcher)

        lines = service.get_info_lines("https://www.youtube.com/playlist?list=PL123")

        self.assertIn("Playlist Title: Lazy Playlist", lines)
        self.assertIn("Number of Videos: 2", lines)

    def test_get_playlist_videos_falls_back_to_initial_data_when_video_urls_are_empty(self):
        playlist = LazyPlaylist()
        playlist.video_urls = []
        playlist.initial_data = {
            "contents": {
                "twoColumnBrowseResultsRenderer": {
                    "tabs": [
                        {
                            "tabRenderer": {
                                "content": {
                                    "sectionListRenderer": {
                                        "contents": [
                                            {
                                                "itemSectionRenderer": {
                                                    "contents": [
                                                        {
                                                            "playlistVideoListRenderer": {
                                                                "contents": [
                                                                    {"playlistVideoRenderer": {"videoId": "one"}},
                                                                    {"playlistVideoRenderer": {"videoId": "two"}},
                                                                ]
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }
        video_fetcher = Mock()
        video_fetcher.get_playlist_obj.return_value = playlist
        video_fetcher.get_video_obj.side_effect = [
            FakeVideo("First", "https://www.youtube.com/watch?v=one"),
            FakeVideo("Second", "https://www.youtube.com/watch?v=two"),
        ]

        service = MediaInfoService(video_fetcher=video_fetcher)

        videos = service.get_playlist_videos("https://www.youtube.com/playlist?list=PL123")

        self.assertEqual([video.title for video in videos], ["First", "Second"])
        self.assertEqual(
            [call.args[0] for call in video_fetcher.get_video_obj.call_args_list],
            [
                "https://www.youtube.com/watch?v=one",
                "https://www.youtube.com/watch?v=two",
            ],
        )


class TestDownloadPlaylistReliability(unittest.TestCase):
    def test_download_playlist_uses_fallback_resolved_videos(self):
        playlist = LazyPlaylist()
        video_fetcher = Mock()
        video_fetcher.get_playlist_obj.return_value = playlist
        video_fetcher.get_video_obj.side_effect = [
            FakeVideo("First", playlist.video_urls[0]),
            FakeVideo("Second", playlist.video_urls[1]),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            os_handler = Mock()
            os_handler.setup_playlist_dir.return_value = Path(tmpdir) / "Lazy Playlist"

            orchestrator = DownloadOrchestrator(
                os_handler=os_handler,
                vid_fetcher=video_fetcher,
            )
            orchestrator.download_single = Mock(
                side_effect=[
                    DownloadResult(success=True, errors=[], video_title="First", video_url=playlist.video_urls[0]),
                    DownloadResult(success=True, errors=[], video_title="Second", video_url=playlist.video_urls[1]),
                ]
            )

            results = orchestrator.download_playlist(
                "https://www.youtube.com/playlist?list=PL123",
                Path(tmpdir),
                DownloadOptions(default_download_directory=tmpdir),
            )

            self.assertEqual(len(results), 2)
            self.assertEqual(orchestrator.download_single.call_count, 2)

    def test_download_playlist_returns_failed_result_when_no_videos_resolve(self):
        playlist = LazyPlaylist()
        playlist.video_urls = []
        video_fetcher = Mock()
        video_fetcher.get_playlist_obj.return_value = playlist

        with tempfile.TemporaryDirectory() as tmpdir:
            os_handler = Mock()
            os_handler.setup_playlist_dir.return_value = Path(tmpdir) / "Lazy Playlist"

            orchestrator = DownloadOrchestrator(
                os_handler=os_handler,
                vid_fetcher=video_fetcher,
            )

            results = orchestrator.download_playlist(
                "https://www.youtube.com/playlist?list=PL123",
                Path(tmpdir),
                DownloadOptions(default_download_directory=tmpdir),
            )

            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].success)
            self.assertEqual(results[0].playlist_title, "Lazy Playlist")
            self.assertIn("resolved zero videos", results[0].errors[0])


if __name__ == "__main__":
    unittest.main()
