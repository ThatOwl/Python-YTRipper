# Pattern 5: Plugin System
# Most extensible approach for third-party codec support

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Any
import subprocess
import importlib.util
import logging

logger = logging.getLogger(__name__)


# ============================================================
# PLUGIN INTERFACE
# ============================================================

class CodecPlugin(ABC):
    """
    Abstract base class for codec plugins.
    
    Plugins register themselves with the codec registry and provide:
    - Profile definition (codec, bitrates, args)
    - Environment validation (is codec available on system?)
    - Custom encoding presets (quality tradeoffs)
    """
    
    @abstractmethod
    def get_profile(self) -> 'CodecProfile':
        """
        Return the CodecProfile for this plugin.
        
        Returns:
            CodecProfile with codec metadata and FFMPEG args
        """
        pass
    
    @abstractmethod
    def validate_environment(self) -> bool:
        """
        Check if required codec/tools are available in system environment.
        
        Should test:
        - FFMPEG is installed and accessible
        - Codec library is available (ffmpeg -codecs | grep <codec>)
        - Any external dependencies
        
        Returns:
            True if environment is ready, False otherwise
        """
        pass
    
    @abstractmethod
    def get_preset_options(self) -> Dict[str, Any]:
        """
        Return encoding presets for this codec.
        
        Example return value:
        {
            "speed": ["fast", "medium", "slow"],
            "quality": [0, 5, 10],
            "description": "Choose between speed and quality"
        }
        
        Returns:
            Dict mapping preset names to lists of options
        """
        pass
    
    def get_metadata(self) -> Dict[str, str]:
        """
        Return plugin metadata (optional override).
        
        Returns:
            Dict with "name", "version", "author" keys
        """
        return {
            "name": self.__class__.__name__,
            "version": "1.0.0",
            "author": "Unknown",
        }
    
    def on_before_encode(self, input_path: Path) -> bool:
        """
        Hook called before encoding starts (optional override).
        
        Use for pre-processing, validation, or logging.
        
        Args:
            input_path: Input media file path
        
        Returns:
            True to proceed, False to abort
        """
        return True
    
    def on_after_encode(self, output_path: Path) -> bool:
        """
        Hook called after encoding completes (optional override).
        
        Use for post-processing or validation.
        
        Args:
            output_path: Output media file path
        
        Returns:
            True if successful, False if validation failed
        """
        return True


# ============================================================
# BUILT-IN PLUGINS
# ============================================================

