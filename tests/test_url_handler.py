import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from infrastructure.url_handler import URLHandler


class TestURLHandler(unittest.TestCase):
    def test_is_youtube_url_accepts_real_youtube_hosts(self):
        self.assertTrue(URLHandler.is_youtube_url("https://www.youtube.com/watch?v=abc123"))
        self.assertTrue(URLHandler.is_youtube_url("https://music.youtube.com/watch?v=abc123"))
        self.assertTrue(URLHandler.is_youtube_url("https://youtu.be/abc123"))

    def test_is_youtube_url_rejects_substring_spoof_hosts(self):
        self.assertFalse(URLHandler.is_youtube_url("https://youtube.com.evil.example/watch?v=abc123"))
        self.assertFalse(URLHandler.is_youtube_url("https://notyoutube.example/watch?v=abc123"))

    def test_clean_video_link_removes_playlist_and_start_radio_params(self):
        cleaned = URLHandler.clean_video_link(
            "https://www.youtube.com/watch?v=7S_cMrxjZFo&list=RD7S_cMrxjZFo&start_radio=1"
        )
        self.assertEqual(cleaned, "https://www.youtube.com/watch?v=7S_cMrxjZFo")


if __name__ == "__main__":
    unittest.main()
