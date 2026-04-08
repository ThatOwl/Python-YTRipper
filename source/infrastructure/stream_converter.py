import os
from pathlib import Path 
import ffmpeg as fpg
from utility.logger import get_logger

logger = get_logger(__name__, 'StreamConverter_debug.log')

#TODO: neccessary ? & decide what to put inside 
class VideoConversionParameters:
    actual_video_codec: str = None
    actual_audio_codec: str = None
    target_video_codec: str = None
    target_audio_codec: str = None
    

class StreamConverter:
    """Handles conversion and merging of audio/video streams."""

    #TODO: implement (variable datatypes open until implementation dictates them)
    @staticmethod
    def combine_streams_new(audio, video, conversion_params: VideoConversionParameters): # or combine_parameters object 
        # implement temp logic 
        # implement passing 
        pass
    
    #TODO: implement (variable datatypes open until implementation dictates them)
    @staticmethod
    def convert_audio_new(audio, target_codec, thumbnail, bitrate):
        
        # this can be deleted => logic is moved to MediaAssembler
        """"# Codec & extension from the flag
        if audio_mp3:
            used_a_codec = "libmp3lame"
            target_ext = ".mp3"
        else:
            used_a_codec = "aac"
            target_ext = ".m4a"""""

        # uneccessary as it will be created locally or with os_interaction
        """# Ensure output_path carries the correct extension
        if output_path.suffix.lower() != target_ext:
            logger.warning(
                f"Output extension mismatch ({output_path.suffix}), adjusting to {target_ext}."
            )
            output_path = output_path.with_suffix(target_ext)"""

        logger.debug(f"Converting audio to ({used_a_codec}) with ffmpeg...")

        # could also be moved to MediaAssembler
        """# pytubefix returns e.g. "160kbps" but ffmpeg expects "160k"
        if audio_bitrate:
            ffmpeg_bitrate = audio_bitrate.replace("kbps", "k").replace("mbps", "M")
            bitrate_kwargs = {"audio_bitrate": ffmpeg_bitrate}
            logger.debug(f"Using source-matched audio bitrate: {ffmpeg_bitrate} (raw: {audio_bitrate})")
        else:
            bitrate_kwargs = {"qscale:a": 3}
            logger.debug("No source bitrate provided, using VBR qscale:a=3")"""



    #TODO: retire 
    @staticmethod
    def combine_streams(audio_path: Path, video_path: Path, output_path: Path) -> None:
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
        
        # Use a temporary output file to avoid overwriting input files
        temp_output_path = Path(output_path).parent / f".{Path(output_path).stem}.tmp.mp4"
        
        try:
            (
                fpg
                .output(
                    fpg.input(str(video_path)), 
                    fpg.input(str(audio_path)), 
                    str(temp_output_path), 
                    vcodec='copy', 
                    acodec='aac', 
                    strict='experimental'
                    )
                .run(
                    capture_stdout=True, 
                    capture_stderr=True,
                    overwrite_output=True, 
                    quiet=True
                    )
            )
            
            # Remove input files
            os.remove(video_path)
            os.remove(audio_path)
            
            # Move temp file to final location
            os.rename(temp_output_path, output_path)
            logger.info(f"Merged file saved to: {output_path}")
            
        except Exception as e:
            logger.exception(f"Error during ffmpeg merging: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original files.")
            # Clean up temp file if it exists
            if temp_output_path.exists():
                try:
                    os.remove(temp_output_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to clean up temp file {temp_output_path}: {cleanup_err}")
            raise e  # Re-raise the exception for upstream handling

    #TODO: retire 
    @staticmethod
    def convert_audio(
        audio_path: Path,
        output_path: Path,
        thumbnail_path: Path | None = None,
        audio_bitrate: str = "",
        audio_mp3: bool = False,
    ) -> None:
        """Converts audio (always re-encodes — source is Opus, not AAC).

        Uses a safe temp-file pattern: writes to a .tmp file first, then
        replaces the target only on success.

        Args:
            audio_path (Path): The path to the source audio file.
            output_path (Path): The desired output path (extension may be corrected).
            thumbnail_path (Path | None, optional): Thumbnail image to embed as cover art.
            audio_bitrate (str, optional): Target bitrate e.g. "128kbps". Falls back
                to VBR qscale if empty.
            audio_mp3 (bool): If True encode to MP3 (libmp3lame), otherwise to M4A (AAC).
        """

        # Codec & extension from the flag
        if audio_mp3:
            used_a_codec = "libmp3lame"
            target_ext = ".mp3"
        else:
            used_a_codec = "aac"
            target_ext = ".m4a"

        # Ensure output_path carries the correct extension
        if output_path.suffix.lower() != target_ext:
            logger.warning(
                f"Output extension mismatch ({output_path.suffix}), adjusting to {target_ext}."
            )
            output_path = output_path.with_suffix(target_ext)

        logger.debug(f"Converting audio to {target_ext} ({used_a_codec}) with ffmpeg...")

        # Bitrate kwargs
        # pytubefix returns e.g. "160kbps" but ffmpeg expects "160k"
        if audio_bitrate:
            ffmpeg_bitrate = audio_bitrate.replace("kbps", "k").replace("mbps", "M")
            bitrate_kwargs = {"audio_bitrate": ffmpeg_bitrate}
            logger.debug(f"Using source-matched audio bitrate: {ffmpeg_bitrate} (raw: {audio_bitrate})")
        else:
            bitrate_kwargs = {"qscale:a": 3}
            logger.debug("No source bitrate provided, using VBR qscale:a=3")

        # Temporary output file (safe conversion pattern)
        temp_output = output_path.with_name(output_path.stem + ".tmp" + output_path.suffix)

        audio_input = fpg.input(str(audio_path))
        image_input = fpg.input(str(thumbnail_path)) if thumbnail_path else None

        try:
            if thumbnail_path and thumbnail_path.exists():
                (
                    fpg
                    .output(
                        audio_input,
                        image_input,
                        str(temp_output),
                        acodec=used_a_codec,
                        **bitrate_kwargs,
                        extra_args=[
                            "-map", "0:a",
                            "-map", "1:v",
                            "-metadata:s:v", "title=Album cover",
                            "-metadata:s:v", "comment=Cover (front)",
                        ],
                    )
                    .run(
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True,
                        quiet=True,
                    )
                )
                thumbnail_path.unlink()
            else:
                (
                    fpg
                    .output(
                        audio_input,
                        str(temp_output),
                        acodec=used_a_codec,
                        **bitrate_kwargs,
                    )
                    .run(
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True,
                        quiet=True,
                    )
                )

            # ✅ Conversion succeeded — replace safely
            audio_path.unlink()  # remove original (opus)
            os.replace(temp_output, output_path)

            logger.info(f"Audio file saved to: {output_path}")

        except Exception as e:
            stderr = getattr(e, "stderr", None)
            logger.exception(
                f"Error during ffmpeg audio conversion: {stderr.decode() if stderr else e}"
            )

            # Clean up temp file if conversion failed
            if temp_output.exists():
                temp_output.unlink()

            logger.info("Keeping original audio file.")
            raise e