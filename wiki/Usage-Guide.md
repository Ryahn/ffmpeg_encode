# Usage Guide

This page is a condensed guide to all tabs. For step-by-step instructions with screenshots, see the main repository’s [USAGE.md](https://github.com/Ryahn/ffmpeg_encode/blob/main/USAGE.md).

---

## Files tab

The **Files** tab is where you build the list of videos to encode and set the output destination.

![Files tab](img/FIles.png)

- **Scan folder**: Enter or paste a folder path, or click **Browse** to pick a folder. Click **Scan** to recursively find video files (MKV, MP4, MOV, AVI, etc.) and add them to the list.
- **Output**: Choose **Same folder as input file** or **Output folder**. If you choose a custom output folder, the app preserves the relative folder structure from the scan folder.
- **File list**: Shows each file with **Source path** (filename/path), **Size** (MB), **Tracks** (audio/subtitle counts after analysis), and **Status** (Pending, Encoding, Complete, Error, Skipped).
- **Add Files**: Manually add one or more video files via a file dialog.
- **Remove Selected** / **Clear All**: Remove selected items or clear the entire list.

---

## HandBrake tab

Encode using HandBrake CLI with a JSON preset.

![HandBrake tab](img/Handbrake.png)

- **Preset**: Use the dropdown to pick a previously loaded preset, or **Load Preset** to load a new HandBrake `.json` file (it is saved automatically).
- **Dry Run**: When checked, the app simulates encoding without writing files—useful to verify settings and commands.
- **Skip Existing**: Skip files that already have an encoded output file in the output folder.
- **Output suffix**: Appended to the output filename (e.g. `_encoded` → `video_encoded.mp4`). Default comes from Settings.
- **Mode**: **Sequential** (one file at a time) or **Parallel** (multiple files at once; uses more CPU/RAM).
- **Start Encoding** / **Stop**: Start the batch or stop after the current file.
- **Progress**: Progress bar and status text (percentage, ETA, speed).
- **Encoding log**: Live output from HandBrake CLI, including track analysis and any errors.

---

## FFmpeg tab

Encode using FFmpeg with a command that can be generated from a preset and then edited.

![FFmpeg tab](img/Ffmpeg.png)

- **Preset**: Select a HandBrake preset from the dropdown; the app generates an FFmpeg command from it. You can also **Load Preset** to add a new one.
- **Command editor**: The large text area shows the current FFmpeg command. You can edit it (e.g. change codecs, add filters). The placeholders `input.mkv` and `output.mp4` (or `{INPUT}` / `{OUTPUT}`) are replaced with real paths at encode time.
- **Save / Load / Load from File / Save to File / Reset / Delete**: Save the current command under a name (persists between sessions), load from the dropdown or from a file, save to a file, reset to the preset-generated default, or delete a saved command. See [FFmpeg Command Management](FFmpeg-Command-Management).
- **Placeholder buttons**: Insert `{INPUT}`, `{OUTPUT}`, `{AUDIO_TRACK}`, `{SUBTITLE_TRACK}`, `{SUBTITLE_FILE}` into the command.
- **Detect Tracks**: Re-run track detection and refresh the command preview if needed.
- **Encode options**: Same as HandBrake tab—Dry Run, Skip Existing, Output suffix, Sequential/Parallel, Start/Stop, progress bar, and encoding log.

---

## Settings tab

Configure executable paths, defaults, and track detection.

![Settings tab](img/Settings.png)

- **Executable paths**: Set paths for **FFmpeg**, **HandBrake CLI**, and **mkvinfo**. Use **Browse** to pick the executable or **Auto-detect** to search common locations and PATH.
- **Default output suffix**: Default suffix for output filenames (used by HandBrake and FFmpeg tabs unless overridden).
- **Default encoding mode**: **Sequential** or **Parallel** as the default when you start encoding.
- **Skip existing encoded files by default**: When enabled, “Skip Existing” is checked by default in the encode tabs.
- **Track detection**: Six pattern groups—**Audio Language Tags**, **Audio Name Patterns**, **Audio Exclude Patterns**, **Subtitle Language Tags**, **Subtitle Name Patterns**, **Subtitle Exclude Patterns**. These control how the app picks the English audio track and the Signs/Songs-style subtitle track. See [Track Detection](Track-Detection).
- Settings are saved automatically when changed. Use **Save All Settings** to force a write if desired.

---

## Debug tab

Inspect a single file’s structure and track analysis to troubleshoot detection.

![Debug tab](img/Debug.png)

- **Browse**: Select a video file (MKV, MP4, etc.).
- **Analyze**: Run mkvinfo (for MKV) and the app’s track analysis on that file.
- **mkvinfo Output**: Raw mkvinfo output—tracks, language tags, names—to see exactly what’s in the file.
- **Track Analysis**: Which audio and subtitle tracks were selected and why, plus your current detection settings. Use this to adjust language tags, name patterns, or exclude patterns in Settings when the wrong track is chosen.

See [Troubleshooting](Troubleshooting#track-detection-issues) for common fixes.
