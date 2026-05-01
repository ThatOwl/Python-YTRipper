import os
import requests
import pytube as ptf
from utility.logger import get_logger
from utility.utils import retry_call

logger = get_logger(__name__, 'thumbnail_handler_debug.log')

class ThumbnailHandler:
    """Handles downloading and saving YouTube video thumbnails."""
    
    @staticmethod
    def download_thumbnail(video: ptf.YouTube, download_dir: str, base_filename: str) -> str:
        """
        Downloads the thumbnail image of a YouTube video.

        Args:
            video (ptf.YouTube): The YouTube video object from which to download the thumbnail.
            download_dir (str): The directory where the thumbnail will be saved.
            base_filename (str): The base filename to use for the thumbnail file.
        Returns:
            str: The file path of the downloaded thumbnail image.
        Logs:
            - Thumbnail download status.
        """
        thumbnail_url = video.thumbnail_url
        logger.debug(f"Downloading thumbnail from: {thumbnail_url}")
        try:
            # retry the HTTP GET in case of transient network errors
            response = retry_call(lambda: requests.get(thumbnail_url, timeout=10),
                                  exceptions=(requests.RequestException,),
                                  retries=3, backoff=1.0, backoff_factor=2.0, jitter=0.25, logger=logger)
        except Exception as e:
            logger.exception(f"Failed to download thumbnail after retries: {e}")
            return ""
        
        if response.status_code == 200:
            ext = thumbnail_url.split('.')[-1].split('?')[0]
            thumbnail_path = os.path.join(download_dir, f"{base_filename}_thumbnail.{ext}")
            with open(thumbnail_path, 'wb') as f:
                f.write(response.content)
            logger.debug(f"Thumbnail downloaded to: {thumbnail_path}")
            return thumbnail_path
        else:
            logger.warning("Failed to download thumbnail.")
            return ""