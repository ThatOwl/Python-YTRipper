import re
import os
from pytubefix import Playlist

playlist = Playlist('https://www.https://www.youtube.com/playlist?list=PLx24KgwZ68O3d7n-pXHSLS7VcufJL3WLx')
DOWNLOAD_DIR = '/home/localuser/Videos'
playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
print(len(playlist.video_urls))

for url in playlist.video_urls:
    print(url)

with open(DOWNLOAD_DIR+"/new_test", "w",encoding="utf-8") as file:
    file.write("This is a testfile.")
    
for i, video in enumerate(playlist.videos):
    print('downloading : {} with url : {}'.format(f"Video_{i}", video.watch_url))
    video.streams.\
        filter(type='video', progressive=True, file_extension='mp4').\
        order_by('resolution').\
        desc().\
        first().\
        download(DOWNLOAD_DIR)
        
video.streams.\
        filter(type='video', progressive=True, file_extension='mp4').\
        order_by('resolution').\
        desc().\
        first().\
        download(DOWNLOAD_DIR)