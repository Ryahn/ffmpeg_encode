# FFmpeg Settings Tab - Implementation Status

## Summary
The FFmpeg Settings tab implementation is **complete and functional**. All core systems are working correctly, including:
- ✅ Command preview generation with proper placeholder substitution
- ✅ File selection callback integration
- ✅ Media property detection (resolution, audio codec)
- ✅ Smart audio codec handling (copy vs re-encode)
- ✅ Subtitle handling policy system
- ✅ Quality preset configuration
- ✅ Command template generation with {INPUT}/{OUTPUT}/{AUDIO_TRACK}/{SUBTITLE_TRACK}/{SUBTITLE_FILE} placeholders

## Test Results

### Command Preview Generation ✅
- Template: `ffmpeg -i {INPUT} -c:v hevc_nvenc -cq 28 -preset p5 -y {OUTPUT}`
- Preview: `ffmpeg -i test_input.mkv -c:v hevc_nvenc -cq 28 -preset p5 -y test_input_encoded.mp4`
- Result: **PASS** - Placeholders properly replaced with actual file paths

### Command Substitution & Parsing ✅
- Input file path: Correctly substituted
- Output file path: Correctly substituted
- Audio track mapping: `{AUDIO_TRACK}` → actual track number
- Command parsing: Produces 19 valid FFmpeg arguments
- Result: **PASS** - All placeholders replaced and parsed correctly

### Callback Integration ✅
- FileListWidget has `on_file_selected` callback attribute
- FFmpegSettingsTab has `set_source_file()` method
- MainWindow connects: `files_tab.file_list.on_file_selected` → `_on_file_selected_for_ffmpeg()`
- FileListWidget connects: `itemSelectionChanged` signal → `_on_row_selected()` handler
- Result: **PASS** - Full callback chain properly implemented

### Media Detection ✅
- ffprobe integration implemented in `FFmpegSettingsTab._get_ffprobe_info()`
- Detects video resolution (width, height)
- Detects audio codec type
- Populates UI with detected properties
- Result: **PASS** - Media detection working

## Configuration Status

### Quality Presets ✅
```json
{
  "balanced": {"crf": 28, "preset": "medium"},
  "quality": {"crf": 24, "preset": "slow"},
  "compact": {"crf": 32, "preset": "faster"}
}
```
- Default: "balanced"
- UI: Dropdown selector in FFmpeg Settings tab
- Status: **Working**

### Subtitle Handling ✅
```json
{
  "pgs": "omit",
  "embedded_text": "mux",
  "embedded_ass": "external",
  "external_text": "keep",
  "external_ass": "keep",
  "subtitle_source_priority": ["external", "embedded"]
}
```
- Policy engine: `src/core/subtitle_policy.py`
- Classes: `SubtitleInfo`, `SubtitleDecision` in `core/encoder.py`
- Codec definitions: TEXT_SUBTITLE_CODECS, BITMAP_SUBTITLE_CODECS
- Status: **Working**

## Files Modified/Created

### Core Files
- ✅ `src/gui/tabs/ffmpeg_settings_tab.py` (NEW, 490 lines) - Complete implementation
- ✅ `src/gui/main_window.py` - Added FFmpeg Settings tab and callback connection
- ✅ `src/gui/widgets/file_list.py` - Added `_on_row_selected()` handler and signal connection
- ✅ `src/gui/tabs/ffmpeg_command_util.py` - Fixed quote-stripping issue
- ✅ `src/utils/config.py` - Added quality_presets configuration
- ✅ `src/core/ffmpeg_translator.py` - Added x265 → hevc_nvenc mapping
- ✅ `src/core/encoder.py` - Added subtitle handling classes
- ✅ `src/core/subtitle_policy.py` (NEW) - Subtitle policy decision engine

## Command Template Format

The FFmpeg Settings tab generates command templates using the following placeholders:

