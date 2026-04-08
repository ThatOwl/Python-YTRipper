import urllib.parse as ulp
import requests
from utility.logger import get_logger

#TODO Improve logging
#TODO Add error handling for invalid URLs, etc.
#TODO Reinforce URL validation in other parts of the code using this class

logger = get_logger(__name__, 'uh_debug.log')


class URLHandler:
    """ 
    A class to handle URL validation and extraction for YouTube links.
    """
    
    YOUTUBE_DOMAINS = [
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "www.youtu.be"
    ]
    
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
            parsed_url = ulp.urlparse(url)
            domain = parsed_url.netloc.lower()
            return any(youtube_domain in domain for youtube_domain in URLHandler.YOUTUBE_DOMAINS)
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
        try:
            response = requests.head(url, allow_redirects=True)
            return response.status_code == 200
        except Exception as e:
            logger.exception(f"Error checking URL accessibility: {e}")
            #raise e
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
            video_id = qs.get("v", [None])[0] or self._extract_video_id(url)
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