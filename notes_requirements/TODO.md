## research
- how to properly log
- how to minimize exception handling 

## big
- ! refactor "download_dir" into "options" => DO NOT ... as file-dwnld may create multiple playlists => which have own dwnld-dirs !
- !!! ONLY DEPEND ON INTERFACES ! => impl. interfaces
- !! fix path handling and renaming o file ... including .mp4/mp3 bullshit
- ! add unittesting
- op. adapt stream_converter to accept any file-format
- op. implement "datasaver" mode (mobile lower quality and warn video length -> size prediction ?)

- check preferences handling
- handle exception thrown resulting from internet connection timeout (cleanly)
- maybe: make options part of downloader-class ? discuss with chat
- add history in file with max size of 20 entries -> use arrow key for navigation during interaction
- add method (CLI done, json done, GUI separate) to interact with preferrence file for editing with limits

## Small
- Vary testing URLs for better robustness ... maybe search for specific codecs and paring them together

## By Topic
### Pasting link is not well-defined
- find out if start_radio is appended to valid playlists => add case so list can still be downloaded
### Parallel Processing
- will not be implemented in near future => requires usage of proxies / multi-point to not trigger YTs Bot-detection


## orchestration:
- read docu and discussion with chat

## pytube_interface:
- refactor to multiple classes ! (Orchestration)
- Check dataclass DownloadOptions for completness and functionality 
- look at codec and container for naming file and passing as much info as needed via (maybe new container and not "options")
- get stream download size before download => info for user in "datasaver" mode
- op. look at /.venv/lib/python3.11/site-packages/pytubefix/query.py
- op. warn on "datasaver"
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
- How to test cli?
- => Tasks (bash etc -> can still be unittested)
- op. validate user_saettings file for fields and content type
- op. => later GUI to interface with CLI instead of classes? ... facade-pattern instead? 

## stream converter
- refactor needed as cleanup
- improve argument passing
- look at interaction with PytubeInterface => improve container selection and passing

## select stream 
- major refactor into methods (+, cleanup, logging, exceptions, includes)