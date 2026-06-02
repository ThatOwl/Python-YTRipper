# Autotagger Subsystem

This document tracks the newer package-driven autotagging subsystem inside `Python-YTRipper`.

It complements:

- [README.md](README.md) for the main downloader
- [scripts/README_auto_tagging.md](scripts/README_auto_tagging.md) for legacy reference on the older standalone `python-autotagger.py`

## Goal

The current direction is to split autotagging into:

- a conservative embedded downloader feature
- a filesystem-backed background worker
- a richer standalone operator CLI
- shared tagging core modules reused by both

The downloader should stay simple and fast. Expert controls, repairs, inspection, and operator workflows should gradually move into the standalone autotagging tool.

## Current Temporary State

The subsystem is already usable in a temporary but real form.

Implemented pieces:

- tagging packages are emitted after downloads
- packages are persisted in `runtime/tagging/`
- a background worker can process queued packages asynchronously
- downloader and tagger can cooperate on one mutable results CSV for later manual review
- queue/session/event inspection is available from a standalone CLI
- standalone local-directory crawling can produce editable tag suggestion CSVs
- reviewed suggestion CSVs can be written back into the original files in place
- failed, skipped, and enriched jobs can be manually requeued
- selected jobs can be requeued and immediately reprocessed
- operator review decisions and manual overrides can be persisted
- simple session and queue repair suggestions are available

Still missing for a fuller standalone mode:

- manual approval / override persistence
- richer repair planning across sessions
- notes, operator comments, or review queues
- stronger batch workflows and summary dashboards
- a final stable user-facing command name

## Runtime Layout

```text
runtime/
  tagging/
    pending/
    processing/
    done/
    failed/
    reviews/
    events.jsonl
```

Queue placement and package state are intentionally separate concepts:

- directory says where the package currently lives
- `payload["state"]` says the current semantic state

Examples:

- `done/` may contain `written`, `skipped`, or `enriched`
- `failed/` contains `failed`
- `pending/` usually contains `prepared`

## Main Modules

Shared queue / worker core:

- [source/autotagging/runtime/package_builder.py](source/autotagging/runtime/package_builder.py)
- [source/autotagging/runtime/worker.py](source/autotagging/runtime/worker.py)
- [source/autotagging/runtime/event_logger.py](source/autotagging/runtime/event_logger.py)
- [source/autotagging/runtime/results_report.py](source/autotagging/runtime/results_report.py)

Standalone operator surface:

- [source/autotagging/standalone/app.py](source/autotagging/standalone/app.py)
- [source/autotagging/standalone/local_directory.py](source/autotagging/standalone/local_directory.py)
- [source/autotagging/standalone/reporting.py](source/autotagging/standalone/reporting.py)
- [source/autotagging/standalone/review_store.py](source/autotagging/standalone/review_store.py)
- [source/autotagging/standalone/repair_planner.py](source/autotagging/standalone/repair_planner.py)
- [source/run_tagging_worker.py](source/run_tagging_worker.py)

Core tagging helpers:

- [source/autotagging/core/title_normalizer.py](source/autotagging/core/title_normalizer.py)
- [source/autotagging/core/evidence_extractor.py](source/autotagging/core/evidence_extractor.py)
- [source/autotagging/core/candidate_resolver.py](source/autotagging/core/candidate_resolver.py)
- [source/autotagging/core/musicbrainz_enricher.py](source/autotagging/core/musicbrainz_enricher.py)
- [source/autotagging/core/tag_writer.py](source/autotagging/core/tag_writer.py)

## Current Matching Strategy

The current matching logic is intentionally layered:

- explicit YouTube music metadata wins immediately
- structured descriptions are treated as high-confidence evidence
  - `Provided to YouTube by ...`
  - `Single: ... / From the album: ...`
  - `Song: "..." by ...`
- uploader, keywords, and normalized title splits are combined for official uploads and collaborations
- fan-upload title hints are parsed conservatively for patterns like:
  - `Title by Artist`
  - contextual prefixes such as `Radio New Vegas - Title (Artist)`
  - reverse forms like `Title - Artist`
