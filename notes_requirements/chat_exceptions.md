RF-at-FH-Joanneum: I am trying to clean up exception handling and implementing an orchestration layer (application layer).
As far as I know exceptions should be handled below this layer -> how should this be done ... currently i am thinking about letting all methodsd called in orchestration return either a boolen success flag or let them know an use "DownloadResult"
starting work here: "download_playlist" in line 78-82

GitHub Copilot: For a clean orchestration layer, I'd recommend **having domain/infrastructure methods raise exceptions** (don't catch them), and **catch them only at the orchestration level** before returning `DownloadResult`.

This approach:
- Keeps lower layers focused on their domain logic
- Makes methods testable and predictable
- Centralizes error handling decisions at the orchestration layer
- Maintains clear separation of concerns

Here's how I'd refactor the `download_playlist` method:

````python
def download_playlist(self, playlist_url: str, download_dir: Path, options: DownloadOptions) -> List[DownloadResult]:
    """
    Download all videos from a YouTube playlist as video or audio files.
    
    Returns:
        List[DownloadResult]: A list of results for each video download in the playlist.
    """
    results: List[DownloadResult] = []
    playlist_obj = None
    playlist_dir = None
    
    try:
        # Let exceptions bubble up from vid_fetcher
        playlist_obj = self.vid_fetcher.get_playlist_obj(playlist_url)
        
        # Build playlist directory
        date = datetime.today().strftime('%Y_%m_') if not options.no_dir_date else ""
        playlist_dir = Path(download_dir) / f"{date}{sanitize_filename(playlist_obj.title)}"
        
        # Create directory - let OSInteractions raise if it fails
        if not playlist_dir.exists():
            logger.info(f"Creating playlist download directory: {playlist_dir}")
            playlist_dir.mkdir(parents=True, exist_ok=True)
        
        # Override pytube's video URL regex
        playlist_obj._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        logger.debug(f"Found {len(playlist_obj.video_urls)} videos in the playlist. {playlist_obj.title}")
        
        # Download each video
        for i, video in enumerate(playlist_obj.videos):
            logger.info(f'[{i + 1}/{len(playlist_obj.videos)}] Processing: {video.title}')
            result = self.download_single(download_dir=playlist_dir, options=options, video_obj=video)
            results.append(result)
    
    except Exception as e:
        # Handle playlist-level failures here
        logger.error(f"Playlist download failed: {e}")
        # Return empty list or partial results depending on when failure occurred
        return results
    
    # Log summary
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    logger.info(f"Playlist download completed: {success_count} succeeded, {fail_count} failed")
    
    if fail_count > 0:
        logger.warning("Failed downloads:")
        for result in results:
            if not result.success:
                logger.warning(f"  ✗ {result.video_title}: {'; '.join(result.errors)}")
    
    return results
````

**Key improvements:**

1. **Single try-except block** - catches playlist-level errors only
2. **Individual video errors** - handled by `download_single()` returning `DownloadResult`
3. **Lower layers don't catch** - `vid_fetcher`, `os_handler` methods should raise exceptions naturally
4. **Orchestration decides response** - convert exceptions to `DownloadResult` only here

**For other methods in this class**, apply the same pattern: let `StreamDownloadError`, `ConversionError`, etc. propagate, then catch them at the orchestration boundary.

# Exception Logging 
RF-at-FH-Joanneum: what does the layer on top yalling this method receive ?

GitHub Copilot: - The caller receives a PlaylistFetchError (which is a subclass of DownloadError).
- Its str() will contain the f-string message you built, so the caller sees "An error occurred while fetching the playlist {playlist_url}: {e}".
- Because you used "raise ... from e", the original exception e is attached as the new exception's __cause__ (and Python will show the chained traceback that the original exception was the direct cause).

Quick example of how an upstream layer would observe this:

````python
# python
try:
    fetch_playlist(...)  # the function that runs your except/raise
except DownloadError as ex:         # will catch PlaylistFetchError
    print(type(ex))                 # <class 'yourmodule.PlaylistFetchError'>
    print(str(ex))                  # "An error occurred while fetching the playlist ...: <original message>"
    print("cause:", ex.__cause__)   # the original exception instance (the `e` you raised from)
