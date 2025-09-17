
# for manual testing of pytube_interface functions
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import source.pytube_interface as pti
import pytubefix as ptf
import unittest
import os
#import re
import shutil

#TODO: Add more tests for error handling, edge cases, etc.
# Only happy path tests are implemented so far
# Validate behavior using mock objects if possible

KEEP_FILES = True

class TestPyTubeDownloader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists("temp_test_download"):
            os.mkdir("temp_test_download")
        
    @classmethod
    def tearDownClass(cls):
        if not KEEP_FILES:
            shutil.rmtree("temp_test_download")
    
    def setUp(self):
        self.downloader = pti.PyTubeDownloader()
        self.video_url = "https://www.youtube.com/watch?v=W9NRUznftt8"  # Example video URL
        self.playlist_url = "https://www.youtube.com/playlist?list=PLK-wX9rC-lPPgFaXPQuyVX-WfW8EWHA_3"  # Example playlist URL
        self.download_dir = "./temp_test_download"

    def test_single_video_info_happy(self):
        try:
            self.downloader.single_video_info(self.video_url)
        except Exception as e:
            self.fail(f"single_video_info raised an exception: {e}")

    def test_download_single_video_happy(self):
        try:
            self.downloader.download_single(self.video_url, self.download_dir, audio_only=False)
        except Exception as e:
            self.fail(f"_download_stream raised an exception: {e}")

    def test_download_single_audio_happy(self):
        try:
            video_obj = ptf.YouTube(self.video_url)
            self.downloader._download_stream(video_obj, self.download_dir, audio_only=True)
        except Exception as e:
            self.fail(f"_download_stream raised an exception: {e}")

    @unittest.skip("Skipping playlist download test to save time and resources")
    def test_download_playlist_videos_happy(self):
        try:
            self.downloader.download_playlist(self.playlist_url, self.download_dir, audio_only=False)
        except Exception as e:
            self.fail(f"download_playlist raised an exception: {e}")

    @unittest.skip("Skipping playlist download test to save time and resources")
    def test_download_playlist_audios_happy(self):
        try:
            self.downloader.download_playlist(self.playlist_url, self.download_dir, audio_only=True)
        except Exception as e:
            self.fail(f"download_playlist raised an exception: {e}")
            
            
if __name__ == "__main__":
    unittest.main()