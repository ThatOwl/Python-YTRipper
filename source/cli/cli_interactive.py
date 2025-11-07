# ...existing code...
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.cli.cli_base import CLIBase

from source.core.logger import get_logger
from source.core.utils import DownloadOptions
from source.core import preferences


logger = get_logger(__name__, 'cli_inter_debug.log')


class InteractiveCLI(CLIBase):
    """
    Interactive CLI with two-step workflow:
      1) Edit presets (preferences)
      2) Download (uses current presets)
    """

    def __init__(self):
        super().__init__()
        
    def _show_menu(self) -> None:
        print("\nPython-YTRipper")
        print("1) Edit presets")
        print("2) Download")
        print("3) Show current presets")
        print("4) Quit")

    def _display_choice_line(self, key: str, descr: str, choices: list) -> None:
        """Print a compact line describing available choices for a preference."""
        # Format: key: [skip] | [0] - val0 | [1] - val1 ...
        parts = ["[skip]"]
        for i, val in enumerate(choices):
            parts.append(f"[{i}] - {val}")
        print(f"{key}: " + " | ".join(parts))
        if descr:
            print(f"  {descr}")

    def edit_presets(self) -> None:
        """Interactive editor for preferences (shows exhaustive choices where appropriate)."""
        prefs = dict(preferences.DEFAULT_PREFS)  # canonical keys/order
        current = self.os.read_preferences()
        # always reload current for editing
        self.preferences = current

        print("\nEditing presets (leave blank to keep current value)\n")

        for key, default in prefs.items():
            descr = ""  # could be extended per-key
            # Provide exhaustive choices for known keys
            if key == "loglevel":
                choices = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                self._display_choice_line(key, "Logger verbosity (console).", choices)
                raw = input(f"Select {key} (index or name) [{self.preferences.get(key, default)}]: ").strip()
                if raw == "":
                    continue
                # accept numeric index or name
                if raw.isdigit():
                    idx = int(raw)
                    if 0 <= idx < len(choices):
                        self.preferences[key] = choices[idx]
                else:
                    if raw.upper() in choices:
                        self.preferences[key] = raw.upper()
                continue

            if isinstance(default, bool):
                choices = ["False", "True"]
                self._display_choice_line(key, "Boolean option.", choices)
                raw = input(f"Set {key} (0/1) [{self.preferences.get(key, default)}]: ").strip()
                if raw == "":
                    continue
                if raw in ("0", "false", "False"):
                    self.preferences[key] = False
                elif raw in ("1", "true", "True"):
                    self.preferences[key] = True
                else:
                    print("  Unrecognized input; skipping.")
                continue

            # path-like string (download directory)
            if key == "default_download_directory":
                print(f"{key}: string path (current: {self.preferences.get(key, default)})")
                print("  Short explanation: default place where downloads are stored (supports ~ expansion).")
                raw = input("Enter new path (or empty to keep): ").strip()
                if raw == "":
                    continue
                # expand and normalize
                newp = str(self.os.expand_path(raw))
                self.preferences[key] = newp
                print(f"  Set {key} -> {newp}")
                continue

            # other strings: accept free text, explain purpose
            if isinstance(default, str):
                print(f"{key}: string (current: {self.preferences.get(key, default)})")
                print("  Short explanation: free-text preference, leave empty to keep current.")
                raw = input("Enter new value (or empty to keep): ").strip()
                if raw == "":
                    continue
                self.preferences[key] = raw
                continue

            # fallback: skip unknown types
            print(f"{key}: (unsupported type for interactive edit)")

        # write back preferences and reload
        try:
            self.os.write_preferences(self.preferences)
            logger.info("Preferences saved.")
        except Exception as e:
            logger.error("Failed to save preferences: %s", e)
        # reload into instance
        self.preferences = self.os.read_preferences()
        print("Presets updated.\n")

    def show_presets(self) -> None:
        self.preferences = self.os.read_preferences()
        print("\nCurrent presets:")
        for k, v in self.preferences.items():
            print(f"  {k}: {v}")
        print("")

    def download_flow(self) -> None:
        # reload preferences to use most recent values
        self.preferences = self.os.read_preferences()
        print("\nDownload mode (uses current presets).")
        url = input("Enter YouTube video or playlist URL: ").strip()
        if not url:
            print("No URL entered. Returning to main menu.")
            return
        # ask whether to override audio_only transiently
        default_audio = self.preferences.get("audio_only", preferences.DEFAULT_PREFS["audio_only"])
        raw = input(f"Audio only? [y/N] (current default: {default_audio}): ").strip().lower()
        if raw in ("y", "yes"):
            self.preferences["audio_only"] = True
        elif raw in ("n", "no"):
            self.preferences["audio_only"] = False
        # Expand download dir
        raw_dl = self.preferences.get("default_download_directory", preferences.DEFAULT_PREFS["default_download_directory"])
        expanded_download_dir = str(self.os.expand_path(raw_dl))
        print(f"Download directory: {expanded_download_dir}")

        opts = DownloadOptions.from_preferences(self.preferences)
        print("Starting download (press Ctrl-C to abort)...")
        try:
            self.ytd.download(url=url, download_dir=expanded_download_dir, options=opts)
        except KeyboardInterrupt:
            print("\nDownload interrupted by user.")
        except Exception as e:
            logger.error("Download failed: %s", e)

    def run(self) -> None:
        # main interactive loop
        while True:
            self._show_menu()
            choice = input("Select an option: ").strip()
            if choice in ("1", "edit", "e"):
                self.edit_presets()
            elif choice in ("2", "download", "d"):
                self.download_flow()
            elif choice in ("3", "show", "s"):
                self.show_presets()
            elif choice in ("4", "q", "quit", "exit"):
                print("Exiting.")
                break
            else:
                print("Unknown option. Please choose 1-4.")


def main():
    cli = InteractiveCLI()
    # reload preferences once more to ensure latest on startup
    cli.preferences = cli.os.read_preferences()
    print("Welcome to Python-YTRipper")
    cli.run()


if __name__ == "__main__":
    main()