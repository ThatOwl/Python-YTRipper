import sys
import os
import shutil
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.logger import get_logger
from source.pytube_interface import YouTubeDownloader as YTD
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
            print(f'Failed to delete {file_path}. Reason: {e}')

def process_command(command):
    """Process a command string for downloading YouTube videos or playlists.

    Args:
        command (str): The command string input by the user.
    """
    parser = argparse.ArgumentParser(description="YouTube Video/Playlist Downloader", add_help=False)
    parser.add_argument('url', help='YouTube video or playlist URL')
    parser.add_argument('-d', '--dir', default='./temp_ripper_downloads', help='Download directory')
    parser.add_argument('-a', '--audio', action='store_true', help='Download audio only')
    parser.add_argument('--clear', action='store_true', help='Clear download directory before downloading')
    try:
        args = parser.parse_args(command.split())
    except SystemExit:
        logger.error("Invalid command or arguments.")
        return

    ytd = YTD()
    urlh = URLH()

    if args.clear:
        logger.info(f"Are you sure you want to clear the directory: {args.dir} ? (y/n)")
        confirmation = input().strip().lower()
        if confirmation == 'y':
            clear_directory(args.dir)
            logger.info(f"Cleared directory: {args.dir}")
        else: 
            logger.info("Directory clear operation cancelled.")
        
    logger.info("------ Starting download ------")
    os.path.exists()
    try:
        ytd.download(url=args.url, download_dir=args.dir, audio_only=args.audio)
        logger.info("Download completed successfully.")
    except Exception as e:
        logger.error(f"Download failed: {e}")
    logger.info("------ End of action ------")

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
            print("Exiting CLI.")
            break
        if not command:
            continue
        process_command(command)
    
if __name__ == "__main__":
    main()