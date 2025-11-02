# Python-YTRipper

A small, opinionated YouTube downloader toolkit built around pytubefix and ffmpeg.  
Designed for private use, easy extension, and experimentation — provides a programmatic API, a simple CLI, and a foundation for a future GUI or threaded downloader.

## Disclaimer

- heavily supported by copilot as learning objectives are architecture, unit-testing, API-integration and error handling. (Not primarily coding or efficiency)
- not all copied/inspired code sections are referenced yet
- current state many thing do not work properly including [argcomplete](https://pypi.org/project/argcomplete/)
---

## Features

- Download single YouTube videos or entire playlists
- Download audio-only (convert to MP3/M4A) or full video (merge separate audio/video streams)
- Thumbnail download and optional embedding as cover art
- Centralized logging with configurable verbosity
- Retry wrapper for transient network/IO errors
- Modular design: YouTubeDownloader, StreamConverter, ThumbnailHandler
- Safe filename sanitization and collision-resistant temp filenames

---

## Quick Start

Prerequisites:
- Python 3.9+
- ffmpeg installed and available on PATH
- Recommended: use a virtualenv

Install project dependencies:
```bash
sudo apt install python3-full python3-venv
```

In the directory where this project is clone to do this manually:
(optionally use [install.sh](https://github.com/RF-at-FH-Joanneum/Python-YTRipper/blob/main/install.sh) script)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

IF you are having trouble with externally managed environment do:
```bash
rm -rf .venv
python3 -m venv --without-pip .venv
source .venv/bin/activate
curl -sS https://bootstrap.pypa.io/get-pip.py | python
python3 -m pip install -r requirements.txt
```

Run the interactive CLI (from the project root):
Or use the [star_app.sh](https://github.com/RF-at-FH-Joanneum/Python-YTRipper/blob/main/start_app.sh)
```bash
python3 -m source.cl_interface
```

One-shot CLI example (interactive prompt accepts the same arguments):
```
# At the prompt:
yt> https://www.youtube.com/watch?v=VIDEO_ID -a --clear -d ./downloads
```

Or run a module-level download from Python:
```python
from source.pytube_interface import YouTubeDownloader, DownloadOptions

opts = DownloadOptions.from_preferences({
    "audio_only": True,
    "preferred_quality": "",
})
ytd = YouTubeDownloader()
ytd.download("https://www.youtube.com/watch?v=VIDEO_ID", download_dir="./downloads", options=opts)
```

---

## Configuration

User preferences are read from `user_settings.json` (located next to the project root by default). The CLI reads `loglevel` and other defaults from that file. If missing, sensible defaults are created.

Important preferences:
- `default_download_directory`
- `audio_only`
- `loglevel` (e.g. DEBUG, INFO, WARNING)
- `preferred_[video|audio]_quality`

---

## Project layout

- `source/`
  - `pytube_interface.py` — main downloader and orchestration
  - `stream_converter.py` — ffmpeg helpers (merge/convert)
  - `url_handler.py` — URL detection/validation utilities
  - `cl_interface.py` — interactive CLI
  - `logger.py` — centralized logger factory
- `tests/` — unit / manual tests
- `.venv/`, `requirements.txt`

---

## Design notes & rationale

- SOLID-inspired: responsibilities are split (downloader vs converters vs thumbnail). This improves testability and concurrency readiness.
- Download options are represented as an immutable dataclass (`DownloadOptions`, frozen) — safe to share between threads.
- Low-level helpers log full diagnostics and raise domain-specific exceptions; the CLI/top level logs concise user-facing messages.

- Not yet implemented: _Temporary filenames use a short UUID suffix to avoid collisions when multiple downloads run concurrently._

---

## Concurrency considerations

- The library is designed to be safe for multi-threaded use when following the recommended patterns:
  - Keep `DownloadOptions` immutable.
  - Use stateless downloader instance or create one downloader per task.
  - Missing: _Avoid sharing mutable state (e.g., per-download temp filenames are generated)._
- Coordinate writes to the same directory (unique filenames or per-task temp dirs) to avoid collisions.

---

## Troubleshooting

- ModuleNotFoundError: No module named 'source'  
  Run the script from project root and use `python -m source.cl_interface ...` or add the project root to `PYTHONPATH` / `sys.path`. The CLI uses package-style invocation.
- ffmpeg errors (codec incompatibility): try encoding instead of copy:
  - `vcodec='libx264'` and `acodec='aac'` produce broadly compatible MP4 files (slower).
- Downloaded file extension doesn't match stream subtype: use the path returned by `stream.download()` instead of guessing file extensions.
- If thumbnail embedding fails for MP3, the code uses the proper ffmpeg mapping (image as second input, `-map 0:a -map 1:v`).

---

## Tests

Run tests with pytest from project root:
```bash
pytest -q
```
Note: some tests may depend on network connectivity; many tests are intended as manual/integration checks.

---

## Contributing

Contributions welcome. Suggested areas:
- Add unit tests and CI
- Improve error handling and recoverability
- Add a GUI or a simple HTTP API
- Add a progress bar and better rate-limiting / backoff policies

Please follow existing code style and add tests for new logic.

---

## [License](https://github.com/RF-at-FH-Joanneum/Python-YTRipper/blob/main/LICENSE)

---

## Final notes

This project is intended for private / personal use. Respect YouTube's Terms of Service and copyright rules when downloading content. Use responsibly.
