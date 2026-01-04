import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
from enum import Enum
from datetime import datetime
from typing import List
from pathlib import Path 

from core.logger import get_logger
from core.stream_converter import StreamConverter
from core.url_handler import URLHandler
from core.os_interactions import OSInteractions
from core.thumbnail_handler import ThumbnailHandler
from core.utils import DownloadError, DownloadOptions, DownloadResult

logger = get_logger(__name__, 'ytd_debug.log')

# downloader-specific subclasses (keep here for module-local semantics)
class VideoFetchError(DownloadError):
    pass

class PlaylistFetchError(DownloadError):
    pass

class StreamDownloadError(DownloadError):
    pass

class ConversionError(DownloadError):
    pass

class CombineError(DownloadError):
    pass

class YouTubeDownloader:
    """
    Handles high-level download logic for YouTube videos and playlists using pytubefix.
    """
    class StreamType(Enum):
        AUDIO = 1
        VIDEO = 0
    stream_type_map = {
        StreamType.AUDIO:'Audio',
        StreamType.VIDEO:'Video'
    }

    def __init__(self, os_handler: OSInteractions):
        self.thumbnail_handler = ThumbnailHandler()
        self.stream_converter = StreamConverter()
        self.urlh = URLHandler()
        self.os_handler = os_handler
        if self.os_handler is None:
            from source.core.os_interactions import OSInteractions
            self.os_handler = OSInteractions()

    def _get_video_obj(self, video_url: str) -> ptf.YouTube | Exception:
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
            raise VideoFetchError(f"Live stream video (not supported): {video_url}") from e
        except ptf_ex.RegexMatchError as e:
            logger.error("Invalid or malformed video URL: %s", video_url)
            logger.debug("RegexMatchError while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Regex match error for video: {video_url}") from e
        except ptf_ex.VideoPrivate as e:
            logger.error("Private video: %s", video_url)
            logger.debug("VideoPrivate while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Private video: {video_url}") from e
        except ptf_ex.VideoRegionBlocked as e:
            logger.error("Region-blocked video: %s", video_url)
            logger.debug("VideoRegionBlocked while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Region-blocked video: {video_url}") from e
        except (ptf_ex.AgeCheckRequiredAccountError, ptf_ex.AgeCheckRequiredError) as e:
            logger.error("Age check required for video: %s", video_url)
            logger.debug("Age-check exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Age check required for video: {video_url}") from e
        except ptf_ex.VideoUnavailable as e:
            # concise user-facing error
            logger.error("Video unavailable: %s", video_url)    
            # full diagnostic to debug/file
            logger.debug("VideoUnavailable exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"video unavailable: {video_url}") from e
        except Exception as e:
            logger.error("Failed to fetch video: %s", video_url)
            logger.debug("Unexpected exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"An error occurred while fetching the video {video_url}: {e}") from e

    #TODO improve error handling
    def _get_playlist_obj(self, playlist_url: str) -> ptf.Playlist:
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
            raise PlaylistFetchError(f"An error occurred while fetching the playlist {playlist_url}: {e}") from e

    def _sanitize_filename(self, title: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", title)

    #FIXME: does not use preferred quality etc yet
    #FIXME: does not use os.path ... str or PathLike ???
    def _download_stream_type(self, video: ptf.YouTube, download_dir: Path, base_filename: str, str_type: Enum) -> str | None:
        """
        Downloads either the highest quality audio or video stream from a YouTube video object.
        
        Args:
            video (ptf.YouTube): The YouTube video object from which to download the stream.
            download_dir (str): The directory where the downloaded file will be saved.
            base_filename (str): The base filename to use for the downloaded file.
            type (int): The type of stream to download. If truthy, downloads audio; if falsy, downloads video.
        Returns:
            str: The file path of the downloaded stream, or an empty string if no suitable stream is found.
        Logs:
            - Selected stream details (audio bitrate or video resolution and mime type).
            - If no suitable stream is available.
        Raises:
            StreamDownloadError: If there is an error during the download process.
        """
        try:
            # Select the appropriate stream based on the type
            #TODO implement preferred quality, abr, resolution
            if str_type == self.StreamType.AUDIO:
                stream: ptf.Stream = video.streams.filter(type='audio').order_by('abr').desc().first()
                logger.debug(f"Selected audio stream: {stream.abr}, {stream.mime_type}")
            else:
                stream: ptf.Stream = video.streams.filter(type='video', progressive=False).order_by('resolution').desc().first()
                logger.debug(f"Selected video stream: {stream.resolution}, {stream.mime_type}")

            if not stream:
                logger.warning(f"No suitable {self.stream_type_map[str_type.value]} stream available for this video.")
                return ""
            
            ext = stream.subtype # FIXME: this is idiotic
            downloaded_path = stream.download(
                output_path=str(download_dir),
                filename=f"{base_filename}_{self.stream_type_map[str_type.value]}.{ext}", # FIXME: does nothing
                skip_existing=True,
                timeout=5,
                max_retries=3
            )
            
            #TODO: could be changed to 
            # file: Path =  stream.download()
            # file.rename("base_filename")
            # file.with_suffix
            # file.with_name
            # file.with_stem
            return downloaded_path
        
        except Exception as e:
            logger.exception(f"Error downloading {self.stream_type_map[str_type.value]} stream: {e}")
            raise StreamDownloadError(f"Error downloading {self.stream_type_map[str_type.value]} stream: {e}") from e

    def download_single(self, download_dir: Path, options: DownloadOptions, video_obj: ptf.YouTube) -> DownloadResult:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_obj (ptf.YouTube): The YouTube video object to download.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """        
        base_filename: str = self._sanitize_filename(video_obj.title)
        logger.info(f'Downloading {"soundtrack" if options.audio_only else "video"}: {video_obj.title}') #TODO log less info?
        
        try:
            if options.audio_only:
                audio_path_str = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
                thumbnail_path = None #FIXME self.thumbnail_handler.download_thumbnail(video_obj, download_dir, base_filename)
                output_path = Path(download_dir) / f"{base_filename}{'.mp3' if options.audio_mp3 else '.m4a'}"
                if not audio_path_str:
                    msg = "no audio stream available"
                    logger.error(msg)
                    return DownloadResult(success=False, errors=[msg])
                audio_path = Path(audio_path_str)
                self.stream_converter.convert_audio(audio_path, output_path, thumbnail_path)
                
            else:
                video_path_str = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.VIDEO)
                audio_path_str = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
                output_path = Path(download_dir) / f"{base_filename}.mp4"
                if not video_path_str or not audio_path_str:
                    msg = "missing audio or video stream"
                    logger.error(msg)
                    return DownloadResult(success=False, errors=[msg])
                video_path = Path(video_path_str)
                audio_path = Path(audio_path_str)
                self.stream_converter.combine_streams(audio_path, video_path, output_path)

            logger.debug(f'Download of {"soundtrack" if options.audio_only else "video"} completed.')
            return DownloadResult(success=True, errors=[])
        
        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"Download failed: {e}")
            return DownloadResult(success=False, errors=[str(e)])
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return DownloadResult(success=False, errors=[str(e)])

    # TODO improve error handling (return exceptions or ...?)
    def download_playlist(self, playlist_url: str, download_dir: Path, options: DownloadOptions) -> List[DownloadResult]:
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
        date = datetime.today().strftime('%Y_%m_')
        results: List[DownloadResult] = []
        try:
            playlist_obj = self._get_playlist_obj(playlist_url)
        except Exception as e:
            logger.error(f"Failed to fetch playlist object: {e}")
            return #TODO could raise error upstream
        
        # Override pytube's video URL regex to capture all videos in the playlist
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        logger.debug(f"Found {len(playlist_obj.video_urls)} videos in the playlist. {playlist_obj.title}")
        
        # Build a Path for the playlist directory and ensure it exists
        playlist_dir = Path(download_dir) / f"{date}{self._sanitize_filename(playlist_obj.title)}"

        # create new directory for each playlists -> easier for user
        try:
            if not playlist_dir.exists(): #if user retries existing dir, skip creation
                logger.info(f"Creating playlist download directory: {playlist_dir}")
                playlist_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create playlist directory {playlist_dir}: {e}")
            return results

        for i, video in enumerate(playlist_obj.videos):
            logger.info(f'At {"soundtrack" if options.audio_only else "video"} {i + 1}/{len(playlist_obj.videos)}: ')
            result = self.download_single(download_dir=playlist_dir, options=options, video_obj=video)
            results.append(result)

        logger.info("Playlist download completed.")
        return results

    def info(self, url: str = None, video_obj: ptf.YouTube = None, output: callable = logger.info) -> None:
        """
        Print or log information about a YouTube video or playlist.

        Args:
        url (str): The URL of the YouTube video or playlist.
        video_obj (ptf.YouTube, optional): A YouTube video object. Defaults to None.
        output (callable, optional): A callable that takes a string, e.g. `print` or `logger.info`.
            Defaults to `logger.info`.
        """
        #DELETEME
        #output = output or logger.info
        
        if self.urlh.is_youtube_playlist(url):
            try:
                playlist_obj = self._get_playlist_obj(url)
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
                    video_obj = self._get_video_obj(url)
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

    def download(self, url: str, download_dir: str, options: DownloadOptions) -> None:
        """
        Download a YouTube video or playlist.
        Args:
            url (str): The URL of the YouTube video or playlist.
            download_dir (str): The directory to save the downloaded files.
            options (DownloadOptions): The download options.
        Side Effects:
            - creates download directory if it does not exist. 
        Logs:
            - Download status.
        """
        results = []
        
        if self.urlh.is_youtube_url(url) and self.urlh.is_accessible(url):
            logger.debug(f"Valid YouTube URL: {url}")
            try:
                if not os.path.exists(download_dir): # should work for multiple levels TODO: check
                    os.makedirs(download_dir)
                    logger.info(f"Created download directory: {download_dir}")

                if self.urlh.is_youtube_playlist(url):
                    logger.debug("Detected as a playlist URL.")
                    results = self.download_playlist(playlist_url=url, download_dir=download_dir, options=options)
                else:
                    logger.debug("Detected as a single video URL.")
                    video = self._get_video_obj(url)
                    results.append(self.download_single(video_obj=video, download_dir=download_dir, options=options))
                    
            except Exception as e:
                logger.error(f"Download failed: {e}")
                return #TODO could raise error upstream
        else:
            logger.error("The provided URL is not a valid YouTube URL or inaccessible.")
            raise ValueError("The provided URL is not valid or unreachable.")
        
        # Summarize results
        success_count = sum(1 for result in results if result.success)
        failure_count = len(results) - success_count
        logger.info(f"Download Summary: {success_count} succeeded, {failure_count} failed.")''