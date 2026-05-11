# Multi-Format Audio/Video Conversion Implementation Guide

**Date Created:** May 1, 2026  
**Status:** Design Phase - Awaiting Decision  
**Context:** Conversation exploring 5 implementation patterns for multi-format codec conversion

---

## Current Architecture Analysis

### Existing Format Handling
- **Audio:** MP3 (libmp3lame) or AAC (aac) via `audio_mp3` boolean flag
- **Video:** H.264 (copy codec) in MP4 container
- **Config System:** JSON-based preferences with CLI arg merging
- **Stream Selection:** Via `StreamSelector` (resolution/bitrate/mime)
- **Codec Application:** Via `StreamConverter.convert_audio()` and `combine_streams()`

### Data Flow
```
CLI args (--audio_mp3) 
  → DownloadOptions dataclass 
  → StreamSelector/StreamConverter 
  → FFMPEG invocation with hardcoded codec flags
```

### Key Components
- **preferences.py**: `DownloadOptions` dataclass (central option carrier)
- **stream_converter.py**: Legacy methods `convert_audio()`, `combine_streams()` + unused stubs
- **cli_command.py**: Argument parsing and option merging
- **utils.py**: Alias mappings (quality, bitrate, resolution)
- **codec_config.py**: Proposed new module (does not exist yet)

### Open Gaps
- `VideoConversionParameters` dataclass defined but unused
- `preferred_format` field in DownloadOptions never used (reserved slot)
- Codec selection hardcoded (not parameterized)
- No registry or plugin system for formats

---

## 5 Implementation Patterns

### Pattern 1: Extended Dict Configuration
**Simplicity Level:** ⭐⭐⭐ (Moderate)  
**Type Safety:** ⭐⭐ (Limited)  
**Extensibility:** ⭐⭐ (Basic dict operations)

**Artifacts:**
- `codec_profiles_dict.py` - Dict-based codec definitions
- Usage in `stream_converter.py` - Dynamic arg lookup

**Pros:**
- Closest to existing code patterns
- Easy to add new formats
- Low boilerplate

**Cons:**
- No validation
- Hardcoded strings throughout
- No type hints for IDE support
- Brittle to refactoring

---

### Pattern 2: Dataclass Registry (RECOMMENDED)
**Simplicity Level:** ⭐⭐⭐⭐ (Good balance)  
**Type Safety:** ⭐⭐⭐⭐⭐ (Full)  
**Extensibility:** ⭐⭐⭐⭐ (Excellent)

**Artifacts:**
- `codec_registry.py` - Registry + dataclass definitions
- Integration points in `stream_converter.py`
- `DownloadOptions` updates

**Pros:**
- Type-safe (Pylance integration)
- Leverages unused `VideoConversionParameters`
- Central registry for validation
- CLI integration straightforward

**Cons:**
- More initial boilerplate
- Requires careful dataclass design

**Recommended For:** Your use case—production-ready with growth path

---

### Pattern 3: CLI Integration with Format Selection
**Simplicity Level:** ⭐⭐⭐ (Moderate)  
**Type Safety:** ⭐⭐⭐⭐ (Via Pattern 2)  
**Extensibility:** ⭐⭐⭐ (Limited to CLI layer)

**Artifacts:**
- `cli_format_commands.py` - Format listing and selection helpers
- `cli_command.py` modifications - New `--output-format`, `--list-formats` flags

**Pros:**
- User-friendly discovery (`--list-formats`)
- Integrates with existing preference system
- CLI-first design

**Cons:**
- Depends on Pattern 2 or 1
- Requires `DownloadOptions` schema update

**Usage Example:**
```bash
./yt_ripper.py <url> --output-format opus --bitrate 192k
./yt_ripper.py --list-formats
```

---

### Pattern 4: Template-Based Command Builder
**Simplicity Level:** ⭐⭐ (Low—complex templates)  
**Type Safety:** ⭐⭐⭐ (Moderate—Jinja2 is untyped)  
**Extensibility:** ⭐⭐⭐⭐ (Excellent for conditional logic)

**Artifacts:**
- `ffmpeg_command_templates.py` - Jinja2 template definitions
- `ffmpeg_builder.py` - Template renderer + fallback logic

**Pros:**
- Readable FFMPEG commands
- Easy to audit/version commands
- Flexible for complex scenarios
- Human-readable format

**Cons:**
- Adds Jinja2 dependency
- Template logic harder to test
- Less type safety

**Best For:** Complex encoding scenarios with many conditional options

---

### Pattern 5: Plugin System
**Simplicity Level:** ⭐ (High complexity)  
**Type Safety:** ⭐⭐⭐⭐ (Via ABC + dataclasses)  
**Extensibility:** ⭐⭐⭐⭐⭐ (Maximum)

**Artifacts:**
- `codec_plugins.py` - Abstract base class + plugin interface
- `plugins/` directory - Individual plugin modules
- `plugin_registry.py` - Discovery and registration

**Pros:**
- Third-party extensible
- Clean separation of concerns
- Zero-cost plugins (lazy load)
- Environment validation (codec availability check)

**Cons:**
- Significant boilerplate
- Discovery mechanism required
- Overkill for simple needs

**Best For:** Long-term extensibility, community contributions

---

## Implementation Roadmap

### Phase 1: Foundation (Pattern 2)
1. Create `codec_registry.py` with dataclass definitions
2. Register built-in profiles (MP3, AAC, Opus, Vorbis, H264, H265)
3. Update `DownloadOptions` to include `output_format` and `target_bitrate` fields
4. Modify `StreamConverter.convert_audio()` to use registry
5. Write unit tests for codec registration

