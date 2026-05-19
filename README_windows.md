# Python-YTRipper on Windows

## Read This First

This project is **Windows-able**, but **not fully Windows-supported**.

That wording is intentional.

It means:

- the core Python application can likely run on native Windows
- the main downloader can be used from PowerShell
- much of the CLI behavior is already cross-platform
- but the project is still designed and documented primarily around a Linux-first workflow

It does **not** mean:

- polished Windows installer
- official end-to-end Windows support
- guaranteed parity with Linux behavior
- extensive Windows testing across all features

If you want the blunt version:

- this is **not** a click-and-go Windows app
- this is **not** a finished Windows product
- this is a Python CLI project that can be made to run on Windows if you set it up carefully

If that sounds acceptable, continue.

---

## What Works Best on Windows

Most realistic Windows usage right now:

- run from source
- use Python in a virtual environment
- use PowerShell
- install `ffmpeg` separately and make sure it is on `PATH`

Recommended expectation level:

- downloader CLI: likely usable
- interactive loop mode: likely usable
- batch mode: likely usable
- ffmpeg conversion/merge: usable if `ffmpeg` is installed correctly
- autotagging: partly usable, but more experimental

---

## Prerequisites

You need:

- Windows
- Python 3.9+
- `git`
- `ffmpeg`

```powershell
winget install python3
winget install git
winget install ffmpeg
```

You should also be comfortable with:

- opening PowerShell
- creating a Python virtual environment
- running Python scripts from the repository root

---

## Manual Installation

Open PowerShell and run:

```powershell
git clone https://github.com/RF-at-FH-Joanneum/Python-YTRipper.git
cd Python-YTRipper

py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use the virtual environment Python directly instead:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Confirm that `ffmpeg` is available:

```powershell
ffmpeg -version
```

If that command fails, the downloader may still start, but media conversion / merging features will fail later.

---

## Important Windows Rules

- Run commands from the repository root.
- Prefer PowerShell examples from this file, not the Linux `.sh` launchers.
- Do not rely on `start_w_args.sh` or `start_autotagger_w_args.sh` on Windows.
- Use quoted Windows paths when they contain spaces.
- Keep `ffmpeg` on `PATH`.

Example repository-root usage:

```powershell
.\.venv\Scripts\python.exe .\source\yt_ripper.py --help
```

Example quoted Windows path:

```powershell
.\.venv\Scripts\python.exe .\source\yt_ripper.py "https://www.youtube.com/watch?v=example" -o "C:\Users\YourName\Downloads\RipperDownloads"
```

---

## Usage

### Interactive Loop Mode

From the project root:

```powershell
.\.venv\Scripts\python.exe .\source\yt_ripper.py --loop
```

This starts the prompt-based loop. Each entered line is parsed like a normal one-shot CLI command.

When `prompt_toolkit` is installed and the CLI is running in a real terminal, loop mode can also provide:

- arrow-key editing
- command history across sessions
- `Ctrl-R` history search
- completion for flags, common flag values, and filesystem paths after `-f` / `-o`

### Command Mode

Use one-shot commands like this:

```powershell
.\.venv\Scripts\python.exe .\source\yt_ripper.py <URL> [options]
```

### Examples

```powershell
# Audio-only download
.\.venv\Scripts\python.exe .\source\yt_ripper.py "https://www.youtube.com/watch?v=7S_cMrxjZFo" -a true

# Batch mode from file
.\.venv\Scripts\python.exe .\source\yt_ripper.py -f .\tests\test_download.txt

