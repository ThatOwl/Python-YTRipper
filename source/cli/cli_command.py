import sys
import os
import argparse
import logging

#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cli.cli_base import CLIBase

from core.logger import get_logger
from core.pytube_interface import DownloadOptions, YouTubeDownloader as YTD
from core.os_interactions import OSInteractions
from core.utils import QUALITY_ALIAS_MAP, COMMON_AUDIO_ABR, COMMON_VIDEO_RESOLUTIONS


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
        parser = argparse.ArgumentParser(description="YouTube Video/Playlist Downloader", add_help=False)
        parser.add_argument('url', help='YouTube video or playlist URL')
        parser.add_argument('-h', '--help', action='help', help='Show this help message and exit')
        parser.add_argument('-i', '--info', action='store_true', help='Print video/playlist info and exit')
        parser.add_argument('-a', '--audio', action='store_true', help='Download audio only')
        parser.add_argument('-a3', '--audio_mp3', action='store_true', help='Download audio as MP3')
        parser.add_argument('-q', '--quality', type=str, help='Preferred quality (e.g., [h]igh, [m]edium, [l]ow)')
        parser.add_argument('-r', '--resolution', type=str, help='Preferred video resolution (e.g., 1080p, 720p) => OVERRIDES quality!')
        parser.add_argument('-au', '--abr', type=str, help='Preferred audio bitrate (e.g., 128k, 192k) => OVERRIDES quality!')
        parser.add_argument('-o', '--output', type=str, help='Output directory: supports ~ expansion')
        parser.add_argument('-w', '--warnme', type=str, help='Set warning prompts (true/false)')

        return parser

    #TODO: FIXME: not working properly
    #--- INACTIVE !
    def enable_argcomplete(self, parser: argparse.ArgumentParser):
        """Attempt to enable argcomplete if installed."""
        try:
            import argcomplete
            from argcomplete.completers import DirectoriesCompleter
            # Assign completers (once)
            comp = DirectoriesCompleter()
            for action in parser._actions:
                if action.dest == "output":
                    pass
                    #action.completer = DirectoriesCompleter()
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

        if args.resolution:
            self.preferences["preferred_resolution"] = args.resolution
            
            resolution_key = args.resolution.lower()
            mapped_resolution = COMMON_VIDEO_RESOLUTIONS.get(resolution_key)
            if mapped_resolution:
                self.preferences["preferred_resolution"] = mapped_resolution
            else:
                logger.warning(f"Unknown quality alias '{args.quality}'; ignoring.")
        
        if args.abr:
            abr_key = args.abr.lower()
            mapped_abr = COMMON_AUDIO_ABR.get(abr_key)
            if mapped_abr:
                self.preferences["preferred_abr"] = mapped_abr
            else:
                logger.warning(f"Unknown audio bitrate alias '{args.abr}'; ignoring.")
            
        if args.quality:
            quality_key = args.quality.lower()
            mapped_quality = QUALITY_ALIAS_MAP.get(quality_key)
            if mapped_quality:
                self.preferences["preferred_audio_quality"] = mapped_quality
                self.preferences["preferred_video_quality"] = mapped_quality
            else:
                logger.warning(f"Unknown quality alias '{args.quality}'; ignoring.")

        if args.warnme or self.preferences.get('warn_me', False):
            self.preferences["warn_me"] = args.warnme.lower() in ('true', '1', 'yes', 'y')
            print("Loaded Preferences: ")
            for key, value in self.preferences.items():
                print(f"{key}: {value}")

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