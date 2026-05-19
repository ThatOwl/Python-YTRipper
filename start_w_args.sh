#!/bin/bash
# Script to start the Python-YTRipper application with optional command-line arguments.
# Usage: start_w_args.sh [options]
# Options:
#   --loop             Start the application in interactive loop mode
#   --help             Show this help message 
# This script assumes it is located in the repository root and that a virtual environment is set up in .venv.

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the repository root
cd "$SCRIPT_DIR" || exit 1

echo "Repository root: $SCRIPT_DIR"

# Create or locate virtual environment
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

# Make repo-local imports explicit for shells, wrappers, and helpers that reuse this script.
export PROJECT_ROOT="$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR/source${PYTHONPATH:+:$PYTHONPATH}"

# Start the application (as a script, not module)
echo "Starting application 'Python-YTRipper'..."
exec "$VENV_PYTHON" "$SCRIPT_DIR/source/yt_ripper.py" "$@"
