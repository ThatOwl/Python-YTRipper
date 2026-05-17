# Autotagger Subsystem

This document tracks the newer package-driven autotagging subsystem inside `Python-YTRipper`.

It complements:

- [README.md](README.md) for the main downloader
- [scripts/README_auto_tagging.md](scripts/README_auto_tagging.md) for the older standalone `python-autotagger.py`

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

Current entrypoint:

```bash
python source/run_tagging_worker.py <command> [options]
```

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

Examples:

```bash
python source/run_tagging_worker.py status
python source/run_tagging_worker.py session --session-id <session-id>
python source/run_tagging_worker.py events --event-type candidate_resolved --limit 20
python source/run_tagging_worker.py review-list
python source/run_tagging_worker.py review-override --job-id <job-id> --artist "Artist" --title "Title"
python source/run_tagging_worker.py review-approve --job-id <job-id> --note "ready to retry"
python source/run_tagging_worker.py review-reject --job-id <job-id> --reason "needs manual research"
python source/run_tagging_worker.py plan-session --session-id <session-id>
python source/run_tagging_worker.py plan-queue
python source/run_tagging_worker.py retry --job-id <job-id>
python source/run_tagging_worker.py retry --session-id <session-id> --source-state skipped
python source/run_tagging_worker.py retry-run --job-id <job-id>
```

Output defaults to CSV for human-readable terminal usage. JSON remains available where useful.

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
- persistent manual overrides
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
