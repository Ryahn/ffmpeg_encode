# FFmpeg Settings Tab - User Guide

## Quick Start

### 1. Open FFmpeg Settings Tab
- Start the Video Encoder application
- Click the "FFmpeg Settings" tab

### 2. Select Source File
- Go to the "Files" tab and select a video file
- The FFmpeg Settings tab will automatically:
  - Display the file name
  - Detect the video resolution
  - Detect the audio codec

### 3. Configure Encoding
Choose your preferred settings:

**Preset Selection**
- Select a preset like "AppleTV 1080p30 Auto" (optional)
- Presets auto-load all recommended settings

**Quality Preset**
- **Balanced** (default): Good quality, moderate file size (~28 CRF)
- **Quality**: Best quality, larger files (~24 CRF)
- **Compact**: Smallest files, acceptable quality (~32 CRF)

**Video Codec**
- **HEVC GPU** (hevc_nvenc): Best quality, fastest with NVIDIA GPU
- **H.264 GPU** (h264_nvenc): Good compatibility, faster with NVIDIA GPU
- **HEVC CPU** (hevc_libx265): Best quality without GPU, very slow
- **H.264 CPU** (h264_libx264): Good quality without GPU, very slow

**Audio Settings**
- Auto-copy: Enable to keep original audio if compatible
- Fallback codec: What to use if original audio can't be copied
- Bitrate: Audio quality in kbps (128k recommended)

**Subtitle Strategy**
- Choose how to handle subtitles:
  - External: Keep in separate file
  - Mux: Embed in MP4 (requires re-encoding playback for some players)
  - Omit: Ignore subtitles
  - Burn: Embed in video (causes Jellyfin re-encoding on playback)

### 4. Review Command Preview
- The command preview shows exactly what FFmpeg will execute
- Shows actual file paths (with placeholders like {INPUT}, {OUTPUT})
- Click "Copy" to copy the command to clipboard

### 5. Use Command in FFmpeg Tab
- Go to the "FFmpeg" tab
- If you have a custom command field, paste the copied command
- The FFmpeg tab will show a preview with actual file paths
- Queue your files and click Encode

## Placeholder Reference

When copying commands from FFmpeg Settings, you'll see these placeholders:

| Placeholder | Meaning | Example |
|-------------|---------|---------|
| `{INPUT}` | Input video file | `C:\video.mkv` |
| `{OUTPUT}` | Output video file | `C:\video_encoded.mp4` |
| `{AUDIO_TRACK}` | Audio stream number | `2` (2nd audio track) |
| `{SUBTITLE_TRACK}` | Subtitle stream number | `0` (1st subtitle) |
| `{SUBTITLE_FILE}` | External subtitle file | `C:\subtitles.srt` |

These are **automatically replaced** when encoding, so don't manually change them.

## Common Scenarios

### Scenario 1: Anime with 720p Resolution + External SRT Subs
1. Select the anime file in Files tab
2. In FFmpeg Settings:
   - Quality Preset: **Balanced**
   - Video Codec: **HEVC GPU** (best quality)
   - Audio: Enable auto-copy if original is AAC
   - Subtitles: **External** (keeps .srt file separate)
3. Click Copy, paste into FFmpeg tab, encode

**Result**: 720p preserved (no upscaling), soft subtitles in MP4, efficient encoding

### Scenario 2: Movie with Multiple Audio Tracks
1. Select the movie file in Files tab
2. In FFmpeg Settings:
   - Quality Preset: **Quality** (high quality)
   - Video Codec: **HEVC GPU**
   - Audio Bitrate: 192k (for high quality)
   - Subtitles: Choose based on what's available
3. Copy and encode

**Note**: If the movie has PGS (bitmap) subtitles, choose "Omit" to avoid encoding overhead.

### Scenario 3: Optimized AppleTV Format
1. Select the video file in Files tab
2. Preset: Select "AppleTV 1080p30 Auto" - this loads optimized settings
3. Quality Preset: **Compact** (good balance for streaming)
4. Copy and encode

**Result**: Video optimized for AppleTV playback (H.264/AAC, proper settings)

