#--------------------
#
#     cli_base.py
#
#--------------------

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.core.logger import get_logger
from source.core.pytube_interface import YouTubeDownloader as YTD
from source.core.os_interactions import OSInteractions

logger = get_logger(__name__, 'cli_debug.log')
class CLIBase:
    def __init__(self):
        self.os = OSInteractions()
        self.preferences = self.os.read_preferences()  # initial load
        # downloader gets os handler injected
        self.ytd = YTD(os_handler=self.os)
    
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
                self.os.clear_directory(dir_path)
                logger.debug(f"Cleared directory: {dir_path}")
            else: 
                logger.debug("Directory clear operation cancelled.")
        else:
            self.os.clear_directory(dir_path)
            logger.debug(f"Cleared directory without confirmation: {dir_path}")
        
        return
    
    


#--------------------
#
#     cli_command.py
#
#--------------------

import sys
import os
import argparse
import logging

#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from source.cli.cli_base import CLIBase

from source.core.logger import get_logger
from source.core.pytube_interface import DownloadOptions, YouTubeDownloader as YTD
from source.core.os_interactions import OSInteractions


logger = get_logger(__name__, 'cli_com_debug.log')

class CommandCLI(CLIBase):
    def __init__(self):
        super().__init__()
        self.parser = self.build_parser()
        self.enable_argcomplete(self.parser)
    
    def build_parser(self) -> argparse.ArgumentParser:
        """Build and return the argument parser for command-line options.
        Returns:
            argparse.ArgumentParser: Configured argument parser.
        """
        parser = argparse.ArgumentParser(description="YouTube Video/Playlist Downloader", add_help=False)
        parser.add_argument('url', help='YouTube video or playlist URL')
        parser.add_argument('-a', '--audio', action='store_true', help='Download audio only')
        parser.add_argument('-a3', '--audio_mp3', action='store_true', help='Download audio as MP3')
        parser.add_argument('-i', '--info', action='store_true', help='Print video/playlist info and exit')
        parser.add_argument('-cl', '--clear_logs', action='store_true', help='Clear log files before downloading')
        parser.add_argument('-c', '--clear', action='store_true', help='Clear download directory before downloading')
        parser.add_argument('-o', '--output', type=OSInteractions().expand_path, help='Output directory: supports ~ expansion')
        parser.add_argument('-h', '--help', action='help', help='Show this help message and exit')
        return parser

    def enable_argcomplete(self, parser):
        """Attempt to enable argcomplete if installed."""
        try:
            import argcomplete
            from argcomplete.completers import DirectoriesCompleter
            # Assign completers (once)
            for action in parser._actions:
                if action.dest == "output":
                    action.completer = DirectoriesCompleter()
            argcomplete.autocomplete(parser)
        except ImportError:
            pass

    def run(self, command:str) -> None:
        """Process a command string for downloading YouTube videos or playlists.
        #this need to be deleted ... again
        Args:
            command (str): The command string input by the user.
        """

        try:
            args = self.parser.parse_args(command.split())
        except SystemExit:
            logger.error("Invalid command or arguments.")
            return 1

        # Update preferences based on command-line arguments
        self.preferences["audio_only"] = True if args.audio else self.preferences.get("audio_only", False)
        if args.audio_mp3:
            self.preferences["audio_mp3"] = True
            self.preferences["audio_only"] = True
        else:
            self.preferences["audio_mp3"] = False
        self.preferences["default_download_directory"] = args.output if args.output else self.preferences.get("default_download_directory", "./temp_ripper_downloads")
        #DELETEME
        print(f"Download directory set to: {self.preferences['default_download_directory']}")
        
        if args.clear: #FIXME: not working properly
            self.clear_dialog(args.dir)

        if args.clear_logs: #FIXME: not working properly
            self.os.clear_logs()
            logger.debug(f"Cleared log files before downloading.")

        if args.info:
            print("Fetching video/playlist info...")
            try:
                self.ytd.info(url=args.url, output=print)
            except Exception as e:
                logger.error(f"Failed to fetch info: {e}")
                return 1
        else:
            print("------ Starting action ------")
            try:
                # Always expand the download directory before passing to downloader
                expanded_download_dir = self.os.expand_path(self.preferences["default_download_directory"])
                self.ytd.download(url=args.url, download_dir=expanded_download_dir, options=DownloadOptions.from_preferences(self.preferences))
            except Exception as e:
                #logger.error(f"Download failed: {e}")
                return 1

        print("------ End of action ------")
        return 0


#--------------------
#
#     cli_interactive.py
#
#--------------------

# ...existing code...
import sys
import os
import argparse

