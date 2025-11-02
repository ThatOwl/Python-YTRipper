import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
from enum import Enum
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import List
import time
import random

#FIXME check import from different locations
from source.logger_a_constants import get_logger
from source.stream_converter import StreamConverter
from source.url_handler import URLHandler
from source.os_interactions import OSInteractions

#- Missing  proper cleanup and logging practices to avoid duplicate logs and maintain clarity.

logger = get_logger(__name__, 'ytd-th_debug.log')

class DownloadError(Exception):
    """Base exception for download-related errors."""

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

@dataclass#(frozen=True)
class DownloadOptions:
    audio_only: bool = False
    preferred_abr: str = ""
    preferred_resolution: str = ""
    preferred_audio_quality: str = ""
    preferred_video_quality: str = ""
    preferred_format: str = ""
    preferred_mime: str = ""
    # Add more options as needed
    
    @classmethod
    def from_preferences(cls, prefs: dict) -> 'DownloadOptions':
        return cls(
            audio_only=prefs.get("audio_only", False),
            preferred_abr=prefs.get("preferred_abr", ""),
            preferred_resolution=prefs.get("preferred_resolution", ""),
            preferred_audio_quality=prefs.get("preferred_audio_quality", "best"),
            preferred_video_quality=prefs.get("preferred_video_quality", "best"),
            preferred_format=prefs.get("preferred_format", ""),
            preferred_mime=prefs.get("preferred_mime", ""),
        )

@dataclass
class DownloadResult:
    success: bool
    errors: List[str]

def retry_call(callable_fn, exceptions=(Exception,), retries: int = 3, backoff: float = 1.0,
               backoff_factor: float = 2.0, jitter: float = 0.25, logger=None):
    """
    Inline retry helper for callables (useful for third-party methods).
    Retries callable_fn() on specified exception types.
    Args:
        callable_fn: The callable to be executed.
        exceptions: A tuple of exception types that should trigger a retry.
        retries: Number of retry attempts.
        backoff: Initial delay between retries in seconds.
        backoff_factor: Factor by which the delay increases after each retry.
        jitter: Maximum random jitter to add to the delay in seconds.
        logger: Optional logger for logging retry attempts.
    Returns:
        The result of callable_fn() if successful.
    Raises:
        The last exception raised by callable_fn() after exhausting retries.
    """
    attempts_left = retries
    delay = backoff
    attempt = 1
    while True:
        try:
            return callable_fn()
        except exceptions as e:
            if attempts_left <= 0:
                # no retries left; re-raise
                raise
            if logger:
                #not recognized by pylint ? .warning correct?
                logger.warning("Transient error (inline) in attempt %d/%d: %s — retrying in %.2fs",
                               attempt, retries + 1, e, delay)
            time.sleep(delay + random.uniform(0, jitter))
            attempts_left -= 1
            delay *= backoff_factor
            attempt += 1

