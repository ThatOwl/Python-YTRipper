#!/usr/bin/env python3
"""Batch convert all .m4a files in a directory tree to AAC (.m4a) or MP3.

Usage (standalone – no prior setup needed):
    ./scripts/run_batch_convert.sh /path/to/music
    ./scripts/run_batch_convert.sh /path/to/music --format mp3
    ./scripts/run_batch_convert.sh /path/to/music --dry-run

The wrapper creates a temporary venv, installs ffmpeg-python, runs this
script, and cleans everything up afterwards.

Or run directly if ffmpeg-python is already installed:
    python3 ./scripts/batch_convert_audio.py /path/to/music [--format m4a|mp3] [--dry-run]

Requirements:
    - python3 (with venv module)
    - ffmpeg / ffprobe on PATH
"""
import os
import sys
import argparse
from pathlib import Path

import ffmpeg as fpg

# Standard audio bitrate ladder (kbps) — pick the next one up from the source
STANDARD_BITRATES = [64, 96, 128, 160, 192, 256, 320]


def probe_bitrate(audio_path: Path) -> int | None:
    """Return the audio bitrate in kbps by probing with ffprobe, or None on failure."""
    try:
        info = fpg.probe(str(audio_path), select_streams="a:0")
        # bit_rate may live on the stream or the format level
        stream = info.get("streams", [{}])[0]
        raw = stream.get("bit_rate") or info.get("format", {}).get("bit_rate")
        if raw:
            return int(raw) // 1000  # bps → kbps
    except Exception:
        pass
    return None


def next_standard_bitrate(source_kbps: int) -> int:
    """Return the next-higher standard bitrate (ceiling), capped at 320k."""
    for std in STANDARD_BITRATES:
        if std >= source_kbps:
            return std
    return STANDARD_BITRATES[-1]


def convert_audio(audio_path: Path, output_format: str) -> None:
    """Convert a single audio file to the target format using a safe temp-file pattern.

    Args:
        audio_path:    Path to the source .m4a file.
        output_format: Target format – "m4a" or "mp3".
    """
    output_path = audio_path.with_suffix(f".{output_format}")
    temp_output = output_path.with_name(output_path.stem + ".tmp" + output_path.suffix)

    # Probe source bitrate and pick the next-higher standard tier
    source_kbps = probe_bitrate(audio_path)
    if source_kbps:
        target_kbps = next_standard_bitrate(source_kbps)
        bitrate_str = f"{target_kbps}k"
        print(f"    source ≈{source_kbps}k → encoding at {bitrate_str}")
    else:
        target_kbps = None
        bitrate_str = None
        print("    could not probe bitrate, falling back to VBR qscale")

    # Codec / quality settings per format
    if output_format == "m4a":
        codec_kwargs: dict = {"acodec": "aac"}
    else:  # mp3
        codec_kwargs = {"acodec": "libmp3lame"}

    if bitrate_str:
        codec_kwargs["audio_bitrate"] = bitrate_str
    else:
        codec_kwargs["qscale:a"] = 3  # VBR fallback

    audio_input = fpg.input(str(audio_path))

    try:
        (
            fpg
            .output(
                audio_input,
                str(temp_output),
                **codec_kwargs,
            )
            .run(
                capture_stdout=True,
                capture_stderr=True,
                overwrite_output=True,
                quiet=True,
            )
        )

        # Conversion succeeded — replace safely
        if output_format == "m4a":
            # In-place re-encode: remove original, move temp to same name
            audio_path.unlink()
        os.replace(temp_output, output_path)

        # If converting to mp3, the original .m4a is still there — remove it
        if output_format != "m4a" and audio_path.exists():
            audio_path.unlink()

        print(f"  ✅  {audio_path.name}  →  {output_path.name}")

    except Exception as e:
        stderr = getattr(e, "stderr", None)
        msg = stderr.decode().strip() if stderr else str(e)
        print(f"  ❌  {audio_path.name}  — {msg}")

        if temp_output.exists():
            temp_output.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recursively convert every .m4a file under a directory."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Root directory to walk.",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["m4a", "mp3"],
        default="m4a",
        help="Target format (default: m4a). "
             "m4a re-encodes to AAC; mp3 uses libmp3lame V0 (≈245 kbps VBR, near-transparent).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be converted without touching them.",
    )
    args = parser.parse_args()

    root = args.directory.resolve()
    if not root.is_dir():
        print(f"Error: '{root}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    files = sorted(root.rglob("*.m4a"))
    if not files:
        print("No .m4a files found.")
        return

    print(f"Found {len(files)} .m4a file(s) under {root}")
    print(f"Target format: {args.format}\n")

    if args.dry_run:
        for f in files:
            kbps = probe_bitrate(f)
            target = f"{next_standard_bitrate(kbps)}k" if kbps else "VBR"
            print(f"  {f.relative_to(root)}  (≈{kbps}k → {target})" if kbps else f"  {f.relative_to(root)}  (bitrate unknown)")
        return

    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {f.relative_to(root)}")
        convert_audio(f, args.format)

    print("\nDone.")


if __name__ == "__main__":
    main()
