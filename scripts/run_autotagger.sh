#!/bin/bash
# ─────────────────────────────────────────────────────────────────────
# Self-contained runner for python-autotagger.py
#
# Creates a temporary venv, installs required packages, runs the script
# with all passed arguments, and removes the temp venv on exit.
#
# Usage examples:
#   ./scripts/run_autotagger.sh /mnt/d/Program_Targets/MusicBrainz --enrich-all --write
#   ./scripts/run_autotagger.sh /mnt/d/Program_Targets/TaggingTarget/mnt/d/Program_Targets/TempTarget_YTD --strip-track-prefix
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/python-autotagger.py"
VENV_DIR="$(mktemp -d "${TMPDIR:-/tmp}/autotagger_venv.XXXXXX")"

cleanup() {
    if [ -d "$VENV_DIR" ]; then
        rm -rf "$VENV_DIR"
        echo ""
        echo "Temporary venv removed: $VENV_DIR"
    fi
}
trap cleanup EXIT

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found." >&2
    exit 1
fi

if ! python3 -c "import venv" &>/dev/null; then
    echo "Error: python3-venv module not available." >&2
    echo "  Install with: sudo apt install python3-venv" >&2
    exit 1
fi

if [ ! -f "$PY_SCRIPT" ]; then
    echo "Error: Python script not found at $PY_SCRIPT" >&2
    exit 1
fi

echo "Creating temporary venv in $VENV_DIR ..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --quiet mutagen musicbrainzngs

echo "Setup done."
echo ""

python3 "$PY_SCRIPT" "$@"
