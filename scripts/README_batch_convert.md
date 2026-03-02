# run_batch_convert.sh + batch_convert_audio.py

Wrapper + Python converter for recursive `.m4a` audio conversion.

## Components

- `scripts/run_batch_convert.sh`
  - Creates temporary virtualenv
  - Installs `ffmpeg-python`
  - Runs `batch_convert_audio.py`
  - Removes venv on exit
- `scripts/batch_convert_audio.py`
  - Recursively finds `.m4a`
  - Probes source bitrate via `ffprobe`
  - Re-encodes to target format (`m4a` or `mp3`)
  - Uses safe temp output file and atomic replace

## Recommended usage

```bash
./scripts/run_batch_convert.sh <directory> [--format m4a|mp3] [--dry-run]
```

## Direct Python usage

```bash
python3 ./scripts/batch_convert_audio.py <directory> [--format m4a|mp3] [--dry-run]
```

## Options (batch_convert_audio.py)

- positional `directory` : root folder to process
- `-f`, `--format` : `m4a` (default) or `mp3`
- `--dry-run` : list planned conversions only

## Behavior notes

- Input scan is currently `*.m4a` only
- `--format m4a` performs in-place re-encode (via temp file then replace)
- `--format mp3` writes `.mp3` and removes original `.m4a` after successful conversion
- Bitrate target is selected from a standard ladder (`64, 96, 128, 160, 192, 256, 320`) using next-higher source tier

## Dependencies

- `python3` + `python3-venv`
- `ffmpeg` / `ffprobe` on `PATH`
- `ffmpeg-python` (installed automatically by wrapper)
