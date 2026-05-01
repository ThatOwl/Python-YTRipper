# Pattern 4: Template-Based Command Builder
# Use Jinja2 templates for complex FFMPEG command generation

from jinja2 import Template, Environment, FileSystemLoader, TemplateNotFound
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ============================================================
# FFMPEG COMMAND TEMPLATES
# ============================================================

FFMPEG_TEMPLATES = {
    # Audio encoding templates
    "audio_bitrate": Template("""
ffmpeg -i {{ input_path }}
{%- if audio_codec %}
  -acodec {{ audio_codec }}
{%- endif %}
{%- if bitrate %}
  -b:a {{ bitrate }}
{%- endif %}
{%- if quality is defined %}
  -q:a {{ quality }}
{%- endif %}
{%- if extra_args %}
  {{ extra_args | join(' ') }}
{%- endif %}
  {{ output_path }}
""".strip()),
    
    "audio_lossless": Template("""
ffmpeg -i {{ input_path }}
  -acodec {{ audio_codec }}
  {{ output_path }}
""".strip()),
    
    # Video encoding templates
    "video_h264": Template("""
ffmpeg -i {{ input_path }}
  -vcodec libx264
  -preset {{ preset | default('medium') }}
  -crf {{ quality | default('23') }}
{%- if audio_codec %}
  -acodec {{ audio_codec }}
{%- endif %}
  {{ output_path }}
""".strip()),
    
    "video_h265": Template("""
ffmpeg -i {{ input_path }}
  -vcodec libx265
  -preset {{ preset | default('medium') }}
  -crf {{ quality | default('23') }}
{%- if audio_codec %}
  -acodec {{ audio_codec }}
{%- endif %}
  {{ output_path }}
""".strip()),
    
    "video_vp9": Template("""
ffmpeg -i {{ input_path }}
  -vcodec libvpx-vp9
  -cpu-used {{ cpu_used | default('4') }}
  -crf {{ quality | default('30') }}
{%- if audio_codec %}
  -acodec {{ audio_codec }}
{%- endif %}
  {{ output_path }}
""".strip()),
    
    # Composition templates
    "compose_audio_video": Template("""
ffmpeg -i {{ video_path }}
  -i {{ audio_path }}
  -c:v copy
  -c:a {{ audio_codec | default('aac') }}
  -map 0:v:0 -map 1:a:0
  {{ output_path }}
""".strip()),
}


class TemplateNotFoundError(Exception):
    """Raised when template is not found"""
    pass


