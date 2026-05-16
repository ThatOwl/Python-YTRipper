import datetime
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from infrastructure.os_interactions import OSInteractions
from utility.utils import DownloadResult


class TestSaveDownloadResults(unittest.TestCase):
    def test_batch_single_results_write_header_once_then_append_rows(self):
        timestamp = datetime.datetime(2026, 5, 16, 12, 0, 0)
        first_result = DownloadResult(
            success=True,
            errors=[],
            video_title="First Video",
            video_url="https://www.youtube.com/watch?v=first",
        )
        second_result = DownloadResult(
            success=False,
            errors=["network"],
            video_title="Second Video",
            video_url="https://www.youtube.com/watch?v=second",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            OSInteractions.save_download_results([first_result], tmpdir, timestamp=timestamp)
            OSInteractions.save_download_results([second_result], tmpdir, timestamp=timestamp)

            output_path = Path(tmpdir) / "2026-05-16_12-00-00_batch_single_results.csv"
            self.assertTrue(output_path.exists())

            lines = output_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "video_title,video_url,success,errors")
            self.assertEqual(len(lines), 3)
            self.assertIn("First Video", lines[1])
            self.assertIn("Second Video", lines[2])


if __name__ == "__main__":
    unittest.main()
