# Video Encoder GUI

A cross-platform Python GUI application for encoding video files using HandBrake or FFmpeg. Features automatic track detection, preset management, and real-time progress tracking.

## Features

- **Cross-platform**: Works on Windows and macOS
- **Dual encoder support**: Use HandBrake or FFmpeg
- **HandBrake preset support**: Load and use HandBrake JSON presets
- **Automatic FFmpeg translation**: Converts HandBrake presets to FFmpeg commands
- **Smart track detection**: Automatically finds English audio and subtitle tracks
- **Real-time progress**: See encoding progress with ETA and speed
- **Built-in log viewer**: Monitor encoding output in real-time
- **Folder structure preservation**: Maintains directory structure in output
- **Auto-install dependencies**: Automatically installs FFmpeg, HandBrake, and mkvtoolnix via package managers
- **Editable FFmpeg commands**: Customize and save FFmpeg commands for reuse

## Requirements

- Python 3.8 or higher
- FFmpeg (auto-installed via Chocolatey/Homebrew)
- HandBrake CLI (auto-installed via Chocolatey/Homebrew)
- MKVToolNix (auto-installed via Chocolatey/Homebrew)

## Installation

### Option 1: Run from Source

1. Clone this repository:
```bash
git clone <repository-url>
cd ffmpeg_encode
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python src/main.py
```

### Option 2: Use Pre-built Executables

Download the latest release from the [Releases](https://github.com/yourusername/ffmpeg_encode/releases) page:
- **Windows**: Download `VideoEncoder.exe`
- **macOS**: Download `VideoEncoder` or `VideoEncoder.dmg`

The application will automatically detect and offer to install missing dependencies (FFmpeg, HandBrake, mkvinfo) via:
- **Windows**: Chocolatey
- **macOS**: Homebrew

## Building Executables

### Automated Build (GitHub Actions)

The repository includes GitHub Actions workflows that automatically build executables for Windows and macOS when:
- A new tag is pushed (e.g., `v1.0.0`)
- The workflow is manually triggered

Download the built executables from the [Actions](https://github.com/yourusername/ffmpeg_encode/actions) page.

### Manual Build

To build executables locally:

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Build using the spec file:
```bash
pyinstaller build.spec
```

The executable will be in the `dist/` directory:
- **Windows**: `dist/VideoEncoder.exe`
- **macOS**: `dist/VideoEncoder`

## Usage

1. **Files Tab**: Select a folder to scan for video files (MKV, MP4, MOV, etc.)
2. **HandBrake Tab**: Load a HandBrake preset JSON file and configure encoding options
3. **FFmpeg Tab**: View and edit the translated FFmpeg command, then encode with FFmpeg
4. **Settings Tab**: Configure paths for FFmpeg, HandBrake, and mkvinfo, and adjust track detection patterns
5. **Debug Tab**: Analyze individual files to see track information and mkvinfo output

## FFmpeg Command Editing

The FFmpeg tab allows you to:
- Edit the generated command from HandBrake presets
- Write custom FFmpeg commands from scratch
- Use placeholders: `{INPUT}`, `{OUTPUT}`, `{AUDIO_TRACK}`, `{SUBTITLE_TRACK}`, `{SUBTITLE_FILE}`
- Save commands for reuse (persists between sessions)
- Load commands from files
- Note: `input.mkv` and `output.mp4` shown in the command are example placeholders that will be replaced with actual file paths during encoding

## License

MIT License
