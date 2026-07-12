from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Callable

import utility.preferences as preferences
from application.state_models import HealthCheckItem, HealthCheckReport
from infrastructure.os_interactions import OSInteractions
from utility.logger import get_logger

logger = get_logger(__name__, "health_check_service_debug.log")


class HealthCheckService:
    """Shared startup-style health checks for the future web UI backend."""

    OPTIONAL_DEPENDENCIES = (
        "pytubefix",
        "requests",
        "ffmpeg",
    )

    def __init__(
        self,
        *,
        os_handler: OSInteractions | None = None,
        which_fn: Callable[[str], str | None] | None = None,
        import_spec_fn: Callable[[str], object | None] | None = None,
    ):
        self.os = os_handler or OSInteractions()
        self.which_fn = which_fn or shutil.which
        self.import_spec_fn = import_spec_fn or importlib.util.find_spec

    def run_startup_checks(self) -> HealthCheckReport:
        items = [
            self.check_ffmpeg_binary(),
            self.check_config_directory(),
            self.check_web_runtime_directory(),
            self.check_default_download_directory(),
            self.check_python_dependencies(),
        ]
        return HealthCheckReport(ok=all(item.ok for item in items), items=items)

    def check_ffmpeg_binary(self) -> HealthCheckItem:
        ffmpeg_path = self.which_fn("ffmpeg")
        if ffmpeg_path:
            return HealthCheckItem(
                name="ffmpeg_binary",
                ok=True,
                message="ffmpeg is available on PATH",
                details={"path": ffmpeg_path},
            )
        return HealthCheckItem(
            name="ffmpeg_binary",
            ok=False,
            message="ffmpeg is not available on PATH",
            details={},
        )

    def check_config_directory(self) -> HealthCheckItem:
        return self._check_directory(
            name="config_directory",
            target_path=preferences.CONFIG_DIR,
            create_if_missing=True,
        )

    def check_web_runtime_directory(self) -> HealthCheckItem:
        return self._check_directory(
            name="web_runtime_directory",
            target_path=preferences.WEB_GUI_RUNTIME_DIR,
            create_if_missing=True,
        )

    def check_default_download_directory(self) -> HealthCheckItem:
        prefs = self.os.read_preferences()
        raw_dir = str(
            prefs.get("default_download_directory")
            or preferences.DEFAULT_PREFS["default_download_directory"]
        )
        try:
            expanded = self.os.expand_path(raw_dir)
            expanded.mkdir(parents=True, exist_ok=True)
            return HealthCheckItem(
                name="default_download_directory",
                ok=True,
                message="Default download directory is writable",
                details={"path": str(expanded)},
            )
        except Exception as exc:
            logger.warning("Default download directory check failed for %s: %s", raw_dir, exc)
            return HealthCheckItem(
                name="default_download_directory",
                ok=False,
                message="Default download directory is not writable",
                details={"path": raw_dir, "error": str(exc)},
            )

    def check_python_dependencies(self) -> HealthCheckItem:
        missing = [
            name
            for name in self.OPTIONAL_DEPENDENCIES
            if self.import_spec_fn(name) is None
        ]
        if not missing:
            return HealthCheckItem(
                name="python_dependencies",
                ok=True,
                message="Required Python dependencies are importable",
                details={"checked": list(self.OPTIONAL_DEPENDENCIES)},
            )
        return HealthCheckItem(
            name="python_dependencies",
            ok=False,
            message="Some Python dependencies are missing",
            details={
                "checked": list(self.OPTIONAL_DEPENDENCIES),
                "missing": missing,
            },
        )

    @staticmethod
    def _check_directory(
        *,
        name: str,
        target_path: Path,
        create_if_missing: bool,
    ) -> HealthCheckItem:
        try:
            if create_if_missing:
                target_path.mkdir(parents=True, exist_ok=True)
            exists = target_path.exists()
            writable = exists and target_path.is_dir()
            return HealthCheckItem(
                name=name,
                ok=writable,
                message="Directory is available" if writable else "Directory is unavailable",
                details={"path": str(target_path)},
            )
        except Exception as exc:
            return HealthCheckItem(
                name=name,
                ok=False,
                message="Directory check failed",
                details={"path": str(target_path), "error": str(exc)},
            )
