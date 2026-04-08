"""VideoFetcher
Responsibility: “Given a URL → return a video/playlist object”
Wraps pytubefix exceptions
No filesystem
No looping
"""

import pytubefix as ptf
import pytubefix.exceptions as ptf_ex

from utility.logger import get_logger
from utility.utils import VideoFetchError, PlaylistFetchError

logger = get_logger(__name__, 'VideoFetcher_debug.log')

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
    def get_video_obj(video_url: str) -> ptf.YouTube | Exception:
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
            raise PlaylistFetchError(f"An error occurred while fetching the playlist {playlist_url}: {e}") from e
