import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.candidate_resolver import CandidateResolver


class TestCandidateResolver(unittest.TestCase):
    def test_prefers_explicit_youtube_metadata(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Ignored Playlist",
            "source": {
                "metadata": {
                    "music": {
                        "artist": "Odd Chap",
                        "song": "Swing Theory",
                        "album": "Electro Swing Essentials",
                    }
                }
            },
            "normalization": {},
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Odd Chap")
        self.assertEqual(candidate.title, "Swing Theory")
        self.assertEqual(candidate.album, "Electro Swing Essentials")
        self.assertEqual(candidate.source, "youtube_metadata")
        self.assertTrue(candidate.write_allowed)

    def test_author_matched_title_analysis_is_auto_writable(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Electro Swing",
            "source": {"author": "Caro Emerald"},
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Caro Emerald",
                    "guessed_title": "Tangled Up Odd Chap Bootleg",
                    "split_confidence": "author_matched_left",
                    "lookup_title": "Tangled Up Odd Chap Bootleg",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertEqual(candidate.artist, "Caro Emerald")
        self.assertEqual(candidate.title, "Tangled Up Odd Chap Bootleg")
        self.assertEqual(candidate.album, "Electro Swing")
        self.assertEqual(candidate.source, "title_author_match")
        self.assertTrue(candidate.write_allowed)

    def test_unconfirmed_dash_split_stays_non_destructive(self):
        resolver = CandidateResolver()
        payload = {
            "playlist_title": "Electro Swing",
            "source": {"author": "Unrelated Channel"},
            "normalization": {
                "title_analysis": {
                    "guessed_artist": "Odd Chap, Alanna Lyes",
                    "guessed_title": "Blaze Electro Swing",
                    "split_confidence": "dash_split",
                }
            },
        }

        candidate = resolver.resolve(payload)

        self.assertFalse(candidate.write_allowed)
        self.assertEqual(candidate.source, "title_dash_split")


if __name__ == "__main__":
    unittest.main()
