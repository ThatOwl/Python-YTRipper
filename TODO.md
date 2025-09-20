## Small
- Add thumbnail (reachable via youtube.thumbnail_url) to audio files using ffmeg
- check ffmpeg output for sync and playback errors
- check advantages of converting to different video/audio format
- Add logger stream for removing print/statements => keeping  optional terminal out
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


## From pytube_interface:
### mandatory
TODO: Add logging instead of print statements
- Add error handling for network issues, invalid URLs, etc.
- Add support for different video/audio formats and qualities
- Add command-line interface for easier usage
- Add unit tests for the functions
TODO 
- look at `/.venv/lib/python3.11/site-packages/pytubefix/query.py`
- warn:
    * "video_obj.length" if length is very short or very long
    * low resolution videos
- handle: 
    *   age-restricted videos
    *   private videos
    *   deleted videos
    *   region-restricted videos
### optional
TODO 
- Add progress bar for downloads
- write a method based on "yt.streams.all()" to warn user if some formats 
 are not available for a video in a playlist and skip those formats (?)
 or download the next best format available 
