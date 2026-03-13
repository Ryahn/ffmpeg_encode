# Home

**ffmpeg_encode** is a cross-platform GUI for batch-encoding video files using HandBrake or FFmpeg. It solves the problem of applying the same encoding settings to many files (e.g. an entire season or library) while automatically choosing the right audio and subtitle tracks. You load a HandBrake preset (or edit the resulting FFmpeg command), scan a folder, and encode with one click—with optional dry run, skip existing, and sequential or parallel encoding.

## Who is it for?

- Users who want to **batch-encode anime**, MKV collections, or video libraries
- Anyone who prefers **HandBrake presets** as a starting point but also wants to tweak or run **custom FFmpeg commands**
- People who need **automatic track selection** (e.g. English audio and Signs/Songs subtitles) without picking tracks manually for each file

## Table of contents

- [Application Overview](Application-Overview)
- [Installation](Installation)
- [Dependencies](Dependencies)
- [Usage Guide](Usage-Guide)
- [Preset Management](Preset-Management)
- [FFmpeg Command Management](FFmpeg-Command-Management)
- [Track Detection](Track-Detection)
- [Building from Source](Building-from-Source)
- [Security & Antivirus](Security-and-Antivirus)
- [Troubleshooting](Troubleshooting)

## Quick start

1. **Install dependencies**  
   Either use a [pre-built executable](Installation#option-a-pre-built-executables) (Windows or macOS) or run from source: install Python 3.8+, then `pip install -r requirements.txt` and install FFmpeg, HandBrake CLI, and MKVToolNix (see [Dependencies](Dependencies)).

2. **Load a preset**  
   In the **HandBrake** or **FFmpeg** tab, click **Load Preset** and select a HandBrake `.json` preset file. The app saves it and can auto-load the last-used preset on startup.

3. **Scan folder and set output**  
   In the **Files** tab, choose a scan folder and click **Scan**, then set where encoded files should go (same folder as input or a custom output folder).

4. **Encode**  
   In the **HandBrake** or **FFmpeg** tab, click **Start Encoding**. Use **Dry Run** first if you want to test without writing files, and **Skip Existing** to avoid re-encoding files that already have output.
