Perfect idea. Here is a **clean technical project summary** you can paste into a new session so I can immediately continue with Phase 2 and debugging without re-explaining everything.

---

# PROJECT SUMMARY – Batch Audio Metadata Cleanup Pipeline

## 🎯 Goal

Build a **defensive, rule-based batch tagging pipeline** for `.mp3` and `.m4a` files to:

1. Clean filenames (remove junk like “Official Video”, “FULL ALBUM”, etc.)
2. Normalize characters (allow only `a-z A-Z 0-9 äöüÄÖÜ ß & ' - .`)
3. Extract base metadata:

   * artist
   * title
   * track number
   * album (from folder if possible)
4. Skip files with already strong tags
5. Overwrite weak tags
6. Produce clean base metadata so **MusicBrainz Picard** (from MusicBrainz) can auto-complete albums afterward
7. Never write garbage data
8. Scale to very large messy collections

---

# 🧠 Core Design Decisions

## Tag Priority Rules

* Track-level information wins over folder-level inference
* Filename wins over folder if conflict
* Overwrite weak tags
* Skip strong tags entirely

---

## Strong vs Weak Tags

### Strong tag (skip file completely):

* Title exists
* Artist exists

### Weak tag (overwrite allowed):

* Only title present
* Only artist present
* Title equals raw filename with junk
* Missing album

---

# 🏗 Architecture

## Confidence Model (0–100)

| Situation                             | Score |
| ------------------------------------- | ----- |
| Track + Artist + Title parsed cleanly | 95    |
| Artist - Title clean                  | 90    |
| Track + Title (artist from folder)    | 85    |
| Title only + folder artist            | 70    |
| Unclear / ambiguous                   | <50   |

### Safe write threshold:

```python
CONFIDENCE_THRESHOLD = 85
```

Only write when confidence ≥ 85.

---

# 🧹 Cleaning Rules

Remove:

* `(Official Video)`
* `(Official Audio)`
* `(Official Trailer)`
* `(Full Album)`
* `FULL ALBUM`
* `(Soundtrack)`
* trailing `(1)`
* duplicate whitespace
* YouTube-style clutter
* illegal symbols

Allowed characters:

```
a-z A-Z 0-9 äöüÄÖÜ ß & ' - .
```

Everything else removed.

---

# 📂 Known File Structure Patterns

Dataset contains:

### 1. Album folders

```
Rammstein - Mutter (Full Album)/
    Adios.m4a
```

### 2. Track numbers

```
01 Angst.m4a
```

### 3. Artist - Title

```
Pink Floyd - Burning Bridges (Official Audio).m4a
```

### 4. Track Artist - Title

```
03 Hans Zimmer & John Powell - Dragon Warrior Is Among Us.mp3
```

### 5. Soundtrack structured

```
ARC RAIDERS - SoundTrack - 00. Welcome Speranza.m4a
```

### 6. Reversed pattern

```
Extreme Ways - Moby (The Bourne Identity).mp3
```

### 7. Mixed / chaotic YouTube dumps

---

# 🚀 Phases

## ✅ Phase 1 – Dry Run (DONE)

* Parses files
* Does NOT modify anything
* Generates:

  * `dry_run_report.csv`
  * `unmatched_files.txt`
  * `unmatched_directories.txt`
* Directory marked unmatched if >50% files fail confidence threshold

---

## 🔜 Phase 2 – Safe Write (NEXT STEP)

Will:

* Write only if confidence ≥ 85
* Backup existing tags before write
* Optionally rename files to clean format:

  ```
  01 - Title.ext
  ```
* Normalize album and artist strings
* Keep absolute path logging of all changes

Needs implementation + debugging.

---

## 🔜 Phase 3 – Large-Scale Trash Management

If lots of files unmatched:

Planned improvements:

1. Pattern clustering:

   * Detect dominant filename regex automatically
   * Suggest new parsing rules

2. Smart directory triage:

   * If >50% unmatched → log whole directory
   * Else → log individual tracks

3. Possibly generate:

   * `needs_manual_review.csv`
   * grouped by inferred pattern

Goal: Make fixing thousands of bad files manageable.

---

# ⚙️ Tech Stack

* Python
* mutagen (MP3 + MP4)
* Regex-based rule engine
* CSV logging
* OS: cross-platform
* Handles `.mp3` + `.m4a`

---

# 📌 What To Continue With Next Session

1. Implement Phase 2 safe-write mode
2. Add:

   * tag backup system (JSON per file before write)
   * safe rename system
   * conflict detection (don’t overwrite existing files)
3. Improve rule engine:

   * handle reversed "Title - Artist"
   * detect soundtrack patterns more intelligently
4. Add debug verbosity mode
5. Test on small subset before full run

---

# 🛑 Safety Constraints

* Never write if confidence < threshold
* Never overwrite strong tags
* Always log every change with absolute path
* Prefer skipping over guessing

---

When continuing in next session, start with:

> Continue Phase 2 implementation. Add safe write mode, tag backup, rename normalization, and improved rule engine. Assume Phase 1 dry run script already exists as described.

That will allow immediate continuation without re-analysis.

---

If you want, I can also prepare a **more technical developer-facing continuation brief** with function signatures and refactor plan.
