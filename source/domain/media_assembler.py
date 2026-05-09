"""MediaAssembler
Responsibility:
convert audio
merge audio/video
Wraps StreamConverter
"""

from utility.logger import get_logger
from infrastructure.stream_converter import StreamConverter

logger = get_logger(__name__, "media_assembler_debug.log")

"""
final extension,
final output path,
temp output path,
whether to delete source fragments,
whether to delete thumbnail,
how to normalize bitrate,
how to translate ffmpeg failure into ConversionError or CombineError,
what path to return after success.
"""


class MediaAssembler(object):
    """docstring for MediaAssembler."""
    def __init__(self, stream_converter: StreamConverter = None):
        self.stream_converter = stream_converter if stream_converter is not None else StreamConverter()
        
    def convert_audio(self, ?? ) -> None:
        """Will delegate to StreamConverter.convert_audio, but will also handle any media-assembler specific logic (e.g. file management, logging, error handling, etc.)"""
        self.stream_converter.convert_audio_new()
        
    def combine_streams(self, ?? ) -> None:
        """Will delegate to StreamConverter.combine_streams, , but will also handle any media-assembler specific logic (e.g. file management, logging, error handling, etc.)"""
        self.stream_converter.combine_streams()