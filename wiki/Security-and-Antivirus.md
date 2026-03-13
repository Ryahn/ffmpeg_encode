# Security and Antivirus

This page explains why security software may flag ffmpeg_encode and what the application actually does. The project is open source; the build process and behavior can be verified from the repository.

---

## Why security software may flag the installer or executable

### Process creation

The app launches **FFmpeg** and **HandBrake** as child processes and reads their stdout/stderr. This is normal encoder behavior: the GUI runs the encoders via subprocess and parses progress output. It is not malware.

### “Writes to remote process” (application)

The Windows build is produced with **PyInstaller**. PyInstaller’s bootloader unpacks the bundled Python app at runtime. Some sandboxes report this as writing to a process. The application **does not** use process injection APIs (e.g. `WriteProcessMemory`). It only starts FFmpeg/HandBrake with standard subprocess calls.

### “Writes to remote process” (installer)

The **Inno Setup** installer extracts its payload to a temporary folder (e.g. `%TEMP%\is-XXXXX.tmp\`) and may write to that extracted process as part of the install flow. This is the installer communicating with its own extracted helper, not cross-process injection (e.g. not ATT&CK T1055 in a malicious sense).

### Archive / installer behavior

The Inno Setup installer uses compression (LZMA2) and extracts files. Installers are often heuristically flagged for “writes archive files” and similar. That is expected for any installer.

### No UPX

The main executable is **not** packed with UPX, to reduce the chance of false positives from packer heuristics.

---

## What the project does

- Builds are produced from the **public repository** (e.g. via GitHub Actions). You can review the source and the workflow.
- The app does **not** ship obfuscated or packed code beyond PyInstaller’s normal bundling.
- **Code signing** for Windows releases is recommended when possible to improve trust with AV vendors; the project may adopt it in the future.

---

## If you’re a user

If your antivirus flags `ffmpeg_encode.exe` or the installer:

1. **Build from source**: Clone the repo, install Python dependencies, and run `python src/main.py`. No packaged executable is involved. See [Installation](Installation#option-b-run-from-source) and [Building from Source](Building-from-Source).
2. **Report a false positive**: Use your antivirus vendor’s “submit sample” or “report false positive” option. If you have a report from a sandbox (e.g. Hybrid Analysis), you can submit the same sample to your AV vendor for re-analysis.

---

## If you’re a security researcher or vendor

- **Source**: This repository. All application code and build scripts are available for review.
- **Build process**: PyInstaller (`build.spec`) and Inno Setup (`build_installer.iss`). No custom packers or obfuscation.
- **Runtime behavior**: No process injection, no shellcode, no use of `WriteProcessMemory` / `VirtualAllocEx`. The app uses standard `subprocess` usage to run FFmpeg/HandBrake and read stdout/stderr.

For a **formal security issue** (e.g. a vulnerability in the code), please open a **GitHub Security Advisory** or contact the maintainers privately so it can be addressed before public disclosure.
