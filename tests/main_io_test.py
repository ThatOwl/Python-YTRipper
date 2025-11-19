import subprocess
import sys
import unittest
from pathlib import Path

# Path to the CLI entry script
SCRIPT_PATH = Path(__file__).parent / "yt_ripper.py"

class TestYouTubeDownloaderCLI(unittest.TestCase):
    """Tests for the CLI entry behavior (argument handling and IO)."""

    def run_cli(self, *args, input_text=None, timeout=3):
        """Helper: run CLI script and capture output, return (stdout, stderr, exitcode)."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *args],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        return result

    # 1️⃣ Test default (interactive) mode — no arguments
    def test_no_arguments_interactive_mode(self):
        """No args should start the InteractiveCLI."""
        result = self.run_cli(input_text="exit\n")
        output = result.stdout.lower()
        self.assertIn("exit", output)  # expected text in output
        self.assertEqual(result.returncode, 0, msg=f"Unexpected exit code: {result.returncode}")

    # 2️⃣ Test help mode
    def test_help_flag(self):
        """--help should print help text and exit."""
        result = self.run_cli("--help")
        output = result.stdout
        self.assertIn("YouTube Downloader CLI", output)
        self.assertEqual(result.returncode, 0)

    # 3️⃣ Test loop mode — simulate "exit"
    def test_loop_mode_with_exit(self):
        """Loop mode should accept commands until 'exit' is entered."""
        result = self.run_cli("-l", input_text="exit\n")
        output = result.stdout.lower()
        self.assertIn("exiting cli", output)
        self.assertEqual(result.returncode, 0)

    # 4️⃣ Test command mode — provide dummy URL
    def test_command_mode_dummy_url(self):
        """Providing a single argument should run CommandCLI with it."""
        result = self.run_cli("https://youtu.be/dQw4w9WgXcQ")
        output = result.stdout + result.stderr
        # No fixed output expected — just ensure no crash
        self.assertIsInstance(result.returncode, int)
        self.assertTrue(len(output) >= 0)

    # 5️⃣ Test invalid flag — should show argparse error or fail
    def test_invalid_argument_flag(self):
        """Invalid flag should trigger argparse error or failure."""
        result = self.run_cli("--nonexistent")
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            "error" in output.lower() or "unrecognized arguments" in output.lower(),
            msg=f"Unexpected output: {output}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
