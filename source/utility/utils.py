from dataclasses import dataclass, asdict
import logging
from typing import List, Callable, Tuple, Type, Any, Dict
import time
import random
import re

#TODO currently has no logging; consider adding if needed

QUALITY_ALIAS_MAP = {
    # high / best
    "high": "high", "h": "high", "best": "high", "b": "high",
    # medium
    "medium": "medium", "m": "medium", "mid": "medium", "average": "medium", "a": "medium",
    # low / worst
    "low": "low", "lowest": "low", "l": "low", "worst": "low", "w": "low",
}

# Common YouTube audio bitrates (kbps)
COMMON_AUDIO_ABR = {
    "48k": "48kbps",
    "50k": "50kbps",
    "56k": "56kbps",
    "64k": "64kbps",
    "96k": "96kbps",
    "128k": "128kbps",
    "192k": "192kbps",
    "256k": "256kbps",
    "320k": "320kbps",
}

# Common YouTube video resolutions
COMMON_VIDEO_RESOLUTIONS = {
    "144p": "144p",
    "240p": "240p",
    "360p": "360p",
    "480p": "480p",
    "720p": "720p",
    "1080p": "1080p",
    "1440p": "1440p",
    "2160p": "2160p",  # 4K
}

# Boolean string parsing constants
BOOLEAN_TRUE_VALUES = ('true', '1', 'yes', 'y', 't')
BOOLEAN_FALSE_VALUES = ('false', '0', 'no', 'n', 'f')

# FPS preference constants
FPS_ANY = 0      # Accept any FPS
FPS_30 = 30      # Prefer 30 FPS (lower bandwidth, older devices)
FPS_60 = 60      # Prefer 60 FPS (smooth motion, higher bandwidth)

LOGLEVEL_ALIAS_MAP = {
    "CRITICAL": "CRITICAL", "CRIT": "CRITICAL", "C": "CRITICAL",
    "ERROR": "ERROR", "ERR": "ERROR", "E": "ERROR",
    "WARNING": "WARNING", "WARN": "WARNING", "W": "WARNING",
    "INFO": "INFO", "INFORMATION": "INFO", "I": "INFO",
    "DEBUG": "DEBUG", "DBG": "DEBUG", "D": "DEBUG",
    # Add more aliases as needed
}
def parse_bool_string(value: Any) -> bool:
    """Parse a boolean value from string or bool.
    
    Args:
        value: String ('true'/'false'/'yes'/'no'/'1'/'0'/'y'/'n') or bool
        
    Returns:
        bool: Parsed boolean value
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in BOOLEAN_TRUE_VALUES
    return bool(value)


# Domain exceptions / base
#TODO: might want to split this or adapt some specific behaviour
# downloader-specific subclasses (keep here for module-local semantics)
# TODO: improve exception hierarchy if needed and add more specific exceptions

class DownloadError(Exception):
    """Base exception for download-related errors."""
class VideoFetchError(DownloadError):
    pass

class PlaylistFetchError(DownloadError):
    pass

class StreamSelectionError(DownloadError):
    pass

class StreamDownloadError(DownloadError):
    pass

class ConversionError(DownloadError):
    pass

class CombineError(DownloadError):
    pass

# Models / result objects

@dataclass
class DownloadOptions:
    """Centralized download preferences (mirrors preferences.py DEFAULT_PREFS)."""
    default_download_directory: str = "~/Downloads"
    audio_only: bool = False
    audio_mp3: bool = False
    warn_me: bool = False
    preferred_audio_quality: str = ""
    preferred_video_quality: str = ""
    preferred_resolution: str = ""
    preferred_abr: str = ""
    #preferred_mime: str = ""
    preferred_format: str = ""
    preferred_fps: int = 0  # 0=any, 30=prefer 30fps, 60=prefer 60fps
    visible_loglevel: str = "INFO"
    #ui_loglevel:Str = "WARNING"
    donotconvert: bool = False
    no_dir_date: bool = False
    autotag: bool = True  # If True, attempt to auto-tag downloaded files with metadata
    

    @classmethod
    def from_preferences(cls, prefs: Dict) -> "DownloadOptions":
        """Load from preferences dict."""
        return cls(**{k: v for k, v in prefs.items() if k in cls.__dataclass_fields__})
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def update_from_dict(self, data: Dict) -> None:
        """Update options from dictionary (only non-None values)."""
        for key, value in data.items():
            if value is not None and hasattr(self, key):
                setattr(self, key, value)

@dataclass
class DownloadResult:
    success: bool
    errors: List[str]
    video_title: str = ""
    video_url: str = ""
    
    def __str__(self) -> str:
        """String representation for display."""
        status = "✓" if self.success else "✗"
        if self.success:
            return f"{status} {self.video_title}"
        else:
            error_msg = "; ".join(self.errors) if self.errors else "Unknown error"
            return f"{status} {self.video_title}: {error_msg}"

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

def sanitize_filename(title: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", title)