- weak candidates can be confirmed through a bounded MusicBrainz query plan instead of brute-forcing every combination

Current emphasis:

- avoid false positives where franchise or playlist context is mistaken for the artist
- improve hit rate on private/fan playlists when title and artist are both present somewhere in the source metadata

## Standalone CLI

Quick DAU/operator notes before the command list:

- Use `python3` here, not `python`, unless your local environment already maps `python` correctly.
- `runtime/tagging/` is the working area.
  - `pending` = waiting
  - `processing` = worker is handling it
  - `done` = finished package file
  - `failed` = worker failure
  - `reviews` = saved operator notes / overrides
  - `events.jsonl` = activity log
- One subtle but important detail:
  - `done` is a queue folder, not a success state
  - logical states inside `done/` can still be `written`, `skipped`, or `enriched`

Current launcher:

```bash
./start_autotagger_w_args.sh <command> [options]
```

Windows PowerShell equivalent:

```powershell
.\start_autotagger_w_args.ps1 <command> [options]
```

Direct Python entrypoint:

```bash
python3 source/run_tagging_worker.py <command> [options]
```

It can also run in an interactive prompt loop like the main downloader CLI:

```bash
./start_autotagger_w_args.sh
./start_autotagger_w_args.sh --loop
python3 source/run_tagging_worker.py
python3 source/run_tagging_worker.py --loop
```

Opinionated shell helpers for the most common paths live in `microtools/shell_aliases.sh`:

- `tagDir [directory]`
  - scan missing metadata and keep MusicBrainz confirmation enabled
- `tagDirFast [directory]`
  - same as `tagDir` but skip MusicBrainz for a quicker first pass
- `tagDirAll [directory]`
  - scan everything in the directory, including already-tagged files
- `tagApply <csv>`
  - apply reviewed suggestions back into the source files with safe `missing` overwrite mode
- `tagLoop`
  - open the standalone autotagger prompt
- `tagStatus`
  - inspect current queue state

Available commands:

- `run`
  - run the background worker until idle
- `status`
  - inspect queue counts and recent packages
- `session`
  - inspect one session’s package summaries
- `events`
  - inspect recent lifecycle events
- `review-list`
  - inspect packages that likely need operator attention
- `review-override`
  - persist manual artist/title/album overrides for one job
- `review-approve`
  - persist an approval decision for one job
- `review-reject`
  - persist a rejection decision for one job
- `plan-session`
  - suggest follow-up actions for one session
- `plan-queue`
  - suggest queue-level operator actions
- `retry`
  - requeue matching packages back to `pending`
- `retry-run`
  - requeue matching packages and process just those packages immediately
- `scan-dir`
  - crawl one local directory tree and write an editable tag suggestion CSV
- `apply-csv`
  - read a reviewed suggestion CSV and write tags back into the original files in place

Examples:

```bash
python3 source/run_tagging_worker.py status
python3 source/run_tagging_worker.py session --session-id <session-id>
python3 source/run_tagging_worker.py events --event-type candidate_resolved --limit 20
python3 source/run_tagging_worker.py review-list
python3 source/run_tagging_worker.py review-override --job-id <job-id> --artist "Artist" --title "Title"
python3 source/run_tagging_worker.py review-approve --job-id <job-id> --note "ready to retry"
python3 source/run_tagging_worker.py review-reject --job-id <job-id> --reason "needs manual research"
python3 source/run_tagging_worker.py plan-session --session-id <session-id>
python3 source/run_tagging_worker.py plan-queue
python3 source/run_tagging_worker.py retry --job-id <job-id>
python3 source/run_tagging_worker.py retry --session-id <session-id> --source-state skipped
python3 source/run_tagging_worker.py retry-run --job-id <job-id>
python3 source/run_tagging_worker.py scan-dir --directory /mnt/d/Music/Rammstein
python3 source/run_tagging_worker.py apply-csv --csv /mnt/d/Music/Rammstein/2026-05-19_Rammstein_tag_suggestions.csv
```

Output defaults to CSV for human-readable terminal usage. JSON remains available where useful.

## Local Directory CSV Workflow

