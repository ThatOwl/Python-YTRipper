
import argparse
import datetime
import shlex
from pathlib import Path
from typing import List

from cli.cli_base import CLIBase

from application.download_orchestrator import DownloadOrchestrator as YTD
from application.media_info_service import MediaInfoService

from domain.video_fetcher import VideoFetcher
from infrastructure.os_interactions import OSInteractions
from infrastructure.url_handler import URLHandler

from utility.logger import get_logger, set_visible_log_level
from utility.utils import (
    DownloadOptions,
    QUALITY_ALIAS_MAP,
    COMMON_AUDIO_ABR,
    COMMON_VIDEO_RESOLUTIONS,
    LOGLEVEL_ALIAS_MAP,
    parse_bool_string,
    DownloadResult
)

import utility.preferences as preferences


logger = get_logger(__name__, "cli_command_debug.log")


class CommandCLI(CLIBase):
    def __init__(self):
        super().__init__()

        # Shared infrastructure/services for this CLI session.
        # Keeping these as attributes makes later GUI/CLI dependency injection easier.
        self.os = OSInteractions()
        self.url_handler = URLHandler() #DELETE ? why is this needed in CLI? => not called
        self.video_fetcher = VideoFetcher() #DELETE ? why is this needed in CLI? => not called

        self.preferences = self.os.read_preferences()
        self.options = DownloadOptions.from_preferences(self.preferences)

        # Normalize persisted config once on startup.
        # This applies visible_loglevel from preferences to already-created visible handlers.
        self._normalize_options()

        self.ytd = YTD(
            os_handler=self.os,
            url_handler=self.url_handler,
            vid_fetcher=self.video_fetcher,
        )

        self.media_info_service = MediaInfoService(
            url_handler=self.url_handler,
            video_fetcher=self.video_fetcher,
        )

        self.parser = self.build_parser()
        self.enable_argcomplete(self.parser)

    def build_parser(self) -> argparse.ArgumentParser:
        """
        Build argument parser.

        Important design choice:
        User-overridable options default to None here.

        That means:
            args.some_option is None  -> user did not provide this option
            self.options.some_option  -> current effective setting from preferences / previous state

        This keeps argument parsing separate from option merging.
        """
        parser = argparse.ArgumentParser(
            description="YouTube Video/Playlist Downloader",
            add_help=False,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=(
                "Examples:\n"
                "  yt_ripper <URL> -a true -q high\n"
                "  yt_ripper <URL> -r 1080p -o ~/Downloads\n"
                "  yt_ripper -f ~/urls.txt -a true -q low\n"
                "  yt_ripper <URL> -vl debug"
            ),
        )

        parser.add_argument(
            "url",
            nargs="?",
            default=None,
            help="YouTube video or playlist URL",
        )

        parser.add_argument(
            "-f",
            "--file",
            type=str,
            default=None,
            help="Batch file with URLs (.txt or .csv)",
        )

        parser.add_argument(
            "-h",
            "--help",
            action="help",
            help="Show this help message and exit",
        )

        parser.add_argument(
            "-i",
            "--info",
            action="store_true",
            help="Print video/playlist info and exit",
        )
        
        parser.add_argument(
            "-lp",
            "--load_preset",
            type=str,
            default=None,
            help="Load default preferences: 'XY' num custom or 'a' audio high, 'vh' video high, 'vl' video low, 't' test mode"
        )

        parser.add_argument(
            "-a",
            "--audio_only",
            type=str,
            default=None,
            help=f"Download audio only (true/false). Current default: {self.options.audio_only}",
        )

        parser.add_argument(
            "-a3",
            "--audio_mp3",
            type=str,
            default=None,
            help=f"Convert audio to MP3 (true/false). Current default: {self.options.audio_mp3}",
        )

        parser.add_argument(
            "-q",
            "--preferred_quality",
            type=str,
            default=None,
            help=(
                f"Quality: {', '.join(sorted(set(QUALITY_ALIAS_MAP.values())))}. "
                f"Current default: {self.options.preferred_video_quality or 'best available'}"
            ),
        )

        parser.add_argument(
            "-r",
            "--preferred_resolution",
            type=str,
            default=None,
            help=(
                f"Resolution: {', '.join(COMMON_VIDEO_RESOLUTIONS.keys())}. "
                f"Current default: {self.options.preferred_resolution or 'best available'}"
            ),
        )

        parser.add_argument(
            "-au",
            "--preferred_abr",
            type=str,
            default=None,
            help=(
                f"Audio bitrate: {', '.join(COMMON_AUDIO_ABR.keys())}. "
                f"Current default: {self.options.preferred_abr or 'best available'}"
            ),
        )

        parser.add_argument(
            "-hf",
            "--high_fps",
            type=str,
            default=None,
            help=(
                "Prefer 60fps (true), 30fps (false), or any (0/any/none). "
                f"Current default: {self.options.preferred_fps}"
            ),
        )

        parser.add_argument(
            "-o",
            "--download_directory",
            type=str,
            default=None,
            help=(
                "Output directory; supports ~ expansion. "
                f"Current default: {self.options.default_download_directory}"
            ),
        )

        parser.add_argument(
            "-nd",
            "--no_dir_date",
            type=str,
            default=None,
            help=(
                "Disable auto date prefix for playlist directory (true/false). "
                f"Current default: {self.options.no_dir_date}"
            ),
        )

        parser.add_argument(
            "-sc",
            "--save-config",
            action="store_true",
            help="Save current effective options to config file",
        )
         
        parser.add_argument(
            "-w",
            "--warn_me",
            type=str,
            default=None,
            help=f"Show loaded preferences before running (true/false). Current default: {self.options.warn_me}",
        )
        
        parser.add_argument(
            "-at",
            "--autotag",
            type=str,
            default=None,
            help=f"Attempt to auto-tag downloaded files with metadata (true/false). Current default: {self.options.autotag}",
        )
        
        parser.add_argument(
            "-sr",
            "--save-results",
            type=str,
            default=None,
            help=f"Save download results to a file (true/false). Default: None",
        )

        parser.add_argument(
            "-vl",
            "--visible-loglevel",
            type=str,
            default=None,
            help=(
                "Set visible log level for CLI output. "
                "Examples: debug, info, warning, error, d, i, w, e. "
                f"Current default: {self.options.visible_loglevel}"
            ),
        )
        
        return parser

    def enable_argcomplete(self, parser: argparse.ArgumentParser) -> None:
        """Attempt to enable argcomplete if installed."""
        try:
            import argcomplete

            argcomplete.autocomplete(parser)
        except ImportError:
            pass

    def _parse_args(self, command: str) -> argparse.Namespace | None:
        """
        Parse a command string.

        shlex.split is safer than command.split because it supports quoted paths:
            -o "~/My Downloads"
        """
        try:
            return self.parser.parse_args(shlex.split(command))
        except SystemExit as exc:
            # argparse uses SystemExit(0) for --help.
            # That is not an error.
            if exc.code == 0:
                return None

            logger.error("Invalid command or arguments.")
            return None

    def _parse_fps_preference(self, value: str) -> int:
        """
        Parse FPS preference.

        Returns:
            60 for high FPS
            30 for low FPS
            0 for any
        """
        if value is None:
            return self.options.preferred_fps

        normalized = str(value).strip().lower()

        if normalized in ("", "0", "any", "none"):
            return 0

        if parse_bool_string(normalized):
            return 60

        return 30

    def _apply_options(self, args: argparse.Namespace) -> None:
        """
        Apply explicitly provided args to self.options.

        argparse defaults are None for user-overridable options.
        Therefore:
            if args.x is not None:
                user or batch params supplied x
            else:
                keep existing self.options.x
        """
        updates = {}

        if args.audio_only is not None:
            updates["audio_only"] = parse_bool_string(args.audio_only)

        if args.audio_mp3 is not None:
            updates["audio_mp3"] = parse_bool_string(args.audio_mp3)

        if args.preferred_quality is not None:
            updates["preferred_video_quality"] = args.preferred_quality
            updates["preferred_audio_quality"] = args.preferred_quality

        if args.preferred_resolution is not None:
            updates["preferred_resolution"] = args.preferred_resolution

        if args.preferred_abr is not None:
            updates["preferred_abr"] = args.preferred_abr

        if args.high_fps is not None:
            updates["preferred_fps"] = self._parse_fps_preference(args.high_fps)

        if args.download_directory is not None:
            updates["default_download_directory"] = self.os.expand_path(args.download_directory)

        if args.warn_me is not None:
            updates["warn_me"] = parse_bool_string(args.warn_me)

        if args.no_dir_date is not None:
            updates["no_dir_date"] = parse_bool_string(args.no_dir_date)

        if args.visible_loglevel is not None:
            updates["visible_loglevel"] = args.visible_loglevel
        
        if args.autotag is not None:
            updates["autotag"] = parse_bool_string(args.autotag)
            
        if args.save_results is not None:
            updates["save_results"] = parse_bool_string(args.save_results)
            
        self.options.update_from_dict(updates)
        self._normalize_options()

    def _normalize_options(self) -> None:
        """
        Normalize final effective options.

        This method is allowed to use if self.options.x checks because it works
        on the final options object, not on raw parser input.
        """
        self._normalize_quality_options()
        self._normalize_audio_bitrate()
        self._normalize_resolution()
        self._normalize_visible_loglevel()
        self._normalize_download_directory()

    def _normalize_download_directory(self) -> None:
        if not self.options.default_download_directory:
            self.options.default_download_directory = str(self.os.expand_path("~/Downloads"))
            return

        self.options.default_download_directory = str(
            self.os.expand_path(self.options.default_download_directory)
        )
        
    def _normalize_quality_options(self) -> None:
        if self.options.preferred_video_quality:
            raw_value = self.options.preferred_video_quality.strip().lower()
            mapped_quality = QUALITY_ALIAS_MAP.get(raw_value)

            if mapped_quality:
                self.options.preferred_video_quality = mapped_quality
            else:
                logger.warning(
                    f"Unknown video quality alias '{self.options.preferred_video_quality}'; ignoring."
                )
                self.options.preferred_video_quality = ""

        if self.options.preferred_audio_quality:
            raw_value = self.options.preferred_audio_quality.strip().lower()
            mapped_quality = QUALITY_ALIAS_MAP.get(raw_value)

            if mapped_quality:
                self.options.preferred_audio_quality = mapped_quality
            else:
                logger.warning(
                    f"Unknown audio quality alias '{self.options.preferred_audio_quality}'; ignoring."
                )
                self.options.preferred_audio_quality = ""

    def _normalize_audio_bitrate(self) -> None:
        if not self.options.preferred_abr:
            return

        raw_value = self.options.preferred_abr.strip().lower()
        mapped_abr = COMMON_AUDIO_ABR.get(raw_value)

        if mapped_abr:
            self.options.preferred_abr = mapped_abr
        else:
            logger.warning(f"Unknown audio bitrate '{self.options.preferred_abr}'; ignoring.")
            self.options.preferred_abr = ""

    def _normalize_resolution(self) -> None:
        if not self.options.preferred_resolution:
            return

        raw_value = self.options.preferred_resolution.strip().lower()
        mapped_resolution = COMMON_VIDEO_RESOLUTIONS.get(raw_value)

        if mapped_resolution:
            self.options.preferred_resolution = mapped_resolution
        else:
            logger.warning(f"Unknown resolution '{self.options.preferred_resolution}'; ignoring.")
            self.options.preferred_resolution = ""

    def _normalize_visible_loglevel(self) -> None:
        """
        Normalize and apply the visible loglevel.

        File logs should remain DEBUG. This only changes visible handlers,
        such as console and later GUI handlers.
        """
        raw_level = self.options.visible_loglevel or "WARNING"
        level_key = str(raw_level).strip().upper()

        mapped_level = LOGLEVEL_ALIAS_MAP.get(level_key)

        if mapped_level is None:
            logger.warning(
                f"Unknown visible log level '{raw_level}'; falling back to WARNING."
            )
            mapped_level = "WARNING"

        self.options.visible_loglevel = mapped_level

        try:
            set_visible_log_level(mapped_level)
        except ValueError as e:
            logger.error(f"Failed to set visible log level '{mapped_level}': {e}")

    def _save_config_if_requested(self, args: argparse.Namespace) -> None:
        if not args.save_config:
            return

        self.preferences = self.options.to_dict()
        self.os.write_preferences(self.preferences)
        print(f"✓ Config saved to {preferences.PATH_TO_PREFERENCES}")

    def _display_preferences_if_enabled(self) -> None:
        if not self.options.warn_me:
            return

        print("Loaded Preferences:")
        for key, value in self.options.to_dict().items():
            print(f"  {key}: {value}")

    def _download_single_url(self, url: str, save_results: bool) -> int:
        """Download a single URL. Returns 0 on success, 1 on failure."""
        try:
            results: List[DownloadResult] = self.ytd.download(url=url, options=self.options)

            if results:
                if save_results and self.media_info_service.is_playlist(url):
                    self.os.save_batch_results(results=results, download_dir=self.options.default_download_directory, playlist_name=self.media_info_service.get_playlist_title(url))

                success_count = sum(1 for result in results if result.success)
                fail_count = len(results) - success_count

                if len(results) > 1:
                    print(f"\n{'=' * 50}")
                    print(f"Download Summary: {success_count} succeeded, {fail_count} failed")

                    if fail_count > 0:
                        print("\nFailed downloads:")
                        for result in results:
                            if not result.success:
                                print(f"  {result}")

                    print(f"{'=' * 50}")

                return 0 if fail_count == 0 else 1

            return 0

        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            return 1

    def _parse_file_params(self, file_params: str) -> argparse.Namespace | None:
        if not file_params:
            return None

        try:
            return self.parser.parse_args(shlex.split(file_params))
        except SystemExit:
            logger.warning(f"Invalid params in batch file; ignoring params: {file_params}")
            return None

    def _run_info_mode(self, url: str) -> int:
        print("Fetching video/playlist info...")

        try:
            lines = self.media_info_service.get_info_lines(url)
            for line in lines:
                print(line)
            return 0

        except Exception as e:
            logger.error(f"Failed to fetch info: {e}")
            return 1

    def _run_batch_mode(self, args: argparse.Namespace) -> int:
        file_path = self.os.expand_path(args.file)

        if not file_path.exists():
            logger.error(f"Batch file not found: {file_path}")
            return 1

        try:
            urls, file_params = self.os.load_batch_urls(file_path)
        except Exception as e:
            logger.error(f"Failed to load batch file: {e}")
            return 1

        # Batch-file params are weaker than CLI params.
        # Apply file params first, then apply CLI args so CLI wins.
        file_args = self._parse_file_params(file_params)
        if file_args is not None:
            logger.info(f"Batch file parameters: {file_params}")
            self._apply_options(file_args)

        self._apply_options(args)
        self._save_config_if_requested(args)
        self._display_preferences_if_enabled()

        valid_urls, skipped_count = self.os.filter_valid_urls(urls)

        if valid_urls:
            logger.info(
                f"Batch file loaded: {len(urls)} total URLs, "
                f"{skipped_count} invalid/skipped, {len(valid_urls)} valid."
            )

        if not valid_urls:
            logger.warning("No valid URLs found in batch file.")
            return 1

        logger.info(f"Download directory: {self.options.default_download_directory}")

        print(f"------ Batch Processing {len(valid_urls)} URLs ------")

        success_count = 0
        fail_count = 0

        for idx, url in enumerate(valid_urls, 1):
            print(f"\n[{idx}/{len(valid_urls)}] Processing: {url}")

            if self._download_single_url(url, self.options.save_results) == 0:
                success_count += 1
            else:
                fail_count += 1

        print("\n------ Batch Complete ------")
        print(f"Summary: {success_count} succeeded, {fail_count} failed.")

        return 0 if fail_count == 0 else 1

    def _run_single_mode(self, args: argparse.Namespace) -> int:
        self._apply_options(args)
        self._save_config_if_requested(args)
        self._display_preferences_if_enabled()

        logger.info(f"Download directory: {self.options.default_download_directory}")

        if args.info:
            return self._run_info_mode(args.url)

        print("------ Starting Download ------")
        return self._download_single_url(args.url, self.options.save_results)

    def run(self, command: str) -> int:
        """Process a command string for downloading YouTube videos or playlists."""
        args = self._parse_args(command)

        # argparse --help already printed help.
        if args is None:
            return 0

        if not args.url and not args.file:
            logger.error("Either provide a URL or use -f/--file for batch processing.")
            return 1

        if args.url and args.file:
            logger.error("Cannot specify both URL and --file; choose one.")
            return 1

        if args.file:
            return self._run_batch_mode(args)

        return self._run_single_mode(args)
