import os
import shutil
import ffmpeg as fpg
from source.logger import get_logger


logger = get_logger(__name__, 'sc_debug.log')

class StreamConverter:
    """Handles conversion and merging of audio/video streams."""
    @staticmethod
    def _resolve_ffmpeg_cmd() -> str:
        """Return the ffmpeg executable to use.

        Resolution order:
        - Use file path from env var FFMPEG_BINARY if it exists
        - If FFMPEG_PATH points to a directory, append ffmpeg(.exe)
        - Use binary discovered on PATH via shutil.which('ffmpeg')
        - Otherwise raise FileNotFoundError with guidance
        """
        # 1) Explicit file path
        env_bin = os.environ.get("FFMPEG_BINARY")
        if env_bin and os.path.isfile(env_bin):
            return env_bin

        # 2) Directory path
        env_dir = os.environ.get("FFMPEG_PATH")
        if env_dir and os.path.isdir(env_dir):
            candidate = os.path.join(env_dir, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            if os.path.isfile(candidate):
                return candidate

        # 3) PATH lookup
        which = shutil.which("ffmpeg")
        if which:
            return which

        # 4) Not found
        raise FileNotFoundError(
            "ffmpeg executable not found. Install ffmpeg and ensure it's on PATH, "
            "or set FFMPEG_BINARY to the full path, or FFMPEG_PATH to its folder."
        )
    
    @staticmethod
    def convert_to_m4a(audio_path: str, output_path: str, thumbnail_path: str = None) -> None:
        """
        #TODO summary

        Args:
            audio_path (str): _description_
            output_path (str): _description_
            thumbnail_path (str, optional): _description_. Defaults to None.
        """
        logger.debug("Converting audio to m4a with ffmpeg...")
        try:
            cmd = StreamConverter._resolve_ffmpeg_cmd()
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
                    .run(overwrite_output=True, quiet=True, cmd=cmd)
                )
                os.remove(thumbnail_path)
            else:
                (
                    fpg
                    .input(audio_path)
                    .output(output_path, acodec='mp3', strict='experimental')
                    .run(overwrite_output=True, quiet=True, cmd=cmd)
                )
            logger.info(f"Audio file saved to: {output_path}")
            os.remove(audio_path)
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                logger.exception(
                    "ffmpeg not found. Install it and add to PATH, or set FFMPEG_BINARY/FFMPEG_PATH. "
                    "See README for setup instructions."
                )
            else:
                logger.exception(f"Error during ffmpeg audio conversion: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original audio file.")

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
            cmd = StreamConverter._resolve_ffmpeg_cmd()
            (
                fpg
                .input(audio_path)
                .output(output_path, acodec='mp3', strict='experimental')
                .run(overwrite_output=True, quiet=True, cmd=cmd)
            )
            logger.info(f"Audio file saved to: {output_path}")
            os.remove(audio_path)
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                logger.exception(
                    "ffmpeg not found. Install it and add to PATH, or set FFMPEG_BINARY/FFMPEG_PATH. "
                    "See README for setup instructions."
                )
            else:
                logger.exception(f"Error during ffmpeg audio conversion: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original audio file.")

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
            cmd = StreamConverter._resolve_ffmpeg_cmd()
            (
                fpg
                .output(fpg.input(video_path), fpg.input(audio_path), output_path, vcodec='copy', acodec='aac', strict='experimental')
                .run(overwrite_output=True, quiet=True, cmd=cmd)
            )
            logger.info(f"Merged file saved to: {output_path}")
            os.remove(video_path)
            os.remove(audio_path)
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                logger.exception(
                    "ffmpeg not found. Install it and add to PATH, or set FFMPEG_BINARY/FFMPEG_PATH. "
                    "See README for setup instructions."
                )
            else:
                logger.exception(f"Error during ffmpeg merging: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original files.")
