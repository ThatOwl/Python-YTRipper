#!/bin/bash

# Central shell aliases/functions for Python-YTRipper helpers.
# Keep these helpers opinionated and focused on the most common workflows.

unalias autotag autotag-mb ytl-h slf-h 2>/dev/null || true

_helper_function_names=(
    ytf
    ytp
    ytl
    slf
    tagLoop
    tagStatus
    tagRun
    tagDir
    tagDirFast
    tagDirAll
    tagApply
)
for _helper_name in "${_helper_function_names[@]}"; do
    unset -f "$_helper_name" 2>/dev/null || true
    unalias "$_helper_name" 2>/dev/null || true
done
unset _helper_name

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

TAGDIR_DEFAULT_DIRECTORY="${TAGDIR_DEFAULT_DIRECTORY:-}"
YTF_DEFAULT_FILE="${YTF_DEFAULT_FILE:-$HOME/RipperTarget/paste-here.txt}"

START_W_ARGS_SCRIPT="$YTRIPPER_REPO_ROOT/start_w_args.sh"
START_AUTOTAGGER_SCRIPT="$YTRIPPER_REPO_ROOT/start_autotagger_w_args.sh"
SHOW_LARGE_FILES_SCRIPT="$YTRIPPER_REPO_ROOT/scripts/show_large_files.sh"

_run_from_repo_root() {
    local script_path="$1"
    shift
    (cd "$YTRIPPER_REPO_ROOT" && bash "$script_path" "$@")
}

_resolve_tag_directory() {
    local helper_name="$1"
    shift

    if [ "$#" -gt 1 ]; then
        echo "Usage: $helper_name [directory]" >&2
        return 1
    fi

    if [ "$#" -eq 1 ]; then
        printf '%s\n' "$1"
        return 0
    fi

    if [ -n "$TAGDIR_DEFAULT_DIRECTORY" ]; then
        printf '%s\n' "$TAGDIR_DEFAULT_DIRECTORY"
        return 0
    fi

    printf '%s\n' "$PWD"
}

tagLoop() {
    _run_from_repo_root "$START_AUTOTAGGER_SCRIPT" --loop
}

tagStatus() {
    _run_from_repo_root "$START_AUTOTAGGER_SCRIPT" status
}

tagRun() {
    _run_from_repo_root "$START_AUTOTAGGER_SCRIPT" run
}

tagDir() {
    local directory
    directory="$(_resolve_tag_directory tagDir "$@")" || return 1
    _run_from_repo_root "$START_AUTOTAGGER_SCRIPT" scan-dir --directory "$directory" --scan-scope missing-any
}

tagDirFast() {
    local directory
    directory="$(_resolve_tag_directory tagDirFast "$@")" || return 1
    _run_from_repo_root "$START_AUTOTAGGER_SCRIPT" scan-dir --directory "$directory" --scan-scope missing-any --no-enrich
}

tagDirAll() {
    local directory
    directory="$(_resolve_tag_directory tagDirAll "$@")" || return 1
    _run_from_repo_root "$START_AUTOTAGGER_SCRIPT" scan-dir --directory "$directory" --scan-scope all
}

tagApply() {
    if [ "$#" -ne 1 ]; then
        echo "Usage: tagApply <tag_suggestions.csv>" >&2
        return 1
    fi
    _run_from_repo_root "$START_AUTOTAGGER_SCRIPT" apply-csv --csv "$1" --overwrite-mode missing
}

# PythonRipper setup
ytf() {
    _run_from_repo_root "$START_W_ARGS_SCRIPT" -f "$1"
}

ytp() {
    ytf "$YTF_DEFAULT_FILE"
}

ytl() {
    _run_from_repo_root "$START_W_ARGS_SCRIPT" -l
}

alias ytl-h='ytl --help'

slf() {
    "$SHOW_LARGE_FILES_SCRIPT" "$@"
}

alias slf-h='slf --help'
