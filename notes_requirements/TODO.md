## big
- retry wrapper 5s timeout
- file parser for csv should be able to have results-csv as input (including playlist name)
- ??? pivot to secondary wrapper arounf yt-dlp
- tell ffmpeg to use GPU for videos ?
- DONE Add load_preset behaviour -> laod then overwrite with passed args -> only allow saving of custom!
- op. adapt stream_converter to accept SOME file-formats
- handle exception thrown resulting from internet connection timeout (cleanly)

## warning
- X refactor "download_dir" into "options" => DO NOT ... as file-dwnld may create multiple playlists => which have own dwnld-dirs !
(in playlists dwdnld skip x > 15min->add url to output.txt & in single more complex)
- X will not be implemented => requires usage of proxies / multi-point to not trigger YTs Bot-detection

## Small
- Vary testing URLs for better robustness ... maybe search for specific codecs and paring them together
- write two scripts for installation and aliases

## later 
- if packaged -> use std paths in os (e.g. appdata for win) 

## By Topic
## research
- how to properly log
- how to minimize exception handling 
- find out if start_radio is appended to valid playlists => add case so list can still be downloaded (Pasting link is not well-defined)

## documentation
- RECOMMEND users to use presets as much as possible -> way less work
- user should know that re-downloading after a try (without renaming or moving download-dir / target-dir) AUTOCOMPLETES the playlists
- check setup and cleanup shell.conf 
- adapt the install bash script to a setup tool asking user for locations (checking if exists and or setting up) -> aliases -> notify what they can change
- ytf ytp ytl ... 

### Parallel Processing

### Testing
- !!! add unittesting


## DownloadOrchestrator:
- get stream download size before download => info for user in "datasaver" mode
- op. look at /.venv/lib/python3.11/site-packages/pytubefix/query.py
- op. warn on "datasaver"
 "video_obj.length" if length is very short or very long
 low resolution videos
- Adapt info for GUI:

## cl_interface:
- How to test cli? => Tasks (bash etc -> can still be unittested) + unittesting now possible
- TRAILING URL "-" BREAKES DOWNLOADER !
- add cli flaggs that make "--<smth>" behave like user expects them (without 'true' or 'false' requirement) 

## web-ui
- read [chat_webUI-vs-desktop.md](./chat_webUI-vs-desktop.md)

## stream converter

## select stream 
