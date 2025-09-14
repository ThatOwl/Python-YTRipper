import re
import os
from pytubefix import Playlist
from pytubefix import YouTube

def download_videos_from_playlist(playlist_url, download_dir):
    
    playlist = Playlist(playlist_url)
    playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
    print(f"Found {len(playlist.video_urls)} videos in the playlist.")

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    for i, video in enumerate(playlist.videos):
        print(f'Downloading video {i + 1}/{len(playlist.videos)}: {video.title}')
        video.streams.\
            filter(type='video', progressive=True, file_extension='mp4').\
            order_by('resolution').\
            desc().\
            first().\
            download(download_dir)
    print("Download completed.")
    
def download_single_video(video_url, download_dir):
    video = YouTube(video_url)
    print(f'Downloading video: {video.title}')
    video.streams.\
        filter(type='video', progressive=True, file_extension='mp4').\
        order_by('resolution').\
        desc().\
        first().\
        download(download_dir)
    print("Download completed.")

if __name__ == "__main__":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
# This script downloads videos from a YouTube playlist using the pytubefix library.
# Make sure to install pytubefix using pip: pip install pytubefix
# Replace the playlist URL with your desired playlist URL

    playlist = Playlist('https://www.youtube.com/playlist?list=PLK-wX9rC-lPPgFaXPQuyVX-WfW8EWHA_3')
    DOWNLOAD_DIR = '/home/localuser/Videos'
    
    download_videos_from_playlist(playlist.playlist_url, DOWNLOAD_DIR)
    # For downloading a single video, uncomment the line below and provide the video URL
    # download_single_video('https://www.youtube.com/watch?v=AFnp28QasHE', DOWNLOAD_DIR)