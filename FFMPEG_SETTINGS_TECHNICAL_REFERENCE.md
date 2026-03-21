# FFmpeg Settings - Technical Reference

## Architecture Overview

### Component Diagram
```
FileListWidget (Files Tab)
    |
    └─> on_file_selected callback
        |
        └─> MainWindow._on_file_selected_for_ffmpeg()
            |
            └─> FFmpegSettingsTab.set_source_file()
                |
                ├─> FFmpegSettingsTab._get_ffprobe_info()  [Media Detection]
                ├─> FFmpegSettingsTab._update_preview()    [Command Generation]
                |
                └─> ffmpeg_command_util.generate_command_preview()
                    |
                    └─> Generate {INPUT}/{OUTPUT} placeholders

FFmpegTab (FFmpeg Tab)
    |
    └─> Custom command field (user pastes template from FFmpegSettingsTab)
        |
        └─> ffmpeg_command_util.generate_command_preview()  [Show preview]
        |
        └─> During encoding:
            └─> ffmpeg_command_util.parse_and_substitute_command()
                |
                └─> Replace placeholders with actual paths
                |
                └─> Parse with shlex.split()
                |
                └─> Return FFmpeg argument list
                |
                └─> Execute FFmpeg with parsed args
```

## Key Classes and Methods

### FFmpegSettingsTab (src/gui/tabs/ffmpeg_settings_tab.py)

```python
class FFmpegSettingsTab(QWidget):
    """Configure FFmpeg encoding settings and generate command templates."""

    def __init__(self, parent=None):
        """Initialize tab with all UI elements."""
        # Creates groups:
        # - Preset selection
        # - Video encoding (codec, CRF, speed, profile, level)
        # - Audio configuration
        # - Subtitle handling
        # - Command preview and copy button

    def set_source_file(self, file_path: Path) -> None:
        """Called when user selects file in Files tab."""
        # 1. Store source file path
        # 2. Run ffprobe detection
        # 3. Update UI with detected properties
        # 4. Call _update_preview()

    def _get_ffprobe_info(self, file_path: Path) -> Dict:
        """Detect media properties using ffprobe."""
        # Runs: ffprobe -v error -show_entries stream=...
        # Returns: JSON with stream information
        # Looks for: video resolution, audio codec

    def _update_preview(self) -> None:
        """Generate FFmpeg command template with placeholders."""
        # Builds command from:
        # - Selected codec, CRF, speed values
        # - Smart resolution handling
        # - Audio codec decision
        # - Subtitle configuration
        # Returns: Command with {INPUT}/{OUTPUT}/{AUDIO_TRACK} placeholders
```

### Command Preview Generation

#### Function: generate_command_preview()
**Location**: src/gui/tabs/ffmpeg_command_util.py

```python
def generate_command_preview(
    command_template: str,
    get_files_callback: Optional[Callable],
    get_output_path_callback: Optional[Callable],
    suffix: str,
) -> str:
    """Generate preview showing actual file paths."""
    # Input: Template like "ffmpeg -i {INPUT} -y {OUTPUT}"
    # Output: "ffmpeg -i C:\video.mkv -y C:\video_encoded.mp4"
    #
    # Process:
    # 1. Get first file from callback
    # 2. Parse source and output paths
    # 3. Replace placeholders:
    #    - {INPUT} → actual input path
    #    - {OUTPUT} → actual output path
    #    - {AUDIO_TRACK} → actual track number
    #    - {SUBTITLE_TRACK} → actual track number
    #    - {SUBTITLE_FILE} → actual subtitle path
    # 4. Return formatted command string
```

#### Function: parse_and_substitute_command()
**Location**: src/gui/tabs/ffmpeg_command_util.py