class MP3Plugin(CodecPlugin):
    """MP3 audio codec plugin"""
    
    def get_profile(self) -> 'CodecProfile':
        from infrastructure.codec_registry import CodecProfile, CodecFamily, FFMpegArg
        
        return CodecProfile(
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
        )
    
    def validate_environment(self) -> bool:
        try:
            result = subprocess.run(
                ["ffmpeg", "-codecs"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "libmp3lame" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_preset_options(self) -> Dict[str, Any]:
        return {
            "bitrate_presets": {
                "low": "64k",
                "medium": "192k",
                "high": "320k",
            }
        }


class OpusPlugin(CodecPlugin):
    """Opus audio codec plugin"""
    
    def get_profile(self) -> 'CodecProfile':
        from infrastructure.codec_registry import CodecProfile, CodecFamily, FFMpegArg
        
        return CodecProfile(
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
        )
    
    def validate_environment(self) -> bool:
        try:
            result = subprocess.run(
                ["ffmpeg", "-codecs"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "libopus" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_preset_options(self) -> Dict[str, Any]:
        return {
            "application": ["voip", "audio", "lowdelay"],
            "compression_level": [0, 5, 10],
        }


class H264Plugin(CodecPlugin):
    """H.264 video codec plugin"""
    
    def get_profile(self) -> 'CodecProfile':
        from infrastructure.codec_registry import CodecProfile, CodecFamily, FFMpegArg
        
        return CodecProfile(
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
        )
    
    def validate_environment(self) -> bool:
        try:
            result = subprocess.run(
                ["ffmpeg", "-codecs"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "libx264" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def get_preset_options(self) -> Dict[str, Any]:
        return {
            "preset": ["ultrafast", "fast", "medium", "slow", "veryslow"],
            "quality": [0, 15, 23, 32, 51],  # CRF values
        }


# ============================================================
# PLUGIN REGISTRY
# ============================================================

class PluginRegistry:
    """
    Central registry for codec plugins.
    
    Handles:
    - Plugin registration and discovery
    - Environment validation
    - Integration with CodecRegistry
    - Dynamic plugin loading from files
    """
    
    _plugins: Dict[str, CodecPlugin] = {}
    _loaded: bool = False
    
    @classmethod
    def register(cls, plugin: CodecPlugin) -> bool:
        """
        Register a plugin and validate environment.
        
        Args:
            plugin: CodecPlugin instance
        
        Returns:
            True if registered successfully, False if validation failed
        """
        if not plugin.validate_environment():
            logger.warning(
                f"Plugin {plugin.__class__.__name__} failed environment validation. "
                f"Codec may not be available."
            )
            return False
        
        profile = plugin.get_profile()
        cls._plugins[profile.name] = plugin
        
        # Register profile with codec registry
        from infrastructure.codec_registry import CodecRegistry
        CodecRegistry.register(profile)
        
        logger.info(f"Registered plugin: {profile.name}")
        return True
    
    @classmethod
    def get(cls, name: str) -> Optional[CodecPlugin]:
        """Get plugin by format name"""
        return cls._plugins.get(name)
    
    @classmethod
    def list_plugins(cls) -> List[str]:
        """List all loaded plugin names"""
        return list(cls._plugins.keys())
    
    @classmethod
    def load_all(cls) -> None:
        """
        Load and register all built-in plugins.
        
        Call once at application startup.
        """
        if cls._loaded:
            return
        
        # Register built-in plugins
        cls.register(MP3Plugin())
        cls.register(OpusPlugin())
        cls.register(H264Plugin())
        
        # Load external plugins from plugins/ directory
        cls._load_external_plugins()
        
        cls._loaded = True
        logger.info(f"Loaded {len(cls._plugins)} codec plugins")
    
    @classmethod
    def _load_external_plugins(cls, plugin_dir: str = "infrastructure/plugins") -> None:
        """
        Dynamically discover and load plugins from directory.
        
        Plugin files should:
        - Be named *_plugin.py
        - Contain class ending in "Plugin" inheriting from CodecPlugin
        - Be importable from plugin_dir
        
        Args:
            plugin_dir: Path to plugins directory
        """
        plugin_path = Path(plugin_dir)
        
        if not plugin_path.exists():
            logger.debug(f"Plugin directory not found: {plugin_dir}")
            return
        
        for plugin_file in sorted(plugin_path.glob("*_plugin.py")):
            try:
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem,
                    plugin_file
                )
                if not spec or not spec.loader:
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find CodecPlugin subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, CodecPlugin) and
                        attr is not CodecPlugin):
                        
                        try:
                            plugin_instance = attr()
                            cls.register(plugin_instance)
                        except Exception as e:
                            logger.error(
                                f"Failed to instantiate plugin {attr_name}: {e}"
                            )
                
            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_file}: {e}")


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_plugins() -> None:
    """Initialize all plugins at application startup"""
    PluginRegistry.load_all()


# ============================================================
# INTEGRATION PATTERN
# ============================================================

"""
PATTERN 5A: Application Startup
=====================================================

# In yt_ripper.py or main entry point:

from infrastructure.codec_plugins import initialize_plugins

def main():
    initialize_plugins()  # Load all codec plugins
    
    # Now CodecRegistry has all profiles, PluginRegistry has all plugins
    # Rest of application continues normally...
    cli = CLICommand()
    return cli.run()


PATTERN 5B: Creating Custom Plugins
=====================================================

Create file: infrastructure/plugins/flac_plugin.py

from infrastructure.codec_plugins import CodecPlugin
from infrastructure.codec_registry import CodecProfile, CodecFamily, FFMpegArg

class FLACPlugin(CodecPlugin):
    def get_profile(self) -> CodecProfile:
        return CodecProfile(
            name="flac",
            codec_family=CodecFamily.AUDIO,
            codec="flac",
            container="flac",
            output_ext=".flac",
            base_args=[FFMpegArg("-acodec", "flac")],
            supported_bitrates=None,
            description="FLAC Audio (Lossless)"
        )
    
    def validate_environment(self) -> bool:
        # Check if ffmpeg has FLAC support
        import subprocess
        try:
            result = subprocess.run(
                ["ffmpeg", "-codecs"],
                capture_output=True,
                text=True
            )
            return "flac" in result.stdout
        except FileNotFoundError:
            return False
    
    def get_preset_options(self) -> dict:
        return {"compression_level": [0, 5, 8, 12]}
    
    def on_before_encode(self, input_path) -> bool:
        # Custom validation before encoding
        logger.info(f"Starting FLAC encoding of {input_path}")
        return True
    
    def on_after_encode(self, output_path) -> bool:
        # Custom validation after encoding
        if output_path.stat().st_size == 0:
            return False
        return True


PATTERN 5C: Using Plugins in StreamConverter
=====================================================

class StreamConverter:
    def convert_audio(self, audio_path: Path, target_format: str, bitrate: str) -> Path:
        plugin = PluginRegistry.get(target_format)
        if not plugin:
            raise ValueError(f"No plugin for format: {target_format}")
        
        # Call pre-encoding hook
        if not plugin.on_before_encode(audio_path):
            raise RuntimeError(f"Plugin validation failed")
        
        # Get profile and encode
        profile = plugin.get_profile()
        output_path = audio_path.with_suffix(profile.output_ext)
        
        cmd = profile.build_ffmpeg_command(
            str(audio_path),
            str(output_path),
            bitrate
        )
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Call post-encoding hook
        if not plugin.on_after_encode(output_path):
            output_path.unlink()
            raise RuntimeError(f"Post-encode validation failed")
        
        return output_path


PATTERN 5D: File Structure
=====================================================

source/
├── infrastructure/
│   ├── codec_plugins.py           # Plugin interface + built-ins
│   ├── plugin_registry.py          # Discovery and registration
│   └── plugins/                    # Third-party plugins
│       ├── __init__.py
│       ├── flac_plugin.py          # User-created plugin
│       ├── vorbis_plugin.py        # User-created plugin
│       └── custom_h265_plugin.py   # User-created plugin
"""