# Will be exported to own file later
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
            logger.info(f"Thumbnail downloaded to: {thumbnail_path}")
            return thumbnail_path
        else:
            logger.warning("Failed to download thumbnail.")
            return ""

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

    def __init__(self, os_handler: OSInteractions = None):
        self.thumbnail_handler = ThumbnailHandler()
        self.stream_converter = StreamConverter()
        self.urlh = URLHandler()
        self.os_handler = os_handler
        if self.os_handler is None:
            from source.os_interactions import OSInteractions
            self.os_handler = OSInteractions()

    def _get_video_obj(self, video_url: str) -> ptf.YouTube:
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
        except ptf_ex.VideoUnavailable as e:
            # concise user-facing error
            logger.error("Video unavailable: %s", video_url)
            # full diagnostic to debug/file
            logger.debug("VideoUnavailable exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"video unavailable: {video_url}") from e
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

    def _download_stream_type(self, video: ptf.YouTube, download_dir: str, base_filename: str, type: Enum) -> str:
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
            if type == self.StreamType.AUDIO:
                stream = video.streams.filter(type='audio').order_by('abr').desc().first()
                logger.debug(f"Selected audio stream: {stream.abr}, {stream.mime_type}")
            else:
                stream = video.streams.filter(type='video', progressive=False).order_by('resolution').desc().first()
                logger.debug(f"Selected video stream: {stream.resolution}, {stream.mime_type}")

            if not stream:
                logger.debug(f"No suitable {self.stream_type_map[type]} stream available for this video.")
                return ""
            
            ext = stream.subtype
            downloaded_path = stream.download(
                output_path=download_dir,
                filename=f"{base_filename}_{self.stream_type_map[type]}.{ext}",
                skip_existing=True,
                timeout=5,
                max_retries=3
            )
            return downloaded_path
        
        except Exception as e:
            logger.exception(f"Error downloading {self.stream_type_map[type]} stream: {e}")
            raise StreamDownloadError(f"Error downloading {self.stream_type_map[type]} stream: {e}") from e

    def download_single(self, download_dir: str, options: DownloadOptions, video_url: str = None, video_obj: ptf.YouTube = None) -> DownloadResult:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """
        # in case a video object is already available, use it
        try:
            if video_obj is None: 
                video_obj = self._get_video_obj(video_url)
        except Exception as e:
            logger.error(f"Failed to fetch video object: {e}")
            return DownloadResult(success=False, errors=[str(e)])

        base_filename = self._sanitize_filename(video_obj.title)
        logger.info(f'Downloading {"soundtrack" if options.audio_only else "video"}: {video_obj.title}') #TODO log less info?
        try:
            if options.audio_only:
                audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
                thumbnail_path = None #FIXME self.thumbnail_handler.download_thumbnail(video_obj, download_dir, base_filename)
                output_path = os.path.join(download_dir, f"{base_filename}.m4a")
                if not audio_path:
                    msg = "no audio stream available"
                    logger.error(msg)
                    return DownloadResult(success=False, errors=[msg])
                self.stream_converter.convert_to_m4a(audio_path, output_path, thumbnail_path)
                
            else:
                video_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.VIDEO)
                audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
                output_path = os.path.join(download_dir, f"{base_filename}.mp4")
                if not video_path or not audio_path:
                    msg = "missing audio or video stream"
                    logger.error(msg)
                    return DownloadResult(success=False, errors=[msg])
                self.stream_converter.combine_streams(audio_path, video_path, output_path)

            logger.debug(f'Download of {"soundtrack" if options.audio_only else "video"} completed.')
            return DownloadResult(success=True, errors=[])
        
        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"Download failed: {e}")
            return DownloadResult(success=False, errors=[str(e)])
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return DownloadResult(success=False, errors=[str(e)])

    def download_playlist(self, playlist_url: str, download_dir: str, options: DownloadOptions) -> List[DownloadResult]:
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
        
        download_dir = download_dir + '/' + date + playlist_obj.title
        # create new directory for each playlists -> easier for user
        if not os.path.exists(download_dir): #works for one level only
            logger.debug(f"Creating playlist download directory: {download_dir}")
            os.mkdir(download_dir)

        for i, video in enumerate(playlist_obj.videos):
            logger.info(f'At {"soundtrack" if options.audio_only else "video"} {i + 1}/{len(playlist_obj.videos)}: ')
            result = self.download_single(download_dir=download_dir, options=options, video_obj=video)
            results.append(result)

        logger.info("Playlist download completed.")
        return results

    def info(self, url: str = None, video_obj: ptf.YouTube = None) -> None:
        """Print information about a YouTube video or playlist.
        Args:
            url (str): The URL of the YouTube video or playlist.
            video_obj (ptf.YouTube, optional): An existing YouTube video object. Defaults to None.
        Side Effects:
            - prints information to the console."""
        
        if self.urlh.is_youtube_playlist(url):
            try: 
                playlist_obj = self._get_playlist_obj(url)
            except Exception as e:
                logger.error(f"Failed to fetch playlist object: {e}")
                return #TODO could raise error upstream
        
            
            logger.info(f"Playlist Title: {playlist_obj.title}")
            logger.info(f"Number of Videos: {len(playlist_obj.videos)}")
            #logger.info(f"Playlist Description: {playlist_obj.description}")
            logger.info("Videos:")
            for i, video in enumerate(playlist_obj.videos):
                logger.info(f"{i + 1}. {video.title} ({video.length} seconds)")
        else:
            try: 
                if video_obj is None: video_obj = self._get_video_obj(url)
            except Exception as e:
                logger.error(f"Failed to fetch video object: {e}")
                return #TODO could raise error upstream
        
            logger.debug(f'Video title: {video_obj.title}')
            logger.debug(f'Video length: {video_obj.length} seconds')
            logger.debug(f'Video views: {video_obj.views}')
            logger.debug(f'Video author: {video_obj.author}')
            logger.debug(f'Video description: {video_obj.description[:200]}...')
            logger.debug(f"Thumbnail: {video_obj.thumbnail_url}")
            logger.debug("Available streams:")
            
            logger.debug("  Video:")
            for stream in video_obj.streams.filter(type='video').order_by('resolution').desc():
                logger.debug(f'- {stream.resolution}, {stream.mime_type}, {stream.fps}fps')
            logger.info(video_obj.streams.filter(type='video').order_by('resolution').desc().first())
            
            logger.debug("  Audio:")
            for stream in video_obj.streams.filter(type='audio').order_by('abr').desc():
                logger.debug(f'- {stream.mime_type}, {stream.abr}')
            logger.info(video_obj.streams.filter(type='audio').order_by('abr').desc().first())

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
                if not os.path.exists(download_dir): #works for one level only
                    os.mkdir(download_dir)
                    logger.debug(f"Created download directory: {download_dir}")

                if self.urlh.is_youtube_playlist(url):
                    logger.debug("Detected as a playlist URL.")
                    results = self.download_playlist(playlist_url=url, download_dir=download_dir, options=options)
                else:
                    logger.debug("Detected as a single video URL.")
                    results.append(self.download_single(video_url=url, download_dir=download_dir, options=options))
                    
            except Exception as e:
                logger.error(f"Download failed: {e}")
                return #TODO could raise error upstream
        else:
            logger.error("The provided URL is not a valid YouTube URL or inaccessible.")
            raise ValueError("The provided URL is not valid or unreachable.")
        
        # Summarize results
        success_count = sum(1 for result in results if result.success)
        failure_count = len(results) - success_count
        logger.info(f"Download Summary: {success_count} succeeded, {failure_count} failed.")