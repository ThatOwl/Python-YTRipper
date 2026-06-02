#!/usr/bin/env python3
"""Double video duration by concatenating each file with itself.

Execution hints:
- Requires `ffmpeg` available on PATH.
- Input: one directory containing video files.
- Output: sibling directory named `<input_dir>_longer`.
- Track tag: if filename ends with `_<number>` (e.g. `example_14.mp4`),
  writes metadata `track=<number>` on the output file.
- Repair mode: `--repair-tags` edits files in `<input_dir>` in place.
    It reads existing `track` metadata and only retags files where it is missing,
    using the same `_<number>` filename rule.

Usage:
    python3 scripts/extend_videos_longer.py /path/to/input_dir
        python3 scripts/extend_videos_longer.py /path/to/input_dir --repair-tags

Example:
    python3 scripts/extend_videos_longer.py /mnt/d/videos
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi"}
TRACK_SUFFIX_RE = re.compile(r"_(\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create doubled-duration copies of videos in <input_dir> by concatenating "
            "each file with itself. Output folder is <input_dir>_longer."
        )
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing video files")
    parser.add_argument(
        "--repair-tags",
        action="store_true",
        help=(
            "Repair mode: in <input_dir>, read existing track tag and retag only files "
            "where track is missing, using filename suffix _<number>."
        ),
    )
    return parser.parse_args()


def extract_track_number(stem: str) -> str | None:
    match = TRACK_SUFFIX_RE.search(stem)
    return match.group(1) if match else None


def build_concat_list_file(video_path: Path) -> Path:
    temp_file = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt")
    temp_path = Path(temp_file.name)
    escaped = str(video_path.resolve()).replace("'", "'\\''")
    temp_file.write(f"file '{escaped}'\n")
    temp_file.write(f"file '{escaped}'\n")
    temp_file.flush()
    temp_file.close()
    return temp_path


def run_ffmpeg_concat(input_video: Path, output_video: Path, track: str | None) -> None:
    list_file = build_concat_list_file(input_video)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
    ]
    if track is not None:
        cmd.extend(["-metadata", f"track={track}"])
    cmd.append(str(output_video))

    try:
        subprocess.run(cmd, check=True)
    finally:
        list_file.unlink(missing_ok=True)


def read_track_tag(video_path: Path) -> str | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format_tags=track",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def apply_track_tag_in_place(video_path: Path, track: str) -> None:
    with tempfile.NamedTemporaryFile(
        "wb", delete=False, suffix=video_path.suffix, dir=str(video_path.parent)
    ) as tmp:
        temp_output = Path(tmp.name)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-map",
        "0",
        "-c",
        "copy",
        "-metadata",
        f"track={track}",
        str(temp_output),
    ]

    try:
        subprocess.run(cmd, check=True)
        temp_output.replace(video_path)
    finally:
        temp_output.unlink(missing_ok=True)


def repair_missing_tags(videos: list[Path]) -> int:
    repaired = 0
    skipped_with_tag = 0
    skipped_no_suffix = 0
    failed = 0

    for video in videos:
        existing_track = read_track_tag(video)
        if existing_track is not None:
            skipped_with_tag += 1
            print(f"KEEP {video.name} (existing tag: {existing_track})")
            continue

        track = extract_track_number(video.stem)
        if track is None:
            skipped_no_suffix += 1
            print(f"SKIP {video.name} (no _<number> suffix)")
            continue

        try:
            apply_track_tag_in_place(video, track)
            repaired += 1
            print(f"RETAG {video.name} (tag: {track})")
        except subprocess.CalledProcessError:
            failed += 1
            print(f"FAIL {video.name}", file=sys.stderr)

    print(
        f"Repair summary: repaired={repaired}, kept={skipped_with_tag}, "
        f"no_suffix={skipped_no_suffix}, failed={failed}"
    )
    return 0 if failed == 0 else 1


def main() -> int:
    args = parse_args()

    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH", file=sys.stderr)
        return 1
    if shutil.which("ffprobe") is None:
        print("ERROR: ffprobe not found in PATH", file=sys.stderr)
        return 1

    input_dir = args.input_dir.expanduser().resolve()
    if not input_dir.is_dir():
        print(f"ERROR: input_dir is not a directory: {input_dir}", file=sys.stderr)
        return 1

    videos = sorted(
        p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    )

    if not videos:
        print(f"No supported video files found in: {input_dir}")
        return 0

    if args.repair_tags:
        print(f"Repair mode on: {input_dir}")
        print(f"Files:  {len(videos)}")
        return repair_missing_tags(videos)

    output_dir = input_dir.parent / f"{input_dir.name}_longer"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Files:  {len(videos)}")

    for video in videos:
        track = extract_track_number(video.stem)
        out_file = output_dir / video.name
        try:
            run_ffmpeg_concat(video, out_file, track)
            if track is None:
                print(f"OK  {video.name} -> {out_file.name} (tag: none)")
            else:
                print(f"OK  {video.name} -> {out_file.name} (tag: {track})")
        except subprocess.CalledProcessError:
            print(f"FAIL {video.name}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
