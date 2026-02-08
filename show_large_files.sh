#!/usr/bin/env bash
set -euo pipefail

# ---------------- CONFIG DEFAULTS ----------------

MIN_SECONDS=$((8 * 60))
SORT_BY="duration"
OUT_CONSOLE=false
OUT_TXT=""
OUT_CSV=""
OUT_JSON=""
JOBS=$(nproc 2>/dev/null || echo 4)
EXTENSIONS=("mp3" "m4a" "mp4") #check

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
Usage: $0 [options]

Output:
  -c                 Output to console (colorized if TTY)
  -t <file>          Output to text file
  -v <file>          Output to CSV file
  -j <file>          Output to JSON file

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
  $0 -c -t out.txt -v out.csv
  $0 -j media.json -m 20 -s size
EOF
}

# ---------------- ARG PARSING ----------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -c) OUT_CONSOLE=true ;;
    -t) OUT_TXT="$2"; shift ;;
    -v) OUT_CSV="$2"; shift ;;
    -j) OUT_JSON="$2"; shift ;;
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
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
  shift
done
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
  find . -type f \( -iname "*.mp3" -o -iname "*.m4a" -o -iname "*.mp4" \) -print0 |
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

if [[ -n "$OUT_TXT" ]]; then
  for r in "${ROWS[@]}"; do
    IFS='|' read -r sec size size_h dir name <<< "$r"
    printf "%s\t | \t%s\t | \t%s\t | \t%s\n" \
      "$size_h" "$(fmt_duration "$sec")" "$dir" "$name"
  done > "$OUT_TXT"
fi

if [[ -n "$OUT_CSV" ]]; then
  {
    echo "filesize,duration,directory,filename"
    for r in "${ROWS[@]}"; do
      IFS='|' read -r sec size size_h dir name <<< "$r"
      printf "\"%s\",\"%s\",\"%s\",\"%s\"\n" \
        "$size_h" "$(fmt_duration "$sec")" "$dir" "$name"
    done
  } > "$OUT_CSV"
fi

if [[ -n "$OUT_JSON" ]]; then
  {
    echo "["
    first=true
    for r in "${ROWS[@]}"; do
      IFS='|' read -r sec size size_h dir name <<< "$r"
      $first || echo ","
      first=false
      printf '  {"filesize":"%s","duration":"%s","seconds":%s,"directory":"%s","filename":"%s"}' \
        "$size_h" "$(fmt_duration "$sec")" "$sec" "${dir//\"/\\\"}" "${name//\"/\\\"}"
    done
    echo
    echo "]"
  } > "$OUT_JSON"
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
