# Dependencies

## External tools (required at runtime)

These must be available when you run the app. The app uses them to encode video and to analyze MKV track structure.

| Tool | Purpose | Windows install | macOS install |
|------|----------|------------------|---------------|
| **FFmpeg** | Video encoding (FFmpeg tab), subtitle extraction | `choco install ffmpeg` | `brew install ffmpeg` |
| **HandBrake CLI** | Video encoding (HandBrake tab) | `choco install handbrake-cli` | `brew install handbrake` |
| **MKVToolNix** (mkvinfo) | MKV track analysis for automatic track detection | `choco install mkvtoolnix` | `brew install mkvtoolnix` |

- The app **auto-detects** these if they are on PATH or in common locations (e.g. `C:\Program Files\HandBrake`, `C:\Program Files\MKVToolNix`, `/usr/local/bin`, `/opt/homebrew/bin`). When found, their paths are saved to config.
- On **Windows** and **macOS**, the app can **auto-install** them via Chocolatey or Homebrew when those package managers are installed.
- You can always set or override paths manually in the **Settings** tab (Browse or Auto-detect per executable).

On **Linux**, install with your package manager (e.g. Debian/Ubuntu: `apt install ffmpeg handbrake-cli mkvtoolnix`; Fedora: `dnf install ffmpeg HandBrake-cli mkvtoolnix`; Arch: `pacman -S ffmpeg handbrake-cli mkvtoolnix`), then use Auto-detect or Browse in Settings.

---

## Python packages (source installs only)

When running from source (`python src/main.py`), install the Python dependencies with:

```bash
pip install -r requirements.txt
```

| Package | Version | Purpose |
|---------|----------|---------|
| **customtkinter** | ≥ 5.2.0 | Themed GUI widgets (modern look and feel) |
| **Pillow** | ≥ 10.0.0 | Image handling for icons and assets |

Pre-built executables already include these; you do not need to install them for the portable or installer builds.
