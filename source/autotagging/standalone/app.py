import argparse
import sys
from pathlib import Path
from typing import Callable

from autotagging.runtime_tagging.package_builder import TaggingQueueStore
from autotagging.runtime_tagging.worker import TaggingWorker
from autotagging.standalone.reporting import (
    format_events,
    format_queue_snapshot,
    format_repair_plans,
    format_requeue_results,
    format_review_candidates,
    format_session_snapshot,
)
from autotagging.standalone.local_directory import LocalDirectoryTagger
from autotagging.standalone.repair_planner import TaggingRepairPlanner
from autotagging.standalone.review_store import TaggingReviewStore


class TaggingStandaloneService:
    """Higher-level operator service for the standalone autotagging tool."""

    def __init__(
        self,
        queue_store: TaggingQueueStore | None = None,
        review_store: TaggingReviewStore | None = None,
        local_directory_tagger: LocalDirectoryTagger | None = None,
    ):
        self.queue_store = queue_store or TaggingQueueStore()
        self.review_store = review_store or TaggingReviewStore(self.queue_store.base_dir)
        self.repair_planner = TaggingRepairPlanner(self.queue_store, self.review_store)
        self.local_directory_tagger = local_directory_tagger or LocalDirectoryTagger()

    def render_queue_status(
        self,
        *,
        output_format: str = "csv",
        view: str = "both",
        limit_per_state: int = 10,
    ) -> str:
        snapshot = self.queue_store.build_queue_snapshot(limit_per_state=max(limit_per_state, 0))
        return format_queue_snapshot(snapshot, output_format=output_format, view=view)

    def render_session_status(
        self,
        *,
        session_id: str,
        output_format: str = "csv",
    ) -> str:
        snapshot = self.queue_store.build_session_snapshot(session_id)
        return format_session_snapshot(snapshot, output_format=output_format)

    def render_events(
        self,
        *,
        output_format: str = "csv",
        limit: int = 50,
        session_id: str | None = None,
        job_id: str | None = None,
        event_type: str | None = None,
    ) -> str:
        events = self.queue_store.event_logger.read_events(
            limit=max(limit, 0),
            session_id=session_id,
            job_id=job_id,
            event_type=event_type,
        )
        return format_events(events, output_format=output_format)

    def requeue(
        self,
        *,
        source_state: str = "failed",
        session_id: str | None = None,
        job_id: str | None = None,
        dry_run: bool = False,
        output_format: str = "csv",
    ) -> tuple[str, int]:
        results = self.queue_store.requeue_packages(
            source_state=source_state,
            session_id=session_id,
            job_id=job_id,
            dry_run=dry_run,
        )
        return format_requeue_results(results, output_format=output_format), (0 if results else 1)

    def render_review_candidates(
        self,
        *,
        output_format: str = "csv",
        session_id: str | None = None,
        states: tuple[str, ...] | None = None,
    ) -> str:
        candidates = self.review_store.list_review_candidates(
            self.queue_store,
            session_id=session_id,
            states=states,
        )
        return format_review_candidates(candidates, output_format=output_format)

    def save_override(
        self,
        *,
        job_id: str,
        artist: str = "",
        title: str = "",
        album: str = "",
        note: str = "",
        output_format: str = "csv",
    ) -> str:
        review = self.review_store.save_override(
            job_id,
            {
                "artist": artist,
                "title": title,
                "album": album,
            },
            note=note,
        )
        return format_review_candidates(
            [
                {
                    "job_id": review.get("job_id", ""),
                    "session_id": "",
                    "sequence_no": 0,
                    "state": "override_saved",
                    "review_decision": review.get("decision", ""),
                    "override_saved": bool(review.get("override_fields")),
                    "review_note": review.get("note", ""),
                    "source_author": review.get("override_fields", {}).get("artist", ""),
                    "source_title": review.get("override_fields", {}).get("title", ""),
                    "candidate_source": "",
                    "candidate_confidence": "",
                    "write_allowed": "",
                    "write_status": "",
                    "final_output_path": "",
                }
            ],
            output_format=output_format,
        )

    def approve_review(
        self,
        *,
        job_id: str,
        note: str = "",
        output_format: str = "csv",
    ) -> str:
        review = self.review_store.approve_candidate(job_id, note=note)
        return self._format_single_review_record(review, state="approved", output_format=output_format)

    def reject_review(
        self,
        *,
        job_id: str,
        reason: str = "",
        output_format: str = "csv",
    ) -> str:
        review = self.review_store.reject_candidate(job_id, reason=reason)
        return self._format_single_review_record(review, state="rejected", output_format=output_format)

    def render_session_repair_plan(
        self,
        *,
        session_id: str,
        output_format: str = "csv",
    ) -> str:
        plans = self.repair_planner.plan_session_repairs(session_id)
        return format_repair_plans(plans, output_format=output_format)

    def render_queue_repair_plan(
        self,
        *,
        output_format: str = "csv",
    ) -> str:
        plans = self.repair_planner.plan_queue_maintenance()
        return format_repair_plans(plans, output_format=output_format)

    @staticmethod
    def _format_single_review_record(
        review: dict[str, object],
        *,
        state: str,
        output_format: str,
    ) -> str:
        return format_review_candidates(
            [
                {
                    "job_id": review.get("job_id", ""),
                    "session_id": "",
                    "sequence_no": 0,
                    "state": state,
                    "review_decision": review.get("decision", ""),
                    "override_saved": bool(review.get("override_fields")),
                    "review_note": review.get("note", ""),
                    "source_author": review.get("override_fields", {}).get("artist", "") if isinstance(review.get("override_fields"), dict) else "",
                    "source_title": review.get("override_fields", {}).get("title", "") if isinstance(review.get("override_fields"), dict) else "",
                    "candidate_source": "",
                    "candidate_confidence": "",
                    "write_allowed": "",
                    "write_status": "",
                    "final_output_path": "",
                }
            ],
            output_format=output_format,
        )

    def requeue_and_process(
        self,
        *,
        source_state: str = "failed",
        session_id: str | None = None,
        job_id: str | None = None,
        dry_run: bool = False,
        output_format: str = "csv",
    ) -> tuple[str, int]:
        results = self.queue_store.requeue_packages(
            source_state=source_state,
            session_id=session_id,
            job_id=job_id,
            dry_run=dry_run,
        )
        if not results:
            return format_requeue_results(results, output_format=output_format), 1

        if not dry_run:
            worker = TaggingWorker(queue_store=self.queue_store)
            for result in results:
                pending_path = Path(result.get("target_queue_path", "") or "")
                if not pending_path.exists():
                    continue
                final_path = worker.process_package_file(pending_path)
                final_payload = self.queue_store.read_package(final_path)
                result["worker_processed"] = True
                result["final_state"] = final_payload.get("state", "")
                result["final_queue_path"] = str(final_path)
                result["status"] = "requeued_and_processed"

        return format_requeue_results(results, output_format=output_format), 0

    def run_worker(
        self,
        *,
        poll_interval: float = 1.0,
        idle_timeout: float = 30.0,
    ) -> int:
        worker = TaggingWorker(
            queue_store=self.queue_store,
            poll_interval=poll_interval,
            idle_timeout=idle_timeout,
        )
        worker.run_until_idle()
        return 0

    def scan_local_directory(
        self,
        *,
        directory: str,
        report_csv: str | None = None,
        include_tagged: bool = False,
        enrich: bool = True,
        scan_scope: str = "missing-any",
    ) -> str:
        summary = self.local_directory_tagger.scan_directory(
            directory,
            report_csv=report_csv,
            include_tagged=include_tagged,
            enrich=enrich,
            scan_scope=scan_scope,
        )
        return (
            f"scan_directory={summary['directory']}\n"
            f"report_csv={summary['report_csv']}\n"
            f"files_seen={summary['files_seen']}\n"
            f"rows_written={summary['rows_written']}\n"
            f"already_tagged_skipped={summary['already_tagged_skipped']}\n"
            f"write_ready_rows={summary['write_ready_rows']}\n"
            f"review_rows={summary['review_rows']}\n"
            f"no_suggestion_rows={summary['no_suggestion_rows']}\n"
        )

    def apply_local_csv(
        self,
        *,
        csv_path: str,
        overwrite_mode: str = "missing",
    ) -> str:
        summary = self.local_directory_tagger.apply_csv_with_overwrite_mode(
            csv_path,
            overwrite_mode=overwrite_mode,
        )
        return (
            f"csv_path={summary['csv_path']}\n"
            f"rows_seen={summary['rows_seen']}\n"
            f"rows_written={summary['rows_written']}\n"
            f"rows_skipped={summary['rows_skipped']}\n"
            f"rows_errored={summary['rows_errored']}\n"
        )


