
import os
from utility.logger import get_logger
from application.download_orchestrator import DownloadOrchestrator as YTD
from infrastructure.os_interactions import OSInteractions

logger = get_logger(__name__, 'cli_base_debug.log')
class CLIBase:
    def __init__(self):
        self.os = OSInteractions()
        self.preferences = self.os.read_preferences()  # initial load
        # downloader gets os handler injected
        self.ytd = YTD(os_handler=self.os)
    
    