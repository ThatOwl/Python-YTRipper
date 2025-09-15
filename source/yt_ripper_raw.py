import re
import os
import pytube
from pytube_interface import PyTubeDownloader as PTD
from url_handler import URLHandler as URLH


from pytube_interface import PyTubeDownloader2 as PTD2


if __name__ == "__main__":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # This script downloads videos from a YouTube playlist using the pytubefix library.
    # Make sure to install pytubefix using pip: pip install pytubefix
    # Replace the playlist URL with your desired playlist URL
    
    ptd = PTD()
    urlh = URLH()
    
    ptd2 = PTD2()
    
    playlist_url ='https://www.youtube.com/playlist?list=PLK-wX9rC-lPPgFaXPQuyVX-WfW8EWHA_3'
    DOWNLOAD_DIR = '/home/localuser/Videos'
    video_url = 'https://www.youtube.com/watch?v=W9NRUznftt8'
    
    ptd.single_video_info(video_url)
    
    if urlh.is_youtube_url(playlist_url):
        ptd.download_playlist(playlist_url, DOWNLOAD_DIR)
    else:
        print("Invalid YouTube URL")
        
    
    if urlh.is_youtube_url(video_url):
        ptd2.download_single(video_url, DOWNLOAD_DIR, audio_only=False)
    else:
        print("Invalid YouTube URL")    
    
    #ptd2.download_playlist(playlist_url, DOWNLOAD_DIR, audio_only=True)