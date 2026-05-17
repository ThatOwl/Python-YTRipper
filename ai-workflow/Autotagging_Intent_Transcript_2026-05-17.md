# Autotagging Intent Transcript — 2026-05-17

This document captures the user/assistant conversation that established the current direction for `python-autotagger`, embedded tagging in `ytripper`, and the future split between the main downloader and a dedicated tagging tool.

## Transcript

### User

how does the enrich threshold and its core mechanisms work togethere with the local metadata writting?

in python-autotagger

### Assistant

In `python-autotagger`, the enrich threshold and the local metadata write step are related, but they are not the same gate.

The key split is:

- `CONFIDENCE_THRESHOLD = 85` is the normal write threshold in Phase 2.
- `--conf-ceiling` also defaults to `85`, but it controls which rows get MusicBrainz enrichment in Phase 1.5, not which rows get written locally.

So the default behavior is:

1. Phase 1 parses filenames/folders and assigns `Confidence`.
2. `--enrich` queries MusicBrainz only for rows with `Confidence < 85`.
3. Enrichment does not change the `Confidence` field. It only adds `MB_*` columns plus review metadata.
4. Phase 2 local writing still filters with `Confidence >= 85` unless `--mb-only` is used.

Important consequence:

- A low-confidence row that gets a strong MusicBrainz match will still not be written by normal `--write`, because its original `Confidence` is still below `85`.
- That low-confidence enriched row only becomes writable automatically with `--mb-only`, because in that mode `MB_Score` becomes the gate and confidence is bypassed.

### User

yes proceed

### Assistant

Practical behavior for the three common combinations:

- `--enrich --write`
  - enriches only rows with `Confidence < 85`
  - writes only rows with `Confidence >= 85`
  - enrichment does not rescue low-confidence rows into Phase 2
- `--enrich-all --write`
  - enriches every row
  - still writes only rows with `Confidence >= 85`
  - improves metadata choice for rows that already qualify
- `--enrich-all --write --mb-only`
  - enriches every row
  - writes only rows with a MusicBrainz match
  - confidence is bypassed entirely

Short model:

- `--enrich`: who should be queried
- `--write`: who is allowed to be copied and tagged
- `--mb-only`: switch the write gate from confidence to MB match

### User

I want you to either improve this code or completely pivot with a new system.

1 this tool will be its own little tool with cli
2 the best automation option will be moved to a class into the app (simply switched on or off -> if the user want options, they can use the tool instead of the embedded option -> cli will get too large as well as options maintainance)

=> goal is that the most common formats of video titles will be properly cleaned and "chopped" SInce they turn into our only (i do not think we can get any yt-metadata which helps?) source of truth for later comparison / mb-lookup
=> if my application (architecture ! - not present feature!) can assist in making that source of truth pool larger (other lookups when downloading+embedding) also lokk at that
=> generally start with planning, research not directly coding

### Assistant

Research and architecture findings:

- The current `python-autotagger.py` contains useful heuristics, but it is too monolithic to become both a maintainable standalone tool and an embedded app feature.
- The main downloader already exposes an `autotag` switch in config/CLI, but no real behavior is implemented yet.
- `DownloadOrchestrator` is the correct seam for a future embedded on/off metadata service because it already owns the finished output path and the `video_obj`.
- The ffmpeg/media pipeline already has a structured output-profile layer that can later carry embedded textual metadata, not just artwork.

Metadata/source-of-truth findings:

- The app already accesses `video.title`, `video.author`, `video.description`, and `video.thumbnail_url`.
- `pytubefix` can also expose richer fields such as `channel_id`, `captions`, `chapters`, `publish_date`, `vid_details`, `vid_info`, and a `metadata` property that may contain music-style fields when YouTube provides them.

Recommendation:

- Pivot the architecture, but keep the proven heuristics.
- Build a shared tagging core reused by:
  - a standalone advanced autotag CLI
  - a conservative embedded app service behind a simple on/off switch

Suggested shared components:

- `VideoMetadataSnapshot`
- `TitleNormalizer`
- `EvidencePoolBuilder`
- `CandidateExtractor`
- `MatchResolver`
- `MusicBrainzEnricher`
- `TagWriter`
- `AutotagAutomationService`

