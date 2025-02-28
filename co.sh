#!/bin/bash
# compile.sh - Compile selected file contents into a single output file.
#
# - Code files (extensions in code_exts) are included if ≤ 5MB.
# - Data files (extensions in data_exts) are included if ≤ 1MB and have < 50 lines.
# - Hidden files and directories (those starting with '.') and common pycache directories are ignored.
#
# Output is saved to "compiled.txt".

OUTPUT="compiled.txt"
rm -f "$OUTPUT"

# Function to get file size in bytes. Works with both GNU and BSD/macOS stat.
get_file_size() {
    if stat --version >/dev/null 2>&1; then
        # GNU stat
        stat -c%s "$1"
    else
        # BSD/macOS stat
        stat -f%z "$1"
    fi
}

# Write the directory structure first, ignoring dot files.
echo "=== Directory Tree ===" > "$OUTPUT"
if command -v tree &> /dev/null; then
    # The -I option tells tree to ignore files/directories starting with a dot.
    tree -I '.*' >> "$OUTPUT"
else
    # Using find to exclude hidden paths.
    find . -not -path '*/.*' >> "$OUTPUT"
fi

echo -e "\n\n=== File Contents ===\n" >> "$OUTPUT"

# Define allowed file extensions.
code_exts=("sh" "py" "c" "cpp" "java" "js" "ts" "rb" "php" "html" "css" "sql" "go")
data_exts=("csv" "tsv" "dat")

# Helper function to check if a value is in an array.
in_array() {
    local needle="$1"
    shift
    for element in "$@"; do
        if [[ "$element" == "$needle" ]]; then
            return 0
        fi
    done
    return 1
}

# Process each file while excluding:
# - the output file,
# - hidden files or those in hidden directories,
# - and pycache directories.
find . -type f ! -name "$OUTPUT" \
         ! -path "*/.*" \
         ! -path "*/__pycache__/*" \
         ! -path "*/_pycache/*" | while IFS= read -r file; do

    # Extract the file extension (in lowercase).
    ext="${file##*.}"
    ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

    include_file=false

    if in_array "$ext" "${code_exts[@]}"; then
        # Code file: check size ≤ 5MB (5*1024*1024 bytes).
        filesize=$(get_file_size "$file")
        if [ "$filesize" -le 5242880 ]; then
            include_file=true
        else
            continue
        fi
    elif in_array "$ext" "${data_exts[@]}"; then
        # Data file: check size ≤ 1MB and line count < 50.
        filesize=$(get_file_size "$file")
        if [ "$filesize" -gt 1048576 ]; then
            continue
        fi
        line_count=$(wc -l < "$file")
        if [ "$line_count" -lt 50 ]; then
            include_file=true
        else
            continue
        fi
    else
        # Not a recognized file type; skip.
        continue
    fi

    if $include_file; then
        {
            echo "--------------------"
            echo "File: $file"
            echo "Size: $filesize bytes"
            if in_array "$ext" "${data_exts[@]}"; then
                echo "Line Count: $line_count"
            fi
            echo "--------------------"
            cat "$file"
            echo -e "\n"
        } >> "$OUTPUT"
    fi

done

echo "Compilation complete. Output saved to $OUTPUT."
