# Preset Management

## What is a HandBrake JSON preset?

A HandBrake preset is a JSON file that stores encoding settings: video codec and quality (e.g. x264, CRF, preset, profile/level), resolution, audio codec and bitrate, subtitle handling, and other options. You can export a preset from the HandBrake GUI (Presets → Export) to get a `.json` file and then load it in ffmpeg_encode.

## How to get a preset

1. Open the HandBrake desktop application.
2. Configure your desired video, audio, and subtitle settings.
3. Use **Presets → Export** (or the equivalent in your HandBrake version) to save a `.json` file.
4. In ffmpeg_encode, use **Load Preset** in the HandBrake or FFmpeg tab and select that file.

## Where presets are stored

When you load a preset, the app copies it into a **presets** folder under the config directory:

| Platform | Presets folder |
|----------|----------------|
| Windows | `%LOCALAPPDATA%\VideoEncoder\presets\` |
| macOS / Linux | `~/.video_encoder/presets/` |

Each preset is saved with a filename derived from the preset name (e.g. `My Preset.json`). The mapping from preset name to file path is stored in config so the dropdown can list and load them by name.

## Preset dropdown and auto-load

- **Dropdown**: Lists all presets you have loaded (by name). Selecting one loads that preset from the saved file.
- **Auto-save**: When you load a new preset file, it is copied to the presets folder and added to the dropdown automatically.
- **Last-used preset**: The app saves the name of the preset you last used and, on startup, automatically loads that preset so you can resume with the same settings.

## How the preset becomes an FFmpeg command

In the **FFmpeg** tab, when you select a HandBrake preset (or load one), the app uses the **FFmpegTranslator** to convert the preset into an FFmpeg command. The translation includes:

- Video: codec (e.g. libx264), CRF, preset, profile/level, resolution, color range, pixel format
- Audio: codec (e.g. AAC), bitrate, mixdown (channels)
- Subtitles: burned-in subtitle filter using `{SUBTITLE_FILE}` (replaced at encode time with the extracted subtitle path, or the filter is removed if no subtitle)
- Chapters, metadata, faststart when applicable

The translation runs when you select or load a preset in the FFmpeg tab. The result is shown in the command text area.

## When to edit the FFmpeg command manually

After the preset is translated, you can edit the command to:

- Add or change filters (e.g. scaling, denoising)
- Change codec options or add extra FFmpeg flags
- Adjust the mapping or placeholder usage

Use **Reset** to discard your edits and restore the command generated from the current preset. Use **Save** to store your edited command under a name for reuse (see [FFmpeg Command Management](FFmpeg-Command-Management)).
