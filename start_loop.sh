# ensure script is run from the repository root directory "Python-YTRipper"
if [ "$(basename "$PWD")" != "Python-YTRipper" ]; then
    echo "Please run this script from the repository root directory 'Python-YTRipper'."
    exit 1
else
    # Start the application
    echo "Starting application 'Python-YTRipper'."
    source .venv/bin/activate
    python3 -m source.main --loop
fi