#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from source.cli.cli_base import CLIBase

from source.core.logger import get_logger
from source.core.utils import DownloadOptions
from source.core import preferences


logger = get_logger(__name__, 'cli_inter_debug.log')


class InteractiveCLI(CLIBase):
    """
    Interactive CLI with two-step workflow:
      1) Edit presets (preferences)
      2) Download (uses current presets)
    """

    def __init__(self):
        super().__init__()
        
    def _show_menu(self) -> None:
        print("\nPython-YTRipper - interactive menu")
        print("1) [E]dit presets")
        print("2) [S]how current presets")
        print("3) [D]ownload Single")
        print("4) Download [M]ultiple (loop)")
        print("5) [B]atch import (file with URLs)  [TODO implement parsing formats]")
        print("q) [Q]uit")

    def edit_presets(self) -> None:
        """Interactive editor for preferences. Shows exhaustive choices for known keys."""
        # reload latest prefs before editing
        self.preferences = self.os.read_preferences()

        print("\nEditing presets (leave blank to keep current value)\n")
        defaults = preferences.DEFAULT_PREFS

        for key, default in defaults.items():
            if key == "loglevel":
                choices = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                print(f"{key}: " + " | ".join(f"[{i}] {v}" for i, v in enumerate(choices)))
                print("  Logger verbosity (console).")
                raw = input(f"Select {key} (index or name) [{self.preferences.get(key, default)}]: ").strip()
                if raw == "":
                    continue
                if raw.isdigit():
                    idx = int(raw)
                    if 0 <= idx < len(choices):
                        self.preferences[key] = choices[idx]
                else:
                    if raw.upper() in choices:
                        self.preferences[key] = raw.upper()
                continue

            if isinstance(default, bool):
                print(f"{key}: [0] False | [1] True")
                print("  Boolean option.")
                raw = input(f"Set {key} (0/1) [{self.preferences.get(key, default)}]: ").strip()
                if raw == "":
                    continue
                if raw in ("0", "false", "False"):
                    self.preferences[key] = False
                elif raw in ("1", "true", "True"):
                    self.preferences[key] = True
                else:
                    print("  Unrecognized input; skipping.")
                continue

            if key == "default_download_directory":
                print(f"{key}: path (current: {self.preferences.get(key, default)})")
                print("  Default place where downloads are stored (supports ~ expansion).")
                raw = input("Enter new path (or empty to keep): ").strip()
                if raw == "":
                    continue
                newp = str(self.os.expand_path(raw))
                self.preferences[key] = newp
                print(f"  Set {key} -> {newp}")
                continue

            # fallback for strings
            if isinstance(default, str):
                print(f"{key}: string (current: {self.preferences.get(key, default)})")
                print("  Short explanation: free-text preference, leave empty to keep current.")
                raw = input("Enter new value (or empty to keep): ").strip()
                if raw == "":
                    continue
                self.preferences[key] = raw
                continue

            # unsupported type
            print(f"{key}: (unsupported type for interactive edit)")

        # persist changes
        try:
            self.os.write_preferences(self.preferences)
            logger.info("Preferences saved.")
        except Exception as e:
            logger.error("Failed to save preferences: %s", e)

        # reload to ensure canonicalization
        self.preferences = self.os.read_preferences()
        print("Presets updated.\n")

    def show_presets(self) -> None:
        self.preferences = self.os.read_preferences()
        print("\nCurrent presets:")
        for k, v in self.preferences.items():
            print(f"  {k}: {v}")
        print("")

    def download_flow(self, adjust_preferences: bool = False) -> None:
        """Interactive single-download flow that reuses downloader and prefs."""

        url = input("Enter YouTube video/playlist URL: ").strip()
        if not url:
            print("No URL entered.")
            return
        
        if adjust_preferences:
            raw = input(f"Audio only? (leave empty to use preset {self.preferences.get('audio_only')} ) [y/N]: ").strip().lower()
            if raw in ("y","yes"):
                self.preferences["audio_only"] = True
            elif raw in ("n","no"):
                self.preferences["audio_only"] = False
            dl_dir = self.preferences.get("default_download_directory", preferences.DEFAULT_PREFS["default_download_directory"])
            expanded = str(self.os.expand_path(dl_dir))
            print(f"Using download dir: {expanded}")

        opts = DownloadOptions.from_preferences(self.preferences)
        try:
            self.ytd.download(url=url, download_dir=expanded, options=opts)
        except Exception as e:
            logger.error("Download failed: %s", e)
    
    def download_loop(self) -> None:
        """Simple loop to download multiple URLs sequentially."""
        
        print("Entering download loop. CTRL-C to exit.")
        
        while True:
            self.download_flow()

    def process_batch_file(self, path: str) -> None:
        """
        Placeholder for batch import processing.
        Future: support .txt/.csv/.xlsx with optional per-line overrides (audio-only, output-dir).
        Current: simple text file with one URL per line.
        """
        if not os.path.exists(path):
            print("Batch file not found:", path)
            return
        urls = []
        try:
            if path.lower().endswith(".txt"):
                with open(path, 'r', encoding='utf-8') as fh:
                    for ln in fh:
                        ln = ln.strip()
                        if ln:
                            urls.append(ln)
            else:
                # TODO: implement CSV / XLSX parsing with optional column mapping
                print("Batch format not yet implemented for this extension. Only .txt supported for now.")
                return
        except Exception as e:
            logger.error("Failed reading batch file: %s", e)
            return

        if not urls:
            print("No URLs found in batch file.")
            return

        print(f"Found {len(urls)} entries. Starting sequential download (CTRL-C to stop).")
        opts = DownloadOptions.from_preferences(self.os.read_preferences())
        for u in urls:
            try:
                self.ytd.download(url=u, download_dir=str(self.os.expand_path(self.preferences.get("default_download_directory"))), options=opts)
            except Exception as e:
                logger.error("Failed downloading %s: %s", u, e)
                # continue with next

    def run(self) -> None:
        """Interactive menu loop that coexists with the prompt-based mode."""
        while True:
            self._show_menu()
            choice = input("Select option: ").strip().lower()
            if choice in ("1", "edit", "e"):
                self.edit_presets()
            elif choice in ("2", "show", "s"):
                self.show_presets()
            elif choice in ("3", "single", "d"):
                self.download_flow()
            elif choice in ("4", "multiple", "m"):
                self.download_loop()
            elif choice in ("5", "batch", "b"):
                path = input("Path to batch file (.txt/.csv/.xlsx): ").strip()
                if path:
                    self.process_batch_file(path)
            elif choice in ("q", "quit", "exit"):
                print("Exiting.")
                raise SystemExit(0)
            else:
                print("Unknown option.")



