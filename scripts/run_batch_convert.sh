#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# Self-contained runner for batch_convert_audio.py
#
# Creates a temporary venv, installs the single dependency
# (ffmpeg-python), runs the Python script with all passed arguments,
# and removes the venv on exit — even on Ctrl-C or errors.
#
# Prerequisites:
#   • python3 with the venv module  (sudo apt install python3-venv)
#   • ffmpeg / ffprobe on PATH      (sudo apt install ffmpeg)
#
# Usage:
#   ./scripts/run_batch_convert.sh /path/to/music
#   ./scripts/run_batch_convert.sh /path/to/music --format mp3
#   ./scripts/run_batch_convert.sh /path/to/music --dry-run
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/batch_convert_audio.py"
VENV_DIR="$(mktemp -d "${TMPDIR:-/tmp}/batch_convert_venv.XXXXXX")"

# ── Cleanup on exit (always) ─────────────────────────────────────────
cleanup() {
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
        echo ""
        echo "Temporary venv removed: $VENV_DIR"
    fi
}
trap cleanup EXIT

# ── Pre-flight checks ────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found. Install it first." >&2
    exit 1
fi

if ! python3 -c "import venv" &>/dev/null; then
    echo "Error: python3-venv module not available." >&2
    echo "  Install it with:  sudo apt install python3-venv" >&2
    exit 1
fi

if ! command -v ffmpeg &>/dev/null || ! command -v ffprobe &>/dev/null; then
    echo "Error: ffmpeg / ffprobe not found on PATH." >&2
    echo "  Install with:  sudo apt install ffmpeg" >&2
    exit 1
fi

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Error: Python script not found at $PY_SCRIPT" >&2
    exit 1
fi

# ── Create temp venv & install dependency ─────────────────────────────
echo "Creating temporary venv in $VENV_DIR ..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --quiet ffmpeg-python

echo "Setup done."
echo ""

# ── Run the actual script (forward all arguments) ────────────────────
python3 "$PY_SCRIPT" "$@"
