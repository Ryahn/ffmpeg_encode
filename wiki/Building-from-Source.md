# Building from Source

This page is for developers and advanced users who want to build the executables themselves.

---

## Automated build (GitHub Actions)

The repository’s GitHub Actions workflow (`.github/workflows/build.yml`) builds Windows and macOS artifacts when:

- A tag matching `v*` is pushed (e.g. `v1.0.0`), or
- The workflow is triggered manually (**Actions** → **Build Executables** → **Run workflow**).

### What gets built

- **Windows**: A portable ZIP (`ffmpeg_encode-portable.zip`) containing the app folder, and an installer (`ffmpeg_encode-Setup.exe`) created with Inno Setup. Both are uploaded as workflow artifacts.
- **macOS**: An app bundle, a `.dmg` disk image, and a `.zip` of the app. Uploaded as workflow artifacts.

When the run is triggered by a tag, a **Create Release** job runs and attaches these artifacts to a GitHub Release.

### Downloading artifacts

1. Open the repository’s **Actions** tab.
2. Select the **Build Executables** workflow and the run you want.
3. In the **Artifacts** section, download **ffmpeg_encode-Windows** and/or **ffmpeg_encode-macOS**.
4. Unzip the Windows artifact to get the portable folder and the Setup executable; use the macOS artifact for the app/DMG/ZIP.

---

## Manual build

### Prerequisites

- Python 3.8+ with dependencies: `pip install -r requirements.txt`
- **PyInstaller**: `pip install pyinstaller`
- **Windows installer only**: [Inno Setup](https://jrsoftware.org/isinfo.php) installed so the installer step can run (the GitHub workflow installs it via Chocolatey).

### Build command

From the repository root:

```bash
pyinstaller build.spec
```

### Output locations

| Platform | Output | Notes |
|----------|--------|--------|
| Windows | `dist/ffmpeg_encode/` | Folder containing the executable and dependencies (portable run). |
| Windows | `dist_installer/ffmpeg_encode-Setup.exe` | Created only if you run the Inno Setup step (see below). |
| macOS | `dist/ffmpeg_encode` | Executable and bundle contents. |
| macOS | `.dmg` / `.zip` | Built by the GitHub workflow; for local builds you can create them manually or use a script. |

### Windows installer (Inno Setup)

The installer is produced by Inno Setup using `build_installer.iss`. To create it locally:

1. Build the app with `pyinstaller build.spec` so that `dist/ffmpeg_encode/` exists.
2. Run Inno Setup (e.g. `ISCC.exe`) with the script:

   ```text
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DMyAppVersion=1.0.0 build_installer.iss
   ```

   Replace `1.0.0` with your version. Output goes to `dist_installer/ffmpeg_encode-Setup.exe`.

If Inno Setup is not installed, you can still use the portable build from `dist/ffmpeg_encode/`.

---

## Chocolatey package

The `chocolatey/` directory contains the packaging files for publishing ffmpeg_encode to the Chocolatey gallery (Windows). The package depends on Chocolatey packages for FFmpeg, HandBrake CLI, and MKVToolNix so that installing ffmpeg_encode can pull in those tools.

- **Nuspec**: `chocolatey/ffmpeg_encode/ffmpeg_encode.nuspec` defines the package id, version, description, and dependencies.
- **Scripts and assets**: Under `chocolatey/ffmpeg_encode/tools/` (install/uninstall scripts, etc.).

For details on how to create and maintain the Chocolatey package (scripts, shims, versioning), see [chocolatey/ffmpeg_encode/ReadMe.md](https://github.com/Ryahn/ffmpeg_encode/blob/main/chocolatey/ffmpeg_encode/ReadMe.md) in the repository.
