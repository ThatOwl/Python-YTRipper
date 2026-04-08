
import os
from source.infrastructure.logger import get_logger
from source.domain.pytube_interface import YouTubeDownloader as YTD
from source.infrastructure.os_interactions import OSInteractions

logger = get_logger(__name__, 'cli_debug.log')
class CLIBase:
    def __init__(self):
        self.os = OSInteractions()
        self.preferences = self.os.read_preferences()  # initial load
        # downloader gets os handler injected
        self.ytd = YTD(os_handler=self.os)
    
    def clear_dialog(self, dir_path: os.PathLike) -> None:
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
    
    