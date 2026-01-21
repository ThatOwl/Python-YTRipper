#!/bin/bash

# Output file
output_file="codebase.py"

# Clear the output file if it exists
> "$output_file"

# Find all .py files recursively (excluding the output file itself and __init__.py files)
find . -type f -name "*.py" ! -name "$(basename "$output_file")" ! -name "__init__.py" | sort | while read -r file; do
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