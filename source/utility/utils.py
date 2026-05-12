from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Callable, Tuple, Type, Any, Dict
import time
import random
import re

# TODO currently has no logging; consider adding if needed

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

BOOLEAN_TRUE_VALUES = ("true", "yes", "y", "t", "1")
BOOLEAN_FALSE_VALUES = ("false", "no", "n", "f", "0")

FPS_ANY = 0
FPS_30 = 30
FPS_60 = 60

LOGLEVEL_ALIAS_MAP = {
    "CRITICAL": "CRITICAL", "CRIT": "CRITICAL", "C": "CRITICAL",
    "ERROR": "ERROR", "ERR": "ERROR", "E": "ERROR",
    "WARNING": "WARNING", "WARN": "WARNING", "W": "WARNING",
    "INFO": "INFO", "INFORMATION": "INFO", "I": "INFO",
    "DEBUG": "DEBUG", "DBG": "DEBUG", "D": "DEBUG",
}


def parse_bool_string(value: Any) -> bool:
    """Parse a boolean value from string or bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in BOOLEAN_TRUE_VALUES:
            return True
        if normalized in BOOLEAN_FALSE_VALUES:
            return False
    return bool(value)


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


@dataclass
class DownloadOptions:
    """Centralized download preferences (mirrors preferences.py DEFAULT_PREFS)."""
    current_preset: str = "default"
    default_download_directory: str = "~/Downloads/RipperDownloads"
    audio_only: bool = False
    audio_mp3: bool = False
    show_preset: bool = False
    preferred_audio_quality: str = ""
    preferred_video_quality: str = ""
    preferred_resolution: str = ""
    preferred_abr: str = ""
    preferred_format: str = ""
    preferred_fps: int = 0
    visible_loglevel: str = "INFO"
    donotconvert: bool = False
    no_dir_date: bool = False
    autotag: bool = True
    save_results: bool = False

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
    # Optional future field. Keeping it optional avoids forcing every caller to set it now.
    output_path: Path | None = None

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        if self.success:
            return f"{status} {self.video_title}"
        error_msg = "; ".join(self.errors) if self.errors else "Unknown error"
        return f"{status} {self.video_title}: {error_msg}"


@dataclass
class StreamInfo:
    """
    Neutral stream metadata used by MediaAssembler.

    This deliberately does not expose pytubefix.Stream to StreamConverter, so the
    conversion layer can be tested without pytubefix/network objects.
    """

    path: Path
    codec: str | None = None
    bitrate: str | int | None = None
    mime_type: str | None = None
    container: str | None = None
    resolution: str | None = None
    fps: int | None = None
    includes_audio: bool = False
    includes_video: bool = False
    codecs: list[str] = field(default_factory=list)

    @classmethod
    def from_pytubefix_stream(cls, stream: Any, path: Path) -> "StreamInfo":
        """Create neutral metadata from a pytubefix Stream-like object."""
        codecs = _coerce_codecs(getattr(stream, "codecs", None))
        mime_type = getattr(stream, "mime_type", None)
        includes_audio = bool(getattr(stream, "includes_audio_track", False))
        includes_video = bool(getattr(stream, "includes_video_track", False))

        audio_codec = getattr(stream, "audio_codec", None)
        video_codec = getattr(stream, "video_codec", None)

        if includes_video and video_codec:
            codec = video_codec
        elif includes_audio and audio_codec:
            codec = audio_codec
        elif codecs:
            codec = codecs[0]
        else:
            codec = None

        bitrate = getattr(stream, "abr", None) or getattr(stream, "bitrate", None)
        container = mime_type.split("/", 1)[1] if isinstance(mime_type, str) and "/" in mime_type else None

        return cls(
            path=Path(path),
            codec=codec,
            bitrate=bitrate,
            mime_type=mime_type,
            container=container,
            resolution=getattr(stream, "resolution", None),
            fps=getattr(stream, "fps", None),
            includes_audio=includes_audio,
            includes_video=includes_video,
            codecs=codecs,
        )


@dataclass
class OutputProfile:
    """The target artifact MediaAssembler wants StreamConverter to create."""

    extension: str
    container: str
    audio_codec: str | None = None
    video_codec: str | None = None
    audio_bitrate: str | None = None
    video_bitrate: str | None = None


def _coerce_codecs(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()] if str(value).strip() else []


def retry_call(
    callable_fn: Callable[[], Any],
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    retries: int = 3,
    backoff: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: float = 0.25,
    logger=None,
) -> Any:
    """Inline retry helper for callables."""
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
                    "Transient error attempt %d/%d: %s — retrying in %.2fs",
                    attempt,
                    retries + 1,
                    e,
                    delay,
                )
            time.sleep(delay + random.uniform(0, jitter))
            attempts_left -= 1
            delay *= backoff_factor
            attempt += 1


def sanitize_filename(title: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", title)
