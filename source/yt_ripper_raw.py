import re
import os
import pytube
from pytube_interface import PyTubeDownloader as PTD

if __name__ == "__main__":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # This script downloads videos from a YouTube playlist using the pytubefix library.
    # Make sure to install pytubefix using pip: pip install pytubefix
    # Replace the playlist URL with your desired playlist URL
    
    ptd = PTD()

    playlist_url ='https://www.youtube.com/playlist?list=PLK-wX9rC-lPPgFaXPQuyVX-WfW8EWHA_3'
    DOWNLOAD_DIR = '/home/localuser/Videos'
    video_url = 'https://www.youtube.com/watch?v=AFnp28QasHE'
    
    #PTD.download_playlist_as_audio(PTD, playlist_url, DOWNLOAD_DIR)
    # PTD.download_videos_from_playlist(PTD, playlist_url, DOWNLOAD_DIR)
    # PTD.download_audio_from_video(PTD, video_url, DOWNLOAD_DIR)
    ptd.single_video_info(video_url)