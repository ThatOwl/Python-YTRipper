# Pattern 2: Dataclass Registry (RECOMMENDED)
# Type-safe, extensible, production-ready

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from pathlib import Path


class CodecFamily(Enum):
    """Classification of codec type"""
    AUDIO = "audio"
    VIDEO = "video"


@dataclass
class FFMpegArg:
    """
    Single FFMPEG command-line argument with optional value.
    Ensures proper splitting of flags and values.
    """
    flag: str
    value: Optional[str] = None
    
    def to_args(self) -> List[str]:
        """Convert to command-line argument list"""
        return [self.flag] if self.value is None else [self.flag, self.value]
    
    def __repr__(self) -> str:
        return f"{self.flag}" if self.value is None else f"{self.flag} {self.value}"


@dataclass
class CodecProfile:
    """
    Comprehensive codec configuration defining how to encode/transcode media.
    
    Attributes:
        name: User-facing format name (e.g., "mp3", "opus", "h265")
        codec_family: AUDIO or VIDEO
        codec: Internal codec identifier (for documentation/validation)
        container: Output container format
        output_ext: File extension (e.g., ".mp3", ".mkv")
        base_args: List of FFMPEG arguments (flags + values)
        supported_bitrates: List of valid bitrates, or None for variable/lossless
        description: Human-readable format description
        preset_quality: Encoding preset (fast/medium/slow) for lossy formats
    """
    name: str
    codec_family: CodecFamily
    codec: str
    container: str
    output_ext: str
    base_args: List[FFMpegArg]
    description: str = ""
    supported_bitrates: Optional[List[str]] = None
    preset_quality: str = "medium"
    
    def build_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        bitrate: Optional[str] = None
    ) -> List[str]:
        """
        Build complete FFMPEG command for this codec profile.
        
        Args:
            input_path: Path to input media file
            output_path: Path to output media file
            bitrate: Optional bitrate (validated against supported_bitrates)
        
        Returns:
            Complete command as list of strings ready for subprocess
        
        Raises:
            ValueError: If bitrate is not in supported list
        """
        cmd = ["ffmpeg", "-i", input_path]
        
        # Add base codec arguments
        for arg in self.base_args:
            cmd.extend(arg.to_args())
        
        # Add bitrate if provided and supported
        if bitrate:
            if not self.is_bitrate_supported(bitrate):
                raise ValueError(
                    f"Bitrate {bitrate} not supported for {self.name}. "
                    f"Supported: {self.supported_bitrates}"
                )
            # Audio bitrate: -b:a, Video bitrate: -b:v
            bitrate_flag = "-b:a" if self.codec_family == CodecFamily.AUDIO else "-b:v"
            cmd.extend([bitrate_flag, bitrate])
        
        cmd.append(output_path)
        return cmd
    
    def is_bitrate_supported(self, bitrate: str) -> bool:
        """Check if bitrate is in supported list (or all bitrates supported if None)"""
        if self.supported_bitrates is None:
            return True  # Lossless or variable bitrate
        return bitrate in self.supported_bitrates
    
    def __str__(self) -> str:
        bitrates_str = (
            f" | Bitrates: {', '.join(self.supported_bitrates)}"
            if self.supported_bitrates
            else " | Lossless/Variable Bitrate"
        )
        return f"{self.name}: {self.description}{bitrates_str}"


