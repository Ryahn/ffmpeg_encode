# Video Encoder GUI

A cross-platform Python GUI application for encoding video files using HandBrake or FFmpeg. Features automatic track detection, preset management, and real-time progress tracking.

## Features

- **Cross-platform**: Works on Windows and macOS
- **Dual encoder support**: Use HandBrake or FFmpeg
- **HandBrake preset support**: Load and use HandBrake JSON presets
- **Preset management**: Dropdown selection with auto-save and last-used preset auto-loading
- **Automatic FFmpeg translation**: Converts HandBrake presets to FFmpeg commands
- **FFmpeg command management**: Save, load, delete, and manage custom FFmpeg commands
- **Placeholder system**: Use `{INPUT}`, `{OUTPUT}`, `{AUDIO_TRACK}`, `{SUBTITLE_TRACK}`, `{SUBTITLE_FILE}` in FFmpeg commands
- **Smart track detection**: Automatically finds English audio and subtitle tracks with configurable patterns
- **Track detection configuration**: Customize language tags, name patterns, and exclude patterns for audio and subtitles
- **Real-time progress**: See encoding progress with ETA, speed, and duration parsing
- **Built-in log viewer**: Monitor encoding output in real-time
- **Folder structure preservation**: Maintains directory structure in output
- **Encoding modes**: Sequential or parallel encoding
- **Skip existing files**: Option to skip files that already have encoded versions
- **Dry run mode**: Test encoding without actually processing files
- **Auto-install dependencies**: Automatically installs FFmpeg, HandBrake, and mkvtoolnix via package managers
- **Auto-detect executables**: Automatically find FFmpeg, HandBrake, and mkvinfo paths
- **Settings auto-save**: Settings are automatically saved when changed
- **Debug tab**: Analyze individual files to see track information and mkvinfo output
- **Cross-platform config**: Platform-appropriate config directory handling (Windows: AppData\Local, macOS/Linux: ~/.video_encoder)

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
- **Windows**: Download `ffmpeg_encode-portable.exe` (portable) or `ffmpeg_encode-Setup.exe` (installer)
- **macOS**: Download `ffmpeg_encode.dmg` (disk image) or `ffmpeg_encode.zip` (app bundle)

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
- **Windows**: `dist/ffmpeg_encode.exe` (portable) or `dist_installer/ffmpeg_encode-Setup.exe` (installer created with Inno Setup)
- **macOS**: `dist/ffmpeg_encode` (executable) or `dist/ffmpeg_encode.dmg` (disk image)

**Windows Installer**: The build process automatically creates an installer using Inno Setup when building on Windows. The installer provides a standard Windows installation experience.

**macOS DMG**: The build process creates a `.dmg` disk image for easy distribution on macOS, along with a `.zip` file containing the `.app` bundle.

## Usage

For detailed step-by-step instructions with screenshots, see [USAGE.md](USAGE.md).

Quick overview:
1. **Files Tab**: Select a folder to scan for video files (MKV, MP4, MOV, etc.)
2. **HandBrake Tab**: Load a HandBrake preset JSON file and configure encoding options
3. **FFmpeg Tab**: View and edit the translated FFmpeg command, then encode with FFmpeg
4. **Settings Tab**: Configure paths for FFmpeg, HandBrake, and mkvinfo, and adjust track detection patterns
5. **Debug Tab**: Analyze individual files to see track information and mkvinfo output

## Preset Management

The application supports comprehensive preset management:

- **Preset Dropdown**: Quickly select from previously loaded HandBrake presets
- **Auto-save**: Presets are automatically saved to the config directory when loaded
- **Last Used Preset**: The application automatically loads your last used preset on startup
- **Preset Storage**: Presets are stored in platform-appropriate locations:
  - Windows: `%LOCALAPPDATA%\VideoEncoder\presets\`
  - macOS/Linux: `~/.video_encoder/presets/`

## FFmpeg Command Management

The FFmpeg tab provides powerful command management:

- **Edit Commands**: Edit the generated command from HandBrake presets or write custom commands from scratch
- **Save Commands**: Save commands with custom names for reuse (persists between sessions)
- **Load Commands**: Load previously saved commands from the dropdown
- **File Operations**: Load commands from files or save commands to files
- **Delete Commands**: Remove saved commands you no longer need
- **Reset**: Reset the command to the default generated from the current preset
- **Placeholders**: Use dynamic placeholders that are replaced during encoding:
  - `{INPUT}` - Input file path
  - `{OUTPUT}` - Output file path
  - `{AUDIO_TRACK}` - Selected audio track number
  - `{SUBTITLE_TRACK}` - Selected subtitle track number
  - `{SUBTITLE_FILE}` - Extracted subtitle file path (if applicable)
- **Note**: `input.mkv` and `output.mp4` shown in the command are example placeholders that will be replaced with actual file paths during encoding

## Track Detection

The application uses intelligent track detection with configurable patterns:

- **Language Tags**: Match tracks by language codes (e.g., `en`, `eng`)
- **Name Patterns**: Match tracks by name using regex patterns (e.g., `English`, `ENG`, `Signs.*Song`)
- **Exclude Patterns**: Exclude tracks matching specific patterns (e.g., `Japanese`, `日本語`)
- **Separate Configuration**: Different patterns for audio and subtitle tracks
- **Debug Tools**: Use the Debug tab to analyze why specific tracks are selected or excluded

## Troubleshooting

### Dependencies Not Found

If FFmpeg, HandBrake, or mkvinfo are not found:
1. Use the **Auto-detect** button in Settings to automatically find installed executables
2. Use the **Browse** button to manually select executable paths
3. Install missing dependencies:
   - **Windows**: Use Chocolatey (`choco install ffmpeg handbrake-cli mkvtoolnix`)
   - **macOS**: Use Homebrew (`brew install ffmpeg handbrake mkvtoolnix`)

### Track Detection Issues

If tracks are not being detected correctly:
1. Open the **Debug Tab** and analyze a problematic file
2. Check the **Track Analysis** view to see why tracks are or aren't being selected
3. Adjust **Track Detection Settings** in the Settings tab:
   - Add language tags if needed
   - Modify name patterns to match your file naming conventions
   - Add exclude patterns to filter out unwanted tracks

### Encoding Errors

If encoding fails:
1. Check the **Encoding Log** for detailed error messages
2. Verify that all executable paths are correct in Settings
3. Try **Dry Run** mode first to test the command without encoding
4. Ensure output directory has write permissions

## License

MIT License
