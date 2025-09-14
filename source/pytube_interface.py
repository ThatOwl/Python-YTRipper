import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re


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

    def _get_video_obj(self, video_url: str) -> ptf.YouTube:
        """
        Get a pytubefix.YouTube object for the given video URL.

        Args:
            video_url (str): The URL of the YouTube video.

        Returns:
            pytubefix.YouTube: The YouTube video object.
        """
        return ptf.YouTube(video_url)

    def _download_stream(self, stream: ptf.Stream, download_dir: str) -> None:
        """
        Download a given stream to the specified directory.

        Args:
            stream (pytubefix.Stream): The stream to download.
            download_dir (str): The directory to save the downloaded file.
        """
        stream.download(
            output_path=download_dir,
            skip_existing=True,
            timeout=5,
            max_retries=3
        )

    def download_videos_from_playlist(self, playlist_url: str, download_dir: str) -> None:
        """
        Download all videos from a YouTube playlist as video files.

        Args:
            playlist_url (str): The URL of the YouTube playlist.
            download_dir (str): The directory to save the downloaded videos.
        """
        playlist_obj = ptf.Playlist(playlist_url)
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        print(f"Found {len(playlist_obj.video_urls)} videos in the playlist.")

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        for i, video in enumerate(playlist_obj.videos):
            print(f'Downloading video {i + 1}/{len(playlist_obj.videos)}: {video.title}')
            stream = video.streams.filter(type='video', progressive=True, file_extension='mp4') \
                                  .order_by('resolution').desc().first()
            if stream:
                self._download_stream(stream, download_dir)
        print("Download completed.")

    def download_playlist_as_audio(self, playlist_url: str, download_dir: str) -> None:
        """
        Download all videos from a YouTube playlist as audio files.

        Args:
            playlist_url (str): The URL of the YouTube playlist.
            download_dir (str): The directory to save the downloaded audio files.
        """
        playlist_obj = ptf.Playlist(playlist_url)
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        print(f"Found {len(playlist_obj.video_urls)} videos in the playlist.")

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        for i, video in enumerate(playlist_obj.videos):
            print(f'Downloading audio {i + 1}/{len(playlist_obj.videos)}: {video.title}')
            stream = video.streams.filter(only_audio=True, file_extension='mp4') \
                                  .order_by('abr').desc().first()
            if stream:
                self._download_stream(stream, download_dir)
        print("Audio download completed.")

    def single_video_info(self, video_url: str) -> None:
        """
        Print information about a single YouTube video.

        Args:
            video_url (str): The URL of the YouTube video.
        """
        video_obj = self._get_video_obj(video_url)
        print(f'Video title: {video_obj.title}')
        print(f'Video length: {video_obj.length} seconds')
        print(f'Video views: {video_obj.views}')
        print(f'Video author: {video_obj.author}')
        print(f'Video description: {video_obj.description[:100]}...')
        print("Available streams:")
        
        print(video_obj.streams.all())
        
        for stream in video_obj.streams.filter(type='video', progressive=True, file_extension='mp4') \
                                       .order_by('resolution').desc():
            print(f'- {stream.resolution}, {stream.mime_type}, {stream.fps}fps')

    def download_single_video(self, video_url: str, download_dir: str) -> None:
        """
        Download a single YouTube video as a video file.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded video.
        """
        video_obj = self._get_video_obj(video_url)
        print(f'Downloading video: {video_obj.title}')
        stream = video_obj.streams.filter(type='video', progressive=True, file_extension='mp4') \
                                 .order_by('resolution').desc().first()
        if stream:
            self._download_stream(stream, download_dir)
        print("Download completed.")
        
    def download_single_audio(self, video_url: str, download_dir: str) -> None:
        """
        Download the audio stream of a single YouTube video.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded audio file.
        """
        video_obj = self._get_video_obj(video_url)
        print(f'Downloading audio for video: {video_obj.title}')
        stream = video_obj.streams.filter(only_audio=True, file_extension='mp3') \
                                 .order_by('abr').desc().first()
        if stream:
            self._download_stream(stream, download_dir)
        print("Audio download completed.")
