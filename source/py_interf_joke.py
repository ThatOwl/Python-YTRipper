import pytubefix as ptf
import os
import re
from enum import Enum
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import List

from source.stream_converter import StreamConverter
from source.url_handler import URLHandler


@dataclass
class DownloadOptions:
    audio_only: bool = False
    preferred_quality: str = ""
    preferred_abr: str = ""
    preferred_resolution: str = ""


@dataclass
class DownloadResult:
    success: bool
    errors: List[str]


class ThumbnailHandler:
    @staticmethod
    def download_thumbnail(video: ptf.YouTube, download_dir: str, base_filename: str) -> str:
        thumbnail_url = video.thumbnail_url
        response = requests.get(thumbnail_url)
        if response.status_code == 200:
            ext = thumbnail_url.split('.')[-1].split('?')[0]
            thumbnail_path = os.path.join(download_dir, f"{base_filename}_thumbnail.{ext}")
            with open(thumbnail_path, 'wb') as f:
                f.write(response.content)
            return thumbnail_path
        return ""


class YouTubeDownloader:
    class StreamType(Enum):
        AUDIO = 1
        VIDEO = 0

    stream_type_map = {
        StreamType.AUDIO: 'Audio',
        StreamType.VIDEO: 'Video'
    }

    def __init__(self):
        self.thumbnail_handler = ThumbnailHandler()
        self.stream_converter = StreamConverter()
        self.urlh = URLHandler()

    def _get_video_obj(self, video_url: str) -> ptf.YouTube:
        return ptf.YouTube(video_url)

    def _get_playlist_obj(self, playlist_url: str) -> ptf.Playlist:
        return ptf.Playlist(playlist_url)

    def _sanitize_filename(self, title: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", title)

    def _download_stream_type(self, video: ptf.YouTube, download_dir: str, base_filename: str, type: Enum) -> str:
        if type == self.StreamType.AUDIO:
            stream = video.streams.filter(type='audio').order_by('abr').desc().first()
        else:
            stream = video.streams.filter(type='video', progressive=False).order_by('resolution').desc().first()

        if not stream:
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

    def download_single(self, download_dir: str, options: DownloadOptions, video_url: str = None, video_obj: ptf.YouTube = None) -> DownloadResult:
        if video_obj is None:
            video_obj = self._get_video_obj(video_url)

        base_filename = self._sanitize_filename(video_obj.title)

        if options.audio_only:
            audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
            thumbnail_path = None
            output_path = os.path.join(download_dir, f"{base_filename}.mp3")
            if not audio_path:
                return DownloadResult(False, errors=["no audio stream available"])
            self.stream_converter.convert_to_m4a(audio_path, output_path, thumbnail_path)
        else:
            video_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.VIDEO)
            audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
            output_path = os.path.join(download_dir, f"{base_filename}.mp4")
            if not video_path or not audio_path:
                return DownloadResult(False, errors=["missing audio or video stream"])
            self.stream_converter.combine_streams(audio_path, video_path, output_path)

        return DownloadResult(success=True, errors=[])

    def download_playlist(self, playlist_url: str, download_dir: str, options: DownloadOptions) -> None:
        playlist_obj = self._get_playlist_obj(playlist_url)
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        date = datetime.today().strftime('%Y_%m_')
        playlist_dir = os.path.join(download_dir, date + playlist_obj.title)
        if not os.path.exists(playlist_dir):
            os.mkdir(playlist_dir)

        for i, video in enumerate(playlist_obj.videos):
            self.download_single(download_dir=playlist_dir, options=options, video_obj=video)

    def info(self, url: str = None, video_obj: ptf.YouTube = None) -> None:
        if self.urlh.is_youtube_playlist(url):
            playlist_obj = self._get_playlist_obj(url)
            print(f"Playlist Title: {playlist_obj.title}")
            print(f"Number of Videos: {len(playlist_obj.videos)}")
            for i, video in enumerate(playlist_obj.videos):
                print(f"{i + 1}. {video.title} ({video.length} seconds)")
            return

        if video_obj is None:
            video_obj = self._get_video_obj(url)

        print(f'Video title: {video_obj.title}')
        print(f'Video length: {video_obj.length} seconds')
        print(f'Video views: {video_obj.views}')
        print(f'Video author: {video_obj.author}')
        print(f'Video description: {video_obj.description[:200]}...')
        print(f"Thumbnail: {video_obj.thumbnail_url}")

        print("Available video streams:")
        for stream in video_obj.streams.filter(type='video').order_by('resolution').desc():
            print(f'- {stream.resolution}, {stream.mime_type}, {stream.fps}fps')
        print("Available audio streams:")
        for stream in video_obj.streams.filter(type='audio').order_by('abr').desc():
            print(f'- {stream.mime_type}, {stream.abr}')

    def download(self, url: str, download_dir: str, options: DownloadOptions) -> None:
        failed = False
        failed_list = []

        if self.urlh.is_youtube_url(url) and self.urlh.is_accessible(url):
            if not os.path.exists(download_dir):
                os.mkdir(download_dir)

            if self.urlh.is_youtube_playlist(url):
                self.download_playlist(playlist_url=url, download_dir=download_dir, options=options)
            else:
                self.download_single(video_url=url, download_dir=download_dir, options=options)
        else:
            raise ValueError("The provided URL is not valid or unreachable.")

        if failed:
            for fail in failed_list:
                print(f"- {fail}")