The standalone autotagger can now work directly on a local music directory without using the downloader queue.

`scan-dir`:

- walks one root recursively
- inspects supported files in place
- skips already-tagged files by default
- uses filename, folder context, and optional MusicBrainz confirmation to propose tags
- writes one CSV with both current values and proposed values

The main editable columns are:

- `artist_to_write`
- `title_to_write`
- `album_to_write`
- `apply_mode`

The main diagnostic columns are:

- `suggestion_source`
- `suggestion_confidence`
- `suggestion_reason`

`apply-csv`:

- reads the edited CSV back
- writes only rows whose `apply_mode` is set to a write-like value such as `write`
- updates the same CSV with `write_status`, `write_details`, `written_artist`, and `written_title`
- writes tags directly into the original files
- never creates copy targets or staging directories

## Standalone CLI Walkthrough

The standalone autotagger is an operator CLI around a filesystem queue.

1. Check whether anything is in the queue.

```bash
python3 source/run_tagging_worker.py status
```

Why: this is the safest first command; it shows counts plus recent items.

2. If you only want counts, reduce noise.

```bash
python3 source/run_tagging_worker.py status --view counts
```

Why `--view counts`: quick health check.
What it does: hides the recent-item table.

3. If you want machine-readable output, switch format.

```bash
python3 source/run_tagging_worker.py status --format json
```

Why `--format json`: easier to script or inspect precisely.
What it does: prints structured JSON instead of CSV.

4. If a session ID appears in `status`, inspect that session only.

```bash
python3 source/run_tagging_worker.py session --session-id <session-id>
```

Why `--session-id`: narrows to one batch/run.
What it does: shows only packages from that session.

5. See which items likely need human attention.

```bash
python3 source/run_tagging_worker.py review-list
```

Why: this is the “what should I look at next?” command.
What it does: lists `failed`, `skipped`, and `enriched` items by default.

6. Narrow review output if needed.

```bash
python3 source/run_tagging_worker.py review-list --states skipped
```

Why `--states`: focus on one problem type.
What it does: filters review candidates by terminal tag state.

7. Inspect recent activity when a result feels unclear.

```bash
python3 source/run_tagging_worker.py events --limit 20
```

Why `--limit`: keeps output readable.
What it does: shows the newest worker lifecycle events.

8. Filter events to one job or one event type.

```bash
python3 source/run_tagging_worker.py events --job-id <job-id>
python3 source/run_tagging_worker.py events --event-type candidate_resolved
```

Why: faster debugging.
What it does: trims the event log to the thing you care about.

9. Save a manual override for a job.

```bash
python3 source/run_tagging_worker.py review-override --job-id <job-id> --artist "Artist" --title "Title"
```

Why `--artist` / `--title` / `--album`: store the fields you want to correct.
What it does: writes a review file under `runtime/tagging/reviews/`.

10. Record a review decision.

```bash
python3 source/run_tagging_worker.py review-approve --job-id <job-id> --note "looks good"
python3 source/run_tagging_worker.py review-reject --job-id <job-id> --reason "needs manual research"
```

Why: useful operator bookkeeping.
What it does: saves approval/rejection metadata for that job.

11. Dry-run a retry before changing anything.

```bash
python3 source/run_tagging_worker.py retry --job-id <job-id> --dry-run
```

Why `--dry-run`: DAU-safe preview.
What it does: shows what would be requeued without moving files.

12. Actually requeue it.

```bash
python3 source/run_tagging_worker.py retry --job-id <job-id>
```

Why: moves the package back to `pending`.
What it does: prepares it for worker processing again.

13. Requeue and process immediately in one shot.

```bash
python3 source/run_tagging_worker.py retry-run --job-id <job-id>
```

Why: quickest operator loop.
What it does: requeues the package and runs the worker on just that item.

14. Run the worker normally.

```bash
python3 source/run_tagging_worker.py run
```

Why: processes anything sitting in `pending`.
What it does: polls until the queue stays idle, then exits.

15. Tune worker behavior if needed.

```bash
python3 source/run_tagging_worker.py run --poll-interval 1 --idle-timeout 30
```

