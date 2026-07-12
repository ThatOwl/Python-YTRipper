#!/bin/bash
# Start the Python-YTRipper web UI/backend from the repository root.
# Supports simple environment overrides:
#   YTRIPPER_WEB_HOST   default: 127.0.0.1
#   YTRIPPER_WEB_PORT   default: 8000
#   YTRIPPER_WEB_RELOAD default: false

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

export PROJECT_ROOT="$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR/source${PYTHONPATH:+:$PYTHONPATH}"

HOST="${YTRIPPER_WEB_HOST:-127.0.0.1}"
PORT="${YTRIPPER_WEB_PORT:-8000}"
RELOAD="${YTRIPPER_WEB_RELOAD:-false}"

echo "Using virtual environment interpreter: $VENV_PYTHON"
echo "Starting web UI on http://$HOST:$PORT"

UVICORN_ARGS=(
    "-m" "uvicorn"
    "web.main:app"
    "--app-dir" "$SCRIPT_DIR/source"
    "--host" "$HOST"
    "--port" "$PORT"
)

if [ "$RELOAD" = "true" ] || [ "$RELOAD" = "1" ]; then
    UVICORN_ARGS+=("--reload")
fi

exec "$VENV_PYTHON" "${UVICORN_ARGS[@]}"
