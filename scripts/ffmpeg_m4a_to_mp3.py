#!/usr/bin/env python3
"""
m4a_to_mp3.py

Convert all .m4a files in a given directory to .mp3 using ffmpeg-python,
encoding explicitly with the libmp3lame codec.

USAGE (Linux CLI):
    python3 ffmpeg_m4a_to_mp3.py /path/to/directory

REQUIREMENTS:
    - ffmpeg installed and available in PATH
      (e.g. sudo apt install ffmpeg)
    - ffmpeg-python installed:
      pip install ffmpeg-python

NOTES:
    - Uses a safe temp-file pattern (.tmp → replace on success)
    - Original .m4a files are deleted after successful conversion
    - Output files are written in the same directory
"""

import sys
import os
from pathlib import Path
import ffmpeg


def convert_file(input_path: Path, output_path: Path):
    """
    Convert a single .m4a file to .mp3 using libmp3lame.
    Uses a temporary file to avoid partial/corrupt outputs.
    """

    # Ensure correct extension
    output_path = output_path.with_suffix(".mp3")

    # Temporary output file
    temp_output = output_path.with_name(output_path.stem + ".tmp.mp3")

    audio_input = ffmpeg.input(str(input_path))

    try:
        (
            ffmpeg
            .output(
                audio_input,
                str(temp_output),
                acodec="libmp3lame",   # explicit codec (important)
                audio_bitrate="160k",  # fixed target bitrate
            )
            .run(
                capture_stdout=True,
                capture_stderr=True,
                overwrite_output=True,
                quiet=True,
            )
        )

        # Replace original safely
        input_path.unlink()  # remove source file
        os.replace(temp_output, output_path)

        print(f"[OK] {input_path.name} -> {output_path.name}")

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        print(f"[ERROR] {input_path.name}")
        print(stderr)

        # Cleanup temp file if failed
        if temp_output.exists():
            temp_output.unlink()


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 m4a_to_mp3.py /path/to/directory")
        sys.exit(1)

    directory = Path(sys.argv[1])

    if not directory.is_dir():
        print(f"Error: '{directory}' is not a valid directory.")
        sys.exit(1)

    for file in directory.iterdir():
        if file.suffix.lower() == ".m4a":
            output_file = file.with_suffix(".mp3")
            convert_file(file, output_file)


if __name__ == "__main__":
    main()