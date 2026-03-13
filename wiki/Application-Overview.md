# Application Overview

## What the application does

ffmpeg_encode is a desktop GUI that batch-encodes video files. You add a list of source files (by scanning a folder or adding files manually), choose encoding settings via a HandBrake preset or an FFmpeg command, and run encoding for all files. The app preserves folder structure in the output, can skip files that already have an encoded version, and shows progress and logs in real time.

## Two encoding paths

| Path | When to use it |
|------|-----------------|
| **HandBrake CLI** | You want to stick to a HandBrake preset exactly. The app passes the preset file and track numbers to HandBrakeCLI; HandBrake does the encoding. |
| **FFmpeg** | You want to edit the command (filters, codecs, etc.) or run a fully custom command. The app can generate an FFmpeg command from a HandBrake preset, then you edit it and encode with FFmpeg. |

Both paths use the same file list, output folder logic, track detection, and options (dry run, skip existing, suffix, sequential/parallel).

## HandBrake presets as source of truth

HandBrake JSON presets define video/audio/subtitle settings. The app uses them in two ways:

1. **HandBrake tab**: The preset file is passed directly to HandBrake CLI with `--preset-import-file` and `--preset`.
2. **FFmpeg tab**: The preset is **translated** into an FFmpeg command by the built-in `FFmpegTranslator` (resolution, CRF, codecs, audio bitrate, subtitle burning, etc.). You can then edit that command before encoding.

So the preset is the starting point; for FFmpeg you get an editable command derived from it.

## Placeholder system

FFmpeg commands can use placeholders that are replaced **at encode time** for each file:

| Placeholder | Replaced with |
|-------------|----------------|
| `{INPUT}` | Absolute path to the source file |
| `{OUTPUT}` | Absolute path to the output file |
| `{AUDIO_TRACK}` | Detected English audio track number |
| `{SUBTITLE_TRACK}` | Detected subtitle track number |
| `{SUBTITLE_FILE}` | Path to extracted subtitle file (when used for burning); if no subtitle file exists, the subtitle filter is removed from the filter chain |

The literals `input.mkv` and `output.mp4` in the command are also replaced with the real paths. Angle-bracket variants (e.g. `<INPUT>`) are supported the same way.

## Track detection

MKV files (and similar) often have multiple audio and subtitle tracks. The app **automatically** picks:

- An **English audio** track (by language tag and/or name patterns, with optional exclude patterns).
- A **Signs/Songs-style subtitle** track (by language and name patterns).

Detection is configurable in Settings (language tags, name patterns, exclude patterns for both audio and subtitles). The **Debug** tab lets you open a single file and see the raw mkvinfo output plus the track analysis so you can see why a track was or wasn’t selected. See [Track Detection](Track-Detection) for details.

## Config persistence

The app saves settings automatically. Stored data includes:

- Executable paths (FFmpeg, HandBrake CLI, mkvinfo)
- Default output suffix, encoding mode (sequential/parallel), skip existing default
- Track detection patterns (audio and subtitle language tags, name patterns, exclude patterns)
- Saved HandBrake presets (copied into the config presets folder) and last-used preset name
- Saved FFmpeg commands (by name)
- Last scan folder, output folder preference

**Where it lives:**

| Platform | Config directory |
|----------|------------------|
| Windows | `%LOCALAPPDATA%\VideoEncoder` |
| macOS / Linux | `~/.video_encoder` |

Config file: `config.json`. Presets are stored under a `presets` subdirectory.

## Data flow

```
Scan Folder → File List → Track Analysis → Preset/Command → Encoder → Output Folder
```

1. **Scan Folder**: User selects a folder; the app recursively finds video files (MKV, MP4, MOV, etc.) and fills the file list.
2. **File List**: Shows source path, size, track counts (after analysis), and status. User can add/remove files and set the output folder (or “same folder as input”).
3. **Track Analysis**: For each file (at encode time, or on demand in the Debug tab), mkvinfo is used to get track info; the configurable patterns pick the English audio track and the Signs/Songs subtitle track.
4. **Preset/Command**: HandBrake tab uses the selected preset file; FFmpeg tab uses the command derived from the preset (and possibly edited), with placeholders filled per file.
5. **Encoder**: HandBrake CLI or FFmpeg is invoked as a subprocess; progress is parsed and shown in the UI.
6. **Output Folder**: Encoded files are written to the chosen output location, preserving the relative folder structure of the scan.
