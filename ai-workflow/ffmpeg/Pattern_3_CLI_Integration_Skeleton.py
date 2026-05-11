# Pattern 3: CLI Integration with Format Selection
# Add user-friendly format discovery and selection to CLI layer

from typing import List, Optional
from pathlib import Path
from infrastructure.codec_registry import CodecRegistry, CodecFamily


class FormatSelectionHelper:
    """Helper class for format discovery and validation in CLI"""
    
    @staticmethod
    def get_available_formats() -> dict:
        """Get all formats grouped by family"""
        return {
            "audio": CodecRegistry.list_audio_formats(),
            "video": CodecRegistry.list_video_formats(),
        }
    
    @staticmethod
    def print_formats_table(output=None):
        """Print formatted table of all available formats"""
        import io
        import sys
        
        if output is None:
            output = sys.stdout
        
        def write(msg=""):
            print(msg, file=output)
        
        write("\n" + "="*70)
        write("AVAILABLE OUTPUT FORMATS")
        write("="*70 + "\n")
        
        # Audio formats
        write("AUDIO FORMATS:")
        write("-" * 70)
        audio_formats = CodecRegistry.get_profiles_by_family(CodecFamily.AUDIO)
        for name, profile in sorted(audio_formats.items()):
            write(f"  {name:15} {profile.description}")
            if profile.supported_bitrates:
                bitrates_str = ", ".join(profile.supported_bitrates)
                write(f"    └─ Bitrates: {bitrates_str}")
        
        # Video formats
        write("\nVIDEO FORMATS:")
        write("-" * 70)
        video_formats = CodecRegistry.get_profiles_by_family(CodecFamily.VIDEO)
        for name, profile in sorted(video_formats.items()):
            write(f"  {name:15} {profile.description}")
        
        write("\n" + "="*70 + "\n")
    
    @staticmethod
    def validate_format_choice(format_name: str) -> bool:
        """Validate that format name is available"""
        try:
            CodecRegistry.get(format_name)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def get_format_info(format_name: str) -> Optional[dict]:
        """Get detailed info about a format"""
        try:
            profile = CodecRegistry.get(format_name)
            return {
                "name": profile.name,
                "family": profile.codec_family.value,
                "codec": profile.codec,
                "container": profile.container,
                "extension": profile.output_ext,
                "description": profile.description,
                "bitrates": profile.supported_bitrates,
                "preset": profile.preset_quality,
            }
        except ValueError:
            return None
    
    @staticmethod
    def suggest_formats(media_type: str = "audio") -> List[str]:
        """Suggest popular formats for a media type"""
        suggestions = {
            "audio": ["mp3", "aac", "opus"],  # Most compatible first
            "video": ["h264", "h265", "vp9"],
        }
        return suggestions.get(media_type.lower(), [])


# ============================================================
# CLI COMMAND MODIFICATIONS
# ============================================================