# Show info without downloading
.\.venv\Scripts\python.exe .\source\yt_ripper.py "https://www.youtube.com/watch?v=7S_cMrxjZFo" --info
```

---

## Auto-Tagging Pipeline

The main downloader includes an early-stage autotagging pipeline.

- `-at, --autotag true`
  - downloads normally
  - prepares tagging queue packages
  - starts a lightweight background worker
- `--prepare-tagging true`
  - downloads normally
  - prepares tagging queue packages only
  - does not start worker-based processing

This area is still more experimental than the main downloader.

Windows-specific caution:

- the autotagging flow is more likely than the base downloader to expose platform-specific rough edges
- background worker behavior has a higher chance of surprises than simple one-shot downloads
- if you are testing Windows viability, validate normal downloading first before enabling autotagging

Example:

```powershell
.\.venv\Scripts\python.exe .\source\yt_ripper.py "https://www.youtube.com/watch?v=7S_cMrxjZFo" -at true
```

---

## Standalone Autotagger on Windows

There is also a separate standalone autotagging CLI.

Direct Python entrypoint:

```powershell
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py --help
```

Interactive loop:

```powershell
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py --loop
```

Available commands include:

- `run`
- `status`
- `session`
- `events`
- `review-list`
- `review-override`
- `review-approve`
- `review-reject`
- `plan-session`
- `plan-queue`
- `retry`
- `retry-run`
- `scan-dir`
- `apply-csv`

Examples translated to Windows paths:

```powershell
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py status
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py session --session-id <session-id>
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py events --event-type candidate_resolved --limit 20
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py review-list
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py review-override --job-id <job-id> --artist "Artist" --title "Title"
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py review-approve --job-id <job-id> --note "ready to retry"
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py review-reject --job-id <job-id> --reason "needs manual research"
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py plan-session --session-id <session-id>
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py plan-queue
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py retry --job-id <job-id>
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py retry --session-id <session-id> --source-state skipped
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py retry-run --job-id <job-id>
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py scan-dir --directory "D:\Music\Rammstein"
.\.venv\Scripts\python.exe .\source\run_tagging_worker.py apply-csv --csv "D:\Music\Rammstein\2026-05-19_Rammstein_tag_suggestions.csv"
```

### Local Directory CSV Workflow

`scan-dir`:

- walks one root recursively
- inspects supported files in place
- skips already-tagged files by default
- uses filename, folder context, and optional MusicBrainz confirmation to propose tags
- writes one CSV with current and proposed values

`apply-csv`:

- reads the edited CSV back
- writes only rows whose `apply_mode` is set to a write-like value such as `write`
- updates the same CSV with write results
- writes tags directly into the original files

---

## Configuration

The main config file is:

- `config/default_settings_<username>.json`

If it does not exist, it is created automatically from internal defaults.

Important preferences:

- `default_download_directory`
- `audio_only`
- `audio_mp3`
- `visible_loglevel`
- `preferred_[video|audio]_quality`
- `preferred_resolution`
- `preferred_abr`
- `no_dir_date`
- `save_results`
- `autotag`
- `prepare_tagging`

Windows note:

- use Windows paths in your saved config, for example `"C:\\Users\\YourName\\Downloads\\RipperDownloads"`
- some repo examples and existing preset values may still show Linux or WSL-style paths

### Presets

Immutable presets can be loaded with:

- `-lp ah` for audio-high
- `-lp vh` for video-high
- `-lp vl` for video-low
- `-lp test` for test-mode
- `-lp ds` for datasaver

Custom presets use ids `0` to `9`:

- `-lp 0` loads `config/presets/custom/0__custom_preset.json`
- `-sc 0` saves the current session options to custom preset `0`

Other useful config-related flags:

- `-sp true` shows the effective options before running
- `-sc true` saves the current session options to the default per-user config

---

## Main CLI Flags

- `-f, --file` batch input file (`.txt` or `.csv`)
- `-i, --info` show video or playlist info without downloading
- `-a, --audio_only` download audio only
- `-a3, --audio_mp3` convert audio output to mp3
- `-q, --preferred_quality` quality alias (`high`, `medium`, `low`)
- `-r, --preferred_resolution` target resolution
- `-au, --preferred_abr` preferred audio bitrate
- `-hf, --high_fps` prefer `60`, `30`, or `0/any`
- `-o, --download_directory` target directory
- `-nd, --no_dir_date` disable automatic date prefix on playlist folders
- `-lp, --load_preset` load preset
- `-sc, --save-config` save current config/defaults
- `-sp, --show_preset` print effective options before running
- `-sr, --save-results` save CSV download results in batch mode
- `-vl, --visible-loglevel` set console log verbosity
- `-at, --autotag` prepare tagging packages and start the background tagging worker
- `--prepare-tagging` prepare tagging packages without starting worker processing

---

## Current Behavior Notes

- Loop mode replaces the older interactive menu flow.
- Loop mode uses `prompt_toolkit` when available in a real terminal and falls back to basic input in non-interactive contexts.
- `--menu` is no longer supported.
- `save_results` writes result CSVs for batch/file-driven runs and for direct playlist URLs.
- Single standalone video URLs still do not write result CSVs.
- Batch result saving is still a young feature and may keep evolving.
- `autotag` currently does not replace the richer standalone autotagging workflow.
- `argcomplete` support is optional and not a primary workflow.

Windows interpretation of the above:

- the simpler the workflow, the safer the bet
- plain one-shot downloads are lower risk than autotagging
- Linux documentation and examples still represent the most battle-tested path

---

## Troubleshooting

**Issue: `ModuleNotFoundError`**

- Make sure you are running from the repository root.
- Make sure dependencies were installed into the same virtual environment you are using.
- Prefer calling `.\.venv\Scripts\python.exe` explicitly if you are unsure.

**Issue: `ffmpeg` not found**

- Install `ffmpeg`.
- Make sure `ffmpeg.exe` is on `PATH`.
- Open a new PowerShell window after changing `PATH`.
- Re-test with:

```powershell
ffmpeg -version
```

**Issue: PowerShell blocks `Activate.ps1`**

- Use the venv Python directly instead of activating:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\source\yt_ripper.py --help
```

**Issue: Paths with spaces fail**

- Quote them:

```powershell
-o "C:\Users\YourName\Music Downloads"
```

**Issue: A preset or config points to `/mnt/...` or `~/...`**

- That is a Linux/WSL-flavored path.
- Replace it with a real Windows path in quotes.

**Issue: Autotagging behaves strangely on Windows**

- Test the plain downloader first.
- Then test `--prepare-tagging true`.
- Only then test full `--autotag true`.

That order is not paranoia.
That is defensive driving.

---

## Final Warning, Repeated On Purpose

This repository is currently best understood as:

- Linux-first
- Windows-runnable
- Windows-documentable
- not yet confidently Windows-supported

So yes, it may work.

No, that is not the same thing as a promise.
