import datetime
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
        "AgeRestrictedError",
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

if "pytube" not in sys.modules:
    pytube_stub = types.ModuleType("pytube")
    pytube_stub.YouTube = type("YouTube", (), {})
    sys.modules["pytube"] = pytube_stub

from cli.cli_command import CommandCLI
from utility.utils import DownloadOptions, DownloadResult


class TestBatchSingleResultSaving(unittest.TestCase):
    def test_autotag_forces_save_results(self):
        cli = CommandCLI()
        options = DownloadOptions(
            default_download_directory="/tmp/ripper-test",
            autotag=True,
            save_results=False,
        )

        cli._normalize_options(options)

        self.assertTrue(options.save_results)

    def test_non_playlist_batch_url_does_not_fetch_playlist_title(self):
        cli = CommandCLI()
        cli.ytd.download = Mock(
            return_value=[
                DownloadResult(
                    success=True,
                    errors=[],
                    video_title="Example Video",
                    video_url="https://www.youtube.com/watch?v=WRfiUywCdZU",
                )
            ]
        )
        cli.media_info_service.is_playlist = Mock(return_value=False)
        cli.media_info_service.get_playlist_title = Mock(side_effect=AssertionError("playlist title should not be fetched"))
        cli.os.save_download_results = Mock()

        options = DownloadOptions(
            default_download_directory="/tmp/ripper-test",
            save_results=True,
        )
        start_time = datetime.datetime(2026, 5, 12, 12, 0, 0)

        exit_code = cli._download_single_url(
            "https://www.youtube.com/watch?v=WRfiUywCdZU",
            options,
            start_time=start_time,
        )

        self.assertEqual(exit_code, 0)
        cli.media_info_service.is_playlist.assert_called_once_with("https://www.youtube.com/watch?v=WRfiUywCdZU")
        cli.media_info_service.get_playlist_title.assert_not_called()
        _, download_kwargs = cli.ytd.download.call_args
        self.assertFalse(download_kwargs["allow_interactive_oauth"])
        cli.os.save_download_results.assert_called_once()
        _, kwargs = cli.os.save_download_results.call_args
        self.assertIsNone(kwargs["playlist_name"])
        self.assertEqual(kwargs["timestamp"], start_time)
        self.assertTrue(kwargs["batch_mode"])
        self.assertIsNotNone(kwargs["report_path"])

    def test_direct_playlist_url_saves_results_without_batch_timestamp(self):
        cli = CommandCLI()
        cli.ytd.download = Mock(
            return_value=[
                DownloadResult(
                    success=True,
                    errors=[],
                    video_title="Playlist Video",
                    video_url="https://www.youtube.com/watch?v=zg2yp9NHYEQ",
                )
            ]
        )
        cli.media_info_service.is_playlist = Mock(return_value=True)
        cli.media_info_service.get_playlist_title = Mock(return_value="Playlist Title")
        cli.os.save_download_results = Mock()

        options = DownloadOptions(
            default_download_directory="/tmp/ripper-test",
            save_results=True,
        )

        exit_code = cli._download_single_url(
            "https://www.youtube.com/watch?v=zg2yp9NHYEQ&list=PLNC-2EHussAB-YMr1L_0AblQc6611RQ0y",
            options,
        )

        self.assertEqual(exit_code, 0)
        cli.media_info_service.is_playlist.assert_called_once()
        cli.media_info_service.get_playlist_title.assert_called_once()
        _, download_kwargs = cli.ytd.download.call_args
        self.assertFalse(download_kwargs["allow_interactive_oauth"])
        cli.os.save_download_results.assert_called_once()
        _, kwargs = cli.os.save_download_results.call_args
        self.assertEqual(kwargs["playlist_name"], "Playlist Title")
        self.assertIsNone(kwargs["timestamp"])
        self.assertFalse(kwargs["batch_mode"])
        self.assertIsNotNone(kwargs["report_path"])

    def test_failed_results_return_nonzero_without_save_results(self):
        cli = CommandCLI()
        cli.ytd.download = Mock(
            return_value=[
                DownloadResult(
                    success=False,
                    errors=["failed"],
                    video_title="Broken Video",
                    video_url="https://www.youtube.com/watch?v=broken",
                )
            ]
        )
        cli.media_info_service.is_playlist = Mock(return_value=False)
        cli.os.save_download_results = Mock()

        options = DownloadOptions(
            default_download_directory="/tmp/ripper-test",
            save_results=False,
        )

        exit_code = cli._download_single_url(
            "https://www.youtube.com/watch?v=broken",
            options,
        )

        self.assertEqual(exit_code, 1)
        cli.os.save_download_results.assert_not_called()


if __name__ == "__main__":
    unittest.main()
