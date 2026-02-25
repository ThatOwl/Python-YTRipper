import os
from pathlib import Path 
import ffmpeg as fpg
from core.logger import get_logger

logger = get_logger(__name__, 'sc_debug.log')

class StreamConverter:
    """Handles conversion and merging of audio/video streams."""
    @staticmethod
    def convert_audio_old(audio_path: Path, output_path: Path, thumbnail_path: Path | None = None) -> None:
        """Converts audio to desired format based on output_path extension.
        Args:
            audio_path (Path): The path to the source audio file.
            output_path (Path): The path where the converted audio file will be saved.
            thumbnail_path (Path, optional): The path to the thumbnail image file. Defaults to None.
        """
        ext_out = os.path.splitext(output_path)[1].lower()
        ext_in = os.path.splitext(audio_path)[1].lower()

        if ext_out == '.m4a':
            StreamConverter.convert_to_m4a(audio_path, output_path, thumbnail_path)
        elif ext_out == '.mp3' and ext_in != '.mp3':
            StreamConverter.convert_to_mp3(audio_path, output_path)
        else:
            logger.warning(f"Unsupported audio format '{ext_out}' for output. Keeping original audio file at: {audio_path}")
                      
    @staticmethod
    def convert_to_m4a(audio_path: Path, output_path: Path, thumbnail_path: Path | None = None) -> None:
        """Converts audio to m4a format.

        Args:
            audio_path (Path): The path to the source audio file.
            output_path (Path): The path where the converted m4a file will be saved.
            thumbnail_path (Path | None, optional): The path to the thumbnail image file. Defaults to None.
        """
        ext_out = os.path.splitext(output_path)[1].lower()
        ext_in = os.path.splitext(audio_path)[1].lower()
        
        logger.debug("Converting audio to m4a with ffmpeg...")
        # ensure output has proper extension so ffmpeg can pick container
        if not output_path.suffix.lower() == ".m4a":
            logger.warning(f"Output path does not have .m4a extension: {output_path}. Adjusting accordingly.")
            output_path = output_path.with_suffix('.m4a')

        audio_input = fpg.input(str(audio_path))
        image_input = fpg.input(str(thumbnail_path)) if thumbnail_path else None
        output = str(output_path)
        try:
            if thumbnail_path and os.path.exists(thumbnail_path):
                (
                    fpg
                    .output(
                        audio_input, image_input, output,
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
                logger.info(f"Audio file saved to: {output}")
                os.remove(audio_path)
            elif ext_in != '.m4a':
                (
                    fpg
                    .output(
                        audio_input, output,
                        vcodec='copy', acodec='aac', strict='experimental',
                    )
                    .run(capture_stdout=True, capture_stderr=True, overwrite_output=True, quiet=True)   
                )
                logger.info(f"Audio file saved to: {output}")
                os.remove(audio_path)
            else:
                # if input is already mp4, just rename to m4a
                os.rename(audio_path, output)
                logger.info(f"Renamed audio file to: {output}")
                            
        except Exception as e:
            stderr = getattr(e, 'stderr', None)
            logger.exception(f"Error during ffmpeg audio conversion: {stderr.decode() if stderr else e}")
            logger.info("Keeping original audio file.")
            raise e  # propagate for upstream handling

    @staticmethod
    def convert_to_mp3(audio_input: Path, output_path: Path) -> None:
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
                .output(
                        audio_input, output_path,
                        vcodec='copy', acodec='aac', strict='experimental',
                    )
                    .run(capture_stdout=True, capture_stderr=True, overwrite_output=True, quiet=True)   
            )
            logger.info(f"Audio file saved to: {output_path}")
            os.remove(audio_input)
        except Exception as e:
            logger.exception(f"Error during ffmpeg audio conversion: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            logger.info("Keeping original audio file.")
            raise e  # Re-raise the exception for upstream handling
        
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
                .output(fpg.input(str(video_path)), fpg.input(str(audio_path)), str(temp_output_path), vcodec='copy', acodec='aac', strict='experimental')
                .run(capture_stdout=True, capture_stderr=True, overwrite_output=True, quiet=True)
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


    # replaces convert_to_m4a and convert_to_mp3
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

        # ── Codec & extension from the flag ──────────────────────────────
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

        # ── Bitrate kwargs ────────────────────────────────────────────────
        # pytubefix returns e.g. "160kbps" but ffmpeg expects "160k"
        if audio_bitrate:
            ffmpeg_bitrate = audio_bitrate.replace("kbps", "k").replace("mbps", "M")
            bitrate_kwargs = {"audio_bitrate": ffmpeg_bitrate}
            logger.debug(f"Using source-matched audio bitrate: {ffmpeg_bitrate} (raw: {audio_bitrate})")
        else:
            bitrate_kwargs = {"qscale:a": 3}
            logger.debug("No source bitrate provided, using VBR qscale:a=3")

        # ── Temporary output file (safe conversion pattern) ───────────────
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
            raise

    @staticmethod
    def temp_convert_audio(audio_path: Path, output_path: Path, thumbnail_path: Path | None = None, audio_bitrate: str = "") -> None:
        """Converts audio to m4a format using AAC.
        
        Args:
            audio_path (Path): The path to the source audio file.
            output_path (Path): The path where the converted m4a file will be saved.
            thumbnail_path (Path | None, optional): The path to the thumbnail image file. Defaults to None.
            audio_bitrate (str, optional): Target audio bitrate e.g. "128kbps". When set, uses
                CBR at this rate instead of VBR qscale. Defaults to "".
        """

        logger.debug("Converting audio to m4a with ffmpeg...")

        # Ensure correct extension
        if output_path.suffix.lower() != ".m4a":
            logger.warning(
                f"Output path does not have .m4a extension: {output_path}. Adjusting accordingly."
            )
            output_path = output_path.with_suffix(".m4a")

        # Build bitrate kwargs: prefer explicit bitrate over VBR qscale
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
                        acodec="aac",
                        **bitrate_kwargs,
                        extra_args=[
                            "-map", "0:a",
                            "-map", "1:v",
                            "-metadata:s:v", "title=Album cover",
                            "-metadata:s:v", "comment=Cover (front)"
                        ]
                    )
                    .run(
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True,
                        quiet=True
                    )
                )

                thumbnail_path.unlink()

            else:
                (
                    fpg
                    .output(
                        audio_input,
                        str(temp_output),
                        acodec="aac",
                        **bitrate_kwargs
                    )
                    .run(
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True,
                        quiet=True
                    )
                )

            # ✅ Conversion succeeded — now replace safely
            audio_path.unlink()  # remove original
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
            raise