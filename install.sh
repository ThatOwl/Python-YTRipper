#!/bin/bash
set -e  # stop on errors

REPO_NAME="Python-YTRipper"

# Remove existing folder if present
if [ -d "$REPO_NAME" ]; then
    echo "Removing preexisting directory"
    rm -rf "$REPO_NAME"
fi

# Clone the repository
git clone https://github.com/RF-at-FH-Joanneum/Python-YTRipper.git

# Change to repo directory
cd "$REPO_NAME"

# Create virtual environment and activate
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (check your filename)
pip install -r requirements.txt

echo ""
echo "Setup complete. Virtual environment is activated."
echo "  | Be aware you just entered a virtual environment! (exit with deactivate)"
