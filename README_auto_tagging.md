# python-autotagger.py — Usage Documentation

Batch audio metadata cleanup and tagging pipeline for `.mp3` and `.m4a` files.  
Parses artist / title / track / album from filenames and folder structure, optionally
enriches results via the MusicBrainz API, then copies files to a staging directory
with clean tags written — without ever touching the originals.

---

## Requirements

```bash
pip install mutagen musicbrainzngs
```

`musicbrainzngs` is optional. The script works fully without it; the `--enrich` /
`--enrich-all` / `--mb-only` flags will print a warning if it is missing.

---

## Quick-start examples

```bash
# Dry run only — inspect what the tool would do, writes nothing
python3 scripts/python-autotagger.py /mnt/d/Music/Rammstein

# Dry run on multiple roots — per-root reports + combined CSV
python3 scripts/python-autotagger.py /mnt/d/Musik /mnt/d/Program_Targets/RipperTarget

# Dry run + MusicBrainz enrichment for low-confidence entries (conf < 85)
python3 scripts/python-autotagger.py /mnt/d/Music/Deadpool --enrich

# Dry run + MusicBrainz enrichment for ALL entries
python3 scripts/python-autotagger.py /mnt/d/Music/60s_Hits --enrich-all

# Dry run → enrich all → copy+tag only MB-matched files to staging dir
python3 scripts/python-autotagger.py /mnt/d/Music/60s_Hits \
    --enrich-all --write --mb-only

# Skip scan, run Phase 2 write directly from an existing CSV
python3 scripts/python-autotagger.py --write \
    --from-csv .batch_fix/mb_enriched_report.csv

# Override output and target directories
python3 scripts/python-autotagger.py /mnt/d/Music \
    --out-dir /tmp/my_fix --target /mnt/staging/tagged

# Tune dominant-artist retry sensitivity
python3 scripts/python-autotagger.py /mnt/d/Music/Compilations \
  --enrich-all --dominant-threshold 0.80 --dominant-min-files 8

# Disable dominant retry completely (pure base MB behavior)
python3 scripts/python-autotagger.py /mnt/d/Music/Compilations \
  --enrich-all --no-dominant-retry

# Mark unresolved dominant-outlier rows for manual review
python3 scripts/python-autotagger.py /mnt/d/Music/Compilations \
  --enrich-all --dominant-fixme-suffix " (FIXME)"

# Filename-only cleanup: preview recursive track-prefix removal
python3 scripts/python-autotagger.py /mnt/d/Musik \
  --strip-track-prefix --strip-dry-run

# Filename-only cleanup: test safely on copied tree
python3 scripts/python-autotagger.py /mnt/d/Musik \
  --strip-track-prefix --strip-safe-copy-dir /tmp/strip_test

# Filename-only cleanup: apply in-place (renames files, never edits tags)
python3 scripts/python-autotagger.py /mnt/d/Musik \
  --strip-track-prefix
```

---

## Command-line reference

| Argument | Default | Description |
|---|---|---|
| `ROOT [ROOT …]` | `/mnt/d/Program_Targets/MusicBrainz` | One or more directories to scan recursively |
| `--out-dir DIR` | `./.batch_fix` | Where to write scan reports. With >1 root, each gets a subdirectory |
| `--enrich` | off | After scan: query MusicBrainz for entries with confidence < `--conf-ceiling` |
| `--enrich-all` | off | After scan: query MusicBrainz for **every** entry |
| `--conf-ceiling N` | `85` | Upper bound for `--enrich` targeting (entries strictly below this value) |
| `--dominant-threshold RATIO` | `0.70` | During enrichment, retry likely outliers in a directory when one artist dominates this ratio |
| `--dominant-min-files N` | `5` | Minimum files required in a directory before dominant-artist retry is considered |
| `--no-dominant-retry` | off | Disable dominant-artist retry logic during enrichment |
| `--dominant-fixme-suffix TEXT` | empty | Optional suffix appended to unresolved dominant-outlier `Artist` values (example: ` (FIXME)`) |
| `--dry-run-only` | off | Suppress Phase 2 even when `--enrich` is set — useful to re-run scan part only |
| `--write` | off | **Phase 2**: copy qualifying files to `--target` and write tags |
| `--target DIR` | `/mnt/d/Program_Targets/TaggingTarget` | Destination for tagged copies |
| `--from-csv CSV` | _(auto)_ | Feed a specific CSV into Phase 2 instead of the auto-generated one |
| `--mb-only` | off | Phase 2: copy only files that have a MusicBrainz match (requires prior `--enrich`/`--enrich-all`) |
| `--no-prefer-mb` | off | Phase 2: ignore MB columns even when present; use rule-based fields only |
| `--strip-track-prefix` | off | Standalone mode: recursively remove leading track-number prefixes from filenames only (never edits tags) |
| `--strip-dry-run` | off | With `--strip-track-prefix`: preview rename plan only, no filesystem changes |
| `--strip-safe-copy-dir DIR` | _(none)_ | With `--strip-track-prefix`: copy each root to `DIR/<root-name>` and perform renames there for safe testing |

