# This script downloads videos from a YouTube playlist using the pytubefix library.
# Make sure to install pytubefix using pip: pip install pytubefix

# for manual testing of pytube_interface functions
import sys
import os
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.infrastructure.logger import get_logger
from source.domain.pytube_interface import YouTubeDownloader as YTD
from source.components.url_handler import URLHandler as URLH

logger = get_logger(__name__, 'man_test_debug.log')


def clear_directory(dir_path):
    """Utility function to clear all files in a directory."""
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


if __name__ == "__main__":
    #os.environ['PYTHONIOENCODING'] = 'utf-8'
    logger.info(" ------ Manual test script for pytube_interface and url_handler ------ \n\n\n")
    ytd = YTD()
    urlh = URLH()
    
    playlist_url ='https://www.youtube.com/playlist?list=PLK-wX9rC-lPPgFaXPQuyVX-WfW8EWHA_3'
    DOWNLOAD_DIR = './temp_test_download'
    video_url = 'https://www.youtube.com/watch?v=W9NRUznftt8'
    
    ytd.download(url=playlist_url, download_dir=DOWNLOAD_DIR, audio_only=True)
    ytd.download(url=video_url, download_dir=DOWNLOAD_DIR, audio_only=False)

    #clear_directory('./logs')
    #clear_directory(DOWNLOAD_DIR)
    logger.info("\n\n\n ------ End of manual test script for pytube_interface and url_handler ------ ")