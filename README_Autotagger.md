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
- queue/session/event inspection is available from a standalone CLI
- failed, skipped, and enriched jobs can be manually requeued
- selected jobs can be requeued and immediately reprocessed

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

- [source/autotagging/package_builder.py](source/autotagging/package_builder.py)
- [source/autotagging/worker.py](source/autotagging/worker.py)
- [source/autotagging/event_logger.py](source/autotagging/event_logger.py)
- [source/autotagging/reporting.py](source/autotagging/reporting.py)

Standalone operator surface:

- [source/autotagging/standalone_app.py](source/autotagging/standalone_app.py)
- [source/run_tagging_worker.py](source/run_tagging_worker.py)

Core tagging helpers:

- [source/autotagging/title_normalizer.py](source/autotagging/title_normalizer.py)
- [source/autotagging/candidate_resolver.py](source/autotagging/candidate_resolver.py)
- [source/autotagging/musicbrainz_enricher.py](source/autotagging/musicbrainz_enricher.py)
- [source/autotagging/tag_writer.py](source/autotagging/tag_writer.py)

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
- `retry`
  - requeue matching packages back to `pending`
- `retry-run`
  - requeue matching packages and process just those packages immediately

Examples:

```bash
python source/run_tagging_worker.py status
python source/run_tagging_worker.py session --session-id <session-id>
python source/run_tagging_worker.py events --event-type candidate_resolved --limit 20
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

## Planned Standalone Classes

The newer standalone code now includes some intentionally incomplete roadmap classes in [source/autotagging/standalone_app.py](source/autotagging/standalone_app.py).

Implemented now:

- `TaggingStandaloneService`
  - current high-level operator actions and reports
- `TaggingStandaloneCLI`
  - parser and command dispatch

Sketched for later:

- `TaggingReviewStore`
  - intended place for persistent approval / override / operator-note state
- `TaggingRepairPlanner`
  - intended place for higher-level “what should I do next?” logic

These placeholders exist on purpose so the missing pieces are visible in code instead of only implied in chat history.

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
