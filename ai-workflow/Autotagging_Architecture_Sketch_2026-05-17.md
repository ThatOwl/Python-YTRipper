# Autotagging Architecture Sketch — 2026-05-17

## Intent

Split autotagging into:

- a conservative embedded app feature for `ytripper`
- a richer standalone autotagging tool/CLI
- a shared metadata/tagging core used by both

The downloader must not block on MusicBrainz enrichment. ffmpeg stays inline for now. Tagging becomes asynchronous and package-driven.

## Core Principles

- Keep YouTube download pacing and ffmpeg conversion/combine in the main process.
- Never pass live `pytubefix.YouTube` objects to child processes.
- Persist all inter-process handoff data as JSON packages.
- Treat package/job state as the source of truth for future web UI progress/state display.
- Keep the main downloader CLI small; expert controls belong in the standalone tool.

## High-Level Components

### Main App

- `DownloadOrchestrator`
  - fetches streams
  - runs ffmpeg combine/convert inline
  - produces final output file
  - emits tagging packages when requested

- `TaggingPackageBuilder`
  - extracts raw evidence from download-time context
  - serializes a stable JSON-safe package

- `TaggingQueueStore`
  - persists packages to queue directories
  - owns queue layout and state transitions at the filesystem level

### Shared Tagging Core

- `VideoMetadataSnapshot`
- `TitleNormalizer`
- `EvidencePoolBuilder`
- `CandidateExtractor`
- `MatchResolver`
- `MusicBrainzEnricher`
- `TagWriter`

### Background Worker

- `TaggingWorker`
  - consumes package JSON
  - enriches / resolves metadata
  - writes final tags
  - updates package state

### Standalone Tool

- advanced CLI over the shared tagging core
- owns expert flags, dry-runs, reports, overrides, and repair workflows

## Runtime Flow

### `--autotag`

1. Downloader finishes a file.
2. Downloader builds a tagging package.
3. Package is written into `runtime/tagging/pending/`.
4. A worker process can later consume it asynchronously.

### `--prepare-tagging`

1. Downloader finishes a file.
2. Downloader builds a tagging package.
3. Package is written into `runtime/tagging/pending/`.
4. No worker is required in this mode.
5. Expert users can run the standalone tagging tool later against the prepared packages.

## Queue Layout

```text
runtime/
  tagging/
    pending/
    processing/
    done/
    failed/
```

## Package States

- `prepared`
- `queued`
- `processing`
- `enriched`
- `written`
- `failed`
- `skipped`

The first implementation slice only needs `prepared` plus queue placement in `pending/`.

## Proposed Package Schema

```json
{
  "package_version": 1,
  "job_id": "uuid",
  "state": "prepared",
  "requested_actions": ["autotag"],
  "created_at": "2026-05-17T12:34:56Z",
  "final_output_path": "/abs/path/file.m4a",
  "download_directory": "/abs/path/downloads",
  "container": "m4a",
  "playlist_title": "Playlist Title",
  "source": {
    "url": "https://youtube.com/watch?v=...",
    "video_id": "...",
    "title": "raw youtube title",
    "author": "channel or artist-like author",
    "channel_id": "...",
    "publish_date": "2025-01-01",
    "thumbnail_url": "https://...",
    "description": "raw description",
    "keywords": ["..."],
    "metadata": "...",
    "captions_available": true,
    "chapters": [...]
  },
  "download_options": {
    "audio_only": true,
    "audio_mp3": false,
    "preferred_format": ""
  },
  "normalization": {
    "normalization_version": "yt-title-v1"
  }
}
```

The exact package can expand later, but the contract should stay JSON-safe and process-safe.

## Why Not Pass `video_obj`

- it is network-backed and runtime-specific
- it is not a stable process boundary
- it does not fit future web UI or daemonized worker models
- JSON packages are debuggable, durable, and replayable

## Web UI Alignment

This package/job model supports the future web UI naturally:

- progress updates
- current stage
- queue size
- final outputs
- failure states
- per-job inspection

The UI should read package states, not scrape logs.

## ffmpeg / Throughput Guidance

Current recommendation:

- keep ffmpeg in the main flow for now
- let it continue acting as a natural rate limiter for YouTube access
- make MB enrichment and richer autotagging asynchronous

Later options:

- stronger copy-vs-transcode optimization
- limited worker concurrency for tagging only
- GPU or multicore tuning for long video conversions

GPU / multicore ffmpeg tuning is explicitly deferred for a later performance slice.

## First Implementation Slice

1. Add a new shared `source/autotagging/` package.
2. Add queue/package models and JSON persistence.
3. Add `prepare_tagging` to downloader config and CLI.
4. Emit tagging packages from `DownloadOrchestrator` after successful file creation.
5. Reuse the same package boundary later for the worker and standalone autotag CLI.

## Follow-Up Slices

1. Background tagging worker process lifecycle.
2. Shared title normalization engine extraction from `python-autotagger.py`.
3. Evidence scoring and candidate resolution.
4. MusicBrainz enrichment moved onto package-driven worker flow.
5. Standalone advanced autotag CLI rebuilt on top of the shared core.
