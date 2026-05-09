import os
import re
from pathlib import Path
import csv
from typing import Dict, List, Tuple
from datetime import datetime

from utility.logger import get_logger
import utility.preferences as preferences
from infrastructure.url_handler import URLHandler
from utility.utils import sanitize_filename

logger = get_logger(__name__, 'os_interactions_debug.log')


class OSInteractions:
    """Filesystem and file I/O operations (preferences, batch files, paths)."""

    def __init__(self):
        self.prefs_path = preferences.PATH_TO_PREFERENCES
        self.logs_path = preferences.PATH_TO_LOGS

    def expand_path(self, path_str: str) -> Path:
        """
        Expand user-provided paths.

        Handles:
        - ~/Downloads
        - $HOME/Downloads
        - normal absolute Linux paths
        - common WSL typo: mnt/d/... -> /mnt/d/...
        - optional Windows drive paths: D:\\Folder -> /mnt/d/Folder
        """
        if path_str is None:
            raise ValueError("Path cannot be None")

        raw_path = str(path_str).strip().strip('"').strip("'")

        if not raw_path:
            raise ValueError("Path cannot be empty")

        raw_path = os.path.expandvars(os.path.expanduser(raw_path))

        # Convert Windows path like D:\Folder or D:/Folder to WSL path /mnt/d/Folder
        windows_drive_match = re.match(r"^([A-Za-z]):[\\/](.*)$", raw_path)
        if windows_drive_match:
            drive = windows_drive_match.group(1).lower()
            rest = windows_drive_match.group(2).replace("\\", "/")
            raw_path = f"/mnt/{drive}/{rest}"
            logger.warning(f"Converted Windows path to WSL path: {raw_path}")

        # Common WSL typo: mnt/d/... should usually be /mnt/d/...
        if re.match(r"^mnt/[A-Za-z]/", raw_path):
            corrected_path = "/" + raw_path
            logger.warning(
                f"Path looks like a WSL mount path but is missing leading '/'. "
                f"Using '{corrected_path}' instead of '{raw_path}'."
            )
            raw_path = corrected_path

        return Path(raw_path).resolve()
    
    def read_preferences(self) -> Dict:
        """Delegate to preferences module."""
        return preferences.read_preferences()

    def write_preferences(self, prefs: Dict) -> None:
        """Delegate to preferences module."""
        preferences.write_preferences(prefs)

    # BATCH FILE LOADING
    @staticmethod
    def load_batch_urls_txt(file_path: Path) -> Tuple[List[str], str]:
        """
        Load URLs from .txt file.
        First line may contain params (format: "param: -a -q low -r 480p")
        Returns: (list of URLs, param_string or empty string)
        """
        urls = []
        params = ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            if not lines:
                return [], ""
            
            # Check if first line contains params
            first_line = lines[0].lower()
            if first_line.startswith("param:") or first_line.startswith("params:"):
                params = lines[0].split(":", 1)[1].strip()
                urls = lines[1:]
            else:
                urls = lines
            
            return urls, params
        except Exception as e:
            raise IOError(f"Error reading file {file_path}: {e}")

    @staticmethod
    def load_batch_urls_csv(file_path: Path, url_column: int = 0) -> Tuple[List[str], str]:
        """
        Load URLs from .csv file.
        First line may contain params (same format as .txt).
        url_column: which column contains the URL (default: 0).
        """
        urls = []
        params = ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            if not rows:
                return [], ""
            
            # Check if first line contains params
            first_row = rows[0][0].lower() if rows[0] else ""
            if first_row.startswith("param:") or first_row.startswith("params:"):
                params = rows[0][0].split(":", 1)[1].strip()
                rows = rows[1:]
            
            urls = [row[url_column].strip() for row in rows if len(row) > url_column]
            return urls, params
        except Exception as e:
            raise IOError(f"Error reading CSV file {file_path}: {e}")

    @staticmethod
    def load_batch_urls(file_path: Path, url_column: int = 0) -> Tuple[List[str], str]:
        """
        Auto-detect file format and load batch URLs.
        Returns: (list of URLs, param_string or empty string)
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        if suffix == ".txt":
            return OSInteractions.load_batch_urls_txt(file_path)
        elif suffix == ".csv":
            return OSInteractions.load_batch_urls_csv(file_path, url_column)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    @staticmethod
    def filter_valid_urls(urls: List[str]) -> Tuple[List[str], int]:
        """
        Filter out invalid/empty URLs from a list.
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            Tuple of (valid_urls, skipped_count)
        """
        valid_urls = []
        skipped_count = 0
        
        for idx, url in enumerate(urls, 1):
            if url and url.strip() and URLHandler.is_youtube_url(url):
                valid_urls.append(url)
            else:
                logger.warning(f"Skipping invalid/empty URL at line {idx}: '{url}'")
                skipped_count += 1
        
        return valid_urls, skipped_count

    @staticmethod
    def setup_playlist_dir(download_dir: Path, playlist_title: str, no_dir_date: bool) -> Path:
        """
        Set up the directory for the playlist download. Creates any missing directories.
        Returns the playlist directory path.
        """
        download_dir = Path(download_dir)
        date_prefix = datetime.today().strftime('%Y_%m_') if not no_dir_date else ""
        playlist_dir = download_dir / f"{date_prefix}{sanitize_filename(playlist_title)}"

        try:
            created_count = OSInteractions.create_directory(playlist_dir)
            if created_count:
                logger.info(f"Created playlist download directory: {playlist_dir} (created {created_count} levels)")
            else:
                logger.debug(f"Playlist directory already exists: {playlist_dir}")
            return playlist_dir
        except Exception as e:
            logger.error(f"Failed to create playlist directory {playlist_dir}: {e}")
            logger.debug("Unexpected error occurred while creating playlist directory %s", playlist_dir, exc_info=True)
            raise IOError(f"Failed to create playlist directory {playlist_dir}") from e

    #TODO: cleanup or delete a use 
        """
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            logger.info(f"Created download directory: {download_dir}")
        """
    @staticmethod
    def create_directory(dir_path: Path) -> int:
        """
        Create a directory and all missing parent directories.
        Returns the number of directory levels that were created (0 if none).
        """
        dir_path = Path(dir_path)
        # Find how many ancestor directories do not exist (count from the target up to the nearest existing ancestor)
        missing_count = 0
        p = dir_path
        # Use resolve(strict=False) to normalize path without requiring existence
        try:
            p = p.resolve(strict=False)
        except Exception:
            p = dir_path

        temp = p
        while not temp.exists():
            missing_count += 1
            if temp.parent == temp:
                # reached filesystem root
                break
            temp = temp.parent

        if missing_count == 0:
            logger.debug(f"Directory already exists, nothing to create: {dir_path}")
            return 0

        try:
            # Create all missing directories in one call
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created path: {dir_path} (created {missing_count} levels)")
            return missing_count
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            logger.debug("Unexpected error occurred while creating directory %s", dir_path, exc_info=True)
            raise IOError(f"Failed to create directory {dir_path}") from e

    # TODO: add method to append to batch results file instead of overwriting (for long-running batch processes)
    # Currently unused !
    @staticmethod
    def save_batch_results(results: List[Dict], output_path: Path) -> None:
        """
        Save batch download results to a CSV file.

        Args:
            results: List of dictionaries containing download results (e.g. video_title, video_url, success, errors).
            output_path: Path to the output CSV file.
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['video_title', 'video_url', 'success', 'errors']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for result in results:
                    writer.writerow(result)
            logger.info(f"Batch results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save batch results to {output_path}: {e}")
            logger.debug("Unexpected error occurred while saving batch results to %s", output_path, exc_info=True)
            raise IOError(f"Failed to save batch results to {output_path}") from e

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['video_title', 'video_url', 'success', 'errors']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)                    
                writer.writeheader()
                for result in results:
                    writer.writerow(result)
            logger.info(f"Batch results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save batch results to {output_path}: {e}")
            logger.debug("Unexpected error occurred while saving batch results to %s", output_path, exc_info=True)
            raise IOError(f"Failed to save batch results to {output_path}") from e

        # Optionally, you could return a success status or the output path
        return