#--------------------
#
#     os_interactions.py
#
#--------------------

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


#--------------------
#
#     preferences.py
#
#--------------------

import os
import json
from pathlib import Path
from typing import Dict

from source.core import logger
import getpass

# ---------- CONSTANTS FOR SETUP & RESTORE -------------------
CURRENT_DIR = Path(__file__).resolve().parent   # → Python-YTRipper/source/core
SOURCE_DIR = CURRENT_DIR.parent                 # → Python-YTRipper/source
PROJECT_ROOT = SOURCE_DIR.parent                # → Python-YTRipper
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

PATH_TO_LOGS = str(LOGS_DIR)

DEFAULT_PREFS: Dict = {
    "default_download_directory": "~/Downloads",
    "audio_only": False,
    "audio_mp3": False,
    "warn_me": False,
    "preferred_audio_quality": "",
    "preferred_video_quality": "",
    "preferred_format": "",
    "preferred_abr": "",
    "preferred_resolution": "",
    "preferred_mime": "",
    "loglevel": "WARNING"
}
# -----------------------------

def current_username() -> str:
    """Return the current executing user's username; fallback to HOME parsing."""
    try:
        return getpass.getuser()
    except Exception:
        home = os.environ.get("HOME", "")
        return Path(home).name if home else ""

PATH_TO_PREFERENCES = str(CONFIG_DIR / f"user_settings_{current_username()}.json")

