# Security and antivirus false positives

## About this project

ffmpeg_encode is an open-source GUI for encoding video with FFmpeg and HandBrake. The source code is available in this repository. The Windows build is produced with PyInstaller and packaged with Inno Setup.

## Why security software may flag the installer or executable

- **Process creation**: The app launches FFmpeg and HandBrake as child processes and reads their output. This is normal encoder behavior, not malware.
- **“Writes to remote process”**: PyInstaller’s bootloader unpacks the bundled app at runtime. Some sandboxes report this as writing to a process. The app does not use process injection APIs (e.g. `WriteProcessMemory`).
- **Archive / installer behavior**: The Inno Setup installer compresses and extracts files (LZMA2). Installers are often heuristically flagged for “writes archive files” and similar.

We do not use UPX compression in the main executable to reduce false positives.

## What we do

- Builds are produced from this public repo (e.g. via GitHub Actions).
- We do not ship obfuscated or packed code beyond PyInstaller’s normal bundling.
- We recommend code signing for Windows releases when possible to improve trust with AV vendors.

## If you’re a user

If your antivirus flags `ffmpeg_encode.exe` or the installer:

1. You can build from source (see README) and run the Python app without the packaged executable.
2. Report the file as a false positive to your antivirus vendor (e.g. via their “submit sample” or “report false positive” option). The Hybrid Analysis report you received is from a sandbox; the same sample can be submitted to your AV vendor for re-analysis.

## If you’re a security researcher or vendor

- Source: this repository.
- Build process: PyInstaller (`build.spec`) and Inno Setup (`build_installer.iss`).
- No process injection, no shellcode, no use of `WriteProcessMemory` / `VirtualAllocEx`; only standard `subprocess` usage to run FFmpeg/HandBrake and read stdout/stderr.

For a formal security issue (vulnerability in the code), please open a GitHub Security Advisory or contact the maintainers privately.
