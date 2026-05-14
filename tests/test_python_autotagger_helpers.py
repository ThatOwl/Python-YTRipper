import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _load_autotagger_module():
    module_name = "python_autotagger_under_test"
    if module_name in sys.modules:
        return sys.modules[module_name]

    mutagen_pkg = types.ModuleType("mutagen")
    mutagen_mp3 = types.ModuleType("mutagen.mp3")
    mutagen_mp4 = types.ModuleType("mutagen.mp4")
    mutagen_id3 = types.ModuleType("mutagen.id3")

    class _DummyTag:
        def __init__(self, *args, **kwargs):
            pass

    class _DummyID3NoHeaderError(Exception):
        pass

    mutagen_mp3.MP3 = _DummyTag
    mutagen_mp4.MP4 = _DummyTag
    mutagen_id3.ID3 = _DummyTag
    mutagen_id3.ID3NoHeaderError = _DummyID3NoHeaderError
    mutagen_id3.TIT2 = _DummyTag
    mutagen_id3.TPE1 = _DummyTag
    mutagen_id3.TALB = _DummyTag
    mutagen_id3.TRCK = _DummyTag

    sys.modules["mutagen"] = mutagen_pkg
    sys.modules["mutagen.mp3"] = mutagen_mp3
    sys.modules["mutagen.mp4"] = mutagen_mp4
    sys.modules["mutagen.id3"] = mutagen_id3
    sys.modules["musicbrainzngs"] = types.ModuleType("musicbrainzngs")

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "python-autotagger.py"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module


autotagger = _load_autotagger_module()


class TestPythonAutotaggerHelpers(unittest.TestCase):
    def test_parse_filename_strips_leading_context_label_with_double_space(self):
        result = autotagger.parse_filename(
            "ELECTRO SWING  Caro Emerald - Tangled Up (Odd Chap Bootleg).m4a"
        )

        self.assertEqual(result["artist"], "Caro Emerald")
        self.assertEqual(result["title"], "Tangled Up Odd Chap Bootleg")
        self.assertEqual(result["confidence"], 90)

    def test_parse_filename_preserves_collaborator_comma(self):
        result = autotagger.parse_filename(
            "Odd Chap, Alanna Lyes - Blaze (Electro Swing).m4a"
        )

        self.assertEqual(result["artist"], "Odd Chap, Alanna Lyes")
        self.assertEqual(result["title"], "Blaze Electro Swing")

    def test_artist_query_candidates_expand_common_collaboration_forms(self):
        candidates = autotagger._artist_query_candidates("VICO NEO x ODD CHAP")

        self.assertEqual(candidates[0], "VICO NEO x ODD CHAP")
        self.assertIn("VICO NEO", candidates)
        self.assertIn("ODD CHAP", candidates)

    def test_title_retry_variants_keep_original_and_add_search_only_fallbacks(self):
        variants = autotagger._title_retry_variants("Antics 2017 Re-Edit")

        self.assertEqual(variants[0], "Antics 2017 Re-Edit")
        self.assertIn("Antics", variants)

    def test_leading_context_label_does_not_strip_plain_phrase_without_separator(self):
        value = autotagger._strip_leading_context_label("Electro Swing Fever")

        self.assertEqual(value, "Electro Swing Fever")


if __name__ == "__main__":
    unittest.main()
