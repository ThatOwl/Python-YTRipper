import os
import re
import csv
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

CONFIDENCE_THRESHOLD = 85
AUDIO_EXTENSIONS = (".mp3", ".m4a")

JUNK_PATTERNS = [
    r"\(Official.*?\)",
    r"\(Full Album.*?\)",
    r"FULL ALBUM",
    r"\(Soundtrack.*?\)",
    r"\(.*?Trailer.*?\)",
    r"\(\d+\)$",
    r"\(Remastered.*?\)",
    r"\(Mono.*?\)",
    r"\(Stereo.*?\)",
    r"\(Live.*?\)",
    r"\(HD.*?\)",
    r"\(Audio.*?\)",
    r"\(Video.*?\)",
    r"\(.*?Version.*?\)",
]

ALLOWED_CHARS = r"[^a-zA-Z0-9äöüÄÖÜß&'\-\. ]"

def clean_string(text):
    for pattern in JUNK_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(ALLOWED_CHARS, "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

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

def parse_filename(filename, folder_artist=None):
    name = os.path.splitext(filename)[0]
    cleaned = clean_string(name)

    # 1️⃣ Track Artist - Title
    m = re.match(r"(\d+)[\.\- ]+(.+?) - (.+)", cleaned)
    if m:
        return {
            "track": m.group(1),
            "artist": m.group(2),
            "title": m.group(3),
            "confidence": 95
        }

    # 2️⃣ Artist - Title
    m = re.match(r"(.+?) - (.+)", cleaned)
    if m:
        return {
            "track": "",
            "artist": m.group(1),
            "title": m.group(2),
            "confidence": 90
        }

    # 3️⃣ Track Title
    m = re.match(r"(\d+)[\.\- ]+(.+)", cleaned)
    if m and folder_artist:
        return {
            "track": m.group(1),
            "artist": folder_artist,
            "title": m.group(2),
            "confidence": 85
        }

    # 4️⃣ Title only
    if folder_artist:
        return {
            "track": "",
            "artist": folder_artist,
            "title": cleaned,
            "confidence": 70
        }

    return None

def analyze_directory(root_path):
    unmatched_files = []
    unmatched_dirs = []
    report_rows = []

    for root, dirs, files in os.walk(root_path):
        audio_files = [f for f in files if f.lower().endswith(AUDIO_EXTENSIONS)]
        if not audio_files:
            continue

        folder_artist = os.path.basename(root)
        folder_artist = clean_string(folder_artist)

        dir_unmatched = 0

        for file in audio_files:
            full_path = os.path.join(root, file)
            title, artist = read_tags(full_path)

            if strong_tags(title, artist):
                continue

            result = parse_filename(file, folder_artist)

            if not result:
                unmatched_files.append(full_path)
                dir_unmatched += 1
                continue

            report_rows.append([
                full_path,
                result["artist"],
                result["title"],
                result["track"],
                result["confidence"]
            ])

            if result["confidence"] < CONFIDENCE_THRESHOLD:
                unmatched_files.append(full_path)
                dir_unmatched += 1

        if audio_files and dir_unmatched / len(audio_files) > 0.5:
            unmatched_dirs.append(root)

    # Write reports
    with open("./.batch_fix/dry_run_report.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Path", "Artist", "Title", "Track", "Confidence"])
        writer.writerows(report_rows)

    with open("./.batch_fix/unmatched_files.txt", "w", encoding="utf-8") as f:
        for u in unmatched_files:
            f.write(u + "\n")

    with open("./.batch_fix/unmatched_directories.txt", "w", encoding="utf-8") as f:
        for d in unmatched_dirs:
            f.write(d + "\n")

    print("Dry run complete.")
    print(f"Proposed matches: {len(report_rows)}")
    print(f"Unmatched files: {len(unmatched_files)}")
    print(f"Unmatched directories: {len(unmatched_dirs)}")

if __name__ == "__main__":
    analyze_directory("/mnt/d/Program_Targets/MusicBrainz")