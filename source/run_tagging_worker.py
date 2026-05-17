import argparse

from autotagging.package_builder import TaggingQueueStore
from autotagging.worker import TaggingWorker


def main() -> int:
    parser = argparse.ArgumentParser(description="Background worker for ytripper tagging packages")
    parser.add_argument("--queue-dir", default=None, help="Optional queue directory override")
    parser.add_argument("--idle-timeout", type=float, default=30.0, help="Seconds to wait before exiting when idle")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Seconds between pending-queue polls")
    args = parser.parse_args()

    queue_store = TaggingQueueStore(base_dir=args.queue_dir) if args.queue_dir else TaggingQueueStore()
    worker = TaggingWorker(
        queue_store=queue_store,
        poll_interval=args.poll_interval,
        idle_timeout=args.idle_timeout,
    )
    worker.run_until_idle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