---

## How it works

### Phase 1 — Dry run (scan)

Walks every subdirectory of each ROOT. For each audio file:

1. **Read existing tags** via mutagen. If both `title` and `artist` are already set
   ("strong tags"), the file is skipped entirely — no proposed change.
2. **Parse the folder name** to infer `artist` and/or `album`. Handles:
   - `Artist - Album (junk)` dash-separated
   - `Artist – Album` em-dash
   - `Artist ⌛ Album` special character separators
   - `Artist (Album, Year)` parenthesised
   - `Something Full Album` → album only
   - `Something Soundtrack/OST` → album only
   - Date prefixes `YYYY_`, `YYYY_MM_`, `YYYY_MM_DD_` stripped
   - Genre category folders (`Filmmusik`, `Spielemusik`, `Serienmusik`, …) are detected
     and not confused for artist names
3. **Parse the filename** using 7 ordered patterns with confidence scores (see below).
   - If a name looks like `Album/OST Label - Track Title` and folder artist is known,
     the left side is treated as album-ish context (not artist), and folder artist is used.
4. **Strip artist from title** if the artist name is embedded in the title string.
5. Record the result in the report CSV.

#### Confidence model

| Score | Pattern | Written? |
|---|---|---|
| **95** | Track + Artist + Title all from filename (`03 Hans Zimmer - Dragon Racing`) | ✅ |
| **90** | Artist – Title split from filename (incl. reversal detection) | ✅ |
| **85** | Track + Title from file, artist from folder; or title + folder artist + album | ✅ |
| **70** | Title from file + artist from folder, no album context | ❌ skipped |
| **60** | Track/title from file + album from folder, no artist | ❌ skipped |

Write threshold: **≥ 85**. Entries below threshold appear in `unmatched_files.txt`
and are candidates for MusicBrainz enrichment or manual review.

#### Nested folder support

| Structure | Behaviour |
|---|---|
| `Artist/tracks/` | Artist from folder |
| `Artist/Album/tracks/` | Artist from grandparent, album from immediate folder |
| `Genre/Album/tracks/` | Genre detected → album from immediate folder, artist from filename |

---

### Phase 1.5 — MusicBrainz enrichment (`--enrich` / `--enrich-all`)

