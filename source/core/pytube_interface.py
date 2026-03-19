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

logger = get_logger(__name__, 'ytd_debug.log')

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

class StreamSelectionError(DownloadError):
    pass

class YouTubeDownloader:
    """
    Handles high-level download logic for YouTube videos and playlists using pytubefix.
    """
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
        
    def _get_video_obj(self, video_url: str) -> ptf.YouTube | Exception:
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
    def _get_playlist_obj(self, playlist_url: str) -> ptf.Playlist:
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

    def _select_stream(self, video: ptf.YouTube, str_type: Enum, options: DownloadOptions) -> ptf.Stream:
        """
            Select a pytubefix Stream for audio or video using preferences in DownloadOptions.
            Priority:
            - VIDEO: preferred_resolution > preferred_mime > preferred_video_quality (with FPS consideration) > best available
            - AUDIO: preferred_abr > preferred_audio_quality > best available
        Returns:
            ptf.Stream
        Raises:
            StreamSelectionError
        """
        try:
            if str_type == self.StreamType.AUDIO:
                q = video.streams.filter(type='audio')
                stream = None

                # 1) preferred_abr exact match
                if options and options.preferred_abr:
                    stream = q.filter(abr=options.preferred_abr).first()
                    logger.debug(f"[select] audio preferred abr={options.preferred_abr} -> {stream}")

                # 2) preferred_audio_quality via aliases (optionally constrained by mime)
                if not stream and options and options.preferred_audio_quality:
                    qual_key = QUALITY_ALIAS_MAP.get(options.preferred_audio_quality.strip().lower())
                    aq = q.filter(mime_type=options.preferred_mime) if options.preferred_mime else q
                    if qual_key == "high":
                        stream = aq.order_by('abr').desc().first()
                    elif qual_key == "low":
                        stream = aq.order_by('abr').asc().first()
                    elif qual_key == "medium":
                        candidates = list(aq.order_by('abr'))
                        if candidates:
                            idx = len(candidates) // 2  # upper-middle for even counts
                            stream = candidates[idx]
                    logger.debug(f"[select] audio quality={options.preferred_audio_quality} (mime={options.preferred_mime or 'any'}) -> {stream}")

                # 3) best available (highest abr)
                if not stream:
                    stream = q.order_by('abr').desc().first()
                    logger.debug(f"[select] audio fallback best abr -> {stream}")

                if not stream:
                    raise StreamSelectionError("No audio stream available")
                return stream

            else:
                # VIDEO
                q = video.streams.filter(type='video', progressive=False)
                stream = None

                # Helper to filter by FPS preference
                def apply_fps_filter(candidates_list, preferred_fps):
                    """Filter candidates by FPS preference: 0=any, 30=prefer 30fps, 60=prefer 60fps"""
                    if not candidates_list or preferred_fps == 0:
                        return candidates_list
                    # Extract fps from stream strings like "60fps" -> 60
                    result = []
                    for stream_obj in candidates_list:
                        try:
                            stream_fps = int(str(stream_obj.fps).rstrip('fps')) if stream_obj.fps else 0
                            if stream_fps == preferred_fps:
                                result.append(stream_obj)
                        except (ValueError, AttributeError):
                            pass
                    return result if result else candidates_list  # fallback to all if none match

                # 1) preferred_resolution (DASH first, then progressive)
                if options and options.preferred_resolution:
                    stream = q.filter(resolution=options.preferred_resolution).order_by('fps').desc().first() if options.preferred_fps == 60 else q.filter(resolution=options.preferred_resolution).order_by('fps').asc().first() if options.preferred_fps == 30 else q.filter(resolution=options.preferred_resolution).first()
                    logger.debug(f"[select] video preferred resolution={options.preferred_resolution} fps={options.preferred_fps or 'any'} (DASH) -> {stream}")
                    if not stream:
                        candidates = list(video.streams.filter(type='video', progressive=True, resolution=options.preferred_resolution).order_by('fps'))
                        candidates = apply_fps_filter(candidates, options.preferred_fps)
                        stream = candidates[-1] if candidates else None
                        logger.debug(f"[select] video preferred resolution={options.preferred_resolution} (progressive) -> {stream}")

                # 2) preferred_mime (best resolution within mime, considering FPS)
                if not stream and options and options.preferred_mime:
                    candidates = list(q.filter(mime_type=options.preferred_mime).order_by('resolution'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None  # highest resolution
                    logger.debug(f"[select] video preferred mime={options.preferred_mime} fps={options.preferred_fps or 'any'} (DASH) -> {stream}")
                    if not stream:
                        candidates = list(video.streams.filter(type='video', progressive=True, mime_type=options.preferred_mime).order_by('resolution'))
                        candidates = apply_fps_filter(candidates, options.preferred_fps)
                        stream = candidates[-1] if candidates else None
                        logger.debug(f"[select] video preferred mime={options.preferred_mime} (progressive) -> {stream}")

                # 3) preferred_video_quality via aliases (resolution + FPS consideration)
                if not stream and options and options.preferred_video_quality:
                    qual_key = QUALITY_ALIAS_MAP.get(options.preferred_video_quality.strip().lower())
                    candidates = list(q.order_by('resolution'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    
                    if qual_key == "high":
                        stream = candidates[-1] if candidates else None  # highest resolution
                    elif qual_key == "low":
                        stream = candidates[0] if candidates else None  # lowest resolution
                    elif qual_key == "medium":
                        if candidates:
                            idx = len(candidates) // 2  # middle resolution
                            stream = candidates[idx]
                    logger.debug(f"[select] video quality={options.preferred_video_quality} fps={options.preferred_fps or 'any'} -> {stream}")
            
                # 4) best available (highest resolution, considering FPS)
                if not stream:
                    candidates = list(q.order_by('resolution'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None  # highest resolution
                    logger.debug(f"[select] video fallback best resolution (DASH) fps={options.preferred_fps or 'any'} -> {stream}")
                    if not stream:
                        candidates = list(video.streams.filter(type='video').order_by('resolution'))
                        candidates = apply_fps_filter(candidates, options.preferred_fps)
                        stream = candidates[-1] if candidates else None

                return stream
        except Exception as e:
            raise StreamSelectionError(f"Stream selection failed: {e}") from e
    
    # TODO: Test and         
    def _download_stream_type(self, video: ptf.YouTube, download_dir: Path, options: DownloadOptions, base_filename: str, str_type: Enum) -> str | None:
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
                
            else:
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

    def download(self, url: str, download_dir: Path, options: DownloadOptions) -> List[DownloadResult]:
        """Download a YouTube video or playlist based on the provided URL and options.
        Args:
            url (str): The URL of the YouTube video or playlist to download.
            download_dir (Path): The directory where the downloaded files should be saved.
            options (DownloadOptions): The download options specifying preferences for audio/video quality, format, etc.
        Returns:
            List[DownloadResult]: List of download results for each video.
        Side Effects:
            - Downloads the specified video or playlist to the given directory.
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