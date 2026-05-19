# FFmpeg Hardware Utilization

## Intent

This is a later performance slice, not a current project priority.

The goal is narrow:

- speed up clearly long-running ffmpeg jobs
- keep normal 3-5 minute videos unchanged
- preserve the current "ffmpeg as a natural request-rate limiter" behavior for short jobs
- avoid medium/high-risk refactors that destabilize the downloader

This matters most for cases like:

- playlists with many 45-60 minute items
- podcasts
- long-form archives
- training / dataset collection workflows

It matters much less for:

- short music tracks
- single normal-length YouTube videos
- copy-only mux jobs

## Project Constraints

The downloader supports different user intents under one roof, so optimization should be conservative.

Recommended guardrails:

- do not speed up short jobs by default
- do not add broad concurrency around ffmpeg right now
- do not add vendor-specific GPU assumptions as default behavior
- only optimize when there is a strong chance of meaningful savings

## What The Current Code Already Does Well

The current architecture already has a useful split:

- `DownloadOrchestrator` owns the job flow
- `MediaAssembler` resolves output intent into an `OutputProfile`
- `StreamConverter` owns ffmpeg graph construction and execution

Important current behavior:

- video output already avoids re-encoding when the selected video is H.264-like and the target is MP4
- audio output already avoids re-encoding when the selected audio is AAC-like and the target is M4A
- pure copy/mux paths should remain untouched, because they are not the expensive part

That means the real optimization target is not "all ffmpeg work".
It is specifically long transcode jobs.

## Main Recommendation

Do not implement the earlier "auto-add `-threads auto` for > 15 min" plan as-is.

Reasons:

- it threads duration through too many layers for limited proven benefit
- ffmpeg encoders already use threading in many cases
- a hardcoded 15-minute heuristic is too eager for this project
- GPU support is more complex than a simple `nvidia/amd/intel` switch

Instead, use a more conservative policy:

- target only long transcodes
- leave short jobs alone
- keep the default behavior unchanged
- make any hardware-heavy behavior opt-in or deferred until measured

## Recommended Long-Job Policy

Only consider acceleration when all of the following are true:

1. the job duration is known
2. the duration is above a clearly long threshold
3. the selected output profile requires real transcoding
4. the optimization path is supported by the local ffmpeg/runtime

Suggested starting threshold:

- default to 30 minutes for the first pass
- only lower this later if benchmarks show a clear win without harming the short-job flow

Rationale:

- 30 minutes is far away from the 3-5 minute "normal" case
- 45-60 minute playlist items still qualify
- this keeps the optimization focused on obvious heavy jobs

## Low-Risk Plan For This Codebase

### Phase 0: Measure First

Before changing behavior, add lightweight instrumentation around ffmpeg calls:

- wall-clock time for `convert_audio_new()`
- wall-clock time for `combine_streams_new()`
- whether the job was copy-only, audio transcode, or video transcode
- selected codecs from `OutputProfile`
- optional known media duration

Why this comes first:

- it shows where the real cost is
- it avoids tuning the wrong path
- it gives a baseline before any optimization work

### Phase 1: Add A Clean Policy Hook, But Keep It Off

Add a small policy decision point for long jobs, but keep default behavior unchanged.

Preferred shape:

- pass `job_duration_seconds` as optional job context from orchestrator-level code
- do not add duration directly to `StreamInfo`
- keep `StreamInfo` focused on stream metadata

Why:

- duration belongs to the overall media job more than to each downloaded stream fragment
- this avoids pushing job-level policy into low-level stream metadata

### Phase 2: Optimize Only Confirmed Transcode Paths

If a job qualifies as "long" and the profile actually transcodes:

- audio-only long transcodes may get their own tuning later
- video transcodes are the main likely win
- copy-only mux paths should stay exactly as they are

Important:

- do not change the normal short-video path
- do not change download concurrency
- do not change playlist pacing behavior

## GPU Guidance

GPU support should be treated as a later, explicit feature.

Not recommended for the first implementation:

- auto-detect vendor and silently switch encoders
- map `nvidia -> nvenc`, `amd -> amf`, `intel -> qsv` without runtime verification
- assume that a GPU path preserves the same output tradeoffs as software encoding

Recommended later approach:

- explicit opt-in
- explicit encoder choice or capability-checked mode
- only for long transcodes
- clear logging when hardware acceleration is requested but unavailable

If GPU support is added later, prefer a design closer to:

- `off`
- `long_job_cpu`
- `long_job_gpu`

or explicit encoder override values, rather than vague vendor names.

## CPU / Threads Guidance

Do not assume that adding `-threads auto` alone will produce a major improvement.

It may still be worth testing, but it should be treated as a benchmarked experiment, not the default first solution.

Why:

- encoder threading may already be happening
- the gain may be small compared with the implementation complexity
- long-job wins may come more from smarter encoder selection than from a single thread flag

## Suggested First Implementation Slice

If this gets worked on later, the first slice should stay small:

1. Add ffmpeg timing + structured logging.
2. Add optional `job_duration_seconds` plumbing at the job/service boundary.
3. Add a long-job policy helper that is default-off.
4. Keep all short jobs on the exact current path.
5. Add targeted tests around the policy decision, not just CLI parsing.

This first slice should not yet:

- add GPU CLI flags
- add automatic hardware detection
- add playlist-wide ffmpeg worker pools
- rewrite the ffmpeg integration layer

## What Success Looks Like

Success is not "ffmpeg uses more hardware everywhere".

Success is:

- short 3-5 minute jobs feel unchanged
- long 45-60 minute items process meaningfully faster when they require transcoding
- copy-only jobs stay stable
- default behavior remains predictable
- the code remains easy to reason about

## Decision

Recommended status for now:

- keep this as a deferred performance note
- when revisited, start with measurement
- optimize only long transcode cases
- preserve short-job pacing by default
