import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
import ffmpeg as fpg
from source.logger import get_logger
from enum import Enum
import requests

#TODO: Add logging instead of print statements
# Add error handling for network issues, invalid URLs, etc.
# Add support for different video/audio formats and qualities
# Add command-line interface for easier usage
# Add unit tests for the functions

#TODO mandatory
# look at /.venv/lib/python3.11/site-packages/pytubefix/query.py
# warn
#   "video_obj.length" if length is very short or very long
#   low resolution videos
# handle 
#   age-restricted videos
#   private videos
#   deleted videos
#   region-restricted videos

#TODO optional
# Add progress bar for downloads

# write a method based on "yt.streams.all()" to warn user if some formats 
# are not available for a video in a playlist 
#   and skip those formats (?)
# or download the next best format available 

logger = get_logger(__name__, 'pti_debug.log')

class PyTubeDownloader:
    """
    A class to handle downloading YouTube videos and playlists using pytubefix.
    Supports downloading single videos, playlists, audio streams, and displaying video info.
    """

    class StreamType(Enum):
        AUDIO = 1
        VIDEO = 0
    stream_type_map = {
        StreamType.AUDIO:'Audio',
        StreamType.VIDEO:'Video'
    }
    
    def __init__(self):
        """Initialize the PyTubeDownloader."""
        pass

    def _get_video_obj(self, video_url: str) -> ptf.YouTube:
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
    
    def _download_stream_type(self, video: ptf.YouTube, download_dir: str, base_filename: str, type: StreamType) -> str:
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
        if type == self.StreamType.AUDIO:  # audio:
            stream = video.streams.filter(type='audio').order_by('abr').desc().first()
            logger.debug(f"Selected audio stream: {stream.abr}, {stream.mime_type}")
        else:
            stream = video.streams.filter(type='video', progressive=False).order_by('resolution').desc().first()
            logger.debug(f"Selected video stream: {stream.resolution}, {stream.mime_type}")
        
        if not stream:
            logger.debug(f"No suitable {self.stream_type_map[type]} stream available for this video.")
            return ""
        ext = stream.subtype
        #file_path = os.path.join(download_dir, f"{base_filename}_{self.stream_type_map[type]}.{ext}")
        downloaded_path = stream.download(
            output_path=download_dir,
            filename=f"{base_filename}_{self.stream_type_map[type]}.{ext}",
            skip_existing=True,
            timeout=5,
            max_retries=3
        )
        return downloaded_path
    
    def _convert_to_mp3(self, audio_path: str, output_path: str, thumbnail_path: str = None) -> None:
        """
        Converts an audio file to MP3 format using ffmpeg and saves it to the specified output path.
        Optionally embeds a thumbnail image into the MP3 file.

        Args:
            audio_path (str): The path to the source audio file to be converted.
            output_path (str): The path where the converted MP3 file will be saved.
            thumbnail_path (str, optional): Path to the thumbnail image to embed.
        """
        logger.debug("Converting audio to mp3 with ffmpeg...")
        try:
            if thumbnail_path and os.path.exists(thumbnail_path):
                (
                    fpg
                    .input(audio_path)
                    .output(
                        output_path,
                        acodec='mp3',
                        **{'id3v2_version': '3'},
                        extra_args=[
                            '-i', thumbnail_path,
                            '-map', '0:a',
                            '-map', '1:v',
                            '-metadata:s:v', 'title=Album cover',
                            '-metadata:s:v', 'comment=Cover (front)'
                        ]
                    )
                    .run(overwrite_output=True, quiet=True)
                )
                os.remove(thumbnail_path)
            else:
                (
                    fpg
                    .input(audio_path)
                    .output(output_path, acodec='mp3', strict='experimental')
                    .run(overwrite_output=True, quiet=True)
                )
            logger.info(f"Audio file saved to: {output_path}")
            os.remove(audio_path)
        except Exception as e:
            logger.exception(f"Error during ffmpeg audio conversion: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original audio file.")


    def _convert_to_mp3_v1(self, audio_path: str, output_path: str) -> None:
        """
        Converts an audio file to MP3 format using ffmpeg and saves it to the specified output path.

        Args:
            audio_path (str): The path to the source audio file to be converted.
            output_path (str): The path where the converted MP3 file will be saved.
        Raises:
            Exception: Logs and handles any exceptions that occur during the conversion process.
        Side Effects:
            - Saves the converted MP3 file to the specified output path.
            - Removes the original audio file upon successful conversion.
            - Logs conversion progress and errors.
        """
        logger.debug("Converting audio to mp3 with ffmpeg...")
        try:
            (
                fpg
                .input(audio_path)
                .output(output_path, acodec='mp3', strict='experimental')
                .run(overwrite_output=True, quiet=True)
            )
            logger.info(f"Audio file saved to: {output_path}")
            os.remove(audio_path)
        except Exception as e:
            logger.exception(f"Error during ffmpeg audio conversion: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original audio file.")
            
    def _download_thumbnail(self, video: ptf.YouTube, download_dir: str, base_filename: str) -> str:
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
        #TODO use urllib to download the thumbnail in max quality and handle errors
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

    #FIXME: seems to fail with some videos
    def _combine_streams(self, audio_path: str, video_path: str, output_path: str) -> None:
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
        try:
            (
                fpg
                .output(fpg.input(video_path), fpg.input(audio_path), output_path, vcodec='copy', acodec='aac', strict='experimental')
                .run(overwrite_output=True, quiet=True)
            )
            logger.info(f"Merged file saved to: {output_path}")
            os.remove(video_path)
            os.remove(audio_path)
        except Exception as e:
            logger.exception(f"Error during ffmpeg merging: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original files.")

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
    
    def download_single(self, download_dir: str, audio_only: bool = False, video_url: str = None, video_obj: ptf.YouTube = None) -> None:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """
        if video_obj is None: video_obj = self._get_video_obj(video_url)

        base_filename = self._sanitize_filename(video_obj.title)
        logger.info(f'Downloading {"soundtrack" if audio_only else "video"}: {video_obj.title}')
        
        if audio_only:
            audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
            thumbnail_path = None #FIXME = self._download_thumbnail(video_obj, download_dir, base_filename)
            output_path = os.path.join(download_dir, f"{base_filename}.mp3")
            if audio_path:
                self._convert_to_mp3(audio_path, output_path, thumbnail_path)
        else:
            video_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.VIDEO)
            audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
            output_path = os.path.join(download_dir, f"{base_filename}.mp4")
            if video_path and audio_path:
                self._combine_streams(audio_path, video_path, output_path)
        logger.debug(f"Download of {"soundtrack" if audio_only else "video"} completed.")

    def download_playlist(self, playlist_url: str, download_dir: str, audio_only: bool = False) -> None:
        """
        Download all videos from a YouTube playlist as video or audio files.

        Args:
            playlist_url (str): The URL of the YouTube playlist.
            download_dir (str): The directory to save the downloaded files.
            audio_only (bool): If True, download audio only. If False, download video.
        """
        
        playlist_obj = ptf.Playlist(playlist_url)
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        logger.debug(f"Found {len(playlist_obj.video_urls)} videos in the playlist.")

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        for i, video in enumerate(playlist_obj.videos): # types: int, ptf.YouTube
            logger.info(f'At {"soundtrack" if audio_only else "video"} {i + 1}/{len(playlist_obj.videos)}: ')
            self.download_single(download_dir=download_dir, audio_only=audio_only, video_obj=video)
            
        logger.info("Playlist download completed.")