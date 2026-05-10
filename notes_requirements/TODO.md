## research
- how to properly log
- how to minimize exception handling 

## big
- X refactor "download_dir" into "options" => DO NOT ... as file-dwnld may create multiple playlists => which have own dwnld-dirs !
- ! Add behaviour for autotag
- ! Add behaviour for datasaver (use video_obj.filesize or .length) 
- ! Add load_preset behaviour -> laod then overwrite with passed args -> only allow saving of custom!
(in playlists dwdnld skip x > 15min->add url to output.txt & in single more complex)
- !!! ONLY DEPEND ON INTERFACES ! => impl. interfaces
- !! fix path handling and renaming o file ... including .mp4/mp3 bullshit
- ! add unittesting
- op. adapt stream_converter to accept SOME file-formats
- !! validate user_saettings file for fields and content type

- handle exception thrown resulting from internet connection timeout (cleanly)
- add history CONSIDER: [argparse_history](https://pypi.org/project/argparse-history/) or in file with max size of 20 entries -> use arrow key for navigation during interaction

## Small
- Vary testing URLs for better robustness ... maybe search for specific codecs and paring them together

## By Topic
### Pasting link is not well-defined
- find out if start_radio is appended to valid playlists => add case so list can still be downloaded
### Parallel Processing
- X will not be implemented in near future => requires usage of proxies / multi-point to not trigger YTs Bot-detection

## DownloadOrchestrator:
- look at codec and container for naming file and passing as much info as needed via (maybe new container and not "options")
- get stream download size before download => info for user in "datasaver" mode
- op. look at /.venv/lib/python3.11/site-packages/pytubefix/query.py
- op. warn on "datasaver"
 "video_obj.length" if length is very short or very long
 low resolution videos
- Adapt info for GUI:

## cl_interface:
- How to test cli? => Tasks (bash etc -> can still be unittested) + unittesting now possible

## web-ui
- read [chat_webUI-vs-desktop.md](./chat_webUI-vs-desktop.md)

## stream converter
- refactor needed as cleanup
- improve argument passing
- look at interaction with DownloadOrchestrator => improve container/codec selection and passing

## select stream 
- ? major refactor into methods (+, cleanup, logging, exceptions, includes)