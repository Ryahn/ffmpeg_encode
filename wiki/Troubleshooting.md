# Troubleshooting

---

## Dependencies not found

If FFmpeg, HandBrake CLI, or mkvinfo are not found at launch or when encoding:

1. **Auto-detect**: In the **Settings** tab, use the **Auto-detect** button next to each executable (FFmpeg, HandBrake CLI, mkvinfo). The app will search PATH and common installation paths and fill in the paths when found.
2. **Manual paths**: Use **Browse** next to each tool to select the executable (e.g. `ffmpeg.exe`, `HandBrakeCLI.exe`, `mkvinfo.exe` on Windows; `ffmpeg`, `HandBrakeCLI`, `mkvinfo` on macOS/Linux).
3. **Install missing tools**:
   - **Windows (Chocolatey)**: `choco install ffmpeg handbrake-cli mkvtoolnix`
   - **macOS (Homebrew)**: `brew install ffmpeg handbrake mkvtoolnix`
   - **Linux**: Use your package manager (e.g. Debian/Ubuntu: `apt install ffmpeg handbrake-cli mkvtoolnix`; Fedora: `dnf install ffmpeg HandBrake-cli mkvtoolnix`; Arch: `pacman -S ffmpeg handbrake-cli mkvtoolnix`). Then run **Auto-detect** or **Browse** in Settings.

See [Dependencies](Dependencies) for more detail.

---

## Track detection issues

If the wrong audio or subtitle track is selected (or none):

1. **Use the Debug tab**: Open **Debug**, click **Browse** and select the problematic file, then **Analyze**. Check **mkvinfo Output** to see all tracks (language, name, type) and **Track Analysis** to see which track was chosen and why.
2. **Adjust patterns in Settings**: Under Track Detection, update **Audio Language Tags**, **Audio Name Patterns**, **Audio Exclude Patterns**, and the corresponding **Subtitle** pattern groups so they match your files. For example, if your tracks are named “ENG” instead of “English,” add `ENG` to the audio name patterns.
3. **Common MKV naming**: Many releases use “English,” “ENG,” “Signs & Songs,” “Signs and Songs,” or similar. Add regex patterns that match your naming (e.g. `Signs.*Songs`, `Signs$`). Use exclude patterns to avoid selecting commentary or non-English tracks.

See [Track Detection](Track-Detection) for the full behavior and pattern reference.

---

## Encoding errors

If encoding fails for one or all files:

1. **Check the encoding log**: In the HandBrake or FFmpeg tab, read the **Encoding Log** for the failing file. It usually shows the exact command and the encoder’s error message.
2. **Verify executable paths**: In **Settings**, confirm that the paths to FFmpeg, HandBrake CLI, and mkvinfo are correct and that those executables run from a terminal.
3. **Use Dry Run**: Enable **Dry Run** and run the batch. The log will show what would be executed without writing files. This helps catch command or path errors.
4. **Output directory permissions**: Ensure the output folder (or the “same folder as input”) is writable and not on a read-only or full disk.

---

## Antivirus blocking the app

If your antivirus quarantines or blocks the Windows executable or installer, see [Security & Antivirus](Security-and-Antivirus). Options include building and running from source or reporting the file as a false positive to your AV vendor.
