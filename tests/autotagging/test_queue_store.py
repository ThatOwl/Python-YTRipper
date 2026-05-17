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

from autotagging.package_builder import TaggingQueueStore


class TestTaggingQueueStore(unittest.TestCase):
    def test_recover_stale_processing_moves_package_back_to_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TaggingQueueStore(base_dir=Path(tmpdir) / "runtime" / "tagging")
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


if __name__ == "__main__":
    unittest.main()
