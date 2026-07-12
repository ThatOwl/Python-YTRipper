# Python-YTRipper Web UI

This document covers the web GUI/backend work separately from the CLI README.

It is intentionally maintained at larger implementation milestones, not after every tiny internal change.
That keeps the documentation useful without turning it into commit-by-commit noise.

## Current Status

The web UI is in `V2 iteration 1` after the V1 inspection milestone.

That means:

- the backend exists
- a more intentional shell redesign is underway on top of the V1 backend
- session config, URL inspection, health checks, and job start/status flows are wired
- the UI is usable for early local testing
- inline URL validation exists
- job detail visibility is good enough for V1 inspection
- shared playlist handling was live-validated through the CLI on July 12, 2026

It does **not** mean:

- polished frontend
- complete feature parity with the CLI
- final architecture
- multi-user support

The current direction is intentionally conservative.
The backend/services proved themselves in V1, and the current work is focused on making the frontend layout and controls feel like a real operator UI.

## V2 Focus

The first post-V1 iteration is focused on:

- replacing the proof-of-concept shell layout with a stronger operator layout
- expanding session controls to cover more CLI options with sensible labels
- improving readability before adding heavier local-only integrations

This is intentionally not a ground-up rewrite of the backend.
It is a frontend-first iteration on top of the V1 service layer.

## V1 Validation Notes

As of July 12, 2026, the shared backend/services used by the web UI were validated through the CLI against live playlist URLs.

That validation confirmed:

- single-video and playlist top-level jobs are both part of the intended V1 scope
- the earlier zero-item playlist regression was fixed in the shared service layer
- playlist jobs now produce item-level results instead of collapsing into an empty job

This does not mean every YouTube-side edge case is solved.
It does mean the web UI is now sitting on a materially more trustworthy V1 backend than it was at the original checkpoint.

## Design Intent

The web UI is built around the same principles documented during the implementation work:

- single-user app
- local-first usage
- coarse but honest job progress
- shared service layer instead of GUI code calling the CLI
- persistent filesystem-backed job and event state

The UI is not supposed to parse terminal output.
It is supposed to consume structured application services and stored job state.

## V1 Inspection Checklist

Use this when reviewing the V1 checkpoint locally.

1. Start the UI with `./start_web_ui.sh` or `.\start_web_ui.ps1`.
2. Open `http://127.0.0.1:8000`.
3. Confirm the `Health & Status` panel loads and shows whether the backend is ready.
4. Confirm session settings load into the form without manual refresh.
5. Inspect a known single-video URL and verify title/info appears.
6. Start a single-video job and confirm it appears in the job list.
7. Click the job and confirm summary, items, and events appear in `Job Detail`.
8. Test a playlist URL and confirm the job is recognized as a playlist and produces item-level results instead of an empty job.

If these checks pass, the V1 slice is doing its current job even if the interface still feels intentionally basic.

## What V1 Now Includes

At this checkpoint, the web UI covers the core local operator loop:

- launch the backend with the provided scripts
- see backend dependency/runtime health on the page
- load and adjust session settings
- validate a URL before acting on it
- inspect a URL for richer metadata
- start background jobs
- run either a single-video job or a playlist job from one pasted URL
- review top-level job status and per-job item/event detail

That is enough for a meaningful V1 review, even though it is not yet the final UX direction.

## Current V1 Components

### Shared Services

- `source/application/session_config_service.py`
- `source/application/session_runtime_service.py`
- `source/application/url_inspection_service.py`
- `source/application/download_job_service.py`
- `source/application/health_check_service.py`
- `source/application/job_store.py`
- `source/application/job_event_store.py`

### Web Backend

- `source/web/api_app.py`
- `source/web/main.py`
- `source/web/html_shell.py`

### Current API Surface

- `GET /`
- `GET /api/health`
- `GET /api/session-config`
- `POST /api/session-config`
- `GET /api/presets`
- `POST /api/presets/load`
- `POST /api/presets/save`
- `POST /api/url/inspect`
- `POST /api/jobs/download`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`

## Launching the Web UI

Linux / WSL:

```bash
./start_web_ui.sh
```

Windows PowerShell:

```powershell
.\start_web_ui.ps1
```

Default address:

- `http://127.0.0.1:8000`

### Environment Overrides

The launchers support a few simple overrides.

Linux / WSL:

```bash
YTRIPPER_WEB_HOST=0.0.0.0 YTRIPPER_WEB_PORT=8010 ./start_web_ui.sh
```

PowerShell:

```powershell
$env:YTRIPPER_WEB_HOST = "0.0.0.0"
$env:YTRIPPER_WEB_PORT = "8010"
.\start_web_ui.ps1
```

Optional reload mode:

Linux / WSL:

```bash
YTRIPPER_WEB_RELOAD=true ./start_web_ui.sh
```

PowerShell:

```powershell
$env:YTRIPPER_WEB_RELOAD = "true"
.\start_web_ui.ps1
```

## Current V1 Workflow

1. Open the web UI.
2. Adjust the current session settings if needed.
3. Paste a YouTube video or playlist URL.
4. Inspect the URL first if you want metadata/validation feedback.
5. Start the download job.
6. Watch the job list update.

Current note:

- one top-level action creates one top-level job
- playlist or batch item detail belongs under the job, not the top-level session list

## Current V1 Limits

These limits are expected for the current milestone:

- the HTML shell is intentionally basic
- the job list is still summary-oriented
- the page is not yet a polished operator interface
- batch/file-driven flows are not yet represented well in the shell
- per-item job detail presentation is still shallow
- styling is present, but still utility-level rather than final product-level
- cancellation/pause controls do not exist yet

## Dependency Notes

The web backend currently expects:

- `fastapi`
- `uvicorn`

These are now included in `requirements.txt`.

If the launch script fails because the local virtual environment is stale, reinstall requirements:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Or on Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Relationship To The CLI

The CLI still matters.
The web UI is not replacing it yet.

Current rule of thumb:

- CLI remains the richer, battle-tested control surface
- web UI is the emerging graphical shell around shared services

The shared service layer is what keeps both paths aligned.

## Milestone Policy

This README will be updated at meaningful web-UI milestones, especially:

- when the next larger post-V1 iteration begins
- when the runtime/launch flow changes materially
- when the route surface or user workflow changes enough to matter

It will not be updated for every tiny internal refactor.
