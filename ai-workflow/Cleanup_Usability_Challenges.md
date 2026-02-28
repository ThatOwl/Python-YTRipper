Let me check what needs to be cleaned first, then write docs and clean up in parallel: 

Ran terminal command:  find /home/localuser/GitRepos/Python-YTRipper/.batch_fix -type f 2>/dev/null | sort; echo "---TEMP---"; ls /tmp/60s_test* /tmp/stresstest* /tmp/phase2* 2>/dev/null

Good. Now writing the docs and cleaning up simultaneously: 

Created [](file:///home/localuser/GitRepos/Python-YTRipper/README_auto_tagging.md)

Summarized conversation history

Ran terminal command:  rm -rf /home/localuser/GitRepos/Python-YTRipper/.batch_fix && rm -f /tmp/60s_test.txt /tmp/60s_test2.txt /tmp/stresstest_out.txt /tmp/phase2_out.txt && echo "done"

Done. Documentation written to README_auto_tagging.md, all temp files deleted.

---

## Usability & Challenges — Discussion

*(Referencing Session_Snapshot_file_cleanup.md)*

### What works well

**Structured library folders** (`Artist/Album/tracks`): the tool handles these near-perfectly. The 95/90/85 confidence tier captures virtually every well-named file. The 6,254-file stress test had zero parse failures and `Musik/` — which is a curated library — came in at 96.1% above threshold with no MB pass needed.

**Track-numbered files**: `03 - Some Song.mp3` and `03 Some Song.mp3` patterns both resolve cleanly with artist from folder. This is the strongest, least ambiguous signal in any file collection.

**MusicBrainz enrichment on flat playlist dumps**: the 60s test — 84/97 (87%) matched and written cleanly — shows that `--enrich-all --mb-only` is a solid strategy for "YouTube playlist folder, no idea what's in it." The tool only writes what MB can verify.

**The GENRE_FOLDERS detection** correctly prevents folder names like `Filmmusik`, `Serienmusik`, `Musik` from being misidentified as artist names. This was a real-world pain point that required explicit dataset knowledge to handle.

---

### Persistent challenges

**The reversal problem — artist vs. title order.** `"Bad Moon Rising - Creedence Clearwater Revival"` parses artist = *Bad Moon Rising* because the tool has no external reference for which side is the artist. Folder context helps when it's a single-artist folder, but in a flat mixed playlist dump there is none. MB then succeeds anyway — but on the *wrong* side. This is structurally unsolvable without either (a) a reference list of known artists or (b) querying MB both ways and comparing scores. Neither is implemented yet.

**False positives on title-only MB queries.** When no artist is known, the tool falls back to a title-only MB query. "Wild Thing" or "Twist and Shout" will match confidently — but it may match a cover recording, a live version, or the wrong artist. The similarity gate (`MB_TITLE_MIN_SIM`) helps but doesn't eliminate this.

**MB rate limiting is slow at scale.** 1.1 s/call × 3 attempts × hundreds of entries = multi-minute runs. The Session Snapshot ("Phase 3 – Large-Scale Trash Management") flagged this as a scalability concern. It's not addressed yet; an async queue or local cache would help significantly.

**`[unknown]` and completely untagged rips.** Files where both tags are empty and the filename is just `track01.mp3` / `01.m4a` produce 60-confidence entries at best. They appear in `unmatched_files.txt`. MB title-only queries on "Track 01" return garbage. These require a human.

**Flat playlist dumps with no folder artist context** (the 60s folder at 67.9% Phase-1 pass rate) represent the hardest case. MB recovers most of them, but the ones MB can't match are left unwritten — probably the right call, but the user has no actionable path forward beyond manually renaming them.

---

### Recommended usage pattern

1. **Point the tool at single-artist or single-album directories** for Phase 1 alone. This is where confidence is highest and the output most trustworthy.  
2. **Use `--enrich-all --mb-only`** on flat YouTube playlist dumps. Accept that ~10–15% won't be matched and won't be written — that is intentional conservatism.  
3. **Always review `unmatched_files.txt`** before deciding the run is done. It tells you exactly which files fell below threshold and why.  
4. **`write_log.csv` and `tag_backup.json`** provide a full rollback path if a batch write produces unexpected results. The tagged copies can be deleted and regenerated from the CSVs.

---

### What's still missing (per Session Snapshot "Phase 3")

The Snapshot described *pattern clustering* — automatically grouping `unmatched_files.txt` entries by folder to detect systematic failures (e.g. "all RipperTarget files are artist-reversed"). That analysis would let the tool auto-apply a per-folder correction heuristic. Not yet built. It would also benefit from the *known-artist reference list* approach above as a reversal disambiguator. These are the two highest-leverage unimplemented features.

Made changes.