from asyncio.log import logger
import logging
import sys
import os
from typing import Optional, Dict

# Delegated constants / preference loading
import utility.preferences as preferences

VISIBLE_HANDLER_KINDS = {"console", "gui"}

def _load_preferences() -> Dict:
    """
    Delegate preference loading to source.preferences (single source of truth).
    """
    try:
        return preferences.read_preferences()
    except Exception:
        return {}


class _NoTracebackFormatter(logging.Formatter):
    """
    Formatter for console output that suppresses exception tracebacks.
    """
    def formatException(self, ei):
        # suppress traceback in console output
        return ""


def get_logger(name: str, logfile: Optional[str] = None, prefs: Optional[Dict] = None) -> logging.Logger:
    """
    Create/return a module logger configured with:
      - console handler level taken from preferences (or INFO by default)
      - file handler at DEBUG (if logfile provided) placed under preferences.LOGS_DIR
      - console formatter that suppresses tracebacks
      - file formatter that includes timestamps and full tracebacks
    """
    prefs = prefs or _load_preferences()
    level_name = (
        prefs.get("visible_loglevel")
        or prefs.get("loglevel")  # backward compatibility
        or "WARNING"
    ).upper()
    try:
        console_level = getattr(logging, level_name)
    except Exception:
        console_level = logging.INFO

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # let handlers filter
    for h in list(logger.handlers):
        logger.removeHandler(h)

    # Console handler (no tracebacks)
    console_fmt = "%(levelname)s - %(message)s"
    console_formatter = _NoTracebackFormatter(console_fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.yt_ripper_kind = "console" # custom attribute to identify console handlers for log level adjustments
    ch.setLevel(console_level)
    ch.setFormatter(console_formatter)
    logger.addHandler(ch)

    # File handler (always DEBUG) with timestamp and module.func context
    if logfile:
        try:
            logs_dir = preferences.LOGS_DIR
            os.makedirs(logs_dir, exist_ok=True)
            if os.path.isabs(logfile):
                logfile_path = logfile
            else:
                logfile_path = os.path.join(logs_dir, logfile)
            file_fmt = "%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s"
            fh = logging.FileHandler(logfile_path, encoding="utf-8")
            fh.yt_ripper_kind = "file" # custom attribute to identify file handlers for log level adjustments
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter(file_fmt))
            logger.addHandler(fh)
        except Exception:
            logger.warning("Failed to create file handler for logger %s (file: %s)", name, logfile)
    logger.debug("Logger initialized --------------------------------")
    logger.propagate = False
    return logger

def set_visible_log_level(level_name: str) -> None:
    level_name = level_name.upper()

    try:
        level = getattr(logging, level_name)
    except AttributeError:
        raise ValueError(f"Invalid log level: {level_name}")

    for logger_obj in logging.Logger.manager.loggerDict.values():
        if not isinstance(logger_obj, logging.Logger):
            continue

        for handler in logger_obj.handlers:
            if getattr(handler, "yt_ripper_kind", None) in VISIBLE_HANDLER_KINDS:
                handler.setLevel(level)