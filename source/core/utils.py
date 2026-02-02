from dataclasses import dataclass, asdict
from typing import List, Callable, Tuple, Type, Any, Dict
import time
import random

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


# Domain exceptions / base
class DownloadError(Exception):
    """Base exception for download-related errors."""

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
    preferred_mime: str = ""
    preferred_format: str = ""
    loglevel: str = "WARNING"
    donotconvert: bool = False

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