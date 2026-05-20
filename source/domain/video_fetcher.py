"""VideoFetcher
Responsibility: “Given a URL → return a video/playlist object”
Wraps pytubefix exceptions
No filesystem
No looping
"""

from typing import Callable, TypeVar

import pytubefix as ptf
import pytubefix.exceptions as ptf_ex

from utility.logger import get_logger
from utility.utils import VideoFetchError, PlaylistFetchError

logger = get_logger(__name__, 'VideoFetcher_debug.log')

T = TypeVar("T")
AGE_CHECK_EXCEPTIONS = (
    ptf_ex.AgeRestrictedError,
    ptf_ex.AgeCheckRequiredAccountError,
    ptf_ex.AgeCheckRequiredError,
)

class VideoFetcher(object):
    """docstring for VideoFetcher."""

    #TODO: implement as YT-API seems to actually "miss" sometimes
    # reasons not to implement: first try-hit-ratio is ~95 % and
    #  YT-API blocking that results from too many requests this strategy might hurt perfomance (earlier blocking)
    #  =>   current strategy is: "user restarts same operation after 10min on inadequate hit-rate after blocking opccured"
    #       "exists-scan" only requests when an earlier miss occured (efficient) limiting total requests
    """@retry(exceptions=(ptf_ex.VideoUnavailable, ptf_ex.RegexMatchError, ptf_ex.LiveStreamError, Exception),
        retries=2, backoff=1.0, backoff_factor=2.0, jitter=0.2, logger=logger)
    def _get_video_obj_with_retry(self, video_url: str) -> ptf.YouTube:
        # delegate to existing logic (keeps original exception handling and logging)
        return YouTubeDownloader._get_video_obj.__wrapped__(self, video_url) if hasattr(YouTubeDownloader._get_video_obj, "__wrapped__") else YouTubeDownloader._get_video_obj(self, video_url)
    """

    @staticmethod
    def _build_video_obj(
        video_url: str,
        *,
        use_oauth: bool = False,
        allow_oauth_cache: bool = True,
        oauth_verifier: Callable[[str, str], None] | None = None,
    ) -> ptf.YouTube:
        """
        Build a pytubefix YouTube object, optionally using OAuth for age-restricted content.
        """
        kwargs = {}
        if use_oauth:
            kwargs.update(
                use_oauth=True,
                allow_oauth_cache=allow_oauth_cache,
                oauth_verifier=oauth_verifier,
            )

        try:
            video_obj = ptf.YouTube(video_url, **kwargs)
            return video_obj

        except ptf_ex.LiveStreamError as e:
            logger.error("Live stream video (not supported): %s", video_url)
            logger.debug("LiveStreamError while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Live stream videos are not supported: {video_url}") from e
        except ptf_ex.RegexMatchError as e:
            logger.error("Invalid or malformed video URL: %s", video_url)
            logger.debug("RegexMatchError while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Invalid or malformed video URL: {video_url}") from e
        except ptf_ex.VideoPrivate as e:
            logger.error("Private video: %s", video_url)
            logger.debug("VideoPrivate while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Private video: {video_url}") from e
        except ptf_ex.VideoRegionBlocked as e:
            logger.error("Region-blocked video: %s", video_url)
            logger.debug("VideoRegionBlocked while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Video is not available in your region: {video_url}") from e
        except AGE_CHECK_EXCEPTIONS as e:
            logger.error("Age check required for video: %s", video_url)
            logger.debug("Age-check exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Age verification is required to view this video: {video_url}") from e
        except ptf_ex.VideoUnavailable as e:
            logger.error("Video unavailable: %s", video_url)
            logger.debug("VideoUnavailable exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Could not fetch the video at {video_url}. It appears to be unavailable.") from e
        except VideoFetchError:
            raise
        except Exception as e:
            logger.error("Failed to fetch video %s", video_url)
            logger.debug("Unexpected exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(
            f"Could not fetch the video at {video_url}. Please check the URL and your network connection."
            ) from e

    @staticmethod
    def _default_cli_oauth_verifier(verification_url: str, user_code: str) -> None:
        print("")
        print("Age-restricted content requires a one-time YouTube device sign-in.")
        print(f"Open this URL: {verification_url}")
        print(f"Enter this code: {user_code}")

        try:
            input("Press Enter here after you complete the sign-in flow to continue the download: ")
        except EOFError as exc:
            raise VideoFetchError(
                "Interactive OAuth was started, but this session could not accept confirmation input. "
                "Re-run the download in an interactive terminal to complete sign-in."
            ) from exc

    @staticmethod
    def _is_age_restriction_exception(exc: BaseException | None) -> bool:
        current = exc
        seen: set[int] = set()

        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, AGE_CHECK_EXCEPTIONS):
                return True
            current = current.__cause__ or current.__context__

        return False

    @staticmethod
    def _non_interactive_oauth_required_message(video_url: str) -> str:
        return (
            "Age-restricted content requires an interactive OAuth session. "
            "This run is non-interactive (batch/playlist), so the item was skipped. "
            f"Re-run this video separately, or start a dedicated authenticated session first with --auth-session true: {video_url}"
        )

    @staticmethod
    def get_video_obj(video_url: str) -> ptf.YouTube | Exception:
        """
        Fetch a YouTube video object without OAuth.
        """
        return VideoFetcher._build_video_obj(video_url)

    @staticmethod
    def get_video_obj_with_oauth(
        video_url: str,
        *,
        allow_oauth_cache: bool = True,
        oauth_verifier: Callable[[str, str], None] | None = None,
    ) -> ptf.YouTube:
        """
        Fetch a YouTube video object with pytubefix OAuth enabled.

        This is intended as a narrow fallback for age-restricted content so the
        default downloader path stays unauthenticated.
        """
        return VideoFetcher._build_video_obj(
            video_url,
            use_oauth=True,
            allow_oauth_cache=allow_oauth_cache,
            oauth_verifier=oauth_verifier,
        )

    @staticmethod
    def run_with_age_restricted_oauth_fallback(
        video_ref: ptf.YouTube | str,
        action: Callable[[ptf.YouTube], T],
        *,
        allow_oauth_cache: bool = True,
        allow_interactive_oauth: bool = True,
        oauth_verifier: Callable[[str, str], None] | None = None,
    ) -> T:
        """
        Execute an operation against a video and retry with OAuth only when
        pytubefix reports that age verification is required.
        """
        if isinstance(video_ref, str):
            video_url = video_ref
            try:
                video_obj = VideoFetcher.get_video_obj(video_ref)
            except VideoFetchError as exc:
                if not VideoFetcher._is_age_restriction_exception(exc):
                    raise

                if not allow_interactive_oauth:
                    logger.info("Skipping OAuth prompt for non-interactive age-restricted video: %s", video_url)
                    raise VideoFetchError(
                        VideoFetcher._non_interactive_oauth_required_message(video_url)
                    ) from exc

                logger.info("Age-restricted video detected during fetch; retrying with OAuth: %s", video_url)
                video_obj = VideoFetcher.get_video_obj_with_oauth(
                    video_url,
                    allow_oauth_cache=allow_oauth_cache,
                    oauth_verifier=oauth_verifier or VideoFetcher._default_cli_oauth_verifier,
                )
        else:
            video_obj = video_ref
            video_url = str(getattr(video_obj, "watch_url", "") or "")

        try:
            return action(video_obj)
        except AGE_CHECK_EXCEPTIONS as exc:
            if not allow_interactive_oauth:
                if video_url:
                    logger.info("Skipping OAuth prompt for non-interactive age-restricted video: %s", video_url)
                    raise VideoFetchError(
                        VideoFetcher._non_interactive_oauth_required_message(video_url)
                    ) from exc
                raise VideoFetchError(
                    "Age-restricted content requires an interactive OAuth session, but no retryable video URL was available."
                ) from exc

            if getattr(video_obj, "use_oauth", False):
                logger.error("Age check still required after OAuth retry: %s", video_url)
                raise VideoFetchError(
                    f"Age verification is required to view this video even after OAuth retry: {video_url}"
                ) from exc

            if not video_url:
                logger.error("Age check required but the video URL is unavailable for OAuth retry.")
                raise VideoFetchError(
                    "Age verification is required, but the video could not be retried with OAuth."
                ) from exc

            logger.info("Age-restricted video detected; retrying with OAuth: %s", video_url)
            oauth_video_obj = VideoFetcher.get_video_obj_with_oauth(
                video_url,
                allow_oauth_cache=allow_oauth_cache,
                oauth_verifier=oauth_verifier or VideoFetcher._default_cli_oauth_verifier,
            )

            try:
                return action(oauth_video_obj)
            except AGE_CHECK_EXCEPTIONS as oauth_exc:
                logger.error("OAuth retry did not unlock age-restricted video: %s", video_url)
                raise VideoFetchError(
                    f"Age verification is required to view this video even after OAuth retry: {video_url}"
                ) from oauth_exc

    #TODO improve error handling
    @staticmethod
    def get_playlist_obj(playlist_url: str) -> ptf.Playlist:
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
            raise PlaylistFetchError(
                f"Could not fetch the playlist at {playlist_url}. Please check the URL and your network connection."
            ) from e
