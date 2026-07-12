
import argparse
import datetime
import subprocess
import sys
from pathlib import Path
from typing import List

from application.session_config_service import SessionConfigService
from cli.cli_base import CLIBase

from application.download_orchestrator import DownloadOrchestrator as YTD
from application.media_info_service import MediaInfoService

from domain.video_fetcher import VideoFetcher
from infrastructure.os_interactions import OSInteractions
from infrastructure.url_handler import URLHandler

from utility.logger import get_logger
from utility.utils import (
    DownloadOptions,
    QUALITY_ALIAS_MAP,
    COMMON_AUDIO_ABR,
    COMMON_VIDEO_RESOLUTIONS,
    DownloadResult,
)

import utility.preferences as preferences

from autotagging.runtime_tagging.results_report import TaggingResultsReport
from cli.interactive_prompt import split_prompt_command

logger = get_logger(__name__, "cli_command_debug.log")


class CommandCLI(CLIBase):
    def __init__(self):
        super().__init__()

        # Shared infrastructure/services for this CLI session.
        # Keeping these as attributes makes later GUI/CLI dependency injection easier.
        self.os = OSInteractions()
        self.url_handler = URLHandler()
        self.video_fetcher = VideoFetcher()
        self.config_service = SessionConfigService(os_handler=self.os)

        config_state = self.config_service.read_state(apply_runtime=True)
        self.preferences = config_state.preferences
        self.options = config_state.options
        self.loaded_preset_path: Path | None = config_state.loaded_preset_path
        self._last_parse_exit_code = 0
        self._tagging_worker_process: subprocess.Popen | None = None

        self.ytd = YTD(
            os_handler=self.os,
            url_handler=self.url_handler,
            vid_fetcher=self.video_fetcher,
        )

        self.media_info_service = MediaInfoService(
            url_handler=self.url_handler,
            video_fetcher=self.video_fetcher,
        )
        self.results_report = TaggingResultsReport()

        self.parser = self.build_parser()
        self.enable_argcomplete(self.parser)

    def _refresh_parser(self) -> None:
        self.parser = self.build_parser()
        self.enable_argcomplete(self.parser)

    def _clone_options(self, options: DownloadOptions | None = None) -> DownloadOptions:
        source_options = self.options if options is None else options
        return self.config_service.clone_options(source_options)

    def build_parser(self) -> argparse.ArgumentParser:
        """ #TODO still accurate?
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
                "  yt_ripper> <URL> -a true -q high\n"
                "  yt_ripper> <URL> -lp 0 -a true -q high  (overrides preset for session)\n"
                "  yt_ripper> <URL> -r 1080p -o ~/Downloads\n"
                "  yt_ripper> -f ~/urls.txt -a true -q low\n"
                "  yt_ripper> <URL> -vl debug -sr true (save download results)\n"
                "  yt_ripper> <URL> -at true (attempt auto-tagging with metadata)\n"
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
            "-ld", # author misstyped so often that I added this alias for convenience "ld = load" 
            "--load_preset",
            type=str,
            default=None,
            help="Load preset: custom '0'-'9' or immutable 'ah'/'vh'/'vl'/'test'/'ds'",
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
            type=str,
            default=None,
            help=(
                "Save current session options to config. "
                "Use true to save to the default config, or 0-9 to save to a custom preset. "
                "Batch-file-local params are never saved."
            ),
        )

        parser.add_argument(
            "-sp",
            "--show_preset",
            type=str,
            default=None,
            help=f"Show loaded preferences before running (true/false). Current default: {self.options.show_preset}",
        )

        parser.add_argument(
            "-at",
            "--autotag",
            type=str,
            default=None,
            help=f"Attempt to auto-tag downloaded files with metadata (true/false). Current default: {self.options.autotag}",
        )

        parser.add_argument(
            "--prepare-tagging",
            type=str,
            default=None,
            help=(
                "Prepare tagging package JSON files for later processing (true/false). "
                f"Current default: {self.options.prepare_tagging}"
            ),
        )

        parser.add_argument(
            "-sr",
            "--save-results",
            type=str,
            default=None,
            help="Save download results to a file (true/false). Default: None",
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
        try:
            import argcomplete

            argcomplete.autocomplete(parser)
        except ImportError:
            pass

    @staticmethod
    def _split_command(command: str) -> list[str]:
        return split_prompt_command(command)

    def _parse_args(self, command: str) -> argparse.Namespace | None:
        self._last_parse_exit_code = 0
        try:
            return self.parser.parse_args(self._split_command(command))
        except SystemExit as exc:
            self._last_parse_exit_code = exc.code if isinstance(exc.code, int) else 1
            if self._last_parse_exit_code == 0:
                return None

            logger.error("Invalid command or arguments.")
            return None

    def _parse_fps_preference(
        self,
        value: str,
        options: DownloadOptions | None = None,
    ) -> int:
        current_options = self.options if options is None else options
        return self.config_service.parse_fps_preference(value, current_options)

    def _normalize_load_preset(self, value: str | None) -> Path | None:
        return self.config_service.resolve_load_preset(value)

    def _normalize_save_config_path(self, value: str | None) -> Path | None:
        return self.config_service.resolve_save_config_path(
            value,
            loaded_preset_path=self.loaded_preset_path,
        )

    def _apply_options(
        self,
        args: argparse.Namespace,
        options: DownloadOptions | None = None,
    ) -> DownloadOptions:
        target_options = self.options if options is None else options
        return self.config_service.apply_args(
            args,
            target_options,
            apply_runtime=options is None,
        )

    def _normalize_options(self, options: DownloadOptions, apply_runtime: bool = False) -> None:
        self.config_service.normalize_options(options, apply_runtime=apply_runtime)

    def _normalize_boolean_options(self, options: DownloadOptions) -> None:
        self.config_service.normalize_boolean_options(options)

    def _normalize_download_directory(self, options: DownloadOptions) -> None:
        self.config_service.normalize_download_directory(options)

    def _normalize_quality_options(self, options: DownloadOptions) -> None:
        self.config_service.normalize_quality_options(options)

    def _normalize_audio_bitrate(self, options: DownloadOptions) -> None:
        self.config_service.normalize_audio_bitrate(options)

    def _normalize_resolution(self, options: DownloadOptions) -> None:
        self.config_service.normalize_resolution(options)

    def _normalize_visible_loglevel(self, options: DownloadOptions) -> None:
        self.config_service.normalize_visible_loglevel(options)

    def _apply_runtime_options(self, options: DownloadOptions) -> None:
        self.config_service.apply_runtime_options(options)

    def _save_config_if_requested(self, args: argparse.Namespace) -> None:
        if args.save_config is None:
            return

        try:
            save_path = self._normalize_save_config_path(args.save_config)
        except ValueError as exc:
            logger.error(str(exc))
            return

        if save_path is None:
            return

        self.preferences = self.options.to_dict()
        if self.os.write_preferences(self.preferences, prefs_path=save_path):
            print(f"✓ Config saved to {save_path}")
        else:
            logger.error(f"Failed to save config to {save_path}")
            print(f"Failed to save config to {save_path}")

    def _load_preset_if_requested(self, args: argparse.Namespace) -> bool:
        """Load preset if requested and merge into current options.
        Returns True if a preset was loaded successfully or no preset was requested, False if loading failed.
        """
        if not args.load_preset:
            return True

        try:
            config_state = self.config_service.load_preset(
                args.load_preset,
                apply_runtime=True,
            )
        except ValueError as exc:
            logger.error(str(exc))
            return False

        self.loaded_preset_path = config_state.loaded_preset_path
        self.preferences = config_state.preferences
        self.options = config_state.options
        self._refresh_parser()
        return True

    def _display_preferences_if_enabled(self, options: DownloadOptions) -> None:
        if not options.show_preset:
            return

        print("Loaded Preferences:")
        for key, value in options.to_dict().items():
            print(f"  {key}: {value}")

    def _download_single_url(self, url: str, options: DownloadOptions, start_time: datetime.datetime | None = None) -> int:
        try:
            is_playlist = self.media_info_service.is_playlist(url)
            report_path: Path | None = None
            playlist_name: str | None = None
            if options.save_results and (start_time is not None or is_playlist):
                if start_time is None and is_playlist:
                    playlist_name = self.media_info_service.get_playlist_title(url)
                report_path = self.results_report.build_report_path(
                    options.default_download_directory,
                    playlist_name=playlist_name,
                    timestamp_label=(start_time or datetime.datetime.now()).strftime("%Y-%m-%d_%H-%M-%S"),
                    batch_mode=start_time is not None,
                )

            results: List[DownloadResult] = self.ytd.download(
                    url=url,
                    options=options,
                    results_report_path=report_path,
            )
            if options.autotag and any(result.success for result in results):
                self._ensure_tagging_worker(options)
            if not results:
                logger.error(
                    "Download produced no structured results for %s. "
                    "This indicates a downloader failure path that should be investigated.",
                    url,
                )
                return 1

            success_count = sum(1 for result in results if result.success)
            fail_count = len(results) - success_count

            # Single standalone URLs intentionally do not create result files.
            # Direct playlist URLs and batch/file-driven runs do.
            if options.save_results and (start_time is not None or is_playlist):
                self.os.save_download_results(
                    results=results,
                    download_dir=options.default_download_directory,
                    playlist_name=playlist_name,
                    timestamp=start_time,
                    report_path=report_path,
                    batch_mode=start_time is not None,
                )

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

        except Exception as exc:
            logger.error(f"Download failed for {url}: {exc}")
            return 1

    def _ensure_tagging_worker(self, options: DownloadOptions) -> None:
        if not options.autotag:
            return

        if self._tagging_worker_process is not None and self._tagging_worker_process.poll() is None:
            return

        worker_script = preferences.PROJECT_ROOT / "source" / "run_tagging_worker.py"
        command = [
            sys.executable,
            str(worker_script),
            "--idle-timeout",
            "30",
            "--poll-interval",
            "1",
        ]

        self._tagging_worker_process = subprocess.Popen(
            command,
            cwd=str(preferences.PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.info("Spawned background tagging worker: pid=%s", self._tagging_worker_process.pid)

    def _parse_file_params(self, file_params: str) -> argparse.Namespace | None:
        if not file_params:
            return None

        try:
            return self.parser.parse_args(self._split_command(file_params))
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

        except Exception as exc:
            logger.error(f"Failed to fetch info: {exc}")
            return 1

    def _run_batch_mode(self, args: argparse.Namespace) -> int:
        if not self._load_preset_if_requested(args):
            return 1

        file_path = self.os.expand_path(args.file)

        if not file_path.exists():
            logger.error(f"Batch file not found: {file_path}")
            return 1

        try:
            urls, file_params = self.os.load_batch_urls(file_path)
        except Exception as exc:
            logger.error(f"Failed to load batch file: {exc}")
            return 1

        # Batch-file params are local to this one batch run. They are applied to
        # effective_options only and are never copied back into self.options.
        session_options_before_command = self._clone_options()
        effective_options = self._clone_options(session_options_before_command)

        file_args = self._parse_file_params(file_params)
        if file_args is not None:
            logger.info(f"Batch file parameters: {file_params}")
            self._apply_options(file_args, options=effective_options)
            #NOTE: should a file be able to load a preset for its batch runs? => no it s already complicated enough with the current options merging order, and presets are meant to be user-invoked for interactive session

        # CLI args belong to the interactive session and should persist in loop
        # mode. Apply them to self.options after file params so file params do not
        # leak into the session state.
        self.options = session_options_before_command
        self._apply_options(args)
        self._refresh_parser()

        # CLI args also override batch-file params for this run.
        self._apply_options(args, options=effective_options)
        self._save_config_if_requested(args)
        self._display_preferences_if_enabled(effective_options)

        valid_urls, skipped_count = self.os.filter_valid_urls(urls)

        if valid_urls:
            logger.info(
                f"Batch file loaded: {len(urls)} total URLs, "
                f"{skipped_count} invalid/skipped, {len(valid_urls)} valid."
            )

        if not valid_urls:
            logger.warning("No valid URLs found in batch file.")
            return 1

        logger.info(f"Download directory: {effective_options.default_download_directory}")

        print(f"------ Batch Processing {len(valid_urls)} URLs ------")

        success_count = 0
        fail_count = 0

        # Runtime-only effects from file params, such as visible log level, should
        # affect this batch only. Restore the session runtime settings afterward.
        self._apply_runtime_options(effective_options)
        start_time = datetime.datetime.now()
        try:
            for idx, url in enumerate(valid_urls, 1):
                print(f"\n[{idx}/{len(valid_urls)}] Processing: {url}")

                if self._download_single_url(url, effective_options, start_time=start_time) == 0:
                    success_count += 1
                else:
                    fail_count += 1
        finally:
            self._apply_runtime_options(self.options)

        print("\n------ Batch Complete ------")
        print(f"Summary: {success_count} succeeded, {fail_count} failed.")

        return 0 if fail_count == 0 else 1

    def _run_single_mode(self, args: argparse.Namespace) -> int:
        if not self._load_preset_if_requested(args):
            return 1

        self._apply_options(args)
        self._refresh_parser()
        self._save_config_if_requested(args)

        effective_options = self._clone_options()
        self._display_preferences_if_enabled(effective_options)

        logger.info(f"Download directory: {effective_options.default_download_directory}")

        if args.info:
            return self._run_info_mode(args.url)

        print("------ Starting Download ------")
        return self._download_single_url(args.url, effective_options)

    def run(self, command: str) -> int:
        args = self._parse_args(command)

        if args is None:
            return self._last_parse_exit_code

        if not args.url and not args.file:
            logger.error("Either provide a URL or use -f/--file for batch processing.")
            return 1

        if args.url and args.file:
            logger.error("Cannot specify both URL and --file; choose one.")
            return 1

        if args.file:
            return self._run_batch_mode(args)

        return self._run_single_mode(args)
