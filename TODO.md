## Small
- Add thumbnail (reachable via youtube.thumbnail_url) to audio files using ffmeg


## 1. Pasting link is not well-defined
- YT may think of video as part of playlist and or radio
- Look at: https://www.youtube.com/watch?v=W9NRUznftt8  &list=RDW9NRUznftt8 &start_radio=1 
- IMPORTANT: This is a special URL that combines a video and a playlist => common case when user clicks "Play all" on a video page
- Handle this case properly in interface and url_handler

## 2. Parallel Processing
- Selecting downloads folder will stay singular for all
- However pasing links of multiple playlists or videos shall be worked on with a variable (settings) thread count
- This may require dynamic allocation (one playlist finishes downloads (freeing threads) -> other thread family can grow)