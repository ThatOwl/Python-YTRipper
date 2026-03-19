#TODO: reduce includes after renaming / moving methods is done
from xml.etree.ElementInclude import include
import pytubefix as ptf
from enum import Enum

from core.logger import get_logger
from core.utils import DownloadError, DownloadOptions, DownloadResult, QUALITY_ALIAS_MAP

class StreamSelectionError(DownloadError):
    pass


logger = get_logger(__name__, 'SelectStream_debug.log')


class SelectStream:
    """docstring for SelectStream."""
    def __init__(self, arg):
        self.arg = arg

    def select_stream_audio(self, video: ptf.YouTube, options: DownloadOptions) -> ptf.Stream:
        """Select an audio stream based on DownloadOptions preferences."""
        try:
            q = video.streams.filter(type='audio')
            stream = None

            # 1) preferred_abr exact match
            if options and options.preferred_abr:
                stream = q.filter(abr=options.preferred_abr).first()
                logger.debug(f"[select] audio preferred abr={options.preferred_abr} -> {stream}")

            # 2) preferred_audio_quality via aliases (optionally constrained by mime)
            if not stream and options and options.preferred_audio_quality:
                qual_key = QUALITY_ALIAS_MAP.get(options.preferred_audio_quality.strip().lower())
                aq = q.filter(mime_type=options.preferred_mime) if options.preferred_mime else q
                if qual_key == "high":
                    stream = aq.order_by('abr').desc().first()
                elif qual_key == "low":
                    stream = aq.order_by('abr').asc().first()
                elif qual_key == "medium":
                    candidates = list(aq.order_by('abr'))
                    if candidates:
                        idx = len(candidates) // 2  # upper-middle for even counts
                        stream = candidates[idx]
                logger.debug(f"[select] audio quality={options.preferred_audio_quality} (mime={options.preferred_mime or 'any'}) -> {stream}")

            # 3) best available (highest abr)
            if not stream:
                stream = q.order_by('abr').desc().first()
                logger.debug(f"[select] audio fallback best abr -> {stream}")

            if not stream:
                raise StreamSelectionError("No audio stream available")
        
            return stream
            
        except Exception as e:
            raise StreamSelectionError(f"Stream selection failed: {e}") from e
    

    def select_stream_video(self, video: ptf.YouTube, options: DownloadOptions) -> ptf.Stream:
        """Select a video stream based on DownloadOptions preferences."""
        try:
            q = video.streams.filter(type='video', progressive=False)
            stream = None

            # Helper to filter by FPS preference
            def apply_fps_filter(candidates_list, preferred_fps):
                """Filter candidates by FPS preference: 0=any, 30=prefer 30fps, 60=prefer 60fps"""
                if not candidates_list or preferred_fps == 0:
                    return candidates_list
                # Extract fps from stream strings like "60fps" -> 60
                result = []
                for stream_obj in candidates_list:
                    try:
                        stream_fps = int(str(stream_obj.fps).rstrip('fps')) if stream_obj.fps else 0
                        if stream_fps == preferred_fps:
                            result.append(stream_obj)
                    except (ValueError, AttributeError):
                        pass
                return result if result else candidates_list  # fallback to all if none match

            # 1) preferred_resolution (DASH first, then progressive)
            if options and options.preferred_resolution:
                stream = q.filter(resolution=options.preferred_resolution).order_by('fps').desc().first() if options.preferred_fps == 60 else q.filter(resolution=options.preferred_resolution).order_by('fps').asc().first() if options.preferred_fps == 30 else q.filter(resolution=options.preferred_resolution).first()
                logger.debug(f"[select] video preferred resolution={options.preferred_resolution} fps={options.preferred_fps or 'any'} (DASH) -> {stream}")
                if not stream:
                    candidates = list(video.streams.filter(type='video', progressive=True, resolution=options.preferred_resolution).order_by('fps'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None
                    logger.debug(f"[select] video preferred resolution={options.preferred_resolution} (progressive) -> {stream}")

            # 2) preferred_mime (best resolution within mime, considering FPS)
            if not stream and options and options.preferred_mime:
                candidates = list(q.filter(mime_type=options.preferred_mime).order_by('resolution'))
                candidates = apply_fps_filter(candidates, options.preferred_fps)
                stream = candidates[-1] if candidates else None  # highest resolution
                logger.debug(f"[select] video preferred mime={options.preferred_mime} fps={options.preferred_fps or 'any'} (DASH) -> {stream}")
                if not stream:
                    candidates = list(video.streams.filter(type='video', progressive=True, mime_type=options.preferred_mime).order_by('resolution'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None
                    logger.debug(f"[select] video preferred mime={options.preferred_mime} (progressive) -> {stream}")

            # 3) preferred_video_quality via aliases (resolution + FPS consideration)
            if not stream and options and options.preferred_video_quality:
                qual_key = QUALITY_ALIAS_MAP.get(options.preferred_video_quality.strip().lower())
                candidates = list(q.order_by('resolution'))
                candidates = apply_fps_filter(candidates, options.preferred_fps)
                
                if qual_key == "high":
                    stream = candidates[-1] if candidates else None  # highest resolution
                elif qual_key == "low":
                    stream = candidates[0] if candidates else None  # lowest resolution
                elif qual_key == "medium":
                    if candidates:
                        idx = len(candidates) // 2  # middle resolution
                        stream = candidates[idx]
                logger.debug(f"[select] video quality={options.preferred_video_quality} fps={options.preferred_fps or 'any'} -> {stream}")
        
            # 4) best available (highest resolution, considering FPS)
            if not stream:
                candidates = list(q.order_by('resolution'))
                candidates = apply_fps_filter(candidates, options.preferred_fps)
                stream = candidates[-1] if candidates else None  # highest resolution
                logger.debug(f"[select] video fallback best resolution (DASH) fps={options.preferred_fps or 'any'} -> {stream}")
                if not stream:
                    candidates = list(video.streams.filter(type='video').order_by('resolution'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None

            return stream
    
        except Exception as e:
            raise StreamSelectionError(f"Stream selection failed: {e}") from e
    
    # OLD !!! ------------------------------------------------------
    def _select_stream(self, video: ptf.YouTube, str_type: Enum, options: DownloadOptions) -> ptf.Stream:
        """
            Select a pytubefix Stream for audio or video using preferences in DownloadOptions.
            Priority:
            - VIDEO: preferred_resolution > preferred_mime > preferred_video_quality (with FPS consideration) > best available
            - AUDIO: preferred_abr > preferred_audio_quality > best available
        Returns:
            ptf.Stream
        Raises:
            StreamSelectionError
        """
        try:
            if str_type == self.StreamType.AUDIO:
                q = video.streams.filter(type='audio')
                stream = None

                # 1) preferred_abr exact match
                if options and options.preferred_abr:
                    stream = q.filter(abr=options.preferred_abr).first()
                    logger.debug(f"[select] audio preferred abr={options.preferred_abr} -> {stream}")

                # 2) preferred_audio_quality via aliases (optionally constrained by mime)
                if not stream and options and options.preferred_audio_quality:
                    qual_key = QUALITY_ALIAS_MAP.get(options.preferred_audio_quality.strip().lower())
                    aq = q.filter(mime_type=options.preferred_mime) if options.preferred_mime else q
                    if qual_key == "high":
                        stream = aq.order_by('abr').desc().first()
                    elif qual_key == "low":
                        stream = aq.order_by('abr').asc().first()
                    elif qual_key == "medium":
                        candidates = list(aq.order_by('abr'))
                        if candidates:
                            idx = len(candidates) // 2  # upper-middle for even counts
                            stream = candidates[idx]
                    logger.debug(f"[select] audio quality={options.preferred_audio_quality} (mime={options.preferred_mime or 'any'}) -> {stream}")

                # 3) best available (highest abr)
                if not stream:
                    stream = q.order_by('abr').desc().first()
                    logger.debug(f"[select] audio fallback best abr -> {stream}")

                if not stream:
                    raise StreamSelectionError("No audio stream available")
                return stream

            else:
                # VIDEO
                q = video.streams.filter(type='video', progressive=False)
                stream = None

                # Helper to filter by FPS preference
                def apply_fps_filter(candidates_list, preferred_fps):
                    """Filter candidates by FPS preference: 0=any, 30=prefer 30fps, 60=prefer 60fps"""
                    if not candidates_list or preferred_fps == 0:
                        return candidates_list
                    # Extract fps from stream strings like "60fps" -> 60
                    result = []
                    for stream_obj in candidates_list:
                        try:
                            stream_fps = int(str(stream_obj.fps).rstrip('fps')) if stream_obj.fps else 0
                            if stream_fps == preferred_fps:
                                result.append(stream_obj)
                        except (ValueError, AttributeError):
                            pass
                    return result if result else candidates_list  # fallback to all if none match

                # 1) preferred_resolution (DASH first, then progressive)
                if options and options.preferred_resolution:
                    stream = q.filter(resolution=options.preferred_resolution).order_by('fps').desc().first() if options.preferred_fps == 60 else q.filter(resolution=options.preferred_resolution).order_by('fps').asc().first() if options.preferred_fps == 30 else q.filter(resolution=options.preferred_resolution).first()
                    logger.debug(f"[select] video preferred resolution={options.preferred_resolution} fps={options.preferred_fps or 'any'} (DASH) -> {stream}")
                    if not stream:
                        candidates = list(video.streams.filter(type='video', progressive=True, resolution=options.preferred_resolution).order_by('fps'))
                        candidates = apply_fps_filter(candidates, options.preferred_fps)
                        stream = candidates[-1] if candidates else None
                        logger.debug(f"[select] video preferred resolution={options.preferred_resolution} (progressive) -> {stream}")

                # 2) preferred_mime (best resolution within mime, considering FPS)
                if not stream and options and options.preferred_mime:
                    candidates = list(q.filter(mime_type=options.preferred_mime).order_by('resolution'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None  # highest resolution
                    logger.debug(f"[select] video preferred mime={options.preferred_mime} fps={options.preferred_fps or 'any'} (DASH) -> {stream}")
                    if not stream:
                        candidates = list(video.streams.filter(type='video', progressive=True, mime_type=options.preferred_mime).order_by('resolution'))
                        candidates = apply_fps_filter(candidates, options.preferred_fps)
                        stream = candidates[-1] if candidates else None
                        logger.debug(f"[select] video preferred mime={options.preferred_mime} (progressive) -> {stream}")

                # 3) preferred_video_quality via aliases (resolution + FPS consideration)
                if not stream and options and options.preferred_video_quality:
                    qual_key = QUALITY_ALIAS_MAP.get(options.preferred_video_quality.strip().lower())
                    candidates = list(q.order_by('resolution'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    
                    if qual_key == "high":
                        stream = candidates[-1] if candidates else None  # highest resolution
                    elif qual_key == "low":
                        stream = candidates[0] if candidates else None  # lowest resolution
                    elif qual_key == "medium":
                        if candidates:
                            idx = len(candidates) // 2  # middle resolution
                            stream = candidates[idx]
                    logger.debug(f"[select] video quality={options.preferred_video_quality} fps={options.preferred_fps or 'any'} -> {stream}")
            
                # 4) best available (highest resolution, considering FPS)
                if not stream:
                    candidates = list(q.order_by('resolution'))
                    candidates = apply_fps_filter(candidates, options.preferred_fps)
                    stream = candidates[-1] if candidates else None  # highest resolution
                    logger.debug(f"[select] video fallback best resolution (DASH) fps={options.preferred_fps or 'any'} -> {stream}")
                    if not stream:
                        candidates = list(video.streams.filter(type='video').order_by('resolution'))
                        candidates = apply_fps_filter(candidates, options.preferred_fps)
                        stream = candidates[-1] if candidates else None

                return stream
        except Exception as e:
            raise StreamSelectionError(f"Stream selection failed: {e}") from e
    