#!/usr/bin/env bash
# Script to find and list large media files in the current directory and subdirectories.
# Usage: show_large_files.sh [options] [rootdir]
# Options:
#   -m <minutes>       Minimum duration to consider (default: 8)
#   -s <field>         Sort by: duration | size | name (default: duration)
#   -p <jobs>          Parallel ffprobe jobs (default: CPU cores)
#   -c, --console      Output to console (colorized if TTY)
#   -t, --text         Output to auto-named text file
#   -v, --csv          Output to auto-named CSV file

# This script uses ffprobe to analyze media files and outputs those that exceed the specified duration threshold.
# It supports parallel processing for faster analysis and can output results in various formats. Colorized console output is provided if the terminal supports it.
set -euo pipefail

# ---------------- CONFIG DEFAULTS ----------------

MIN_SECONDS=$((8 * 60))
SORT_BY="duration"
OUT_CONSOLE=false
OUT_TEXT=false
OUT_CSV=false
JOBS=$(( ($(nproc 2>/dev/null || echo 8) + 1) / 2 ))
EXTENSIONS=("mp3" "m4a" "mp4")
ROOT_DIR="."

# ---------------- COLOR HANDLING ----------------

if [[ -t 1 ]]; then
  GREEN=$'\033[0;32m'
  YELLOW=$'\033[0;33m'
  RED=$'\033[0;31m'
  RESET=$'\033[0m'
  COLOR_ENABLED=true
else
  GREEN="" YELLOW="" RED="" RESET=""
  COLOR_ENABLED=false
fi

# ---------------- HELP ----------------

usage() {
  cat <<EOF
Usage: $0 [options] [rootdir]

Path:
  rootdir            Directory tree to scan (default: current directory)

Output:
  -c, --console      Output to console (colorized if TTY)
  -t, --text         Output to text file named: <date>_<rootdir>_Large-Files.txt
  -v, --csv          Output to CSV file named:  <date>_<rootdir>_Large-Files.csv

Filtering & sorting:
  -m <minutes>       Minimum duration (default: 8)
  -s <field>         Sort by: duration | size | name
  -p <jobs>          Parallel ffprobe jobs (default: CPU cores)

Info:
  --info             Show environment & dependency info
  -h, --help         Show this help

Dependencies:
    - ffprobe        (from ffmpeg)  → media duration detection

Examples:
  $0 --console --text /mnt/d/media
  $0 -c --csv -m 20 -s size /mnt/d/media
EOF
}

# ---------------- ARG PARSING ----------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--console) OUT_CONSOLE=true ;;
    -t|--text) OUT_TEXT=true ;;
    -v|--csv) OUT_CSV=true ;;
    -m) MIN_SECONDS=$(( $2 * 60 )); shift ;;
    -s) SORT_BY="$2"; shift ;;
    -p) JOBS="$2"; shift ;;
    --info)
      echo "Media scan tool info"
      echo "-------------------"
      echo "ffprobe:      $(command -v ffprobe >/dev/null && echo yes || echo no)"
      echo "CPU cores:    $(nproc 2>/dev/null || echo unknown)"
      echo "Parallelism:  $JOBS job(s)"
      echo "Color output: $COLOR_ENABLED"
      echo "Extensions:   ${EXTENSIONS[*]}"
      echo "Min duration: $((MIN_SECONDS/60)) minutes"
      exit 0
      ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Unknown option: $1"; usage; exit 1 ;;
    *)
      if [[ "$ROOT_DIR" != "." ]]; then
        echo "Only one rootdir may be provided"
        usage
        exit 1
      fi
      ROOT_DIR="$1"
      ;;
  esac
  shift
done

if [[ ! -d "$ROOT_DIR" ]]; then
  echo "ERROR: rootdir does not exist or is not a directory: $ROOT_DIR" >&2
  exit 1
fi

ROOT_BASENAME=$(basename -- "$(realpath "$ROOT_DIR")")
if [[ -z "$ROOT_BASENAME" || "$ROOT_BASENAME" == "/" || "$ROOT_BASENAME" == "." ]]; then
  ROOT_BASENAME="root"
fi

ROOT_SAFE=$(printf '%s' "$ROOT_BASENAME" | sed 's/[^[:alnum:]_.-]/_/g')
DATE_STAMP=$(date +%Y_%m_%d)
OUT_TXT="${DATE_STAMP}_${ROOT_SAFE}_Large-Files.txt"
OUT_CSV_FILE="${DATE_STAMP}_${ROOT_SAFE}_Large-Files.csv"
# ---------------- DEP CHECK ----------------

command -v ffprobe >/dev/null || {
  echo "ERROR: ffprobe not found (install ffmpeg)" >&2
  exit 1
}

# ---------------- SCAN (PARALLEL) ----------------

export MIN_SECONDS

scan_file() {
  file="$1"

  duration=$(ffprobe -v error \
    -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 \
    "$file" 2>/dev/null) || exit 0

  [[ -z "$duration" ]] && exit 0

  sec=${duration%.*}
  (( sec > MIN_SECONDS )) || exit 0

  size=$(stat -c %s "$file")
  size_h=$(du -h --apparent-size "$file" | cut -f1)

  printf "%s|%s|%s|%s|%s\n" \
    "$sec" "$size" "$size_h" "$(dirname "$file")" "$(basename "$file")"
}

export -f scan_file

mapfile -t ROWS < <(
  find "$ROOT_DIR" -type f \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.mp4" \) -print0 |
  xargs -0 -n1 -P "$JOBS" bash -c 'scan_file "$0"'
)

# ---------------- SORT ----------------

case "$SORT_BY" in
  duration) sort_key=1 ;;
  size)     sort_key=2 ;;
  name)     sort_key=5 ;;
  *) echo "Invalid sort field"; exit 1 ;;
esac

IFS=$'\n' ROWS=($(sort -t'|' -k"$sort_key","$sort_key" <<< "${ROWS[*]}"))
unset IFS

# ---------------- FORMAT HELPERS ----------------

fmt_duration() {
  printf '%02d:%02d:%02d' \
    $(($1/3600)) $(($1%3600/60)) $(($1%60))
}

dur_color() {
  if (( $1 < 1200 )); then
    printf "%s" "$GREEN"
  elif (( $1 < 3600 )); then
    printf "%s" "$YELLOW"
  else
    printf "%s" "$RED"
  fi
}

# ---------------- FILE OUTPUTS ----------------

if $OUT_TEXT; then
  for r in "${ROWS[@]}"; do
    IFS='|' read -r sec size size_h dir name <<< "$r"
    printf "%s\t | \t%s\t | \t%s\t | \t%s\n" \
      "$size_h" "$(fmt_duration "$sec")" "$dir" "$name"
  done > "$OUT_TXT"
fi

if $OUT_CSV; then
  {
    echo "filesize,duration,directory,filename"
    for r in "${ROWS[@]}"; do
      IFS='|' read -r sec size size_h dir name <<< "$r"
      printf "\"%s\",\"%s\",\"%s\",\"%s\"\n" \
        "$size_h" "$(fmt_duration "$sec")" "$dir" "$name"
    done
  } > "$OUT_CSV_FILE"
fi

# ---------------- CONSOLE (LAST) ----------------

if $OUT_CONSOLE; then
  for r in "${ROWS[@]}"; do
    IFS='|' read -r sec size size_h dir name <<< "$r"
    color=$(dur_color "$sec")
    printf "%b\n" \
      "$size_h\t | \t${color}$(fmt_duration "$sec")${RESET}\t | \t$dir\t | \t$name"
  done
fi
