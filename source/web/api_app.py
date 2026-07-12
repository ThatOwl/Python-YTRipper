from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from application.download_job_service import DownloadJobService
from application.health_check_service import HealthCheckService
from application.session_config_service import SessionConfigService
from application.session_runtime_service import SessionRuntimeService
from application.url_inspection_service import UrlInspectionService
from utility.logger import get_logger
from web.html_shell import render_index_html

logger = get_logger(__name__, "web_api_app_debug.log")


def create_app(
    *,
    health_service: HealthCheckService | None = None,
    session_runtime_service: SessionRuntimeService | None = None,
    url_inspection_service: UrlInspectionService | None = None,
    download_job_service: DownloadJobService | None = None,
) -> FastAPI:
    config_service = SessionConfigService()
    runtime_service = session_runtime_service or SessionRuntimeService(config_service=config_service)
    inspection_service = url_inspection_service or UrlInspectionService()
    job_service = download_job_service or DownloadJobService(config_service=config_service)
    health = health_service or HealthCheckService()

    app = FastAPI(title="Python-YTRipper Web API", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def get_index() -> str:
        return render_index_html()

    @app.get("/api/health")
    def get_health() -> dict[str, Any]:
        return health.run_startup_checks().to_dict()

    @app.get("/api/session-config")
    def get_session_config() -> dict[str, Any]:
        return runtime_service.get_state().to_dict()

    @app.post("/api/session-config")
    def update_session_config(payload: dict[str, Any]) -> dict[str, Any]:
        updates = dict(payload.get("updates", {}) or {})
        return runtime_service.update_options(updates).to_dict()

    @app.get("/api/presets")
    def list_presets() -> list[dict[str, str]]:
        return config_service.list_available_presets()

    @app.post("/api/presets/load")
    def load_preset(payload: dict[str, Any]) -> dict[str, Any]:
        preset_identifier = str(payload.get("preset_id", "") or "").strip()
        if not preset_identifier:
            raise HTTPException(status_code=400, detail="preset_id is required")
        try:
            return runtime_service.load_preset(preset_identifier).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/presets/save")
    def save_preset(payload: dict[str, Any]) -> dict[str, Any]:
        save_value = str(payload.get("save_config", "") or "").strip()
        if not save_value:
            raise HTTPException(status_code=400, detail="save_config is required")
        try:
            save_path = runtime_service.save_config(save_value)
            return {"saved": bool(save_path), "path": str(save_path or "")}
        except (ValueError, IOError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/url/inspect")
    def inspect_url(payload: dict[str, Any]) -> dict[str, Any]:
        url = str(payload.get("url", "") or "").strip()
        if not url:
            raise HTTPException(status_code=400, detail="url is required")
        remote_check = bool(payload.get("remote_check", False))
        fetch_info = bool(payload.get("fetch_info", False))
        return inspection_service.inspect(
            url,
            remote_check=remote_check,
            fetch_info=fetch_info,
        ).to_dict()

    @app.post("/api/jobs/download")
    def start_download_job(payload: dict[str, Any]) -> dict[str, Any]:
        url = str(payload.get("url", "") or "").strip()
        if not url:
            raise HTTPException(status_code=400, detail="url is required")

        state = runtime_service.get_state()
        summary = job_service.start_url_job(url=url, options=state.options)
        return summary.to_dict()

    @app.get("/api/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        return [summary.to_dict() for summary in job_service.list_jobs()]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        detail = job_service.get_job_detail(job_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="job not found")
        return detail.to_dict()

    return app
