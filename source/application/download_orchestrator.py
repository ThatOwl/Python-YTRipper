from pathlib import Path
from typing import List
import re
import uuid

import pytubefix as ptf

from utility.logger import get_logger
from utility.utils import (
    PlaylistFetchError,
    StreamDownloadError,
    StreamSelectionError,
    ConversionError,
    CombineError,
    DownloadOptions,
    DownloadResult,
    StreamInfo,
    sanitize_filename,
)
from autotagging.runtime_tagging.package_builder import TaggingPackageBuilder, TaggingQueueStore
from infrastructure.media_assembler import MediaAssembler
from infrastructure.stream_converter import StreamConverter
from infrastructure.url_handler import URLHandler
from infrastructure.os_interactions import OSInteractions
from infrastructure.thumbnail_handler import ThumbnailHandler
from domain.stream_downloader import StreamDownloadService
from domain.stream_selector import StreamSelector
from domain.video_fetcher import VideoFetcher

logger = get_logger(__name__, "download_orchestrator_debug.log")


class DownloadOrchestrator:
    """Coordinates fetching, selecting, downloading and final media assembly."""

    def __init__(
        self,
        os_handler: OSInteractions | None = None,
        thumbnail_handler: ThumbnailHandler | None = None,
        media_assembler: MediaAssembler | None = None,
        stream_converter: StreamConverter | None = None,
        url_handler: URLHandler | None = None,
        vid_fetcher: VideoFetcher | None = None,
        stream_selector: StreamSelector | None = None,
        stream_download: StreamDownloadService | None = None,
        tagging_package_builder: TaggingPackageBuilder | None = None,
        tagging_queue_store: TaggingQueueStore | None = None,
    ):
        self.os_handler = os_handler or OSInteractions()
        self.thumbnail_handler = thumbnail_handler or ThumbnailHandler()
        self.media_assembler = media_assembler or MediaAssembler(stream_converter=stream_converter)
        self.urlh = url_handler or URLHandler()
        self.vid_fetcher = vid_fetcher or VideoFetcher()
        self.stream_selector = stream_selector or StreamSelector()
        self.stream_download = stream_download or StreamDownloadService()
        self.tagging_package_builder = tagging_package_builder or TaggingPackageBuilder()
        self.tagging_queue_store = tagging_queue_store or TaggingQueueStore() # base-dir location should be managed by ? (user facing relevance?)
        self.tagging_session_id = str(uuid.uuid4())
        self.tagging_sequence_no = 0

    def download_playlist(
        self,
        playlist_url: str,
        base_download_dir: Path,
        options: DownloadOptions,
        results_report_path: Path | None = None,
    ) -> List[DownloadResult]:
        results: List[DownloadResult] = []

        try:
            playlist_obj: ptf.Playlist = self.vid_fetcher.get_playlist_obj(playlist_url)
            playlist_dir: Path = self.os_handler.setup_playlist_dir(
                base_download_dir,
                playlist_obj.title,
                options.no_dir_date,
            )

            # Existing pytubefix workaround retained.
            playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
            logger.debug("Found %s videos in playlist %s", len(playlist_obj.video_urls), playlist_obj.title)

            for i, video in enumerate(playlist_obj.videos):
                logger.info("[%s/%s] Processing: %s", i + 1, len(playlist_obj.videos), video.title)
                results.append(
                    self.download_single(
                        download_dir=playlist_dir,
                        options=options,
                        video_obj=video,
                        playlist_title=playlist_obj.title,
                        results_report_path=results_report_path,
                    )
                )

        except (IOError, PlaylistFetchError) as e:
            logger.error("Failed to process playlist: %s", e)
            return results
        except Exception as e:
            logger.error("Unexpected playlist error: %s", e)
            return results

        success_count = sum(1 for result in results if result.success)
        fail_count = len(results) - success_count
        logger.info("Playlist download completed: %s succeeded, %s failed", success_count, fail_count)
        return results

    def _download_single_video(
        self,
        video_obj: ptf.YouTube,
        download_dir: Path,
        output_path: Path,
        options: DownloadOptions,
    ) -> Path:
        video_stream: ptf.Stream = self.stream_selector.select_stream_video(video_obj, options)
        video_path: Path = self.stream_download.download_stream(video_stream, download_dir)
        if not video_path:
            raise StreamDownloadError("No video stream downloaded")

        video_info = StreamInfo.from_pytubefix_stream(video_stream, video_path)

        audio_info: StreamInfo | None = None
        audio_path: Path | None = None
        try:
            audio_stream: ptf.Stream = self.stream_selector.select_stream_audio(video_obj, options)
            audio_path = self.stream_download.download_stream(audio_stream, download_dir)
            if audio_path:
                audio_info = StreamInfo.from_pytubefix_stream(audio_stream, audio_path)
        except StreamSelectionError:
            if not video_info.includes_audio:
                raise
            logger.info("No separate audio stream selected; using audio embedded in video stream.")

        if options.donotconvert:
            logger.info("Raw mode enabled; keeping downloaded video/audio fragments unchanged.")
            return video_path

        profile = self.media_assembler.resolve_output_profile(
            options,
            audio_only=False,
            video=video_info,
            audio=audio_info,
        )
        return self.media_assembler.combine_streams(
            video=video_info,
            audio=audio_info,
            output_path=output_path,
            profile=profile,
            delete_sources=True,
        )

    def _download_single_audio(
        self,
        video_obj: ptf.YouTube,
        download_dir: Path,
        output_path: Path,
        options: DownloadOptions,
    ) -> Path:
        audio_stream: ptf.Stream = self.stream_selector.select_stream_audio(video_obj, options)
        audio_path: Path = self.stream_download.download_stream(audio_stream, download_dir)
        if not audio_path:
            raise StreamDownloadError("No audio stream downloaded")

        audio_info = StreamInfo.from_pytubefix_stream(audio_stream, audio_path)
        thumbnail_path = self.thumbnail_handler.download_thumbnail(video_obj, download_dir, ) #None  # TODO: re-enable after thumbnail/metadata behavior is decided.

        if options.donotconvert:
            logger.info("Raw mode enabled; keeping downloaded audio fragment unchanged.")
            return audio_path

        profile = self.media_assembler.resolve_output_profile(
            options,
            audio_only=True,
            audio=audio_info,
        )
        return self.media_assembler.convert_audio(
            audio=audio_info,
            output_path=output_path,
            profile=profile,
            thumbnail_path=thumbnail_path,
            delete_sources=True,
        )

    def download_single(
        self,
        options: DownloadOptions,
        download_dir: Path,
        video_obj: ptf.YouTube | None = None, #TODO check: maybe obscurred
        url: str | None = None,
        playlist_title: str | None = None,
        results_report_path: Path | None = None,
    ) -> DownloadResult:
        video_obj: ptf.YouTube = video_obj or self.vid_fetcher.get_video_obj(url)

        base_filename = sanitize_filename(video_obj.title)
        video_title = video_obj.title
        target_ext = self.media_assembler.expected_extension(options)
        target_file = Path(download_dir) / f"{base_filename}{target_ext}"

        #TODO could later be specified to look at ext (e.g. downloaded audio-only and video _> mussic video)
        # Side effect of this being here: _download_single_video can downlaod both streams separat without being blocked by find_existing_file_by_stem()
        existing_file = self.os_handler.find_existing_file_by_stem(download_dir, base_filename)

        if existing_file is not None:
            tagging_info = self._prepare_tagging_package(
                final_path=existing_file,
                download_dir=download_dir,
                video_obj=video_obj,
                options=options,
                playlist_title=playlist_title,
                results_report_path=results_report_path,
            )
            logger.info("⏭ Skipping (already exists): %s -> %s", video_title, existing_file.name)
            return DownloadResult(
                success=True,
                errors=[],
                video_title=video_title,
                video_url=video_obj.watch_url,
                output_path=existing_file,
                source_author=str(getattr(video_obj, "author", "") or ""),
                playlist_title=playlist_title or "",
                tagging_job_id=str((tagging_info or {}).get("job_id", "") or ""),
                tagging_session_id=str((tagging_info or {}).get("session_id", "") or ""),
                tagging_sequence_no=int((tagging_info or {}).get("sequence_no", 0) or 0),
                tagging_state="queue_failed" if options.autotag and tagging_info is None else "",
                tagging_reason="tagging_package_not_created" if options.autotag and tagging_info is None else "",
            )

        logger.info("Downloading %s: %s", "soundtrack" if options.audio_only else "video", video_title)

        try:
            if options.audio_only:
                final_path = self._download_single_audio(video_obj, download_dir, target_file, options)
            else:
                final_path = self._download_single_video(video_obj, download_dir, target_file, options)

            tagging_info = self._prepare_tagging_package(
                final_path=final_path,
                download_dir=download_dir,
                video_obj=video_obj,
                options=options,
                playlist_title=playlist_title,
                results_report_path=results_report_path,
            )
            logger.info("✓ %s", video_title)
            return DownloadResult(
                success=True,
                errors=[],
                video_title=video_title,
                video_url=video_obj.watch_url,
                output_path=final_path,
                source_author=str(getattr(video_obj, "author", "") or ""),
                playlist_title=playlist_title or "",
                tagging_job_id=str((tagging_info or {}).get("job_id", "") or ""),
                tagging_session_id=str((tagging_info or {}).get("session_id", "") or ""),
                tagging_sequence_no=int((tagging_info or {}).get("sequence_no", 0) or 0),
                tagging_state="queue_failed" if options.autotag and tagging_info is None else "",
                tagging_reason="tagging_package_not_created" if options.autotag and tagging_info is None else "",
            )

        except (StreamSelectionError, StreamDownloadError, ConversionError, CombineError) as e:
            logger.error("✗ %s with %s: %s", type(e).__name__, video_title, e)
            return DownloadResult(
                success=False,
                errors=[str(e)],
                video_title=video_title,
                video_url=video_obj.watch_url,
                source_author=str(getattr(video_obj, "author", "") or ""),
                playlist_title=playlist_title or "",
            )
        except Exception as e:
            logger.error("✗ Unexpected error with %s: %s", video_title, e)
            return DownloadResult(
                success=False,
                errors=[str(e)],
                video_title=video_title,
                video_url=video_obj.watch_url,
                source_author=str(getattr(video_obj, "author", "") or ""),
                playlist_title=playlist_title or "",
            )

    def _prepare_tagging_package(
        self,
        *,
        final_path: Path,
        download_dir: Path,
        video_obj: ptf.YouTube,
        options: DownloadOptions,
        playlist_title: str | None = None,
        results_report_path: Path | None = None,
    ) -> dict[str, str | int] | None:
        requested_actions: list[str] = []
        if options.autotag:
            requested_actions.append("autotag")
        if options.prepare_tagging:
            requested_actions.append("prepare_tagging")

        if not requested_actions:
            return None

        self.tagging_sequence_no += 1

        try:
            package = self.tagging_package_builder.build_package(
                final_output_path=final_path,
                download_directory=download_dir,
                video_obj=video_obj,
                options=options,
                requested_actions=requested_actions,
                session_id=self.tagging_session_id,
                sequence_no=self.tagging_sequence_no,
                playlist_title=playlist_title,
                result_report_path=results_report_path,
            )
            package_path = self.tagging_queue_store.write_pending_package(package)
            logger.info("Prepared tagging package: %s", package_path)
            return {
                "job_id": str(getattr(package, "job_id", "") or ""),
                "session_id": str(getattr(package, "session_id", self.tagging_session_id) or ""),
                "sequence_no": int(getattr(package, "sequence_no", self.tagging_sequence_no) or 0),
                "package_path": str(package_path),
            }
        except Exception as exc:
            logger.warning("Failed to prepare tagging package for %s: %s", final_path, exc)
            return None

    def download(
        self,
        url: str,
        options: DownloadOptions,
        results_report_path: Path | None = None,
    ) -> List[DownloadResult]:
        results: List[DownloadResult] = []
        base_download_dir = self.os_handler.expand_path(options.default_download_directory)

        if not (self.urlh.is_youtube_url(url) and self.urlh.is_accessible(url)):
            logger.error("The provided URL is not a valid YouTube URL or inaccessible.")
            return results

        try:
            self.os_handler.create_directory(base_download_dir)

            if self.urlh.has_start_radio(url):
                cleaned = self.urlh.clean_video_link(url)
                if cleaned:
                    logger.info("start_radio detected; treating as single video: %s", cleaned)
                    url = cleaned

            if self.urlh.is_youtube_playlist(url):
                return self.download_playlist(url, base_download_dir, options, results_report_path=results_report_path)

            cleaned_url = self.urlh.clean_video_link(url) or url
            results.append(
                self.download_single(
                    url=cleaned_url,
                    options=options,
                    download_dir=base_download_dir,
                    results_report_path=results_report_path,
                )
            )
            return results

        except Exception as e:
            logger.error("Download failed: %s", e)
            return results