````

Gotcha: using "raise ... from e" sets __cause__ to e and suppresses the implicit __context__, so traceback shows the direct-cause chaining rather than the implicit context. If you want callers to handle the original exception type, either re-raise e or attach it as an attribute on PlaylistFetchError.

RF-at-FH-Joanneum: look at the logging. is this sensible? ... error will also be shown to a user in cli / gui

GitHub Copilot: Step-by-step review
1. Current behavior:
   - logger.error(...) logs a concise message (good).
   - logger.debug(..., exc_info=True) logs the full traceback to debug logs (good).
   - The raised PlaylistFetchError interpolates the original exception string into a message that will likely be shown to the user/CLI/GUI.

2. Problems / gotchas:
   - Double-reporting: logging the error here and also showing the exception message to the user can produce duplicated/noisy output.
   - User-facing content: the current exception message embeds the raw exception (e), which can be cryptic or leak internals. If the CLI/GUI displays the exception message, prefer a clear, actionable message.
   - Stack traces: keep full trace only in debug logs (exc_info=True). Do not send tracebacks to user-facing logs/outputs.

Recommended change
- Keep a concise error-level log (no exc_info).
- Keep the full traceback only at debug level (exc_info=True).
- Raise PlaylistFetchError with a short, user-friendly message. Keep the original exception as the cause (raise ... from e) so callers can inspect the underlying exception if needed.

Suggested code (replace the excerpt in video_fetcher.py):

````python
# ...existing code...
except Exception as e:
    logger.error("Failed to fetch playlist %s", playlist_url)  # concise, user-facing log
    logger.debug("Unexpected exception while fetching playlist %s", playlist_url, exc_info=True)  # full traceback for devs
    raise PlaylistFetchError(
        f"Could not fetch the playlist at {playlist_url}. Please check the URL and your network connection."
    ) from e
# ...existing code...
````

Extra notes
- If the upper layer (CLI/GUI) is responsible for showing errors to users, consider not logging at ERROR here to avoid duplicate messages — either log here and have the UI avoid re-logging, or let the UI handle presentation and log only debug info here.
- Consider internationalization / localization for user-facing messages if your app targets multiple languages.
- For more structured logs, include context fields (e.g., playlist_id) if available.

# older ------------------------------------------------
Short answer: your instinct is good — log detailed diagnostics where the error occurs, but propagate a clear error (or a result) to the top-level that decides user-facing action. Avoid duplicate noisy logs at every layer; log full exception info at the lowest layer and only user-friendly messages at the top.

Below are concrete recommendations and a small, minimal code patch you can drop into your file to illustrate the pattern.

Key rules
- Catch specific exceptions (ptf_ex.*, requests.RequestException, ffmpeg.Error/OSError) where you can add useful context.
- At low-level helpers: log.exception(...) with context, then raise a domain-specific exception (use raise ... from e to preserve the chain).
- At high-level entry points (download / CLI): catch the domain exceptions, log user-facing messages (logger.error) and decide retries/cleanup/reporting.
- Use a result object for reporting success/failure instead of relying on exceptions for flow control when you need aggregate status (e.g., playlist).
- Ensure cleanup of temp files in finally blocks so failed steps don’t leave junk.
- Don’t log the same stack trace in both the low-level method and the top-level handler (log full details at source, concise message at the top).

Example additions (custom exceptions + result type)
```python
# ...existing code...

from dataclasses import dataclass
from typing import List

class DownloadError(Exception):
    """Base exception for download-related errors."""

class VideoFetchError(DownloadError):
    pass

class StreamDownloadError(DownloadError):
    pass

class ConversionError(DownloadError):
    pass

class CombineError(DownloadError):
    pass

@dataclass
class DownloadResult:
    success: bool
    errors: List[str]

# ...existing code...
```

