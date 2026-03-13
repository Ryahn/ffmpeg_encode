# Installation

## Option A: Pre-built executables (recommended for most users)

Pre-built binaries are produced by GitHub Actions and published on the [Releases](https://github.com/Ryahn/ffmpeg_encode/releases) page. You can also download artifacts from the [Actions](https://github.com/Ryahn/ffmpeg_encode/actions) tab after a workflow run.

### Windows

- **Portable**: Download `ffmpeg_encode-portable.zip`, extract it, and run the executable inside the extracted folder.
- **Installer**: Download `ffmpeg_encode-Setup.exe` and run it to install the application (Start Menu shortcut, optional desktop icon, uninstaller).

### macOS

- **Disk image**: Download `ffmpeg_encode.dmg`, open it, and drag the app to Applications (or run from the DMG).
- **ZIP**: Download `ffmpeg_encode.zip`, unzip it, and run the `ffmpeg_encode.app` bundle.

### Linux

Pre-built executables are not provided for Linux. Use [Option B: Run from source](#option-b-run-from-source) and install FFmpeg, HandBrake CLI, and MKVToolNix with your package manager (e.g. `apt install ffmpeg handbrake-cli mkvtoolnix`). The app will find them if they are on PATH, or you can set paths in Settings.

### Antivirus false positives

Some security software may flag the Windows executable or installer. This is a known heuristic issue with PyInstaller and installers; the app does not use process injection or malicious behavior. See [Security & Antivirus](Security-and-Antivirus) for details and what to do (e.g. build from source or report a false positive to your AV vendor).

---

## Option B: Run from source

### Prerequisites

- **Python 3.8 or higher**
- FFmpeg, HandBrake CLI, and MKVToolNix (mkvinfo) installed and on PATH, or install them and configure their paths in the app’s Settings. See [Dependencies](Dependencies).

### Steps

```bash
git clone https://github.com/Ryahn/ffmpeg_encode.git
cd ffmpeg_encode
pip install -r requirements.txt
python src/main.py
```

On Linux, install the external tools with your package manager (e.g. `apt install ffmpeg handbrake-cli mkvtoolnix`) and use **Auto-detect** in Settings if they are on PATH.

---

## First launch

On first run, the application checks for FFmpeg, HandBrake CLI, and mkvinfo. If they are found (on PATH or in common installation locations), their paths are saved to config automatically. If any are missing, the app logs a warning and you need to:

1. **Install the missing tools** (see [Dependencies](Dependencies) for Chocolatey/Homebrew/package manager commands).
2. Open the **Settings** tab and either click **Auto-detect** to find them or use **Browse** to set each executable path manually.

The app can offer to auto-install dependencies via Chocolatey (Windows) or Homebrew (macOS) when supported; if that flow is not available, install the tools yourself and then configure paths in Settings.
