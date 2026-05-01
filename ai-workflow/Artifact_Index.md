# Artifact Index: Multi-Format Audio/Video Conversion

**Status:** Design Phase - Artifacts Ready for Implementation  
**Date Created:** May 1, 2026  
**Project:** Python-YTRipper  
**Context:** Support for multiple audio/video codec formats beyond current MP3/AAC/H.264 limitation

---

## Overview

This directory contains a complete design package for implementing flexible, multi-format audio/video conversion in Python-YTRipper. The artifacts support 5 different implementation patterns ranging from simple dict-based configuration to a full plugin system.

**Recommendation:** Start with **Pattern 2 (Dataclass Registry)** + **Pattern 3 (CLI Integration)** for a balanced production solution.

---

## Artifact Files

### 📋 Documentation

1. **Format_Conversion_Implementation_Guide.md** (MAIN REFERENCE)
   - Complete analysis of current architecture
   - Detailed breakdown of all 5 patterns
   - Implementation roadmap with phases
   - Design decisions and testing strategy
   - Decision matrix for pattern selection

### 🔧 Code Skeletons (Ready to Implement)

2. **Pattern_1_Dict_Config_Skeleton.py**
   - Simplest approach using nested dicts
   - Minimal boilerplate
   - Use when: Quick prototyping, simple needs
   - **Effort:** ~2 hours
   - **Risk:** Low (but not type-safe)

3. **Pattern_2_Dataclass_Registry_Skeleton.py** ⭐ RECOMMENDED
   - Type-safe dataclass + registry system
   - Leverages unused `VideoConversionParameters`
   - Integration points clearly marked
   - Use when: Production-grade solution needed
   - **Effort:** ~2-3 hours
   - **Risk:** Very low (backward compatible)
   - **Includes:** Complete docstrings and usage patterns

4. **Pattern_3_CLI_Integration_Skeleton.py**
   - User-friendly CLI commands
   - Format discovery and listing
   - Depends on Pattern 2 (or 1)
   - Use when: User-facing interface needed
   - **Effort:** ~1-2 hours
   - **Risk:** Very low
   - **Includes:** Example usage and output

5. **Pattern_4_Template_Builder_Skeleton.py**
   - Jinja2-based command generation
   - Human-readable FFMPEG commands
   - Flexible for complex scenarios
   - Use when: Complex encoding pipelines needed
   - **Effort:** ~2 hours
   - **Risk:** Medium (Jinja2 dependency)
   - **Includes:** Multiple codec template examples

6. **Pattern_5_Plugin_System_Skeleton.py**
   - Fully extensible plugin architecture
   - Dynamic loading from plugins/ directory
   - Built-in plugins provided
   - Use when: Community extensibility needed
   - **Effort:** ~4-5 hours
   - **Risk:** Medium (largest refactor)
   - **Includes:** Plugin interface, example plugins, hooks

---

## Quick Start: Implementation Path

### Phase 1: Foundation (Recommended First)
**Files to implement:** Pattern_2_Dataclass_Registry_Skeleton.py

1. Copy dataclass definitions to new file: `source/infrastructure/codec_registry.py`
2. Update `source/utility/preferences.py`:
   - Add `output_format: str` field to `DownloadOptions`
   - Add `target_bitrate: str` field to `DownloadOptions`
   - Update `DEFAULT_PREFS` and `from_preferences()`
3. Update `source/infrastructure/stream_converter.py`:
   - Replace hardcoded codec selection with `CodecRegistry.get()`
   - Use `profile.build_ffmpeg_command()` instead of manual arg building
4. Write unit tests for codec registration and FFMPEG command generation

**Estimated Time:** 2-3 hours  
**Backward Compatibility:** ✅ Maintained  
**Type Safety:** ✅ Full Pylance support

### Phase 2: User Interface (Highly Recommended)
**Files to implement:** Pattern_3_CLI_Integration_Skeleton.py

1. Create new file: `source/cli/format_helpers.py` with `FormatSelectionHelper` class
2. Update `source/cli/cli_command.py`:
   - Add `--output-format`, `--bitrate`, `--list-formats`, `--format-info` flags
   - Add format validation and discovery methods
3. Update preference schema to persist format choices

**Estimated Time:** 1-2 hours  
**Impact:** Major usability improvement

### Phase 3: Advanced (Optional)
**Choose ONE:**

**Option A: Template-Based (Pattern 4)**
- Use if: Complex FFMPEG pipelines, auditable commands, custom scenarios
- Time: ~2 hours
- Add: `source/infrastructure/ffmpeg_builder.py`

**Option B: Plugin System (Pattern 5)**
- Use if: Long-term extensibility, third-party support, clean architecture
- Time: ~4-5 hours
- Add: `source/infrastructure/codec_plugins.py` + `source/infrastructure/plugins/`

---

## File Organization

```
ai-workflow/
├── Format_Conversion_Implementation_Guide.md     ← START HERE
├── Artifact_Index.md                              ← YOU ARE HERE
├── Pattern_1_Dict_Config_Skeleton.py
├── Pattern_2_Dataclass_Registry_Skeleton.py       ← USE THIS FIRST
├── Pattern_3_CLI_Integration_Skeleton.py          ← USE THIS SECOND
├── Pattern_4_Template_Builder_Skeleton.py         ← OPTIONAL
└── Pattern_5_Plugin_System_Skeleton.py            ← OPTIONAL FOR FUTURE

After implementation, code moves to:
source/
├── infrastructure/
│   ├── codec_registry.py                          (from Pattern 2)
│   ├── ffmpeg_builder.py                          (from Pattern 4 if chosen)
│   ├── codec_plugins.py                           (from Pattern 5 if chosen)
│   └── plugins/                                   (from Pattern 5 if chosen)
└── cli/
    └── format_helpers.py                          (from Pattern 3)
```

