import os
import ffmpeg as fpg
from source.logger import get_logger

logger = get_logger(__name__, 'sc_debug.log')

class StreamConverter:
    """Handles conversion and merging of audio/video streams."""
    
    @staticmethod
    def convert_to_m4a_old(audio_path: str, output_path: str, thumbnail_path: str = None) -> None:
        """Converts audio to m4a format.

        Args:
            audio_path (str): The path to the source audio file.
            output_path (str): The path where the converted m4a file will be saved.
            thumbnail_path (str, optional): The path to the thumbnail image file. Defaults to None.
        """
        logger.debug("Converting audio to m4a with ffmpeg...")
        try:
            if thumbnail_path and os.path.exists(thumbnail_path):
                (
                    fpg
                    .input(audio_path)
                    .output(
                        output_path,
                        acodec='m4a',
                        **{'id3v2_version': '3'},
                        extra_args=[
                            '-i', thumbnail_path,
                            '-map', '0:a',
                            '-map', '1:v',
                            '-metadata:s:v', 'title=Album cover',
                            '-metadata:s:v', 'comment=Cover (front)'
                        ]
                    )
                    .run(capture_stdout=True, capture_stderr=True, overwrite_output=True, quiet=True)
                )
                os.remove(thumbnail_path)
            else:
                (
                    fpg
                    .input(audio_path)
                    .output(output_path, acodec='aac', strict='experimental')
                    .run(capture_stdout=True, capture_stderr=True, overwrite_output=True, quiet=True)
                )
            logger.info(f"Audio file saved to: {output_path}")
            os.remove(audio_path)
        except Exception as e:
            logger.exception(f"Error during ffmpeg audio conversion: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original audio file.")
            raise e  # Re-raise the exception for upstream handling

    @staticmethod
    def convert_to_m4a(audio_path: str, output_path: str, thumbnail_path: str = None) -> None:
        """Converts audio to m4a format.

        Args:
            audio_path (str): The path to the source audio file.
            output_path (str): The path where the converted m4a file will be saved.
            thumbnail_path (str, optional): The path to the thumbnail image file. Defaults to None.
        """
        logger.debug("Converting audio to m4a with ffmpeg...")
        # ensure output has proper extension so ffmpeg can pick container
        if not output_path.lower().endswith('.m4a'):
            output_path = f"{output_path}.m4a"

        try:
            if thumbnail_path and os.path.exists(thumbnail_path):
                audio_input = fpg.input(audio_path)
                image_input = fpg.input(thumbnail_path)
                (
                    fpg
                    .output(
                        audio_input, image_input, output_path,
                        acodec='aac',
                        # map audio + image, set metadata for cover art
                        extra_args=[
                            '-map', '0:a',
                            '-map', '1:v',
                            '-metadata:s:v', 'title=Album cover',
                            '-metadata:s:v', 'comment=Cover (front)'
                        ]
                    )
                    .run(capture_stdout=True, capture_stderr=True, overwrite_output=True, quiet=True)
                )
                os.remove(thumbnail_path)
            else:
                (
                    fpg
                    .input(audio_path)
                    .output(output_path, acodec='aac', strict='experimental')
                    .run(capture_stdout=True, capture_stderr=True, overwrite_output=True, quiet=True)
                )
            logger.info(f"Audio file saved to: {output_path}")
            os.remove(audio_path)
        except Exception as e:
            stderr = getattr(e, 'stderr', None)
            logger.exception(f"Error during ffmpeg audio conversion: {stderr.decode() if stderr else e}")
            logger.info("Keeping original audio file.")
            raise e  # propagate for upstream handling

    @staticmethod
    def convert_to_mp3(audio_path: str, output_path: str) -> None:
        """
        currently unused !
        Converts an audio file to MP3 format using ffmpeg and saves it to the specified output path.

        Args:
            audio_path (str): The path to the source audio file to be converted.
            output_path (str): The path where the converted MP3 file will be saved.
        Raises:
            Exception: Logs and handles any exceptions that occur during the conversion process.
        Side Effects:
            - Saves the converted MP3 file to the specified output path.
            - Removes the original audio file upon successful conversion.
            - Logs conversion progress and errors.
        """
        logger.debug("Converting audio to mp3 with ffmpeg...")
        try:
            (
                fpg
                .input(audio_path)
                .output(output_path, acodec='mp3', strict='experimental')
                .run(overwrite_output=True, quiet=True)
            )
            logger.info(f"Audio file saved to: {output_path}")
            os.remove(audio_path)
        except Exception as e:
            logger.exception(f"Error during ffmpeg audio conversion: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original audio file.")
            raise e  # Re-raise the exception for upstream handling
        
    @staticmethod
    def combine_streams(audio_path: str, video_path: str, output_path: str) -> None:
        """
        Combines separate audio and video files into a single output file using ffmpeg.

        This method takes the paths to an audio file and a video file, merges them into one media file at the specified output path,
        and removes the original input files upon successful completion.
        Args:
            audio_path (str): Path to the audio file to be merged.
            video_path (str): Path to the video file to be merged.
            output_path (str): Path where the merged output file will be saved.
        Raises:
            Exception: Logs any exception raised during the ffmpeg merging process.
        """
        logger.debug("Combining video and audio with ffmpeg...")
        try:
            (
                fpg
                .output(fpg.input(video_path), fpg.input(audio_path), output_path, vcodec='copy', acodec='aac', strict='experimental')
                .run(capture_stdout=True, capture_stderr=True, overwrite_output=True, quiet=True)
            )
            logger.info(f"Merged file saved to: {output_path}")
            os.remove(video_path)
            os.remove(audio_path)
        except Exception as e:
            logger.exception(f"Error during ffmpeg merging: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original files.")
            raise e  # Re-raise the exception for upstream handling