```python
def parse_and_substitute_command(
    command_template: str,
    input_file: Path,
    output_file: Path,
    audio_track: int,
    subtitle_track: Optional[int],
    subtitle_file: Optional[Path],
    on_log: Callable[[str, str], None],
) -> List[str]:
    """Parse template and return FFmpeg argument list."""
    # Input: Template with placeholders and actual file paths
    # Output: List of FFmpeg arguments ready for execution
    #
    # Process:
    # 1. Replace all placeholders with actual values
    # 2. Handle special cases:
    #    - Path quoting for spaces/special chars
    #    - Audio stream mapping
    #    - Subtitle file escaping
    # 3. Parse with shlex.split() to handle quotes correctly
    # 4. Return argument list: ["ffmpeg", "-i", "path", ...]
    #
    # Key fix (from previous work):
    # - shlex.split() is the single source of truth for quote handling
    # - Do NOT strip quotes afterward (causes double-quoting)
```

### Media Detection

#### Method: FFmpegSettingsTab._get_ffprobe_info()

**ffprobe command executed**:
```bash
ffprobe -v error \
  -show_entries stream=width,height,codec_name,codec_type \
  -of json \
  "C:\path\to\video.mkv"
```

**JSON output example**:
```json
{
  "streams": [
    {
      "index": 0,
      "codec_type": "video",
      "codec_name": "h264",
      "width": 1920,
      "height": 1080
    },
    {
      "index": 1,
      "codec_type": "audio",
      "codec_name": "aac"
    },
    {
      "index": 2,
      "codec_type": "subtitle",
      "codec_name": "subrip"
    }
  ]
}
```

**Parsing logic**:
```python
streams = data.get('streams', [])
for stream in streams:
    if stream.get('codec_type') == 'video' and not video_stream:
        video_stream = stream  # Extract resolution
    elif stream.get('codec_type') == 'audio' and not audio_stream:
        audio_stream = stream  # Extract codec
```

## Placeholder Substitution System

### Placeholder Types

| Placeholder | Type | Scope | Example |
|------------|------|-------|---------|
| `{INPUT}` | Path | Single file | `C:\input.mkv` |
| `{OUTPUT}` | Path | Single file | `C:\output.mp4` |
| `{AUDIO_TRACK}` | Index | Stream | `2` (0-indexed) |
| `{SUBTITLE_TRACK}` | Index | Stream | `0` |
| `{SUBTITLE_FILE}` | Path | Subtitle | `C:\subs.srt` |

### Substitution Process (Simplified)

```python
# 1. Start with template
template = 'ffmpeg -i {INPUT} -map 0:a:{AUDIO_TRACK} -y {OUTPUT}'

# 2. Apply regex replacements
command = re.sub(r'{INPUT}', input_file_path, template)
command = re.sub(r'{OUTPUT}', output_file_path, command)
command = re.sub(r'{AUDIO_TRACK}', str(audio_track), command)

# 3. Handle quoting for paths with spaces
def quote_path_if_needed(path_str: str) -> str:
    if any(c in path_str for c in ' &^%!'):
        return f'"{path_str}"'
    return path_str

# 4. Parse with shlex to handle all quoting correctly
args = shlex.split(command, posix=False)
# Result: ['ffmpeg', '-i', 'C:\\input.mkv', '-map', '0:a:2', '-y', 'C:\\output.mp4']
```

## Configuration System

### Quality Presets
**Location**: src/utils/config.py

```python
config.get('quality_presets') = {
    'balanced': {'crf': 28, 'preset': 'medium'},
    'quality': {'crf': 24, 'preset': 'slow'},
    'compact': {'crf': 32, 'preset': 'faster'}
}
```

**Usage in FFmpeg Settings**:
```python
preset = config.get_encoder_quality_preset()  # 'balanced'
crf_value = config.get_quality_preset_crf(preset)  # 28
speed = config.get_quality_preset_speed(preset)  # 'medium'
```

### Subtitle Handling Configuration
**Location**: src/utils/config.py

```python
config.get('subtitle_handling') = {
    'pgs': 'omit',                          # Bitmap subs: skip
    'embedded_text': 'mux',                 # Embedded SRT: mux
    'embedded_ass': 'external',             # Embedded ASS: keep external
    'external_text': 'keep',                # External SRT: keep file
    'external_ass': 'keep',                 # External ASS: keep file
    'subtitle_source_priority': ['external', 'embedded']
}
```

