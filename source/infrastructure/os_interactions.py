import os
import re
import logging
from pathlib import Path
import csv
from typing import Dict, List, Tuple
from datetime import datetime

from utility.logger import get_logger
import utility.preferences as preferences
from infrastructure.url_handler import URLHandler
from utility.utils import sanitize_filename, DownloadResult

logger = get_logger(__name__, 'os_interactions_debug.log')


class OSInteractions:
    """Filesystem and file I/O operations (preferences, batch files, paths)."""

    def __init__(self):
        self.prefs_path = preferences.PATH_TO_DEFAULT_PREFERENCES
        self.logs_path = preferences.PATH_TO_LOGS

    def expand_path(self, path_str: str | Path) -> Path:
        if path_str is None:
            raise ValueError("Path cannot be None")

        raw_path = str(path_str).strip().strip('"').strip("'")

        if not raw_path:
            raise ValueError("Path cannot be empty")

        raw_path = os.path.expandvars(os.path.expanduser(raw_path))

        windows_drive_match = re.match(r"^([A-Za-z]):[\\/](.*)$", raw_path)

        # Only convert D:\... to /mnt/d/... when running in a Unix/WSL-like environment.
        if windows_drive_match and os.name != "nt" and Path("/mnt").exists():
            drive = windows_drive_match.group(1).lower()
            rest = windows_drive_match.group(2).replace("\\", "/")
            raw_path = f"/mnt/{drive}/{rest}"
            logger.warning(f"Converted Windows path to WSL path: {raw_path}")

        if os.name != "nt" and re.match(r"^mnt/[A-Za-z]/", raw_path):
            corrected_path = "/" + raw_path
            logger.warning(
                f"Path looks like a WSL mount path but is missing leading '/'. "
                f"Using '{corrected_path}' instead of '{raw_path}'."
            )
            raw_path = corrected_path

        return Path(raw_path).resolve()
    
    def read_preferences(self, prefs_path: Path | None = None) -> Dict:
        """Delegate to preferences module."""
        return preferences.read_preferences(path=prefs_path)

    def write_preferences(self, prefs: Dict, prefs_path: Path | None = None) -> bool:
        """Delegate to preferences module."""
        return preferences.write_preferences(prefs, path=prefs_path)

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

    @staticmethod
    def create_directory(dir_path: Path) -> int:
        """
        Create a directory and all missing parent directories.
        Returns the number of directory levels that were created (0 if none).
        """
        dir_path = Path(dir_path)
        
        # Only count missing dirs when debug logging enabled
        missing_count = 0
        if logger.isEnabledFor(logging.DEBUG):
            temp = dir_path
            while not temp.exists():
                missing_count += 1
                if temp.parent == temp:
                    break
                temp = temp.parent
        
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Created path: {dir_path} (created {missing_count} levels)")
            return missing_count
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            raise IOError(f"Failed to create directory {dir_path}") from e

    @staticmethod
    def save_batch_results(results: List[DownloadResult], download_dir: str | Path, playlist_name: str) -> None:
        """
        Save batch download results to a CSV file.

        Args:
            results: Download results to save.
            download_dir: Directory where the batch results file will be saved.
            playlist_name: Name of the playlist for which to save results.
        """
        target_dir = Path(download_dir).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_playlist_name = sanitize_filename(playlist_name).strip() or "playlist"
        output_path = target_dir / (
            f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{safe_playlist_name}_results.csv"
        )

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['video_title', 'video_url', 'success', 'errors']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for result in results:
                    writer.writerow(
                        {
                            'video_title': result.video_title,
                            'video_url': result.video_url,
                            'success': result.success,
                            'errors': "; ".join(result.errors),
                        }
                    )
            logger.info(f"Batch results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save batch results to {output_path}: {e}")
            logger.debug("Unexpected error occurred while saving batch results to %s", output_path, exc_info=True)
            raise IOError(f"Failed to save batch results to {output_path}") from e

        # Optionally, you could return a success status or the output path
        return
