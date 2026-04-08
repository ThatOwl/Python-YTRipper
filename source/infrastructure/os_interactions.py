import os
from pathlib import Path
import shutil
import csv
from typing import Dict, List, Tuple

from source.infrastructure.logger import get_logger
import source.infrastructure.preferences as preferences
from source.components.url_handler import URLHandler

logger = get_logger(__name__, 'osi_debug.log')


class OSInteractions:
    """Filesystem and file I/O operations (preferences, batch files, paths)."""

    def __init__(self):
        self.prefs_path = preferences.PATH_TO_PREFERENCES
        self.logs_path = preferences.PATH_TO_LOGS

    def expand_path(self, path_str: str) -> Path:
        """Expand ~ and environment variables."""
        return Path(os.path.expandvars(os.path.expanduser(path_str))).resolve()

    def read_preferences(self) -> Dict:
        """Delegate to preferences module."""
        return preferences.read_preferences()

    def write_preferences(self, prefs: Dict) -> None:
        """Delegate to preferences module."""
        preferences.write_preferences(prefs)

    def clear_directory(self, dir_path: Path) -> None:
        """...existing code..."""
        pass

    def clear_logs(self) -> None:
        """...existing code..."""
        pass

    # BATCH FILE LOADING
    def load_batch_urls_txt(self, file_path: Path) -> Tuple[List[str], str]:
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

    def load_batch_urls_csv(self, file_path: Path, url_column: int = 0) -> Tuple[List[str], str]:
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

    def load_batch_urls(self, file_path: Path, url_column: int = 0) -> Tuple[List[str], str]:
        """
        Auto-detect file format and load batch URLs.
        Returns: (list of URLs, param_string or empty string)
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        if suffix == ".txt":
            return self.load_batch_urls_txt(file_path)
        elif suffix == ".csv":
            return self.load_batch_urls_csv(file_path, url_column)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    def filter_valid_urls(self, urls: List[str]) -> Tuple[List[str], int]:
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