from xml.etree.ElementInclude import include
import pytubefix as ptf
from pytubefix import exceptions as ptf_ex
import os
import re
from enum import Enum
from datetime import datetime
from typing import List
from pathlib import Path 

from source.infrastructure.logger import get_logger
from source.components.stream_converter import StreamConverter
from source.components.url_handler import URLHandler
from source.infrastructure.os_interactions import OSInteractions
from source.components.thumbnail_handler import ThumbnailHandler
from source.infrastructure.utils import DownloadError, DownloadOptions, DownloadResult, QUALITY_ALIAS_MAP

logger = get_logger(__name__, 'pytube_interface_debug.log')

# DEBUG < INFO < WARNING < ERROR < CRITICAL


class PytubeInterface:
    """
    Handles high-level download logic for YouTube videos and playlists using pytubefix.
    """
    #FIXME: needs better solution -> maintain readable code and avoid too many arguments in methods
    class StreamType(Enum):
        AUDIO = 1
        VIDEO = 0
    stream_type_map = {
        StreamType.AUDIO:'Audio',
        StreamType.VIDEO:'Video'
    }

    def __init__(self, 
                 os_handler: OSInteractions = None, 
                 thumbnail_handler: ThumbnailHandler = None,
                 stream_converter: StreamConverter = None, 
                 url_handler: URLHandler = None):
        """
        Initialize the YouTubeDownloader with optional handlers for OS interactions,
        thumbnail downloading, and stream conversion.
        Args:
            os_handler (OSInteractions): Handler for OS interactions.
            thumbnail_handler (ThumbnailHandler, optional): Handler for thumbnail downloading. Defaults to None.
            stream_converter (StreamConverter, optional): Handler for stream conversion. Defaults to None.
            url_handler (URLHandler, optional): Handler for URL handling. Defaults to None.
        """
            
        self.thumbnail_handler = thumbnail_handler if thumbnail_handler is not None else ThumbnailHandler()
        self.stream_converter = stream_converter if stream_converter is not None else StreamConverter()
        self.urlh = url_handler if url_handler is not None else URLHandler()
        self.os_handler = os_handler if os_handler is not None else OSInteractions()
        
    
    # TODO: Test and implement
    