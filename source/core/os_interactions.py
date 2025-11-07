import sys
import os
import json
import shutil
from typing import Dict
from pathlib import Path

#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import source.core.logger
import source.core.preferences as preferences
logger = source.core.logger.get_logger(__name__, 'osi_debug.log')


class OSInteractions:
    """Small utility for filesystem / preferences operations. Stateless and easy to mock."""

    def __init__(self):
        self.prefs_path = preferences.PATH_TO_PREFERENCES # could be parameterized if needed
        self.logs_path = preferences.PATH_TO_LOGS


    def expand_path(self, path_str: str) -> Path:
        return Path(os.path.expandvars(os.path.expanduser(path_str))).resolve()
        
    def read_preferences(self) -> Dict:
        # delegate to single source of truth to avoid duplicate code/import locks
        return preferences.read_preferences()

    def write_preferences(self, prefs: Dict) -> None:
        # delegate to single source of truth to avoid duplicate code/import locks
        preferences.write_preferences(prefs)

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