def read_preferences() -> Dict:
    """
    Read preferences from PATH_TO_PREFERENCES. If missing, create it with DEFAULT_PREFS.
    Returns a dict (never None).
    """
    if not os.path.exists(PATH_TO_PREFERENCES):
        try:
            os.makedirs(os.path.dirname(PATH_TO_PREFERENCES), exist_ok=True)
            with open(PATH_TO_PREFERENCES, 'w', encoding="utf-8") as f:
                json.dump(DEFAULT_PREFS, f, indent=4)
        except:
            return dict(DEFAULT_PREFS)
    else:
        with open(PATH_TO_PREFERENCES, 'r', encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else dict(DEFAULT_PREFS)

def write_preferences(prefs: Dict) -> None:
    """Write provided prefs dict to PATH_TO_PREFERENCES (best-effort)."""
    try:
        os.makedirs(os.path.dirname(PATH_TO_PREFERENCES), exist_ok=True)
        with open(PATH_TO_PREFERENCES, "w", encoding="utf-8") as fh:
            json.dump(prefs if isinstance(prefs, dict) else DEFAULT_PREFS, fh, indent=4)
    except Exception:
        # intentionally silent/fail-safe here; callers can log if desired
        pass


#--------------------
#
#     pytube_interface.py
#
#--------------------

import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
from enum import Enum
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import List
import time
import random
from pathlib import Path 
#FIXME check import from different locations
from source.core.logger import get_logger
from source.core.stream_converter import StreamConverter
from source.core.url_handler import URLHandler
from source.core.os_interactions import OSInteractions
from source.core.thumbnail_handler import ThumbnailHandler
from source.core.utils import DownloadError, DownloadOptions, DownloadResult, retry_call

logger = get_logger(__name__, 'ytd_debug.log')

# downloader-specific subclasses (keep here for module-local semantics)
class VideoFetchError(DownloadError):
    pass

class PlaylistFetchError(DownloadError):
    pass

class StreamDownloadError(DownloadError):
    pass

class ConversionError(DownloadError):
    pass

class CombineError(DownloadError):
    pass

class YouTubeDownloader:
    """
    Handles high-level download logic for YouTube videos and playlists using pytubefix.
    """
    class StreamType(Enum):
        AUDIO = 1
        VIDEO = 0
    stream_type_map = {
        StreamType.AUDIO:'Audio',
        StreamType.VIDEO:'Video'
    }

    def __init__(self, os_handler: OSInteractions = None):
        self.thumbnail_handler = ThumbnailHandler()
        self.stream_converter = StreamConverter()
        self.urlh = URLHandler()
        self.os_handler = os_handler
        if self.os_handler is None:
            from source.core.os_interactions import OSInteractions
            self.os_handler = OSInteractions()

    def _get_video_obj(self, video_url: str) -> ptf.YouTube:
        """
        Fetches a YouTube video object.
        Args:
            video_url (str): The URL of the YouTube video.
        Returns:
            ptf.YouTube: The YouTube video object.
        Raises:
            VideoFetchError: If there is an error fetching the video.
        """
        try:
            video_obj = ptf.YouTube(video_url)
            return video_obj
        except ptf_ex.VideoUnavailable as e:
            # concise user-facing error
            logger.error("Video unavailable: %s", video_url)
            # full diagnostic to debug/file
            logger.debug("VideoUnavailable exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"video unavailable: {video_url}") from e
        except ptf_ex.LiveStreamError as e:
            logger.error("Live stream video (not supported): %s", video_url)
            logger.debug("LiveStreamError while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Live stream video (not supported): {video_url}") from e
        except ptf_ex.RegexMatchError as e:
            logger.error("Invalid or malformed video URL: %s", video_url)
            logger.debug("RegexMatchError while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Regex match error for video: {video_url}") from e
        except ptf_ex.VideoPrivate as e:
            logger.error("Private video: %s", video_url)
            logger.debug("VideoPrivate while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Private video: {video_url}") from e
        except ptf_ex.VideoRegionBlocked as e:
            logger.error("Region-blocked video: %s", video_url)
            logger.debug("VideoRegionBlocked while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Region-blocked video: {video_url}") from e
        except (ptf_ex.AgeCheckRequiredAccountError, ptf_ex.AgeCheckRequiredError) as e:
            logger.error("Age check required for video: %s", video_url)
            logger.debug("Age-check exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"Age check required for video: {video_url}") from e
        except Exception as e:
            logger.error("Failed to fetch video: %s", video_url)
            logger.debug("Unexpected exception while fetching %s", video_url, exc_info=True)
            raise VideoFetchError(f"An error occurred while fetching the video {video_url}: {e}") from e

    #TODO improve error handling
    def _get_playlist_obj(self, playlist_url: str) -> ptf.Playlist:
        """
        Fetches a YouTube playlist object.
        Args:
            playlist_url (str): The URL of the YouTube playlist.
        Returns:
            ptf.Playlist: The YouTube playlist object.
        Raises:
            PlaylistFetchError: If there is an error fetching the playlist.
        """
        try:
            playlist_obj = ptf.Playlist(playlist_url)
            return playlist_obj
        except ptf_ex.RegexMatchError as e:
            logger.error("Invalid or malformed playlist URL: %s", playlist_url)
            logger.debug("RegexMatchError while fetching playlist %s", playlist_url, exc_info=True)
            raise PlaylistFetchError(f"Regex match error for playlist: {playlist_url}") from e
        except Exception as e:
            logger.error("Failed to fetch playlist: %s", playlist_url)
            logger.debug("Unexpected exception while fetching playlist %s", playlist_url, exc_info=True)
            raise PlaylistFetchError(f"An error occurred while fetching the playlist {playlist_url}: {e}") from e

    def _sanitize_filename(self, title: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", title)

    def _download_stream_type(self, video: ptf.YouTube, download_dir: str, base_filename: str, type: Enum) -> str:
        """
        Downloads either the highest quality audio or video stream from a YouTube video object.
        
        Args:
            video (ptf.YouTube): The YouTube video object from which to download the stream.
            download_dir (str): The directory where the downloaded file will be saved.
            base_filename (str): The base filename to use for the downloaded file.
            type (int): The type of stream to download. If truthy, downloads audio; if falsy, downloads video.
        Returns:
            str: The file path of the downloaded stream, or an empty string if no suitable stream is found.
        Logs:
            - Selected stream details (audio bitrate or video resolution and mime type).
            - If no suitable stream is available.
        Raises:
            StreamDownloadError: If there is an error during the download process.
        """
        try:
            # Select the appropriate stream based on the type
            #TODO implement preferred quality, abr, resolution
            if type == self.StreamType.AUDIO:
                stream = video.streams.filter(type='audio').order_by('abr').desc().first()
                logger.debug(f"Selected audio stream: {stream.abr}, {stream.mime_type}")
            else:
                stream = video.streams.filter(type='video', progressive=False).order_by('resolution').desc().first()
                logger.debug(f"Selected video stream: {stream.resolution}, {stream.mime_type}")

            if not stream:
                logger.warning(f"No suitable {self.stream_type_map[type]} stream available for this video.")
                return ""
            
            ext = stream.subtype
            downloaded_path = stream.download(
                output_path=download_dir,
                filename=f"{base_filename}_{self.stream_type_map[type]}.{ext}",
                skip_existing=True,
                timeout=5,
                max_retries=3
            )
            return downloaded_path
        
        except Exception as e:
            logger.exception(f"Error downloading {self.stream_type_map[type]} stream: {e}")
            raise StreamDownloadError(f"Error downloading {self.stream_type_map[type]} stream: {e}") from e

    def download_single(self, download_dir: str, options: DownloadOptions, video_url: str = None, video_obj: ptf.YouTube = None) -> DownloadResult:
        """
        Download a single YouTube video as video or audio.

        Args:
            video_url (str): The URL of the YouTube video.
            download_dir (str): The directory to save the downloaded file.
            audio_only (bool): If True, download audio only. If False, download video.
        """
        # in case a video object is already available, use it
        try:
            if video_obj is None: 
                video_obj = self._get_video_obj(video_url)
        except Exception as e:
            logger.error(f"Failed to fetch video object: {e}")
            return DownloadResult(success=False, errors=[str(e)])

        base_filename: str = self._sanitize_filename(video_obj.title)
        logger.info(f'Downloading {"soundtrack" if options.audio_only else "video"}: {video_obj.title}') #TODO log less info?
        try:
            if options.audio_only:
                audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
                thumbnail_path = None #FIXME self.thumbnail_handler.download_thumbnail(video_obj, download_dir, base_filename)
                output_path = os.path.join(download_dir, base_filename+f"{'.m4a' if not options.audio_mp3 else '.mp3'}")
                if not audio_path:
                    msg = "no audio stream available"
                    logger.error(msg)
                    return DownloadResult(success=False, errors=[msg])
                self.stream_converter.convert_audio(audio_path, output_path, thumbnail_path)
                
            else:
                video_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.VIDEO)
                audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
                output_path = os.path.join(download_dir, f"{base_filename}.mp4")
                if not video_path or not audio_path:
                    msg = "missing audio or video stream"
                    logger.error(msg)
                    return DownloadResult(success=False, errors=[msg])
                self.stream_converter.combine_streams(audio_path, video_path, output_path)

            logger.debug(f'Download of {"soundtrack" if options.audio_only else "video"} completed.')
            return DownloadResult(success=True, errors=[])
        
        except (StreamDownloadError, ConversionError, CombineError) as e:
            logger.error(f"Download failed: {e}")
            return DownloadResult(success=False, errors=[str(e)])
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return DownloadResult(success=False, errors=[str(e)])

    def download_playlist(self, playlist_url: str, download_dir: str, options: DownloadOptions) -> List[DownloadResult]:
        """
        Download all videos from a YouTube playlist as video or audio files.

        Args:
            playlist_url (str): The URL of the YouTube playlist.
            download_dir (str): The directory to save the downloaded files.
            audio_only (bool): If True, download audio only. If False, download video.
        Side Effects:
            - creates directory as playlist download target. 
        Logs:
            - Playlist download status.
        Returns:
            List[DownloadResult]: A list of results for each video download in the playlist.
        """
        date = datetime.today().strftime('%Y_%m_')
        results: List[DownloadResult] = []
        try:
            playlist_obj = self._get_playlist_obj(playlist_url)
        except Exception as e:
            logger.error(f"Failed to fetch playlist object: {e}")
            return #TODO could raise error upstream
        
        # Override pytube's video URL regex to capture all videos in the playlist
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        logger.debug(f"Found {len(playlist_obj.video_urls)} videos in the playlist. {playlist_obj.title}")
        
        # Build a Path for the playlist directory and ensure it exists
        playlist_dir = Path(download_dir) / f"{date}{self._sanitize_filename(playlist_obj.title)}"

        # create new directory for each playlists -> easier for user
        try:
            if not playlist_dir.exists(): #if user retries existing dir, skip creation
                logger.info(f"Creating playlist download directory: {playlist_dir}")
                playlist_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create playlist directory {playlist_dir}: {e}")
            return results

        for i, video in enumerate(playlist_obj.videos):
            logger.info(f'At {"soundtrack" if options.audio_only else "video"} {i + 1}/{len(playlist_obj.videos)}: ')
            result = self.download_single(download_dir=str(playlist_dir), options=options, video_obj=video)
            results.append(result)

        logger.info("Playlist download completed.")
        return results

    def info(self, url: str = None, video_obj: ptf.YouTube = None, output: callable = None) -> None:
        """
        Print or log information about a YouTube video or playlist.

        Args:
        url (str): The URL of the YouTube video or playlist.
        video_obj (ptf.YouTube, optional): A YouTube video object. Defaults to None.
        output (callable, optional): A callable that takes a string, e.g. `print` or `logger.info`.
            Defaults to `logger.info`.
        """
        
        output = output or logger.info        
        
        if self.urlh.is_youtube_playlist(url):
            try:
                playlist_obj = self._get_playlist_obj(url)
            except Exception as e:
                logger.error(f"Failed to fetch playlist object: {e}")
                return
        
            output(f"Playlist Title: {playlist_obj.title}")
            output(f"Number of Videos: {len(playlist_obj.videos)}")
            output("Videos:")
            for i, video in enumerate(playlist_obj.videos):
                output(f"{i + 1}. {video.title} ({video.length} seconds)")
        else:
            try:
                if video_obj is None:
                    video_obj = self._get_video_obj(url)
            except Exception as e:
                logger.error(f"Failed to fetch video object: {e}")
                return

            output(f"Video title: {video_obj.title}")
            output(f"Video length: {video_obj.length} seconds")
            output(f"Video views: {video_obj.views}")
            output(f"Video author: {video_obj.author}")
            output(f"Video description: {video_obj.description[:200]}...")
            output(f"Thumbnail: {video_obj.thumbnail_url}")

            output("Available streams:")
            output("  Video:")
            for stream in video_obj.streams.filter(type='video').order_by('resolution').desc():
                output(f"- {stream.resolution}, {stream.mime_type}, {stream.fps}fps")
            output(f"Best video: {video_obj.streams.filter(type='video').order_by('resolution').desc().first()}")

            output("  Audio:")
            for stream in video_obj.streams.filter(type='audio').order_by('abr').desc():
                output(f"- {stream.mime_type}, {stream.abr}")
            output(f"Best audio: {video_obj.streams.filter(type='audio').order_by('abr').desc().first()}")

    def download(self, url: str, download_dir: str, options: DownloadOptions) -> None:
        """
        Download a YouTube video or playlist.
        Args:
            url (str): The URL of the YouTube video or playlist.
            download_dir (str): The directory to save the downloaded files.
            options (DownloadOptions): The download options.
        Side Effects:
            - creates download directory if it does not exist. 
        Logs:
            - Download status.
        """
        results = []
        
        if self.urlh.is_youtube_url(url) and self.urlh.is_accessible(url):
            logger.debug(f"Valid YouTube URL: {url}")
            try:
                if not os.path.exists(download_dir): #works for one level only
                    os.makedirs(download_dir)
                    logger.info(f"Created download directory: {download_dir}")

                if self.urlh.is_youtube_playlist(url):
                    logger.debug("Detected as a playlist URL.")
                    results = self.download_playlist(playlist_url=url, download_dir=download_dir, options=options)
                else:
                    logger.debug("Detected as a single video URL.")
                    results.append(self.download_single(video_url=url, download_dir=download_dir, options=options))
                    
            except Exception as e:
                logger.error(f"Download failed: {e}")
                return #TODO could raise error upstream
        else:
            logger.error("The provided URL is not a valid YouTube URL or inaccessible.")
            raise ValueError("The provided URL is not valid or unreachable.")
        
        # Summarize results
        success_count = sum(1 for result in results if result.success)
        failure_count = len(results) - success_count
        logger.info(f"Download Summary: {success_count} succeeded, {failure_count} failed.")


#--------------------
#
#     stream_converter.py
# ... uses ffmpeg (via ffmpeg-python) for conversion
# will not be displayed in full (unneccessary), but has these functions: 
#--------------------

# convert_audio uses convert_to_m4a and convert_to_m4a -> will later be refactored to be private and other formats will be supported
class StreamConverter:
    def convert_audio(audio_path: str, output_path: str, thumbnail_path: str = None) -> None:
    def convert_to_mp3(audio_path: str, output_path: str) -> None:
    def convert_to_m4a(audio_path: str, output_path: str, thumbnail_path: str = None) -> None:
    def combine_streams(audio_path: str, video_path: str, output_path: str) -> None:

#--------------------
#
#     thumbnail_handler.py
#
#--------------------

import os
import requests
import pytube as ptf
from source.core.logger import get_logger
from source.core.utils import retry_call

logger = get_logger(__name__, 'th_debug.log')

class ThumbnailHandler:
    """Handles downloading and saving YouTube video thumbnails."""
    
    @staticmethod
    def download_thumbnail(video: ptf.YouTube, download_dir: str, base_filename: str) -> str:
        """
        Downloads the thumbnail image of a YouTube video.

        Args:
            video (ptf.YouTube): The YouTube video object from which to download the thumbnail.
            download_dir (str): The directory where the thumbnail will be saved.
            base_filename (str): The base filename to use for the thumbnail file.
        Returns:
            str: The file path of the downloaded thumbnail image.
        Logs:
            - Thumbnail download status.
        """
        thumbnail_url = video.thumbnail_url
        logger.debug(f"Downloading thumbnail from: {thumbnail_url}")
        try:
            # retry the HTTP GET in case of transient network errors
            response = retry_call(lambda: requests.get(thumbnail_url, timeout=10),
                                  exceptions=(requests.RequestException,),
                                  retries=3, backoff=1.0, backoff_factor=2.0, jitter=0.25, logger=logger)
        except Exception as e:
            logger.exception(f"Failed to download thumbnail after retries: {e}")
            return ""
        
        if response.status_code == 200:
            ext = thumbnail_url.split('.')[-1].split('?')[0]
            thumbnail_path = os.path.join(download_dir, f"{base_filename}_thumbnail.{ext}")
            with open(thumbnail_path, 'wb') as f:
                f.write(response.content)
            logger.debug(f"Thumbnail downloaded to: {thumbnail_path}")
            return thumbnail_path
        else:
            logger.warning("Failed to download thumbnail.")
            return ""


#--------------------
#
#     url_handler.py
#
#--------------------

import urllib.parse
import requests
from source.core.logger import get_logger

#TODO Add unit tests for this class
#TODO Add logging instead of print statements
#TODO Add error handling for invalid URLs, etc.
#TODO Reinforce URL validation in other parts of the code using this class
#TODO Review code for efficiency and correctness


logger = get_logger(__name__, 'uh_debug.log')


class URLHandler:
    """ 
    A class to handle URL validation and extraction for YouTube links.
    """
    
    YOUTUBE_DOMAINS = [
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "www.youtu.be"
    ]

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """
        Check if the given URL is a valid YouTube URL.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL is a YouTube URL, False otherwise.
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc.lower()
            return any(youtube_domain in domain for youtube_domain in URLHandler.YOUTUBE_DOMAINS)
        except Exception as e:
            logger.exception(f"Error parsing URL: {e}")
            return False
        
    @staticmethod
    def is_accessible(url: str) -> bool:
        """
        Check if the given URL is accessible.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL is accessible, False otherwise.
        """
        try:
            response = requests.head(url, allow_redirects=True)
            return response.status_code == 200
        except Exception as e:
            logger.exception(f"Error checking URL accessibility: {e}")
            #raise e
            return False

    @staticmethod
    def extract_video_id(url: str) -> str | None:
        """
        Extract the video ID from a YouTube URL.

        Args:
            url (str): The YouTube URL.
        Returns:
            str or None: The video ID if found, None otherwise.
        """
        try:
            parsed_url = urllib.parse.urlparse(url)
            if 'youtu.be' in parsed_url.netloc:
                return parsed_url.path.lstrip('/')
            elif 'youtube.com' in parsed_url.netloc:
                query_params = urllib.parse.parse_qs(parsed_url.query)
                return query_params.get('v', [None])[0]
            return None
        except Exception as e:
            logger.exception(f"Error extracting video ID: {e}")
            return None
    
    def is_youtube_playlist(self, url: str) -> bool:
        """
        Check if the given URL is a YouTube playlist URL.

        Args:
            url (str): The URL to check.
        Returns:
            bool: True if the URL contains '&list=' indicating a playlist, False otherwise.
        """
        try:
            # Check for '&list=' or '?list=' in the URL string (case-insensitive)
            return '&list=' in url.lower() or '?list=' in url.lower()
        except Exception as e:
            logger.exception(f"Error parsing URL for playlist: {e}")
            return False



#--------------------
#
#     utils.py
#
#--------------------

from dataclasses import dataclass
from typing import List, Callable, Tuple, Type, Any, Dict
import time
import random

#TODO currently has no logging; consider adding if needed

# Domain exceptions / base
class DownloadError(Exception):
    """Base exception for download-related errors."""

# Models / result objects
@dataclass(frozen=True)
class DownloadOptions:
    audio_only: bool = False
    audio_mp3: bool = False
    preferred_abr: str = ""
    preferred_resolution: str = ""
    preferred_audio_quality: str = ""
    preferred_video_quality: str = ""
    preferred_format: str = ""
    preferred_mime: str = ""

    @classmethod
    def from_preferences(cls, prefs: Dict[str, Any]) -> 'DownloadOptions':
        return cls(
            audio_only=prefs.get("audio_only", False),
            audio_mp3=prefs.get("audio_mp3", False),
            preferred_abr=prefs.get("preferred_abr", ""),
            preferred_resolution=prefs.get("preferred_resolution", ""),
            preferred_audio_quality=prefs.get("preferred_audio_quality", "best"),
            preferred_video_quality=prefs.get("preferred_video_quality", "best"),
            preferred_format=prefs.get("preferred_format", ""),
            preferred_mime=prefs.get("preferred_mime", "")
        )

@dataclass
class DownloadResult:
    success: bool
    errors: List[str]

# Retry helper (stateless)
def retry_call(callable_fn: Callable[[], Any],
               exceptions: Tuple[Type[BaseException], ...] = (Exception,),
               retries: int = 3,
               backoff: float = 1.0,
               backoff_factor: float = 2.0,
               jitter: float = 0.25,
               logger=None) -> Any:
    """
    Inline retry helper for callables. Retries callable_fn() on specified exception types.
    - callable_fn: no-arg callable to execute
    - exceptions: tuple of exception types to catch and retry on
    - retries: number of retry attempts (not counting first try)
    - backoff/backoff_factor/jitter: control wait between retries
    - logger: optional logger to log retry attempts
    """
    attempts_left = retries
    delay = backoff
    attempt = 1
    while True:
        try:
            return callable_fn()
        except exceptions as e:
            if attempts_left <= 0:
                raise
            if logger:
                logger.warning(
                    "Transient error (inline) attempt %d/%d: %s — retrying in %.2fs",
                    attempt, retries + 1, e, delay
                )
            time.sleep(delay + random.uniform(0, jitter))
            attempts_left -= 1
            delay *= backoff_factor
            attempt += 1


#--------------------
#
#     main.py
#
#--------------------

import sys
import os

#TODO ... a lot 
# implement startup into different modes based on sys.argv
# e.g. "menu" for interactive, otherwise command mode
# possibly add other modes later (e.g. GUI)
# for now, just basic interactive vs command line

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.cli.cli_interactive import InteractiveCLI
from source.cli.cli_command import CommandCLI

def main():
    if len(sys.argv) == 1 or sys.argv[1] in ("-m", "-i","--menu", "--interactive"):
        InteractiveCLI().run()
    elif sys.argv[1] in ("-h", "--help", "-l", "--loop"):
        if sys.argv[1] in ("-h", "--help"):
            print("YouTube Downloader CLI (type 'exit' or '(q)uit' to leave)")
            print("Either run in interactive mode (no arguments) or provide a single command.")
            print("- Interactive mode enter with [m]enu or [i]nteractive.")
            print("- Loop mode [l]oop: command menu repeatedly after each command.")
            print("- Command mode: provide all arguments in one line. (limited options)")
            CommandCLI().run("--help")
        
        while True:
            try:
                command = input("yt-ripper> ").strip()
            except EOFError:
                print("\nExiting CLI.")
                return 1
            if command.lower() in ('exit', 'quit', 'q'):
                print("\n Exiting CLI. \n\n")
                return 0
            if not command:
                continue
            
            CommandCLI().run(command)
    else:
        cmdline = " ".join(sys.argv[1:])
        CommandCLI().run(cmdline)

if __name__ == "__main__":
    main()