Suggested migration path:

1. Extract title-cleaning and parsing heuristics into reusable classes.
2. Add download-time metadata snapshot capture.
3. Implement conservative embedded automation behind `options.autotag`.
4. Rebuild the standalone CLI on top of the shared core.

### User

this is very strong. keep this!

First lets continue talking about architecture and app behaviour.

=> this app (ytripper)
1 will later get a web ui (progress updates, states, final reults passing + visulaization, OS interaction paths naming etc)
2 currently needs time to process convert/combine with ffmpeg ...
resulting in larger playlist downloads taking long (speedup ideas appreciated GPU or multicore possible?)

The time needed currently is "ok" (sufficient) but mb lookups take really long, which i do not mind if they run in the background. Stopping the main downloader however limits speed way too much.

My idea(s):
1 i will not separate ffmpeg tasks as they naturally limit yt access-rate -> stopping bot-protection from detecting it easily (works rather great up until ~300 - 500 downloads in one go)
2 restrucutre MOST everything like you said for autotagging -> however, when autotagging is turned on:
a) in some way a child process is spawned which gets (in some way) the current queue as e.g. packages (path + meta-json (+ video-obj or smth else?)) and works thorugh them. (json cleanup handled by ?)
b) add a second cli flag "prepare_tagging" which just creates the jsons and user (probably experts) can user separate tool, like our autotagger (to be -application XD)

with this in mind fuirther discuss.

### Assistant

Direction:

- Decouple autotagging from the downloader, but do not pass live Python objects across the boundary.
- Keep ffmpeg inline in the main flow.
- After each final file exists, emit a persisted tagging work package for a background worker.

Important boundary:

- Do not send `video_obj` to a child process.
- Use a serialized package only.

Recommended package contents:

- `job_id`
- `download_id` / `playlist_id`
- `final_output_path`
- `container`
- `created_at`
- `source_url`
- `video_id`
- `raw_title`
- `author`
- `playlist_title`
- `description`
- `publish_date`
- `thumbnail_path` or `thumbnail_url`
- `youtube_metadata`
- `captions_available`
- `chapters`
- `existing_embedded_tags`
- `normalization_version`

Recommended runtime model:

1. downloader fetches streams
2. ffmpeg combine/convert runs inline
3. final file is written
4. tagging package JSON is persisted
5. background tagging worker picks it up later

Recommended queue shape:

- `runtime/tagging/pending/*.json`
- `runtime/tagging/processing/*.json`
- `runtime/tagging/done/*.json`
- `runtime/tagging/failed/*.json`

Recommended package/job states:

- `prepared`
- `queued`
- `processing`
- `enriched`
- `written`
- `failed`
- `skipped`

CLI behavior recommendation:

- `--autotag`
  - download normally, then queue background tagging work automatically
- `--prepare-tagging`
  - do not run the worker, only emit tagging packages/sidecars

Why this matches the future web UI:

- explicit job/state objects
- easy progress/state visualization
- clear final artifacts and error states
- no need for the UI to infer truth from logs

Performance recommendation:

- keep ffmpeg inline for now
- make tagging fully async
- evaluate GPU/multicore ffmpeg tuning later
- prioritize stream-copy and no-transcode opportunities before aggressive parallelization

Suggested service split:

- `DownloadOrchestrator`
- `TaggingPackageBuilder`
- `TaggingWorker`

### User

copy this whole conversation into ai-workflow, as documentaion of intent.
do the architect sketch.
afterwards not now, focus on this (smaller) task - start with implementation (like you portrait in your last two answeres - STRONG!)

comment: cpu multicore / gpu will probabily be implemented lateron for ffmpeg, since this tool is also used for ~2h 1080p video downloads, and when bot-detection can be tricked the ffmpeg-process-speed will be tuned to maximum

## Working Note

The implementation immediately following this document begins with the smallest structurally-correct slice of that direction:

- add a shared tagging package boundary
- add `--prepare-tagging`
- persist package JSON from the downloader
- keep the actual background worker for a later slice