Reads the Phase 1 CSV and queries the [MusicBrainz API](https://musicbrainz.org/)
for each qualifying entry. Three progressively-relaxed query attempts are made:

1. `title + artist + album` (when album is non-generic)
2. `title + artist`
3. `title only` (requires tighter fuzzy similarity ≥ 0.75)

When `artist` is a duo in the form `Artist A & Artist B`, artist-based queries use:

1. full duo string (`Artist A & Artist B`)
2. first artist (`Artist A`)
3. second artist (`Artist B`)

and stop on first acceptable match.

A match is accepted only when:
- The MB API score ≥ `MB_MIN_SCORE` (default: 75)
- The MB title similarity to the queried title ≥ `MB_TITLE_MIN_SIM` (default: 0.75)

Before querying, YouTube-style junk is stripped from the title (e.g. "Official Music
Video", "Remastered In 1080p", "on The Ed Sullivan Show", episode references, etc.).

Rate limit: one HTTP call per 1.1 s (respects MusicBrainz's 1 req/s cap).

#### Dominant-artist retry (conservative)

To reduce false artist matches in mostly single-artist folders, enrichment can run
an extra retry pass per directory:

- If a directory has at least `--dominant-min-files` entries and one artist covers
  at least `--dominant-threshold` (default 70%), that artist is treated as dominant.
- Rows with a different parsed artist are considered likely outliers.
- Those outliers are retried against MusicBrainz with the dominant artist, using
  conservative replacement rules (it does not force replacement aggressively).
- If no good retry match is found, the row is left as-is; optionally append a marker
  via `--dominant-fixme-suffix " (FIXME)"` for manual review.

---

### Phase 2 — Safe write (`--write`)

Copies files from their original location into `--target`, mirroring the source path:

```
/mnt/d/Musik/Rammstein/Mutter/01 Mein Herz Brennt.mp3
→ /mnt/d/Program_Targets/TaggingTarget/mnt/d/Musik/Rammstein/Mutter/01 Mein Herz Brennt.mp3
```

**The source files are never modified.**

For each copied file:
- Existing tags are backed up to `tag_backup.json` before any write
- Tags are written using `mutagen` (ID3 for `.mp3`, MP4 atoms for `.m4a`)
- Only non-empty fields are written; unresolved fields are left untouched
- When MB columns are present and a score exists, MB values take priority
  (disable with `--no-prefer-mb`)
- With `--mb-only`: only files with a MusicBrainz match are copied at all;
  confidence threshold is bypassed (MB match IS the quality gate)

---

### Standalone mode — Filename track-prefix cleanup (`--strip-track-prefix`)

This mode is independent from tagging/enrichment and exits after rename processing.

- Recursively scans each provided `ROOT` for `.mp3` and `.m4a`
- Renames **filename only** (keeps extension), stripping common leading track-number styles
- Never reads or writes metadata tags
- Optional dry run: `--strip-dry-run`
- Optional safe-copy test mode: `--strip-safe-copy-dir DIR`

Examples of prefixes removed:

- `01 - Song Title.mp3` → `Song Title.mp3`
- `(03) Song Title.m4a` → `Song Title.m4a`
- `[07] Song Title.mp3` → `Song Title.mp3`
- `Track 08 - Song Title.mp3` → `Song Title.mp3`

---

## Output files

All outputs land in `--out-dir` (default `./.batch_fix`). When scanning >1 root,
per-root reports are in `out_dir/<RootName>/`; the combined report is in `out_dir/`.

| File | Phase | Description |
|---|---|---|
| `dry_run_report.csv` | 1 | All proposed tag changes with confidence score. Not written for multi-root runs (see combined). |
| `unmatched_files.txt` | 1 | Files with confidence < 85 or no parse result |
| `unmatched_directories.txt` | 1 | Directories where >50% of files were unmatched |
| `combined_report.csv` | 1 (multi-root) | Union of all per-root dry_run_report.csv files |
| `mb_enriched_report.csv` | 1.5 | dry_run/combined CSV + MB and review metadata columns (see below) |
| `write_log.csv` | 2 | Per-file write record: source, dest, fields before and after, status |
| `tag_backup.json` | 2 | Raw tag dump of every file before writing (keyed by destination path) |

### CSV column reference

#### `dry_run_report.csv` / `combined_report.csv`

| Column | Description |
|---|---|
| `Path` | Absolute path to the source file |
| `Artist` | Proposed artist tag |
| `Title` | Proposed title tag |
| `Track` | Proposed track number (empty if not found) |
| `Album` | Proposed album tag (from folder) |
| `Confidence` | Score 60–95 (see confidence model above) |

#### `mb_enriched_report.csv` (adds)

| Column | Description |
|---|---|
| `MB_Artist` | Artist from MusicBrainz (empty = no match) |
| `MB_Title` | Title from MusicBrainz |
| `MB_Album` | Album/release title from MusicBrainz |
| `MB_Score` | Raw MusicBrainz API relevance score (0–100) |
| `MB_MatchSource` | `base` or `dominant_retry` when a dominant-artist retry supplied the accepted match |
| `Dir_Dominant_Artist` | Dominant artist detected for the file's directory (empty if none) |
| `Review_Flag` | Review marker for unresolved likely outliers (currently `dominant_outlier_no_match`) |

#### `write_log.csv`

| Column | Description |
|---|---|
| `Source` | Original file path |
| `Dest` | Copied file path in `--target` |
| `Confidence` | Score from Phase 1 |
| `Artist_written` / `Title_written` / `Track_written` / `Album_written` | Values actually written |
| `Artist_before` / `Title_before` / `Album_before` | Values read from the copy before writing |
| `Status` | `ok` or `ERROR: <message>` |

---

## Typical workflows

### Workflow A — Well-structured library (artist/album folders)

```bash
# 1. Dry run — inspect the CSV, check confidence distribution
python3 scripts/python-autotagger.py /mnt/d/Musik

# 2. If happy with Phase 1 results, write to staging
python3 scripts/python-autotagger.py /mnt/d/Musik --write

# 3. Verify staging, then move to final location manually
```

### Workflow B — Messy YouTube playlist dump (flat folder, no artist info)

```bash
# 1. Scan + enrich all entries via MusicBrainz
python3 scripts/python-autotagger.py "/mnt/d/Music/60s Hits Playlist" --enrich-all

# 2. Review .batch_fix/mb_enriched_report.csv

# 3. Write only MB-matched files to staging
python3 scripts/python-autotagger.py "/mnt/d/Music/60s Hits Playlist" \
    --enrich-all --write --mb-only

# Result: only songs MB could confidently identify are copied and tagged
```

### Workflow C — Multiple mixed roots, stress test

```bash
python3 scripts/python-autotagger.py \
    /mnt/d/Musik \
    /mnt/d/Program_Targets/RipperTarget \
    --out-dir /tmp/batch_results

# Per-root reports:  /tmp/batch_results/Musik/
#                    /tmp/batch_results/RipperTarget/
# Combined:          /tmp/batch_results/combined_report.csv
```

### Workflow D — OST folder with album-like prefixes in filenames

```bash
# Example file names: "Starsector OST - Battle Ambience.m4a"
# Parser treats "Starsector OST" as album-ish prefix, not as artist.
python3 scripts/python-autotagger.py \
  "/mnt/d/Program_Targets/RipperTarget/Stian Stark & Joel Baylis - Starsector Full OST" \
  --enrich-all --dominant-fixme-suffix " (FIXME)"

# Output to inspect:
# .batch_fix/*_dry_run_report.csv (Artist should be folder artist, not "Starsector OST")
# .batch_fix/*_mb_enriched_report.csv
```

### Workflow E — Duo artist query fallback

```bash
python3 scripts/python-autotagger.py \
  "/mnt/d/Program_Targets/RipperTarget/Ben Prunty & Simon Chylinski - Subnautica Full OST" \
  --enrich-all --out-dir .batch_fix/duo_artist_test

# MB query order for artist field:
# 1) "Ben Prunty & Simon Chylinski" 2) "Ben Prunty" 3) "Simon Chylinski"
```

---

## Constants you may want to tune

In the top of `scripts/python-autotagger.py`:

| Constant | Default | Effect |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | `85` | Minimum score for Phase 2 write (without `--mb-only`) |
| `MB_MIN_SCORE` | `75` | Minimum MusicBrainz API relevance score to accept a result |
| `MB_TITLE_MIN_SIM` | `0.75` | Minimum fuzzy title similarity (0–1) to accept a MB result |
| `MB_REQUEST_DELAY` | `1.1` | Seconds between MB API calls (must be ≥ 1.0) |
| `GENRE_FOLDERS` | see source | Folder names treated as genre categories, not artist names |
| `JUNK_PATTERNS` | see source | Regex patterns stripped from filenames/folders before parsing |
| `ALLOWED_CHARS` | `a-z A-Z 0-9 äöüÄÖÜß & ' - .` | Characters kept after cleaning |

---

## Safety guarantees

- **Source files are never modified.** Phase 2 always copies first.
- **Strong tags are always skipped.** Files with both `title` and `artist` already set
  are never proposed for changes.
- **Confidence gating.** Nothing below the write threshold is written unless you
  explicitly use `--mb-only`.
- **Full audit trail.** Every write is logged in `write_log.csv`; every pre-write tag
  state is saved in `tag_backup.json`.
- **Idempotent target dir.** The `--target` directory is fully owned by the tool and
  can be wiped and re-generated at any time.
