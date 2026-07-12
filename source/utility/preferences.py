import os
import json
from pathlib import Path
from typing import Dict
import getpass

# ---------- CONSTANTS FOR SETUP & RESTORE -------------------
CURRENT_DIR: Path = Path(__file__).resolve().parent   # → Python-YTRipper/source/core
SOURCE_DIR: Path = CURRENT_DIR.parent                 # → Python-YTRipper/source
PROJECT_ROOT: Path = SOURCE_DIR.parent                # → Python-YTRipper
CONFIG_DIR: Path = PROJECT_ROOT / "config"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
RUNTIME_DIR: Path = PROJECT_ROOT / "runtime"

PATH_TO_LOGS: Path = LOGS_DIR
PRESETS_DIR: Path = CONFIG_DIR / "presets"
IMMUTABLE_PRESETS_DIR: Path = PRESETS_DIR / "immutable"
CUSTOM_PRESETS_DIR: Path = PRESETS_DIR / "custom" # IMPORTANT: 9__custom_preset.json is full of garbage and should be ignored (used for testing edge cases in read/write prefs)
WEB_GUI_RUNTIME_DIR: Path = RUNTIME_DIR / "web-gui"
WEB_GUI_JOBS_DIR: Path = WEB_GUI_RUNTIME_DIR / "jobs"
WEB_GUI_EVENTS_PATH: Path = WEB_GUI_RUNTIME_DIR / "events.jsonl"

DEFAULT_PREFS: Dict = {
    "current_preset": "default",
    "default_download_directory": "~/Downloads/RipperDownloads",
    "audio_only": False,
    "audio_mp3": False,
    "show_preset": False,
    "preferred_audio_quality": "",
    "preferred_video_quality": "",
    "preferred_resolution": "",
    "preferred_abr": "",
    "preferred_format": "",
    "preferred_fps": 0,
    "visible_loglevel": "INFO",
    "donotconvert": False,
    "no_dir_date": False,
    "autotag": False,
    "prepare_tagging": False,
    "save_results": False
}

def current_username() -> str:
    """Return the current executing user's username; fallback to HOME parsing."""
    try:
        return getpass.getuser()
    except Exception:
        home = os.environ.get("HOME", "")
        return Path(home).name if home else ""

PATH_TO_DEFAULT_PREFERENCES: Path = CONFIG_DIR / f"default_settings_{current_username()}.json"
PATHS_TO_CUSTOM_PRESETS: tuple[Path, ...] = tuple(
    CUSTOM_PRESETS_DIR / f"{preset_id}__custom_preset.json"
    for preset_id in range(10)
)
PATHS_TO_IMMUTABLE_PRESETS: Dict[str, Path] = {
    "vh": IMMUTABLE_PRESETS_DIR / "vh__video_high.json",
    "vl": IMMUTABLE_PRESETS_DIR / "vl__video_low.json",
    "ah": IMMUTABLE_PRESETS_DIR / "ah__audio_high.json",
    "test": IMMUTABLE_PRESETS_DIR / "t__test_mode.json",
    "ds": IMMUTABLE_PRESETS_DIR / "ds__datasaver.json",
}


def _read_json_dict(path: Path) -> Dict:
    """Read a JSON file and merge dict content onto DEFAULT_PREFS."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        return dict(DEFAULT_PREFS)

    merged = dict(DEFAULT_PREFS)
    merged.update(data)
    return merged


def _create_default_preferences_file() -> Dict:
    """Create the default preferences file if possible, then return defaults."""
    try:
        PATH_TO_DEFAULT_PREFERENCES.parent.mkdir(parents=True, exist_ok=True)
        with open(PATH_TO_DEFAULT_PREFERENCES, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_PREFS, f, indent=4)
    except Exception:
        pass

    return dict(DEFAULT_PREFS)


def read_preferences(path: Path | None = None) -> Dict:
    """
    Read preferences from the default config or an explicit path.

    Startup/default behavior:
    - read PATH_TO_DEFAULT_PREFERENCES
    - create it with DEFAULT_PREFS if missing

    Explicit-path behavior:
    - do not create missing files
    - fall back to DEFAULT_PREFS on missing/invalid content

    Returns a dict (never None).
    """
    if path is None:
        if not PATH_TO_DEFAULT_PREFERENCES.exists():
            return _create_default_preferences_file()

        try:
            return _read_json_dict(PATH_TO_DEFAULT_PREFERENCES)
        except Exception:
            return dict(DEFAULT_PREFS)

    try:
        return _read_json_dict(path)
    except Exception:
        return dict(DEFAULT_PREFS)


def write_preferences(prefs: Dict, path: Path | None = None) -> bool:
    """Write provided prefs dict to the default config or an explicit path."""
    #TODO do not ever override "current_preset"-field ... 
    #TODO will be annoying to implement: never write (default) prefs to file if some values were incorrectly passed 
    # => "-a" instead of "-a true" (or "-q something", "-r 999") would cause the default prefs to be written with "audio_only": false, which is not what we want ...
    # handle with _normalize_save_config_path ?
    try:
        target_path = PATH_TO_DEFAULT_PREFERENCES if path is None else path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as fh:
            json.dump(prefs if isinstance(prefs, dict) else DEFAULT_PREFS, fh, indent=4)
        return True
    except Exception:
        return False
