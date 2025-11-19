import os
import json
from pathlib import Path
from typing import Dict
import getpass

#from core.logger import logger

# ---------- CONSTANTS FOR SETUP & RESTORE -------------------
CURRENT_DIR = Path(__file__).resolve().parent   # → Python-YTRipper/source/core
SOURCE_DIR = CURRENT_DIR.parent                 # → Python-YTRipper/source
PROJECT_ROOT = SOURCE_DIR.parent                # → Python-YTRipper
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

PATH_TO_LOGS = str(LOGS_DIR)

DEFAULT_PREFS: Dict = {
    "default_download_directory": "~/Downloads",
    "audio_only": False,
    "audio_mp3": False,
    "warn_me": False,
    "preferred_audio_quality": "",
    "preferred_video_quality": "",
    "preferred_format": "",
    "preferred_abr": "",
    "preferred_resolution": "",
    "preferred_mime": "",
    "loglevel": "WARNING"
}
# -----------------------------

def current_username() -> str:
    """Return the current executing user's username; fallback to HOME parsing."""
    try:
        return getpass.getuser()
    except Exception:
        home = os.environ.get("HOME", "")
        return Path(home).name if home else ""

PATH_TO_PREFERENCES = str(CONFIG_DIR / f"user_settings_{current_username()}.json")

def read_preferences() -> Dict:
    """
    Read preferences from PATH_TO_PREFERENCES. If missing, create it with DEFAULT_PREFS.
    Returns a dict (never None).
    """
    if not os.path.exists(PATH_TO_PREFERENCES):
        try:
            os.makedirs(os.path.dirname(PATH_TO_PREFERENCES), exist_ok=True)
            with open(PATH_TO_PREFERENCES, 'w', encoding="utf-8") as f:
                json.dump(DEFAULT_PREFS, f, indent=4)
        except:
            return dict(DEFAULT_PREFS)
    else:
        with open(PATH_TO_PREFERENCES, 'r', encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else dict(DEFAULT_PREFS)

def write_preferences(prefs: Dict) -> None:
    """Write provided prefs dict to PATH_TO_PREFERENCES (best-effort)."""
    try:
        os.makedirs(os.path.dirname(PATH_TO_PREFERENCES), exist_ok=True)
        with open(PATH_TO_PREFERENCES, "w", encoding="utf-8") as fh:
            json.dump(prefs if isinstance(prefs, dict) else DEFAULT_PREFS, fh, indent=4)
    except Exception:
        # intentionally silent/fail-safe here; callers can log if desired
        pass