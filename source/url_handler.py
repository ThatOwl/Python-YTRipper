import urllib.parse
import requests
from source.logger_a_constants import get_logger

#TODO Add unit tests for this class
#TODO Add logging instead of print statements
#TODO Add error handling for invalid URLs, etc.
#TODO Reinforce URL validation in other parts of the code using this class
#TODO Review code for efficiency and correctness


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
    def is_youtube_url(url: str) -> bool:
        """
        Check if the given URL is a valid YouTube URL.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL is a YouTube URL, False otherwise.
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
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
    def extract_video_id(url: str) -> str | None:
        """
        Extract the video ID from a YouTube URL.

        Args:
            url (str): The YouTube URL.
        Returns:
            str or None: The video ID if found, None otherwise.
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            if 'youtu.be' in parsed_url.netloc:
                return parsed_url.path.lstrip('/')
            elif 'youtube.com' in parsed_url.netloc:
                query_params = urllib.parse.parse_qs(parsed_url.query)
                return query_params.get('v', [None])[0]
            return None
        except Exception as e:
            logger.exception(f"Error extracting video ID: {e}")
            return None
    
    def is_youtube_playlist(self, url: str) -> bool:
        """
        Check if the given URL is a YouTube playlist URL.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL contains '&list=' indicating a playlist, False otherwise.
        """
        try:
            # Check for '&list=' or '?list=' in the URL string (case-insensitive)
            return '&list=' in url.lower() or '?list=' in url.lower()
        except Exception as e:
            logger.exception(f"Error parsing URL for playlist: {e}")
            return False
