from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ffmpeg as fpg

from utility.logger import get_logger
from utility.utils import OutputProfile

logger = get_logger(__name__, "StreamConverter_debug.log")


@dataclass
class FfmpegSettings:
    """Execution settings for ffmpeg operations."""

    overwrite: bool = True
    quiet: bool = True
    capture_stdout: bool = True
    capture_stderr: bool = True
    # Prefer kwargs for ffmpeg-python, because raw repeated args are awkward there.
    # Example: {"movflags": "+faststart"}
    extra_output_kwargs: dict[str, Any] = field(default_factory=dict)
    # Kept as a future escape hatch. This first pass does not rely on it.
    extra_output_args: list[str] = field(default_factory=list)


class StreamConverter:
    """
    Low-level adapter around ffmpeg-python.

    Owns:
    - constructing ffmpeg input/output graphs
    - running ffmpeg
    - returning the explicit output path

    Does not own:
    - final filename policy
    - deleting source files
    - deleting thumbnails
    - replacing final files
    - YouTube/pytubefix-specific logic
    """

    @staticmethod
    def convert_audio_new(
        input_path: Path,
        output_path: Path,
        profile: OutputProfile,
        settings: FfmpegSettings | None = None,
        thumbnail_path: Path | None = None,
    ) -> Path:
        """Convert/copy one audio input to the explicit output path."""
        settings = settings or FfmpegSettings()
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Audio input does not exist: {input_path}")

        output_kwargs: dict[str, Any] = dict(settings.extra_output_kwargs)

        if profile.audio_codec:
            output_kwargs["acodec"] = profile.audio_codec

        if profile.audio_bitrate and profile.audio_codec != "copy":
            output_kwargs["audio_bitrate"] = profile.audio_bitrate

        audio_input = fpg.input(str(input_path))

        if thumbnail_path and Path(thumbnail_path).exists():
            # Minimal cover-art support. Stream selection is explicit enough to avoid
            # MediaAssembler policy leaking into this class, but detailed tagging can
            # be improved later in a Metadata/Tagging service.
            image_input = fpg.input(str(thumbnail_path))
            stream = fpg.output(
                audio_input,
                image_input,
                str(output_path),
                **output_kwargs,
            )
        else:
            stream = fpg.output(audio_input, str(output_path), **output_kwargs)

        StreamConverter._run(stream, settings)
        return output_path

    @staticmethod
    def combine_streams_new(
        video_path: Path,
        audio_path: Path | None,
        output_path: Path,
        profile: OutputProfile,
        settings: FfmpegSettings | None = None,
    ) -> Path:
        """Mux/transcode video and optional audio into the explicit output path."""
        settings = settings or FfmpegSettings()
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video input does not exist: {video_path}")
        if audio_path is not None and not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio input does not exist: {audio_path}")

        output_kwargs: dict[str, Any] = dict(settings.extra_output_kwargs)

        if profile.video_codec:
            output_kwargs["vcodec"] = profile.video_codec
        if profile.audio_codec:
            output_kwargs["acodec"] = profile.audio_codec
        if profile.video_bitrate and profile.video_codec != "copy":
            output_kwargs["video_bitrate"] = profile.video_bitrate
        if profile.audio_bitrate and profile.audio_codec != "copy":
            output_kwargs["audio_bitrate"] = profile.audio_bitrate

        # Good default for MP4 playback/streaming friendliness. This is still an
        # ffmpeg output option, not an application policy decision.
        if profile.container == "mp4":
            output_kwargs.setdefault("movflags", "+faststart")

        video_input = fpg.input(str(video_path))

        if audio_path is None:
            stream = fpg.output(video_input, str(output_path), **output_kwargs)
        else:
            audio_input = fpg.input(str(audio_path))
            stream = fpg.output(video_input, audio_input, str(output_path), **output_kwargs)

        StreamConverter._run(stream, settings)
        return output_path

    @staticmethod
    def _run(stream, settings: FfmpegSettings) -> None:
        if settings.extra_output_args:
            # ffmpeg-python's kwargs are the safer first-class path. Keeping this as
            # a best-effort escape hatch for future specialized flags.
            stream = stream.global_args(*settings.extra_output_args)

        stream.run(
            capture_stdout=settings.capture_stdout,
            capture_stderr=settings.capture_stderr,
            overwrite_output=settings.overwrite,
            quiet=settings.quiet,
        )

    # Compatibility wrappers. These keep existing call sites alive during migration,
    # but MediaAssembler should be preferred for new code.
    @staticmethod
    def combine_streams(audio_path: Path, video_path: Path, output_path: Path) -> None:
        profile = OutputProfile(
            extension=".mp4",
            container="mp4",
            video_codec="copy",
            audio_codec="aac",
        )
        StreamConverter.combine_streams_new(video_path, audio_path, output_path, profile, FfmpegSettings())

    @staticmethod
    def convert_audio(
        audio_path: Path,
        output_path: Path,
        thumbnail_path: Path | None = None,
        audio_bitrate: str = "",
        audio_mp3: bool = False,
    ) -> None:
        if audio_mp3:
            profile = OutputProfile(
                extension=".mp3",
                container="mp3",
                audio_codec="libmp3lame",
                audio_bitrate=_normalize_bitrate_for_ffmpeg(audio_bitrate),
            )
            output_path = Path(output_path).with_suffix(".mp3")
        else:
            profile = OutputProfile(
                extension=".m4a",
                container="m4a",
                audio_codec="aac",
                audio_bitrate=_normalize_bitrate_for_ffmpeg(audio_bitrate),
            )
            output_path = Path(output_path).with_suffix(".m4a")

        StreamConverter.convert_audio_new(audio_path, output_path, profile, FfmpegSettings(), thumbnail_path)


def _normalize_bitrate_for_ffmpeg(value: str | int | None) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return f"{round(value / 1000)}k" if value > 10000 else f"{value}k"

    text = str(value).strip().lower()
    if not text:
        return None
    return text.replace("kbps", "k").replace("mbps", "M")
