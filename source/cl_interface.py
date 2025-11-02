import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.logger_a_constants import get_logger
from source.pytube_interface import DownloadOptions, YouTubeDownloader as YTD
from source.os_interactions import OSInteractions


logger = get_logger(__name__, 'cli_debug.log')

class CLInterface:
    def __init__(self):
        self.os = OSInteractions()                  # helper instance
        self.preferences = self.os.read_preferences()
        
        #TODO this does not work as intended ... logging level not set properly
        prefs = self.preferences if isinstance(self.preferences, dict) else {}
        level_name = prefs.get("loglevel", "info").upper()
        #DELETEME print(f"Loglevel set to: {level_name}")
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level_name, logging.INFO))
        logger.addHandler(console_handler)
        
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

    def process_command(self, command:str) -> None:
        """Process a command string for downloading YouTube videos or playlists.
        #this need to be deleted ... again
        Args:
            command (str): The command string input by the user.
        """

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
    print("Usage: <url> [-a] [-i] [-cl] [-c] [-o <dir>]")
    print("!! '-c' it will delete EVERYTHING in <dir> !!")
    
    while True:
        """Prompt for user input and process commands until the user decides to exit."""
        try:
            command = input("yt-ripper> ").strip()
        except EOFError:
            print("\nExiting CLI.")
            break
        if command.lower() in ('exit', 'quit', 'q'):
            print("\n Exiting CLI. \n\n")
            break
        if not command:
            continue
        cli.process_command(command)
    
if __name__ == "__main__":
    main()
