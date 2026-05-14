from pathlib import Path

from utility.logger import get_logger
from utility.utils import (
    CombineError,
    ConversionError,
    DownloadOptions,
    OutputProfile,
    StreamInfo,
    build_audio_embedded_artwork_profile,
)
from infrastructure.stream_converter import FfmpegSettings, StreamConverter

logger = get_logger(__name__, "media_assembler_debug.log")

#TODO add more profiles for audio and video
#TODO expected extension is not easily extenable
class MediaAssembler:
    """
    Application-level media assembly service.

    Owns:
    - final output path policy
    - temp-file safety
    - cleanup of downloaded fragments
    - conversion/merge error translation
    - mapping user options + stream metadata to ffmpeg profiles

    Does not own:
    - selecting YouTube streams
    - downloading streams
    - direct ffmpeg graph construction
    """

    def __init__(self, stream_converter: StreamConverter | None = None):
        self.stream_converter = stream_converter or StreamConverter()

    def convert_audio(
        self,
        audio: StreamInfo,
        output_path: Path,
        profile: OutputProfile,
        thumbnail_path: Path | None = None,
        delete_sources: bool = True,
    ) -> Path:
        output_path = self._apply_profile_extension(Path(output_path), profile)
        temp_output = self._temp_output_path(output_path)
        settings = self._build_audio_ffmpeg_settings(profile, thumbnail_path)

        logger.debug("Converting audio %s -> %s with profile=%s", audio.path, output_path, profile)

        try:
            self.stream_converter.convert_audio_new(
                input_path=audio.path,
                output_path=temp_output,
                profile=profile,
                settings=settings,
                thumbnail_path=thumbnail_path,
            )
            self._replace_temp_output(temp_output, output_path)

            if delete_sources:
                self._delete_sources([audio.path], final_output=output_path)
            if thumbnail_path:
                self._delete_sources([Path(thumbnail_path)], final_output=output_path)

            logger.info("Audio file saved to: %s", output_path)
            return output_path

        except Exception as e:
            self._safe_unlink(temp_output)
            logger.exception("Audio conversion failed: %s", self._format_exception(e))
            raise ConversionError(f"Audio conversion failed: {self._format_exception(e)}") from e

    def combine_streams(
        self,
        video: StreamInfo,
        audio: StreamInfo | None,
        output_path: Path,
        profile: OutputProfile,
        delete_sources: bool = True,
    ) -> Path:
        if audio is None and not video.includes_audio:
            raise CombineError("Cannot assemble video: no audio stream and video stream has no embedded audio")

        output_path = self._apply_profile_extension(Path(output_path), profile)
        temp_output = self._temp_output_path(output_path)
        settings = FfmpegSettings()

        logger.debug(
            "Combining video=%s audio=%s -> %s with profile=%s",
            video.path,
            audio.path if audio else None,
            output_path,
            profile,
        )

        try:
            self.stream_converter.combine_streams_new(
                video_path=video.path,
                audio_path=audio.path if audio else None,
                output_path=temp_output,
                profile=profile,
                settings=settings,
            )
            self._replace_temp_output(temp_output, output_path)

            if delete_sources:
                sources = [video.path]
                if audio is not None:
                    sources.append(audio.path)
                self._delete_sources(sources, final_output=output_path)

            logger.info("Merged file saved to: %s", output_path)
            return output_path

        except Exception as e:
            self._safe_unlink(temp_output)
            logger.exception("Media assembly failed: %s", self._format_exception(e))
            raise CombineError(f"Media assembly failed: {self._format_exception(e)}") from e

    def resolve_output_profile(
        self,
        options: DownloadOptions,
        *,
        audio_only: bool,
        audio: StreamInfo | None = None,
        video: StreamInfo | None = None,
    ) -> OutputProfile:
        """Resolve a target profile from user intent and selected stream metadata."""
        preferred_format = (options.preferred_format or "").strip().lower().lstrip(".")

        if audio_only:
            return self._resolve_audio_profile(options, audio, preferred_format)
        return self._resolve_video_profile(options, audio, video, preferred_format)

    def expected_extension(self, options: DownloadOptions) -> str:
        """Lightweight extension prediction for skip-existing checks before streams are selected."""
        fmt = (options.preferred_format or "").strip().lower().lstrip(".")
        if options.audio_only:
            if options.audio_mp3 or fmt == "mp3":
                return ".mp3"
            return ".m4a"
        if fmt == "webm":
            return ".webm"
        return ".mp4"

    def _resolve_audio_profile(
        self,
        options: DownloadOptions,
        audio: StreamInfo | None,
        preferred_format: str,
    ) -> OutputProfile:
        #FIXME audio.bitrate on oups is not constant => we want to maintian as high bitrate as possible without bloating files
        bitrate = _normalize_bitrate_for_ffmpeg(options.preferred_abr or (audio.bitrate if audio else None))

        if options.audio_mp3 or preferred_format == "mp3":
            return OutputProfile(
                extension=".mp3",
                container="mp3",
                audio_codec="libmp3lame",
                audio_bitrate=bitrate,
                embedded_artwork=build_audio_embedded_artwork_profile("mp3"),
            )

        # Standard non-MP3 audio output: M4A/AAC. Copy only if source is already AAC-like.
        source_codec = _normalize_codec(audio.codec if audio else None)
        audio_codec = "copy" if source_codec in {"aac", "mp4a"} else "aac"
        return OutputProfile(
            extension=".m4a",
            container="m4a",
            audio_codec=audio_codec,
            audio_bitrate=None if audio_codec == "copy" else bitrate,
            embedded_artwork=build_audio_embedded_artwork_profile("m4a"),
        )

    def _resolve_video_profile(
        self,
        options: DownloadOptions,
        audio: StreamInfo | None,
        video: StreamInfo | None,
        preferred_format: str,
    ) -> OutputProfile:
        audio_bitrate = _normalize_bitrate_for_ffmpeg(options.preferred_abr or (audio.bitrate if audio else None))
        video_codec = _normalize_codec(video.codec if video else None)
        audio_codec = _normalize_codec(audio.codec if audio else None)

        if preferred_format == "webm":
            resolved_video_codec = "copy" if video_codec in {"vp8", "vp9", "av1", "av01"} else "libvpx-vp9"
            resolved_audio_codec = "copy" if audio_codec in {"opus", "vorbis"} else "libopus"
            return OutputProfile(
                extension=".webm",
                container="webm",
                video_codec=resolved_video_codec,
                audio_codec=resolved_audio_codec,
                audio_bitrate=None if resolved_audio_codec == "copy" else audio_bitrate,
            )

        # Standard video output: MP4. Copy only if container-compatible enough for normal users.
        resolved_video_codec = "copy" if video_codec in {"h264", "avc1"} else "libx264"
        resolved_audio_codec = "copy" if audio_codec in {"aac", "mp4a"} else "aac"
        return OutputProfile(
            extension=".mp4",
            container="mp4",
            video_codec=resolved_video_codec,
            audio_codec=resolved_audio_codec,
            audio_bitrate=None if resolved_audio_codec == "copy" else audio_bitrate,
        )

    @staticmethod
    def _temp_output_path(output_path: Path) -> Path:
        return output_path.with_name(f".{output_path.stem}.tmp{output_path.suffix}")

    @staticmethod
    def _build_audio_ffmpeg_settings(profile: OutputProfile, thumbnail_path: Path | None) -> FfmpegSettings:
        settings = FfmpegSettings()
        if not thumbnail_path:
            return settings

        artwork = profile.embedded_artwork
        if artwork and artwork.enabled:
            settings.extra_output_kwargs.update(artwork.output_kwargs)
        return settings

    @staticmethod
    def _apply_profile_extension(output_path: Path, profile: OutputProfile) -> Path:
        extension = profile.extension if profile.extension.startswith(".") else f".{profile.extension}"
        if output_path.suffix.lower() != extension.lower():
            logger.warning("Output extension mismatch (%s); using %s", output_path.suffix, extension)
            return output_path.with_suffix(extension)
        return output_path

    @staticmethod
    def _replace_temp_output(temp_output: Path, output_path: Path) -> None:
        if not temp_output.exists():
            raise FileNotFoundError(f"Expected ffmpeg temp output was not created: {temp_output}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_output.replace(output_path)

    @staticmethod
    def _delete_sources(paths: list[Path], final_output: Path) -> None:
        final_resolved = final_output.resolve(strict=False)
        for path in paths:
            candidate = Path(path)
            if candidate.resolve(strict=False) == final_resolved:
                # If the raw input had the same name as the final target, os.replace
                # already replaced it. Deleting here would delete the final file.
                continue
            MediaAssembler._safe_unlink(candidate)

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            if path and path.exists():
                path.unlink()
        except Exception as cleanup_err:
            logger.warning("Failed to clean up %s: %s", path, cleanup_err)

    @staticmethod
    def _format_exception(error: Exception) -> str:
        stderr = getattr(error, "stderr", None)
        if stderr:
            try:
                return stderr.decode(errors="replace")
            except Exception:
                return str(stderr)
        return str(error)


def _normalize_codec(codec: str | None) -> str:
    if not codec:
        return ""
    normalized = str(codec).strip().lower()
    if normalized.startswith("avc1"):
        return "avc1"
    if normalized.startswith("mp4a"):
        return "mp4a"
    if normalized.startswith("av01"):
        return "av01"
    if normalized in {"h.264", "h264", "x264"}:
        return "h264"
    if normalized in {"h.265", "h265", "hevc", "x265"}:
        return "hevc"
    return normalized.split(".", 1)[0]

#TODO try to handle botrate loss better. without slowing processing down too much (ffmpeg probe is too expensive to run on every file)
# instead do ? or simply add some headroom to bitrate selection to avoid excessive downscaling => check tron legacy files for example: has 160kbps but sounds bad (even in .m4a)
def _normalize_bitrate_for_ffmpeg(value: str | int | None) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return f"{round(value / 1000)}k" if value > 10000 else f"{value}k"

    text = str(value).strip().lower()
    if not text:
        return None
    return text.replace("kbps", "k").replace("mbps", "M")