| Placeholder | Description | Example |
|------------|-------------|---------|
| `{INPUT}` | Input file path | `C:\video.mkv` |
| `{OUTPUT}` | Output file path | `C:\video_encoded.mp4` |
| `{AUDIO_TRACK}` | Audio stream index | `2` |
| `{SUBTITLE_TRACK}` | Subtitle stream index | `0` |
| `{SUBTITLE_FILE}` | External subtitle path | `C:\subtitles.srt` |

### Example Generated Command
```
ffmpeg -i {INPUT} \
  -map 0:v:0 -map 0:a:{AUDIO_TRACK} \
  -c:v hevc_nvenc -cq 28 -preset p5 \
  -c:a aac -b:a 128k \
  -y {OUTPUT}
```

After substitution:
```
ffmpeg -i C:\video.mkv \
  -map 0:v:0 -map 0:a:2 \
  -c:v hevc_nvenc -cq 28 -preset p5 \
  -c:a aac -b:a 128k \
  -y C:\video_encoded.mp4
```

## Features Implemented

### 1. Preset Selection
- Dropdown to select FFmpeg presets (e.g., "AppleTV 1080p30 Auto")
- Presets auto-load configuration from JSON files

### 2. Quality Presets
- Three quality tiers: Balanced, Quality, Compact
- Configurable CRF values and encoding presets
- Dynamic UI update based on selected preset

### 3. Video Encoding
- Video codec selection (HEVC GPU, H.264 GPU, HEVC CPU, H.264 CPU)
- CRF slider (0-51)
- Speed preset selector (p1-p7 for NVENC, ultrafast-placebo for software)
- Smart resolution handling:
  - Detects source resolution
  - Prevents upscaling (720p stays 720p)
  - Option to force 1080p if needed

### 4. Audio Handling
- Auto-detection of audio codec
- Smart audio copy (if codec is MP4-compatible)
- Fallback to re-encoding for incompatible codecs
- Audio bitrate configuration (96k-320k)

### 5. Subtitle Configuration
- Policy-based subtitle handling
- Support for external SRT/ASS files
- Support for embedded subtitles
- Different handling strategies:
  - Keep external
  - Mux into MP4
  - Omit from encoding
  - Burn into video

### 6. Command Preview
- Live preview of generated FFmpeg command
- Shows all selected options and substitutions
- Copy-to-clipboard button
- Real-time updates as settings change

### 7. File Selection Integration
- Automatic detection when file selected in Files tab
- Media properties auto-detected via ffprobe
- Resolution and audio codec displayed

## Known Limitations

1. **ffprobe detection**: Requires ffprobe to be in PATH or FFmpeg folder
2. **NVENC availability**: GPU encoding requires NVIDIA GPU with NVENC support
3. **Software encoding fallback**: h264_libx264 and hevc_libx265 are slower alternatives
4. **Subtitle burning**: Requires video re-encoding on playback (Jellyfin limitation)

## Next Steps (Optional Enhancements)

1. **Per-file subtitle overrides**: Allow users to override subtitle strategy per file
2. **Preset customization**: Allow saving custom presets from current settings
3. **Advanced audio filtering**: Audio normalization, mixing, delay compensation
4. **Batch encoding**: Queue files with different FFmpeg Settings presets
5. **Encoding preview**: Generate sample frames to preview quality settings

## Testing Instructions

### Manual Testing
1. Open the application and go to the "Files" tab
2. Select a video file from your library
3. Switch to the "FFmpeg Settings" tab
4. Verify that:
   - Source file name appears in "Source File" field
   - Resolution is detected correctly
   - Audio codec is detected
   - Command preview updates with {INPUT} and {OUTPUT} placeholders
5. Change quality preset and verify command updates
6. Change video codec and verify command updates

### Automated Testing
```bash
# Test command preview generation
python test_command_generation.py

# Test command substitution and parsing
python test_command_substitution.py

# Test FFmpeg Settings callback integration
python test_ffmpeg_settings.py
```

## Conclusion

The FFmpeg Settings tab is fully functional and ready for use. All placeholder substitution, command generation, and callback integration is working correctly. The system is prepared to handle encoding with proper file path substitution and flexible configuration options.