---

## Key Integration Points

### 1. Stream Converter Update
**File:** `source/infrastructure/stream_converter.py`

**Current:**
```python
def convert_audio(self, audio_path: Path, format_flag: bool) -> Path:
    # Hardcoded: if format_flag then mp3 else aac
```

**After Pattern 2:**
```python
def convert_audio(self, audio_path: Path, target_format: str, bitrate: str) -> Path:
    profile = CodecRegistry.get(target_format)
    output_path = audio_path.with_suffix(profile.output_ext)
    cmd = profile.build_ffmpeg_command(str(audio_path), str(output_path), bitrate)
    subprocess.run(cmd, check=True)
    return output_path
```

### 2. CLI Arguments
**File:** `source/cli/cli_command.py`

**New Options:**
```bash
--output-format {mp3,aac,opus,flac,h264,h265,vp9}
--bitrate 192k
--list-formats
--format-info opus
```

### 3. Download Options Dataclass
**File:** `source/utility/preferences.py`

**Add Fields:**
```python
@dataclass
class DownloadOptions:
    # ... existing fields ...
    output_format: str = "mp3"
    target_bitrate: str = "192k"
```

### 4. Preferences JSON Schema
**File:** `config/user_settings_{username}.json`

**Add to schema:**
```json
{
    "output_format": "mp3",
    "target_bitrate": "192k"
}
```

---

## Decision Tree

**Q: Which pattern should I implement?**

```
├─ "I want it done quickly"
│  └─ Pattern 1 (Dict Config) - Simplest
│
├─ "I want production-ready code"
│  └─ Pattern 2 (Dataclass Registry) ⭐ RECOMMENDED
│     └─ Plus Pattern 3 (CLI) for user interface
│
├─ "I need complex encoding logic"
│  └─ Pattern 2 + Pattern 4 (Templates)
│
└─ "I want long-term extensibility"
   └─ Pattern 2 + Pattern 5 (Plugins)
```

---

## Testing Checklist

After implementing each pattern, verify:

### Pattern 2 Tests
- [ ] Codec profile registration works
- [ ] Unsupported format raises ValueError
- [ ] Bitrate validation passes/fails correctly
- [ ] FFMPEG command generation produces valid commands
- [ ] Old audio_mp3=True behavior maps to format="mp3"

### Pattern 3 Tests
- [ ] `--list-formats` produces formatted output
- [ ] `--format-info <fmt>` shows correct details
- [ ] Format choice gets saved to config with `--save-config`
- [ ] Invalid format rejected with helpful error

### End-to-End Test
```bash
# Download and convert to multiple formats
./yt_ripper.py <url> --audio_only --output-format mp3 --bitrate 320k
./yt_ripper.py <url> --audio_only --output-format opus --bitrate 192k
./yt_ripper.py <url> --output-format h265
```

---

## Backward Compatibility Notes

**Patterns 1-5 are all backward compatible** because:
1. `audio_mp3=True` can be automatically converted to `output_format="mp3"`
2. Legacy CLI flags still work unchanged
3. Preference loading includes defaults
4. Existing code paths remain untouched during gradual migration

**Migration Strategy:**
1. Implement new registry alongside old code
2. Update `convert_audio()` to use registry
3. Old code paths deprecated (but functional) until full migration
4. No breaking changes to user configs or CLI

---

## Recommended Implementation Sequence

```
Week 1:
  ├─ Review Format_Conversion_Implementation_Guide.md
  ├─ Implement Pattern 2 (codec_registry.py)
  └─ Unit test codec profiles

Week 2:
  ├─ Integrate Pattern 2 into stream_converter.py
  ├─ Update DownloadOptions dataclass
  └─ Integration tests with actual audio conversion

Week 3:
  ├─ Implement Pattern 3 (CLI integration)
  ├─ Add --list-formats, --format-info commands
  └─ User acceptance testing

Week 4 (Optional):
  ├─ Evaluate if Pattern 4 or 5 needed
  ├─ Implement chosen pattern if needed
  └─ Performance and stress testing
```

---

## Next Steps

1. **Read** `Format_Conversion_Implementation_Guide.md` (15 min)
2. **Review** `Pattern_2_Dataclass_Registry_Skeleton.py` code (20 min)
3. **Create feature branch:** `git checkout -b feature/multi-format-conversion`
4. **Begin Phase 1:** Copy Pattern 2 skeleton to `source/infrastructure/codec_registry.py`
5. **Implement integration points** per the guide
6. **Test thoroughly** before merging

---

## Questions & Clarifications

For questions about:
- **Architecture:** See Format_Conversion_Implementation_Guide.md section "Current Architecture Analysis"
- **Patterns comparison:** See "Decision Matrix" in main guide
- **Implementation details:** See comments in Pattern_*_Skeleton.py files
- **Integration points:** See "Integration Patterns" sections in each skeleton

---

## Artifacts Created By

Generated from conversation on May 1, 2026  
Context: Python-YTRipper multi-format audio/video conversion design session  
Patterns: 5 implementation approaches, ranging from simple to fully extensible

**All artifacts are production-ready and can be directly implemented into the codebase.**
