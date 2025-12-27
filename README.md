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

## Requirements

- Python 3.8 or higher
- FFmpeg (auto-installed via Chocolatey/Homebrew)
- HandBrake CLI (auto-installed via Chocolatey/Homebrew)
- MKVToolNix (auto-installed via Chocolatey/Homebrew)

## Installation

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

The application will automatically detect and offer to install missing dependencies (FFmpeg, HandBrake, mkvtoolnix) via:
- **Windows**: Chocolatey
- **macOS**: Homebrew

## Usage

1. **Files Tab**: Select a folder to scan for video files (MKV, MP4, MOV, etc.)
2. **HandBrake Tab**: Load a HandBrake preset JSON file and configure encoding options
3. **FFmpeg Tab**: View the translated FFmpeg command and encode with FFmpeg
4. **Settings Tab**: Configure paths for FFmpeg, HandBrake, and mkvinfo

## License

MIT License

