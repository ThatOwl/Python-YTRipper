#!/usr/bin/env python3
"""Extract a frame at +0.5s and embed it as MP4 cover art metadata.

Examples:
    python3 scripts/embed_cover_at_half_second.py input.mp4
    python3 scripts/embed_cover_at_half_second.py /path/to/videos_dir
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


def run_cmd(cmd: list[str]) -> None:
    """Run a command and exit with a helpful message on failure."""
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc


def output_dir_for_input(input_path: Path) -> Path:
    """Build output dir path as <original>_w_coverart.

    For a directory input: /path/videos -> /path/videos_w_coverart
    For a file input:      /path/movie.mp4 -> /path/movie_w_coverart
    """
    if input_path.is_dir():
        return input_path.with_name(f"{input_path.name}_w_coverart")
    return input_path.with_name(f"{input_path.stem}_w_coverart")


def process_file(ffmpeg_path: str, input_file: Path, output_file: Path) -> None:
    """Extract frame at 0.5s and attach it as cover art for one MP4 file."""
    with tempfile.TemporaryDirectory(prefix="embed_cover_") as tmp_dir:
        # Unique filename is defensive; temp dir is already unique per file.
        cover_path = Path(tmp_dir) / f"cover_{uuid.uuid4().hex}.jpg"

        # Grab a single frame at +0.5 seconds from the start.
        run_cmd(
            [
                ffmpeg_path,
                "-y",
                "-ss",
                "0.5",
                "-i",
                str(input_file),
                "-map",
                "0:v:0",
                "-frames:v",
                "1",
                "-an",
                "-sn",
                "-dn",
                "-update",
                "1",
                str(cover_path),
            ]
        )

        # Map only the primary video stream from input, then add new cover art stream.
        # This avoids wrong cover assignment when source has extra video streams.
        run_cmd(
            [
                ffmpeg_path,
                "-y",
                "-i",
                str(input_file),
                "-i",
                str(cover_path),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-map",
                "0:s?",
                "-map",
                "1:v",
                "-map_metadata",
                "0",
                "-c:v:0",
                "copy",
                "-c:a",
                "copy",
                "-c:s",
                "copy",
                "-c:v:1",
                "mjpeg",
                "-disposition:v:1",
                "attached_pic",
                str(output_file),
            ]
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Add MP4 cover art at +0.5s.")
    parser.add_argument("input", type=Path, help="Path to source .mp4 or directory")
    args = parser.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        raise SystemExit(f"Input path does not exist: {input_path}")

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise SystemExit("ffmpeg not found on PATH")

    output_dir = output_dir_for_input(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        if input_path.suffix.lower() != ".mp4":
            raise SystemExit("Input file must be an .mp4 file")
        mp4_files = [input_path]
    else:
        mp4_files = sorted(p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() == ".mp4")

    if not mp4_files:
        raise SystemExit("No .mp4 files found to process")

    for mp4 in mp4_files:
        out_file = output_dir / mp4.name
        process_file(ffmpeg_path, mp4, out_file)
        print(f"Wrote: {out_file}")


if __name__ == "__main__":
    main()