**Effort:** ~2-3 hours  
**Risk:** Low—backward compatible

### Phase 2: CLI Integration (Pattern 3)
1. Add `--output-format` and `--bitrate` flags to CLI
2. Add `--list-formats` command
3. Extend `DownloadOptions.from_preferences()` to load format choice
4. Update preferences schema in `user_settings_*.json`

**Effort:** ~1-2 hours  
**Risk:** Very low

### Phase 3: Advanced Scenarios (Pattern 4 or 5)
1. Decide: Template-based (Pattern 4) for complex ffmpeg logic OR Plugin system (Pattern 5) for extensibility
2. Implement chosen pattern
3. Migrate patterns 1-2 profiles into new system

**Effort:** Pattern 4: ~2 hours | Pattern 5: ~4-5 hours  
**Risk:** Medium—larger refactor

---

## File Structure After Implementation

```
source/
├── infrastructure/
│   ├── codec_registry.py           # Pattern 2: Core dataclass + registry
│   ├── codec_profiles_dict.py       # Pattern 1: Dict definitions (optional)
│   ├── ffmpeg_command_templates.py  # Pattern 4: Jinja2 templates (optional)
│   ├── ffmpeg_builder.py            # Pattern 4: Template renderer (optional)
│   ├── codec_plugins.py             # Pattern 5: Plugin interface (optional)
│   ├── plugin_registry.py           # Pattern 5: Plugin discovery (optional)
│   ├── plugins/                     # Pattern 5: Plugin directory (optional)
│   │   ├── __init__.py
│   │   ├── mp3_plugin.py
│   │   ├── opus_plugin.py
│   │   └── h265_plugin.py
│   ├── stream_converter.py          # MODIFIED: Use registry in convert_audio()
│   └── os_interactions.py           # (No changes needed)
│
├── cli/
│   ├── cli_command.py               # MODIFIED: Add --output-format, --list-formats
│   └── cli_format_commands.py       # Pattern 3: Format helpers (new)
│
└── utility/
    └── preferences.py               # MODIFIED: Add output_format, target_bitrate to DownloadOptions
```

---

## Key Design Decisions

### 1. Bitrate Handling
- Store bitrate as string ("192k" for FFMPEG, not integer)
- Support format-specific bitrate limits in profile
- Validate against profile.supported_bitrates

### 2. Extension Determination
- Output extension from `CodecProfile.output_ext`
- Computed at time of conversion, not at option parse time
- Allows multiple formats with same container (e.g., both .m4a and .mp4 for AAC)

### 3. Codec vs. Container
- Distinguish between codec (libmp3lame) and container (mp3)
- Profile names match user-facing format strings
- Internal FFMPEG codec names are data, not logic

### 4. Backward Compatibility
- `audio_mp3=True` maps to format "mp3" internally
- Legacy code paths work unchanged
- New code paths use registry
- Gradual migration path

---

## Testing Strategy

### Unit Tests (Pattern 2)
```python
def test_codec_profile_registration():
    assert CodecRegistry.get("mp3") is not None
    
def test_unsupported_format_raises():
    with pytest.raises(ValueError):
        CodecRegistry.get("nonexistent")
        
def test_bitrate_validation():
    profile = CodecRegistry.get("mp3")
    assert profile.is_bitrate_supported("192k")
    assert not profile.is_bitrate_supported("999k")
    
def test_ffmpeg_command_generation():
    profile = CodecRegistry.get("mp3")
    cmd = profile.build_ffmpeg_command("in.opus", "out.mp3", "192k")
    assert "-acodec" in cmd
    assert "libmp3lame" in cmd
    assert "-b:a" in cmd
```

### Integration Tests
```python
def test_convert_audio_with_format():
    converter = StreamConverter()
    result = converter.convert_audio(Path("test.opus"), "mp3", "192k")
    assert result.suffix == ".mp3"
    assert result.exists()
```

---

## CLI Usage Examples (After Implementation)

```bash
# List available formats
./yt_ripper.py --list-formats

# Download and convert to Opus
./yt_ripper.py "https://www.youtube.com/watch?v=..." \
  --output-format opus --bitrate 128k

# Download and convert to high-quality MP3
./yt_ripper.py "https://www.youtube.com/watch?v=..." \
  --audio_only --output-format mp3 --bitrate 320k

# Download video as H.265
./yt_ripper.py "https://www.youtube.com/watch?v=..." \
  --output-format h265

# Save format preference to config
./yt_ripper.py "https://www.youtube.com/watch?v=..." \
  --output-format opus --bitrate 192k --save-config
```

---

## Next Steps

1. **Review this guide** with team/stakeholders
2. **Choose pattern(s):**
   - Commit to Pattern 2 (recommended) + Pattern 3 (CLI)
   - OR combine multiple patterns
3. **Create feature branch:** `feature/multi-format-conversion`
4. **Generate implementation artifacts** for chosen pattern
5. **Begin Phase 1 implementation**

---

## Decision Matrix

| Requirement | Pattern 1 | Pattern 2 | Pattern 3 | Pattern 4 | Pattern 5 |
|---|---|---|---|---|---|
| Type Safety | ❌ | ✅ | ✅ | ⚠️ | ✅ |
| Easy to extend | ⚠️ | ✅ | ❌ | ✅ | ✅ |
| Low boilerplate | ✅ | ⚠️ | ✅ | ⚠️ | ❌ |
| Testable | ❌ | ✅ | ⚠️ | ⚠️ | ✅ |
| Production-ready | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| Community plugins | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Recommended** | - | **YES** | +Pattern 2 | Complex cases | Future |

