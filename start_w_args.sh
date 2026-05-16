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

# Create or activate virtual environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Start the application (as a script, not module)
echo "Starting application 'Python-YTRipper'..."
python3 source/yt_ripper.py "$@"

# Deactivate venv on exit
deactivate
