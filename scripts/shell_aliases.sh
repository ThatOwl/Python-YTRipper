#!/bin/bash

# Central shell aliases/functions for Python-YTRipper helpers.

# Clear old alias names so re-sourcing remains safe.
unalias autotag autotag-mb ytp ytl ytl-h slf slf-h 2>/dev/null || true

_alias_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YTRIPPER_REPO_ROOT="$(cd "$_alias_script_dir/.." && pwd)"

# Load user-overridable defaults from config/shell_aliases.conf.
# Backward-compat: also accept legacy <repo-root>/shell_aliases.conf.
_alias_config="$YTRIPPER_REPO_ROOT/config/shell_aliases.conf"
_legacy_alias_config="$YTRIPPER_REPO_ROOT/shell_aliases.conf"
if [ -f "$_alias_config" ]; then
    # shellcheck source=/dev/null
    source "$_alias_config"
elif [ -f "$_legacy_alias_config" ]; then
    # shellcheck source=/dev/null
    source "$_legacy_alias_config"
fi

AUTOTAG_DEFAULT_ROOT="${AUTOTAG_DEFAULT_ROOT:-/mnt/d/Program_Targets/MusicBrainz}"
AUTOTAG_DEFAULT_TARGET="${AUTOTAG_DEFAULT_TARGET:-/mnt/d/Program_Targets/TaggingTarget}"
YTF_DEFAULT_FILE="${YTF_DEFAULT_FILE:-$HOME/RipperTarget/paste-here.txt}"

AUTOTAG_RUNNER="$YTRIPPER_REPO_ROOT/scripts/run_autotagger.sh"
START_W_ARGS_SCRIPT="$YTRIPPER_REPO_ROOT/start_w_args.sh"
SHOW_LARGE_FILES_SCRIPT="$YTRIPPER_REPO_ROOT/scripts/show_large_files.sh"

autotag() {
    "$AUTOTAG_RUNNER" \
        "$AUTOTAG_DEFAULT_ROOT" \
        --target "$AUTOTAG_DEFAULT_TARGET" \
        --enrich-all --write
}

autotag_mb() {
    "$AUTOTAG_RUNNER" \
        "$AUTOTAG_DEFAULT_ROOT" \
        --target "$AUTOTAG_DEFAULT_TARGET" \
        --enrich-all --write --mb-only
}
alias autotag-mb='autotag_mb'

stripnum() {
    if [ "$#" -lt 1 ]; then
        echo "Usage: stripnum <target_dir>"
        return 1
    fi
    "$AUTOTAG_RUNNER" "$1" --strip-track-prefix
}

# PythonRipper setup
ytf() {
    (cd "$YTRIPPER_REPO_ROOT" && bash "$START_W_ARGS_SCRIPT" -f "$1")
}

ytp() {
    ytf "$YTF_DEFAULT_FILE"
}

ytl() {
    (cd "$YTRIPPER_REPO_ROOT" && bash "$START_W_ARGS_SCRIPT" -l)
}

alias ytl-h='ytl --help'

# show_large_files shortcut
slf() {
    "$SHOW_LARGE_FILES_SCRIPT" "$@"
}

alias slf-h='slf --help'
