GitHub Copilot

Short explanation — what a retry wrapper is and common structure
- A retry wrapper retries a failing operation (usually transient errors like network I/O) a configurable number of times, with a delay between attempts.  
- Common features: exceptions to catch, max attempts, initial backoff, backoff multiplier (exponential), optional jitter, optional on-retry callback/logging, and optional total timeout or circuit-breaker integration.  
- Typical implementations: decorator (apply to functions), function wrapper (retry_call), or context manager. Use decorators for reusable functions and retry_call for inline use (e.g., third-party methods you can't easily decorate).

Suggested policy:
- Only retry on transient/expected exceptions (network, temporary server errors). Don’t retry on permanent errors (invalid URL, authentication failure).
- Log each retry attempt with context at INFO/WARNING; log final failure with full stack at DEBUG/ERROR at the source of failure.

Example implementation and small integration into your pytube_interface.py
- Adds retry decorator + retry_call helper.
- Shows example usage: decorating _get_video_obj and using retry_call around stream.download.

````python
# ...existing code...
import time
import random
import functools
# ...existing code...

def retry(exceptions=(Exception,), retries: int = 3, backoff: float = 1.0, backoff_factor: float = 2.0,
          jitter: float = 0.25, logger=None):
    """
    Decorator to retry a function on specified exceptions.
    - exceptions: tuple of exception types to catch and retry on
    - retries: number of retry attempts (not counting the first try)
    - backoff: initial sleep seconds before first retry
    - backoff_factor: multiplier for exponential backoff
    - jitter: max random seconds added to backoff to avoid thundering herd
    - logger: optional logger to record retry attempts
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts_left = retries
            delay = backoff
            attempt = 1
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempts_left <= 0:
                        # no more retries — re-raise
                        raise
                    if logger:
                        logger.warning("Transient error in %s (attempt %d/%d): %s — retrying in %.2fs",
                                       func.__name__, attempt, retries + 1, e, delay)
                    sleep_time = delay + random.uniform(0, jitter)
                    time.sleep(sleep_time)
                    attempts_left -= 1
                    delay *= backoff_factor
                    attempt += 1
        return wrapper
    return decorator

def retry_call(callable_fn, exceptions=(Exception,), retries: int = 3, backoff: float = 1.0,
               backoff_factor: float = 2.0, jitter: float = 0.25, logger=None):
    """Inline retry helper for callables (useful for third-party methods)."""
    attempts_left = retries
    delay = backoff
    attempt = 1
    while True:
        try:
            return callable_fn()
        except exceptions as e:
            if attempts_left <= 0:
                raise
            if logger:
                logger.warning("Transient error (inline) attempt %d/%d: %s — retrying in %.2fs",
                               attempt, retries + 1, e, delay)
            time.sleep(delay + random.uniform(0, jitter))
            attempts_left -= 1
            delay *= backoff_factor
            attempt += 1

# ...existing code...

# Example: decorate _get_video_obj to retry on transient pytube errors
@retry(exceptions=(ptf_ex.VideoUnavailable, ptf_ex.RegexMatchError, ptf_ex.LiveStreamError, Exception),
       retries=2, backoff=1.0, backoff_factor=2.0, jitter=0.2, logger=logger)
def _get_video_obj_with_retry(self, video_url: str) -> ptf.YouTube:
    # delegate to existing logic (keeps original exception handling and logging)
    return YouTubeDownloader._get_video_obj.__wrapped__(self, video_url) if hasattr(YouTubeDownloader._get_video_obj, "__wrapped__") else YouTubeDownloader._get_video_obj(self, video_url)

# ...existing code...

# Example inline use in _download_stream_type around the download call:
# replace:
#     downloaded_path = stream.download(...)
# with:
#     try:
#         downloaded_path = retry_call(lambda: stream.download(
#             output_path=download_dir,
#             filename=f"{base_filename}_{self.stream_type_map[type]}.{ext}",
#             skip_existing=True,
#             timeout=5,
#             max_retries=3
#         ), exceptions=(OSError, IOError, Exception), retries=3, backoff=1.0, logger=logger)
#     except Exception as e:
#         logger.exception("Final failure downloading stream for %s: %s", base_filename, e)
#         raise StreamDownloadError(...) from e

# ...existing code...
````

Notes and usage tips
- Use the decorator where you control the function definition; use retry_call for in-method third-party actions (e.g., stream.download(), requests.get()).
- Tune retries/backoff/jitter per operation type: thumbnail download may need different parameters than large binary stream downloads.
- Limit which exceptions are retried. Wrapping too-broadly may hide permanent errors.
- On final failure: log full exception with logger.exception at the point you give up, then raise a domain-specific error (you already do this pattern).
- For multithreaded execution, these helpers are thread-safe (stateless) and safe to share.

If you want, I can apply the inline retry_call replacement in your _download_stream_type and wrap the thumbnail and playlist fetches with retries in the file.