Why `--poll-interval`: how often to check `pending`.
Why `--idle-timeout`: how long to wait before exiting when no more work appears.

## Shared Flag Reasoning

`--queue-dir <path>`

Use this only if your queue is not the default `runtime/tagging/`.
It points every command at another queue root.

`--format csv|json`

`csv` is easier for humans in terminal.
`json` is better for scripting or exact field inspection.

`--session-id`

Use when you want one batch/run only.
It avoids mixing unrelated jobs.

`--job-id`

Use when you want one exact package only.
It is the most precise retry/review target.

## State Meanings That Matter

`written` means tags were actually written.
`skipped` means the worker chose not to write because confidence was not safe enough.
`enriched` means enrichment found something, but it still did not auto-write.
`failed` means processing itself failed.

## Logged Events

The event log is append-only JSONL in `runtime/tagging/events.jsonl`.

Currently emitted event types include:

- `package_prepared`
- `state_transition`
- `package_recovered`
- `package_pruned`
- `package_requeued`
- `worker_started`
- `worker_idle_exit`
- `title_normalized`
- `candidate_resolved`
- `candidate_enrichment_missed`
- `candidate_enriched`
- `tag_write_not_requested`
- `tag_write_skipped`
- `tag_write_succeeded`
- `tag_write_failed`

Each package-scoped event carries stable operator identifiers like:

- `job_id`
- `session_id`
- `sequence_no`
- `state`
- `final_output_path`
- `source_url`

## Shared Results CSV

When result saving is enabled, the downloader owns the CSV file and writes one row per attempted entry, including download failures.

When autotagging is enabled:

- `save_results` is forced on
- successful downloads that produced a tagging package are linked to a `job_id`
- the background worker later updates that same row instead of appending a duplicate

The current CSV is intentionally compact and review-oriented. It includes:

- original source fields such as URL, uploader, and title
- local file path when a download succeeded
- download status and download errors
- terminal tag state such as `written`, `skipped`, `enriched`, `failed`, or `queue_failed`
- resolved artist/title/album when present
- resolver / enrichment provenance such as candidate source, confidence, and MusicBrainz source
- a compact machine-oriented failure reason for manual follow-up

## Planned Standalone Classes

The newer standalone code now includes explicit operator classes in [source/autotagging/standalone/app.py](source/autotagging/standalone/app.py), [source/autotagging/standalone/review_store.py](source/autotagging/standalone/review_store.py), and [source/autotagging/standalone/repair_planner.py](source/autotagging/standalone/repair_planner.py).

Implemented now:

- `TaggingStandaloneService`
  - current high-level operator actions and reports
- `TaggingStandaloneCLI`
  - parser and command dispatch

- `TaggingReviewStore`
  - persists approval, rejection, note, and override metadata
- `TaggingRepairPlanner`
  - generates conservative follow-up suggestions from queue and review state

## What Is Still Missing

The biggest missing functional areas are:

- review queue for ambiguous packages
- automatic application of saved manual overrides during retry/write flows
- “approve and write” or “override and retry” workflows
- session-level repair suggestions
- export/import of operator decisions
- richer batch reporting across many sessions

## Design Notes

- The downloader should not carry expert-mode autotagger flags forever.
- Package JSON is the main inter-process contract.
- Queue state should be debuggable on disk without hidden process memory.
- Event history should explain why a package ended up in `failed`, `skipped`, or `enriched`.
- Standalone tooling should grow toward operator workflows, not just raw helper commands.
- Temporary top-level wrapper modules remain under `source/autotagging/` for compatibility while imports migrate to the new `core`, `runtime`, and `standalone` subpackages.

## Current Caveats

- `review-override`, `review-approve`, and `review-reject` already persist operator metadata, notes, and override fields.
- Today, those saved overrides are not yet automatically consumed by the worker during `retry` / `retry-run`.
- So right now:
  - review persistence is real and useful for operator tracking
  - automatic “override and retry writes with the saved manual fields” is not finished yet
- This is worth calling out clearly for DAU workflows so people do not assume override persistence already equals override application.
