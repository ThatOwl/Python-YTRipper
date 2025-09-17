import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
import ffmpeg as fpg
from source.logger import get_logger

from enum import Enum

logger = get_logger(__name__, 'pti_debug.log')


class PyTubeDownloader:
    """
    A class to handle downloading YouTube videos and playlists using pytubefix.
    Supports downloading single videos, playlists, audio streams, and displaying video info.
    """

    def __init__(self):
        """Initialize the PyTubeDownloader."""
        pass

    def _download_stream(self, video: ptf.YouTube, download_dir: str, audio_only: bool) -> None:
        if audio_only:
            stream = video.streams.filter(type='audio').order_by('abr').desc().first()
        else:
            stream = video.streams.filter(type='video').order_by('resolution').desc().first()
        if stream:
            logger.debug( f"Selected stream: {stream.resolution} and {stream.abr} and {stream.filesize_mb}" )
            stream.download(
                output_path=download_dir,
                skip_existing=True,
                timeout=5,
                max_retries=3
            )
        else :
            logger.debug("No suitable stream available for this video.")

    def single_video_info(self, video_url: str) -> None:
        """
        Print information about a single YouTube video.

        Args:
            video_url (str): The URL of the YouTube video.
        """
        video_obj = ptf.YouTube(video_url)
        print(f'Video title: {video_obj.title}')
        print(f'Video length: {video_obj.length} seconds')
        print(f'Video views: {video_obj.views}')
        print(f'Video author: {video_obj.author}')
        print(f'Video description: {video_obj.description[:200]}...')
        print(f"Thumbnail: {video_obj.thumbnail_url}")
        print("Available streams:")
        
        print("  Video:")
        for stream in video_obj.streams.filter(type='video').order_by('resolution').desc():
            print(f'- {stream.resolution}, {stream.mime_type}, {stream.fps}fps')

        print("  Audio:")
        for stream in video_obj.streams.filter(type='audio').order_by('abr').desc():
            print(f'- {stream.mime_type}, {stream.abr}')    
    
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
            logger.debug(f'Downloading {"audio" if audio_only else "video"} {i + 1}/{len(playlist_obj.videos)}: {video.title}')
            self._download_stream(video, download_dir, audio_only)
            
        logger.debug("Process completed.")

    def download_single(self, video_url: str, download_dir: str, audio_only: bool = False) -> None:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """

        video_obj = ptf.YouTube(video_url)
        logger.debug(f'Downloading {"audio" if audio_only else "video"}: {video_obj.title}')
        self._download_stream(video_obj, download_dir, audio_only)
        
        logger.debug("Process completed.")


class PyTubeDownloader2:
    """
    trying to get ffmpeg to combine video and audio streams"""

    def __init__(self):
        """Initialize the PyTubeDownloader."""
        pass

    def single_video_info(self, video_url: str) -> None:
        pass
    
    def download_single(self, video_url: str, download_dir: str, audio_only: bool = False) -> None:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """

        video_obj = ptf.YouTube(video_url)
        logger.debug(f'Downloading {"audio" if audio_only else "video"}: {video_obj.title}')
        self._download_stream(video_obj, download_dir, audio_only)
        logger.debug("Process completed.")

    def download_playlist(self, playlist_url: str, download_dir: str, audio_only: bool = False) -> None:
            pass


    #TODO split this method into _download_audio, _download_video methods and _combine_streams 
    # and call them from download_single and download_playlist methods 
    # (download_playlist method will loop over download_single)
    def _download_stream(self, video: ptf.YouTube, download_dir: str, audio_only: bool) -> None:
        if audio_only:
            # Download best audio only
            audio_stream = video.streams.filter(type='audio').order_by('abr').desc().first()
            
            base_filename = re.sub(r'[\\/*?:"<>|]', "", video.title)
            output_path = os.path.join(download_dir, f"{base_filename}.mp3")
            
            if audio_stream:
                logger.debug(f"Selected audio stream: {audio_stream.abr}, {audio_stream.mime_type}")
                downloaded_audio_path = audio_stream.download(
                    output_path=download_dir,
                    skip_existing=True,
                    timeout=5,
                    max_retries=3
                )
            else:
                logger.debug("No suitable audio stream available for this video.")
                return  # Exit early if no stream

            try:
                logger.debug("Converting audio to mp3 with ffmpeg...")
                if os.path.exists(downloaded_audio_path):
                    (
                        fpg
                        .input(downloaded_audio_path)
                        .output(output_path, acodec='mp3', strict='experimental')
                        .run(overwrite_output=True, quiet=True)
                    )
                    logger.info(f"Audio file saved to: {output_path}")
                    os.remove(downloaded_audio_path)
            except Exception as e:
                logger.exception(f"Error converting audio: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
                logger.info("Keeping original audio file.")

        else:
            # Download best video and best audio separately
            video_stream = video.streams.filter(type='video', progressive=False).order_by('resolution').desc().first()
            audio_stream = video.streams.filter(type='audio').order_by('abr').desc().first()

            if not video_stream or not audio_stream:
                logger.debug("No suitable video or audio stream available for this video.")
                return

            logger.debug(f"Selected video stream: {video_stream.resolution}, {video_stream.mime_type}")
            logger.debug(f"Selected audio stream: {audio_stream.abr}, {audio_stream.mime_type}")

            # Prepare file paths
            base_filename = re.sub(r'[\\/*?:"<>|]', "", video.title)
            video_path = os.path.join(download_dir, f"{base_filename}_video.{video_stream.subtype}")
            audio_path = os.path.join(download_dir, f"{base_filename}_audio.{audio_stream.subtype}")
            output_path = os.path.join(download_dir, f"{base_filename}.mp4")

            # Download streams
            video_stream.download(
                output_path=download_dir,
                filename=f"{base_filename}_video.{video_stream.subtype}",
                skip_existing=True,
                timeout=5,
                max_retries=3
            )
            audio_stream.download(
                output_path=download_dir,
                filename=f"{base_filename}_audio.{audio_stream.subtype}",
                skip_existing=True,
                timeout=5,
                max_retries=3
            )

            # Combine using ffmpeg
            logger.debug("Combining video and audio with ffmpeg...")
            try:
                video_input = fpg.input(video_path)
                audio_input = fpg.input(audio_path)
                (
                    fpg
                    .output(video_input, audio_input, output_path, vcodec='copy', acodec='aac', strict='experimental')
                    .run(overwrite_output=True, quiet=True)
                )
                logger.info(f"Merged file saved to: {output_path}")
                os.remove(video_path)
                os.remove(audio_path)
            except Exception as e:
                logger.exception(f"Error combining video and audio: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
                logger.info("Keeping separate video and audio files.")


class PyTubeDownloader_partial:
    # Split _download_stream into _download_audio, _download_video, and _combine_streams methods.
    # _download_audio and _download_video handle downloading and naming files with correct extensions.
    # _combine_streams handles conversion (audio to mp3) or merging (video+audio to mp4), and deletes source files if successful.
    # download_single and download_playlist should pass base_filename and use these helpers.

    def _sanitize_filename(self, title: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", title)

    def _download_audio(self, video: ptf.YouTube, download_dir: str, base_filename: str) -> str:
        audio_stream = video.streams.filter(type='audio').order_by('abr').desc().first()
        if not audio_stream:
            logger.debug("No suitable audio stream available for this video.")
            return ""
        ext = audio_stream.subtype
        audio_path = os.path.join(download_dir, f"{base_filename}_audio.{ext}")
        logger.debug(f"Selected audio stream: {audio_stream.abr}, {audio_stream.mime_type}")
        downloaded_audio_path = audio_stream.download(
            output_path=download_dir,
            filename=f"{base_filename}_audio.{ext}",
            skip_existing=True,
            timeout=5,
            max_retries=3
        )
        return downloaded_audio_path

    def _download_video(self, video: ptf.YouTube, download_dir: str, base_filename: str) -> str:
        video_stream = video.streams.filter(type='video', progressive=False).order_by('resolution').desc().first()
        if not video_stream:
            logger.debug("No suitable video stream available for this video.")
            return ""
        ext = video_stream.subtype
        video_path = os.path.join(download_dir, f"{base_filename}_video.{ext}")
        logger.debug(f"Selected video stream: {video_stream.resolution}, {video_stream.mime_type}")
        downloaded_video_path = video_stream.download(
            output_path=download_dir,
            filename=f"{base_filename}_video.{ext}",
            skip_existing=True,
            timeout=5,
            max_retries=3
        )
        return downloaded_video_path

    def _combine_streams(self, audio_path: str, video_path: str, output_path: str, audio_only: bool) -> None:
        try:
            if audio_only:
                # Convert audio to mp3
                logger.debug("Converting audio to mp3 with ffmpeg...")
                (
                    fpg
                    .input(audio_path)
                    .output(output_path, acodec='mp3', strict='experimental')
                    .run(overwrite_output=True, quiet=True)
                )
                logger.info(f"Audio file saved to: {output_path}")
                os.remove(audio_path)
            else:
                # Merge video and audio to mp4
                logger.debug("Combining video and audio with ffmpeg...")
                (
                    fpg
                    .output(fpg.input(video_path), fpg.input(audio_path), output_path, vcodec='copy', acodec='aac', strict='experimental')
                    .run(overwrite_output=True, quiet=True)
                )
                logger.info(f"Merged file saved to: {output_path}")
                os.remove(video_path)
                os.remove(audio_path)
        except Exception as e:
            logger.exception(f"Error during ffmpeg processing: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original files.")

    def download_single(self, video_url: str, download_dir: str, audio_only: bool = False) -> None:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """
        video_obj = ptf.YouTube(video_url)
        base_filename = self._sanitize_filename(video_obj.title)
        logger.debug(f'Downloading {"audio" if audio_only else "video"}: {video_obj.title}')
        if audio_only:
            audio_path = self._download_audio(video_obj, download_dir, base_filename)
            output_path = os.path.join(download_dir, f"{base_filename}.mp3")
            if audio_path:
                self._combine_streams(audio_path, None, output_path, audio_only=True)
        else:
            video_path = self._download_video(video_obj, download_dir, base_filename)
            audio_path = self._download_audio(video_obj, download_dir, base_filename)
            output_path = os.path.join(download_dir, f"{base_filename}.mp4")
            if video_path and audio_path:
                self._combine_streams(audio_path, video_path, output_path, audio_only=False)
        logger.debug("Process completed.")
