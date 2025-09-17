# This script downloads videos from a YouTube playlist using the pytubefix library.
# Make sure to install pytubefix using pip: pip install pytubefix

# for manual testing of pytube_interface functions
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from source.pytube_interface import PyTubeDownloader3 as PTD
from source.url_handler import URLHandler as URLH

if __name__ == "__main__":
    #os.environ['PYTHONIOENCODING'] = 'utf-8'
    print(" ------ Manual test script for pytube_interface and url_handler ------ \n\n\n")
    ptd = PTD()
    urlh = URLH()
    
    playlist_url ='https://www.youtube.com/playlist?list=PLK-wX9rC-lPPgFaXPQuyVX-WfW8EWHA_3'
    DOWNLOAD_DIR = './temp_test_download'
    video_url = 'https://www.youtube.com/watch?v=W9NRUznftt8'    
    
    if not os.path.exists("temp_test_download"):
        os.mkdir("temp_test_download")
    
    ptd.single_video_info(video_url)
    
    """ if urlh.is_youtube_url(playlist_url):
        ptd.download_playlist(playlist_url, DOWNLOAD_DIR)
    else:
        print("Invalid YouTube URL")
    """    
    
    if urlh.is_youtube_url(video_url):
        ptd.download_single(video_url, DOWNLOAD_DIR, audio_only=True)
    else:
        print("Invalid YouTube URL")
    
    #ptd2.download_playlist(playlist_url, DOWNLOAD_DIR, audio_only=True)