**Decision process**:
1. Check priority list: external sources before embedded
2. Look for external SRT (if exists → use external_text action)
3. Look for external ASS (if exists → use external_ass action)
4. Look for embedded text (if exists → use embedded_text action)
5. Look for embedded bitmap (if exists → use pgs action)
6. If nothing found → omit subtitles

## Audio Codec Auto-Copy Logic

```python
COMPATIBLE_MP4_CODECS = {'aac', 'mp3', 'opus'}

detected_codec = 'aac'  # From audio_stream.codec_name
if auto_copy_enabled:
    if detected_codec.lower() in COMPATIBLE_MP4_CODECS:
        # Use: -c:a copy (no re-encoding)
        audio_args = '-c:a copy'
    else:
        # Use: -c:a aac -b:a 128k (re-encode to MP4 compatible)
        audio_args = f'-c:a aac -b:a {bitrate}k'
else:
    # User disabled auto-copy, use configured codec
    audio_args = f'-c:a {fallback_codec} -b:a {bitrate}k'
```

## Command Building Process

### Step 1: Collect UI Values
```python
codec = self.codec_combo.currentData()           # 'hevc_nvenc'
crf = self.crf_spinbox.value()                  # 28
speed = self.speed_combo.currentData()          # 'p5'
profile = self.profile_combo.currentData()      # 'main'
level = self.level_combo.currentData()          # '4.1'
```

### Step 2: Smart Resolution Decision
```python
if upscale_enabled:
    scale_filter = 'scale=1920:1080:force_original_aspect_ratio=decrease'
else:
    if source_height <= 1080:
        # Don't upscale, but allow downscaling with intelligent limits
        scale_filter = f'scale=min(1920,{src_width}):min(1080,{src_height}):...'
    else:
        # Source > 1080p, downscale to 1080p
        scale_filter = 'scale=1920:1080:force_original_aspect_ratio=decrease'
```

### Step 3: Build Command Parts
```python
cmd_parts = [
    'ffmpeg -i {INPUT}',
    '-map 0:v:0 -map 0:a:0',
    f'-c:v {codec}',
    f'-cq {crf}',
    f'-preset {speed}',
    f'-profile:v {profile}',
    f'-level {level}',
    f'-vf "{scale_filter}"',
    '-color_range tv',
    '-pix_fmt yuv420p',
    '-g 60',
    audio_codec_option,  # '-c:a aac -b:a 128k'
    '-ac 2',
    '-map_chapters 0',
    '-map_metadata 0',
    '-y {OUTPUT}'
]

command = " ".join(cmd_parts)
```

### Step 4: Return Template
```
ffmpeg -i {INPUT} -map 0:v:0 -map 0:a:0 \
  -c:v hevc_nvenc -cq 28 -preset p5 -profile:v main -level 4.1 \
  -vf "scale=min(1920,1920):min(1080,1080):force_original_aspect_ratio=decrease" \
  -color_range tv -pix_fmt yuv420p -g 60 \
  -c:a aac -b:a 128k -ac 2 \
  -map_chapters 0 -map_metadata 0 \
  -y {OUTPUT}
```

## Integration Points

### MainWindow Callback Connection
```python
# In MainWindow.__init__()
self.ffmpeg_settings_tab = FFmpegSettingsTab()
self.tab_widget.addTab(self.ffmpeg_settings_tab, "FFmpeg Settings")

# Connect file selection callback
self.files_tab.file_list.on_file_selected = self._on_file_selected_for_ffmpeg

def _on_file_selected_for_ffmpeg(self, file_path: Path) -> None:
    if self.ffmpeg_settings_tab:
        self.ffmpeg_settings_tab.set_source_file(file_path)
```