class CodecRegistry:
    """
    Central registry for all supported codec profiles.
    Provides discovery, validation, and access to codec configurations.
    
    Usage:
        CodecRegistry.register(mp3_profile)
        profile = CodecRegistry.get("mp3")
        all_audio = CodecRegistry.list_audio_formats()
    """
    _profiles: Dict[str, CodecProfile] = {}
    
    @classmethod
    def register(cls, profile: CodecProfile) -> None:
        """Register a new codec profile"""
        if profile.name in cls._profiles:
            raise ValueError(f"Profile '{profile.name}' already registered")
        cls._profiles[profile.name] = profile
    
    @classmethod
    def get(cls, name: str) -> CodecProfile:
        """
        Get codec profile by name.
        
        Raises:
            ValueError: If profile not found
        """
        if name not in cls._profiles:
            raise ValueError(
                f"Codec '{name}' not registered. Available: {cls.list_all()}"
            )
        return cls._profiles[name]
    
    @classmethod
    def list_audio_formats(cls) -> List[str]:
        """List names of all registered audio formats"""
        return [
            k for k, v in cls._profiles.items()
            if v.codec_family == CodecFamily.AUDIO
        ]
    
    @classmethod
    def list_video_formats(cls) -> List[str]:
        """List names of all registered video formats"""
        return [
            k for k, v in cls._profiles.items()
            if v.codec_family == CodecFamily.VIDEO
        ]
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered format names"""
        return list(cls._profiles.keys())
    
    @classmethod
    def get_profiles_by_family(cls, family: CodecFamily) -> Dict[str, CodecProfile]:
        """Get all profiles of a specific family"""
        return {
            k: v for k, v in cls._profiles.items()
            if v.codec_family == family
        }
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registrations (useful for testing)"""
        cls._profiles.clear()


# ============================================================
# BUILT-IN PROFILE INITIALIZATION
# ============================================================

def initialize_default_profiles() -> None:
    """Register standard codec profiles"""
    
    # MP3
    CodecRegistry.register(CodecProfile(
        name="mp3",
        codec_family=CodecFamily.AUDIO,
        codec="libmp3lame",
        container="mp3",
        output_ext=".mp3",
        base_args=[
            FFMpegArg("-acodec", "libmp3lame"),
            FFMpegArg("-q:a", "2"),
        ],
        supported_bitrates=["64k", "96k", "128k", "192k", "256k", "320k"],
        description="MP3 Audio (Lossy, Wide Compatibility)"
    ))
    
    # AAC (M4A)
    CodecRegistry.register(CodecProfile(
        name="aac",
        codec_family=CodecFamily.AUDIO,
        codec="aac",
        container="m4a",
        output_ext=".m4a",
        base_args=[
            FFMpegArg("-acodec", "aac"),
        ],
        supported_bitrates=["64k", "96k", "128k", "192k", "256k"],
        description="AAC Audio (M4A, Apple Compatible)"
    ))
    
    # Opus
    CodecRegistry.register(CodecProfile(
        name="opus",
        codec_family=CodecFamily.AUDIO,
        codec="libopus",
        container="opus",
        output_ext=".opus",
        base_args=[
            FFMpegArg("-acodec", "libopus"),
        ],
        supported_bitrates=["64k", "96k", "128k", "192k", "256k"],
        description="Opus Audio (Modern, High Quality at Low Bitrate)"
    ))
    
    # Vorbis
    CodecRegistry.register(CodecProfile(
        name="vorbis",
        codec_family=CodecFamily.AUDIO,
        codec="libvorbis",
        container="ogg",
        output_ext=".ogg",
        base_args=[
            FFMpegArg("-acodec", "libvorbis"),
            FFMpegArg("-q:a", "6"),
        ],
        supported_bitrates=["128k", "192k", "256k", "320k"],
        description="Vorbis Audio (OGG, Open Format)"
    ))
    
    # FLAC (Lossless)
    CodecRegistry.register(CodecProfile(
        name="flac",
        codec_family=CodecFamily.AUDIO,
        codec="flac",
        container="flac",
        output_ext=".flac",
        base_args=[
            FFMpegArg("-acodec", "flac"),
        ],
        supported_bitrates=None,  # Lossless
        description="FLAC Audio (Lossless)"
    ))
    
    # H.264 Video
    CodecRegistry.register(CodecProfile(
        name="h264",
        codec_family=CodecFamily.VIDEO,
        codec="h264",
        container="mp4",
        output_ext=".mp4",
        base_args=[
            FFMpegArg("-vcodec", "libx264"),
            FFMpegArg("-preset", "medium"),
            FFMpegArg("-crf", "23"),
        ],
        supported_bitrates=None,
        description="H.264 Video (MP4, High Compatibility)"
    ))
    
    # H.265 Video
    CodecRegistry.register(CodecProfile(
        name="h265",
        codec_family=CodecFamily.VIDEO,
        codec="h265",
        container="mkv",
        output_ext=".mkv",
        base_args=[
            FFMpegArg("-vcodec", "libx265"),
            FFMpegArg("-preset", "medium"),
            FFMpegArg("-crf", "23"),
        ],
        supported_bitrates=None,
        description="H.265 Video (HEVC, Better Compression)"
    ))
    
    # VP9 Video
    CodecRegistry.register(CodecProfile(
        name="vp9",
        codec_family=CodecFamily.VIDEO,
        codec="vp9",
        container="webm",
        output_ext=".webm",
        base_args=[
            FFMpegArg("-vcodec", "libvpx-vp9"),
            FFMpegArg("-cpu-used", "4"),
            FFMpegArg("-crf", "30"),
        ],
        supported_bitrates=None,
        description="VP9 Video (WebM, Web Friendly)"
    ))


