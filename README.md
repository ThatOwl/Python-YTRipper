# Python-YTRipper
Small project implementing an external API for downloading YT videos. For private use and shall included minimal interface.

## Prerequisites

- Python 3.11+ recommended
- ffmpeg (system binary)

This project uses ffmpeg via the ffmpeg-python wrapper. You must have the ffmpeg executable installed on your system.

### Windows setup (quick)

1) Download a static build of ffmpeg for Windows:
	- https://www.gyan.dev/ffmpeg/builds/#release-builds (get the full or essentials zip)
2) Extract it, e.g. to `C:\ffmpeg` so the binary is at `C:\ffmpeg\bin\ffmpeg.exe`.
3) Add `C:\ffmpeg\bin` to your PATH, or set one of these environment variables before running:
	- `FFMPEG_BINARY` = full path to ffmpeg.exe (e.g. `C:\ffmpeg\bin\ffmpeg.exe`)
	- `FFMPEG_PATH` = directory containing ffmpeg.exe (e.g. `C:\ffmpeg\bin`)

The code will try in this order: FFMPEG_BINARY (file) -> FFMPEG_PATH (directory) -> PATH lookup.

Verify from PowerShell:

```powershell
# If added to PATH
where.exe ffmpeg

# Or set just for the session
$env:FFMPEG_BINARY = 'C:\ffmpeg\bin\ffmpeg.exe'; ffmpeg -version
```

If ffmpeg is not found, conversions/merges will fail with a clear log message.

## Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## Run manual test

```powershell
python .\tests\manual_testing.py
```

Logs are written under `./logs`.