### FileListWidget Signal Connection
```python
# In FileListWidget.__init__()
self._table.itemSelectionChanged.connect(self._on_row_selected)

def _on_row_selected(self) -> None:
    if not self.on_file_selected:
        return

    selected_rows = self._table.selectionModel().selectedRows()
    if selected_rows:
        row_index = selected_rows[0].row()
        if 0 <= row_index < len(self.files):
            file_path = Path(self.files[row_index]["path"])
            self.on_file_selected(file_path)  # Call callback
```

## Error Handling

### ffprobe Failures
```python
def _get_ffprobe_info(self, file_path: Path) -> Dict:
    # Falls back to empty dict if ffprobe not found or fails
    if not ffprobe:
        return {}
    try:
        # Execute and parse JSON
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass  # Return empty dict
    return {}
```

### Command Parsing Failures
```python
def parse_and_substitute_command(...) -> List[str]:
    try:
        args = shlex.split(command, posix=False)
    except Exception as e:
        on_log("ERROR", f"Command parsing failed ({e}); cannot build argument list.")
        return []

    # Validate input file exists
    for i, arg in enumerate(args):
        if arg == "-i" and i + 1 < len(args):
            input_path = args[i + 1]
            if not Path(input_path).exists():
                on_log("ERROR", f"Input file does not exist: {input_path}")
```

## Performance Optimization

### Lazy Media Detection
- ffprobe only runs when:
  - User selects a new file
  - User manually changes source file
  - Does NOT run on every setting change

### Debounced Preview Updates
- Command preview generation debounced
- Updates occur when:
  - Source file changes
  - Codec selection changes
  - Quality preset changes
  - Resolution settings change

### Configuration Caching
- Quality presets cached in memory
- Config file only loaded at startup
- Changes to config immediately effective

## Testing Strategy

### Unit Tests (Existing)
- test_command_generation.py: Placeholder substitution
- test_command_substitution.py: Full parsing pipeline

### Integration Points to Test
1. File selection callback chain
2. Media detection with various file types
3. Command template generation with all codec combinations
4. Subtitle policy decisions with different source types
5. Audio codec detection and fallback logic

### Manual Testing Checklist
- [ ] Select file → media properties detected
- [ ] Change quality preset → command updates
- [ ] Change codec → command updates
- [ ] Toggle audio auto-copy → command updates
- [ ] Copy command → clipboard contains correct template
- [ ] Paste in FFmpeg tab → preview shows actual paths
- [ ] Encode with pasted command → encoding succeeds

## Known Issues and Workarounds

### Issue: ffprobe command not found
**Root cause**: FFmpeg not in PATH, or ffprobe not in same directory
**Workaround**: Configure FFmpeg path in Settings tab

### Issue: Double-quoting of paths
**Root cause**: Multiple layers of quote processing (FIXED)
**Solution**: Use shlex.split() as single source of truth, don't strip quotes afterward

### Issue: Audio codec unknown
**Root cause**: Uncommon audio codec not in MP4 compatibility list
**Workaround**: Uses fallback codec (AAC) automatically

## Future Improvements

### Potential Enhancements
1. **Custom filter templates**: Allow users to save filter chains
2. **Batch preset application**: Apply same settings to multiple files
3. **Encoding preview**: Generate sample frames with different settings
4. **Hardware detection**: Auto-detect available codecs at startup
5. **Command validation**: Warn about potentially invalid FFmpeg args
6. **Preset management UI**: Save/load custom presets from UI

### Code Quality Improvements
1. Add type hints to all functions
2. Extract command building to separate module
3. Add comprehensive unit test suite
4. Add integration tests for full workflow
5. Performance profiling for media detection

## References

### Related Documentation
- FFMPEG_SETTINGS_COMPLETE.md: Implementation summary
- FFMPEG_SETTINGS_USER_GUIDE.md: User instructions
- IMPLEMENTATION_STATUS.md: Testing results

### External Resources
- FFmpeg Documentation: https://ffmpeg.org/documentation.html
- ffprobe Manual: https://ffmpeg.org/ffprobe.html
- PyQt6 Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt6/
