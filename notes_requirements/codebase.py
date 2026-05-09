#--------------------
#
#     download_orchestrator.py
#
#--------------------


import pytubefix as ptf
import re
from typing import List
from pathlib import Path 


from utility.logger import get_logger
from utility.utils import PlaylistFetchError, StreamDownloadError, ConversionError, CombineError, DownloadOptions, DownloadResult, QUALITY_ALIAS_MAP, sanitize_filename

from infrastructure.stream_converter import StreamConverter #TODO:change to MediaAssembler 
from infrastructure.url_handler import URLHandler # TODO: calls move to video_fetcher ?
from infrastructure.os_interactions import OSInteractions
from infrastructure.thumbnail_handler import ThumbnailHandler

from domain.stream_downloader import StreamDownloadService
from domain.stream_selector import StreamSelector
from domain.video_fetcher import VideoFetcher

#TODO: implement proper logging so user does not get unwanted outputs
#TODO: Handle exceptions properly (incl. at interfaces not above)
#TODO: make classes testable (mockable and unittestable if possible)
logger = get_logger(__name__, 'download_orchestrator_debug.log')


class DownloadOrchestrator:
    """docstring for DownloadOrchestrator."""
    def __init__(self, 
                 os_handler: OSInteractions = None, 
                 thumbnail_handler: ThumbnailHandler = None,
                 stream_converter: StreamConverter = None, 
                 url_handler: URLHandler = None,
                 vid_fetcher: VideoFetcher = None,
                 stream_selector: StreamSelector = None,
                 stream_download: StreamDownloadService = None):
        
        self.os_handler = os_handler or OSInteractions()
        self.thumbnail_handler = thumbnail_handler or ThumbnailHandler()
        self.stream_converter = stream_converter or StreamConverter()
        self.urlh = url_handler or URLHandler()

        self.vid_fetcher = vid_fetcher or VideoFetcher()
        self.stream_selector = stream_selector or StreamSelector()
        self.stream_download = stream_download or StreamDownloadService()

 # split into two methods and export to ??
    def info(self, url: str = None, video_obj: ptf.YouTube = None, output: callable = logger.info) -> None:
        """
        Print to console or log information about video or playlist.

        Args:
        url (str): The URL of the YouTube video or playlist.
        video_obj (ptf.YouTube, optional): A YouTube video object. Defaults to None.
        output (callable, optional): A callable that takes a string, e.g. `print` or `logger.info`.
            Defaults to `logger.info`.
        """
        
        if self.urlh.is_youtube_playlist(url):
            try:
                playlist_obj = self.vid_fetcher.get_playlist_obj(url)
            except Exception as e:
                logger.error(f"Failed to fetch playlist object: {e}")
                return
        
            output(f"Playlist Title: {playlist_obj.title}")
            output(f"Number of Videos: {len(playlist_obj.videos)}")
            output("Videos:")
            for i, video in enumerate(playlist_obj.videos):
                output(f"{i + 1}. {video.title} ({video.length} seconds)")
        else:
            try:
                if video_obj is None:
                    video_obj = self.vid_fetcher.get_video_obj(url)
            except Exception as e:
                logger.error(f"Failed to fetch video object: {e}")
                return

            output(f"Video title: {video_obj.title}")
            output(f"Video length: {video_obj.length} seconds")
            output(f"Video views: {video_obj.views}")
            output(f"Video author: {video_obj.author}")
            output(f"Video description: {video_obj.description[:200]}...")
            output(f"Thumbnail: {video_obj.thumbnail_url}")

            output("Available streams:")
            output("  Video:")
            for stream in video_obj.streams.filter(type='video').order_by('resolution').desc():
                output(f"- {stream.resolution}, {stream.mime_type}, {stream.fps}fps")
            output(f"Best video: {video_obj.streams.filter(type='video').order_by('resolution').desc().first()}")
            
            output("  Audio:")
            for stream in video_obj.streams.filter(type='audio').order_by('abr').desc():
                output(f"- {stream.mime_type}, {stream.abr}")
            output(f"Best audio: {video_obj.streams.filter(type='audio').order_by('abr').desc().first()}")
            
    # TODO improve error handling (return exceptions or ...?)
    def download_playlist(self, playlist_url: str, options: DownloadOptions) -> List[DownloadResult]:
        """
        Download all videos from a YouTube playlist as video or audio files.

        Args:
            playlist_url (str): The URL of the YouTube playlist.
            download_dir (str): The directory to save the downloaded files.
            audio_only (bool): If True, download audio only. If False, download video.
        Side Effects:
            - creates directory as playlist download target. 
        Logs:
            - Playlist download status.
        Returns:
            List[DownloadResult]: A list of results for each video download in the playlist.
        """
        download_dir: Path = Path(options.default_download_directory)
        results: List[DownloadResult] = []
        playlist_obj:ptf.Playlist = None
        playlist_dir: Path = None
        
        try:
            # EXCEPT: PlaylistFetchError
            playlist_obj = self.vid_fetcher.get_playlist_obj(playlist_url)

            # EXCEPT: IOError
            playlist_dir = self.os_handler.setup_playlist_dir(download_dir, playlist_obj.title, options.no_dir_date)
            
            # Override pytube's video URL regex to capture all videos in the playlist
            # TODO: put this anywhere in utils / preferences
            playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
            logger.debug(f"Found {len(playlist_obj.video_urls)} videos in the playlist. {playlist_obj.title}")
            
            for i, video in enumerate(playlist_obj.videos):
                logger.info(f'[{i + 1}/{len(playlist_obj.videos)}] Processing: {video.title}')
                #TODO: add urlh.clean_video_link if needed
                result = self.download_single(download_dir=playlist_dir, options=options, video_obj=video)
                results.append(result)

        # catch playlist level exceptions, not indivial video exceptions (handled in download_single)
        except (IOError, PlaylistFetchError) as e:
            logger.error(f"Failed to process playlist: {e}")
            return results
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            return results

        # Log summary
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count
        logger.info(f"Playlist download completed: {success_count} succeeded, {fail_count} failed")
        
        if fail_count > 0:
            logger.warning("Failed downloads:")
            for result in results:
                if not result.success:
                    logger.warning(f"  ✗ {result.video_title}: {'; '.join(result.errors)}")
    
        return results

    def download_single_video(self, video_obj: ptf.YouTube, download_dir: Path, options: DownloadOptions) -> DownloadResult:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video to download.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """        
        try:
            video_stream = self.stream_selector.select_stream_video(video_obj, options)
            video_path:Path = self.stream_download.download_stream(video_stream, download_dir)

            audio_stream = self.stream_selector.select_stream_audio(video_obj, options)
            audio_path:Path = self.stream_download.download_stream(audio_stream, download_dir)
            #TODO: where to put this logic if any => copy input to output (=> delte entirly?)
            output_path = video_path
            video_title = video_path.name

            #TODO: this should be save to delete ? => try except should catch all
            if not video_path or not audio_path:
                msg = "missing audio or video stream"
                logger.error(f"✗ {video_title}: {msg}") #TODO : ----------- DOES THIS EVEN WORK?
                return DownloadResult(success=False, errors=[msg], video_title=video_title, video_url=video_obj.watch_url) 
            
            if not options.donotconvert:
                self.stream_converter.combine_streams(audio_path, video_path, output_path) # TODO inp-name = outp-name

        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"✗ {video_title}: {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_obj.watch_url)#TODO: does this work? "video_url=video_obj.watch_url"

        except Exception as e:
            logger.error(f"✗ {video_title}: Unexpected error - {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_obj.watch_url)

    def download_single_audio(self, video_obj: ptf.YouTube, options: DownloadOptions, download_dir: Path) -> DownloadResult:
        """
        Download a single YouTube video's audio stream.

        Args:
            ...
        """

        try:
            audio_stream = self.stream_selector.select_stream_audio(video_obj, options)
            audio_path:Path = self.stream_download.download_stream(audio_stream, download_dir)
            thumbnail_path = None #FIXME self.thumbnail_handler.download_thumbnail(video_obj, download_dir, base_filename)
            
            #TODO: where to put this logic if any => copy input to output (=> delte entirly?)
            output_path = audio_path
            video_title = audio_path.name

            #TODO: this should be save to delete ? => try except should catch all
            if not audio_path:
                msg = "no audio stream available"
                logger.error(f"✗ {video_title}: {msg}")
                return DownloadResult(success=False, errors=[msg], video_title=video_title, video_url=video_obj.watch_url)#TODO: does this work? "video_url=video_obj.watch_url"
            
            if not options.donotconvert: 
                self.stream_converter.convert_audio( # TODO inp-name = outp-name
                    audio_path, output_path,
                    thumbnail_path=thumbnail_path,
                    audio_bitrate=options.actual_audio_bitrate,
                    audio_mp3=options.audio_mp3,
                )
        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"✗ {video_title}: {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_obj.watch_url)#TODO: does this work? "video_url=video_obj.watch_url"
        except Exception as e:
            logger.error(f"✗ {video_title}: Unexpected error - {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_obj.watch_url)
    
    #TODO video-fetching done in download() should not be required =>  see that download_playlist() can still interface properly
    # this will be a "facade" as functionality was split (=> reverse? was this sensible)
    def download_single(self, options: DownloadOptions, download_dir: Path, video_obj: ptf.YouTube = None, url: str = None) -> DownloadResult:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_obj (ptf.YouTube): The YouTube video object to download.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """        
        video_obj = video_obj or self.vid_fetcher.get_video_obj(url) #TODO: does this work ? => video-fetching should ideally be done outside of this method, but this is a fallback if not (e.g. for playlist download)
        
        base_filename: str = sanitize_filename(video_obj.title)
        video_title = video_obj.title
        video_url = video_obj.watch_url
        
        # Efficiency safeguard: skip download if target file already exists
        #TODO YT downloads are .opus not .mp4 ! => target is .mp4
        #TODO audio is primarily .m4a not .mp3
        if options.audio_only:
            ext = '.mp3' if options.audio_mp3 else '.m4a'
        else:
            ext = '.mp4'
        
        # refactor this look at: https://vscode.dev/github/RF-at-FH-Joanneum/Python-YTRipper/blob/Restructure_Orchestration_2887-7ee1-42fe-b3eb-f9c44204ae24
        target_file = Path(download_dir) / f"{base_filename}{ext}"
        if target_file.exists(): # does this check for extension ?
            logger.info(f'⏭ Skipping (already exists): {video_title} -> {target_file.name}')
            return DownloadResult(success=True, errors=[], video_title=video_title, video_url=video_url)
        
        logger.info(f'Downloading {"soundtrack" if options.audio_only else "video"}: {video_title}')
        
        try:
            if options.audio_only:
                self.download_single_audio(video_obj=video_obj, download_dir=download_dir, options=options)
            else:
                self.download_single_video(video_obj=video_obj, download_dir=download_dir, options=options)

            logger.info(f'✓ {video_title}')
            return DownloadResult(success=True, errors=[], video_title=video_title, video_url=video_url)
        
        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"✗ {video_title}: {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url)
        except Exception as e:
            logger.error(f"✗ {video_title}: Unexpected error - {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url)

    #TODO: Will be interface with CLI and GUI, so should be more generic 
    def download(self, url: str, options: DownloadOptions) -> List[DownloadResult]:
        """Process a YouTube video or playlist based on the provided URL and options.
        Args:
            url (str): The URL of the YouTube video or playlist to process.
            download_dir (Path): The directory where the processed files should be saved.
            options (DownloadOptions): The processing options specifying preferences for audio/video quality, format, etc.
        Returns:
            List[DownloadResult]: List of processing results for each video.
        Side Effects:
            - Processes the specified video or playlist to the given directory.
        Logs:
            - Download status and any errors encountered during the process.
        """
        results = []
        download_dir: Path = Path(options.default_download_directory)

        if self.urlh.is_youtube_url(url) and self.urlh.is_accessible(url):
            logger.debug(f"Valid YouTube URL: {url}")
            try:
                self.os_handler.create_directory(download_dir)

                # if start_radio mix, force single-video download with cleaned URL
                if self.urlh.has_start_radio(url):
                    cleaned = self.urlh.clean_video_link(url)
                    if not cleaned:
                        raise ValueError("Could not extract video id from start_radio URL")
                    logger.info(f"start_radio detected; treating as single video: {cleaned}")
                    url = cleaned

                if self.urlh.is_youtube_playlist(url):
                    logger.debug("Detected as a playlist URL.")
                    results = self.download_playlist(playlist_url=url, options=options)
                else:
                    logger.debug("Detected as a single video URL.")
                    url = self.urlh.clean_video_link(url) or url  # Clean the URL if possible, fallback to original
                    #video = self.vid_fetcher.get_video_obj(video_url=url)  # May raise VideoFetchError, handled in download_single
                    results.append(self.download_single(url=url, options=options, download_dir=download_dir))

            except Exception as e:
                logger.error(f"Download failed: {e}")
                return results
        else:
            logger.error("The provided URL is not a valid YouTube URL or inaccessible.")
            raise ValueError("The provided URL is not valid or unreachable.")
        
        return results

        


#--------------------
#
#     cli_base.py
#
#--------------------


import os
from utility.logger import get_logger
from application.download_orchestrator import DownloadOrchestrator as YTD
from infrastructure.os_interactions import OSInteractions

logger = get_logger(__name__, 'cli_base_debug.log')
class CLIBase:
    def __init__(self):
        self.os = OSInteractions()
        self.preferences = self.os.read_preferences()  # initial load
        # downloader gets os handler injected
        self.ytd = YTD(os_handler=self.os)
    
    


#--------------------
#
#     cli_command.py
#
#--------------------

import argparse
from pathlib import Path

from cli.cli_base import CLIBase
from utility.logger import get_logger
from utility.utils import DownloadOptions, QUALITY_ALIAS_MAP, COMMON_AUDIO_ABR, COMMON_VIDEO_RESOLUTIONS, parse_bool_string
from infrastructure.os_interactions import OSInteractions
import utility.preferences as preferences
from application.download_orchestrator import DownloadOrchestrator as YTD

logger = get_logger(__name__, 'cli_command_debug.log')

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
        parser.add_argument('-o', '--download_directory', type=str, default=self.options.default_download_directory,
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
        """
        Apply CLI arguments (passed during current run) to self.options (shared logic for single/batch).
        DELETEME: UPDATE: self.os.expand_path() called directly before any action
        """
        args_dict = {
            'audio_only': parse_bool_string(args.audio_only),
            'audio_mp3': parse_bool_string(args.audio_mp3),
            'preferred_video_quality': args.preferred_quality or None,
            'preferred_audio_quality': args.preferred_quality or None,
            'preferred_resolution': args.preferred_resolution or None,
            'preferred_abr': args.preferred_abr or None,
            'preferred_fps': self._parse_fps_preference(args.high_fps),
            'default_download_directory': self.os.expand_path(args.download_directory) or None,
            'warn_me': parse_bool_string(args.warn_me) if args.warn_me else self.options.warn_me,
            'no_dir_date': parse_bool_string(args.no_dir_date) if args.no_dir_date else self.options.no_dir_date,
        }
        
        self.options.update_from_dict(args_dict)
        
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

    def _download_single_url(self, url: str) -> int:
        """Download a single URL. Returns 0 on success, 1 on failure."""
        try:
            results = self.ytd.download(url=url, options=self.options)
            
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
            logger.info(f"Download directory: {self.options.default_download_directory}")
            
            print(f"------ Batch Processing {len(valid_urls)} URLs ------")
            success_count = 0
            fail_count = 0
            
            for idx, url in enumerate(valid_urls, 1):
                print(f"\n[{idx}/{len(valid_urls)}] Processing: {url}")
                if self._download_single_url(url) == 0:
                    success_count += 1
                else:
                    fail_count += 1
            
            print(f"\n------ Batch Complete ------")
            print(f"Summary: {success_count} succeeded, {fail_count} failed.")
            return 0 if fail_count == 0 else 1
        
        # SINGLE MODE: process single URL
        else:
            # Expand download directory for single mode
            logger.info(f"Download directory: {self.options.default_download_directory}")
            
            if args.info:
                print("Fetching video/playlist info...")
                try:
                    self.ytd.info(url=args.url, output=print)
                except Exception as e:
                    logger.error(f"Failed to fetch info: {e}") 
                    return 1
            else:
                print("------ Starting Download ------")
                return self._download_single_url(args.url)


#--------------------
#
#     media_assembler.py
#
#--------------------

"""MediaAssembler
Responsibility:
convert audio
merge audio/video
Wraps StreamConverter
"""

from utility.logger import get_logger
from infrastructure.stream_converter import StreamConverter

logger = get_logger(__name__, "media_assembler_debug.log")

class MediaAssembler(object):
    """docstring for MediaAssembler."""
    def __init__(self, stream_converter: StreamConverter = None):
        self.stream_converter = stream_converter if stream_converter is not None else StreamConverter()
        
    def convert_audio(self, ?? ) -> None:
        """Will delegate to StreamConverter.convert_audio, but will also handle any media-assembler specific logic (e.g. file management, logging, error handling, etc.)"""
        self.stream_converter.convert_audio_new()
        
    def combine_streams(self, ?? ) -> None:
        """Will delegate to StreamConverter.combine_streams, , but will also handle any media-assembler specific logic (e.g. file management, logging, error handling, etc.)"""
        self.stream_converter.combine_streams()


#--------------------
#
#     pytube_interface.py
#
#--------------------

from xml.etree.ElementInclude import include
import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
from enum import Enum
from datetime import datetime
from typing import List
from pathlib import Path 

from source.infrastructure.logger import get_logger
from source.components.stream_converter import StreamConverter
from source.components.url_handler import URLHandler
from source.infrastructure.os_interactions import OSInteractions
from source.components.thumbnail_handler import ThumbnailHandler
from source.infrastructure.utils import DownloadError, DownloadOptions, DownloadResult, QUALITY_ALIAS_MAP

logger = get_logger(__name__, 'pytube_interface_debug.log')

# DEBUG < INFO < WARNING < ERROR < CRITICAL


class PytubeInterface:
    """
    Handles high-level download logic for YouTube videos and playlists using pytubefix.
    """
    #FIXME: needs better solution -> maintain readable code and avoid too many arguments in methods
    class StreamType(Enum):
        AUDIO = 1
        VIDEO = 0
    stream_type_map = {
        StreamType.AUDIO:'Audio',
        StreamType.VIDEO:'Video'
    }

    def __init__(self, 
                 os_handler: OSInteractions = None, 
                 thumbnail_handler: ThumbnailHandler = None,
                 stream_converter: StreamConverter = None, 
                 url_handler: URLHandler = None):
        """
        Initialize the YouTubeDownloader with optional handlers for OS interactions,
        thumbnail downloading, and stream conversion.
        Args:
            os_handler (OSInteractions): Handler for OS interactions.
            thumbnail_handler (ThumbnailHandler, optional): Handler for thumbnail downloading. Defaults to None.
            stream_converter (StreamConverter, optional): Handler for stream conversion. Defaults to None.
            url_handler (URLHandler, optional): Handler for URL handling. Defaults to None.
        """
            
        self.thumbnail_handler = thumbnail_handler if thumbnail_handler is not None else ThumbnailHandler()
        self.stream_converter = stream_converter if stream_converter is not None else StreamConverter()
        self.urlh = url_handler if url_handler is not None else URLHandler()
        self.os_handler = os_handler if os_handler is not None else OSInteractions()
        
    
    # TODO: Test and implement
    


#--------------------
#
#     stream_downloader.py
#
#--------------------

"""StreamDownloadService
Responsibility: “Given a stream → download it”
Thin adapter over pytubefix
"""
from pathlib import Path
from pytubefix import Stream as ptfStream

from utility.logger import get_logger
from utility.utils import StreamDownloadError

logger = get_logger( __name__,"StreamDownloader_debug.log")

class StreamDownloadService(object):
    """docstring for StreamDownloadService."""

    #TODO: cleanup (mess of parameters) 
    #TODO:  return path or object => find out if ffmpeg performance improves 
    #       RAM intensive! => large files may require own method*S* !
    @staticmethod
    def download_stream(stream: ptfStream, download_dir: Path) -> Path | None:
        """
        Downloads a specified audio or video stream with given parameters.              
            Args:
                stream (ptf.Stream): The YouTube video stream object to download.
                download_dir (Path): The directory where the downloaded file will be saved.
            Returns:
                Path | None: The file path of the downloaded stream, or None if no suitable stream is found.
            Logs:
                - Debug logs for the download process, including the stream identifier and download path.
                - Exception logs if the download fails, including the error message.
            Raises:
                StreamDownloadError: If there is an error during the download process.
        """
        
        try:
            identifier = "audio" if stream.includes_audio_track and not stream.includes_video_track else "video" if stream.includes_video_track else "Error"
            
            downloaded_path:Path = Path(stream.download
                (
                output_path=str(download_dir),
                skip_existing=True,
                timeout=5,
                max_retries=3
                )
            )
            
            logger.debug(f"{identifier} stream downloaded to: {downloaded_path}")
            return downloaded_path
        except Exception as e:
            logger.exception(f"Error downloading {identifier} stream: {e}")
            raise StreamDownloadError(f"Error downloading {identifier} stream: {e}") from e
    


#--------------------
#
#     stream_selector.py
#
#--------------------

#TODO: reduce includes after renaming / moving methods is done

"""StreamSelector
Responsibility: “Given a video + preferences → choose streams”
No downloading
No ffmpeg
Testable without network
"""

import pytubefix as ptf

from utility.logger import get_logger
from utility.utils import StreamSelectionError, DownloadOptions, DownloadResult, QUALITY_ALIAS_MAP


#TODO: => read methods -> might need improvement (currently not priority) 

logger = get_logger(__name__, 'StreamSelector_debug.log')


class StreamSelector:
    """docstring for StreamSelector."""
    
    @staticmethod
    def select_stream_audio(video: ptf.YouTube, options: DownloadOptions) -> ptf.Stream:
        """Select an audio stream based on DownloadOptions preferences."""
        try:
            q = video.streams.filter(type='audio')
            stream = None

            # 1) preferred_abr exact match
            if options and options.preferred_abr:
                stream = q.filter(abr=options.preferred_abr).first()
                logger.debug(f"[select] audio preferred abr={options.preferred_abr} -> {stream}")

            # 2) preferred_audio_quality via aliases (optionally constrained by mime)
            if not stream and options and options.preferred_audio_quality:
                qual_key = QUALITY_ALIAS_MAP.get(options.preferred_audio_quality.strip().lower())
                aq = q.filter(mime_type=options.preferred_mime) if options.preferred_mime else q
                if qual_key == "high":
                    stream = aq.order_by('abr').desc().first()
                elif qual_key == "low":
                    stream = aq.order_by('abr').asc().first()
                elif qual_key == "medium":
                    candidates = list(aq.order_by('abr'))
                    if candidates:
                        idx = len(candidates) // 2  # upper-middle for even counts
                        stream = candidates[idx]
                logger.debug(f"[select] audio quality={options.preferred_audio_quality} (mime={options.preferred_mime or 'any'}) -> {stream}")

            # 3) best available (highest abr)
            if not stream:
                stream = q.order_by('abr').desc().first()
                logger.debug(f"[select] audio fallback best abr -> {stream}")

            if not stream:
                raise StreamSelectionError("No audio stream available")
        
            return stream
            
        except Exception as e:
            raise StreamSelectionError(f"Stream selection failed: {e}") from e
    
    @staticmethod     # Helper to filter by FPS preference (used in video selection)
    def _apply_fps_filter(candidates_list:list, preferred_fps:int):
        """Filter candidates by FPS preference: 0=any, 30=prefer 30fps, 60=prefer 60fps"""
        if not candidates_list or preferred_fps == 0:
            return candidates_list
        # Extract fps from stream strings like "60fps" -> 60
        result = []
        for stream_obj in candidates_list:
            try:
                stream_fps = int(str(stream_obj.fps).rstrip('fps')) if stream_obj.fps else 0
                if stream_fps == preferred_fps:
                    result.append(stream_obj)
            except (ValueError, AttributeError):
                pass
        return result if result else candidates_list  # fallback to all if none match

    @staticmethod
    def select_stream_video(video: ptf.YouTube, options: DownloadOptions) -> ptf.Stream:
        """Select a video stream based on DownloadOptions preferences."""
        try:
            q = video.streams.filter(type='video', progressive=False)
            stream = None

            # 1) preferred_resolution (DASH first, then progressive)
            if options and options.preferred_resolution:
                stream = q.filter(resolution=options.preferred_resolution).order_by('fps').desc().first() if options.preferred_fps == 60 else q.filter(resolution=options.preferred_resolution).order_by('fps').asc().first() if options.preferred_fps == 30 else q.filter(resolution=options.preferred_resolution).first()
                logger.debug(f"[select] video preferred resolution={options.preferred_resolution} fps={options.preferred_fps or 'any'} (DASH) -> {stream}")
                if not stream:
                    candidates = list(video.streams.filter(type='video', progressive=True, resolution=options.preferred_resolution).order_by('fps'))
                    candidates = StreamSelector._apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None
                    logger.debug(f"[select] video preferred resolution={options.preferred_resolution} (progressive) -> {stream}")

            # 2) preferred_mime (best resolution within mime, considering FPS)
            if not stream and options and options.preferred_mime:
                candidates = list(q.filter(mime_type=options.preferred_mime).order_by('resolution'))
                candidates = StreamSelector._apply_fps_filter(candidates, options.preferred_fps)
                stream = candidates[-1] if candidates else None  # highest resolution
                logger.debug(f"[select] video preferred mime={options.preferred_mime} fps={options.preferred_fps or 'any'} (DASH) -> {stream}")
                if not stream:
                    candidates = list(video.streams.filter(type='video', progressive=True, mime_type=options.preferred_mime).order_by('resolution'))
                    candidates = StreamSelector._apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None
                    logger.debug(f"[select] video preferred mime={options.preferred_mime} (progressive) -> {stream}")

            # 3) preferred_video_quality via aliases (resolution + FPS consideration)
            if not stream and options and options.preferred_video_quality:
                qual_key = QUALITY_ALIAS_MAP.get(options.preferred_video_quality.strip().lower())
                candidates = list(q.order_by('resolution'))
                candidates = StreamSelector._apply_fps_filter(candidates, options.preferred_fps)
                
                if qual_key == "high":
                    stream = candidates[-1] if candidates else None  # highest resolution
                elif qual_key == "low":
                    stream = candidates[0] if candidates else None  # lowest resolution
                elif qual_key == "medium":
                    if candidates:
                        idx = len(candidates) // 2  # middle resolution
                        stream = candidates[idx]
                logger.debug(f"[select] video quality={options.preferred_video_quality} fps={options.preferred_fps or 'any'} -> {stream}")
        
            # 4) best available (highest resolution, considering FPS)
            if not stream:
                candidates = list(q.order_by('resolution'))
                candidates = StreamSelector._apply_fps_filter(candidates, options.preferred_fps)
                stream = candidates[-1] if candidates else None  # highest resolution
                logger.debug(f"[select] video fallback best resolution (DASH) fps={options.preferred_fps or 'any'} -> {stream}")
                if not stream:
                    candidates = list(video.streams.filter(type='video').order_by('resolution'))
                    candidates = StreamSelector._apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None

            return stream
    
        except Exception as e:
            raise StreamSelectionError(f"Stream selection failed: {e}") from e


#--------------------
#
#     video_fetcher.py
#
#--------------------

"""VideoFetcher
Responsibility: “Given a URL → return a video/playlist object”
Wraps pytubefix exceptions
No filesystem
No looping
"""

import pytubefix as ptf
import pytubefix.exceptions as ptf_ex

from utility.logger import get_logger
from utility.utils import VideoFetchError, PlaylistFetchError

logger = get_logger(__name__, 'VideoFetcher_debug.log')

class VideoFetcher(object):
    """docstring for VideoFetcher."""

    #TODO: implement as YT-API seems to actually "miss" sometimes
    # reasons not to implement: first try-hit-ratio is ~95 % and
    #  YT-API blocking that results from too many requests this strategy might hurt perfomance (earlier blocking)
    #  =>   current strategy is: "user restarts same operation after 10min on inadequate hit-rate after blocking opccured"
    #       "exists-scan" only requests when an earlier miss occured (efficient) limiting total requests
    """@retry(exceptions=(ptf_ex.VideoUnavailable, ptf_ex.RegexMatchError, ptf_ex.LiveStreamError, Exception),
        retries=2, backoff=1.0, backoff_factor=2.0, jitter=0.2, logger=logger)
    def _get_video_obj_with_retry(self, video_url: str) -> ptf.YouTube:
        # delegate to existing logic (keeps original exception handling and logging)
        return YouTubeDownloader._get_video_obj.__wrapped__(self, video_url) if hasattr(YouTubeDownloader._get_video_obj, "__wrapped__") else YouTubeDownloader._get_video_obj(self, video_url)
    """

    @staticmethod
    def get_video_obj(video_url: str) -> ptf.YouTube | Exception:
        """
        Fetches a YouTube video object.
        Args:
            video_url (str): The URL of the YouTube video.
        Returns:
            ptf.YouTube: The YouTube video object.
        Raises:
            VideoFetchError: If there is an error fetching the video.
        """
        try:
            video_obj = ptf.YouTube(video_url)
            return video_obj

        except ptf_ex.LiveStreamError as e:
            logger.error("Live stream video (not supported): %s", video_url)
            logger.debug("LiveStreamError while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Live stream videos are not supported: {video_url}") from e
        except ptf_ex.RegexMatchError as e:
            logger.error("Invalid or malformed video URL: %s", video_url)
            logger.debug("RegexMatchError while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Invalid or malformed video URL: {video_url}") from e
        except ptf_ex.VideoPrivate as e:
            logger.error("Private video: %s", video_url)
            logger.debug("VideoPrivate while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Private video: {video_url}") from e
        except ptf_ex.VideoRegionBlocked as e:
            logger.error("Region-blocked video: %s", video_url)
            logger.debug("VideoRegionBlocked while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Video is not available in your region: {video_url}") from e
        except (ptf_ex.AgeCheckRequiredAccountError, ptf_ex.AgeCheckRequiredError) as e:
            logger.error("Age check required for video: %s", video_url)
            logger.debug("Age-check exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Age verification is required to view this video: {video_url}") from e
        except ptf_ex.VideoUnavailable as e:
            logger.error("Video unavailable: %s", video_url)
            logger.debug("VideoUnavailable exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Could not fetch the video at {video_url}. It appears to be unavailable.") from e
        except Exception as e:
            logger.error("Failed to fetch video %s", video_url)
            logger.debug("Unexpected exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(
            f"Could not fetch the video at {video_url}. Please check the URL and your network connection."
            ) from e

    #TODO improve error handling
    @staticmethod
    def get_playlist_obj(playlist_url: str) -> ptf.Playlist:
        """
        Fetches a YouTube playlist object.
        Args:
            playlist_url (str): The URL of the YouTube playlist.
        Returns:
            ptf.Playlist: The YouTube playlist object.
        Raises:
            PlaylistFetchError: If there is an error fetching the playlist.
        """
        try:
            playlist_obj = ptf.Playlist(playlist_url)
            return playlist_obj
        except ptf_ex.RegexMatchError as e:
            logger.error("Invalid or malformed playlist URL: %s", playlist_url)
            logger.debug("RegexMatchError while fetching playlist %s", playlist_url, exc_info=True)
            raise PlaylistFetchError(f"Regex match error for playlist: {playlist_url}") from e
        except Exception as e:
            logger.error("Failed to fetch playlist: %s", playlist_url)
            logger.debug("Unexpected exception while fetching playlist %s", playlist_url, exc_info=True)
            raise PlaylistFetchError(
                f"Could not fetch the playlist at {playlist_url}. Please check the URL and your network connection."
            ) from e


#--------------------
#
#     os_interactions.py
#
#--------------------

import os
from pathlib import Path
import shutil
import csv
from typing import Dict, List, Tuple
from datetime import datetime

from utility.logger import get_logger
import utility.preferences as preferences
from infrastructure.url_handler import URLHandler
from utility.utils import sanitize_filename

logger = get_logger(__name__, 'os_interactions_debug.log')


class OSInteractions:
    """Filesystem and file I/O operations (preferences, batch files, paths)."""

    def __init__(self):
        self.prefs_path = preferences.PATH_TO_PREFERENCES
        self.logs_path = preferences.PATH_TO_LOGS

    def expand_path(self, path_str: str) -> Path:
        """Expand ~ and environment variables."""
        return Path(os.path.expandvars(os.path.expanduser(path_str))).resolve()

    def read_preferences(self) -> Dict:
        """Delegate to preferences module."""
        return preferences.read_preferences()

    def write_preferences(self, prefs: Dict) -> None:
        """Delegate to preferences module."""
        preferences.write_preferences(prefs)

    def clear_directory(self, dir_path: Path) -> None:
        """...existing code..."""
        pass

    def clear_logs(self) -> None:
        """...existing code..."""
        pass

    # BATCH FILE LOADING
    @staticmethod
    def load_batch_urls_txt(file_path: Path) -> Tuple[List[str], str]:
        """
        Load URLs from .txt file.
        First line may contain params (format: "param: -a -q low -r 480p")
        Returns: (list of URLs, param_string or empty string)
        """
        urls = []
        params = ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            if not lines:
                return [], ""
            
            # Check if first line contains params
            first_line = lines[0].lower()
            if first_line.startswith("param:") or first_line.startswith("params:"):
                params = lines[0].split(":", 1)[1].strip()
                urls = lines[1:]
            else:
                urls = lines
            
            return urls, params
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {e}")

    @staticmethod
    def load_batch_urls_csv(file_path: Path, url_column: int = 0) -> Tuple[List[str], str]:
        """
        Load URLs from .csv file.
        First line may contain params (same format as .txt).
        url_column: which column contains the URL (default: 0).
        """
        urls = []
        params = ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            if not rows:
                return [], ""
            
            # Check if first line contains params
            first_row = rows[0][0].lower() if rows[0] else ""
            if first_row.startswith("param:") or first_row.startswith("params:"):
                params = rows[0][0].split(":", 1)[1].strip()
                rows = rows[1:]
            
            urls = [row[url_column].strip() for row in rows if len(row) > url_column]
            return urls, params
        except Exception as e:
            raise IOError(f"Error reading CSV file {file_path}: {e}")

    @staticmethod
    def load_batch_urls(file_path: Path, url_column: int = 0) -> Tuple[List[str], str]:
        """
        Auto-detect file format and load batch URLs.
        Returns: (list of URLs, param_string or empty string)
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        if suffix == ".txt":
            return OSInteractions.load_batch_urls_txt(file_path)
        elif suffix == ".csv":
            return OSInteractions.load_batch_urls_csv(file_path, url_column)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    @staticmethod
    def filter_valid_urls(urls: List[str]) -> Tuple[List[str], int]:
        """
        Filter out invalid/empty URLs from a list.
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            Tuple of (valid_urls, skipped_count)
        """
        valid_urls = []
        skipped_count = 0
        
        for idx, url in enumerate(urls, 1):
            if url and url.strip() and URLHandler.is_youtube_url(url):
                valid_urls.append(url)
            else:
                logger.warning(f"Skipping invalid/empty URL at line {idx}: '{url}'")
                skipped_count += 1
        
        return valid_urls, skipped_count

    @staticmethod
    def setup_playlist_dir(download_dir: Path, playlist_title: str, no_dir_date: bool) -> Path:
        """
        Set up the directory for the playlist download. Creates any missing directories.
        Returns the playlist directory path.
        """
        download_dir = Path(download_dir)
        date_prefix = datetime.today().strftime('%Y_%m_') if not no_dir_date else ""
        playlist_dir = download_dir / f"{date_prefix}{sanitize_filename(playlist_title)}"

        try:
            created_count = OSInteractions.create_directory(playlist_dir)
            if created_count:
                logger.info(f"Created playlist download directory: {playlist_dir} (created {created_count} levels)")
            else:
                logger.debug(f"Playlist directory already exists: {playlist_dir}")
            return playlist_dir
        except Exception as e:
            logger.error(f"Failed to create playlist directory {playlist_dir}: {e}")
            logger.debug("Unexpected error occurred while creating playlist directory %s", playlist_dir, exc_info=True)
            raise IOError(f"Failed to create playlist directory {playlist_dir}") from e

    #TODO: cleanup or delete a use 
        """
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            logger.info(f"Created download directory: {download_dir}")
        """
    @staticmethod
    def create_directory(dir_path: Path) -> int:
        """
        Create a directory and all missing parent directories.
        Returns the number of directory levels that were created (0 if none).
        """
        dir_path = Path(dir_path)
        # Find how many ancestor directories do not exist (count from the target up to the nearest existing ancestor)
        missing_count = 0
        p = dir_path
        # Use resolve(strict=False) to normalize path without requiring existence
        try:
            p = p.resolve(strict=False)
        except Exception:
            p = dir_path

        temp = p
        while not temp.exists():
            missing_count += 1
            if temp.parent == temp:
                # reached filesystem root
                break
            temp = temp.parent

        if missing_count == 0:
            logger.debug(f"Directory already exists, nothing to create: {dir_path}")
            return 0

        try:
            # Create all missing directories in one call
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created path: {dir_path} (created {missing_count} levels)")
            return missing_count
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            logger.debug("Unexpected error occurred while creating directory %s", dir_path, exc_info=True)
            raise IOError(f"Failed to create directory {dir_path}") from e

    # TODO: add method to append to batch results file instead of overwriting (for long-running batch processes)
    # Currently unused !
    @staticmethod
    def save_batch_results(results: List[Dict], output_path: Path) -> None:
        """
        Save batch download results to a CSV file.

        Args:
            results: List of dictionaries containing download results (e.g. video_title, video_url, success, errors).
            output_path: Path to the output CSV file.
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['video_title', 'video_url', 'success', 'errors']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for result in results:
                    writer.writerow(result)
            logger.info(f"Batch results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save batch results to {output_path}: {e}")
            logger.debug("Unexpected error occurred while saving batch results to %s", output_path, exc_info=True)
            raise IOError(f"Failed to save batch results to {output_path}") from e

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['video_title', 'video_url', 'success', 'errors']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)                    
                writer.writeheader()
                for result in results:
                    writer.writerow(result)
            logger.info(f"Batch results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save batch results to {output_path}: {e}")
            logger.debug("Unexpected error occurred while saving batch results to %s", output_path, exc_info=True)
            raise IOError(f"Failed to save batch results to {output_path}") from e

        # Optionally, you could return a success status or the output path
        return


#--------------------
#
#     stream_converter.py
#
#--------------------

import os
from pathlib import Path 
from attr import dataclass
import ffmpeg as fpg
from utility.logger import get_logger

logger = get_logger(__name__, 'StreamConverter_debug.log')

#TODO: neccessary ? & decide what to put inside 
@dataclass
class VideoConversionParameters:
    actual_video_codec: str = None
    actual_audio_codec: str = None
    actual_bitrate: str = None
    target_video_codec: str = None
    target_audio_codec: str = None
    target_bitrate: str = None
    
# TODO!!!! This is a "facade" for the actual conversion logic, which is now in MediaAssembler. This class should be focused on the ffmpeg logic, 
# and should not have any media-assembler specific logic (e.g. file management, logging, error handling, etc.) 
# — that should be in MediaAssembler. The methods here should be as "pure" as possible, just taking inputs and returning outputs without side effects.
# The MediaAssembler will handle all the orchestration around these methods, including any file management, logging, error handling, etc. 
# This separation of concerns will make both classes more maintainable and testable. The StreamConverter should be focused solely on the ffmpeg conversion and 
# merging logic, while the MediaAssembler should handle the higher-level orchestration and any media-assembler specific logic. This way, 
# the StreamConverter can be easily reused in other contexts if needed, without being tightly coupled to the MediaAssembler's responsibilities.
# The StreamConverter methods should ideally be static or class methods, as they don't need to maintain any state. 
# They should take all necessary parameters as arguments and return results without modifying any external state. 
# The MediaAssembler will be responsible for managing any state, file paths, logging, etc., and will call the StreamConverter's methods to perform the actual conversion and 
# merging tasks. This design will lead to a cleaner separation of concerns and make both classes easier to test and maintain.
# The StreamConverter should not have any knowledge of the MediaAssembler's responsibilities or logic. 
# It should be a standalone utility class that focuses solely on the ffmpeg operations. 
# The MediaAssembler will be the one that orchestrates the overall media processing workflow, including calling the StreamConverter's methods when needed, 
# and handling any media-assembler specific logic such as file management, logging, error handling, etc. 
# This way, the StreamConverter can be easily reused in other contexts if needed, without being tightly coupled to the MediaAssembler's responsibilities.
# The StreamConverter should be designed to be as "pure" as possible, with methods that take inputs and return outputs without side effects. 
# This will make it easier to test the StreamConverter's functionality in isolation, without needing to worry about any media-assembler specific logic or state management. 
# The MediaAssembler will handle all of that, and will call the StreamConverter's methods to perform the actual conversion and merging tasks when needed. 
# This separation of concerns will lead to a cleaner and more maintainable codebase overall.

# TODO - decide on datatypes for method parameters and return values (e.g. should we use Path objects, strings, custom data classes, etc. ?)
# The method signatures should be designed to be as clear and intuitive as possible, while also being flexible enough to accommodate any future changes or additions to the conversion and merging logic. The StreamConverter should be focused solely on the ffmpeg operations, and should not have any media-assembler specific logic or state management. The MediaAssembler will handle all of that, and will call the StreamConverter's methods to perform the actual conversion and merging tasks when needed. This way, the StreamConverter can be easily reused in other contexts if needed, without being tightly coupled to the MediaAssembler's responsibilities.

# TODO - actual_audio_bitrate is not being set -> read commit history (did work at some point) => decide if this is neccessary and if so, how to set it (e.g. pass as parameter, set as attribute, etc.)

class StreamConverter:
    """Handles conversion and merging of audio/video streams."""

    #TODO: implement (variable datatypes open until implementation dictates them)
    @staticmethod
    def combine_streams_new(audio, video, conversion_params: VideoConversionParameters): # or combine_parameters object 
        # implement temp logic 
        # implement passing 
        pass
    
    #TODO: implement (variable datatypes open until implementation dictates them)
    @staticmethod
    def convert_audio_new(audio, target_codec, thumbnail, bitrate):
        
        # this can be deleted => logic is moved to MediaAssembler
        """"# Codec & extension from the flag
        if audio_mp3:
            used_a_codec = "libmp3lame"
            target_ext = ".mp3"
        else:
            used_a_codec = "aac"
            target_ext = ".m4a"""""

        # uneccessary as it will be created locally or with os_interaction
        """# Ensure output_path carries the correct extension
        if output_path.suffix.lower() != target_ext:
            logger.warning(
                f"Output extension mismatch ({output_path.suffix}), adjusting to {target_ext}."
            )
            output_path = output_path.with_suffix(target_ext)"""

        logger.debug(f"Converting audio to ({used_a_codec}) with ffmpeg...")

        # could also be moved to MediaAssembler
        """# pytubefix returns e.g. "160kbps" but ffmpeg expects "160k"
        if audio_bitrate:
            ffmpeg_bitrate = audio_bitrate.replace("kbps", "k").replace("mbps", "M")
            bitrate_kwargs = {"audio_bitrate": ffmpeg_bitrate}
            logger.debug(f"Using source-matched audio bitrate: {ffmpeg_bitrate} (raw: {audio_bitrate})")
        else:
            bitrate_kwargs = {"qscale:a": 3}
            logger.debug("No source bitrate provided, using VBR qscale:a=3")"""



    #TODO: retire 
    @staticmethod
    def combine_streams(audio_path: Path, video_path: Path, output_path: Path) -> None:
        """
        Combines separate audio and video files into a single output file using ffmpeg.

        This method takes the paths to an audio file and a video file, merges them into one media file at the specified output path,
        and removes the original input files upon successful completion.
        Args:
            audio_path (str): Path to the audio file to be merged.
            video_path (str): Path to the video file to be merged.
            output_path (str): Path where the merged output file will be saved.
        Raises:
            Exception: Logs any exception raised during the ffmpeg merging process.
        """
        logger.debug("Combining video and audio with ffmpeg...")
        
        # Use a temporary output file to avoid overwriting input files
        temp_output_path = Path(output_path).parent / f".{Path(output_path).stem}_tmp.mp4"
        
        try:
            (
                fpg
                .output(
                    fpg.input(str(video_path)), 
                    fpg.input(str(audio_path)), 
                    str(temp_output_path), 
                    vcodec='copy', 
                    acodec='aac', 
                    strict='experimental'
                    )
                .run(
                    capture_stdout=True, 
                    capture_stderr=True,
                    overwrite_output=True, 
                    quiet=True
                    )
            )
            
            # Remove input files
            os.remove(video_path)
            os.remove(audio_path)
            
            # Move temp file to final location
            os.rename(temp_output_path, output_path)
            logger.info(f"Merged file saved to: {output_path}")
            
        except Exception as e:
            logger.exception(f"Error during ffmpeg merging: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original files.")
            # Clean up temp file if it exists
            if temp_output_path.exists():
                try:
                    os.remove(temp_output_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to clean up temp file {temp_output_path}: {cleanup_err}")
            raise e  # Re-raise the exception for upstream handling

    #TODO: retire 
    @staticmethod
    def convert_audio(
        audio_path: Path, output_path: Path, thumbnail_path: Path = None, audio_bitrate: str = "", audio_mp3: bool = False
        ) -> None:
        """Converts audio (always re-encodes — source is Opus, not AAC).

        Uses a safe temp-file pattern: writes to a .tmp file first, then
        replaces the target only on success.

        Args:
            audio_path (Path): The path to the source audio file.
            output_path (Path): The desired output path (extension may be corrected).
            thumbnail_path (Path | None, optional): Thumbnail image to embed as cover art.
            audio_bitrate (str, optional): Target bitrate e.g. "128kbps". Falls back
                to VBR qscale if empty.
            audio_mp3 (bool): If True encode to MP3 (libmp3lame), otherwise to M4A (AAC).
        """

        # Codec & extension from the flag
        if audio_mp3:
            used_a_codec = "libmp3lame"
            target_ext = ".mp3"
        else:
            used_a_codec = "aac"
            target_ext = ".m4a"

        # Ensure output_path carries the correct extension
        if output_path.suffix.lower() != target_ext:
            logger.warning(
                f"Output extension mismatch ({output_path.suffix}), adjusting to {target_ext}."
            )
            output_path = output_path.with_suffix(target_ext)

        logger.debug(f"Converting audio to {target_ext} ({used_a_codec}) with ffmpeg...")

        # Bitrate kwargs
        # pytubefix returns e.g. "160kbps" but ffmpeg expects "160k"
        if audio_bitrate:
            ffmpeg_bitrate = audio_bitrate.replace("kbps", "k").replace("mbps", "M")
            bitrate_kwargs = {"audio_bitrate": ffmpeg_bitrate}
            logger.debug(f"Using source-matched audio bitrate: {ffmpeg_bitrate} (raw: {audio_bitrate})")
        else:
            bitrate_kwargs = {"qscale:a": 3}
            logger.debug("No source bitrate provided, using VBR qscale:a=3")

        # Temporary output file (safe conversion pattern)
        temp_output = output_path.with_name(output_path.stem + ".tmp" + output_path.suffix)

        audio_input = fpg.input(str(audio_path))
        image_input = fpg.input(str(thumbnail_path)) if thumbnail_path else None

        try:
            if thumbnail_path and thumbnail_path.exists():
                (
                    fpg
                    .output(
                        audio_input,
                        image_input,
                        str(temp_output),
                        acodec=used_a_codec,
                        **bitrate_kwargs,
                        extra_args=[
                            "-map", "0:a",
                            "-map", "1:v",
                            "-metadata:s:v", "title=Album cover",
                            "-metadata:s:v", "comment=Cover (front)",
                        ],
                    )
                    .run(
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True,
                        quiet=True,
                    )
                )
                thumbnail_path.unlink()
            else:
                (
                    fpg
                    .output(
                        audio_input,
                        str(temp_output),
                        acodec=used_a_codec,
                        **bitrate_kwargs,
                    )
                    .run(
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True,
                        quiet=True,
                    )
                )

            # ✅ Conversion succeeded — replace safely
            audio_path.unlink()  # remove original (opus)
            os.replace(temp_output, output_path)

            logger.info(f"Audio file saved to: {output_path}")

        except Exception as e:
            stderr = getattr(e, "stderr", None)
            logger.exception(
                f"Error during ffmpeg audio conversion: {stderr.decode() if stderr else e}"
            )

            # Clean up temp file if conversion failed
            if temp_output.exists():
                temp_output.unlink()

            logger.info("Keeping original audio file.")
            raise e


#--------------------
#
#     thumbnail_handler.py
#
#--------------------

import os
import requests
import pytube as ptf
from utility.logger import get_logger
from utility.utils import retry_call

logger = get_logger(__name__, 'thumbnail_handler_debug.log')

class ThumbnailHandler:
    """Handles downloading and saving YouTube video thumbnails."""
    
    @staticmethod
    def download_thumbnail(video: ptf.YouTube, download_dir: str, base_filename: str) -> str:
        """
        Downloads the thumbnail image of a YouTube video.

        Args:
            video (ptf.YouTube): The YouTube video object from which to download the thumbnail.
            download_dir (str): The directory where the thumbnail will be saved.
            base_filename (str): The base filename to use for the thumbnail file.
        Returns:
            str: The file path of the downloaded thumbnail image.
        Logs:
            - Thumbnail download status.
        """
        thumbnail_url = video.thumbnail_url
        logger.debug(f"Downloading thumbnail from: {thumbnail_url}")
        try:
            # retry the HTTP GET in case of transient network errors
            response = retry_call(lambda: requests.get(thumbnail_url, timeout=10),
                                  exceptions=(requests.RequestException,),
                                  retries=3, backoff=1.0, backoff_factor=2.0, jitter=0.25, logger=logger)
        except Exception as e:
            logger.exception(f"Failed to download thumbnail after retries: {e}")
            return ""
        
        if response.status_code == 200:
            ext = thumbnail_url.split('.')[-1].split('?')[0]
            thumbnail_path = os.path.join(download_dir, f"{base_filename}_thumbnail.{ext}")
            with open(thumbnail_path, 'wb') as f:
                f.write(response.content)
            logger.debug(f"Thumbnail downloaded to: {thumbnail_path}")
            return thumbnail_path
        else:
            logger.warning("Failed to download thumbnail.")
            return ""


#--------------------
#
#     url_handler.py
#
#--------------------

import urllib.parse as ulp
import requests
from utility.logger import get_logger

#TODO Improve logging
#TODO Add error handling for invalid URLs, etc.
#TODO Reinforce URL validation in other parts of the code using this class

logger = get_logger(__name__, 'url_handler_debug.log')


class URLHandler:
    """ 
    A class to handle URL validation and extraction for YouTube links.
    """
    
    YOUTUBE_DOMAINS = [
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "www.youtu.be"
    ]
    
    @staticmethod
    def _extract_video_id(url: str) -> str | None:
        u = ulp.urlparse(url)

        # Case 1 — standard watch?v=
        if u.path == "/watch":
            qs = ulp.parse_qs(u.query)
            return qs.get("v", [None])[0]

        # Case 2 — youtu.be/VIDEOID
        if u.netloc in ("youtu.be", "www.youtu.be"):
            return u.path.lstrip("/") or None

        # Case 3 — /shorts/VIDEOID
        if u.path.startswith("/shorts/"):
            return u.path.split("/")[2]

        # Case 4 — /embed/VIDEOID
        if u.path.startswith("/embed/"):
            return u.path.split("/")[2]

        return None

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """
        Check if the given URL is a valid YouTube URL.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL is a YouTube URL, False otherwise.
        """
        try:
            parsed_url = ulp.urlparse(url)
            domain = parsed_url.netloc.lower()
            return any(youtube_domain in domain for youtube_domain in URLHandler.YOUTUBE_DOMAINS)
        except Exception as e:
            logger.exception(f"Error parsing URL: {e}")
            return False
        
    @staticmethod
    def is_accessible(url: str) -> bool:
        """
        Check if the given URL is accessible.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL is accessible, False otherwise.
        """
        try:
            response = requests.head(url, allow_redirects=True)
            return response.status_code == 200
        except Exception as e:
            logger.exception(f"Error checking URL accessibility: {e}")
            #raise e
            return False
    
    @staticmethod
    def has_start_radio(url: str) -> bool:
        """Return True if the URL contains start_radio=1 (or truthy)."""
        try:
            parsed = ulp.urlparse(url)
            qs = ulp.parse_qs(parsed.query)
            start_radio = qs.get("start_radio", [None])[0]
            return start_radio is not None and str(start_radio).strip().lower() in ("1", "true", "yes")
        except Exception as e:
            logger.exception("Error parsing start_radio: %s", e)
            return False

    @staticmethod
    def is_youtube_playlist(url: str) -> bool:
        """
        Check if the given URL is a YouTube playlist URL.
        If start_radio=1 is present, treat as NOT a playlist.
        """
        try:
            parsed = ulp.urlparse(url)
            qs = ulp.parse_qs(parsed.query)
            has_list = bool(qs.get("list"))
            start_radio = qs.get("start_radio", [None])[0]
            if start_radio is not None and str(start_radio).strip().lower() in ("1", "true", "yes"):
                return False
            return has_list
        except Exception as e:
            logger.exception(f"Error parsing URL for playlist: {e}")
            return False

    @staticmethod
    def clean_video_link(url: str) -> str | None:
        """
        Return a clean YouTube video URL (https://www.youtube.com/watch?v=VIDEOID).
        If 'start_radio' is present it will be logged and removed.
        """
        #TODO: check if this can handle "-" at the end of video ids (some tests show that it runs into errors)
        try:
            parsed = ulp.urlparse(url)
            qs = ulp.parse_qs(parsed.query)
            # prefer explicit v parameter, fallback to extractor (handles youtu.be, /shorts/, /embed/)
            video_id = qs.get("v", [None])[0] or URLHandler._extract_video_id(url)
            if not video_id:
                logger.debug("clean_video_link: no video id found in URL: %s", url)
                return None
            # detect start_radio case-insensitively
            if any(k.lower() == "start_radio" for k in qs.keys()):
                logger.warning("clean_video_link: 'start_radio' parameter present and will be removed: %s", url)
            return f"https://www.youtube.com/watch?v={video_id}"
        except Exception as e:
            logger.exception("Error cleaning video link: %s", e)
            return None


#--------------------
#
#     logger.py
#
#--------------------

from asyncio.log import logger
import logging
import sys
import os
from typing import Optional, Dict

# Delegated constants / preference loading
import utility.preferences as preferences

def _load_preferences() -> Dict:
    """
    Delegate preference loading to source.preferences (single source of truth).
    """
    try:
        return preferences.read_preferences()
    except Exception:
        return {}


class _NoTracebackFormatter(logging.Formatter):
    """
    Formatter for console output that suppresses exception tracebacks.
    """
    def formatException(self, ei):
        # suppress traceback in console output
        return ""


def get_logger(name: str, logfile: Optional[str] = None, prefs: Optional[Dict] = None) -> logging.Logger:
    """
    Create/return a module logger configured with:
      - console handler level taken from preferences (or INFO by default)
      - file handler at DEBUG (if logfile provided) placed under preferences.LOGS_DIR
      - console formatter that suppresses tracebacks
      - file formatter that includes timestamps and full tracebacks
    """
    prefs = prefs or _load_preferences()
    level_name = (prefs.get("loglevel") or "INFO").upper()
    try:
        console_level = getattr(logging, level_name)
    except Exception:
        console_level = logging.INFO

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # let handlers filter
    for h in list(logger.handlers):
        logger.removeHandler(h)

    # Console handler (no tracebacks)
    console_fmt = "%(levelname)s - %(message)s"
    console_formatter = _NoTracebackFormatter(console_fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(console_level)
    ch.setFormatter(console_formatter)
    logger.addHandler(ch)

    # File handler (always DEBUG) with timestamp and module.func context
    if logfile:
        try:
            logs_dir = preferences.LOGS_DIR
            os.makedirs(logs_dir, exist_ok=True)
            if os.path.isabs(logfile):
                logfile_path = logfile
            else:
                logfile_path = os.path.join(logs_dir, logfile)
            file_fmt = "%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s"
            fh = logging.FileHandler(logfile_path, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter(file_fmt))
            logger.addHandler(fh)
        except Exception:
            logger.warning("Failed to create file handler for logger %s (file: %s)", name, logfile)
    logger.debug("Logger initialized --------------------------------")
    logger.propagate = False
    return logger


#--------------------
#
#     preferences.py
#
#--------------------

import os
import json
from pathlib import Path
from typing import Dict
from dataclasses import dataclass, asdict
import getpass

# ---------- CONSTANTS FOR SETUP & RESTORE -------------------
CURRENT_DIR: Path = Path(__file__).resolve().parent   # → Python-YTRipper/source/core
SOURCE_DIR: Path = CURRENT_DIR.parent                 # → Python-YTRipper/source
PROJECT_ROOT: Path = SOURCE_DIR.parent                # → Python-YTRipper
CONFIG_DIR: Path = PROJECT_ROOT / "config"
LOGS_DIR: Path = PROJECT_ROOT / "logs"

PATH_TO_LOGS: Path = LOGS_DIR

DEFAULT_PREFS: Dict = {
    "default_download_directory": "~/Downloads",
    "audio_only": False,
    "audio_mp3": False,
    "warn_me": False,
    "preferred_audio_quality": "",
    "preferred_video_quality": "",
    "preferred_resolution": "",
    "preferred_abr": "",
    "preferred_mime": "",
    "preferred_format": "",
    "preferred_fps": 0,
    "loglevel": "WARNING",
    "donotconvert": False,
    "no_dir_date": False
}

def current_username() -> str:
    """Return the current executing user's username; fallback to HOME parsing."""
    try:
        return getpass.getuser()
    except Exception:
        home = os.environ.get("HOME", "")
        return Path(home).name if home else ""

PATH_TO_PREFERENCES: Path = CONFIG_DIR / f"user_settings_{current_username()}.json"

def read_preferences() -> Dict:
    """
    Read preferences from PATH_TO_PREFERENCES. If missing, create it with DEFAULT_PREFS.
    Returns a dict (never None).
    """
    if not os.path.exists(PATH_TO_PREFERENCES):
        try:
            os.makedirs(os.path.dirname(PATH_TO_PREFERENCES), exist_ok=True)
            with open(PATH_TO_PREFERENCES, 'w', encoding="utf-8") as f:
                json.dump(DEFAULT_PREFS, f, indent=4)
            return dict(DEFAULT_PREFS)
        except Exception:
            return dict(DEFAULT_PREFS)
    else:
        try:
            with open(PATH_TO_PREFERENCES, 'r', encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else dict(DEFAULT_PREFS)
        except Exception:
            return dict(DEFAULT_PREFS)

def write_preferences(prefs: Dict) -> None:
    """Write provided prefs dict to PATH_TO_PREFERENCES (best-effort)."""
    try:
        os.makedirs(os.path.dirname(PATH_TO_PREFERENCES), exist_ok=True)
        with open(PATH_TO_PREFERENCES, "w", encoding="utf-8") as fh:
            json.dump(prefs if isinstance(prefs, dict) else DEFAULT_PREFS, fh, indent=4)
    except Exception:
        pass


#--------------------
#
#     utils.py
#
#--------------------

from dataclasses import dataclass, asdict
from typing import List, Callable, Tuple, Type, Any, Dict
import time
import random
import re

#TODO currently has no logging; consider adding if needed

QUALITY_ALIAS_MAP = {
    # high / best
    "high": "high", "h": "high", "best": "high", "b": "high",
    # medium
    "medium": "medium", "m": "medium", "mid": "medium", "average": "medium", "a": "medium",
    # low / worst
    "low": "low", "lowest": "low", "l": "low", "worst": "low", "w": "low",
}

# Common YouTube audio bitrates (kbps)
COMMON_AUDIO_ABR = {
    "48k": "48kbps",
    "50k": "50kbps",
    "56k": "56kbps",
    "64k": "64kbps",
    "96k": "96kbps",
    "128k": "128kbps",
    "192k": "192kbps",
    "256k": "256kbps",
    "320k": "320kbps",
}

# Common YouTube video resolutions
COMMON_VIDEO_RESOLUTIONS = {
    "144p": "144p",
    "240p": "240p",
    "360p": "360p",
    "480p": "480p",
    "720p": "720p",
    "1080p": "1080p",
    "1440p": "1440p",
    "2160p": "2160p",  # 4K
}

# Boolean string parsing constants
BOOLEAN_TRUE_VALUES = ('true', '1', 'yes', 'y')
BOOLEAN_FALSE_VALUES = ('false', '0', 'no', 'n')

# FPS preference constants
FPS_ANY = 0      # Accept any FPS
FPS_30 = 30      # Prefer 30 FPS (lower bandwidth, older devices)
FPS_60 = 60      # Prefer 60 FPS (smooth motion, higher bandwidth)

def parse_bool_string(value: Any) -> bool:
    """Parse a boolean value from string or bool.
    
    Args:
        value: String ('true'/'false'/'yes'/'no'/'1'/'0'/'y'/'n') or bool
        
    Returns:
        bool: Parsed boolean value
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in BOOLEAN_TRUE_VALUES
    return bool(value)


# Domain exceptions / base
#TODO: might want to split this or adapt some specific behaviour
# downloader-specific subclasses (keep here for module-local semantics)
# TODO: improve exception hierarchy if needed and add more specific exceptions

class DownloadError(Exception):
    """Base exception for download-related errors."""
class VideoFetchError(DownloadError):
    pass

class PlaylistFetchError(DownloadError):
    pass

class StreamSelectionError(DownloadError):
    pass

class StreamDownloadError(DownloadError):
    pass

class ConversionError(DownloadError):
    pass

class CombineError(DownloadError):
    pass

# Models / result objects

@dataclass
class DownloadOptions:
    """Centralized download preferences (mirrors preferences.py DEFAULT_PREFS)."""
    default_download_directory: str = "~/Downloads"
    audio_only: bool = False
    audio_mp3: bool = False
    warn_me: bool = False
    preferred_audio_quality: str = ""
    preferred_video_quality: str = ""
    preferred_resolution: str = ""
    preferred_abr: str = ""
    preferred_mime: str = ""
    preferred_format: str = ""
    preferred_fps: int = 0  # 0=any, 30=prefer 30fps, 60=prefer 60fps
    loglevel: str = "WARNING"
    donotconvert: bool = False
    no_dir_date: bool = False
    actual_audio_bitrate: str = ""  # e.g. "128kbps" — set at runtime from selected stream

    @classmethod
    def from_preferences(cls, prefs: Dict) -> "DownloadOptions":
        """Load from preferences dict."""
        return cls(**{k: v for k, v in prefs.items() if k in cls.__dataclass_fields__})
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def update_from_dict(self, data: Dict) -> None:
        """Update options from dictionary (only non-None values)."""
        for key, value in data.items():
            if value is not None and hasattr(self, key):
                setattr(self, key, value)

@dataclass
class DownloadResult:
    success: bool
    errors: List[str]
    video_title: str = ""
    video_url: str = ""
    
    def __str__(self) -> str:
        """String representation for display."""
        status = "✓" if self.success else "✗"
        if self.success:
            return f"{status} {self.video_title}"
        else:
            error_msg = "; ".join(self.errors) if self.errors else "Unknown error"
            return f"{status} {self.video_title}: {error_msg}"

# Retry helper (stateless)
def retry_call(callable_fn: Callable[[], Any],
               exceptions: Tuple[Type[BaseException], ...] = (Exception,),
               retries: int = 3,
               backoff: float = 1.0,
               backoff_factor: float = 2.0,
               jitter: float = 0.25,
               logger=None) -> Any:
    """
    Inline retry helper for callables. Retries callable_fn() on specified exception types.
    - callable_fn: no-arg callable to execute
    - exceptions: tuple of exception types to catch and retry on
    - retries: number of retry attempts (not counting first try)
    - backoff/backoff_factor/jitter: control wait between retries
    - logger: optional logger to log retry attempts
    """
    attempts_left = retries
    delay = backoff
    attempt = 1
    while True:
        try:
            return callable_fn()
        except exceptions as e:
            if attempts_left <= 0:
                raise
            if logger:
                logger.warning(
                    "Transient error (inline) attempt %d/%d: %s — retrying in %.2fs",
                    attempt, retries + 1, e, delay
                )
            time.sleep(delay + random.uniform(0, jitter))
            attempts_left -= 1
            delay *= backoff_factor
            attempt += 1

def sanitize_filename(title: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", title)


#--------------------
#
#     yt_ripper.py
#
#--------------------

import sys
import os

#TODO ... a lot 
# implement startup into different modes based on sys.argv
# e.g. "menu" for interactive, otherwise command mode
# possibly add other modes later (e.g. GUI)
# for now, just basic interactive vs command line

#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cli.cli_command import CommandCLI

def main():
    #TODO: add GUI linking
    if sys.argv[1] in ("-h", "--help", "-l", "--loop"):
        if sys.argv[1] in ("-h", "--help"):
            print("YouTube Downloader CLI (type 'exit' or '(q)uit' to leave)")
            print("Either run in loop-mode or single by providing a single command.")
            print("- Loop mode [l]oop: command menu repeatedly after each command.")
            print("- Command mode: provide all arguments in one line.")
            print("")
            CommandCLI().run("--help")
        
        while True:
            try:
                command = input("yt-ripper> ").strip()
            except EOFError:
                print("\nExiting CLI.")
                return 1
            if command.lower() in ('exit', 'quit', 'q'):
                print("\n Exiting CLI. \n\n")
                return 0
            if not command:
                continue
            
            CommandCLI().run(command)
    else:
        cmdline = " ".join(sys.argv[1:])
        return CommandCLI().run(cmdline)

if __name__ == "__main__":
    main()


