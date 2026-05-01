"""StreamDownloadService
Responsibility: “Given a stream → download it”
Thin adapter over pytubefix
"""
from pathlib import Path
from pytubefix import Stream as ptfStream

from utility.logger import get_logger
from utility.utils import StreamDownloadError

logger = get_logger( __name__,"StreamDownloader_debug.log")

class StreamDownloadService(object):
    """docstring for StreamDownloadService."""

    #TODO: cleanup (mess of parameters) 
    #TODO:  return path or object => find out if ffmpeg performance improves 
    #       RAM intensive! => large files may require own method*S* !
    @staticmethod
    def download_stream(stream: ptfStream, download_dir: Path) -> Path | None:
        """
        Downloads a specified audio or video stream with given parameters.              
            Args:
                stream (ptf.Stream): The YouTube video stream object to download.
                download_dir (Path): The directory where the downloaded file will be saved.
            Returns:
                Path | None: The file path of the downloaded stream, or None if no suitable stream is found.
            Logs:
                - Debug logs for the download process, including the stream identifier and download path.
                - Exception logs if the download fails, including the error message.
            Raises:
                StreamDownloadError: If there is an error during the download process.
        """
        
        try:
            identifier = "audio" if stream.includes_audio_track and not stream.includes_video_track else "video" if stream.includes_video_track else "Error"
            
            downloaded_path:Path = Path(stream.download
                (
                output_path=str(download_dir),
                skip_existing=True,
                timeout=5,
                max_retries=3
                )
            )
            
            logger.debug(f"{identifier} stream downloaded to: {downloaded_path}")
            return downloaded_path
        except Exception as e:
            logger.exception(f"Error downloading {identifier} stream: {e}")
            raise StreamDownloadError(f"Error downloading {identifier} stream: {e}") from e
    