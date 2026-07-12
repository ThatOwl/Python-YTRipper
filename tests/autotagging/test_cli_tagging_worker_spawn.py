import sys
import types
import unittest
from unittest.mock import Mock, patch

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
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
    ffmpeg_stub.input = lambda *args, **kwargs: None
    ffmpeg_stub.output = lambda *args, **kwargs: None
    sys.modules["ffmpeg"] = ffmpeg_stub

if "pytube" not in sys.modules:
    pytube_stub = types.ModuleType("pytube")
    pytube_stub.YouTube = type("YouTube", (), {})
    sys.modules["pytube"] = pytube_stub

from cli.cli_command import CommandCLI
from utility.utils import DownloadOptions, DownloadResult


class TestCliTaggingWorkerSpawn(unittest.TestCase):
    @patch("cli.cli_command.subprocess.Popen")
    def test_autotag_spawns_worker_once_per_cli_session(self, mock_popen):
        process = Mock()
        process.poll.return_value = None
        process.pid = 4242
        mock_popen.return_value = process

        cli = CommandCLI()
        cli.ytd.download = Mock(
            return_value=[
                DownloadResult(
                    success=True,
                    errors=[],
                    video_title="Prepared",
                    video_url="https://www.youtube.com/watch?v=prepared",
                )
            ]
        )
        cli.media_info_service.is_playlist = Mock(return_value=False)

        options = DownloadOptions(default_download_directory="/tmp/ripper-test", autotag=True)

        exit_code_first = cli._download_single_url("https://www.youtube.com/watch?v=prepared", options)
        exit_code_second = cli._download_single_url("https://www.youtube.com/watch?v=prepared", options)

        self.assertEqual(exit_code_first, 0)
        self.assertEqual(exit_code_second, 0)
        mock_popen.assert_called_once()

    @patch("cli.cli_command.subprocess.Popen")
    def test_autotag_does_not_spawn_worker_when_download_fails(self, mock_popen):
        cli = CommandCLI()
        cli.ytd.download = Mock(
            return_value=[
                DownloadResult(
                    success=False,
                    errors=["broken"],
                    video_title="Broken",
                    video_url="https://www.youtube.com/watch?v=broken",
                )
            ]
        )
        cli.media_info_service.is_playlist = Mock(return_value=False)

        options = DownloadOptions(default_download_directory="/tmp/ripper-test", autotag=True)

        exit_code = cli._download_single_url("https://www.youtube.com/watch?v=broken", options)

        self.assertEqual(exit_code, 1)
        mock_popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
