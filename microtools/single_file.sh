#!/bin/bash

# ==============================================================================
# Single File Codebase Aggregator
# ==============================================================================
# Purpose: Combines all Python source files from the source/ directory into
#          a single consolidated codebase.py file for easy reference
#
# Usage:   ./single_file.sh
#          (Run from anywhere in the project - script finds source/ automatically)
#
# Output:  notes_requirements/codebase.py
# ==============================================================================

# Find project root by looking for common markers
find_project_root() {
    local current_dir="$PWD"
    while [[ "$current_dir" != "/" ]]; do
        if [[ -f "$current_dir/requirements.txt" ]] || [[ -d "$current_dir/.git" ]]; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done
    echo "$PWD"  # Fallback to current directory
}

# Find project root and navigate to source directory
PROJECT_ROOT=$(find_project_root)
SOURCE_DIR="$PROJECT_ROOT/source"

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "❌ Error: source directory not found at $SOURCE_DIR"
    exit 1
fi

cd "$SOURCE_DIR" || exit 1
echo "📂 Working directory: $SOURCE_DIR"

# Output file (using absolute path)
output_file="$PROJECT_ROOT/notes_requirements/codebase.py"

# Clear the output file if it exists
> "$output_file"

# Find all .py files recursively (excluding __init__.py files)
find . -type f -name "*.py" ! -name "__init__.py" | sort | while read -r file; do
    echo "Appending: $file"
    
    cat >> "$output_file" <<EOF
#--------------------
#
#     $(basename "$file")
#
#--------------------

EOF

    cat "$file" >> "$output_file"
    echo -e "\n\n" >> "$output_file"  # Add spacing between files
done

echo "✅ All .py files have been combined into $output_file (excluding __init__.py)"