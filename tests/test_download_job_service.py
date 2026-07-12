import sys
import tempfile
import threading
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from application.download_job_service import DownloadJobService
from application.job_event_store import JobEventStore
from application.job_store import JobStore
from application.session_config_service import SessionConfigService
from utility.utils import DownloadOptions, DownloadResult


class FakeOSInteractions:
    def read_preferences(self, prefs_path=None):
        return {}

    def expand_path(self, path_str):
        return Path(str(path_str).replace("~", "/tmp/test-home")).resolve()


class TestDownloadJobService(unittest.TestCase):
    def test_start_url_job_freezes_option_snapshot_before_runner_executes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner_started = threading.Event()
            runner_continue = threading.Event()
            seen = {}

            def fake_runner(url, options):
                seen["url"] = url
                seen["audio_only"] = options.audio_only
                seen["download_dir"] = options.default_download_directory
                runner_started.set()
                runner_continue.wait(timeout=2)
                return [
                    DownloadResult(
                        success=True,
                        errors=[],
                        video_title="Frozen Snapshot Video",
                        video_url=url,
                        output_path=Path("/tmp/result.mp4"),
                    )
                ]

            service = DownloadJobService(
                job_store=JobStore(base_dir=Path(tmpdir) / "jobs"),
                event_store=JobEventStore(event_log_path=Path(tmpdir) / "events.jsonl"),
                config_service=SessionConfigService(os_handler=FakeOSInteractions()),
                download_runner=fake_runner,
                session_id="session-test",
            )
            options = DownloadOptions(
                audio_only=False,
                default_download_directory="~/Downloads/One",
            )

            summary = service.start_url_job(
                url="https://www.youtube.com/watch?v=abc123",
                options=options,
            )
            self.assertTrue(runner_started.wait(timeout=2))

            options.audio_only = True
            options.default_download_directory = "/tmp/changed-after-start"
            runner_continue.set()
            self.assertTrue(service.wait_for_job(summary.job_id, timeout=2))

            detail = service.get_job_detail(summary.job_id)
            self.assertEqual(seen["url"], "https://www.youtube.com/watch?v=abc123")
            self.assertFalse(seen["audio_only"])
            self.assertEqual(seen["download_dir"], str(Path("/tmp/test-home/Downloads/One").resolve()))
            self.assertIsNotNone(detail)
            self.assertEqual(detail.summary.status, "completed")
            self.assertFalse(detail.summary.option_snapshot["audio_only"])
            self.assertEqual(detail.items[0].label, "Frozen Snapshot Video")

    def test_failed_results_persist_failed_status_and_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            def fake_runner(url, options):
                return [
                    DownloadResult(
                        success=False,
                        errors=["network issue"],
                        video_title="Broken Video",
                        video_url=url,
                    )
                ]

            service = DownloadJobService(
                job_store=JobStore(base_dir=Path(tmpdir) / "jobs"),
                event_store=JobEventStore(event_log_path=Path(tmpdir) / "events.jsonl"),
                config_service=SessionConfigService(os_handler=FakeOSInteractions()),
                download_runner=fake_runner,
                session_id="session-test",
            )

            summary = service.start_url_job(
                url="https://www.youtube.com/watch?v=broken",
                options=DownloadOptions(default_download_directory="~/Downloads"),
            )
            self.assertTrue(service.wait_for_job(summary.job_id, timeout=2))

            detail = service.get_job_detail(summary.job_id)
            events = service.event_store.read_events(job_id=summary.job_id)

            self.assertIsNotNone(detail)
            self.assertEqual(detail.summary.status, "failed")
            self.assertEqual(detail.summary.items_total, 1)
            self.assertEqual(detail.summary.items_failed, 1)
            self.assertEqual(detail.items[0].error, "network issue")
            self.assertIn("job_failed", [event.event_type for event in events])


if __name__ == "__main__":
    unittest.main()