class FFMpegCommandBuilder:
    """Build FFMPEG commands from templates or profiles"""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize builder with optional Jinja2 template directory.
        
        Args:
            template_dir: Path to directory containing .jinja2 template files
                         If None, uses in-memory templates only
        """
        self.template_dir = template_dir
        self.env = None
        
        if template_dir and template_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=False,
            )
    
    def build_audio_conversion(
        self,
        input_path: str,
        output_path: str,
        audio_codec: str,
        bitrate: Optional[str] = None,
        quality: Optional[int] = None,
        extra_args: Optional[list] = None,
    ) -> str:
        """
        Build audio conversion command.
        
        Args:
            input_path: Input audio file path
            output_path: Output audio file path
            audio_codec: FFMPEG audio codec (e.g., libmp3lame, aac, libopus)
            bitrate: Target bitrate (e.g., "192k")
            quality: Quality parameter (codec-specific, e.g., 2 for MP3)
            extra_args: List of additional FFMPEG arguments
        
        Returns:
            Complete FFMPEG command string
        """
        template = FFMPEG_TEMPLATES["audio_bitrate"]
        
        cmd = template.render(
            input_path=input_path,
            output_path=output_path,
            audio_codec=audio_codec,
            bitrate=bitrate,
            quality=quality,
            extra_args=extra_args or [],
        )
        return self._normalize_command(cmd)
    
    def build_audio_lossless(
        self,
        input_path: str,
        output_path: str,
        audio_codec: str,
    ) -> str:
        """Build lossless audio encoding command (FLAC, etc.)"""
        template = FFMPEG_TEMPLATES["audio_lossless"]
        
        cmd = template.render(
            input_path=input_path,
            output_path=output_path,
            audio_codec=audio_codec,
        )
        return self._normalize_command(cmd)
    
    def build_video_h264(
        self,
        input_path: str,
        output_path: str,
        preset: str = "medium",
        quality: int = 23,
        audio_codec: Optional[str] = None,
    ) -> str:
        """Build H.264 video encoding command"""
        template = FFMPEG_TEMPLATES["video_h264"]
        
        cmd = template.render(
            input_path=input_path,
            output_path=output_path,
            preset=preset,
            quality=quality,
            audio_codec=audio_codec,
        )
        return self._normalize_command(cmd)
    
    def build_video_h265(
        self,
        input_path: str,
        output_path: str,
        preset: str = "medium",
        quality: int = 23,
        audio_codec: Optional[str] = None,
    ) -> str:
        """Build H.265 (HEVC) video encoding command"""
        template = FFMPEG_TEMPLATES["video_h265"]
        
        cmd = template.render(
            input_path=input_path,
            output_path=output_path,
            preset=preset,
            quality=quality,
            audio_codec=audio_codec,
        )
        return self._normalize_command(cmd)
    
    def build_video_vp9(
        self,
        input_path: str,
        output_path: str,
        cpu_used: int = 4,
        quality: int = 30,
        audio_codec: Optional[str] = None,
    ) -> str:
        """Build VP9 video encoding command"""
        template = FFMPEG_TEMPLATES["video_vp9"]
        
        cmd = template.render(
            input_path=input_path,
            output_path=output_path,
            cpu_used=cpu_used,
            quality=quality,
            audio_codec=audio_codec,
        )
        return self._normalize_command(cmd)
    
    def build_compose_audio_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        audio_codec: str = "aac",
    ) -> str:
        """Build command to compose video and audio tracks"""
        template = FFMPEG_TEMPLATES["compose_audio_video"]
        
        cmd = template.render(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path,
            audio_codec=audio_codec,
        )
        return self._normalize_command(cmd)
    
    def build_from_template(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """
        Build command from named template with parameters.
        
        Args:
            template_name: Name of template (key in FFMPEG_TEMPLATES)
            **kwargs: Template variables
        
        Returns:
            Rendered command string
        
        Raises:
            TemplateNotFoundError: If template not found
        """
        if template_name not in FFMPEG_TEMPLATES:
            raise TemplateNotFoundError(
                f"Template '{template_name}' not found. "
                f"Available: {list(FFMPEG_TEMPLATES.keys())}"
            )
        
        template = FFMPEG_TEMPLATES[template_name]
        cmd = template.render(**kwargs)
        return self._normalize_command(cmd)
    
    def build_from_file(
        self,
        filename: str,
        **kwargs
    ) -> str:
        """
        Build command from external Jinja2 template file.
        
        Args:
            filename: Template filename (e.g., "custom_encode.jinja2")
            **kwargs: Template variables
        
        Returns:
            Rendered command string
        
        Raises:
            ValueError: If template_dir not set
            TemplateNotFoundError: If file not found
        """
        if not self.env:
            raise ValueError("Template directory not configured")
        
        try:
            template = self.env.get_template(filename)
            cmd = template.render(**kwargs)
            return self._normalize_command(cmd)
        except TemplateNotFound as e:
            raise TemplateNotFoundError(f"Template file not found: {filename}") from e
    
    @staticmethod
    def _normalize_command(cmd_str: str) -> str:
        """
        Normalize command string for execution.
        - Remove excess whitespace
        - Convert to single line for subprocess
        - Preserve quoted arguments
        """
        lines = cmd_str.split('\n')
        normalized = ' '.join(line.strip() for line in lines if line.strip())
        return normalized


# ============================================================
# INTEGRATION PATTERNS
# ============================================================

"""
PATTERN 4A: Usage in stream_converter.py
=====================================================

from infrastructure.ffmpeg_builder import FFMpegCommandBuilder

class StreamConverter:
    def __init__(self):
        self.builder = FFMpegCommandBuilder()
    
    def convert_audio(self, audio_path: Path, target_format: str, bitrate: str) -> Path:
        '''Convert audio using template-based builder'''
        profile = CodecRegistry.get(target_format)
        output_path = audio_path.with_suffix(profile.output_ext)
        
        # Build command from template
        if profile.supported_bitrates:
            cmd_str = self.builder.build_audio_conversion(
                input_path=str(audio_path),
                output_path=str(output_path),
                audio_codec=profile.codec,
                bitrate=bitrate,
            )
        else:
            # Lossless encoding
            cmd_str = self.builder.build_audio_lossless(
                input_path=str(audio_path),
                output_path=str(output_path),
                audio_codec=profile.codec,
            )
        
        # Parse and execute
        cmd = cmd_str.split()
        logger.debug(f"Running: {cmd_str}")
        subprocess.run(cmd, check=True, capture_output=True)
        
        return output_path


PATTERN 4B: Custom template files in templates/
=====================================================

Create: infrastructure/templates/custom_opus_hq.jinja2
---
ffmpeg -i {{ input_path }}
  -acodec libopus
  -b:a {{ bitrate }}
  -application audio
  -compression_level 10
  {{ output_path }}

Usage:
  builder = FFMpegCommandBuilder(Path("infrastructure/templates"))
  cmd = builder.build_from_file(
      "custom_opus_hq.jinja2",
      input_path="input.wav",
      output_path="output.opus",
      bitrate="192k"
  )
"""