### Scenario 4: Ultra-High Quality (for archival)
1. Select the source file in Files tab
2. In FFmpeg Settings:
   - Quality Preset: **Quality** (CRF 24, slowest encoding)
   - Video Codec: **HEVC GPU** (best compression ratio)
   - Audio: Enable auto-copy for lossless, or use high bitrate
   - Upscale: **Disabled** (only upscale if necessary)
3. Copy and encode

**Note**: Will produce largest files, takes longest to encode

## Subtitle Handling Tips

### For Jellyfin Compatibility (No Transcode)
**Best practice**: Soft subtitles (muxed into MP4)
1. Use embedded SRT/ASS subtitles or external SRT
2. Choose "Mux" or "External" strategy
3. Jellyfin plays without re-encoding

**Avoid**:
- Don't burn subtitles (forces Jellyfin to re-encode)
- Don't use PGS if you want to mux

### For Infuse (TV App)
**Best practice**: External ASS subtitles + soft subtitle backup
1. Keep ASS files external (preserves styling)
2. Optionally mux SRT for Jellyfin fallback
3. Use "External + Mux" if available

### For Subtitles Without Compatible Player
- Choose "Burn" to embed subtitles directly in video
- ⚠️ Warning: This forces re-encoding in Jellyfin
- Best used for standalone playback, not streaming servers

## Advanced Tips

### Getting the Best File Size
1. Choose **Compact** quality preset (CRF 32)
2. Use **HEVC GPU** codec (25-50% smaller than H.264)
3. Lower audio bitrate to 96k
4. Don't burn subtitles (requires re-encoding)

**Result**: Smallest file while maintaining watchable quality

### Getting the Best Quality
1. Choose **Quality** preset (CRF 24)
2. Use **HEVC GPU** codec
3. Use high audio bitrate (192k or higher)
4. Don't downscale - keep source resolution
5. Keep audio codec if it's already high quality

**Result**: Visually lossless quality (but slower encoding)

### Balanced Encoding (Recommended)
1. Use **Balanced** preset (CRF 28) - default
2. **HEVC GPU** codec
3. Audio bitrate: 128k
4. Keep source resolution (no upscaling)
5. Soft subtitles (mux or external)

**Result**: Good quality, reasonable file size, fast encoding

## Troubleshooting

### Problem: "Unable to detect" resolution/audio codec
**Solution**:
- Make sure FFmpeg is properly installed
- Check that ffprobe.exe is in the same directory as ffmpeg.exe
- Try selecting the file again

### Problem: Audio codec unknown / Fallback codec used
**Solution**:
- This is normal for uncommon audio formats
- The app will re-encode to AAC (MP4 compatible)
- To keep original audio, use MKV container instead

### Problem: Encoding fails with file path error
**Solution**:
- Make sure the file path doesn't have special characters
- Try moving the file to a simpler path (e.g., `C:\Videos\`)
- Check that the output folder has write permissions

### Problem: Video looks different after encoding
**Solution**:
- If using "Compact" preset: normal, quality intentionally lowered for size
- If using "Balanced": try "Quality" preset for higher quality
- Check that color range is set correctly (TV vs Full)
- Verify playback app is showing correct color settings

## Settings Reference

### Video Codec Comparison
| Codec | Speed | Quality | File Size | GPU Required |
|-------|-------|---------|-----------|--------------|
| h264_nvenc | Fast | Good | 100% | Yes |
| hevc_nvenc | Medium | Excellent | 60-70% | Yes |
| libx264 | Slow | Good | 100% | No |
| libx265 | Very Slow | Excellent | 60-70% | No |

### CRF Quality Scale (Lower = Better Quality)
- **20-23**: Visually lossless quality (experts recommended)
- **24-28**: High quality (balanced default)
- **28-32**: Good quality, noticeably smaller files
- **32+**: Acceptable quality, very small files

### Audio Bitrate Guide
- **96k**: Minimum acceptable, noticeable quality loss
- **128k**: Good compromise (default)
- **192k**: High quality
- **256k+**: Lossless quality

## Keyboard Shortcuts

None specific to FFmpeg Settings, but in FFmpeg tab:
- **Ctrl+C**: Copy command preview to clipboard
- **Enter**: Start encoding (if available)

## More Help

For detailed technical information, see:
- FFMPEG_SETTINGS_COMPLETE.md (technical implementation details)
- IMPLEMENTATION_STATUS.md (testing and verification results)
