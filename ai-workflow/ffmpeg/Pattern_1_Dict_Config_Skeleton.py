# Pattern 1: Extended Dict Configuration
# Simplest approach - minimal boilerplate

CODEC_PROFILES = {
    # ========================
    # AUDIO FORMATS
    # ========================
    "mp3": {
        "codec_family": "audio",
        "codec": "libmp3lame",
        "container": "mp3",
        "ffmpeg_args": ["-acodec", "libmp3lame", "-q:a", "2"],
        "output_ext": ".mp3",
        "supported_bitrates": ["64k", "96k", "128k", "192k", "256k", "320k"],
        "description": "MP3 Audio (Lossy, Wide Compatibility)"
    },
    "aac": {
        "codec_family": "audio",
        "codec": "aac",
        "container": "m4a",
        "ffmpeg_args": ["-acodec", "aac"],
        "output_ext": ".m4a",
        "supported_bitrates": ["64k", "96k", "128k", "192k", "256k"],
        "description": "AAC Audio (M4A, Apple Compatible)"
    },
    "opus": {
        "codec_family": "audio",
        "codec": "libopus",
        "container": "opus",
        "ffmpeg_args": ["-acodec", "libopus"],
        "output_ext": ".opus",
        "supported_bitrates": ["64k", "96k", "128k", "192k", "256k"],
        "description": "Opus Audio (Modern, High Quality at Low Bitrate)"
    },
    "vorbis": {
        "codec_family": "audio",
        "codec": "libvorbis",
        "container": "ogg",
        "ffmpeg_args": ["-acodec", "libvorbis", "-q:a"],
        "output_ext": ".ogg",
        "supported_bitrates": ["128k", "192k", "256k", "320k"],
        "description": "Vorbis Audio (OGG, Open Format)"
    },
    "flac": {
        "codec_family": "audio",
        "codec": "flac",
        "container": "flac",
        "ffmpeg_args": ["-acodec", "flac"],
        "output_ext": ".flac",
        "supported_bitrates": None,  # Lossless, bitrate not applicable
        "description": "FLAC Audio (Lossless)"
    },
    
    # ========================
    # VIDEO FORMATS
    # ========================
    "h264": {
        "codec_family": "video",
        "codec": "h264",
        "container": "mp4",
        "ffmpeg_args": ["-vcodec", "libx264", "-preset", "medium", "-crf", "23"],
        "output_ext": ".mp4",
        "supported_bitrates": None,  # Video bitrate handled separately if needed
        "description": "H.264 Video (MP4, High Compatibility)"
    },
    "h265": {
        "codec_family": "video",
        "codec": "h265",
        "container": "mkv",
        "ffmpeg_args": ["-vcodec", "libx265", "-preset", "medium", "-crf", "23"],
        "output_ext": ".mkv",
        "supported_bitrates": None,
        "description": "H.265 Video (HEVC, Better Compression)"
    },
    "vp9": {
        "codec_family": "video",
        "codec": "vp9",
        "container": "webm",
        "ffmpeg_args": ["-vcodec", "libvpx-vp9", "-cpu-used", "4", "-crf", "30"],
        "output_ext": ".webm",
        "supported_bitrates": None,
        "description": "VP9 Video (WebM, Web Friendly)"
    },
}

# ============================================
# USAGE PATTERNS (in stream_converter.py)
# ============================================
"""
def convert_audio(self, audio_path: Path, target_format: str, bitrate: str) -> Path:
    '''Convert audio to target format using dict-based profile'''
    profile = CODEC_PROFILES.get(target_format)
    if not profile:
        raise ValueError(f"Unsupported format: {target_format}")
    
    output_path = audio_path.with_suffix(profile["output_ext"])
    
    # Build FFMPEG command
    cmd = ["ffmpeg", "-i", str(audio_path)]
    cmd.extend(profile["ffmpeg_args"])
    
    # Add bitrate if applicable and provided
    if bitrate and profile["supported_bitrates"]:
        if bitrate not in profile["supported_bitrates"]:
            logger.warning(f"{bitrate} not in supported {target_format} bitrates")
        cmd.extend(["-b:a", bitrate])
    
    cmd.append(str(output_path))
    
    # Execute
    logger.debug(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    return output_path


# In CLI to list formats:
def list_formats():
    print("\\nAvailable Audio Formats:")
    for name, profile in CODEC_PROFILES.items():
        if profile["codec_family"] == "audio":
            print(f"  {name:12} - {profile['description']}")
            if profile["supported_bitrates"]:
                print(f"    Bitrates: {', '.join(profile['supported_bitrates'])}")
    
    print("\\nAvailable Video Formats:")
    for name, profile in CODEC_PROFILES.items():
        if profile["codec_family"] == "video":
            print(f"  {name:12} - {profile['description']}")
"""
