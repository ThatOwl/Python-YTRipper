import os
import re
import csv
import json
import shutil
import time
import difflib
import argparse
from collections import Counter, defaultdict
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TRCK
try:
    import musicbrainzngs
    _MB_AVAILABLE = True
except ImportError:
    _MB_AVAILABLE = False

CONFIDENCE_THRESHOLD = 85
AUDIO_EXTENSIONS = (".mp3", ".m4a")

# MusicBrainz enrichment settings
MB_APP_NAME = "python-autotagger"
MB_APP_VERSION = "1.0"
MB_CONTACT = "github.com/ThatOwl"
MB_MIN_SCORE = 75        # Minimum MB API score (0-100) to accept a result
MB_TITLE_MIN_SIM = 0.75  # Minimum fuzzy title similarity to accept a result (raised from 0.60 to reduce false positives)
MB_REQUEST_DELAY = 1.1   # Seconds between MB requests (rate limit is 1/sec)

# Genre/category folder names that should NOT be treated as artist names
GENRE_FOLDERS = {
    "filmmusik", "serienmusik", "spielemusik", "musik", "music",
    "soundtracks", "soundtrack", "loose", "various", "various artists",
    "compilations", "downloads", "unsorted", "misc", "other",
}

JUNK_PATTERNS = [
    r"^\d{4}(?:_\d{2}){0,2}_",
    r"\(Official.*?\)",
    r"\(Full Album.*?\)",
    r"Full Album",
    r"\(.*?Soundtrack.*?\)",
    r"\(.*?Trailer.*?\)",
    r"\(\d+\)$",
    r"\(Remastered.*?\)",
    r"\(Mono.*?\)",
    r"\(Stereo.*?\)",
    r"\(Live.*?\)",
    r"\(HD.*?\)",
    r"\(debut.*?\)",
    r"\(Audio.*?\)",
    r"\(Video.*?\)",
    r"\(.*?Version.*?\)",
    r"\(.*?Remix.*?\)",
    r"\(.*?Music\)",
    r"\[.*?\]",
    r"\blyrics?\b",
    r"\.wmv$",
    r"\bHQ\b",
]

ALLOWED_CHARS = r"[^a-zA-Z0-9äöüÄÖÜß&'\-\. ]"

# Filename cleanup patterns for stripping leading track numbers.
# Applied to filename stem only (extension is preserved).
TRACK_PREFIX_PATTERNS = [
    # "01 - Title", "1. Title", "003_Title"
    r"^\s*(?:0?\d{1,2}|1\d{2})\s*[-._)\]]+\s*",
    # "[03] Title", "(03) Title"
    r"^\s*[\[(](?:0?\d{1,2}|1\d{2})[\])]\s*",
    # "Track 03 - Title"
    r"^\s*track\s*(?:0?\d{1,2}|1\d{2})\s*[-._)\]]+\s*",
    # "03 Title" (space-separated)
    r"^\s*(?:0?\d{1,2}|1\d{2})\s+",
]


def _safe_label(text):
    """Create a filesystem-safe label from folder names."""
    label = re.sub(r"[^\w\-.]+", "_", text.strip())
    label = re.sub(r"_+", "_", label).strip("._")
    return label or "root"


def _dated_prefix(root_name):
    """Return YYYY_MM_DD_<root-name> prefix for report files."""
    return f"{time.strftime('%Y_%m_%d')}_{_safe_label(root_name)}"

