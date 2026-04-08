import sys
import os
import argparse
from pathlib import Path

from cli.cli_base import CLIBase
from source.infrastructure.logger import get_logger
from source.domain.pytube_interface import YouTubeDownloader as YTD
from source.infrastructure.utils import DownloadOptions, QUALITY_ALIAS_MAP, COMMON_AUDIO_ABR, COMMON_VIDEO_RESOLUTIONS, parse_bool_string
from source.infrastructure.os_interactions import OSInteractions
import source.infrastructure.preferences as preferences

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
            epilog="Examples:\n  yt_ripper <URL> -a -q high\n  yt_ripper <URL> -r 1080p -o ~/Downloads\n  yt_ripper -f ~/urls.txt -a -q low"
        )
        
        parser.add_argument('url', nargs='?', default=None, help='YouTube video or playlist URL')
        parser.add_argument('-f', '--file', type=str, help='Batch file with URLs (.txt or .csv)')
        parser.add_argument('-h', '--help', action='help', help='Show this help message and exit')
        parser.add_argument('-i', '--info', action='store_true', help='Print video/playlist info and exit')
        parser.add_argument('-a', '--audio_only', type=str, default=str(self.options.audio_only),
                           help='Download audio only (true/false)')
        parser.add_argument('-a3', '--audio_mp3', type=str, default=str(self.options.audio_mp3),
                           help='Convert audio to MP3 (true/false)')
        parser.add_argument('-q', '--preferred_quality', type=str, default=self.options.preferred_video_quality,
                           help=f'Quality: {", ".join(set(QUALITY_ALIAS_MAP.values()))}')
        parser.add_argument('-r', '--preferred_resolution', type=str, default=self.options.preferred_resolution,
                           help=f'Resolution: {", ".join(COMMON_VIDEO_RESOLUTIONS.keys())}')
        parser.add_argument('-au', '--preferred_abr', type=str, default=self.options.preferred_abr,
                           help=f'Audio bitrate: {", ".join(COMMON_AUDIO_ABR.keys())}')
        parser.add_argument('-hf', '--high_fps', type=str, default=str(self.options.preferred_fps),
                           help='Prefer 60fps (true) or 30fps (false), or any (empty/0)')
        parser.add_argument('-o', '--default_download_directory', type=str, default=self.options.default_download_directory,
                           help='Output directory (supports ~ expansion)')
        parser.add_argument('-w', '--warn_me', type=str, default=str(self.options.warn_me),
                           help='Enable warning prompts (true/false)')
        parser.add_argument('-nd', '--no_dir_date', type=str, default=str(self.options.no_dir_date),
                           help='Disable auto date prefix for playlist directory')
        parser.add_argument('--save-config', action='store_true', help='Save current options to config file')
        
        return parser

    def enable_argcomplete(self, parser: argparse.ArgumentParser):
        """Attempt to enable argcomplete if installed."""
        #FIXME
        try:
            import argcomplete
            argcomplete.autocomplete(parser)
        except ImportError:
            pass

    def _parse_fps_preference(self, value: str) -> int:
        """Parse FPS preference from string value.
        Returns 60 for high fps, 30 for low fps, 0 for any.
        """
        if not value or value == '0' or value.lower() in ('', 'any', 'none'):
            return 0
        if parse_bool_string(value):
            return 60
        return 30

    def _apply_options(self, args) -> None:
        """Apply CLI arguments to options (shared logic for single/batch)."""
        args_dict = {
            'audio_only': parse_bool_string(args.audio_only),
            'audio_mp3': parse_bool_string(args.audio_mp3),
            'preferred_video_quality': args.preferred_quality or None,
            'preferred_audio_quality': args.preferred_quality or None,
            'preferred_resolution': args.preferred_resolution or None,
            'preferred_abr': args.preferred_abr or None,
            'preferred_fps': self._parse_fps_preference(args.high_fps),
            'default_download_directory': args.default_download_directory or None,
            'warn_me': parse_bool_string(args.warn_me) if args.warn_me else self.options.warn_me,
            'no_dir_date': parse_bool_string(args.no_dir_date) if args.no_dir_date else self.options.no_dir_date,
        }
        
        self.options.update_from_dict(args_dict)
        
        # Map quality aliases
        if self.options.preferred_video_quality:
            qual_key = QUALITY_ALIAS_MAP.get(self.options.preferred_video_quality.lower())
            if qual_key:
                self.options.preferred_video_quality = qual_key
            else:
                logger.warning(f"Unknown quality alias '{self.options.preferred_video_quality}'; ignoring.")
                self.options.preferred_video_quality = ""
        
        if self.options.preferred_audio_quality:
            qual_key = QUALITY_ALIAS_MAP.get(self.options.preferred_audio_quality.lower())
            if qual_key:
                self.options.preferred_audio_quality = qual_key
            else:
                logger.warning(f"Unknown quality alias '{self.options.preferred_audio_quality}'; ignoring.")
                self.options.preferred_audio_quality = ""
        
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

    def _download_single_url(self, url: str, expanded_dir: Path) -> int:
        """Download a single URL. Returns 0 on success, 1 on failure."""
        try:
            results = self.ytd.download(url=url, download_dir=expanded_dir, options=self.options)
            
            # Display results summary
            if results:
                success_count = sum(1 for r in results if r.success)
                fail_count = len(results) - success_count
                
                # For playlists, show summary
                if len(results) > 1:
                    print(f"\n{'='*50}")
                    print(f"Download Summary: {success_count} succeeded, {fail_count} failed")
                    if fail_count > 0:
                        print("\nFailed downloads:")
                        for result in results:
                            if not result.success:
                                print(f"  {result}")
                    print(f"{'='*50}")
                
                return 0 if fail_count == 0 else 1
            return 0
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            return 1

    def run(self, command: str) -> int:
        """Process a command string for downloading YouTube videos or playlists."""
        try:
            args = self.parser.parse_args(command.split())
        except SystemExit:
            logger.error("Invalid command or arguments.")
            return 1

        # Validate: either URL or --file, not both
        if not args.url and not args.file:
            logger.error("Either provide a URL or use -f/--file for batch processing.")
            return 1
        
        if args.url and args.file:
            logger.error("Cannot specify both URL and --file; choose one.")
            return 1

        # Apply CLI options (will use defaults for missing args)
        self._apply_options(args)
        
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
        
        # BATCH MODE: process file
        if args.file:
            file_path = Path(args.file).expanduser()
            
            if not file_path.exists():
                logger.error(f"Batch file not found: {file_path}")
                return 1
            
            try:
                urls, file_params = self.os.load_batch_urls(file_path)
            except Exception as e:
                logger.error(f"Failed to load batch file: {e}")
                return 1
            
            # Filter out invalid/empty URLs
            valid_urls, skipped_count = self.os.filter_valid_urls(urls)
            
            if valid_urls:
                logger.info(f"Batch file loaded: {len(urls)} total URLs, {skipped_count} invalid/skipped, {len(valid_urls)} valid.")
            
            if not valid_urls:
                logger.warning("No valid URLs found in batch file.")
                return 1
            
            # If file contains params, parse and apply them (but don't override CLI args)
            if file_params:
                try:
                    file_args = self.parser.parse_args(file_params.split())
                    logger.info(f"Batch file parameters: {file_params}")
                    self._apply_options(file_args)
                except SystemExit:
                    logger.warning(f"Invalid params in batch file; using current config: {file_params}")
            
            # Expand download directory AFTER applying batch file parameters
            expanded_download_dir = self.os.expand_path(self.options.default_download_directory)
            logger.info(f"Download directory: {expanded_download_dir}")
            
            print(f"------ Batch Processing {len(valid_urls)} URLs ------")
            success_count = 0
            fail_count = 0
            
            for idx, url in enumerate(valid_urls, 1):
                print(f"\n[{idx}/{len(valid_urls)}] Processing: {url}")
                if self._download_single_url(url, expanded_download_dir) == 0:
                    success_count += 1
                else:
                    fail_count += 1
            
            print(f"\n------ Batch Complete ------")
            print(f"Summary: {success_count} succeeded, {fail_count} failed.")
            return 0 if fail_count == 0 else 1
        
        # SINGLE MODE: process single URL
        else:
            # Expand download directory for single mode
            expanded_download_dir = self.os.expand_path(self.options.default_download_directory)
            logger.info(f"Download directory: {expanded_download_dir}")
            
            if args.info:
                print("Fetching video/playlist info...")
                try:
                    self.ytd.info(url=args.url, output=print)
                except Exception as e:
                    logger.error(f"Failed to fetch info: {e}") 
                    return 1
            else:
                print("------ Starting Download ------")
                return self._download_single_url(args.url, expanded_download_dir)