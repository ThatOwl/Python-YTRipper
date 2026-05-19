import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.runtime_tagging.package_builder import TaggingQueueStore


class TestTaggingQueueStore(unittest.TestCase):
    def test_recover_stale_processing_moves_package_back_to_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime-tagging")
            dirs = store.ensure_queue_dirs()
            processing_path = dirs["processing"] / "stale.json"

            stale_time = (datetime.now(timezone.utc) - timedelta(seconds=600)).replace(microsecond=0).isoformat()
            payload = {
                "job_id": "job-1",
                "state": "processing",
                "created_at": stale_time,
                "lifecycle": {
                    "processing_at": stale_time,
                    "last_transition_at": stale_time,
                    "state_history": [{"state": "processing", "at": stale_time}],
                },
            }
            store.write_package(processing_path, payload)

            recovered = store.recover_stale_processing(max_age_seconds=300)

            self.assertEqual(len(recovered), 1)
            recovered_path = recovered[0]
            self.assertTrue(recovered_path.exists())
            self.assertIn("/pending/", recovered_path.as_posix())

            recovered_payload = json.loads(recovered_path.read_text(encoding="utf-8"))
            self.assertEqual(recovered_payload["state"], "prepared")
            self.assertEqual(recovered_payload["lifecycle"]["recovery_count"], 1)
            self.assertIn("recovered_from_processing_at", recovered_payload["lifecycle"])
            events = [
                json.loads(line)
                for line in (Path(tmpdir) / "runtime-tagging" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            event_types = [event["event_type"] for event in events]
            self.assertIn("state_transition", event_types)
            self.assertIn("package_recovered", event_types)

    def test_prune_state_files_applies_age_and_count_limits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime-tagging")
            dirs = store.ensure_queue_dirs()
            now = datetime.now(timezone.utc).replace(microsecond=0)

            ages = [900, 600, 300]
            paths = []
            for idx, age in enumerate(ages, 1):
                ts = (now - timedelta(seconds=age)).isoformat()
                path = dirs["done"] / f"done-{idx}.json"
                payload = {
                    "job_id": f"job-{idx}",
                    "state": "done",
                    "created_at": ts,
                    "lifecycle": {
                        "done_at": ts,
                        "last_transition_at": ts,
                        "state_history": [{"state": "done", "at": ts}],
                    },
                }
                store.write_package(path, payload)
                paths.append(path)

            deleted = store.prune_state_files("done", max_count=2, max_age_seconds=500)

            self.assertEqual(len(deleted), 2)
            remaining = store.list_state_files("done")
            self.assertEqual(len(remaining), 1)
            self.assertTrue(remaining[0].name.endswith("done-3.json"))
            events = [
                json.loads(line)
                for line in (Path(tmpdir) / "runtime-tagging" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            pruned = [event for event in events if event["event_type"] == "package_pruned"]
            self.assertEqual(len(pruned), 2)

    def test_queue_snapshot_and_session_snapshot_summarize_packages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime-tagging")
            dirs = store.ensure_queue_dirs()
            now = datetime.now(timezone.utc).replace(microsecond=0)

            def _write_package(state: str, name: str, session_id: str, sequence_no: int, seconds_ago: int) -> None:
                ts = (now - timedelta(seconds=seconds_ago)).isoformat()
                payload = {
                    "job_id": name,
                    "session_id": session_id,
                    "sequence_no": sequence_no,
                    "state": state,
                    "created_at": ts,
                    "final_output_path": f"/tmp/{name}.m4a",
                    "playlist_title": "Queue Test",
                    "requested_actions": ["autotag"],
                    "source": {
                        "title": f"Title {name}",
                        "author": "Author Test",
                    },
                    "resolved_tags": {
                        "source": "title_author_match",
                        "confidence": 0.91,
                        "write_allowed": True,
                    },
                    "write_result": {
                        "status": "ok" if state == "done" else "",
                    },
                    "lifecycle": {
                        "last_transition_at": ts,
                        f"{state}_at": ts,
                        "state_history": [{"state": state, "at": ts}],
                    },
                }
                store.write_package(dirs[state] / f"{name}.json", payload)

            _write_package("pending", "job-pending", "session-a", 1, 60)
            _write_package("done", "job-done", "session-a", 2, 30)
            _write_package("failed", "job-failed", "session-b", 1, 10)

            snapshot = store.build_queue_snapshot(limit_per_state=1)

            self.assertEqual(snapshot["counts"]["pending"], 1)
            self.assertEqual(snapshot["counts"]["done"], 1)
            self.assertEqual(snapshot["counts"]["failed"], 1)
            self.assertEqual(snapshot["recent"]["pending"][0]["job_id"], "job-pending")
            self.assertEqual(snapshot["recent"]["done"][0]["write_status"], "ok")
            self.assertEqual(snapshot["sessions"][0]["session_id"], "session-b")
            self.assertEqual(snapshot["sessions"][1]["counts"]["pending"], 1)
            self.assertEqual(snapshot["sessions"][1]["counts"]["done"], 1)

            session_snapshot = store.build_session_snapshot("session-a")

            self.assertEqual(session_snapshot["package_count"], 2)
            self.assertEqual(session_snapshot["counts"]["pending"], 1)
            self.assertEqual(session_snapshot["counts"]["done"], 1)
            self.assertEqual(
                [package["job_id"] for package in session_snapshot["packages"]],
                ["job-pending", "job-done"],
            )

    def test_requeue_failed_packages_moves_matching_package_back_to_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime-tagging")
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

            failed_path = dirs["failed"] / "job-1.json"
            store.write_package(
                failed_path,
                {
                    "job_id": "job-1",
                    "session_id": "session-a",
                    "sequence_no": 3,
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

            results = store.requeue_failed_packages(job_id="job-1")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["status"], "requeued")
            self.assertFalse(failed_path.exists())
            pending_files = store.list_state_files("pending")
            self.assertEqual(len(pending_files), 1)
            payload = json.loads(pending_files[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "prepared")
            self.assertEqual(payload["lifecycle"]["manual_requeue_count"], 1)
            events = [
                json.loads(line)
                for line in (Path(tmpdir) / "runtime-tagging" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            event_types = [event["event_type"] for event in events]
            self.assertIn("state_transition", event_types)
            self.assertIn("package_requeued", event_types)

    def test_requeue_failed_packages_dry_run_leaves_failed_package_in_place(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime-tagging")
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

            failed_path = dirs["failed"] / "job-1.json"
            store.write_package(
                failed_path,
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

            results = store.requeue_failed_packages(session_id="session-a", dry_run=True)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["status"], "dry_run")
            self.assertTrue(failed_path.exists())
            self.assertEqual(store.list_state_files("pending"), [])
            event_log = Path(tmpdir) / "runtime-tagging" / "events.jsonl"
            self.assertFalse(event_log.exists())

    def test_requeue_packages_can_move_skipped_package_from_done_back_to_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime-tagging")
            dirs = store.ensure_queue_dirs()
            ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

            skipped_path = dirs["done"] / "job-skipped.json"
            written_path = dirs["done"] / "job-written.json"
            store.write_package(
                skipped_path,
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
                written_path,
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

            results = store.requeue_packages(source_state="skipped", session_id="session-a")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["job_id"], "job-skipped")
            self.assertEqual(results[0]["source_state"], "skipped")
            self.assertTrue(written_path.exists())
            self.assertFalse(skipped_path.exists())
            pending_files = store.list_state_files("pending")
            self.assertEqual(len(pending_files), 1)
            payload = json.loads(pending_files[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "prepared")
            self.assertEqual(payload["lifecycle"]["manual_requeue_count"], 1)
            events = [
                json.loads(line)
                for line in (Path(tmpdir) / "runtime-tagging" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            requeued_event = next(event for event in events if event["event_type"] == "package_requeued")
            self.assertEqual(requeued_event["requeued_from"], "skipped")
            self.assertEqual(requeued_event["requeued_from_queue_state"], "done")


if __name__ == "__main__":
    unittest.main()
