# ...existing code...
import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.core.logger import get_logger
from source.core.pytube_interface import DownloadOptions, YouTubeDownloader as YTD
from source.core.os_interactions import OSInteractions
from source.core import preferences

logger = get_logger(__name__, 'cli_debug.log')

class CLInterface:
    def __init__(self):
        self.os = OSInteractions()                  # helper instance
        self.preferences = self.os.read_preferences()  # load prefs once
        self.ytd = YTD(os_handler=self.os)

        self.parser = self.build_parser()
        self.enable_argcomplete(self.parser)
    
    def clear_dialog(self, dir_path: str) -> None:
        """Prompt the user for confirmation before clearing a directory.
        Args:
            dir_path (str): Path to the directory to be cleared.
        """
        # discrepacy of print and logger on purpose -> user should only see print
        if self.preferences.get("warn_me", True):
            print(f"Are you sure you want to clear the directory: {dir_path} ? (y/n)")
            confirmation = input().strip().lower()
            if confirmation.lower() in {'y', 'yes'}:
                self.os.clear_directory(dir_path)
                logger.debug(f"Cleared directory: {dir_path}")
            else: 
                logger.debug("Directory clear operation cancelled.")
        else:
            self.os.clear_directory(dir_path)
            logger.debug(f"Cleared directory without confirmation: {dir_path}")
        
        return

    def build_parser(self) -> argparse.ArgumentParser:
        """Build and return the argument parser for command-line options.
        Returns:
            argparse.ArgumentParser: Configured argument parser.
        """
        parser = argparse.ArgumentParser(description="YouTube Video/Playlist Downloader", add_help=False)
        parser.add_argument('url', help='YouTube video or playlist URL')
        parser.add_argument('-a', '--audio', action='store_true', help='Download audio only')
        parser.add_argument('-i', '--info', action='store_true', help='Print video/playlist info and exit')
        parser.add_argument('-cl', '--clear_logs', action='store_true', help='Clear log files before downloading')
        parser.add_argument('-c', '--clear', action='store_true', help='Clear download directory before downloading')
        parser.add_argument('-o', '--output', type=OSInteractions().expand_path, help='Output directory: supports ~ expansion')
        parser.add_argument('-h', '--help', action='help', help='Show this help message and exit')
        return parser

    def enable_argcomplete(self, parser):
        """Attempt to enable argcomplete if installed."""
        try:
            import argcomplete
            from argcomplete.completers import DirectoriesCompleter
            # Assign completers (once)
            for action in parser._actions:
                if action.dest == "output":
                    action.completer = DirectoriesCompleter()
            argcomplete.autocomplete(parser)
        except ImportError:
            pass

    # ----------------------------
    # Interactive / menu features
    # ----------------------------
    def _show_menu(self) -> None:
        print("\nPython-YTRipper - interactive menu")
        print("1) Edit presets")
        print("2) Download (single URL)")
        print("3) Batch import (file with URLs)  [TODO implement parsing formats]")
        print("4) Show current presets")
        print("5) Return to prompt")
        print("q) Quit")

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

    def download_flow(self) -> None:
        """Interactive single-download flow that reuses downloader and prefs."""
        self.preferences = self.os.read_preferences()
        url = input("Enter YouTube video/playlist URL: ").strip()
        if not url:
            print("No URL entered.")
            return
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

    def interactive_menu(self) -> None:
        """Interactive menu loop that coexists with the prompt-based mode."""
        while True:
            self._show_menu()
            choice = input("Select option: ").strip().lower()
            if choice in ("1", "edit", "e"):
                self.edit_presets()
            elif choice in ("2", "download", "d"):
                self.download_flow()
            elif choice in ("3", "batch", "b"):
                path = input("Path to batch file (.txt/.csv/.xlsx): ").strip()
                if path:
                    self.process_batch_file(path)
            elif choice in ("4", "show", "s"):
                self.show_presets()
            elif choice in ("5", "return", "r"):
                return
            elif choice in ("q", "quit", "exit"):
                print("Exiting.")
                raise SystemExit(0)
            else:
                print("Unknown option.")

    # ----------------------------
    # Existing prompt/argparse flow
    # ----------------------------
    def process_command(self, command:str) -> None:
        """Process a command string for downloading YouTube videos or playlists."""
        # keep the original parser-based behavior intact
        try:
            args = self.parser.parse_args(command.split())
        except SystemExit:
            logger.error("Invalid command or arguments.")
            return

        # Update preferences based on command-line arguments
        self.preferences["audio_only"] = True if args.audio else self.preferences.get("audio_only", True)
        self.preferences["default_download_directory"] = args.output if args.output else self.preferences.get("default_download_directory", "./temp_ripper_downloads")
        #DELETEME
        print(f"Download directory set to: {self.preferences['default_download_directory']}")
        
        if args.clear: #FIXME: not working properly
            self.clear_dialog(args.dir)

        if args.clear_logs: #FIXME: not working properly
            self.os.clear_logs()
            logger.debug(f"Cleared log files before downloading.")

        if args.info:
            print("Fetching video/playlist info...")
            try:
                self.ytd.info(url=args.url)
            except Exception as e:
                logger.error(f"Failed to fetch info: {e}")
            return
        else: 
            print("------ Starting action ------")
            try:
                # Always expand the download directory before passing to downloader
                expanded_download_dir = self.os.expand_path(self.preferences["default_download_directory"])
                self.ytd.download(url=args.url, download_dir=expanded_download_dir, options=DownloadOptions.from_preferences(self.preferences))
            except Exception as e:
                #logger.error(f"Download failed: {e}")
                return

        print("------ End of action ------")

def main():
    cli = CLInterface()

    print("YouTube Downloader CLI (type 'exit' or '(q)uit' to leave)")
    print("Type 'menu' to open the interactive menu.")
    print("Usage: <url> [-a] [-i] [-cl] [-c] [-o <dir>]")
    print("!! '-c' it will delete EVERYTHING in <dir> !!")
    
    while True:
        try:
            command = input("yt-ripper> ").strip()
        except EOFError:
            print("\nExiting CLI.")
            break
        if command.lower() in ('exit', 'quit', 'q'):
            print("\n Exiting CLI. \n\n")
            break
        if command.lower() in ('menu', 'm', 'interactive'):
            try:
                cli.interactive_menu()
            except SystemExit:
                break
            continue
        # support quick batch invocation: "batch path/to/file"
        if command.lower().startswith("batch "):
            _, _, path = command.partition(" ")
            cli.process_batch_file(path.strip())
            continue
        if not command:
            continue


        cli.process_command(command)
    
if __name__ == "__main__":
    main()