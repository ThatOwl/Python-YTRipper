from dataclasses import dataclass, field
from pathlib import Path
import subprocess
from typing import Any

import ffmpeg as fpg

from utility.logger import get_logger
from utility.utils import OutputProfile, build_audio_embedded_artwork_profile

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

        artwork = profile.embedded_artwork
        if artwork and artwork.enabled:
            output_kwargs.update(artwork.output_kwargs)

        audio_input = fpg.input(str(input_path))

        if thumbnail_path and Path(thumbnail_path).exists() and artwork and artwork.enabled:
            output_kwargs.setdefault("vcodec", artwork.codec)
            image_input = fpg.input(str(thumbnail_path))
            stream = fpg.output(
                audio_input.audio,
                image_input.video,
                str(output_path),
                **output_kwargs,
            )
        else:
            if thumbnail_path and Path(thumbnail_path).exists() and not (artwork and artwork.enabled):
                logger.debug(
                    "Thumbnail input provided for %s, but output profile %s does not define embeddable artwork.",
                    output_path,
                    profile.container,
                )
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
            raise ValueError(
                "extra_output_args are not supported by the subprocess ffmpeg runner yet; "
                "prefer explicit output kwargs or graph stream selection."
            )

        cmd = fpg.compile(stream, overwrite_output=settings.overwrite)

        stdout_pipe = subprocess.PIPE if settings.capture_stdout else None
        stderr_pipe = subprocess.PIPE if settings.capture_stderr else None

        if settings.quiet:
            cmd[1:1] = ["-loglevel", "error"]

        completed = subprocess.run(
            cmd,
            stdout=stdout_pipe,
            stderr=stderr_pipe,
            check=False,
        )

        if completed.returncode != 0:
            raise subprocess.CalledProcessError(
                completed.returncode,
                cmd,
                output=completed.stdout,
                stderr=completed.stderr,
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
                embedded_artwork=build_audio_embedded_artwork_profile("mp3"),
            )
            output_path = Path(output_path).with_suffix(".mp3")
        else:
            profile = OutputProfile(
                extension=".m4a",
                container="m4a",
                audio_codec="aac",
                audio_bitrate=_normalize_bitrate_for_ffmpeg(audio_bitrate),
                embedded_artwork=build_audio_embedded_artwork_profile("m4a"),
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
