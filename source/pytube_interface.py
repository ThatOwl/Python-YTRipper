import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
import ffmpeg as fpg
from source.logger import get_logger
from enum import Enum
import requests
import source.url_handler as uh

logger = get_logger(__name__, 'pti_v2_debug.log')

class ThumbnailHandler:
    """Handles downloading and saving YouTube video thumbnails."""
    @staticmethod
    def download_thumbnail(video: ptf.YouTube, download_dir: str, base_filename: str) -> str:
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

class StreamConverter:
    """Handles conversion and merging of audio/video streams."""
    @staticmethod
    def convert_to_m4a(audio_path: str, output_path: str, thumbnail_path: str = None) -> None:
        logger.debug("Converting audio to m4a with ffmpeg...")
        try:
            if thumbnail_path and os.path.exists(thumbnail_path):
                (
                    fpg
                    .input(audio_path)
                    .output(
                        output_path,
                        acodec='m4a',
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

    @staticmethod
    def convert_to_mp3(audio_path: str, output_path: str) -> None:
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

    @staticmethod
    def combine_streams(audio_path: str, video_path: str, output_path: str) -> None:
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

class YouTubeDownloader:
    """
    Handles high-level download logic for YouTube videos and playlists using pytubefix.
    """
    urlh = uh.URLHandler()
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
        playlist_obj = ptf.Playlist(playlist_url)
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        logger.debug(f"Found {len(playlist_obj.video_urls)} videos in the playlist. {playlist_obj.title}")

        for i, video in enumerate(playlist_obj.videos):
            logger.info(f'At {"soundtrack" if audio_only else "video"} {i + 1}/{len(playlist_obj.videos)}: ')
            self._download_single(download_dir=download_dir, audio_only=audio_only, video_obj=video)

        logger.info("Playlist download completed.")

    def single_video_info(self, video_url: str = None, video_obj: ptf.YouTube = None) -> None:
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
        if self.urlh.is_youtube_url(url):
            logger.debug(f"Valid YouTube URL: {url}")

            if not os.path.exists(download_dir):
                os.mkdir(download_dir)
                logger.debug(f"Created download directory: {download_dir}")

            if self.urlh.is_youtube_playlist(url):
                logger.debug("Detected as a playlist URL.")
                self._download_playlist(playlist_url=url, download_dir=download_dir, audio_only=audio_only)
            else:
                logger.debug("Detected as a single video URL.")
                self._download_single(video_url=url, download_dir=download_dir, audio_only=audio_only)