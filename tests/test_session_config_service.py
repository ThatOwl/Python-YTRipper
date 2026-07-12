import argparse
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from application.session_config_service import SessionConfigService
from application.state_models import JobDetail, JobEvent, JobItemStatus, JobSummary, SessionConfigState
from utility.utils import DownloadOptions


class FakeOSInteractions:
    def __init__(self):
        self.read_calls: list[Path | None] = []
        self.prefs_by_path: dict[Path | None, dict] = {
            None: {
                "default_download_directory": "~/Downloads/RipperDownloads",
                "audio_only": False,
                "audio_mp3": False,
                "show_preset": False,
                "preferred_audio_quality": "",
                "preferred_video_quality": "",
                "preferred_resolution": "",
                "preferred_abr": "",
                "preferred_format": "",
                "preferred_fps": 0,
                "visible_loglevel": "INFO",
                "donotconvert": False,
                "no_dir_date": False,
                "autotag": False,
                "prepare_tagging": False,
                "save_results": False,
            }
        }

    def read_preferences(self, prefs_path: Path | None = None):
        self.read_calls.append(prefs_path)
        return dict(self.prefs_by_path.get(prefs_path, self.prefs_by_path[None]))

    def expand_path(self, path_str: str | Path) -> Path:
        return Path(str(path_str).replace("~", "/tmp/test-home")).resolve()


class TestSessionConfigService(unittest.TestCase):
    def test_resolve_load_preset_supports_custom_and_immutable_ids(self):
        self.assertTrue(str(SessionConfigService.resolve_load_preset("0")).endswith("0__custom_preset.json"))
        self.assertTrue(str(SessionConfigService.resolve_load_preset("ah")).endswith("ah__audio_high.json"))

    def test_resolve_save_config_path_true_prefers_loaded_custom_preset(self):
        custom_path = SessionConfigService.resolve_load_preset("3")
        resolved = SessionConfigService.resolve_save_config_path(
            "true",
            loaded_preset_path=custom_path,
        )
        self.assertEqual(resolved, custom_path)

    def test_apply_args_normalizes_values_and_forces_autotag_results(self):
        service = SessionConfigService(os_handler=FakeOSInteractions())
        options = DownloadOptions(default_download_directory="~/Downloads", save_results=False)
        args = argparse.Namespace(
            audio_only="true",
            audio_mp3=None,
            preferred_quality="best",
            preferred_resolution="1080p",
            preferred_abr="128k",
            high_fps="true",
            download_directory="~/Music",
            show_preset=None,
            no_dir_date="false",
            visible_loglevel="debug",
            autotag="true",
            prepare_tagging=None,
            save_results="false",
        )

        service.apply_args(args, options, apply_runtime=False)

        self.assertTrue(options.audio_only)
        self.assertEqual(options.preferred_video_quality, "high")
        self.assertEqual(options.preferred_audio_quality, "high")
        self.assertEqual(options.preferred_resolution, "1080p")
        self.assertEqual(options.preferred_abr, "128kbps")
        self.assertEqual(options.preferred_fps, 60)
        self.assertEqual(options.default_download_directory, str(Path("/tmp/test-home/Music").resolve()))
        self.assertEqual(options.visible_loglevel, "DEBUG")
        self.assertTrue(options.autotag)
        self.assertTrue(options.save_results)

    def test_load_preset_returns_state_with_loaded_path(self):
        fake_os = FakeOSInteractions()
        service = SessionConfigService(os_handler=fake_os)
        preset_path = SessionConfigService.resolve_load_preset("2")
        fake_os.prefs_by_path[preset_path] = {
            **fake_os.prefs_by_path[None],
            "audio_only": True,
        }

        state = service.load_preset("2", apply_runtime=False)

        self.assertEqual(state.loaded_preset_path, preset_path)
        self.assertTrue(state.options.audio_only)
        self.assertEqual(fake_os.read_calls[-1], preset_path)

    def test_normalize_audio_bitrate_accepts_already_normalized_value(self):
        service = SessionConfigService(os_handler=FakeOSInteractions())
        options = DownloadOptions(preferred_abr="128kbps")

        service.normalize_audio_bitrate(options)

        self.assertEqual(options.preferred_abr, "128kbps")


class TestStateModels(unittest.TestCase):
    def test_session_config_state_round_trip(self):
        state = SessionConfigState(
            preferences={"audio_only": True},
            options=DownloadOptions(audio_only=True),
            loaded_preset_path=Path("/tmp/preset.json"),
        )

        restored = SessionConfigState.from_dict(state.to_dict())

        self.assertTrue(restored.options.audio_only)
        self.assertEqual(restored.loaded_preset_path, Path("/tmp/preset.json"))

    def test_job_detail_round_trip(self):
        detail = JobDetail(
            summary=JobSummary(job_id="job-1", status="running", items_total=2, option_snapshot={"audio_only": True}),
            items=[JobItemStatus(item_id="1", label="Video A", status="success", success=True)],
            events=[JobEvent(at="2026-07-12T10:00:00Z", event_type="job_started", job_id="job-1", message="started")],
        )

        restored = JobDetail.from_dict(detail.to_dict())

        self.assertEqual(restored.summary.job_id, "job-1")
        self.assertEqual(len(restored.items), 1)
        self.assertEqual(restored.items[0].label, "Video A")
        self.assertEqual(len(restored.events), 1)
        self.assertEqual(restored.events[0].event_type, "job_started")


if __name__ == "__main__":
    unittest.main()
