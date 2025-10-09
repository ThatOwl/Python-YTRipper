import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
from enum import Enum
import requests

# import logger #FIXME does this work better? -> auto testing ! (pwd!)

from source.logger import get_logger
from source.stream_converter import StreamConverter
from source.url_handler import URLHandler

#TODO:
# Check interaction for pointing to right directory and path creation !!
# Add error handling for network issues, invalid URLs, etc. !
# Add support for different video/audio formats and qualities !!!
# Add command-line interface for easier usage !!
# Add unit tests for the functions !

#TODO mandatory
# handle 
#   age-restricted videos
#   private videos
#   deleted videos
#   region-restricted videos

#TODO optional
# Add progress bar for downloads
# look at /.venv/lib/python3.11/site-packages/pytubefix/query.py
# warn
#   "video_obj.length" if length is very short or very long
#   low resolution videos
#
# write a method based on "yt.streams.all()" to warn user if some formats 
# are not available for a video in a playlist 
#   and skip those formats (?)
# or download the next best format available 


logger = get_logger(__name__, 'pti_v2_debug.log')

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
        response = requests.get(thumbnail_url)
        
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
    urlh = URLHandler()
    class StreamType(Enum):
        AUDIO = 1
        VIDEO = 0
    stream_type_map = {
        StreamType.AUDIO:'Audio',
        StreamType.VIDEO:'Video'
    }

    def __init__(self):
        self.thumbnail_handler = ThumbnailHandler()
        self.stream_converter = StreamConverter()

    def _get_video_obj(self, video_url: str) -> ptf.YouTube:
        """
        #TODO summary

        Args:
            video_url (str): _description_

        Returns:
            ptf.YouTube: _description_
        """
        try:
            video_obj = ptf.YouTube(video_url)
            return video_obj
        except ptf_ex.VideoUnavailable:
            logger.error(f"Video unavailable: {video_url}")
            raise
        except ptf_ex.AgeRestrictedError:
            logger.error(f"Age-restricted video: {video_url}")
            raise
        except ptf_ex.LiveStreamError:
            logger.error(f"Live stream video (not supported): {video_url}")
            raise
        except Exception as e:
            logger.error(f"An error occurred while fetching the video: {e}")
            raise

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
        """
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

    def _download_single(self, download_dir: str, audio_only: bool = False, video_url: str = None, video_obj: ptf.YouTube = None) -> None:
        """ #FIXME
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """
        # in case a video object is already available, use it
        if video_obj is None: video_obj = self._get_video_obj(video_url)
        base_filename = self._sanitize_filename(video_obj.title)
        logger.info(f'Downloading {"soundtrack" if audio_only else "video"}: {video_obj.title}')

        if audio_only:
            audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
            thumbnail_path = None #FIXME self.thumbnail_handler.download_thumbnail(video_obj, download_dir, base_filename)
            output_path = os.path.join(download_dir, f"{base_filename}.mp3")
            if audio_path:
                self.stream_converter.convert_to_m4a(audio_path, output_path, thumbnail_path)
        else:
            video_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.VIDEO)
            audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
            output_path = os.path.join(download_dir, f"{base_filename}.mp4")
            if video_path and audio_path:
                self.stream_converter.combine_streams(audio_path, video_path, output_path)
        logger.debug(f'Download of {"soundtrack" if audio_only else "video"} completed.')

    def _download_playlist(self, playlist_url: str, download_dir: str, audio_only: bool = False) -> None:
        """
        Download all videos from a YouTube playlist as video or audio files.

        Args:
            playlist_url (str): The URL of the YouTube playlist.
            download_dir (str): The directory to save the downloaded files.
            audio_only (bool): If True, download audio only. If False, download video.
        Side Effects:
            - creates directory as playlist download target. 
        """
        playlist_obj = ptf.Playlist(playlist_url)
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        logger.debug(f"Found {len(playlist_obj.video_urls)} videos in the playlist. {playlist_obj.title}")
        if not os.path.exists(download_dir + '/' + playlist_obj.title): #FIXME: chcek man test
            os.mkdir(download_dir + '/' + playlist_obj.title)

        for i, video in enumerate(playlist_obj.videos):
            logger.info(f'At {"soundtrack" if audio_only else "video"} {i + 1}/{len(playlist_obj.videos)}: ')
            self._download_single(download_dir=download_dir, audio_only=audio_only, video_obj=video)

        logger.info("Playlist download completed.")

    def single_video_info(self, video_url: str = None, video_obj: ptf.YouTube = None) -> None:
        """
        Print information about a single YouTube video.

        Args:
            video_url (str): The URL of the YouTube video.
        """
        if video_obj is None: video_obj = self._get_video_obj(video_url)
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

    def download(self, url: str, download_dir: str, audio_only: bool = False) -> None:
        """
        Download a single YouTube video or a playlist based on the provided URL.
        Args:
            url (str): The URL of the YouTube video or playlist.
            download_dir (str): The directory to save the downloaded files.
            audio_only (bool): If True, download audio only. If False, download video.
        Side Effects:
            - creates directory as general download target.
        """
        
        failed = False #TODO could implement control-flow to accomodate failed downloads later
        
        if self.urlh.is_youtube_url(url):
            logger.debug(f"Valid YouTube URL: {url}")

            if not os.path.exists(download_dir):
                os.mkdir(download_dir)
                logger.debug(f"Created download directory: {download_dir}")

            if self.urlh.is_youtube_playlist(url):
                logger.debug("Detected as a playlist URL.")
                #would be: failed = self._download_playlist(playlist_url=url, download_dir=download_dir, audio_only=audio_only)
                self._download_playlist(playlist_url=url, download_dir=download_dir, audio_only=audio_only)
            else:
                logger.debug("Detected as a single video URL.")
                self._download_single(video_url=url, download_dir=download_dir, audio_only=audio_only)
                
        #if failed:
        #    logger.error("One or more downloads failed.")   