# Initialize on module import
if not CodecRegistry.list_all():
    initialize_default_profiles()


# ============================================================
# INTEGRATION PATTERNS
# ============================================================

"""
PATTERN 2A: In stream_converter.py
=====================================================

from infrastructure.codec_registry import CodecRegistry

def convert_audio(self, audio_path: Path, target_format: str, bitrate: str) -> Path:
    '''Convert audio to target format using registry'''
    profile = CodecRegistry.get(target_format)
    output_path = audio_path.with_suffix(profile.output_ext)
    
    cmd = profile.build_ffmpeg_command(str(audio_path), str(output_path), bitrate)
    
    logger.debug(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path


PATTERN 2B: In DownloadOptions (utility/preferences.py)
=====================================================

from dataclasses import dataclass, field
from infrastructure.codec_registry import CodecRegistry

@dataclass
class DownloadOptions:
    # ... existing fields ...
    output_format: str = "mp3"              # ADD THIS
    target_bitrate: str = "192k"            # ADD THIS
    
    def validate_format(self) -> bool:
        '''Validate that output format is registered'''
        try:
            CodecRegistry.get(self.output_format)
            return True
        except ValueError:
            logger.error(f"Invalid format: {self.output_format}")
            return False


PATTERN 2C: In CLI (cli/cli_command.py)
=====================================================

from infrastructure.codec_registry import CodecRegistry

class CLICommand:
    def _setup_parser(self):
        # ... existing setup ...
        
        fmt_group = parser.add_argument_group("Output Format Options")
        fmt_group.add_argument(
            "--output-format",
            choices=CodecRegistry.list_all(),
            default="mp3",
            help="Output format for conversion"
        )
        fmt_group.add_argument(
            "--bitrate",
            default="192k",
            help="Target bitrate (format-specific)"
        )
        fmt_group.add_argument(
            "--list-formats",
            action="store_true",
            help="Show all available formats and exit"
        )
    
    def run(self, command: str) -> int:
        args = self._parser.parse_args()
        
        if args.list_formats:
            self._print_available_formats()
            return 0
        
        # ... rest of implementation ...
    
    @staticmethod
    def _print_available_formats():
        print("\\nAvailable Audio Formats:")
        for fmt in CodecRegistry.list_audio_formats():
            profile = CodecRegistry.get(fmt)
            print(f"  {profile}")
        
        print("\\nAvailable Video Formats:")
        for fmt in CodecRegistry.list_video_formats():
            profile = CodecRegistry.get(fmt)
            print(f"  {profile}")
"""
