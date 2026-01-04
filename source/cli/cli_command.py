import sys
import os
import argparse
import logging

#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cli.cli_base import CLIBase

from core.logger import get_logger
from core.pytube_interface import DownloadOptions, YouTubeDownloader as YTD
from core.os_interactions import OSInteractions


logger = get_logger(__name__, 'cli_com_debug.log')

class CommandCLI(CLIBase):
    def __init__(self):
        super().__init__()
        self.parser = self.build_parser()
        self.enable_argcomplete(self.parser)
    
    def build_parser(self) -> argparse.ArgumentParser:
        """Build and return the argument parser for command-line options.
        Returns:
            argparse.ArgumentParser: Configured argument parser.
        """
        parser = argparse.ArgumentParser(description="YouTube Video/Playlist Downloader", add_help=False^)
        parser.add_argument('url', help='YouTube video or playlist URL')
        parser.add_argument('-a', '--audio', action='store_true', help='Download audio only')
        parser.add_argument('-a3', '--audio_mp3', action='store_true', help='Download audio as MP3')
        parser.add_argument('-i', '--info', action='store_true', help='Print video/playlist info and exit')
        parser.add_argument('-c', '--clear', action='store_true', help='Clear download directory before downloading')
        parser.add_argument('-o', '--output', type=str, help='Output directory: supports ~ expansion')
        parser.add_argument('-h', '--help', action='help', help='Show this help message and exit')
        
        act = parser.
        return parser

    def enable_argcomplete(self, parser: argparse.ArgumentParser):
        """Attempt to enable argcomplete if installed."""
        try:
            import argcomplete
            from argcomplete.completers import DirectoriesCompleter
            # Assign completers (once)
            comp = DirectoriesCompleter()
            argp = argparse.
            for action in parser._actions:
                if action.dest == "output":
                    action.
                    action.completer = DirectoriesCompleter()
            argcomplete.autocomplete(parser)
        except ImportError:
            pass

    def run(self, command:str) -> int:
        """Process a command string for downloading YouTube videos or playlists.
        #this need to be deleted ... again
        Args:
            command (str): The command string input by the user.
        """

        try:
            args = self.parser.parse_args(command.split())
        except SystemExit:
            logger.error("Invalid command or arguments.")
            return 1

        # Update preferences based on command-line arguments
        self.preferences["audio_only"] = True if args.audio else self.preferences.get("audio_only", False)
        if args.audio_mp3:
            self.preferences["audio_mp3"] = True
            self.preferences["audio_only"] = True
        else:
            self.preferences["audio_mp3"] = False
        self.preferences["default_download_directory"] = args.output if args.output else self.preferences.get("default_download_directory", "./temp_ripper_downloads")
        #DELETEME
        print(f"Download directory set to: {self.preferences['default_download_directory']}")
        
        if args.clear: #FIXME: not working properly
            self.clear_dialog(args.dir)

        if args.info:
            print("Fetching video/playlist info...")
            try:
                self.ytd.info(url=args.url, output=print)
            except Exception as e:
                logger.error(f"Failed to fetch info: {e}")
                return 1
        else:
            print("------ Starting action ------")
            try:
                # Always expand the download directory before passing to downloader
                expanded_download_dir = self.os.expand_path(self.preferences["default_download_directory"])
                self.ytd.download(url=args.url, download_dir=expanded_download_dir, options=DownloadOptions.from_preferences(self.preferences))
            except Exception as e:
                #logger.error(f"Download failed: {e}")
                return 1

        print("------ End of action ------")
        return 0