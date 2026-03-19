


#TODO: reduce includes after renaming / moving methods is done
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
from core.pytube_interface import PytubeInterface

#TODO: implement proper logging so user does not get unwanted outputs
#TODO: Handle exceptions properly (incl. at interfaces not above)
#TODO: make classes testable (mockable and unittestable if possible)
logger = get_logger(__name__, 'orchestration_debug.log')


class Orchestration:
    """docstring for orchestration."""
    def __init__(self, 
                 os_handler: OSInteractions = None, 
                 thumbnail_handler: ThumbnailHandler = None,
                 stream_converter: StreamConverter = None, 
                 url_handler: URLHandler = None,
                 pyt_interface: PytubeInterface = None):
        
        self.os_handler = os_handler or OSInteractions()
        self.thumbnail_handler = thumbnail_handler or ThumbnailHandler()
        self.stream_converter = stream_converter or StreamConverter()
        self.urlh = url_handler or URLHandler()
        self.pyt_interface = pyt_interface or PytubeInterface()

    def download_single_video(self, video_obj: ptf.YouTube, download_dir: Path, options: DownloadOptions) -> DownloadResult:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video to download.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """        
        try:
            video_path_str = self._download_stream_type(video_obj, download_dir, options, base_filename, self.StreamType.VIDEO)
            audio_path_str = self._download_stream_type(video_obj, download_dir, options, base_filename, self.StreamType.AUDIO)
            output_path = Path(download_dir) / f"{base_filename}.mp4"

            if not video_path_str or not audio_path_str:
                msg = "missing audio or video stream"
                logger.error(f"✗ {video_title}: {msg}")
                return DownloadResult(success=False, errors=[msg], video_title=video_title, video_url=video_url)
            video_path = Path(video_path_str)
            audio_path = Path(audio_path_str)

            if not options.donotconvert:
                self.stream_converter.combine_streams(audio_path, video_path, output_path)

        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"✗ {video_title}: {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url)
        except Exception as e:
            logger.error(f"✗ {video_title}: Unexpected error - {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url)

    def download_single_audio(self, video_obj: ptf.YouTube, download_dir: Path, options: DownloadOptions) -> DownloadResult:
        """
        Download a single YouTube video's audio stream.

        Args:
            ...
        """

        try:
            audio_path_str = self._download_stream_type(video_obj, download_dir, options, base_filename, self.StreamType.AUDIO)
            thumbnail_path = None #FIXME self.thumbnail_handler.download_thumbnail(video_obj, download_dir, base_filename)
            output_path = Path(download_dir) / f"{base_filename}{'.mp3' if options.audio_mp3 else '.m4a'}"
            
            if not audio_path_str:
                msg = "no audio stream available"
                logger.error(f"✗ {video_title}: {msg}")
                return DownloadResult(success=False, errors=[msg], video_title=video_title, video_url=video_url)
            audio_path = Path(audio_path_str)
            
            if not options.donotconvert:
                self.stream_converter.convert_audio(
                    audio_path, output_path,
                    thumbnail_path=thumbnail_path,
                    audio_bitrate=options.actual_audio_bitrate,
                    audio_mp3=options.audio_mp3,
                )
        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"✗ {video_title}: {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url)
        except Exception as e:
            logger.error(f"✗ {video_title}: Unexpected error - {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url)
    
    def download_single(self, download_dir: Path, options: DownloadOptions, video_obj: ptf.YouTube) -> DownloadResult:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_obj (ptf.YouTube): The YouTube video object to download.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """        
        base_filename: str = self._sanitize_filename(video_obj.title)
        video_title = video_obj.title
        video_url = video_obj.watch_url

        # Efficiency safeguard: skip download if target file already exists
        if options.audio_only:
            ext = '.mp3' if options.audio_mp3 else '.m4a'
        else:
            ext = '.mp4'
        target_file = Path(download_dir) / f"{base_filename}{ext}"
        if target_file.exists():
            logger.info(f'⏭ Skipping (already exists): {video_title} -> {target_file.name}')
            return DownloadResult(success=True, errors=[], video_title=video_title, video_url=video_url)
        
        logger.info(f'Downloading {"soundtrack" if options.audio_only else "video"}: {video_title}')
        
        try:
            if options.audio_only:
                self.download_single_audio(video_obj, download_dir, options)
            else:
                self.download_single_video(video_obj, download_dir, options)

            logger.info(f'✓ {video_title}')
            return DownloadResult(success=True, errors=[], video_title=video_title, video_url=video_url)
        
        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"✗ {video_title}: {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url)
        except Exception as e:
            logger.error(f"✗ {video_title}: Unexpected error - {e}")
            return DownloadResult(success=False, errors=[str(e)], video_title=video_title, video_url=video_url)

    # TODO improve error handling (return exceptions or ...?)
    def download_playlist(self, playlist_url: str, download_dir: Path, options: DownloadOptions) -> List[DownloadResult]:
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
        
        if not options.no_dir_date:
            date = datetime.today().strftime('%Y_%m_')
        else:
            date = ""
        
        results: List[DownloadResult] = []
        try:
            playlist_obj = self._get_playlist_obj(playlist_url)
        except Exception as e:
            logger.error(f"Failed to fetch playlist object: {e}")
            return [] #TODO could raise error upstream
        
        # Override pytube's video URL regex to capture all videos in the playlist
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        logger.debug(f"Found {len(playlist_obj.video_urls)} videos in the playlist. {playlist_obj.title}")
        
        # Build a Path for the playlist directory and ensure it exists
        playlist_dir = Path(download_dir) / f"{date}{self._sanitize_filename(playlist_obj.title)}"

        # create new directory for each playlists -> easier for user
        try:
            if not playlist_dir.exists(): #if user retries existing dir, skip creation
                logger.info(f"Creating playlist download directory: {playlist_dir}")
                playlist_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create playlist directory {playlist_dir}: {e}")
            return results

        for i, video in enumerate(playlist_obj.videos):
            logger.info(f'[{i + 1}/{len(playlist_obj.videos)}] Processing: {video.title}')
            #TODO: add urlh.clean_video_link if needed
            result = self.download_single(download_dir=playlist_dir, options=options, video_obj=video)
            results.append(result)

        # Log summary
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count
        logger.info(f"Playlist download completed: {success_count} succeeded, {fail_count} failed")
        
        if fail_count > 0:
            logger.warning("Failed downloads:")
            for result in results:
                if not result.success:
                    logger.warning(f"  ✗ {result.video_title}: {'; '.join(result.errors)}")
        
        return results


    def info(self, url: str = None, video_obj: ptf.YouTube = None, output: callable = logger.info) -> None:
        """
        Print to console or log information about video or playlist.

        Args:
        url (str): The URL of the YouTube video or playlist.
        video_obj (ptf.YouTube, optional): A YouTube video object. Defaults to None.
        output (callable, optional): A callable that takes a string, e.g. `print` or `logger.info`.
            Defaults to `logger.info`.
        """
        #DELETEME
        #output = output or logger.info
        
        if self.urlh.is_youtube_playlist(url):
            try:
                playlist_obj = self._get_playlist_obj(url)
            except Exception as e:
                logger.error(f"Failed to fetch playlist object: {e}")
                return
        
            output(f"Playlist Title: {playlist_obj.title}")
            output(f"Number of Videos: {len(playlist_obj.videos)}")
            output("Videos:")
            for i, video in enumerate(playlist_obj.videos):
                output(f"{i + 1}. {video.title} ({video.length} seconds)")
        else:
            try:
                if video_obj is None:
                    video_obj = self._get_video_obj(url)
            except Exception as e:
                logger.error(f"Failed to fetch video object: {e}")
                return

            output(f"Video title: {video_obj.title}")
            output(f"Video length: {video_obj.length} seconds")
            output(f"Video views: {video_obj.views}")
            output(f"Video author: {video_obj.author}")
            output(f"Video description: {video_obj.description[:200]}...")
            output(f"Thumbnail: {video_obj.thumbnail_url}")

            output("Available streams:")
            output("  Video:")
            for stream in video_obj.streams.filter(type='video').order_by('resolution').desc():
                output(f"- {stream.resolution}, {stream.mime_type}, {stream.fps}fps")
            output(f"Best video: {video_obj.streams.filter(type='video').order_by('resolution').desc().first()}")
            
            output("  Audio:")
            for stream in video_obj.streams.filter(type='audio').order_by('abr').desc():
                output(f"- {stream.mime_type}, {stream.abr}")
            output(f"Best audio: {video_obj.streams.filter(type='audio').order_by('abr').desc().first()}")


    #TODO: Will be interface with CLI and GUI, so should be more generic 
    def process(self, url: str, download_dir: Path, options: DownloadOptions) -> List[DownloadResult]:
        """Process a YouTube video or playlist based on the provided URL and options.
        Args:
            url (str): The URL of the YouTube video or playlist to process.
            download_dir (Path): The directory where the processed files should be saved.
            options (DownloadOptions): The processing options specifying preferences for audio/video quality, format, etc.
        Returns:
            List[DownloadResult]: List of processing results for each video.
        Side Effects:
            - Processes the specified video or playlist to the given directory.
        Logs:
            - Download status and any errors encountered during the process.
        """
        results = []

        if self.urlh.is_youtube_url(url) and self.urlh.is_accessible(url):
            logger.debug(f"Valid YouTube URL: {url}")
            try:
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir)
                    logger.info(f"Created download directory: {download_dir}")

                # NEW: if start_radio mix, force single-video download with cleaned URL
                if self.urlh.has_start_radio(url):
                    cleaned = self.urlh.clean_video_link(url)
                    if not cleaned:
                        raise ValueError("Could not extract video id from start_radio URL")
                    logger.info(f"start_radio detected; treating as single video: {cleaned}")
                    url = cleaned

                if self.urlh.is_youtube_playlist(url):
                    logger.debug("Detected as a playlist URL.")
                    results = self.download_playlist(playlist_url=url, download_dir=download_dir, options=options)
                else:
                    logger.debug("Detected as a single video URL.")
                    url = self.urlh.clean_video_link(url) or url  # Clean the URL if possible, fallback to original
                    video = self._get_video_obj(url)
                    results.append(self.download_single(video_obj=video, download_dir=download_dir, options=options))

            except Exception as e:
                logger.error(f"Download failed: {e}")
                return results
        else:
            logger.error("The provided URL is not a valid YouTube URL or inaccessible.")
            raise ValueError("The provided URL is not valid or unreachable.")
        
        return results