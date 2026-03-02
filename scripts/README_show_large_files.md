# show_large_files.sh

Scan a directory tree for long media files and report them by duration/size/name.

## What it does

- Recursively scans for `.mp3`, `.m4a`, `.mp4`
- Uses `ffprobe` to read duration
- Keeps files longer than a threshold (default: 8 minutes)
- Supports parallel probing (`xargs -P`)
- Outputs to console, text file, and/or CSV

## Usage

```bash
./scripts/show_large_files.sh [options] [rootdir]
```

If `rootdir` is omitted, current directory is scanned.

## Options

- `-c`, `--console` : print to console (colorized when TTY)
- `-t`, `--text` : write `<YYYY_MM_DD>_<root>_Large-Files.txt`
- `-v`, `--csv` : write `<YYYY_MM_DD>_<root>_Large-Files.csv`
- `-m <minutes>` : minimum duration in minutes (default: `8`)
- `-s <field>` : sort by `duration` | `size` | `name` (default: `duration`)
- `-p <jobs>` : parallel ffprobe jobs (default: ~half CPU cores)
- `--info` : print environment/dependency info
- `-h`, `--help` : show help

## Examples

```bash
# Console only
./scripts/show_large_files.sh --console /mnt/d/Musik

# Text + CSV outputs, minimum 20 min, sorted by size
./scripts/show_large_files.sh -t --csv -m 20 -s size /mnt/d/Musik

# Use helper alias/function (if shell aliases are loaded)
slf --console /mnt/d/Musik
slf-h
```

## Dependency

- `ffprobe` (from `ffmpeg`) must be available on `PATH`
