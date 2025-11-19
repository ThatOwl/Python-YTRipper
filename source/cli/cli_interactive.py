# import sys
import os
# import argparse

from cli.cli_base import CLIBase

from core.logger import get_logger
from core.utils import DownloadOptions
import core.preferences as preferences


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
        print("\nPython-YTRipper - interactive menu")
        print("1) [E]dit presets")
        print("2) [S]how current presets")
        print("3) [D]ownload Single")
        print("4) Download [M]ultiple (loop)")
        print("5) [B]atch import (file with URLs)  [TODO implement parsing formats]")
        print("q) [Q]uit")

    def edit_presets(self) -> None:
        """Interactive editor for preferences. Shows exhaustive choices for known keys."""
        # reload latest prefs before editing
        self.preferences = self.os.read_preferences()

        print("\nEditing presets (leave blank to keep current value)\n")
        defaults = preferences.DEFAULT_PREFS

        for key, default in defaults.items():
            if key == "loglevel":
                choices = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                print(f"{key}: " + " | ".join(f"[{i}] {v}" for i, v in enumerate(choices)))
                print("  Logger verbosity (console).")
                raw = input(f"Select {key} (index or name) [{self.preferences.get(key, default)}]: ").strip()
                if raw == "":
                    continue
                if raw.isdigit():
                    idx = int(raw)
                    if 0 <= idx < len(choices):
                        self.preferences[key] = choices[idx]
                else:
                    if raw.upper() in choices:
                        self.preferences[key] = raw.upper()
                continue

            if isinstance(default, bool):
                print(f"{key}: [0] False | [1] True")
                print("  Boolean option.")
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

            if key == "default_download_directory":
                print(f"{key}: path (current: {self.preferences.get(key, default)})")
                print("  Default place where downloads are stored (supports ~ expansion).")
                raw = input("Enter new path (or empty to keep): ").strip()
                if raw == "":
                    continue
                newp = str(self.os.expand_path(raw))
                self.preferences[key] = newp
                print(f"  Set {key} -> {newp}")
                continue

            # fallback for strings
            if isinstance(default, str):
                print(f"{key}: string (current: {self.preferences.get(key, default)})")
                print("  Short explanation: free-text preference, leave empty to keep current.")
                raw = input("Enter new value (or empty to keep): ").strip()
                if raw == "":
                    continue
                self.preferences[key] = raw
                continue

            # unsupported type
            print(f"{key}: (unsupported type for interactive edit)")

        # persist changes
        try:
            self.os.write_preferences(self.preferences)
            logger.info("Preferences saved.")
        except Exception as e:
            logger.error("Failed to save preferences: %s", e)

        # reload to ensure canonicalization
        self.preferences = self.os.read_preferences()
        print("Presets updated.\n")

    def show_presets(self) -> None:
        self.preferences = self.os.read_preferences()
        print("\nCurrent presets:")
        for k, v in self.preferences.items():
            print(f"  {k}: {v}")
        print("")

    def download_flow(self, adjust_preferences: bool = False) -> None:
        """Interactive single-download flow that reuses downloader and prefs."""

        url = input("Enter YouTube video/playlist URL: ").strip()
        if not url:
            print("No URL entered.")
            return
        
        if adjust_preferences:
            raw = input(f"Audio only? (leave empty to use preset {self.preferences.get('audio_only')} ) [y/N]: ").strip().lower()
            if raw in ("y","yes"):
                self.preferences["audio_only"] = True
            elif raw in ("n","no"):
                self.preferences["audio_only"] = False
            dl_dir = self.preferences.get("default_download_directory", preferences.DEFAULT_PREFS["default_download_directory"])
            expanded = str(self.os.expand_path(dl_dir))
            print(f"Using download dir: {expanded}")

        opts = DownloadOptions.from_preferences(self.preferences)
        try:
            self.ytd.download(url=url, download_dir=expanded, options=opts)
        except Exception as e:
            logger.error("Download failed: %s", e)
    
    def download_loop(self) -> None:
        """Simple loop to download multiple URLs sequentially."""
        
        print("Entering download loop. CTRL-C to exit.")
        
        while True:
            self.download_flow()

    def process_batch_file(self, path: str) -> None:
        """
        Placeholder for batch import processing.
        Future: support .txt/.csv/.xlsx with optional per-line overrides (audio-only, output-dir).
        Current: simple text file with one URL per line.
        """
        if not os.path.exists(path):
            print("Batch file not found:", path)
            return
        urls = []
        try:
            if path.lower().endswith(".txt"):
                with open(path, 'r', encoding='utf-8') as fh:
                    for ln in fh:
                        ln = ln.strip()
                        if ln:
                            urls.append(ln)
            else:
                # TODO: implement CSV / XLSX parsing with optional column mapping
                print("Batch format not yet implemented for this extension. Only .txt supported for now.")
                return
        except Exception as e:
            logger.error("Failed reading batch file: %s", e)
            return

        if not urls:
            print("No URLs found in batch file.")
            return

        print(f"Found {len(urls)} entries. Starting sequential download (CTRL-C to stop).")
        opts = DownloadOptions.from_preferences(self.os.read_preferences())
        for u in urls:
            try:
                self.ytd.download(url=u, download_dir=str(self.os.expand_path(self.preferences.get("default_download_directory"))), options=opts)
            except Exception as e:
                logger.error("Failed downloading %s: %s", u, e)
                # continue with next

    def run(self) -> None:
        """Interactive menu loop that coexists with the prompt-based mode."""
        while True:
            self._show_menu()
            choice = input("Select option: ").strip().lower()
            if choice in ("1", "edit", "e"):
                self.edit_presets()
            elif choice in ("2", "show", "s"):
                self.show_presets()
            elif choice in ("3", "single", "d"):
                self.download_flow()
            elif choice in ("4", "multiple", "m"):
                self.download_loop()
            elif choice in ("5", "batch", "b"):
                path = input("Path to batch file (.txt/.csv/.xlsx): ").strip()
                if path:
                    self.process_batch_file(path)
            elif choice in ("q", "quit", "exit"):
                print("Exiting.")
                raise SystemExit(0)
            else:
                print("Unknown option.")