## Project context

This project runs in WSL Ubuntu 24.04.
Use Linux shell commands.
Assume the repository is opened from VS Code Remote WSL.

This repository is a Python-based YouTube downloader toolkit built around `pytubefix` and `ffmpeg`. It provides a CLI-first workflow with interactive and command modes, a reusable downloader core under `source/core`, and supporting scripts for related media tasks like tagging and batch conversion. The main entrypoint is `source/yt_ripper.py`, with `start_w_args.sh` handling local venv activation and launch.


## Working rules

- Do not make large refactors without asking first.
- Prefer small, reviewable changes.
- Explain the plan before editing.
- Show the diff after changes.
- Do not add new dependencies without confirmation.
- Do not touch secrets, credentials, .env files, or deployment config unless explicitly asked.

Permissions baseline: see [permissions.yaml](/home/localuser/GitRepos/Python-YTRipper/ai-workflow/permissions.yaml) for default values and example alternatives.

## Commands
- Install: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run dev server: `./start_w_args.sh --loop`
- Run tests: `python3 -m unittest discover -s tests`
- Lint: not configured
- Build: not configured

## Code style

- Preserve existing style.
- Prefer readable, explicit code over clever abstractions.
- Add comments only when they clarify non-obvious logic.
