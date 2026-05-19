#!/bin/bash
# Script to start the standalone autotagger with optional command-line arguments.
# Usage examples:
#   ./start_autotagger_w_args.sh --loop
#   ./start_autotagger_w_args.sh scan-dir --directory ~/Music
# This script assumes it is located in the repository root and that a virtual environment is set up in .venv.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR" || exit 1

echo "Repository root: $SCRIPT_DIR"

VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

VENV_PYTHON="$SCRIPT_DIR/$VENV_DIR/bin/python3"
if [ ! -x "$VENV_PYTHON" ]; then
    VENV_PYTHON="$SCRIPT_DIR/$VENV_DIR/bin/python"
fi

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Could not find a Python interpreter in $VENV_DIR" >&2
    exit 1
fi

echo "Using virtual environment interpreter: $VENV_PYTHON"

export PROJECT_ROOT="$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR/source${PYTHONPATH:+:$PYTHONPATH}"

echo "Starting standalone autotagger..."
exec "$VENV_PYTHON" "$SCRIPT_DIR/source/run_tagging_worker.py" "$@"
