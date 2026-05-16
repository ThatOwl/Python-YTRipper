import urllib.parse as ulp
import requests
from utility.logger import get_logger
from utility.utils import retry_call

#TODO Improve logging
#TODO Add error handling for invalid URLs, etc.
#TODO Reinforce URL validation in other parts of the code using this class

logger = get_logger(__name__, 'url_handler_debug.log')


class URLHandler:
    """ 
    A class to handle URL validation and extraction for YouTube links.
    """
    
    YOUTUBE_DOMAINS = ("youtube.com", "youtu.be")
    REQUEST_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    ACCESSIBLE_STATUS_CODES = {401, 403, 405, 429}

    @staticmethod
    def _hostname(url: str) -> str:
        return (ulp.urlparse(url).hostname or "").rstrip(".").lower()

    @staticmethod
    def _is_youtube_hostname(hostname: str) -> bool:
        return any(
            hostname == allowed_domain or hostname.endswith(f".{allowed_domain}")
            for allowed_domain in URLHandler.YOUTUBE_DOMAINS
        )
    
    @staticmethod
    def _extract_video_id(url: str) -> str | None:
        u = ulp.urlparse(url)

        # Case 1 — standard watch?v=
        if u.path == "/watch":
            qs = ulp.parse_qs(u.query)
            return qs.get("v", [None])[0]

        # Case 2 — youtu.be/VIDEOID
        if u.netloc in ("youtu.be", "www.youtu.be"):
            return u.path.lstrip("/") or None

        # Case 3 — /shorts/VIDEOID
        if u.path.startswith("/shorts/"):
            return u.path.split("/")[2]

        # Case 4 — /embed/VIDEOID
        if u.path.startswith("/embed/"):
            return u.path.split("/")[2]

        return None

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """
        Check if the given URL is a valid YouTube URL.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL is a YouTube URL, False otherwise.
        """
        try:
            return URLHandler._is_youtube_hostname(URLHandler._hostname(url))
        except Exception as e:
            logger.exception(f"Error parsing URL: {e}")
            return False
        
    @staticmethod
    def is_accessible(url: str) -> bool:
        """
        Check if the given URL is accessible.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL is accessible, False otherwise.
        """
        if not URLHandler.is_youtube_url(url):
            return False

        try:
            response = retry_call(
                lambda: requests.head(
                    url,
                    allow_redirects=True,
                    timeout=10,
                    headers=URLHandler.REQUEST_HEADERS,
                ),
                exceptions=(requests.RequestException,),
                retries=2,
                backoff=1.0,
                backoff_factor=2.0,
                jitter=0.25,
                logger=logger,
            )
            if (
                response.status_code < 400
                or response.status_code in URLHandler.ACCESSIBLE_STATUS_CODES
            ):
                return True
            logger.warning("HEAD accessibility check returned status %s for %s", response.status_code, url)
        except requests.RequestException as e:
            logger.warning("HEAD accessibility check failed for %s: %s", url, e)
        except Exception as e:
            logger.exception(f"Unexpected error checking URL accessibility with HEAD: {e}")

        try:
            response = retry_call(
                lambda: requests.get(
                    url,
                    allow_redirects=True,
                    timeout=10,
                    stream=True,
                    headers=URLHandler.REQUEST_HEADERS,
                ),
                exceptions=(requests.RequestException,),
                retries=1,
                backoff=1.0,
                backoff_factor=2.0,
                jitter=0.25,
                logger=logger,
            )
            try:
                return (
                    response.status_code < 400
                    or response.status_code in URLHandler.ACCESSIBLE_STATUS_CODES
                )
            finally:
                response.close()
        except Exception as e:
            logger.exception(f"Error checking URL accessibility: {e}")
            return False
    
    @staticmethod
    def has_start_radio(url: str) -> bool:
        """Return True if the URL contains start_radio=1 (or truthy)."""
        try:
            parsed = ulp.urlparse(url)
            qs = ulp.parse_qs(parsed.query)
            start_radio = qs.get("start_radio", [None])[0]
            return start_radio is not None and str(start_radio).strip().lower() in ("1", "true", "yes")
        except Exception as e:
            logger.exception("Error parsing start_radio: %s", e)
            return False

    @staticmethod
    def is_youtube_playlist(url: str) -> bool:
        """
        Check if the given URL is a YouTube playlist URL.
        If start_radio=1 is present, treat as NOT a playlist.
        """
        try:
            parsed = ulp.urlparse(url)
            qs = ulp.parse_qs(parsed.query)
            has_list = bool(qs.get("list"))
            start_radio = qs.get("start_radio", [None])[0]
            if start_radio is not None and str(start_radio).strip().lower() in ("1", "true", "yes"):
                return False
            return has_list
        except Exception as e:
            logger.exception(f"Error parsing URL for playlist: {e}")
            return False

    @staticmethod
    def clean_video_link(url: str) -> str | None:
        """
        Return a clean YouTube video URL (https://www.youtube.com/watch?v=VIDEOID).
        If 'start_radio' is present it will be logged and removed.
        """
        #TODO: check if this can handle "-" at the end of video ids (some tests show that it runs into errors)
        try:
            parsed = ulp.urlparse(url)
            qs = ulp.parse_qs(parsed.query)
            # prefer explicit v parameter, fallback to extractor (handles youtu.be, /shorts/, /embed/)
            video_id = qs.get("v", [None])[0] or URLHandler._extract_video_id(url)
            if not video_id:
                logger.debug("clean_video_link: no video id found in URL: %s", url)
                return None
            # detect start_radio case-insensitively
            if any(k.lower() == "start_radio" for k in qs.keys()):
                logger.warning("clean_video_link: 'start_radio' parameter present and will be removed: %s", url)
            return f"https://www.youtube.com/watch?v={video_id}"
        except Exception as e:
            logger.exception("Error cleaning video link: %s", e)
            return None
