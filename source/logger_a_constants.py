import logging
import os
from pathlib import Path

# ---------- CONSTANTS FOR SETUP & RESTORE -------------------
# These reside here as the logger gets imported in multiple modules
# and ALWAYS gets invoked first

CURRENT_DIR = Path(__file__).resolve().parent  # → Python-YTRipper/source
PROJECT_ROOT = CURRENT_DIR.parent              # → Python-YTRipper
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

PATH_TO_LOGS = os.path.join(LOGS_DIR)
PATH_TO_PREFERENCES = os.path.join(CONFIG_DIR, "user_settings.json")

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
# -----------------------------

def get_logger(name: str, debug_logfile: str) -> logging.Logger:
    """
    Get a configured logger that logs DEBUG messages to a specific debug log file
    and INFO messages to a general log file.
    Args:
        name (str): Name of the logger.
        debug_logfile (str): Filename for the debug log file.
    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent adding handlers multiple times in case of repeated calls
    if getattr(logger, "_custom_handlers_added", False):
        return logger


    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s'
    )

    if not os.path.exists(PATH_TO_LOGS):
        os.makedirs(PATH_TO_LOGS)

    filehandler_specific = logging.FileHandler(f'{PATH_TO_LOGS}/{debug_logfile}')
    filehandler_specific.setLevel(logging.DEBUG)
    filehandler_specific.setFormatter(formatter)
    logger.addHandler(filehandler_specific)

    filehandler_general = logging.FileHandler(f'{PATH_TO_LOGS}/general.log')
    filehandler_general.setLevel(logging.INFO)
    filehandler_general.setFormatter(formatter)
    logger.addHandler(filehandler_general)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger._custom_handlers_added = True
    logger.debug("Logger initialized --------------------------------")
    return logger

# Usage in your modules:
# from logger import get_logger
# logger = get_logger(__name__, 'uh_debug.log')
# logger.debug("This goes to uh_debug.log and general.log")
# logger.info("This goes to general.log")

