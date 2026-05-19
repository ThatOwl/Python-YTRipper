import argparse
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from cli.interactive_prompt import InteractivePrompt, parse_completion_context


class TestInteractivePrompt(unittest.TestCase):
    def test_parse_context_detects_path_flag(self):
        context = parse_completion_context("https://example.com -o /tmp/down")

        self.assertEqual(context.active_flag, "-o")
        self.assertEqual(context.current_token, "/tmp/down")
        self.assertTrue(context.expects_path)
        self.assertFalse(context.wants_flag_suggestions)

    def test_parse_context_detects_value_flag(self):
        context = parse_completion_context("https://example.com -q h")

        self.assertEqual(context.active_flag, "-q")
        self.assertEqual(context.current_token, "h")
        self.assertTrue(context.expects_value)
        self.assertFalse(context.expects_path)

    def test_parse_context_detects_pending_flag_completion(self):
        context = parse_completion_context("https://example.com -a true -")

        self.assertIsNone(context.active_flag)
        self.assertEqual(context.current_token, "-")
        self.assertTrue(context.wants_flag_suggestions)

    def test_prompt_toolkit_is_disabled_in_non_tty_contexts(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("-o", "--download_directory")
        prompt = InteractivePrompt(lambda: parser)

        self.assertFalse(prompt.uses_prompt_toolkit)


if __name__ == "__main__":
    unittest.main()