class TaggingStandaloneCLI:
    """Parser and command dispatcher for the standalone autotagging tool."""

    def __init__(
        self,
        queue_store_factory: Callable[[Path | str | None], TaggingQueueStore] | None = None,
    ):
        self.queue_store_factory = queue_store_factory or self._default_queue_store_factory
        self.parser = self.build_parser()
        self.enable_argcomplete(self.parser)

    @staticmethod
    def _default_queue_store_factory(queue_dir: Path | str | None) -> TaggingQueueStore:
        return TaggingQueueStore(base_dir=queue_dir) if queue_dir else TaggingQueueStore()

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Background worker and operator CLI for ytripper tagging packages",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=(
                "Examples:\n"
                "  yt-tagger> status\n"
                "  yt-tagger> scan-dir --directory ~/Music\n"
                "  yt-tagger> scan-dir --directory ~/Music --no-enrich\n"
                "  yt-tagger> apply-csv --csv ~/Music/2026-05-19_tag_suggestions.csv\n"
            ),
        )
        subparsers = parser.add_subparsers(dest="command")
        parser._completion_default_subcommand = "run"

        run_parser = subparsers.add_parser("run", help="Run the background tagging worker")
        run_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        run_parser.add_argument("--idle-timeout", type=float, default=30.0, help="Seconds to wait before exiting when idle")
        run_parser.add_argument("--poll-interval", type=float, default=1.0, help="Seconds between pending-queue polls")

        status_parser = subparsers.add_parser("status", help="Print queue status snapshots")
        status_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        status_parser.add_argument(
            "--view",
            choices=("counts", "recent", "both"),
            default="both",
            help="Which queue snapshot view to print",
        )
        status_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for status snapshots",
        )
        status_parser.add_argument(
            "--limit-per-state",
            type=int,
            default=10,
            help="Maximum recent packages to include per queue state",
        )

        session_parser = subparsers.add_parser("session", help="Print package summaries for one tagging session")
        session_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        session_parser.add_argument("--session-id", required=True, help="Tagging session ID to inspect")
        session_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for session summaries",
        )

        events_parser = subparsers.add_parser("events", help="Print recent tagging lifecycle events")
        events_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        events_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for event rows",
        )
        events_parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximum recent events to include",
        )
        events_parser.add_argument("--session-id", default=None, help="Filter events to one tagging session")
        events_parser.add_argument("--job-id", default=None, help="Filter events to one tagging job")
        events_parser.add_argument("--event-type", default=None, help="Filter events to one event type")

        review_list_parser = subparsers.add_parser("review-list", help="List packages that likely need operator review")
        review_list_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        review_list_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for review candidates",
        )
        review_list_parser.add_argument("--session-id", default=None, help="Filter review candidates to one tagging session")
        review_list_parser.add_argument(
            "--states",
            nargs="+",
            choices=("failed", "skipped", "enriched"),
            default=["failed", "skipped", "enriched"],
            help="Package states to include in review output",
        )

        review_override_parser = subparsers.add_parser("review-override", help="Persist manual override fields for one job")
        review_override_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        review_override_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for saved override details",
        )
        review_override_parser.add_argument("--job-id", required=True, help="Job ID to attach override fields to")
        review_override_parser.add_argument("--artist", default="", help="Manual artist override")
        review_override_parser.add_argument("--title", default="", help="Manual title override")
        review_override_parser.add_argument("--album", default="", help="Manual album override")
        review_override_parser.add_argument("--note", default="", help="Optional operator note")

        review_approve_parser = subparsers.add_parser("review-approve", help="Persist an approval decision for one job")
        review_approve_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        review_approve_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for saved review decisions",
        )
        review_approve_parser.add_argument("--job-id", required=True, help="Job ID to approve")
        review_approve_parser.add_argument("--note", default="", help="Optional operator note")

        review_reject_parser = subparsers.add_parser("review-reject", help="Persist a rejection decision for one job")
        review_reject_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        review_reject_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for saved review decisions",
        )
        review_reject_parser.add_argument("--job-id", required=True, help="Job ID to reject")
        review_reject_parser.add_argument("--reason", default="", help="Optional rejection reason")

        plan_session_parser = subparsers.add_parser("plan-session", help="Suggest follow-up actions for one session")
        plan_session_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        plan_session_parser.add_argument("--session-id", required=True, help="Session ID to inspect")
        plan_session_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for repair plans",
        )

        plan_queue_parser = subparsers.add_parser("plan-queue", help="Suggest queue-level maintenance actions")
        plan_queue_parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        plan_queue_parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for queue repair plans",
        )

        retry_parser = subparsers.add_parser("retry", help="Requeue packages for manual retry")
        self._add_retry_arguments(retry_parser)

        retry_run_parser = subparsers.add_parser(
            "retry-run",
            help="Requeue packages and process just those packages immediately",
        )
        self._add_retry_arguments(retry_run_parser)

        scan_dir_parser = subparsers.add_parser("scan-dir", help="Crawl a local directory and write a tag suggestion CSV")
        scan_dir_parser.add_argument("--directory", required=True, help="Root directory to scan recursively")
        scan_dir_parser.add_argument("--report-csv", default=None, help="Optional destination CSV path")
        scan_dir_parser.add_argument(
            "--include-tagged",
            action="store_true",
            help="Include files that already have both artist and title tags",
        )
        scan_dir_parser.add_argument(
            "--scan-scope",
            choices=("missing-any", "untagged", "missing-artist", "missing-title", "all"),
            default="missing-any",
            help="Which files should be included in the scan before any CSV review",
        )
        scan_dir_parser.add_argument(
            "--no-enrich",
            action="store_true",
            help="Disable MusicBrainz confirmation during the local scan",
        )

        apply_csv_parser = subparsers.add_parser("apply-csv", help="Write reviewed CSV suggestions back into source files in place")
        apply_csv_parser.add_argument("--csv", required=True, help="CSV created by scan-dir and optionally edited by the user")
        apply_csv_parser.add_argument(
            "--overwrite-mode",
            choices=("missing", "all"),
            default="missing",
            help="Whether to fill only missing fields or overwrite existing tag fields too",
        )
        return parser

    @staticmethod
    def enable_argcomplete(parser: argparse.ArgumentParser) -> None:
        try:
            import argcomplete

            argcomplete.autocomplete(parser)
        except ImportError:
            pass

    def execute(self, argv: list[str] | None = None) -> int:
        args = self.parser.parse_args(self._normalize_argv(argv))
        queue_dir = getattr(args, "queue_dir", None)
        service = TaggingStandaloneService(self.queue_store_factory(queue_dir))

        if args.command == "status":
            print(
                service.render_queue_status(
                    output_format=args.format,
                    view=args.view,
                    limit_per_state=args.limit_per_state,
                ),
                end="",
            )
            return 0

        if args.command == "session":
            print(
                service.render_session_status(
                    session_id=args.session_id,
                    output_format=args.format,
                ),
                end="",
            )
            return 0

        if args.command == "events":
            print(
                service.render_events(
                    output_format=args.format,
                    limit=args.limit,
                    session_id=args.session_id,
                    job_id=args.job_id,
                    event_type=args.event_type,
                ),
                end="",
            )
            return 0

        if args.command == "review-list":
            print(
                service.render_review_candidates(
                    output_format=args.format,
                    session_id=args.session_id,
                    states=tuple(args.states),
                ),
                end="",
            )
            return 0

        if args.command == "review-override":
            print(
                service.save_override(
                    job_id=args.job_id,
                    artist=args.artist,
                    title=args.title,
                    album=args.album,
                    note=args.note,
                    output_format=args.format,
                ),
                end="",
            )
            return 0

        if args.command == "review-approve":
            print(
                service.approve_review(
                    job_id=args.job_id,
                    note=args.note,
                    output_format=args.format,
                ),
                end="",
            )
            return 0

        if args.command == "review-reject":
            print(
                service.reject_review(
                    job_id=args.job_id,
                    reason=args.reason,
                    output_format=args.format,
                ),
                end="",
            )
            return 0

        if args.command == "plan-session":
            print(
                service.render_session_repair_plan(
                    session_id=args.session_id,
                    output_format=args.format,
                ),
                end="",
            )
            return 0

        if args.command == "plan-queue":
            print(
                service.render_queue_repair_plan(output_format=args.format),
                end="",
            )
            return 0

        if args.command == "retry":
            output, exit_code = service.requeue(
                source_state=args.source_state,
                session_id=args.session_id,
                job_id=args.job_id,
                dry_run=args.dry_run,
                output_format=args.format,
            )
            print(output, end="")
            return exit_code

        if args.command == "retry-run":
            output, exit_code = service.requeue_and_process(
                source_state=args.source_state,
                session_id=args.session_id,
                job_id=args.job_id,
                dry_run=args.dry_run,
                output_format=args.format,
            )
            print(output, end="")
            return exit_code

        if args.command == "scan-dir":
            print(
                service.scan_local_directory(
                    directory=args.directory,
                    report_csv=args.report_csv,
                    include_tagged=args.include_tagged,
                    enrich=not args.no_enrich,
                    scan_scope=args.scan_scope,
                ),
                end="",
            )
            return 0

        if args.command == "apply-csv":
            print(
                service.apply_local_csv(
                    csv_path=args.csv,
                    overwrite_mode=args.overwrite_mode,
                ),
                end="",
            )
            return 0

        return service.run_worker(
            poll_interval=args.poll_interval,
            idle_timeout=args.idle_timeout,
        )

    @staticmethod
    def _normalize_argv(argv: list[str] | None) -> list[str]:
        normalized = list(sys.argv[1:] if argv is None else argv)
        if normalized and normalized[0] in ("-h", "--help"):
            return normalized
        if not normalized or normalized[0].startswith("-"):
            return ["run", *normalized]
        return normalized

    @staticmethod
    def _add_retry_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
        parser.add_argument(
            "--format",
            choices=("csv", "json"),
            default="csv",
            help="Output format for retry results",
        )
        parser.add_argument(
            "--source-state",
            choices=("failed", "skipped", "enriched"),
            default="failed",
            help="Which package state to requeue back to pending",
        )
        retry_target_group = parser.add_mutually_exclusive_group(required=True)
        retry_target_group.add_argument("--session-id", default=None, help="Retry every matching package in one session")
        retry_target_group.add_argument("--job-id", default=None, help="Retry one package by job ID")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show which packages would be requeued without modifying the queue",
        )
