#!/bin/bash
# filepath: setup.sh
set -e

REPO_NAME="Python-YTRipper"
REPO_MARKER="source/yt_ripper.py"  # unique file to detect repo

# Function to find repo root
find_repo_root() {
    local current_dir="$PWD"

    # Check if we're already inside a repo
    if [ -f "$current_dir/$REPO_MARKER" ]; then
        echo "$current_dir"
        return 0
    fi

    # Check if repo exists in current directory (any name)
    for dir in */; do
        if [ -f "${dir}${REPO_MARKER}" ]; then
            echo "$(cd "$dir" && pwd)"
            return 0
        fi
    done

    return 1
}

# Try to find existing repo
REPO_ROOT=$(find_repo_root 2>/dev/null || echo "")

if [ -n "$REPO_ROOT" ]; then
    echo "Detected existing repository at: $REPO_ROOT"
    echo ""
    echo "Options:"
    echo "1) Update (clone fresh, may overwrite settings)"
    echo "2) Use existing installation"
    echo "3) Cancel"
    read -p "Enter choice [1-3]: " choice

    case $choice in
        1)
            echo "Updating repository..."
            PARENT_DIR="$(dirname "$REPO_ROOT")"
            cd "$PARENT_DIR"
            CURRENT_NAME="$(basename "$REPO_ROOT")"

            if [ -d "${CURRENT_NAME}_backup" ]; then
                rm -rf "${CURRENT_NAME}_backup"
            fi
            mv "$CURRENT_NAME" "${CURRENT_NAME}_backup"
            echo "Backed up existing repo to: ${CURRENT_NAME}_backup"
            ;;
        2)
            echo "Using existing installation at: $REPO_ROOT"
            cd "$REPO_ROOT"

            # Check if venv exists, create if missing
            if [ ! -d ".venv" ]; then
                echo "Creating virtual environment..."
                python3 -m venv .venv
                source .venv/bin/activate
                pip install -r requirements.txt
            else
                source .venv/bin/activate
                echo "Virtual environment already active."
            fi

            deactivate
            echo "Setup complete. To use the app, run: ./run.sh"
            exit 0
            ;;
        3)
            echo "Cancelled."
            exit 0
            ;;
        *)
            echo "Invalid choice. Cancelled."
            exit 1
            ;;
    esac
fi

# Clone the repository (fresh install or after update)
echo "Cloning repository..."
git clone https://github.com/RF-at-FH-Joanneum/Python-YTRipper.git

cd "$REPO_NAME"

# Create virtual environment and activate
echo "Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

deactivate

echo ""
echo "✓ Setup complete."
echo "To activate and run the app:"
echo "  cd $REPO_NAME"
echo "  ./run.sh -l"
echo ""
echo "Or activate venv manually:"
echo "  source .venv/bin/activate"
