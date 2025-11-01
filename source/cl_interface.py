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

DEFAULT_PREFS = {
    "default_download_directory": "~/Downloads",
    "audio_only": True,
    "warn_me": False,
    "preferred_audio_quality": "",
    "preferred_video_quality": "",
    "preferred_format": "",
    "preferred_abr": "",
    "preferred_resolution": "",
    "preferred_mime": "",
    "loglevel": "WARNING"
}


logger = get_logger(__name__, 'cli_debug.log')


class cl_interface:
    def __init__(self):
        self.preferences = self.read_preferences()
        self.download_options = DownloadOptions.from_preferences(self.preferences)
        
        #TODO this does not work as intended ... logging level not set properly
        prefs = self.preferences if isinstance(self.preferences, dict) else {}
        level_name = prefs.get("loglevel", "info").upper()
        print(f"Loglevel set to: {level_name}")
        #console_handler = logging.StreamHandler(sys.stdout)
        #console_handler.setLevel(getattr(logging, level_name, logging.INFO))
    
        #logger.addHandler(console_handler)
        self.ytd = YTD()
    
    def read_preferences(self) -> dict:
        """Read user preferences from a JSON file. If the file does not exist, create it with default preferences.
        Returns:
            dict: A dictionary containing user preferences.
        """
        path_to_preferences = "./user_settings.json"
        if not os.path.exists(path_to_preferences):
            logger.warning("Path to settings file inaccessible ! \n Reverting to defaults.")  # TODO:  logic
            with open(path_to_preferences, 'w') as f:
                json.dump(DEFAULT_PREFS, f, indent=4)
                return DEFAULT_PREFS
        else:
            with open(path_to_preferences, 'r') as f:
                data = json.load(f)
                logger.info(data)
                return data

    #FIXME: generally unsafe ... error handling, logging, confirmation dialog, permission issues, edge cases
    def clear_directory(self, dir_path: str) -> None:
        """
        Utility function to clear all files and subdirectories in a directory.
        Args:
            dir_path (str): Path to the directory to be cleared.
        """
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.error(f'Failed to delete {file_path}. Reason: {e}')
    
    def clear_dialog(self, dir_path: str) -> None:
        """Prompt the user for confirmation before clearing a directory.
        Args:
            dir_path (str): Path to the directory to be cleared.
        """
        # discrepacy of print and logger on purpose -> user should only see print
        if self.preferences.get("warn_me", True):
            print(f"Are you sure you want to clear the directory: {dir_path} ? (y/n)")
            confirmation = input().strip().lower()
            if confirmation.lower() in {'y', 'yes'}:
                self.clear_directory(dir_path)
                logger.debug(f"Cleared directory: {dir_path}")
            else: 
                logger.debug("Directory clear operation cancelled.")
        else:
            self.clear_directory(dir_path)
            logger.debug(f"Cleared directory without confirmation: {dir_path}")
        
        return


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
        
        if args.audio:
            self.download_options.audio_only = True
        
        if args.clear:
            self.clear_dialog(args.dir)

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
                self.ytd.download(url=args.url, download_dir=args.dir, options=self.download_options)
            except Exception as e:
                logger.error(f"Download failed: {e}")

        print("------ End of action ------")

def main():
    cli = cl_interface()

    print("YouTube Downloader CLI (type 'exit' or '(q)uit' to leave)")
    print("Usage: <url> [-i] [-a] [-d <dir>] [--clear]")
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
        cli.process_command(command)
    
if __name__ == "__main__":
    main()