"""
MODIFICATIONS TO: cli/cli_command.py

1. Add imports at top:
   from cli.format_helpers import FormatSelectionHelper

2. In CLICommand._setup_parser(), add new argument group:

   # Output Format Arguments
   format_group = parser.add_argument_group(
       "Output Format Options",
       "Control output media format and quality"
   )
   format_group.add_argument(
       "--output-format",
       dest="output_format",
       metavar="FORMAT",
       default="mp3",
       choices=CodecRegistry.list_all(),
       help="Output format (e.g., mp3, opus, aac, h264, h265). "
            "Use --list-formats to see all options. Default: mp3"
   )
   format_group.add_argument(
       "--bitrate", "-br",
       dest="target_bitrate",
       metavar="BITRATE",
       default="192k",
       help="Target bitrate in FFMPEG format (e.g., 192k, 256k). "
            "Bitrate availability depends on chosen format. Default: 192k"
   )
   format_group.add_argument(
       "--list-formats",
       dest="list_formats",
       action="store_true",
       help="Display all available output formats and exit"
   )
   format_group.add_argument(
       "--format-info",
       dest="format_info",
       metavar="FORMAT",
       help="Show detailed information about a specific format and exit"
   )

3. In CLICommand.run(), add early checks:

   # Handle format listing
   if args.list_formats:
       FormatSelectionHelper.print_formats_table()
       return 0
   
   # Handle format info query
   if args.format_info:
       info = FormatSelectionHelper.get_format_info(args.format_info)
       if info:
           print(f"\\nFormat: {info['name']}")
           print(f"  Type: {info['family']}")
           print(f"  Codec: {info['codec']}")
           print(f"  Container: {info['container']}")
           print(f"  Extension: {info['extension']}")
           print(f"  Description: {info['description']}")
           if info['bitrates']:
               print(f"  Supported Bitrates: {', '.join(info['bitrates'])}")
           return 0
       else:
           logger.error(f"Format not found: {args.format_info}")
           return 1
   
   # Validate format choice
   if not FormatSelectionHelper.validate_format_choice(args.output_format):
       logger.error(f"Invalid format: {args.output_format}")
       logger.info("Use --list-formats to see available options")
       return 1
   
   # Update DownloadOptions with format choices
   options.output_format = args.output_format
   options.target_bitrate = args.target_bitrate

4. Update DownloadOptions.from_preferences() to include:

   @classmethod
   def from_preferences(cls, pref_dict: dict) -> "DownloadOptions":
       options = cls(
           # ... existing field mappings ...
           output_format=pref_dict.get("output_format", "mp3"),
           target_bitrate=pref_dict.get("target_bitrate", "192k"),
       )
       return options

5. In preferences.py DEFAULT_PREFS, add:

   DEFAULT_PREFS = {
       # ... existing ...
       "output_format": "mp3",
       "target_bitrate": "192k",
   }
"""


# ============================================================
# USAGE EXAMPLES
# ============================================================

"""
CLI Usage After Implementation:
================================

# List all available formats
$ python source/yt_ripper.py --list-formats

Output:
======================================================================
                    AVAILABLE OUTPUT FORMATS
======================================================================

AUDIO FORMATS:
----------------------------------------------------------------------
  mp3             MP3 Audio (Lossy, Wide Compatibility)
    └─ Bitrates: 64k, 96k, 128k, 192k, 256k, 320k
  aac             AAC Audio (M4A, Apple Compatible)
    └─ Bitrates: 64k, 96k, 128k, 192k, 256k
  opus            Opus Audio (Modern, High Quality at Low Bitrate)
    └─ Bitrates: 64k, 96k, 128k, 192k, 256k
  vorbis          Vorbis Audio (OGG, Open Format)
    └─ Bitrates: 128k, 192k, 256k, 320k
  flac            FLAC Audio (Lossless)

VIDEO FORMATS:
----------------------------------------------------------------------
  h264            H.264 Video (MP4, High Compatibility)
  h265            H.265 Video (HEVC, Better Compression)
  vp9             VP9 Video (WebM, Web Friendly)

======================================================================


# Show info about a specific format
$ python source/yt_ripper.py --format-info opus

Format: opus
  Type: audio
  Codec: libopus
  Container: opus
  Extension: .opus
  Description: Opus Audio (Modern, High Quality at Low Bitrate)
  Supported Bitrates: 64k, 96k, 128k, 192k, 256k


# Download and convert to specific format
$ python source/yt_ripper.py "https://youtube.com/watch?v=..." \
    --audio_only \
    --output-format opus \
    --bitrate 128k

$ python source/yt_ripper.py "https://youtube.com/watch?v=..." \
    --output-format h265

# Save format preference to config
$ python source/yt_ripper.py "https://youtube.com/watch?v=..." \
    --output-format aac \
    --bitrate 256k \
    --save-config

# Use saved format preference
$ python source/yt_ripper.py "https://youtube.com/watch?v=..."
  (automatically uses aac/256k from saved config)
"""
