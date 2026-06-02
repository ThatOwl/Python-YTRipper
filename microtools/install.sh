#!/bin/bash
# execute in empty directory, will detect existing repo or clone fresh if not found
set -e

REPO_NAME="Python-YTRipper"
REPO_MARKER="source/yt_ripper.py"  # unique file to detect repo

install_shell_aliases_config() {
    local repo_root="$1"
    local config_dir="$repo_root/config"
    local config_file="$config_dir/shell_aliases.conf"
    local legacy_config_file="$repo_root/shell_aliases.conf"

    mkdir -p "$config_dir"

    if [ -f "$legacy_config_file" ] && [ ! -f "$config_file" ]; then
        mv "$legacy_config_file" "$config_file"
        echo "Migrated legacy alias config to: $config_file"
    fi

    if [ -f "$config_file" ]; then
        if ! grep -q '^# TAGDIR_DEFAULT_DIRECTORY=' "$config_file" && ! grep -q '^TAGDIR_DEFAULT_DIRECTORY=' "$config_file"; then
            cat >> "$config_file" <<'EOF'

# Optional default directory used by `tagDir`, `tagDirFast`, and `tagDirAll`.
# Leave commented out to let those aliases default to your current shell directory.
# TAGDIR_DEFAULT_DIRECTORY="$HOME/RipperTarget"
EOF
            echo "Updated alias config with tagger defaults: $config_file"
        else
            echo "Alias config already exists: $config_file"
        fi
        return 0
    fi

    cat > "$config_file" <<'EOF'
# Python-YTRipper shell aliases configuration
# This file is read by both microtools/shell_aliases.sh and microtools/shell_aliases.ps1.
# Override these values for your environment.

# Default file used by `ytp` (calls ytf <file>)
YTF_DEFAULT_FILE="$HOME/RipperTarget/paste-here.txt"

# Optional default directory used by `tagDir`, `tagDirFast`, and `tagDirAll`.
# Leave commented out to let those aliases default to your current shell directory.
# TAGDIR_DEFAULT_DIRECTORY="$HOME/RipperTarget"
EOF

    echo "Created alias config: $config_file"
}

# Ensure shell aliases are sourced from ~/.bashrc
install_shell_aliases() {
    local repo_root="$1"
    local aliases_file="$repo_root/microtools/shell_aliases.sh"
    local bashrc="$HOME/.bashrc"
    local source_line="source $aliases_file"

    if [ ! -f "$aliases_file" ]; then
        echo "Warning: alias file not found: $aliases_file"
        return 0
    fi

    touch "$bashrc"
    # Keep only one shell_aliases source line and make sure it points to this repo.
    sed -i '/source .*\/scripts\/shell_aliases\.sh/d' "$bashrc"
    sed -i '/source .*\/microtools\/shell_aliases\.sh/d' "$bashrc"
    if grep -Fqx "$source_line" "$bashrc"; then
        echo "Shell aliases already configured in $bashrc"
    else
        echo "$source_line" >> "$bashrc"
        echo "Added shell aliases to $bashrc"
    fi
}

print_post_install_help() {
    local repo_root="$1"

    echo ""
    echo "✓ Setup complete."
    echo "Repository: $repo_root"
    echo "Start the app with:"
    echo "  cd $repo_root"
    echo "  ./start_w_args.sh --loop"
    echo "  ./start_autotagger_w_args.sh --loop"
    echo "  tagDir ~/Music"
    echo ""
    echo "README:"
    echo "  $repo_root/README.md"
    echo "  $repo_root/README_Autotagger.md"
    echo "Please open the README for usage, flags, loop mode, and setup details."
    echo ""
    echo "Or activate the virtual environment manually:"
    echo "  source $repo_root/.venv/bin/activate"
}

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

            install_shell_aliases_config "$REPO_ROOT"
            install_shell_aliases "$REPO_ROOT"

            deactivate
            print_post_install_help "$REPO_ROOT"
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
git clone https://github.com/ThatOwl/Python-YTRipper.git

cd "$REPO_NAME"

# Create virtual environment and activate
echo "Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

deactivate

install_shell_aliases_config "$(pwd)"
install_shell_aliases "$(pwd)"

print_post_install_help "$(pwd)"
