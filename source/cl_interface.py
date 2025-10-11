import sys
import os
import shutil
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.logger import get_logger
from source.pytube_interface import DownloadOptions, YouTubeDownloader as YTD
from source.url_handler import URLHandler as URLH

logger = get_logger(__name__, 'cli_debug.log')

def clear_directory(dir_path):
    """Utility function to clear all files and subdirectories in a directory."""
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.warning(f'Failed to delete {file_path}. Reason: {e}')

def process_command(command):
    """Process a command string for downloading YouTube videos or playlists.

    Args:
        command (str): The command string input by the user.
    """
    parser = argparse.ArgumentParser(description="YouTube Video/Playlist Downloader", add_help=False)
    parser.add_argument('url', help='YouTube video or playlist URL')
    parser.add_argument('-d', '--dir', default='./temp_ripper_downloads', help='Download directory')
    parser.add_argument('-a', '--audio', action='store_true', help='Download audio only')
    parser.add_argument('-i', '--info', action='store_true', help='Print video/playlist info and exit')
    parser.add_argument('--clear', action='store_true', help='Clear download directory before downloading')
    
    try:
        args = parser.parse_args(command.split())
    except SystemExit:
        logger.error("Invalid command or arguments.")
        return

    ytd = YTD()
    #urlh = URLH()
    preferences = DownloadOptions(audio_only=args.audio)

    if args.clear:
        print(f"Are you sure you want to clear the directory: {args.dir} ? (y/n)")
        confirmation = input().strip().lower()
        if confirmation == 'y':
            clear_directory(args.dir)
            logger.info(f"Cleared directory: {args.dir}")
        else: 
            logger.info("Directory clear operation cancelled.")
    
    if args.info:
        print("Fetching video/playlist info...")
        try:
            ytd.info(url=args.url)
        except Exception as e:
            logger.error(f"Failed to fetch info: {e}")
        return
    else: 
        print("------ Starting download ------")
        try:
            ytd.download(url=args.url, download_dir=args.dir, options=preferences)
            #logger.info("Download completed successfully.")
        except Exception as e:
            logger.error(f"Download failed: {e}")
            
    """ 
    #optional old code kept for reference
    if urlh.is_youtube_url(args.url):
            logger.debug(f"Valid YouTube URL: {args.url}")

            if not os.path.exists(args.dir):
                os.mkdir(args.dir)
                logger.debug(f"Created download directory: {args.dir}")
            try:    
                if urlh.is_youtube_playlist(args.url):
                    logger.debug("Detected as a playlist URL.")
                    ytd.download_playlist(playlist_url=args.url, download_dir=args.dir, audio_only=args.audio)
                else:
                    logger.debug("Detected as a single video URL.")
                    ytd.download_single(video_url=args.url, download_dir=args.dir, audio_only=args.audio)
            except Exception as e:
                logger.error(f"Download failed: {e}")
                raise e
        else:
            logger.error("The provided URL is not a valid YouTube URL.")
            raise ValueError("The provided URL is not a valid YouTube URL.")"""

    print("------ End of action ------")

def main():
    import logging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    print("YouTube Downloader CLI (type 'exit' or '(q)uit' to leave)")
    print("Usage: <url> [-a] [-d <dir>] [--clear]")
    print("Be aware of --clear it will delete EVERYTHING in <dir> !")
    print("Be aware in current version created empty directories will not be deleted!")
    while True:
        """Prompt for user input and process commands until the user decides to exit."""
        try:
            command = input("yt-ripper> ").strip()
        except EOFError:
            print("\nExiting CLI.")
            break
        if command.lower() in ('exit', 'quit', 'q'):
            print("\n Exiting CLI. \n\n")
            break
        if not command:
            continue
        process_command(command)
    
if __name__ == "__main__":
    main()