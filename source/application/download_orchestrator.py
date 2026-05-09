
import pytubefix as ptf
import re
from typing import List
from pathlib import Path 


from utility.logger import get_logger
from utility.utils import VideoFetchError, PlaylistFetchError, StreamSelectionError, StreamDownloadError, ConversionError, CombineError, DownloadOptions, DownloadResult, QUALITY_ALIAS_MAP, sanitize_filename

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

    # TODO improve error handling (return exceptions or ...?)
    def download_playlist(self, playlist_url: str, options: DownloadOptions) -> List[DownloadResult]:
        """
        Download all videos from a YouTube playlist as video or audio files.

        Args:
            playlist_url (str): The URL of the YouTube playlist.
            options (DownloadOptions): The processing options specifying preferences for audio/video quality, format, etc.
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

    def _download_single_video(self, video_obj: ptf.YouTube, download_dir: Path, options: DownloadOptions) -> None:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video to download.
            download_dir (str): The directory to save the downloaded file.
            options (DownloadOptions): The processing options specifying preferences for audio/video quality, format, etc.
        Side Effects:
            - Downloads the specified video to the given directory.
            - May create temporary files during processing.
        Logs:
            - Download status and any errors encountered during the process.
        Returns:
            None (currently)
        """
        video_stream: ptf.Stream = self.stream_selector.select_stream_video(video_obj, options)
        video_path:Path = self.stream_download.download_stream(video_stream, download_dir)
        
        # TODO refine + decide user options in DownloadOptions + ConversionParameters
        use_this_for_conversion = [video_stream.audio_codec, video_stream.abr, video_stream.bitrate, video_stream.codecs, video_stream.mime_type, video_stream.resolution, video_stream.fps] 
        
        audio_stream: ptf.Stream = self.stream_selector.select_stream_audio(video_obj, options)
        audio_path:Path = self.stream_download.download_stream(audio_stream, download_dir)

        output_path = video_path

        #TODO: refine (handle audio?)
        if not video_path:
            raise StreamDownloadError("Missing audio or video stream")

        
        #TODO !! handle media with no audio stream (e.g. 480p music videos have combined vid-aud-stream) => currently this would just fail with "missing audio or video stream" 
        # => check with if audio_path is None ... and checking video_stream.audio_codec or video_stream.codecs 
        # => this would require some changes in the StreamSelector and StreamDownloadService to allow for optional audio/video streams, and 
        # also in the StreamConverter to handle the case where one of the streams is missing. 
        
        if not options.donotconvert:
            self.stream_converter.combine_streams(audio_path=audio_path, video_path=video_path, output_path=output_path) # TODO inp-name = outp-name
        

    def _download_single_audio(self, video_obj: ptf.YouTube, options: DownloadOptions, download_dir: Path) -> None:
        """
        Download a single YouTube video's audio stream.

        Args:
            video_url (str): The URL of the YouTube video to download.
            download_dir (str): The directory to save the downloaded file.
            options (DownloadOptions): The processing options specifying preferences for audio quality, format, etc.
        Side Effects:
            - Downloads the specified audio stream to the given directory.
            - May create temporary files during processing.
        Logs:
            - Download status and any errors encountered during the process.
        Returns:
            None (currently)
        """

        audio_stream: ptf.Stream = self.stream_selector.select_stream_audio(video_obj, options)
        audio_path:Path = self.stream_download.download_stream(audio_stream, download_dir)
        thumbnail_path = None #FIXME self.thumbnail_handler.download_thumbnail(video_obj, download_dir, base_filename)
        
        #TODO: where to put this logic if any => copy input to output (=> delte entirly?)
        output_path = audio_path

        #TODO: refine
        if not audio_path:
            raise StreamDownloadError("No audio stream downloaded")
        
        if not options.donotconvert: 
            self.stream_converter.convert_audio( # TODO inp-name = outp-name
                audio_path, output_path,
                thumbnail_path=thumbnail_path,
                audio_bitrate=audio_stream.abr, #TODO refine this + decide user options in DownloadOptions + ConversionParameters
                audio_mp3=options.audio_mp3,
            )
    
    def download_single(self, options: DownloadOptions, download_dir: Path, video_obj: ptf.YouTube = None, url: str = None) -> DownloadResult:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_obj (ptf.YouTube): The YouTube video object to download.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """        
        video_obj = video_obj or self.vid_fetcher.get_video_obj(url)
        
        base_filename: str = sanitize_filename(video_obj.title)
        video_title = video_obj.title
        video_url = video_obj.watch_url
        
        # Efficiency safeguard: skip download if target file already exists 
        # (e.g. from previous failed attempt, or if user is re-downloading a playlist they already downloaded before and some files are still there) => this also allows for resuming partially downloaded playlists without re-downloading existing files
        ext = ".mp3" if options.audio_only and options.audio_mp3 else ".m4a" if options.audio_only else ".mp4"
        target_file = Path(download_dir) / f"{base_filename}{ext}"
        
        #TODO ? refactor this look at: https://vscode.dev/github/RF-at-FH-Joanneum/Python-YTRipper/blob/Restructure_Orchestration_2887-7ee1-42fe-b3eb-f9c44204ae2
        if target_file.exists():
            logger.info(f"⏭ Skipping (already exists): {video_title} -> {target_file.name}")
            return DownloadResult(success=True, errors=[], video_title=video_title, video_url=video_url)

        logger.info(f'Downloading {"soundtrack" if options.audio_only else "video"}: {video_title}')
        
        try:
            if options.audio_only:
                self._download_single_audio(video_obj=video_obj, download_dir=download_dir, options=options)
            else:
                self._download_single_video(video_obj=video_obj, download_dir=download_dir, options=options)

            logger.info(f"✓ {video_title}")
            return DownloadResult(success=True, errors=[], video_title=video_title, video_url=video_url or video_obj.watch_url)

        except Exception as e:
            logger.error(f"✗ {video_title}: {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url or video_obj.watch_url)
    
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
                    results.append(self.download_single(url=url, options=options, download_dir=download_dir))

            except Exception as e:
                logger.error(f"Download failed: {e}")
                return results
        else:
            logger.error("The provided URL is not a valid YouTube URL or inaccessible.")
            raise ValueError("The provided URL is not valid or unreachable.")
        
        return results

        