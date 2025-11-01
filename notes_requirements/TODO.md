## big
- move some functions into utility class (os/fs related) -> rm empty folders (e.g. on fatal error)
- 

## Small
- Add thumbnail (reachable via youtube.thumbnail_url) to audio files using ffmeg
- check ffmpeg output for sync and playback errors
- check advantages of converting to different video/audio format
- Vary testing URLs for better robustness ... maybe search for specific codecs and paring them together

## 1. Pasting link is not well-defined
- YT may think of video as part of playlist and or radio
- Look at: https://www.youtube.com/watch?v=W9NRUznftt8  &list=RDW9NRUznftt8 &start_radio=1 
- IMPORTANT: This is a special URL that combines a video and a playlist => common case when user clicks "Play all" on a video page
- Handle this case properly in interface and url_handler

## 2. Parallel Processing
- Selecting downloads folder will stay singular for all
- However pasing links of multiple playlists or videos shall be worked on with a variable (settings) thread count
- This may require dynamic allocation (one playlist finishes downloads (freeing threads) -> other thread family can grow)


## pytube_interface:
### mandatory TODO:
- Check dataclass DownloadOptions for completness and functionality 
- Check interaction for pointing to right directory and path creation !!
- Add support for different video/audio formats and qualities
- Add unit tests for the functions
TODO 
- look at `/.venv/lib/python3.11/site-packages/pytubefix/query.py`
- warn:
    * "video_obj.length" if length is very short or very long
    * low resolution videos

### optional TODO: 
- Add progress bar for downloads
- write a method based on "yt.streams.all()" to warn user if some formats 
 are not available for a video in a playlist and skip those formats (?)
 or download the next best format available 
- look at /.venv/lib/python3.11/site-packages/pytubefix/query.py
- warn
 "video_obj.length" if length is very short or very long
 low resolution videos

## cl_interface:
### mandatory TODO:
- clear_dir could be move to util_class
- --//-- is unsafe and needs to check if dir resides in user-space
- --//-- make default to use new-dir "/PyRipper" -> check if inside this dir => user_settings can disable this -> adapt os-interactions
- How to test this cli?

### optional TODO: 
- validate user_saettings file for fields and contet type
- => later GUI to interface with CLI instead of classes? ... facade-pattern instead? 

Check ext reference:
025-10-11 16:44:08.266 [info] [CODE REFERENCING] file:///media/SharedStorage/GitRepos/Python-YTRipper/source/cl_interface.py Similar code with 5 license types [Apache-2.0, BSD-3-Clause, GPL-3.0, MIT, unknown] https://github.com/github-copilot/code_referencing?cursor=c1bfb56df0a1d42fe1d04c87549d8753&editor=vscode [Ln 15, Col 24] os.path.join(dir_path, filename)  try:  if os.path.isfile(file_path) or os.path.is...