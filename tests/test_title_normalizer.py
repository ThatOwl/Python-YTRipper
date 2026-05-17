import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from autotagging.title_normalizer import TitleNormalizer


class TestTitleNormalizer(unittest.TestCase):
    def test_normalize_strips_context_and_junk(self):
        normalizer = TitleNormalizer()

        result = normalizer.normalize(
            raw_title="ELECTRO SWING  Caro Emerald - Tangled Up (Odd Chap Bootleg) [Official Audio]",
            author="Caro Emerald",
        )

        self.assertEqual(result.context_stripped_title, "Caro Emerald - Tangled Up (Odd Chap Bootleg) [Official Audio]")
        self.assertEqual(result.cleaned_title, "Caro Emerald - Tangled Up Odd Chap Bootleg")
        self.assertEqual(result.guessed_artist, "Caro Emerald")
        self.assertEqual(result.guessed_title, "Tangled Up Odd Chap Bootleg")
        self.assertEqual(result.split_confidence, "author_matched_left")

    def test_dash_split_falls_back_without_author_match(self):
        normalizer = TitleNormalizer()

        result = normalizer.normalize(
            raw_title="Odd Chap, Alanna Lyes - Blaze (Electro Swing)",
            author="Some Other Channel",
        )

        self.assertEqual(result.cleaned_title, "Odd Chap, Alanna Lyes - Blaze Electro Swing")
        self.assertEqual(result.guessed_artist, "Odd Chap, Alanna Lyes")
        self.assertEqual(result.guessed_title, "Blaze Electro Swing")
        self.assertEqual(result.split_confidence, "dash_split")


if __name__ == "__main__":
    unittest.main()
