import argparse
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from cli.interactive_prompt import (
    InteractivePrompt,
    collect_completion_candidates,
    parse_completion_context,
    split_prompt_command,
)


class TestInteractivePrompt(unittest.TestCase):
    @staticmethod
    def _build_tagger_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(add_help=False)
        subparsers = parser.add_subparsers(dest="command")
        parser._completion_default_subcommand = "run"

        run_parser = subparsers.add_parser("run", add_help=False)
        run_parser.add_argument("--idle-timeout")
        run_parser.add_argument("--poll-interval")

        scan_dir_parser = subparsers.add_parser("scan-dir", add_help=False)
        scan_dir_parser.add_argument("--directory")
        scan_dir_parser.add_argument("--scan-scope")

        return parser

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

    def test_split_prompt_command_preserves_windows_backslashes(self):
        tokens = split_prompt_command(r'scan-dir --directory "D:\Music\Target Folder"')

        self.assertEqual(tokens, ["scan-dir", "--directory", r"D:\Music\Target Folder"])

    def test_collect_completion_candidates_suggests_subcommands(self):
        parser = self._build_tagger_parser()

        suggestions = collect_completion_candidates(parser, "sc")

        self.assertIn("scan-dir", suggestions)

    def test_collect_completion_candidates_suggests_subcommand_flags(self):
        parser = self._build_tagger_parser()

        suggestions = collect_completion_candidates(parser, "scan-dir --sc")

        self.assertIn("--scan-scope", suggestions)

    def test_collect_completion_candidates_uses_default_run_subcommand_for_flags(self):
        parser = self._build_tagger_parser()

        suggestions = collect_completion_candidates(parser, "--idle")

        self.assertIn("--idle-timeout", suggestions)

    def test_collect_completion_candidates_suggests_auth_session_boolean_values(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--auth-session")

        suggestions = collect_completion_candidates(parser, "--auth-session t")

        self.assertIn("true", suggestions)


if __name__ == "__main__":
    unittest.main()
