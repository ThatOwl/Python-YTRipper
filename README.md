# Python-YTRipper

A small, opinionated YouTube downloader toolkit built around `pytubefix` and `ffmpeg`.
It is intended for private use, experimentation, and gradual extension, with a strong focus on a Linux-first CLI workflow.

## Disclaimer

- heavily supported by copilot as learning objectives are architecture, unit-testing, API-integration and error handling. (Not primarily coding or efficiency)
- not all copied/inspired code sections are referenced yet

### Current state

- Downloads for videos and playlists work
- Some edge cases and YouTube-side breakage still exist
- Linux is the primary target right now; WSL can work if paths and tools are set up carefully

---

## Features

- Download YouTube videos and playlists
- Audio-only or video download options
- Interactive loop mode
- One-shot command-line mode for automation
- Presets and per-user saved defaults
- Thumbnail download for audio conversion workflows
- Stream conversion and merging via `ffmpeg`

---

## Installation

Prerequisites:

- Python 3.9+
- `ffmpeg` installed and available on `PATH`
- usage of `venv`

Install system packages:

```bash
sudo apt install python3-full python3-venv ffmpeg
```

### Manual Installation

```bash
git clone https://github.com/RF-at-FH-Joanneum/Python-YTRipper.git
cd Python-YTRipper

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you run into externally-managed-environment issues:

```bash
rm -rf .venv
python3 -m venv --without-pip .venv
source .venv/bin/activate
curl -sS https://bootstrap.pypa.io/get-pip.py | python
python3 -m pip install -r requirements.txt
```

---

## Usage

### Auto-tagging pipeline

The main downloader exposes an `--autotag` flag in config/CLI, but actual tagging is not implemented in the main application yet.

For the separate metadata parsing/enrichment/tagging workflow, see:

- `scripts/python-autotagger.py`
- `scripts/README_auto_tagging.md`

### Interactive Loop Mode

```bash
./start_w_args.sh --loop
```

Starts the prompt-based loop. Each entered line is parsed like a normal one-shot CLI command.

### Command Mode

```bash
python3 source/yt_ripper.py <URL> [options]
./start_w_args.sh --help
```

### Examples

```bash
# Download a single video with current defaults
python3 source/yt_ripper.py "https://www.youtube.com/watch?v=7S_cMrxjZFo"

# Audio-only download
python3 source/yt_ripper.py "https://www.youtube.com/watch?v=7S_cMrxjZFo" -a true

# Batch mode from file
python3 source/yt_ripper.py -f ./tests/test_download.txt

# Show info without downloading
python3 source/yt_ripper.py "https://www.youtube.com/watch?v=7S_cMrxjZFo" --info
```

### Manual Virtual Environment Activation

```bash
source .venv/bin/activate
python3 source/yt_ripper.py --help
```

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
- `autotag` (currently config-only; main app behavior not implemented)

### Presets

Immutable presets live in `config/presets/immutable/` and can be loaded with:

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

### Main CLI flags

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
- `-at, --autotag` reserved for future main-app tagging integration

### Current behavior notes

- Loop mode replaces the older interactive menu flow.
- `--menu` is no longer supported.
- `save_results` writes result CSVs for batch/file-driven runs and for direct playlist URLs.
- Single standalone video URLs still do not write result CSVs. (as result easily be managed by user)
- Batch result saving is still a young feature and may keep evolving.
- `argcomplete` support is optional and not a primary workflow.

---

## Project Structure

```text
Python-YTRipper/
├── config/
│   ├── default_settings_<username>.json
│   └── presets/
├── source/
│   ├── yt_ripper.py
│   ├── application/
│   ├── cli/
│   ├── domain/
│   ├── infrastructure/
│   └── utility/
├── scripts/
│   ├── python-autotagger.py
│   ├── README_auto_tagging.md
│   └── ...
├── tests/
├── start_w_args.sh
└── requirements.txt
```

---

## Development

### Running Tests

There is no authoritative full test suite yet. A few focused regression tests exist for selected helpers and recent fixes.

Example:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test*.py' -v
```

### Debugging in VS Code

See `.vscode/launch.json` for local debug configurations.

## Troubleshooting

**Issue: `ModuleNotFoundError`**

- Make sure you're running from the repository root
- Ensure the virtual environment is activated: `source .venv/bin/activate`

**Issue: `ffmpeg` not found**

- Install `ffmpeg`: `sudo apt install ffmpeg`

**Issue: Installation fails**

- Check Python version: `python3 --version` (requires 3.9+)
- Ensure `pip` is installed: `python3 -m pip --version`

---

## Contributing

Contributions are welcome. Suggested areas:

- Add more focused tests
- Improve error handling and recoverability
- Improve user-facing documentation
- Add a GUI or a simple HTTP API

Please follow the existing code style and add tests for new logic when practical.

---

## [License](https://github.com/RF-at-FH-Joanneum/Python-YTRipper/blob/main/LICENSE)

---

## Final notes

This project is intended for private / personal use. Respect YouTube's Terms of Service and copyright rules when downloading content. Use responsibly.