Pattern for low-level helpers: log full details and raise a domain exception
```python
# ...existing code...

def _get_video_obj(self, video_url: str) -> ptf.YouTube:
    try:
        return ptf.YouTube(video_url)
    except ptf_ex.VideoUnavailable as e:
        logger.exception("Video unavailable while creating video object: %s", video_url)
        raise VideoFetchError(f"video unavailable: {video_url}") from e
    except ptf_ex.AgeRestrictedError as e:
        logger.exception("Age restricted video: %s", video_url)
        raise VideoFetchError("age restricted") from e
    except Exception as e:
        logger.exception("Unexpected error creating YouTube object for %s", video_url)
        raise VideoFetchError("failed to fetch video object") from e

def _download_stream_type(self, video: ptf.YouTube, download_dir: str, base_filename: str, type: Enum) -> str:
    try:
        # stream selection logic...
        downloaded_path = stream.download(...)
        return downloaded_path
    except Exception as e:
        # include stream selection context
        logger.exception("Failed downloading %s stream for %s", self.stream_type_map[type], base_filename)
        raise StreamDownloadError(f"failed to download {self.stream_type_map[type]} for {base_filename}") from e

def _combine_streams(self, audio_path: str, video_path: str, output_path: str) -> None:
    try:
        # ffmpeg combine code...
    except Exception as e:
        logger.exception("ffmpeg failed combining %s + %s -> %s", video_path, audio_path, output_path)
        raise CombineError("ffmpeg combine failed") from e
    finally:
        # careful cleanup: only remove inputs on successful combine or if explicitly desired
        pass

# ...existing code...
```

Top-level orchestration: catch domain exceptions, aggregate, and return status
```python
# ...existing code...

def download_single(self, download_dir: str, options: DownloadOptions, video_url: str = None, video_obj: ptf.YouTube = None) -> DownloadResult:
    errors = []
    try:
        if video_obj is None:
            video_obj = self._get_video_obj(video_url)
    except VideoFetchError as e:
        # user-facing log, no stack trace here (already logged at source)
        logger.error("Cannot fetch video: %s", e)
        return DownloadResult(success=False, errors=[str(e)])

    base_filename = self._sanitize_filename(video_obj.title)
    try:
        if options.audio_only:
            audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
            if not audio_path:
                msg = "no audio stream available"
                logger.error(msg)
                return DownloadResult(False, [msg])
            # conversion may raise ConversionError
            self.stream_converter.convert_to_m4a(audio_path, ... )
        else:
            video_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.VIDEO)
            audio_path = self._download_stream_type(video_obj, download_dir, base_filename, self.StreamType.AUDIO)
            if not video_path or not audio_path:
                msg = "missing audio or video stream"
                logger.error(msg)
                return DownloadResult(False, [msg])
            self.stream_converter.combine_streams(audio_path, video_path, ...)
    except (StreamDownloadError, ConversionError, CombineError) as e:
        logger.error("Download failed for %s: %s", base_filename, e)
        return DownloadResult(False, [str(e)])
    except Exception as e:
        # unexpected
        logger.exception("Unexpected error during download_single for %s", base_filename)
        return DownloadResult(False, [str(e)])

    return DownloadResult(True, [])

# ...existing code...
```

Playlist orchestration: collect per-video results instead of letting a single failure stop everything
- iterate videos, call download_single, collect failing items in failed_list
- report summary at end, return overall result

Other practical tips
- Use specific exceptions everywhere where you can (ptf_ex.*, requests.RequestException, ffmpeg.Error).
- Use "raise ... from e" to preserve traceback chain when wrapping exceptions.
- Avoid logging.exception(...) at both low-level and top-level. Low-level: full stack; top-level: concise user message.
- Consider adding a retry wrapper for transient network steps (requests, pytube downloads).
- For cleanup: remove files only on success or when explicitly cleaning up failed temp files in finally (log the cleanup operations).
- For unit testing: return DownloadResult so tests can assert expected failures without parsing logs.

Summary
- Log full diagnostic details at the point of failure, then raise a domain-specific exception.
- Top-level (download / CLI) catches these, logs a concise message for the user, and decides next steps (retry, continue, abort).
- Use result objects for batch operations to aggregate errors and keep the program robust.

If you want, I can produce a small patch implementing these exception classes and converting one or two functions (e.g., _get_video_obj and download_single) to the exact pattern above.