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

if "pytube" not in sys.modules:
    pytube_stub = types.ModuleType("pytube")
    pytube_stub.YouTube = type("YouTube", (), {})
    sys.modules["pytube"] = pytube_stub

from application.download_orchestrator import DownloadOrchestrator
from utility.utils import DownloadOptions


class _DummyVideo:
    title = "Prepared Video"
    watch_url = "https://www.youtube.com/watch?v=prepared123"


class TestDownloadOrchestratorTagging(unittest.TestCase):
    def test_prepare_tagging_emits_package_for_existing_file_skip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_file = Path(tmpdir) / "Prepared Video.m4a"
            existing_file.write_text("audio", encoding="utf-8")

            os_handler = Mock()
            os_handler.find_existing_file_by_stem.return_value = existing_file

            media_assembler = Mock()
            media_assembler.expected_extension.return_value = ".m4a"

            tagging_package = object()
            package_builder = Mock()
            package_builder.build_package.return_value = tagging_package

            queue_store = Mock()
            queue_store.write_pending_package.return_value = Path(tmpdir) / "runtime" / "tagging" / "pending" / "pkg.json"

            orchestrator = DownloadOrchestrator(
                os_handler=os_handler,
                media_assembler=media_assembler,
                tagging_package_builder=package_builder,
                tagging_queue_store=queue_store,
            )

            options = DownloadOptions(default_download_directory=tmpdir, prepare_tagging=True)
            result = orchestrator.download_single(
                options=options,
                download_dir=Path(tmpdir),
                video_obj=_DummyVideo(),
                playlist_title="Prepared Playlist",
            )

            self.assertTrue(result.success)
            self.assertEqual(result.output_path, existing_file)
            package_builder.build_package.assert_called_once()
            _, kwargs = package_builder.build_package.call_args
            self.assertEqual(kwargs["requested_actions"], ["prepare_tagging"])
            self.assertEqual(kwargs["playlist_title"], "Prepared Playlist")
            self.assertEqual(kwargs["final_output_path"], existing_file)
            queue_store.write_pending_package.assert_called_once_with(tagging_package)


if __name__ == "__main__":
    unittest.main()
