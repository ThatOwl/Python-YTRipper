## research
- how to inject logger, os, handlers etc.
- how to properly log
- how to handle errors upstream
- how to minimize exception handling 

## big
- maybe: make options part of downloader-class ? discuss with chat
- refactor codebase as discussed with chat => restructure to make classses injectable and mockable for unittests.
- DROP interactive menu ! (or pause development)
- -> otherwise make a GUI with qt5
- refactor "download_dir" into "options"
- add history in file with max size of 20 entries -> use arrow key for navigation during interaction
- add method to interact with preferrence file for editing with limits
- FIX path being "STR" or "PATH" type !!!
    - > path is cumbersome revise solution
    - > problem with many libs expecting str (ffmpeg, pytube)
- if single video fails (not playlist!) delete download dir 

## Small
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
- Add support for different video/audio formats and qualities
- Add unit tests for the functions

### optional TODO: 
- Add progress bar for downloads
- write a method based on "yt.streams.all()" to warn user if some formats 
 are not available for a video in a playlist and skip those formats (?)
 or download the next best format available 
- look at /.venv/lib/python3.11/site-packages/pytubefix/query.py
- warn
 "video_obj.length" if length is very short or very long
 low resolution videos
- Adapt info for GUI:

If you also want to document and reuse data programmatically, you can make info() return structured info, and have a separate helper for displaying:
```python
def get_info(self, url: str = None, video_obj: ptf.YouTube = None) -> dict:
    """Return structured info about a video or playlist."""
    # ...same logic, but instead of outputting, build a dict
    return {
        "type": "playlist",
        "title": playlist_obj.title,
        "videos": [{"title": v.title, "length": v.length} for v in playlist_obj.videos],
    }
```

## cl_interface:
### mandatory TODO:
- How to test cli?
- => Tasks (bash etc -> can still be unittested)

### optional TODO: 
- validate user_saettings file for fields and content type
- => later GUI to interface with CLI instead of classes? ... facade-pattern instead? 

Check ext reference:
025-10-11 16:44:08.266 [info] [CODE REFERENCING] file:///media/SharedStorage/GitRepos/Python-YTRipper/source/cl_interface.py Similar code with 5 license types [Apache-2.0, BSD-3-Clause, GPL-3.0, MIT, unknown] https://github.com/github-copilot/code_referencing?cursor=c1bfb56df0a1d42fe1d04c87549d8753&editor=vscode [Ln 15, Col 24] os.path.join(dir_path, filename)  try:  if os.path.isfile(file_path) or os.path.is...