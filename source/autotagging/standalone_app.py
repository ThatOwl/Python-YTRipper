import argparse
import sys
from pathlib import Path
from typing import Any, Callable

from .package_builder import TaggingQueueStore
from .reporting import (
    format_events,
    format_queue_snapshot,
    format_requeue_results,
    format_session_snapshot,
)
from .worker import TaggingWorker


class TaggingStandaloneService:
    """Higher-level operator service for the standalone autotagging tool."""

    def __init__(self, queue_store: TaggingQueueStore | None = None):
        self.queue_store = queue_store or TaggingQueueStore()

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


class TaggingStandaloneCLI:
    """Parser and command dispatcher for the standalone autotagging tool."""

    def __init__(
        self,
        queue_store_factory: Callable[[Path | str | None], TaggingQueueStore] | None = None,
    ):
        self.queue_store_factory = queue_store_factory or self._default_queue_store_factory

    @staticmethod
    def _default_queue_store_factory(queue_dir: Path | str | None) -> TaggingQueueStore:
        return TaggingQueueStore(base_dir=queue_dir) if queue_dir else TaggingQueueStore()

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Background worker and operator CLI for ytripper tagging packages")
        subparsers = parser.add_subparsers(dest="command")

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

        retry_parser = subparsers.add_parser("retry", help="Requeue packages for manual retry")
        self._add_retry_arguments(retry_parser)

        retry_run_parser = subparsers.add_parser(
            "retry-run",
            help="Requeue packages and process just those packages immediately",
        )
        self._add_retry_arguments(retry_run_parser)
        return parser

    def execute(self, argv: list[str] | None = None) -> int:
        parser = self.build_parser()
        args = parser.parse_args(self._normalize_argv(argv))
        service = TaggingStandaloneService(self.queue_store_factory(args.queue_dir))

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

        return service.run_worker(
            poll_interval=args.poll_interval,
            idle_timeout=args.idle_timeout,
        )

    @staticmethod
    def _normalize_argv(argv: list[str] | None) -> list[str]:
        normalized = list(sys.argv[1:] if argv is None else argv)
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


class TaggingReviewStore:
    """Planned persistent store for operator review decisions and overrides."""

    def list_review_candidates(self) -> list[dict[str, Any]]:
        pass

    def approve_candidate(self, job_id: str) -> None:
        pass

    def reject_candidate(self, job_id: str, reason: str = "") -> None:
        pass

    def save_override(self, job_id: str, override_fields: dict[str, Any]) -> None:
        pass


class TaggingRepairPlanner:
    """Planned batch-oriented repair planner for richer standalone workflows."""

    def plan_session_repairs(self, session_id: str) -> list[dict[str, Any]]:
        pass

    def plan_queue_maintenance(self) -> list[dict[str, Any]]:
        pass

    def suggest_follow_up_actions(self, job_id: str) -> list[str]:
        pass
