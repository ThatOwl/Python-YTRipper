# Python-YTRipper

A small, opinionated YouTube downloader toolkit built around pytubefix and ffmpeg.  
Designed for private use, easy extension, and experimentation — provides a programmatic API, a simple CLI, and a foundation for a future GUI or threaded downloader.

## Disclaimer

- heavily supported by copilot as learning objectives are architecture, unit-testing, API-integration and error handling. (Not primarily coding or efficiency)
- not all copied/inspired code sections are referenced yet
### Current state: 
- Downloads for videos and playlists work
- Many smaller things and cases (yt related bugs) do not work properly including [argcomplete](https://pypi.org/project/argcomplete/)
---

## Features

- Download YouTube videos and playlists
- Audio-only or video download options
- Interactive menu mode
- Command-line mode for automation
- Thumbnail extraction
- Stream conversion and merging
---

## Installation

Prerequisites:
- Python 3.9+
- ffmpeg installed and available on PATH
- Usage of virtualenv

Install project dependencies:
```bash
sudo apt install python3-full python3-venv
```

### Quick Setup (Linux)

1. **Download and run the installer:**
   ```bash
   wget https://raw.githubusercontent.com/RF-at-FH-Joanneum/Python-YTRipper/main/install.sh
   chmod +x install.sh
   ./install.sh
   ```

2. **The installer will:**
   - Detect existing installations (even if directory was renamed)
   - Offer to update or use existing installation
   - Clone the repository
   - Create a virtual environment
   - Install all dependencies automatically

3. **Follow the prompts:**
   - Option 1: Update (fresh clone, backs up old version to `*_backup`)
   - Option 2: Use existing installation (preserves settings)
   - Option 3: Cancel


### Manual Installation

```bash
# Clone the repository
git clone https://github.com/RF-at-FH-Joanneum/Python-YTRipper.git
cd Python-YTRipper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
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

--- 

## Usage

### Interactive Loop Mode (Recommended)
```bash
./start_w_args.sh --loop
```
Repeatedly shows command menu after each operation.

### Interactive Menu Mode
```bash
./start_w_args.sh --menu
```
Enter interactive mode with full feature menu.

### Command Mode
```bash
# Single command (exits after completion)
python3 source/yt_ripper.py <URL> [options]

# Show help
./start_w_args.sh --help
```

### Manual Virtual Environment Activation
```bash
source .venv/bin/activate
python3 source/yt_ripper.py --help
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
## Project Structure

```
Python-YTRipper/
├── source/
│   ├── yt_ripper.py          # Entry point
│   ├── core/                 # Core functionality
│   │   ├── pytube_interface.py
│   │   ├── stream_converter.py
│   │   └── ...
│   └── cli/                  # CLI interfaces
│       ├── cli_interactive.py
│       └── cli_command.py
├── tests/                    # Test files
├── install.sh                # Automated installer
├── start_w_args.sh           # Run script with arguments
└── requirements.txt          # Python dependencies
```

---

## Design notes & rationale

- SOLID-inspired: responsibilities are split (downloader vs converters vs thumbnail). This improves testability and concurrency readiness.
- Download options are represented as an immutable dataclass (`DownloadOptions`, frozen) — safe to share between threads.
- Low-level helpers log full diagnostics and raise domain-specific exceptions; the CLI/top level logs concise user-facing messages.


---

## Concurrency considerations

- The library shall be designed to be safe for multi-threaded use when following the recommended patterns:
  - Keep `DownloadOptions` immutable.
  - Use stateless downloader instance or create one downloader per task.
  - Missing: _Avoid sharing mutable state (e.g., per-download temp filenames are generated)._
- Coordinate writes to the same directory (unique filenames or per-task temp dirs) to avoid collisions.

---

## Development

### Running Tests
- not yet implemented

### Debugging in VS Code
See launch.json for debug configurations.

## Troubleshooting

**Issue: ModuleNotFoundError**
- Make sure you're running from the repository root
- Ensure virtual environment is activated: `source .venv/bin/activate`

**Issue: FFmpeg not found**
- Install FFmpeg: `sudo apt install ffmpeg` (Ubuntu/Debian)

**Issue: Installation fails**
- Check Python version: `python3 --version` (requires 3.8+)
- Ensure pip is installed: `python3 -m pip --version`

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
