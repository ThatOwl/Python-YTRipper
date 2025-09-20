import logging
import os


def get_logger(name: str, debug_logfile: str):
    """
    Returns a logger instance that writes DEBUG logs to a specific file
    and INFO+ logs to a general log file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent adding handlers multiple times in case of repeated calls
    if getattr(logger, "_custom_handlers_added", False):
        return logger


    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s'
    )
    
    if not os.path.exists('./logs'):
        os.makedirs('./logs')

    filehandler_specific = logging.FileHandler(f'./logs/{debug_logfile}')
    filehandler_specific.setLevel(logging.DEBUG)
    filehandler_specific.setFormatter(formatter)

    filehandler_general = logging.FileHandler('./logs/general.log')
    filehandler_general.setLevel(logging.INFO)
    filehandler_general.setFormatter(formatter)

    logger.addHandler(filehandler_specific)
    logger.addHandler(filehandler_general)

    logger._custom_handlers_added = True
    return logger

# Usage in your modules:
# from logger import get_logger
# logger = get_logger(__name__, 'uh_debug.log')
# logger.debug("This goes to uh_debug.log and general.log")
# logger.info("This goes to general.log")
