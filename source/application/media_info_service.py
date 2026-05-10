
import pytubefix as ptf

from domain.video_fetcher import VideoFetcher
from infrastructure.url_handler import URLHandler
from utility.logger import get_logger

logger = get_logger(__name__, "media_info_service_debug.log")

class MediaInfoService:
    def __init__(self, url_handler: URLHandler = None, video_fetcher: VideoFetcher = None):
        self.urlh = url_handler or URLHandler()
        self.vid_fetcher = video_fetcher or VideoFetcher()

    def get_info_lines(self, url: str) -> list[str]:
        if self.urlh.is_youtube_playlist(url):
            return self._playlist_info_lines(url)
        return self._video_info_lines(url)

    def _playlist_info_lines(self, url: str) -> list[str]:
        playlist: ptf.Playlist = self.vid_fetcher.get_playlist_obj(url)
        lines = [
            f"Playlist Title: {playlist.title}",
            f"Number of Videos: {len(playlist.videos)}",
            "Videos:",
        ]
        for i, video in enumerate(playlist.videos):
            lines.append(f"{i + 1}. {video.title} ({video.length} seconds)")
        return lines

    def _video_info_lines(self, url: str) -> list[str]:
        video: ptf.YouTube = self.vid_fetcher.get_video_obj(url)

        lines = [
            f"Video title: {video.title}",
            f"Video length: {video.length} seconds",
            f"Video views: {video.views}",
            f"Video author: {video.author}",
            f"Video description: {video.description[:200]}...",
            f"Thumbnail: {video.thumbnail_url}",
            "Available streams:",
            "  Video:",
        ]

        for stream in video.streams.filter(type="video").order_by("resolution").desc():
            lines.append(f"- {stream.resolution}, {stream.mime_type}, {stream.fps}fps")

        lines.append(f"Best video: {video.streams.filter(type='video').order_by('resolution').desc().first()}")
        lines.append("  Audio:")

        for stream in video.streams.filter(type="audio").order_by("abr").desc():
            lines.append(f"- {stream.mime_type}, {stream.abr}")

        lines.append(f"Best audio: {video.streams.filter(type='audio').order_by('abr').desc().first()}")

        return lines
    
    #TODO ? just a wrapper around video_fetcher methods ?
    def is_playlist(self, url: str) -> bool:
        return self.urlh.is_youtube_playlist(url)
    
    def get_video_title(self, url: str) -> str:
        video: ptf.YouTube = self.vid_fetcher.get_video_obj(url)
        return video.title
    
    def get_playlist_title(self, url: str) -> str:
        playlist: ptf.Playlist = self.vid_fetcher.get_playlist_obj(url)
        return playlist.title
    
    def get_playlist_video_titles(self, url: str) -> list[str]:
        playlist: ptf.Playlist = self.vid_fetcher.get_playlist_obj(url)
        return [video.title for video in playlist.videos]
    
    def get_playlist_video_urls(self, url: str) -> list[str]:
        playlist: ptf.Playlist = self.vid_fetcher.get_playlist_obj(url)
        return [video.watch_url for video in playlist.videos]
    
    def get_video_length_seconds(self, url: str) -> int:
        video: ptf.YouTube = self.vid_fetcher.get_video_obj(url)
        return video.length
    
    def get_video_length_formatted(self, url: str) -> str:
        video: ptf.YouTube = self.vid_fetcher.get_video_obj(url)
        minutes: int
        seconds: int
        minutes, seconds = divmod(video.length, 60)
        return f"{minutes}:{seconds:02d}"
    
    def get_video_size_mb(self, url: str) -> float:
        video: ptf.YouTube = self.vid_fetcher.get_video_obj(url)
        best_video_stream: ptf.Stream = video.streams.filter(type="video").order_by("resolution").desc().first()
        best_audio_stream: ptf.Stream = video.streams.filter(type="audio").order_by("abr").desc().first()
        total_size_bytes = best_video_stream.filesize + best_audio_stream.filesize
        return total_size_bytes / (1024 * 1024)