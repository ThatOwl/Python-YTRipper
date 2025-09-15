import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
import ffmpeg as fpg

#TODO: Add logging instead of print statements
# Add error handling for network issues, invalid URLs, etc.
# Add progress bar for downloads
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
# write a method based on "yt.streams.all()" to warn user if some formats 
# are not available for a video in a playlist 
#   and skip those formats (?)
# or download the next best format available 


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
            print( f"Selected stream: {stream.resolution} and {stream.abr} and {stream.filesize_mb}" )
            stream.download(
                output_path=download_dir,
                skip_existing=True,
                timeout=5,
                max_retries=3
            )
        else :
            print("No suitable stream available for this video.")

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
        print(f"Found {len(playlist_obj.video_urls)} videos in the playlist.")

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        for i, video in enumerate(playlist_obj.videos):
            print(f'Downloading {"audio" if audio_only else "video"} {i + 1}/{len(playlist_obj.videos)}: {video.title}')
            self._download_stream(video, download_dir, audio_only)
            
        print("Process completed.")

    def download_single(self, video_url: str, download_dir: str, audio_only: bool = False) -> None:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """

        video_obj = ptf.YouTube(video_url)
        print(f'Downloading {"audio" if audio_only else "video"}: {video_obj.title}')
        self._download_stream(video_obj, download_dir, audio_only)
        
        print("Process completed.")


class PyTubeDownloader2:
    """
    trying to get ffmpeg to combine video and audio streams"""

    def __init__(self):
        """Initialize the PyTubeDownloader."""
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
        print(f'Downloading {"audio" if audio_only else "video"}: {video_obj.title}')
        self._download_stream(video_obj, download_dir, audio_only)
        
        print("Process completed.")

    def _download_stream(self, video: ptf.YouTube, download_dir: str, audio_only: bool) -> None:
        if audio_only:
            # Download best audio only
            audio_stream = video.streams.filter(type='audio').order_by('abr').desc().first()
            if audio_stream:
                print(f"Selected audio stream: {audio_stream.abr}, {audio_stream.mime_type}")
                audio_stream.download(
                    output_path=download_dir,
                    skip_existing=True,
                    timeout=5,
                    max_retries=3
                )
            else:
                print("No suitable audio stream available for this video.")
        else:
            # Download best video and best audio separately
            video_stream = video.streams.filter(type='video', progressive=False).order_by('resolution').desc().first()
            audio_stream = video.streams.filter(type='audio').order_by('abr').desc().first()

            if not video_stream or not audio_stream:
                print("No suitable video or audio stream available for this video.")
                return

            print(f"Selected video stream: {video_stream.resolution}, {video_stream.mime_type}")
            print(f"Selected audio stream: {audio_stream.abr}, {audio_stream.mime_type}")

            # Prepare file paths
            base_filename = re.sub(r'[\\/*?:"<>|]', "", video.title)
            video_path = os.path.join(download_dir, f"{base_filename}_video.{video_stream.subtype}")
            audio_path = os.path.join(download_dir, f"{base_filename}_audio.{audio_stream.subtype}")
            output_path = os.path.join(download_dir, f"{base_filename}_merged.mp4")

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
            print("Combining video and audio with ffmpeg...")
            try:
                (
                    fpg
                    .input(video_path)
                    .output(audio_path)
                    .output(output_path, vcodec='copy', acodec='aac', strict='experimental')
                    .run(overwrite_output=True, quiet=True)
                )
                print(f"Merged file saved to: {output_path}")
                # Optionally, remove the separate files
                os.remove(video_path)
                os.remove(audio_path)
            except Exception as e:
                print(f"Error combining video and audio: {e}")