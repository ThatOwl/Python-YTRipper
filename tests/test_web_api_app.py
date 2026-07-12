import sys
import inspect
import tempfile
import threading
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

from fastapi import HTTPException

from application.download_job_service import DownloadJobService
from application.job_event_store import JobEventStore
from application.job_store import JobStore
from application.health_check_service import HealthCheckService
from application.session_config_service import SessionConfigService
from application.session_runtime_service import SessionRuntimeService
from application.url_inspection_service import UrlInspectionService
from utility.utils import DownloadOptions, DownloadResult
from web.api_app import create_app


class FakeOSInteractions:
    def __init__(self):
        self.saved: list[tuple[dict, Path | None]] = []

    def read_preferences(self, prefs_path=None):
        return {
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

    def expand_path(self, path_str):
        return Path(str(path_str).replace("~", "/tmp/test-home")).resolve()

    def write_preferences(self, prefs, prefs_path=None):
        self.saved.append((dict(prefs), prefs_path))
        return True


class TestWebApiApp(unittest.TestCase):
    def _build_app(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        os_handler = FakeOSInteractions()
        config_service = SessionConfigService(os_handler=os_handler)
        runtime_service = SessionRuntimeService(config_service=config_service)
        inspection_service = UrlInspectionService(
            url_handler=type(
                "FakeURLHandler",
                (),
                {
                    "is_youtube_url": staticmethod(lambda url: "youtube.com" in url or "youtu.be" in url),
                    "is_youtube_playlist": staticmethod(lambda url: "list=" in url and "start_radio=1" not in url),
                    "clean_video_link": staticmethod(lambda url: "https://www.youtube.com/watch?v=abc123" if "watch?v=abc123" in url else url),
                    "is_accessible": staticmethod(lambda url: True),
                },
            )(),
            media_info_service=type(
                "FakeMediaInfoService",
                (),
                {
                    "get_info_lines": staticmethod(lambda url: [f"info:{url}"]),
                    "get_video_title": staticmethod(lambda url: "Example Video"),
                    "get_playlist_title": staticmethod(lambda url: "Example Playlist"),
                    "get_playlist_video_titles": staticmethod(lambda url: ["A", "B"]),
                },
            )(),
        )

        runner_continue = threading.Event()

        def fake_runner(url, options):
            runner_continue.wait(timeout=0.01)
            return [
                DownloadResult(
                    success=True,
                    errors=[],
                    video_title="Example Video",
                    video_url=url,
                    output_path=Path("/tmp/example.mp4"),
                )
            ]

        job_service = DownloadJobService(
            job_store=JobStore(base_dir=Path(tmpdir.name) / "jobs"),
            event_store=JobEventStore(event_log_path=Path(tmpdir.name) / "events.jsonl"),
            config_service=config_service,
            download_runner=fake_runner,
            session_id="session-api-test",
        )

        health_service = HealthCheckService(
            os_handler=os_handler,
            which_fn=lambda name: "/usr/bin/ffmpeg",
            import_spec_fn=lambda name: object(),
        )

        app = create_app(
            health_service=health_service,
            session_runtime_service=runtime_service,
            url_inspection_service=inspection_service,
            download_job_service=job_service,
        )
        return app, job_service, runner_continue, os_handler

    @staticmethod
    def _get_endpoint(app, path: str, method: str):
        method = method.upper()
        for route in app.routes:
            if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"Endpoint not found for {method} {path}")

    def _call(self, app, path: str, method: str, *args, **kwargs):
        endpoint = self._get_endpoint(app, path, method)
        if inspect.iscoroutinefunction(endpoint):
            raise AssertionError("Unexpected async endpoint in current tests")
        return endpoint(*args, **kwargs)

    def test_health_and_session_config_endpoints(self):
        app, _, _, _ = self._build_app()

        index_response = self._call(app, "/", "GET")
        health_payload = self._call(app, "/api/health", "GET")
        config_payload = self._call(app, "/api/session-config", "GET")

        self.assertIn("Python-YTRipper Web UI", index_response)
        self.assertIn("Health & Status", index_response)
        self.assertIn("Checking backend health...", index_response)
        self.assertIn("Job Detail", index_response)
        self.assertIn("No item results recorded yet.", index_response)
        self.assertNotIn('"<p class="note">', index_response)
        self.assertNotIn('"<div class="status">', index_response)
        self.assertTrue(health_payload["ok"])
        self.assertIn("options", config_payload)

    def test_update_session_and_start_job(self):
        app, job_service, runner_continue, _ = self._build_app()

        update_payload = self._call(
            app,
            "/api/session-config",
            "POST",
            {"updates": {"audio_only": True, "default_download_directory": "~/Music"}},
        )
        self.assertTrue(update_payload["options"]["audio_only"])

        job_payload = self._call(
            app,
            "/api/jobs/download",
            "POST",
            {"url": "https://www.youtube.com/watch?v=abc123"},
        )
        job_id = job_payload["job_id"]

        runner_continue.set()
        self.assertTrue(job_service.wait_for_job(job_id, timeout=2))

        detail_payload = self._call(app, "/api/jobs/{job_id}", "GET", job_id)
        self.assertTrue(detail_payload["summary"]["option_snapshot"]["audio_only"])
        self.assertIn("events", detail_payload)
        self.assertIn("job_completed", [event["event_type"] for event in detail_payload["events"]])

    def test_inspect_and_save_preset_endpoints(self):
        app, _, _, os_handler = self._build_app()

        presets_payload = self._call(app, "/api/presets", "GET")
        inspect_payload = self._call(
            app,
            "/api/url/inspect",
            "POST",
            {
                "url": "https://www.youtube.com/watch?v=abc123",
                "remote_check": True,
                "fetch_info": True,
            },
        )
        self.assertGreaterEqual(len(presets_payload), 5)
        self.assertTrue(inspect_payload["info_fetched"])

        save_payload = self._call(
            app,
            "/api/presets/save",
            "POST",
            {"save_config": "true"},
        )
        self.assertTrue(save_payload["saved"])
        self.assertEqual(len(os_handler.saved), 1)

    def test_missing_url_payload_raises_http_exception(self):
        app, _, _, _ = self._build_app()

        with self.assertRaises(HTTPException) as exc_context:
            self._call(app, "/api/jobs/download", "POST", {})

        self.assertEqual(exc_context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
