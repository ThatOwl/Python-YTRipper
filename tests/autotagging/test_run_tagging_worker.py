import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.runtime.package_builder import TaggingPackageBuilder, TaggingQueueStore
from run_tagging_worker import main
from utility.utils import DownloadOptions


class TestRunTaggingWorker(unittest.TestCase):
    def test_status_command_outputs_csv_counts_and_recent_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            now = datetime.now(timezone.utc).replace(microsecond=0)

            pending_ts = (now - timedelta(seconds=60)).isoformat()
            done_ts = (now - timedelta(seconds=10)).isoformat()
            store.write_package(
                dirs["pending"] / "pending.json",
                {
                    "job_id": "job-pending",
                    "session_id": "session-a",
                    "sequence_no": 1,
                    "state": "pending",
                    "created_at": pending_ts,
                    "final_output_path": "/tmp/pending.m4a",
                    "requested_actions": ["autotag"],
                    "source": {"title": "Pending Song", "author": "Pending Artist"},
                    "resolved_tags": {},
                    "lifecycle": {
                        "pending_at": pending_ts,
                        "last_transition_at": pending_ts,
                        "state_history": [{"state": "pending", "at": pending_ts}],
                    },
                },
            )
            store.write_package(
                dirs["done"] / "done.json",
                {
                    "job_id": "job-done",
                    "session_id": "session-a",
                    "sequence_no": 2,
                    "state": "written",
                    "created_at": done_ts,
                    "final_output_path": "/tmp/done.m4a",
                    "requested_actions": ["autotag"],
                    "source": {"title": "Done Song", "author": "Done Artist"},
                    "resolved_tags": {"source": "title_author_match", "confidence": 0.92, "write_allowed": True},
                    "write_result": {"status": "ok"},
                    "lifecycle": {
                        "done_at": done_ts,
                        "last_transition_at": done_ts,
                        "state_history": [{"state": "written", "at": done_ts}],
                    },
                },
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["status", "--queue-dir", str(queue_dir), "--limit-per-state", "1"])

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("state,count", text)
            self.assertIn("pending,1", text)
            self.assertIn("done,1", text)
            self.assertIn("job_id,session_id,sequence_no,state", text)
            self.assertIn("job-pending,session-a,1,pending", text)
            self.assertIn("job-done,session-a,2,written", text)

    def test_session_command_outputs_csv_rows_for_selected_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            now = datetime.now(timezone.utc).replace(microsecond=0)

            for name, session_id, sequence_no in (
                ("first", "session-a", 1),
                ("second", "session-a", 2),
                ("other", "session-b", 1),
            ):
                ts = (now - timedelta(seconds=sequence_no)).isoformat()
                store.write_package(
                    dirs["pending"] / f"{name}.json",
                    {
                        "job_id": f"job-{name}",
                        "session_id": session_id,
                        "sequence_no": sequence_no,
                        "state": "pending",
                        "created_at": ts,
                        "final_output_path": f"/tmp/{name}.m4a",
                        "requested_actions": ["prepare_tagging"],
                        "source": {"title": f"Song {name}", "author": "Artist"},
                        "lifecycle": {
                            "pending_at": ts,
                            "last_transition_at": ts,
                            "state_history": [{"state": "pending", "at": ts}],
                        },
                    },
                )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["session", "--queue-dir", str(queue_dir), "--session-id", "session-a"])

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("job_id,session_id,sequence_no,state", text)
            self.assertIn("job-first,session-a,1,pending", text)
            self.assertIn("job-second,session-a,2,pending", text)
            self.assertNotIn("session-b", text)

    def test_status_command_supports_json_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            store.ensure_queue_dirs()

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["status", "--queue-dir", str(queue_dir), "--format", "json", "--view", "counts"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["counts"]["pending"], 0)
            self.assertIn("recent", payload)

    def test_events_command_outputs_filtered_csv_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)

            store.event_logger.emit(
                "worker_started",
                session_id="session-b",
                job_id="",
                state="",
            )
            store.event_logger.emit(
                "candidate_resolved",
                session_id="session-a",
                job_id="job-1",
                sequence_no=1,
                state="processing",
                candidate_source="title_author_match",
                candidate_confidence=0.91,
                source_url="https://example.invalid/1",
                final_output_path="/tmp/song-1.m4a",
            )
            store.event_logger.emit(
                "tag_write_succeeded",
                session_id="session-a",
                job_id="job-1",
                sequence_no=1,
                state="written",
                wrote_fields=["artist", "title"],
                source_url="https://example.invalid/1",
                final_output_path="/tmp/song-1.m4a",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "events",
                        "--queue-dir",
                        str(queue_dir),
                        "--session-id",
                        "session-a",
                        "--limit",
                        "2",
                    ]
                )

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("at,event_type,job_id,session_id", text)
            self.assertIn("candidate_resolved,job-1,session-a", text)
            self.assertIn("tag_write_succeeded,job-1,session-a", text)
            self.assertNotIn("worker_started", text)
            self.assertIn("artist|title", text)

    def test_events_command_supports_json_output_and_event_type_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)

            store.event_logger.emit(
                "candidate_resolved",
                session_id="session-a",
                job_id="job-1",
                candidate_source="title_author_match",
            )
            store.event_logger.emit(
                "candidate_resolved",
                session_id="session-b",
                job_id="job-2",
                candidate_source="musicbrainz_confirmed",
            )
            store.event_logger.emit(
                "tag_write_succeeded",
                session_id="session-a",
                job_id="job-1",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "events",
                        "--queue-dir",
                        str(queue_dir),
                        "--format",
                        "json",
                        "--event-type",
                        "candidate_resolved",
                        "--job-id",
                        "job-2",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["event_type"], "candidate_resolved")
            self.assertEqual(payload[0]["job_id"], "job-2")

    def test_retry_command_requeues_failed_package_and_outputs_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            store.write_package(
                dirs["failed"] / "job-1.json",
                {
                    "job_id": "job-1",
                    "session_id": "session-a",
                    "sequence_no": 1,
                    "state": "failed",
                    "created_at": ts,
                    "final_output_path": "/tmp/song-1.m4a",
                    "lifecycle": {
                        "failed_at": ts,
                        "last_transition_at": ts,
                        "state_history": [{"state": "failed", "at": ts}],
                    },
                },
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["retry", "--queue-dir", str(queue_dir), "--job-id", "job-1"])

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("job_id,session_id,sequence_no,source_state,target_state,status", text)
            self.assertIn("job-1,session-a,1,failed,prepared,requeued", text)
            self.assertEqual(len(store.list_state_files("failed")), 0)
            self.assertEqual(len(store.list_state_files("pending")), 1)

    def test_retry_command_dry_run_reports_matches_without_changing_queue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            for idx in (1, 2):
                store.write_package(
                    dirs["failed"] / f"job-{idx}.json",
                    {
                        "job_id": f"job-{idx}",
                        "session_id": "session-a",
                        "sequence_no": idx,
                        "state": "failed",
                        "created_at": ts,
                        "final_output_path": f"/tmp/song-{idx}.m4a",
                        "lifecycle": {
                            "failed_at": ts,
                            "last_transition_at": ts,
                            "state_history": [{"state": "failed", "at": ts}],
                        },
                    },
                )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["retry", "--queue-dir", str(queue_dir), "--session-id", "session-a", "--dry-run"])

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("job-1,session-a,1,failed,prepared,dry_run", text)
            self.assertIn("job-2,session-a,2,failed,prepared,dry_run", text)
            self.assertEqual(len(store.list_state_files("failed")), 2)
            self.assertEqual(len(store.list_state_files("pending")), 0)

    def test_retry_command_returns_nonzero_when_no_failed_packages_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            store.ensure_queue_dirs()

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["retry", "--queue-dir", str(queue_dir), "--job-id", "missing-job"])

            self.assertEqual(exit_code, 1)
            self.assertIn("job_id,session_id,sequence_no,source_state,target_state,status", output.getvalue())

    def test_retry_command_can_requeue_skipped_packages_from_done_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            store.write_package(
                dirs["done"] / "job-skipped.json",
                {
                    "job_id": "job-skipped",
                    "session_id": "session-a",
                    "sequence_no": 1,
                    "state": "skipped",
                    "created_at": ts,
                    "final_output_path": "/tmp/skipped.m4a",
                    "lifecycle": {
                        "skipped_at": ts,
                        "last_transition_at": ts,
                        "state_history": [{"state": "skipped", "at": ts}],
                    },
                },
            )
            store.write_package(
                dirs["done"] / "job-written.json",
                {
                    "job_id": "job-written",
                    "session_id": "session-a",
                    "sequence_no": 2,
                    "state": "written",
                    "created_at": ts,
                    "final_output_path": "/tmp/written.m4a",
                    "lifecycle": {
                        "written_at": ts,
                        "last_transition_at": ts,
                        "state_history": [{"state": "written", "at": ts}],
                    },
                },
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "retry",
                        "--queue-dir",
                        str(queue_dir),
                        "--source-state",
                        "skipped",
                        "--session-id",
                        "session-a",
                    ]
                )

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("job-skipped,session-a,1,skipped,prepared,requeued", text)
            self.assertNotIn("job-written", text)
            self.assertEqual(len(store.list_state_files("pending")), 1)
            self.assertEqual(len(store.list_state_files("done")), 1)

    def test_retry_run_command_reprocesses_selected_failed_package(self):
        class _WeakVideo:
            title = "Odd Chap, Alanna Lyes - Blaze (Electro Swing)"
            author = "Some Other Channel"
            description = "test"
            thumbnail_url = "https://img.example/thumb.jpg"
            watch_url = "https://www.youtube.com/watch?v=worker123"
            video_id = "worker123"
            channel_id = "channel-7"
            publish_date = "2026-05-17"
            keywords = ["electro swing"]
            metadata = {}
            captions = []
            chapters = []

        builder = TaggingPackageBuilder()
        options = DownloadOptions(autotag=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            final_output = Path(tmpdir) / "Blaze.m4a"
            final_output.write_text("audio", encoding="utf-8")

            package = builder.build_package(
                final_output_path=final_output,
                download_directory=Path(tmpdir),
                video_obj=_WeakVideo(),
                options=options,
                requested_actions=["autotag"],
                session_id="session-a",
                sequence_no=1,
                playlist_title="Electro Swing",
            )
            payload = package.to_dict()
            payload["state"] = "failed"
            payload["lifecycle"]["failed_at"] = payload["created_at"]
            payload["lifecycle"]["last_transition_at"] = payload["created_at"]
            payload["lifecycle"]["state_history"].append({"state": "failed", "at": payload["created_at"]})
            store.write_package(dirs["failed"] / "job-1.json", payload)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "retry-run",
                        "--queue-dir",
                        str(queue_dir),
                        "--job-id",
                        payload["job_id"],
                    ]
                )

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("requeued_and_processed", text)
            self.assertIn(",true,skipped,", text)
            self.assertEqual(len(store.list_state_files("failed")), 0)
            self.assertEqual(len(store.list_state_files("pending")), 0)
            done_files = store.list_state_files("done")
            self.assertEqual(len(done_files), 1)
            done_payload = json.loads(done_files[0].read_text(encoding="utf-8"))
            self.assertEqual(done_payload["state"], "skipped")

    def test_review_override_and_review_list_surface_saved_review_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            store.write_package(
                dirs["done"] / "job-skipped.json",
                {
                    "job_id": "job-skipped",
                    "session_id": "session-a",
                    "sequence_no": 1,
                    "state": "skipped",
                    "created_at": ts,
                    "final_output_path": "/tmp/skipped.m4a",
                    "source": {"title": "Blaze", "author": "Some Other Channel"},
                    "resolved_tags": {"source": "title_dash_split", "confidence": 0.60, "write_allowed": False},
                    "write_result": {"status": "skipped: candidate not safe for auto-write"},
                    "lifecycle": {
                        "skipped_at": ts,
                        "last_transition_at": ts,
                        "state_history": [{"state": "skipped", "at": ts}],
                    },
                },
            )

            override_output = io.StringIO()
            with redirect_stdout(override_output):
                exit_code = main(
                    [
                        "review-override",
                        "--queue-dir",
                        str(queue_dir),
                        "--job-id",
                        "job-skipped",
                        "--artist",
                        "Odd Chap",
                        "--title",
                        "Blaze",
                        "--note",
                        "manual confirmation",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("override_saved", override_output.getvalue())
            self.assertIn("manual confirmation", override_output.getvalue())

            review_list_output = io.StringIO()
            with redirect_stdout(review_list_output):
                exit_code = main(["review-list", "--queue-dir", str(queue_dir), "--session-id", "session-a"])

            text = review_list_output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("job-skipped,session-a,1,skipped,override_saved,true", text)
            self.assertIn("manual confirmation", text)

    def test_review_approve_and_plan_session_expose_follow_up_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            store.write_package(
                dirs["failed"] / "job-failed.json",
                {
                    "job_id": "job-failed",
                    "session_id": "session-a",
                    "sequence_no": 1,
                    "state": "failed",
                    "created_at": ts,
                    "final_output_path": "/tmp/failed.m4a",
                    "lifecycle": {
                        "failed_at": ts,
                        "last_transition_at": ts,
                        "state_history": [{"state": "failed", "at": ts}],
                    },
                },
            )

            approve_output = io.StringIO()
            with redirect_stdout(approve_output):
                exit_code = main(
                    [
                        "review-approve",
                        "--queue-dir",
                        str(queue_dir),
                        "--job-id",
                        "job-failed",
                        "--note",
                        "ready to retry",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("approved", approve_output.getvalue())

            plan_output = io.StringIO()
            with redirect_stdout(plan_output):
                exit_code = main(["plan-session", "--queue-dir", str(queue_dir), "--session-id", "session-a"])

            text = plan_output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("scope,target_id,job_id,current_state,suggested_action,reason,review_decision,override_saved", text)
            self.assertIn("session,session-a,job-failed,failed,inspect_then_retry", text)
            self.assertIn(",approved,false", text)

    def test_plan_queue_reports_pending_and_failed_maintenance_actions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            store = TaggingQueueStore(base_dir=queue_dir)
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            store.write_package(
                dirs["pending"] / "job-pending.json",
                {
                    "job_id": "job-pending",
                    "session_id": "session-a",
                    "sequence_no": 1,
                    "state": "prepared",
                    "created_at": ts,
                    "final_output_path": "/tmp/pending.m4a",
                    "lifecycle": {
                        "prepared_at": ts,
                        "last_transition_at": ts,
                        "state_history": [{"state": "prepared", "at": ts}],
                    },
                },
            )
            store.write_package(
                dirs["failed"] / "job-failed.json",
                {
                    "job_id": "job-failed",
                    "session_id": "session-b",
                    "sequence_no": 2,
                    "state": "failed",
                    "created_at": ts,
                    "final_output_path": "/tmp/failed.m4a",
                    "lifecycle": {
                        "failed_at": ts,
                        "last_transition_at": ts,
                        "state_history": [{"state": "failed", "at": ts}],
                    },
                },
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["plan-queue", "--queue-dir", str(queue_dir)])

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("queue,failed,,failed,review_and_retry", text)
            self.assertIn("queue,pending,,pending,run_worker", text)

    def test_default_invocation_without_subcommand_still_runs_worker_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "runtime" / "tagging"
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["--queue-dir", str(queue_dir), "--idle-timeout", "0", "--poll-interval", "0.01"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
