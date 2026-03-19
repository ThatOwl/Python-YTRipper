from xml.etree.ElementInclude import include
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
from core.utils import DownloadError, DownloadOptions, DownloadResult, QUALITY_ALIAS_MAP

logger = get_logger(__name__, 'pytube_interface_debug.log')

# DEBUG < INFO < WARNING < ERROR < CRITICAL

# downloader-specific subclasses (keep here for module-local semantics)
# TODO: improve exception hierarchy if needed and add more specific exceptions
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
        
    def get_video_obj(self, video_url: str) -> ptf.YouTube | Exception:
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
    def get_playlist_obj(self, playlist_url: str) -> ptf.Playlist:
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

    # TODO: Test and         
    def download_stream_type(self, video: ptf.YouTube, download_dir: Path, options: DownloadOptions, base_filename: str, str_type: Enum) -> str | None:
        """
            Downloads either the highest quality audio or video stream from a YouTube video object.
            
            Args:
                video (ptf.YouTube): The YouTube video object from which to download the stream.
                download_dir (Path): The directory where the downloaded file will be saved.
                options (DownloadOptions): The download options specifying preferences.
                base_filename (str): The base filename to use for the downloaded file.
                str_type (Enum): The type of stream to download (AUDIO or VIDEO).
            Returns:
                str: The file path of the downloaded stream, or an empty string if no suitable stream is found.
            Logs:
                - Selected stream details (audio bitrate or video resolution and mime type).
                - If no suitable stream is available.
            Raises:
                StreamDownloadError: If there is an error during the download process.
        """
        
        try:
            # Use the new stream selector
            stream: ptf.Stream = self._select_stream(video, str_type, options)
            
            # Log selected stream details
            if str_type == self.StreamType.AUDIO:
                logger.debug(f"Selected audio stream: {stream.abr}, {stream.mime_type}")
                # Capture the actual bitrate so the converter can match it
                options.actual_audio_bitrate = stream.abr or ""
            else:
                logger.debug(f"Selected video stream: {stream.resolution}, {stream.mime_type}")
            
        except StreamSelectionError as e:
            logger.warning(f"No suitable {self.stream_type_map[str_type]} stream available: {e}")
            return ""
        
        # Download the selected stream
        try:
            downloaded_path = stream.download(
                output_path=str(download_dir),
                skip_existing=True,
                timeout=5,
                max_retries=3
            )
            
            logger.debug(f"{self.stream_type_map[str_type]} stream downloaded to: {downloaded_path}")
            return downloaded_path
        except Exception as e:
            logger.exception(f"Error downloading {self.stream_type_map[str_type]} stream: {e}")
            raise StreamDownloadError(f"Error downloading {self.stream_type_map[str_type]} stream: {e}") from e
    