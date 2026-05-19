#!/usr/bin/env bash
# ------------------------------------------------------------
# test_cli_cases.sh
# Simple I/O tests for the YouTube Downloader CLI entry script
# ------------------------------------------------------------

# --- Locate project root dynamically ---
PROJECT_ROOT=$(pwd)
while [[ "$PROJECT_ROOT" != "/" && "$(basename "$PROJECT_ROOT")" != "Python-YTRipper" ]]; do
    PROJECT_ROOT=$(dirname "$PROJECT_ROOT")
done

# If we didn't find it, abort
if [[ "$(basename "$PROJECT_ROOT")" != "Python-YTRipper" ]]; then
    echo "❌ Error: Could not locate project root 'Python-YTRipper' in parent directories."
    exit 1
fi

# Change to /source directory
SOURCE_DIR="$PROJECT_ROOT/source"
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "❌ Error: Source directory not found at: $SOURCE_DIR"
    exit 1
fi

cd "$SOURCE_DIR" || exit 1
echo "📂 Changed directory to: $(pwd)"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

# Main Python entrypoint
SCRIPT="./yt_ripper.py"

# Helper function to run tests cleanly
run_test() {
    local desc="$1"
    shift
    local cmd=("$@")
    echo "------------------------------------------------------------"
    echo "TEST: $desc"
    echo "COMMAND: ${cmd[*]}"
    echo "------------------------------------------------------------"

    # Run and capture output and exit code
    output_file=$(mktemp)
    "${cmd[@]}" >"$output_file" 2>&1
    exit_code=$?

    echo "Exit code: $exit_code"
    echo "Output:"
    cat "$output_file"
    echo

    # Cleanup
    rm -f "$output_file"
}

# 1️⃣ Test default (interactive) mode — no arguments
run_test "No arguments (should enter interactive mode)" bash -c "printf 'exit\n' | '$PYTHON_BIN' '$SCRIPT'"

# 2️⃣ Test help mode — should print help text and exit
run_test "Help flag (--help)" "$PYTHON_BIN" "$SCRIPT" --help

# 3️⃣ Test loop mode — simulate a short interactive session
# We’ll simulate input (exit immediately) to avoid hanging
run_test "Loop mode with simulated input (exit immediately)" bash -c "echo 'exit' | '$PYTHON_BIN' '$SCRIPT' -l"

# 4️⃣ Test command mode with a fast-failing non-YouTube URL
run_test "Command mode with invalid non-YouTube URL" "$PYTHON_BIN" "$SCRIPT" "https://example.com/not-youtube"

# 5️⃣ Test invalid argument (expected to fail or misbehave)
run_test "Invalid argument flag (should print error or unexpected behaviour)" "$PYTHON_BIN" "$SCRIPT" --nonexistent

echo "------------------------------------------------------------"
echo "All tests executed."
echo "------------------------------------------------------------"


#Case 1: No args → should trigger interactive CLI mode.
#→ Expected: something like "YouTube Downloader CLI (type 'exit'...)"
#Case 2: --help → should print help text and exit cleanly (exit code 0).
#Case 3: -l (loop mode) → input "exit" to prevent infinite loop.
#→ Expected: "Exiting CLI."
#Case 4: Valid command argument → runs CommandCLI().run(cmdline).
#→ Expected: Depends on implementation — may fail gracefully.
#Case 5: Invalid flag → should show an argparse error or unexpected behavior.
#→ Expected: nonzero exit code and error message.
