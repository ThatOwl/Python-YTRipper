import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from application.job_event_store import JobEventStore
from application.job_store import JobStore
from application.state_models import JobDetail, JobEvent, JobItemStatus, JobSummary


class TestJobStore(unittest.TestCase):
    def test_save_and_reload_job_detail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JobStore(base_dir=tmpdir)
            detail = JobDetail(
                summary=JobSummary(
                    job_id="job-1",
                    job_kind="playlist",
                    created_at="2026-07-12T10:00:00Z",
                    status="running",
                    items_total=3,
                    option_snapshot={"audio_only": True},
                ),
                items=[
                    JobItemStatus(
                        item_id="1",
                        label="Video 1",
                        status="success",
                        success=True,
                        output_path="/tmp/video1.mp4",
                    )
                ],
            )

            output_path = store.save_detail(detail)
            reloaded = store.get_detail("job-1")

            self.assertEqual(output_path, Path(tmpdir) / "job-1.json")
            self.assertIsNotNone(reloaded)
            self.assertEqual(reloaded.summary.job_kind, "playlist")
            self.assertEqual(reloaded.items[0].label, "Video 1")

    def test_list_summaries_sorts_newest_first_and_filters_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = JobStore(base_dir=tmpdir)
            store.save_summary(JobSummary(job_id="job-old", created_at="2026-07-12T09:00:00Z", status="completed"))
            store.save_summary(JobSummary(job_id="job-new", created_at="2026-07-12T11:00:00Z", status="running"))

            summaries = store.list_summaries()
            running = store.list_summaries(status="running")

            self.assertEqual([summary.job_id for summary in summaries], ["job-new", "job-old"])
            self.assertEqual([summary.job_id for summary in running], ["job-new"])


class TestJobEventStore(unittest.TestCase):
    def test_append_and_filter_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            event_store = JobEventStore(event_log_path=Path(tmpdir) / "events.jsonl")
            event_store.append(
                JobEvent(
                    at="2026-07-12T10:00:00Z",
                    event_type="job_started",
                    job_id="job-1",
                    session_id="session-a",
                    message="started",
                )
            )
            event_store.append(
                JobEvent(
                    at="2026-07-12T11:00:00Z",
                    event_type="job_completed",
                    job_id="job-2",
                    session_id="session-a",
                    message="completed",
                )
            )

            session_events = event_store.read_events(session_id="session-a")
            job_events = event_store.read_events(job_id="job-1")
            completed_events = event_store.read_events(event_type="job_completed")

            self.assertEqual([event.job_id for event in session_events], ["job-2", "job-1"])
            self.assertEqual([event.event_type for event in job_events], ["job_started"])
            self.assertEqual([event.job_id for event in completed_events], ["job-2"])


if __name__ == "__main__":
    unittest.main()
