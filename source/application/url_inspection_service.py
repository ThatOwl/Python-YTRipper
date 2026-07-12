from __future__ import annotations

from application.media_info_service import MediaInfoService
from application.state_models import UrlInspectionResult
from domain.video_fetcher import VideoFetcher
from infrastructure.url_handler import URLHandler
from utility.logger import get_logger

logger = get_logger(__name__, "url_inspection_service_debug.log")


class UrlInspectionService:
    """Shared URL validation and info-preview service for CLI and web adapters."""

    def __init__(
        self,
        *,
        url_handler: URLHandler | None = None,
        media_info_service: MediaInfoService | None = None,
        video_fetcher: VideoFetcher | None = None,
    ):
        self.url_handler = url_handler or URLHandler()
        self.video_fetcher = video_fetcher or VideoFetcher()
        self.media_info_service = media_info_service or MediaInfoService(
            url_handler=self.url_handler,
            video_fetcher=self.video_fetcher,
        )

    def inspect_local(self, url: str) -> UrlInspectionResult:
        raw_url = str(url or "").strip()
        looks_like_youtube = self.url_handler.is_youtube_url(raw_url)
        is_playlist = looks_like_youtube and self.url_handler.is_youtube_playlist(raw_url)
        cleaned_url = ""
        normalized_url = raw_url

        if looks_like_youtube and not is_playlist:
            cleaned_url = self.url_handler.clean_video_link(raw_url) or ""
            normalized_url = cleaned_url or raw_url

        return UrlInspectionResult(
            url=raw_url,
            normalized_url=normalized_url,
            cleaned_url=cleaned_url,
            looks_like_youtube_url=looks_like_youtube,
            is_playlist=is_playlist,
        )

    def inspect(
        self,
        url: str,
        *,
        remote_check: bool = False,
        fetch_info: bool = False,
    ) -> UrlInspectionResult:
        result = self.inspect_local(url)

        if not result.looks_like_youtube_url:
            return result

        if remote_check:
            result.remote_checked = True
            result.remotely_accessible = self.url_handler.is_accessible(result.normalized_url or result.url)
            if fetch_info and result.remotely_accessible is False:
                return result

        if not fetch_info:
            return result

        try:
            inspection_url = result.normalized_url or result.url
            result.info_lines = self.media_info_service.get_info_lines(inspection_url)
            result.info_fetched = True
            if result.is_playlist:
                result.title = self.media_info_service.get_playlist_title(inspection_url)
                result.item_count = len(self.media_info_service.get_playlist_video_titles(inspection_url))
            else:
                result.title = self.media_info_service.get_video_title(inspection_url)
                result.item_count = 1
        except Exception as exc:
            logger.warning("Failed to inspect URL %s: %s", result.url, exc)
            result.error = str(exc)

        return result
