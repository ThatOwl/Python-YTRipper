import sys
import os
import shutil
import argparse
import json
import logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.logger import get_logger
from source.pytube_interface import DownloadOptions, YouTubeDownloader as YTD
from source.url_handler import URLHandler as URLH

logger = get_logger(__name__, 'cli_debug.log')

#TODO:  How to test this cli?
#       currently used manually
# maybe add data-object for arguments to pass around? (like DownloadOptions)
# => later GUI to interface with CLI instead of classes? ... facade-pattern instead? 

class cl_interface:
    def __init__(self):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)
        self.ytd = YTD()    
    
    def read_preferences(self):
        path_to_preferences = "./user_settings.json"
        if not os.path.exists(path_to_preferences):
            print("Path to settings file inaccessible !") #TODO: log + logic
        else: 
            with open(path_to_preferences, 'r') as f:
                self.preferences = json.load(f)
            print(self.preferences)
        pass

    def clear_directory(self, dir_path: str) -> None:
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

    def process_command(self, command:str) -> None:
        """Process a command string for downloading YouTube videos or playlists.
        #this need to be deleted ... again
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
        
        print("i was here  ")
        print(self.preferences)
        self.preferences.audio_only = args.audio
        
        if args.clear:
            print(f"Are you sure you want to clear the directory: {args.dir} ? (y/n)")
            confirmation = input().strip().lower()
            if confirmation.lower() in {'y', 'yes'}:
                self.clear_directory(args.dir)
                logger.info(f"Cleared directory: {args.dir}")
            else: 
                logger.info("Directory clear operation cancelled.")
        
        if args.info:
            print("Fetching video/playlist info...")
            try:
                self.ytd.info(url=args.url)
            except Exception as e:
                logger.error(f"Failed to fetch info: {e}")
            return
        else: 
            print("------ Starting action ------")
            try:
                self.ytd.download(url=args.url, download_dir=args.dir, options=self.preferences)
                #logger.info("Download completed successfully.")
            except Exception as e:
                logger.error(f"Download failed: {e}")

        print("------ End of action ------")

def main():
    

    cli = cl_interface()

    print("YouTube Downloader CLI (type 'exit' or '(q)uit' to leave)")
    print("Usage: <url> [-a] [-d <dir>] [--clear]")
    print("Be aware of --clear it will delete EVERYTHING in <dir> !")
    print("Be aware in current version created empty directories will not be deleted!")
    logger.debug("testing: " + os.getcwd())
    cli.read_preferences()
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
        cli.process_command(command)
    
if __name__ == "__main__":
    main()