def clean_string(text):
    for pattern in JUNK_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = text.replace("_", " ")
    text = re.sub(ALLOWED_CHARS, "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_folder_album(text):
    """Clean album text extracted from folder name."""
    # Strip date prefix: "2008_KungFu" → "KungFu", "2026_02_Name" → "Name"
    text = re.sub(r"^\d{4}(?:_\d{2}){0,2}_", "", text)
    text = text.replace("_", " ")
    text = re.sub(r"\(Full Album.*?\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Full Album", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\+\s*Vid[ée]o", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(Expanded Edition.*?\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(Original Motion Picture Soundtrack\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(Original Game Soundtrack.*?\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(Soundtrack\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*-?\s*Album\s*Playlist\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*-\s*Full\s*$", "", text, flags=re.IGNORECASE)
    # Only strip standalone "Soundtrack" / "Ost" when it's the ENTIRE text
    text = re.sub(r"^\s*Soundtrack\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Ost\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(ALLOWED_CHARS, "", text)
    text = re.sub(r"[\s\-]+$", "", text)  # Strip trailing dashes/whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_artist_from_title(title, artist):
    """Remove artist name from the beginning/end of the title if present."""
    if not artist or not title:
        return title
    a = artist.lower().strip()
    t = title.strip()
    t_lower = t.lower()
    # Strip from beginning: "Ray Charles Moonlight" → "Moonlight"
    if t_lower.startswith(a) and len(t) > len(a):
        after = t[len(a):]
        stripped = re.sub(r"^[\s\-]+", "", after).strip()
        if stripped:
            return stripped
    # Strip from end: "Moonlight Ray Charles" → "Moonlight"
    if t_lower.endswith(a) and len(t) > len(a):
        before = t[: len(t) - len(a)]
        stripped = re.sub(r"[\s\-]+$", "", before).strip()
        if stripped:
            return stripped
    return title


def _find_dash_outside_parens(text):
    """Return index of first ' - ' NOT inside parentheses, or -1."""
    depth = 0
    i = 0
    while i < len(text) - 2:
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth = max(0, depth - 1)
        elif text[i:i + 3] == ' - ' and depth == 0:
            return i
        i += 1
    return -1


def parse_folder_name(raw_folder_name):
    """Parse raw folder name into artist and album components.

    Works on the raw name BEFORE character cleaning so that special
    separators (em-dash, special unicode chars) are still available.
    """
    raw = raw_folder_name.strip()

    # Strip date prefix: "2026_02_Rammstein" or "2008_KungFu" or "2020_01_28_X"
    m = re.match(r"^\d{4}(?:_\d{2}){0,2}_(.+)$", raw)
    if m:
        raw = m.group(1).strip()

    # 1. Em-dash separator: "Artist – Album"
    for sep in [" – ", " — "]:
        if sep in raw:
            parts = raw.split(sep, 1)
            artist_raw = parts[0].strip()
            album_raw = parts[1].strip()
            artist_clean = clean_string(artist_raw)
            # Handle "Ray Charles, The Very Best Of" → strip artist repetition
            m_prefix = re.match(
                re.escape(artist_clean) + r"\s*,\s*",
                album_raw,
                re.IGNORECASE,
            )
            if m_prefix:
                album_raw = album_raw[m_prefix.end():]
            album = clean_folder_album(album_raw)
            return {"artist": artist_clean, "album": album}

    # 2. Dash separator (only outside parentheses): "Artist - Album (junk)"
    dash_pos = _find_dash_outside_parens(raw)
    if dash_pos >= 0:
        left = raw[:dash_pos].strip()
        right = raw[dash_pos + 3:].strip()
        # If right side is just a year, treat left as album (no artist)
        if re.match(r"^\d{4}$", right):
            return {"artist": "", "album": clean_string(left)}
        # If right side is just "Soundtrack" / "OST", album = left side
        if re.match(
            r"^(Soundtrack|OST|Ost|SoundTrack)$", right, re.IGNORECASE
        ):
            return {"artist": "", "album": clean_string(left)}
        artist = clean_string(left)
        album = clean_folder_album(right)
        return {"artist": artist, "album": album}

    # 3. Special character separators (⌛, ♫, etc.)
    m = re.match(r"(.+?)\s*[⌛🎵🎶♫♪]\s*(.+)", raw)
    if m:
        artist = clean_string(m.group(1).strip())
        album = clean_folder_album(m.group(2).strip())
        return {"artist": artist, "album": album}

    # 4. "Artist (album info, year)" pattern
    m = re.match(r"^(.+?)\s*\((.+)\)\s*$", raw)
    if m:
        artist = clean_string(m.group(1).strip())
        info = m.group(2).strip()
        # Strip common suffixes inside parentheses
        info = re.sub(r"\s*-\s*Full\s*$", "", info, flags=re.IGNORECASE)
        album = re.sub(r",?\s*\d{4}\s*", "", info).strip().rstrip(",").strip()
        if (
            re.match(
                r"^(full\s*album|soundtrack|re-?release|reissue|remaster(ed)?)$",
                album,
                re.IGNORECASE,
            )
            or not album
        ):
            album = ""
        else:
            album = clean_string(album)
        return {"artist": artist, "album": album}

    # 5. "Something Full Album" suffix → album only, no clear artist
    stripped = re.sub(
        r"\s+Full\s+Album\s*$", "", raw, flags=re.IGNORECASE
    ).strip()
    if stripped != raw:
        return {"artist": "", "album": clean_string(stripped)}

    # 6. "Something Soundtrack/OST" suffix → album, not artist
    stripped = re.sub(
        r"\s+(Soundtrack|OST|Ost|SoundTrack)\s*$", "", raw, flags=re.IGNORECASE
    ).strip()
    if stripped != raw:
        return {"artist": "", "album": clean_string(raw)}

    # 7. Fallback: treat as artist only
    return {"artist": clean_string(raw), "album": ""}

def read_tags(path):
    try:
        if path.endswith(".mp3"):
            audio = MP3(path)
            title = str(audio.get("TIT2", "")).strip()
            artist = str(audio.get("TPE1", "")).strip()
        else:
            audio = MP4(path)
            title = audio.tags.get("\xa9nam", [""])[0] if audio.tags else ""
            artist = audio.tags.get("\xa9ART", [""])[0] if audio.tags else ""
        return title, artist
    except:
        return "", ""

def strong_tags(title, artist):
    return bool(title and artist)

def weak_tags(title, artist):
    return bool(title) and not artist

def _matches_artist(text, folder_artist):
    """Check if text matches (or starts with) the known folder artist."""
    t = text.lower().strip()
    fa = folder_artist.lower().strip()
    if t == fa:
        return True
    if t.startswith(fa) and len(t) > len(fa) and not t[len(fa)].isalpha():
        return True
    return False


def _normalise_compare_text(text):
    """Normalise text for lightweight fuzzy contains checks."""
    t = (text or "").lower().strip()
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _looks_like_albumish_prefix(text, folder_album=""):
    """Return True when left side of 'X - Title' looks like album/OST label.

    Examples: "Starsector OST", "Subnautica Soundtrack", "Original Score".
    """
    left = _normalise_compare_text(text)
    if not left:
        return False

    albumish_tokens = (
        " ost",
        " soundtrack",
        " original soundtrack",
        " score",
        " original score",
        " full ost",
    )
    if any(token in f" {left} " for token in albumish_tokens):
        return True

    album_norm = _normalise_compare_text(folder_album)
    if album_norm:
        if left in album_norm or album_norm in left:
            return True

    return False


def parse_filename(filename, folder_artist=None, folder_album=None):
    name = os.path.splitext(filename)[0]
    cleaned = clean_string(name)

    # 1. Track + Artist - Title: "03 Hans Zimmer - Dragon Racing"
    m = re.match(r"(\d+)[\.\ - ]+(.+?) - (.+)", cleaned)
    if m:
        track = m.group(1)
        artist = m.group(2)
        title = m.group(3)
        # Detect reversal: title side matches folder artist
        if folder_artist and _matches_artist(title, folder_artist):
            artist, title = title, artist
        return {
            "track": track,
            "artist": artist,
            "title": title,
            "album": folder_album or "",
            "confidence": 95,
        }

    # 2. Artist - Title (with reversal detection)
    m = re.match(r"(.+?) - (.+)", cleaned)
    if m:
        left = m.group(1).strip()
        right = m.group(2).strip()

        # If left side is album-ish (e.g. "Starsector OST - Battle Ambience"),
        # don't treat it as artist; trust folder artist and keep right as title.
        if folder_artist and _looks_like_albumish_prefix(left, folder_album):
            return {
                "track": "",
                "artist": folder_artist,
                "title": right,
                "album": folder_album or "",
                "confidence": 85,
            }

        if folder_artist and _matches_artist(right, folder_artist):
            # Reversed: "Title - Artist" or "Title - Artist and collaborators"
            use_artist = (
                right if right.lower() != folder_artist.lower() else folder_artist
            )
            return {
                "track": "",
                "artist": use_artist,
                "title": left,
                "album": folder_album or "",
                "confidence": 90,
            }
        return {
            "track": "",
            "artist": left,
            "title": right,
            "album": folder_album or "",
            "confidence": 90,
        }

    # 3. Track + Title (folder provides artist, or at least album)
    m = re.match(r"(\d+)[\.\ - ]+(.+)", cleaned)
    if m and (folder_artist or folder_album):
        return {
            "track": m.group(1),
            "artist": folder_artist or "",
            "title": m.group(2),
            "album": folder_album or "",
            "confidence": 85 if folder_artist else 60,
        }

    # 4. Filename starts with known artist name (no separator)
    #    e.g. "ray charles see see rider" → title = "see see rider"
    if folder_artist and len(cleaned) > len(folder_artist):
        fa_lower = folder_artist.lower()
        cl_lower = cleaned.lower()
        if cl_lower.startswith(fa_lower) and not cl_lower[len(fa_lower)].isalpha():
            remainder = cleaned[len(folder_artist):].strip()
            remainder = re.sub(r"^[\-\s]+", "", remainder).strip()
            if remainder:
                return {
                    "track": "",
                    "artist": folder_artist,
                    "title": remainder,
                    "album": folder_album or "",
                    "confidence": 85,
                }

    # 5. "Title by Artist" pattern
    if folder_artist:
        m = re.match(
            r"(.+?)\s+by\s+" + re.escape(folder_artist) + r"\s*$",
            cleaned,
            re.IGNORECASE,
        )
        if m:
            return {
                "track": "",
                "artist": folder_artist,
                "title": m.group(1),
                "album": folder_album or "",
                "confidence": 85,
            }

    # 6. Title only (folder provides artist)
    if folder_artist:
        conf = 85 if folder_album else 70
        return {
            "track": "",
            "artist": folder_artist,
            "title": cleaned,
            "album": folder_album or "",
            "confidence": conf,
        }

    # 7. Title only (folder provides album but no artist)
    if folder_album:
        return {
            "track": "",
            "artist": "",
            "title": cleaned,
            "album": folder_album,
            "confidence": 60,
        }

    return None

def analyze_directory(root_path, out_dir="./.batch_fix", report_prefix=None):
    unmatched_files = []
    unmatched_dirs = []
    report_rows = []

    if report_prefix is None:
        root_label = os.path.basename(root_path.rstrip("/\\")) or "root"
        report_prefix = _dated_prefix(root_label)

    for root, dirs, files in os.walk(root_path):
        audio_files = [f for f in files if f.lower().endswith(AUDIO_EXTENSIONS)]
        if not audio_files:
            continue

        folder_info = parse_folder_name(os.path.basename(root))
        folder_artist = folder_info["artist"]
        folder_album = folder_info["album"]

        # Nested folder support: Genre/Album/tracks or Artist/Album/tracks
        # If immediate folder has no album, check grandparent for context
        parent_dir = os.path.dirname(root)
        if parent_dir != root_path and parent_dir != root:
            grandparent_name = os.path.basename(parent_dir)
            if grandparent_name and grandparent_name != os.path.basename(root_path):
                gp_clean = clean_string(grandparent_name).lower()
                is_genre = gp_clean in GENRE_FOLDERS

                if is_genre and not folder_album:
                    # Grandparent is a genre category, not an artist.
                    # Treat immediate folder as album, artist from filename.
                    folder_album = clean_folder_album(
                        os.path.basename(root)
                    )
                    folder_artist = ""
                elif not is_genre:
                    gp_info = parse_folder_name(grandparent_name)
                    if gp_info["artist"] and not folder_album:
                        # Grandparent is artist, immediate folder is album
                        folder_artist = gp_info["artist"]
                        folder_album = clean_folder_album(
                            os.path.basename(root)
                        )

        dir_unmatched = 0

        for file in audio_files:
            full_path = os.path.join(root, file)
            title, artist = read_tags(full_path)

            if strong_tags(title, artist):
                continue

            result = parse_filename(file, folder_artist, folder_album)

            if not result:
                unmatched_files.append(full_path)
                dir_unmatched += 1
                continue

            # Post-processing: strip artist name from title if embedded
            result["title"] = _strip_artist_from_title(
                result["title"], result["artist"]
            )

            report_rows.append([
                full_path,
                result["artist"],
                result["title"],
                result["track"],
                result["album"],
                result["confidence"],
            ])

            if result["confidence"] < CONFIDENCE_THRESHOLD:
                unmatched_files.append(full_path)
                dir_unmatched += 1

        if audio_files and dir_unmatched / len(audio_files) > 0.5:
            unmatched_dirs.append(root)

    # Write reports
    os.makedirs(out_dir, exist_ok=True)
    dry_run_csv = os.path.join(out_dir, f"{report_prefix}_dry_run_report.csv")
    unmatched_files_txt = os.path.join(out_dir, f"{report_prefix}_unmatched_files.txt")
    unmatched_dirs_txt = os.path.join(out_dir, f"{report_prefix}_unmatched_directories.txt")

    with open(dry_run_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Path", "Artist", "Title", "Track", "Album", "Confidence"])
        writer.writerows(report_rows)

    with open(unmatched_files_txt, "w", encoding="utf-8") as f:
        for u in unmatched_files:
            f.write(u + "\n")

    with open(unmatched_dirs_txt, "w", encoding="utf-8") as f:
        for d in unmatched_dirs:
            f.write(d + "\n")

    print(f"  Proposed matches     : {len(report_rows)}")
    print(f"  Unmatched files      : {len(unmatched_files)}")
    print(f"  Unmatched directories: {len(unmatched_dirs)}")
    print(f"  Dry-run report       : {dry_run_csv}")
    print(f"  Unmatched files list : {unmatched_files_txt}")
    print(f"  Unmatched dirs list  : {unmatched_dirs_txt}")

    return report_rows, unmatched_files, unmatched_dirs, {
        "dry_run_csv": dry_run_csv,
        "unmatched_files_txt": unmatched_files_txt,
        "unmatched_dirs_txt": unmatched_dirs_txt,
    }


# ---------------------------------------------------------------------------
# Phase 2 — safe write (tag copies)
# ---------------------------------------------------------------------------

def _backup_tags_raw(path):
    """Read all existing tags from a file. Returns a serialisable dict."""
    try:
        if path.lower().endswith(".mp3"):
            try:
                tags = ID3(path)
                return {k: str(v) for k, v in tags.items()}
            except ID3NoHeaderError:
                return {}
        else:
            audio = MP4(path)
            if not audio.tags:
                return {}
            out = {}
            for k, v in audio.tags.items():
                try:
                    out[k] = [str(x) for x in v] if isinstance(v, list) else str(v)
                except Exception:
                    out[k] = repr(v)
            return out
    except Exception:
        return {}


def _get_tag_field(backup, *keys):
    """Extract the first non-empty value from a tag backup dict, trying each key."""
    for k in keys:
        v = backup.get(k, "")
        if isinstance(v, list):
            v = v[0] if v else ""
        if v:
            return str(v)
    return ""


def write_tags(path, artist="", title="", track="", album=""):
    """Write ID3/MP4 tags to path. Only overwrites non-empty fields.

    Returns True on success or an error string on failure.
    """
    try:
        if path.lower().endswith(".mp3"):
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()  # creates a new tag
            if title:
                tags["TIT2"] = TIT2(encoding=3, text=title)
            if artist:
                tags["TPE1"] = TPE1(encoding=3, text=artist)
            if album:
                tags["TALB"] = TALB(encoding=3, text=album)
            if track:
                tags["TRCK"] = TRCK(encoding=3, text=str(track))
            tags.save(path)
        else:  # .m4a / MP4
            audio = MP4(path)
            if audio.tags is None:
                audio.add_tags()
            if title:
                audio.tags["\xa9nam"] = [title]
            if artist:
                audio.tags["\xa9ART"] = [artist]
            if album:
                audio.tags["\xa9alb"] = [album]
            if track:
                try:
                    trk_num = int(str(track).split("/")[0])
                    audio.tags["trkn"] = [(trk_num, 0)]
                except (ValueError, TypeError):
                    pass
            audio.save()
        return True
    except Exception as exc:
        return str(exc)


def write_tags_to_copies(
    csv_in,
    target_dir,
    min_confidence=None,
    prefer_mb=True,
    mb_only=False,
    log_dir=None,
    report_prefix=None,
):
    """Phase 2 – copy qualifying files to target_dir and write tags.

    Args:
        csv_in:         CSV produced by analyze_directory or enrich_with_musicbrainz.
        target_dir:     Root directory for tagged copies. Source paths are mirrored
                        under target_dir (leading '/' stripped, so
                        /mnt/d/Musik/Foo/bar.mp3 → target_dir/mnt/d/Musik/Foo/bar.mp3).
        min_confidence: Only process rows with Confidence >= this value.
                        Defaults to CONFIDENCE_THRESHOLD.
        prefer_mb:      If the CSV has MB_* columns with a score, prefer those
                        values; fall back to rule-based fields if MB fields are empty.
        mb_only:        If True, skip any row where MusicBrainz did not return a
                        match (MB_Score is empty). Implies the CSV must have MB_*
                        columns (run --enrich / --enrich-all first).
        log_dir:        Where to write <prefix>_write_log.csv and
                <prefix>_tag_backup.json.
                        Defaults to the directory that contains csv_in.
    """
    if min_confidence is None:
        min_confidence = CONFIDENCE_THRESHOLD
    if log_dir is None:
        log_dir = os.path.dirname(os.path.abspath(csv_in))
    if report_prefix is None:
        report_prefix = _safe_label(os.path.splitext(os.path.basename(csv_in))[0])

    with open(csv_in, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("Phase 2: CSV is empty, nothing to do.")
        return

    has_mb = "MB_Score" in rows[0]

    if mb_only:
        # MB match IS the quality gate — bypass confidence threshold entirely
        if not has_mb:
            print("[Phase 2] --mb-only requested but CSV has no MB_Score column.")
            print("  Run --enrich or --enrich-all first to add MB columns.")
            return
        qualifying = [r for r in rows if r.get("MB_Score")]
        skipped_conf = 0
        skipped_no_mb = len(rows) - len(qualifying)
    else:
        qualifying = [r for r in rows if int(r["Confidence"]) >= min_confidence]
        skipped_conf = len(rows) - len(qualifying)
        skipped_no_mb = 0

    print(f"\n{'='*60}")
    print(f"Phase 2 — safe write to copies")
    print(f"  CSV            : {csv_in}")
    print(f"  Target dir     : {target_dir}")
    print(f"  Min confidence : {min_confidence}")
    print(f"  Qualifying     : {len(qualifying)}  (skipped {skipped_conf} below threshold, {skipped_no_mb} no MB match)")
    print(f"  MB columns     : {'yes, prefer_mb=True' if has_mb and prefer_mb else 'no / prefer_mb=False'}")
    print(f"  MB-only mode   : {'yes — only files with a MB match will be copied' if mb_only else 'no'}")
    print(f"{'='*60}")

    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    LOG_FIELDS = [
        "Source", "Dest", "Confidence",
        "Artist_written", "Title_written", "Track_written", "Album_written",
        "Artist_before",  "Title_before",  "Album_before",
        "Status",
    ]
    log_rows = []
    tag_backups = {}
    ok = errors = 0

    for i, row in enumerate(qualifying, 1):
        src = row["Path"]
        if not os.path.isfile(src):
            print(f"  [{i}/{len(qualifying)}] MISSING: {src}")
            log_rows.append({
                "Source": src, "Dest": "", "Confidence": row["Confidence"],
                "Artist_written": "", "Title_written": "",
                "Track_written": "",  "Album_written": "",
                "Artist_before": "",  "Title_before": "",  "Album_before": "",
                "Status": "ERROR: source not found",
            })
            errors += 1
            continue

        # Mirror path under target_dir (strip leading /)
        rel = src.lstrip("/")
        dest = os.path.join(target_dir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        # Copy source → dest (always overwrite; we own the target dir)
        shutil.copy2(src, dest)

        # Backup destination tags (from the fresh copy)
        backup = _backup_tags_raw(dest)
        tag_backups[dest] = backup

        # Resolve which field values to write
        if has_mb and prefer_mb and row.get("MB_Score"):
            artist = row.get("MB_Artist") or row["Artist"]
            title  = row.get("MB_Title")  or row["Title"]
            album  = row.get("MB_Album")  or row["Album"]
        else:
            artist = row["Artist"]
            title  = row["Title"]
            album  = row["Album"]
        track = row["Track"]

        result = write_tags(dest, artist=artist, title=title,
                            track=track, album=album)
        if result is True:
            status = "ok"
            ok += 1
        else:
            status = f"ERROR: {result}"
            errors += 1

        if i % 50 == 0 or i == len(qualifying):
            print(f"  [{i}/{len(qualifying)}] ok={ok} errors={errors}")

        log_rows.append({
            "Source":         src,
            "Dest":           dest,
            "Confidence":     row["Confidence"],
            "Artist_written": artist,
            "Title_written":  title,
            "Track_written":  track,
            "Album_written":  album,
            "Artist_before":  _get_tag_field(backup, "TPE1", "\xa9ART"),
            "Title_before":   _get_tag_field(backup, "TIT2", "\xa9nam"),
            "Album_before":   _get_tag_field(backup, "TALB", "\xa9alb"),
            "Status":         status,
        })

    # Write backup JSON
    backup_path = os.path.join(log_dir, f"{report_prefix}_tag_backup.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(tag_backups, f, indent=2, ensure_ascii=False, default=str)

    # Write log CSV
    log_csv = os.path.join(log_dir, f"{report_prefix}_write_log.csv")
    with open(log_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(log_rows)

    print(f"\n  Written OK : {ok}")
    print(f"  Errors     : {errors}")
    print(f"  Write log  : {log_csv}")
    print(f"  Tag backup : {backup_path}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# MusicBrainz enrichment phase
# ---------------------------------------------------------------------------

def _similarity(a, b):
    """Return fuzzy similarity ratio (0-1) between two strings."""
    a = re.sub(r"\s+", " ", a.lower().strip())
    b = re.sub(r"\s+", " ", b.lower().strip())
    return difflib.SequenceMatcher(None, a, b).ratio()


def _normalise_mb_text(text):
    """Normalise MB response text: fix non-standard hyphens, strip extra spaces."""
    if not text:
        return ""
    # MB sometimes uses Unicode hyphens (‐ U+2010, – U+2013, — U+2014)
    text = text.replace("\u2010", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_title_for_mb(title):
    """Strip YouTube/streaming suffix junk from title before sending to MB.

    clean_string handles parenthesised junk; this handles bare suffixes.
    """
    patterns = [
        # "Official Music Video", "Official Audio", "Official Lyric Video", etc.
        r"\s+Official\s+(?:Music\s+)?(?:Video|Audio|Lyric\s+Video|Visualizer).*$",
        # "Video Remastered", "Video Winner", etc.
        r"\s+Video\s+\w.*$",
        # "LYRICS Video" (LYRICS already stripped by clean_string; catch Video)
        r"\s+Video\b.*$",
        # "Remastered In 1080p", "Remastered 2009" type suffixes
        r"\s+Remaster(?:ed)?\b.*$",
        # "4K", "HD", "HQ" standalone at end
        r"\s+(?:4K|HD|HQ)\b.*$",
        # Resolution markers: "1080p", "720p"
        r"\s+\d{3,4}p\b.*$",
        # "Dir. SomeProduction"
        r"\s+[Dd]ir\.\s+.*$",
        # "ft. @Handle" or featuring tags
        r"\s+ft\.\s+@\S+.*$",
        # "on The Ed Sullivan Show", "from The Concert in Central Park"
        r"\s+(?:on|from)\s+[Tt]he\s+.+$",
        # Trailing year + format: "1968 VINYL LP", "2009 Album"
        r"\s+\d{4}\s+(?:VINYL|LP|Album|EP|Stereo|Mono)\b.*$",
        # Bare year at end: " - 1968" or "  1968"
        r"\s+[-–]\s+\d{4}\s*$",
        # Episode references that crept in
        r"\s+Episode\s+\d.*$",
    ]
    t = title
    for pat in patterns:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    return t.strip()


def _artist_query_candidates(artist):
    """Return ordered artist query candidates for MB lookups.

    Order is conservative:
      1) full artist string
      2) first side of "A & B"
      3) second side of "A & B"
    """
    base = (artist or "").strip()
    if not base:
        return []

    candidates = [base]
    # Duo fallback: "Artist A & Artist B"
    parts = [p.strip() for p in re.split(r"\s*&\s*", base) if p.strip()]
    if len(parts) >= 2:
        candidates.extend([parts[0], parts[1]])

    # Preserve order while removing duplicates.
    out = []
    seen = set()
    for cand in candidates:
        key = _normalise_artist_key(cand)
        if key and key not in seen:
            out.append(cand)
            seen.add(key)
    return out


def lookup_musicbrainz(artist, title, album=""):
    """Query MusicBrainz for a single recording.

    Returns a dict with keys {artist, title, album, mb_score} on success,
    or None if no sufficiently confident match was found.

    Strategy (most to least specific):
      1. cleaned_title + artist [+ album if non-generic]
      2. cleaned_title + artist  (drop album)
      3. cleaned_title only      (relaxed — drops artist guard)
    The fuzzy title-similarity check guards against false positives.
    """
    if not _MB_AVAILABLE:
        return None

    clean_title = _clean_title_for_mb(title)
    if not clean_title:
        return None

    # Generic/noisy album labels that add no value to the query
    _generic_albums = {"various artists", "various", "best of", "greatest hits",
                       "compilation", "playlist", "mix", ""}

    use_album = (
        album
        and album.lower().strip() not in _generic_albums
        and len(album) > 3
    )
    artist_candidates = _artist_query_candidates(artist)

    def _run(recording, artist_kw=None, release_kw=None):
        """Call MB search_recordings with keyword args and return recording list."""
        kwargs = {"limit": 5}
        if recording:
            kwargs["recording"] = recording
        if artist_kw:
            kwargs["artist"] = artist_kw
        if release_kw:
            kwargs["release"] = release_kw
        try:
            time.sleep(MB_REQUEST_DELAY)
            result = musicbrainzngs.search_recordings(**kwargs)
            return result.get("recording-list", [])
        except Exception as exc:
            print(f"    [MB] Error: {exc}")
            return []

    def _pick(recordings):
        """Return the first recording that passes score and similarity checks."""
        for rec in recordings:
            mb_score = int(rec.get("ext:score", 0))
            if mb_score < MB_MIN_SCORE:
                break
            mb_title  = _normalise_mb_text(rec.get("title", ""))
            mb_artist = _normalise_mb_text(rec.get("artist-credit-phrase", ""))
            releases  = rec.get("release-list", [])
            mb_album  = _normalise_mb_text(releases[0].get("title", "") if releases else "")
            sim = _similarity(clean_title, mb_title)
            if sim >= MB_TITLE_MIN_SIM:
                return {"artist": mb_artist, "title": mb_title,
                        "album": mb_album, "mb_score": mb_score}
        return None

    # Attempt 1: title + artist + album (when album is meaningful)
    if artist_candidates and use_album:
        for artist_candidate in artist_candidates:
            hit = _pick(_run(clean_title, artist_kw=artist_candidate, release_kw=album))
            if hit:
                return hit

    # Attempt 2: title + artist
    if artist_candidates:
        for artist_candidate in artist_candidates:
            hit = _pick(_run(clean_title, artist_kw=artist_candidate))
            if hit:
                return hit

    # Attempt 3: title only (accept higher false-positive risk; require sim >= 0.75)
    recs = _run(clean_title)
    for rec in recs:
        mb_score = int(rec.get("ext:score", 0))
        if mb_score < MB_MIN_SCORE:
            break
        mb_title  = _normalise_mb_text(rec.get("title", ""))
        mb_artist = _normalise_mb_text(rec.get("artist-credit-phrase", ""))
        releases  = rec.get("release-list", [])
        mb_album  = _normalise_mb_text(releases[0].get("title", "") if releases else "")
        sim = _similarity(clean_title, mb_title)
        if sim >= 0.75:   # stricter without artist anchor
            return {"artist": mb_artist, "title": mb_title,
                    "album": mb_album, "mb_score": mb_score}

    return None


def _normalise_artist_key(text):
    """Normalise artist strings for robust equality checks."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def _artists_equivalent(left, right):
    """Case/spacing/punctuation-tolerant artist equality."""
    return bool(left and right) and _normalise_artist_key(left) == _normalise_artist_key(right)


def _build_dominant_artist_map(rows, threshold=0.70, min_files=5):
    """Return per-directory dominant artist context.

    Output format:
        {
            "/abs/dir": {
                "artist": "Sammy Davis Jr.",
                "ratio": 0.82,
                "total": 34,
            },
            ...
        }
    """
    by_dir = defaultdict(list)
    for row in rows:
        path = (row.get("Path") or "").strip()
        artist = (row.get("Artist") or "").strip()
        if not path or not artist:
            continue
        by_dir[os.path.dirname(path)].append(artist)

    dominant = {}
    for directory, artists in by_dir.items():
        total = len(artists)
        if total < min_files:
            continue
        counts = Counter(artists)
        top_artist, top_count = counts.most_common(1)[0]
        ratio = top_count / total
        if ratio >= threshold:
            dominant[directory] = {
                "artist": top_artist,
                "ratio": ratio,
                "total": total,
            }
    return dominant


def _title_retry_variants(title):
    """Generate conservative title variants for retry lookups."""
    variants = []
    seen = set()

    def _add(value):
        v = (value or "").strip()
        if v and v not in seen:
            variants.append(v)
            seen.add(v)

    _add(title)
    # Fallback for malformed parse where title still contains an artist prefix.
    if title and " - " in title:
        _add(title.split(" - ", 1)[1])
    return variants


def _strip_track_prefix_from_stem(stem):
    """Return (new_stem, pattern_index) after removing leading track prefix."""
    current = (stem or "").strip()
    first_pattern_idx = 0
    changed = True
    passes = 0

    while changed and passes < 5:
        passes += 1
        changed = False
        for idx, pattern in enumerate(TRACK_PREFIX_PATTERNS, 1):
            updated = re.sub(pattern, "", current, count=1, flags=re.IGNORECASE)
            updated = updated.strip()
            if updated and updated != current:
                if first_pattern_idx == 0:
                    first_pattern_idx = idx
                current = updated
                changed = True
                break

    if first_pattern_idx:
        return current, first_pattern_idx
    return stem, 0


def strip_track_prefixes_recursively(
    roots,
    dry_run=True,
    safe_copy_dir=None,
    include_exts=AUDIO_EXTENSIONS,
):
    """Recursively strip track-number filename prefixes.

    This operation never touches audio tags; it only renames files.
    If safe_copy_dir is provided, roots are copied first and renames are applied
    in the copied tree.
    """
    if not roots:
        print("No roots provided for --strip-track-prefix mode.")
        return

    include_exts = tuple(ext.lower() for ext in include_exts)

    plan = []
    for root in roots:
        if not os.path.isdir(root):
            print(f"[SKIP] Not a directory: {root}")
            continue

        active_root = root
        if safe_copy_dir:
            label = os.path.basename(root.rstrip("/\\")) or "root"
            active_root = os.path.join(safe_copy_dir, label)
            os.makedirs(safe_copy_dir, exist_ok=True)
            print(f"\n[copy] {root} -> {active_root}")
            shutil.copytree(root, active_root, dirs_exist_ok=True)

        for dirpath, _, files in os.walk(active_root):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in include_exts:
                    continue
                stem, _ = os.path.splitext(filename)
                new_stem, pattern_idx = _strip_track_prefix_from_stem(stem)
                if pattern_idx == 0:
                    continue
                new_name = f"{new_stem}{ext}"
                old_path = os.path.join(dirpath, filename)
                new_path = os.path.join(dirpath, new_name)
                plan.append((old_path, new_path, pattern_idx))

    if not plan:
        print("\nNo matching filename track prefixes found.")
        return

    print(f"\nFilename cleanup plan: {len(plan)} rename(s)")
    for idx, (old_path, new_path, pattern_idx) in enumerate(plan[:20], 1):
        print(f"  [{idx}] p{pattern_idx}: {old_path} -> {new_path}")
    if len(plan) > 20:
        print(f"  ... and {len(plan) - 20} more")

    if dry_run:
        print("\nDry-run only: no files were renamed.")
        return

    renamed = 0
    collisions = 0
    errors = 0
    for old_path, new_path, _ in plan:
        if old_path == new_path:
            continue
        if os.path.exists(new_path):
            collisions += 1
            print(f"[skip-collision] {new_path}")
            continue
        try:
            os.rename(old_path, new_path)
            renamed += 1
        except Exception as exc:
            errors += 1
            print(f"[rename-error] {old_path} -> {new_path} ({exc})")

    print(f"\nRename complete: renamed={renamed}, collisions={collisions}, errors={errors}")


def enrich_with_musicbrainz(
    csv_in,
    csv_out,
    confidence_ceiling=None,
    dominant_retry=True,
    dominant_threshold=0.70,
    dominant_min_files=5,
    dominant_fixme_suffix="",
):
    """Read a dry-run CSV, query MusicBrainz for qualifying entries,
    and write an enriched CSV with added MB_* columns.

    Args:
        csv_in:  Path to the existing dry-run CSV.
        csv_out: Path for the enriched output CSV.
        confidence_ceiling: Only enrich entries with Confidence *strictly below*
                    this value. None = enrich ALL entries.
        dominant_retry:     If True, identify dominant-artist directories and
                    retry likely outliers with the dominant artist.
        dominant_threshold: Dominance ratio needed to activate retry (0-1).
        dominant_min_files: Minimum number of files in a directory to evaluate
                    dominance.
        dominant_fixme_suffix:
                    Optional suffix appended to Artist for unresolved
                    outliers (e.g. " (FIXME)"). Empty = no suffix.
    """
    if not _MB_AVAILABLE:
        print("musicbrainzngs not installed. Run: pip install musicbrainzngs")
        return

    musicbrainzngs.set_useragent(MB_APP_NAME, MB_APP_VERSION, MB_CONTACT)

    with open(csv_in, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    fieldnames = [
        "Path", "Artist", "Title", "Track", "Album", "Confidence",
        "MB_Artist", "MB_Title", "MB_Album", "MB_Score",
        "MB_MatchSource", "Dir_Dominant_Artist", "Review_Flag",
    ]

    if confidence_ceiling is None:
        targets_idx = set(range(len(rows)))
    else:
        targets_idx = {i for i, r in enumerate(rows) if int(r["Confidence"]) < confidence_ceiling}

    print(f"\nMusicBrainz enrichment: {len(targets_idx)} entries to query"
          f" (ceiling={confidence_ceiling})")

    dominant_map = {}
    if dominant_retry:
        dominant_map = _build_dominant_artist_map(
            rows,
            threshold=dominant_threshold,
            min_files=dominant_min_files,
        )
        print(
            f"  Dominant retry      : enabled "
            f"(dirs={len(dominant_map)}, threshold={dominant_threshold:.2f}, min_files={dominant_min_files})"
        )
    else:
        print("  Dominant retry      : disabled")

    out_rows = []
    matched = 0
    queried = 0
    dominant_retries = 0
    dominant_retry_hits = 0

    for i, row in enumerate(rows):
        mb_artist = mb_title = mb_album = mb_score_val = ""
        mb_match_source = ""
        review_flag = ""
        out_artist_value = row["Artist"]
        dir_dominant_artist = ""

        if i in targets_idx:
            artist = row["Artist"].strip()
            title = row["Title"].strip()
            album = row["Album"].strip()
            queried += 1

            print(f"  [{queried}/{len(targets_idx)}] {os.path.basename(row['Path'])[:55]}")

            directory = os.path.dirname((row.get("Path") or "").strip())
            dominant_ctx = dominant_map.get(directory)
            dominant_artist = ""
            if dominant_ctx:
                dominant_artist = dominant_ctx["artist"]
                dir_dominant_artist = dominant_artist

            match = lookup_musicbrainz(artist, title, album)
            if match:
                mb_match_source = "base"

            likely_outlier = (
                bool(dominant_ctx)
                and artist
                and not _artists_equivalent(artist, dominant_ctx["artist"])
            )

            should_retry_dominant = (
                likely_outlier
                and (
                    not match
                    or not _artists_equivalent(match.get("artist", ""), dominant_artist)
                )
            )

            if should_retry_dominant:
                dominant_retries += 1
                best_retry = None
                for retry_title in _title_retry_variants(title):
                    candidate = lookup_musicbrainz(dominant_artist, retry_title, album)
                    if not candidate:
                        continue
                    if not _artists_equivalent(candidate.get("artist", ""), dominant_artist):
                        continue
                    if not best_retry or candidate["mb_score"] > best_retry["mb_score"]:
                        best_retry = candidate

                if best_retry:
                    use_retry = False
                    if not match:
                        use_retry = True
                    else:
                        # Conservative replacement: only replace if retry is
                        # clearly better OR current MB result disagrees with
                        # dominant artist and retry agrees.
                        if best_retry["mb_score"] >= match["mb_score"] + 2:
                            use_retry = True
                        elif not _artists_equivalent(match.get("artist", ""), dominant_artist):
                            use_retry = True
                    if use_retry:
                        match = best_retry
                        mb_match_source = "dominant_retry"
                        dominant_retry_hits += 1

            if likely_outlier and not match:
                review_flag = "dominant_outlier_no_match"
                if dominant_fixme_suffix:
                    out_artist_value = (row["Artist"] + dominant_fixme_suffix).strip()

            if match:
                mb_artist = match["artist"]
                mb_title  = match["title"]
                mb_album  = match["album"]
                mb_score_val = str(match["mb_score"])
                matched += 1
                if mb_match_source == "dominant_retry":
                    print(f"    + MB({mb_score_val}) {mb_artist!r} – {mb_title!r} / {mb_album!r} [dominant retry]")
                else:
                    print(f"    + MB({mb_score_val}) {mb_artist!r} – {mb_title!r} / {mb_album!r}")
            else:
                print(f"    – no match")

        out_rows.append({
            "Path":       row["Path"],
            "Artist":     out_artist_value,
            "Title":      row["Title"],
            "Track":      row["Track"],
            "Album":      row["Album"],
            "Confidence": row["Confidence"],
            "MB_Artist":  mb_artist,
            "MB_Title":   mb_title,
            "MB_Album":   mb_album,
            "MB_Score":   mb_score_val,
            "MB_MatchSource": mb_match_source,
            "Dir_Dominant_Artist": dir_dominant_artist,
            "Review_Flag": review_flag,
        })

    with open(csv_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\nEnrichment complete: {matched}/{queried} resolved → {csv_out}")
    if dominant_retry:
        print(f"  Dominant retries: {dominant_retries} (hits: {dominant_retry_hits})")


if __name__ == "__main__":
    # -----------------------------------------------------------------------
    # Confidence model reference:
    #   95  – Track + Artist + Title all parsed from filename            (best)
    #   90  – Artist - Title parsed from filename (incl. reversal)
    #   85  – One of: Track+Title from file + artist from folder;
    #                 Title from file + artist AND album from folder;
    #                 Artist-prefix strip / "by Artist" in filename
    #   70  – Title from file + artist from folder (no album context)   (skip)
    #   60  – Track or Title from file + album from folder, no artist   (skip)
    # Write threshold = 85: entries >= 85 are written; < 85 are candidates
    # for MusicBrainz enrichment (--enrich) or manual review.
    # -----------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Batch audio metadata cleanup pipeline"
    )
    parser.add_argument(
        "roots",
        nargs="*",
        default=["/mnt/d/Program_Targets/MusicBrainz"],
        metavar="ROOT",
        help="One or more root directories to scan (default: /mnt/d/Program_Targets/MusicBrainz)",
    )
    parser.add_argument(
        "--out-dir",
        default="./.batch_fix",
        metavar="DIR",
        help="Base output directory (default: %(default)s). "
             "When scanning >1 root, each gets its own subdirectory.",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Run MusicBrainz enrichment on low-confidence results "
             "(confidence < --conf-ceiling) after the dry run",
    )
    parser.add_argument(
        "--enrich-all",
        action="store_true",
        help="Run MusicBrainz enrichment on ALL entries (not just low-confidence)",
    )
    parser.add_argument(
        "--conf-ceiling",
        type=int,
        default=CONFIDENCE_THRESHOLD,
        metavar="N",
        help="Enrich entries with confidence strictly below N (default: %(default)s)",
    )
    parser.add_argument(
        "--dominant-threshold",
        type=float,
        default=0.70,
        metavar="RATIO",
        help="Directory dominance ratio (0-1) required to retry outliers with dominant artist during enrichment (default: %(default)s)",
    )
    parser.add_argument(
        "--dominant-min-files",
        type=int,
        default=5,
        metavar="N",
        help="Minimum files per directory before dominant-artist retry is considered (default: %(default)s)",
    )
    parser.add_argument(
        "--no-dominant-retry",
        action="store_true",
        help="Disable dominant-artist retry logic during MusicBrainz enrichment",
    )
    parser.add_argument(
        "--dominant-fixme-suffix",
        default="",
        metavar="TEXT",
        help="Optional suffix appended to Artist on unresolved dominant-outlier rows during enrichment (e.g. ' (FIXME)')",
    )
    parser.add_argument(
        "--dry-run-only",
        action="store_true",
        help="Skip enrichment even if --enrich is set (for testing)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Phase 2: copy qualifying files to --target and write tags",
    )
    parser.add_argument(
        "--target",
        default="/mnt/d/Program_Targets/TaggingTarget",
        metavar="DIR",
        help="Destination directory for tagged copies (default: %(default)s)",
    )
    parser.add_argument(
        "--from-csv",
        default=None,
        metavar="CSV",
        help="Read this CSV for Phase 2 instead of the auto-generated one "
               "(e.g. point at *_mb_enriched_report.csv)",
    )
    parser.add_argument(
        "--no-prefer-mb",
        action="store_true",
        help="Do not prefer MB_* column values over rule-based ones in Phase 2",
    )
    parser.add_argument(
        "--mb-only",
        action="store_true",
        help="Phase 2: only copy/tag files where MusicBrainz returned a match "
             "(requires --enrich or --enrich-all to have been run first)",
    )
    parser.add_argument(
        "--strip-track-prefix",
        action="store_true",
        help="Standalone mode: recursively strip leading track-number prefixes from filenames only (never edits tags)",
    )
    parser.add_argument(
        "--strip-dry-run",
        action="store_true",
        help="With --strip-track-prefix: preview planned renames without changing files",
    )
    parser.add_argument(
        "--strip-safe-copy-dir",
        default=None,
        metavar="DIR",
        help="With --strip-track-prefix: copy each root to DIR/<root-name> and run rename there (safe test mode)",
    )
    args = parser.parse_args()

    if args.strip_track_prefix:
        strip_track_prefixes_recursively(
            roots=args.roots,
            dry_run=args.strip_dry_run,
            safe_copy_dir=args.strip_safe_copy_dir,
        )
        raise SystemExit(0)

    roots = args.roots
    base_out = args.out_dir
    multi = len(roots) > 1

    combined_rows = []
    combined_unmatched_files = []
    combined_unmatched_dirs = []
    dry_run_csv_paths = []
    scanned_labels = []
    combined_csv = None
    enriched_csv_path = None

    for root_path in roots:
        if not os.path.isdir(root_path):
            print(f"[SKIP] Not a directory: {root_path}")
            continue

        label = os.path.basename(root_path.rstrip("/\\")) or root_path
        out_dir = os.path.join(base_out, label) if multi else base_out
        report_prefix = _dated_prefix(label)
        scanned_labels.append(label)

        print(f"\n{'='*60}")
        print(f"Scanning: {root_path}")
        print(f"Output  : {out_dir}")
        print(f"{'='*60}")

        rows, uf, ud, report_paths = analyze_directory(
            root_path,
            out_dir=out_dir,
            report_prefix=report_prefix,
        )
        combined_rows.extend(rows)
        combined_unmatched_files.extend(uf)
        combined_unmatched_dirs.extend(ud)
        dry_run_csv_paths.append(report_paths["dry_run_csv"])

    if multi:
        # Write combined report to base output dir
        os.makedirs(base_out, exist_ok=True)
        combined_csv = os.path.join(
            base_out, f"{time.strftime('%Y_%m_%d')}_combined_report.csv"
        )
        with open(combined_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Path", "Artist", "Title", "Track", "Album", "Confidence"])
            writer.writerows(combined_rows)
        print(f"\n{'='*60}")
        print(f"COMBINED TOTALS")
        print(f"  Roots scanned        : {len(roots)}")
        print(f"  Total proposed       : {len(combined_rows)}")
        print(f"  Total unmatched files: {len(combined_unmatched_files)}")
        print(f"  Total unmatched dirs : {len(combined_unmatched_dirs)}")
        if combined_rows:
            from collections import Counter
            dist = Counter(r[5] for r in combined_rows)
            print("  Confidence breakdown :")
            for conf in sorted(dist, reverse=True):
                pct = dist[conf] / len(combined_rows) * 100
                print(f"    {conf:>3}: {dist[conf]:>5} ({pct:.1f}%)")
        print(f"  Combined CSV         : {combined_csv}")
        print(f"{'='*60}")

    run_enrich = (args.enrich or args.enrich_all) and not args.dry_run_only
    if run_enrich:
        csv_in = combined_csv if multi else (dry_run_csv_paths[0] if dry_run_csv_paths else None)
        if multi:
            enrich_prefix = f"{time.strftime('%Y_%m_%d')}_combined"
        else:
            enrich_label = scanned_labels[0] if scanned_labels else "root"
            enrich_prefix = _dated_prefix(enrich_label)
        enriched_csv_path = os.path.join(base_out, f"{enrich_prefix}_mb_enriched_report.csv")
        if not csv_in:
            print("\nNo dry-run report available for enrichment.")
            run_enrich = False
        if not _MB_AVAILABLE:
            print("\nmusicbrainzngs not installed. Run: pip install musicbrainzngs")
        elif run_enrich:
            ceiling = None if args.enrich_all else args.conf_ceiling
            enrich_with_musicbrainz(
                csv_in=csv_in,
                csv_out=enriched_csv_path,
                confidence_ceiling=ceiling,
                dominant_retry=not args.no_dominant_retry,
                dominant_threshold=args.dominant_threshold,
                dominant_min_files=args.dominant_min_files,
                dominant_fixme_suffix=args.dominant_fixme_suffix,
            )

    if args.write:
        # Determine which CSV to read for Phase 2:
        # 1. Explicit --from-csv  2. mb_enriched if it exists  3. combined/dry-run
        if args.from_csv:
            phase2_csv = args.from_csv
        else:
            default_csv = combined_csv if multi else (dry_run_csv_paths[0] if dry_run_csv_paths else "")
            phase2_csv = (
                enriched_csv_path
                if enriched_csv_path and os.path.isfile(enriched_csv_path)
                else default_csv
            )

        if not os.path.isfile(phase2_csv):
            print(f"\n[Phase 2] CSV not found: {phase2_csv}")
            print("  Run a dry-run scan first (without --write) to generate it.")
        else:
            phase2_prefix = _safe_label(os.path.splitext(os.path.basename(phase2_csv))[0])
            write_tags_to_copies(
                csv_in=phase2_csv,
                target_dir=args.target,
                min_confidence=CONFIDENCE_THRESHOLD,
                prefer_mb=not args.no_prefer_mb,
                mb_only=args.mb_only,
                log_dir=base_out,
                report_prefix=phase2_prefix,
            )