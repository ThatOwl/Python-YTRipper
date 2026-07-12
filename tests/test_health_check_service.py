import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

import utility.preferences as preferences
from application.health_check_service import HealthCheckService
from application.state_models import HealthCheckReport


class FakeOSInteractions:
    def __init__(self, default_download_directory: str = "~/Downloads/RipperDownloads", fail_expand: bool = False):
        self.default_download_directory = default_download_directory
        self.fail_expand = fail_expand

    def read_preferences(self, prefs_path=None):
        return {"default_download_directory": self.default_download_directory}

    def expand_path(self, path_str):
        if self.fail_expand:
            raise ValueError("cannot expand path")
        return Path(str(path_str).replace("~", "/tmp/test-home")).resolve()


class TestHealthCheckService(unittest.TestCase):
    def test_startup_report_collects_items_and_overall_status(self):
        service = HealthCheckService(
            os_handler=FakeOSInteractions(),
            which_fn=lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None,
            import_spec_fn=lambda name: object(),
        )

        report = service.run_startup_checks()

        self.assertTrue(report.ok)
        self.assertEqual(len(report.items), 5)
        self.assertTrue(all(item.ok for item in report.items))

    def test_missing_binary_and_dependency_make_report_fail(self):
        service = HealthCheckService(
            os_handler=FakeOSInteractions(fail_expand=True),
            which_fn=lambda name: None,
            import_spec_fn=lambda name: None,
        )

        report = service.run_startup_checks()
        items_by_name = {item.name: item for item in report.items}

        self.assertFalse(report.ok)
        self.assertFalse(items_by_name["ffmpeg_binary"].ok)
        self.assertFalse(items_by_name["python_dependencies"].ok)
        self.assertFalse(items_by_name["default_download_directory"].ok)

    def test_directory_checks_create_missing_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            runtime_dir = Path(tmpdir) / "runtime" / "web-gui"

            original_config_dir = preferences.CONFIG_DIR
            original_runtime_dir = preferences.WEB_GUI_RUNTIME_DIR
            try:
                preferences.CONFIG_DIR = config_dir
                preferences.WEB_GUI_RUNTIME_DIR = runtime_dir

                service = HealthCheckService(
                    os_handler=FakeOSInteractions(),
                    which_fn=lambda name: "/usr/bin/ffmpeg",
                    import_spec_fn=lambda name: object(),
                )

                config_item = service.check_config_directory()
                runtime_item = service.check_web_runtime_directory()

                self.assertTrue(config_item.ok)
                self.assertTrue(runtime_item.ok)
                self.assertTrue(config_dir.exists())
                self.assertTrue(runtime_dir.exists())
            finally:
                preferences.CONFIG_DIR = original_config_dir
                preferences.WEB_GUI_RUNTIME_DIR = original_runtime_dir


class TestHealthReportModel(unittest.TestCase):
    def test_round_trip(self):
        report = HealthCheckReport.from_dict(
            {
                "ok": True,
                "items": [
                    {
                        "name": "ffmpeg_binary",
                        "ok": True,
                        "message": "ok",
                        "details": {"path": "/usr/bin/ffmpeg"},
                    }
                ],
            }
        )

        restored = HealthCheckReport.from_dict(report.to_dict())

        self.assertTrue(restored.ok)
        self.assertEqual(restored.items[0].name, "ffmpeg_binary")


if __name__ == "__main__":
    unittest.main()
