import sys
import os
import argparse

from cli.cli_base import CLIBase
from core.logger import get_logger
from core.pytube_interface import YouTubeDownloader as YTD
from core.utils import DownloadOptions, QUALITY_ALIAS_MAP, COMMON_AUDIO_ABR, COMMON_VIDEO_RESOLUTIONS
from core.os_interactions import OSInteractions
import core.preferences as preferences

logger = get_logger(__name__, 'cli_com_debug.log')

class CommandCLI(CLIBase):
    def __init__(self):
        super().__init__()
        self.os = OSInteractions()
        self.ytd = YTD()
        # Load preferences from file
        self.preferences = self.os.read_preferences()
        self.options = DownloadOptions.from_preferences(self.preferences)
        self.parser = self.build_parser()
        self.enable_argcomplete(self.parser)
    
    def build_parser(self) -> argparse.ArgumentParser:
        """Build argument parser with defaults from loaded preferences."""
        parser = argparse.ArgumentParser(
            description="YouTube Video/Playlist Downloader",
            add_help=False,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="Examples:\n  yt_ripper <URL> -a -q high\n  yt_ripper <URL> -r 1080p -o ~/Downloads"
        )
        
        parser.add_argument('url', help='YouTube video or playlist URL')
        parser.add_argument('-h', '--help', action='help', help='Show this help message and exit')
        parser.add_argument('-i', '--info', action='store_true', help='Print video/playlist info and exit')
        parser.add_argument('-a', '--audio_only', action='store_true', default=self.options.audio_only)
        parser.add_argument('-a3', '--audio_mp3', action='store_true', default=self.options.audio_mp3)
        parser.add_argument('-q', '--preferred_video_quality', type=str, default=self.options.preferred_video_quality,
                           help=f'Quality: {", ".join(set(QUALITY_ALIAS_MAP.values()))}')
        parser.add_argument('-r', '--preferred_resolution', type=str, default=self.options.preferred_resolution,
                           help=f'Resolution: {", ".join(COMMON_VIDEO_RESOLUTIONS.keys())}')
        parser.add_argument('-au', '--preferred_abr', type=str, default=self.options.preferred_abr,
                           help=f'Audio bitrate: {", ".join(COMMON_AUDIO_ABR.keys())}')
        #FIXME
        parser.add_argument('-o', '--default_download_directory', type=str, default=self.options.default_download_directory,
                           help='Output directory (supports ~ expansion)')
        parser.add_argument('-w', '--warn_me', type=str, default=str(self.options.warn_me),
                           help='Enable warning prompts (true/false)')
        parser.add_argument('--save-config', action='store_true', help='Save current options to config file')
        
        return parser

    def enable_argcomplete(self, parser: argparse.ArgumentParser):
        """Attempt to enable argcomplete if installed."""
        try:
            import argcomplete
            argcomplete.autocomplete(parser)
        except ImportError:
            pass

    def run(self, command: str) -> int:
        """Process a command string for downloading YouTube videos or playlists."""
        try:
            args = self.parser.parse_args(command.split())
        except SystemExit:
            logger.error("Invalid command or arguments.")
            return 1

        # Build dict of args to update options
        args_dict = {
            'audio_only': args.audio_only,
            'audio_mp3': args.audio_mp3,
            'preferred_video_quality': args.preferred_video_quality or None,
            'preferred_resolution': args.preferred_resolution or None,
            'preferred_abr': args.preferred_abr or None,
            'default_download_directory': args.default_download_directory or None,
            'warn_me': args.warn_me.lower() in ('true', '1', 'yes', 'y') if args.warn_me else self.options.warn_me,
        }
        
        # Update options from CLI args
        self.options.update_from_dict(args_dict)
        
        # Map quality aliases to preferred values
        if self.options.preferred_video_quality:
            qual_key = QUALITY_ALIAS_MAP.get(self.options.preferred_video_quality.lower())
            if qual_key:
                self.options.preferred_video_quality = qual_key
            else:
                logger.warning(f"Unknown quality alias '{self.options.preferred_video_quality}'; ignoring.")
                self.options.preferred_video_quality = ""
        
        if self.options.preferred_abr:
            abr_key = self.options.preferred_abr.lower()
            mapped_abr = COMMON_AUDIO_ABR.get(abr_key)
            if mapped_abr:
                self.options.preferred_abr = mapped_abr
            else:
                logger.warning(f"Unknown audio bitrate '{self.options.preferred_abr}'; ignoring.")
                self.options.preferred_abr = ""
        
        if self.options.preferred_resolution:
            res_key = self.options.preferred_resolution.lower()
            mapped_res = COMMON_VIDEO_RESOLUTIONS.get(res_key)
            if mapped_res:
                self.options.preferred_resolution = mapped_res
            else:
                logger.warning(f"Unknown resolution '{self.options.preferred_resolution}'; ignoring.")
                self.options.preferred_resolution = ""
        
        # Save config if requested
        if args.save_config:
            self.preferences = {k: getattr(self.options, k) for k in self.options.__dataclass_fields__}
            self.os.write_preferences(self.preferences)
            print(f"✓ Config saved to {preferences.PATH_TO_PREFERENCES}")
        
        # Display preferences if warn_me is enabled
        if self.options.warn_me:
            print("Loaded Preferences:")
            for key, value in self.options.to_dict().items():
                print(f"  {key}: {value}")
        
        # Expand path
        expanded_download_dir = self.os.expand_path(self.options.default_download_directory)
        
        if args.info:
            print("Fetching video/playlist info...")
            try:
                self.ytd.info(url=args.url, output=print)
            except Exception as e:
                logger.error(f"Failed to fetch info: {e}")
                return 1
        else:            
            print("------ Starting Action ------") # as it is not just a (multiple) download(s)
            try:
                self.ytd.download(url=args.url, download_dir=expanded_download_dir, options=self.options)
            except Exception as e:
                logger.error(f"Download failed: {e}")
                return 1

        print("------ Action complete ------")
        return 0