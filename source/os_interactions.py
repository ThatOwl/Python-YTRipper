import sys
import os
import json
import shutil
import logging
from typing import Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import source.logger

logger = source.logger.get_logger(__name__, 'os_interactions.log')

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
PATH_TO_PREFERENCES = "./user_settings.json"

class OSInteractions:
    """Small utility for filesystem / preferences operations. Stateless and easy to mock."""

    def __init__(self):
        self.prefs_path = PATH_TO_PREFERENCES # could be parameterized if needed
        self.logs_path = source.logger.PATH_TO_LOGS

    def read_preferences(self) -> Dict:
        """
        Read user preferences from a JSON file. If the file does not exist, create it with default preferences.
        Returns:
            dict: A dictionary containing user preferences.
        """
        if not os.path.exists(self.prefs_path):
            logger.warning("Path to settings file inaccessible ! \n Reverting to defaults.")  # TODO:  logic
            try:
                with open(self.prefs_path, 'w') as f:
                    json.dump(DEFAULT_PREFS, f, indent=4)
            except Exception as e:
                logger.exception("Failed to create default preferences file: %s", e)
        try:
            with open(self.prefs_path, 'r') as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.exception("Failed to read preferences: %s", e)
        
        return DEFAULT_PREFS

    def write_preferences(self, prefs: Dict) -> None:
        """
        Write user preferences to a JSON file.
        Args:
            prefs (dict): A dictionary containing user preferences.
        """
        try:
            # preferences directory creation if needed
            #os.makedirs(os.path.dirname(self.prefs_path), exist_ok=True)
            with open(self.prefs_path, 'w') as fh:
                json.dump(prefs, fh, indent=4)
        except Exception:
            logger.exception("Failed to write preferences to %s", self.prefs_path)

    #FIXME: a bit unsafe ... permission issues, edge cases
    def clear_directory(self, dir_path: str) -> None:
        """
        Utility function to clear all files and subdirectories in a directory.
        Aborts unless the target directory is inside the current user's home directory.
        Args:
            dir_path (str): Path to the directory to be cleared.
        """
        # Resolve paths safely
        home = os.path.realpath(os.path.expanduser("~"))
        target = os.path.realpath(os.path.abspath(os.path.expanduser(dir_path)))

        # Abort if target is not inside user's home directory
        try:
            if os.path.commonpath([home, target]) != home:
                logger.warning("clear_directory: aborting because %s is not inside the user's home directory %s", target, home)
                return
        except Exception:
            # If commonpath raises (e.g. on different drives on Windows), be conservative and abort
            logger.warning("clear_directory: unable to verify that %s is inside %s — aborting for safety", target, home)
            return

        if not os.path.isdir(target):
            logger.debug("clear_directory: not a directory: %s", target)
            return

        for filename in os.listdir(target):
            file_path = os.path.join(target, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception:
                logger.exception("Failed to delete %s", file_path)

    # maybe unusable ... trying to move to logger.py
    def clear_logs(self) -> None:
        if not os.path.isdir(self.logs_path):
            logger.debug("clear_logs: not a directory: %s", self.logs_path)
            return
        # First, delete old_*.log files
        for filename in os.listdir(self.logs_path):
            if filename.startswith("old_") and filename.endswith(".log"):
                file_path = os.path.join(self.logs_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                except Exception:
                    logger.exception("Failed to delete log file %s", file_path)

        # Then, rename remaining *.log files
        for filename in os.listdir(self.logs_path):
            if filename.endswith(".log"):
                try:
                    new_name = filename.replace(".log", f"old_{filename}.log")
                    os.rename(os.path.join(self.logs_path, filename), os.path.join(self.logs_path, new_name))
                except Exception:
                    logger.exception("Failed renaming log %s", filename)