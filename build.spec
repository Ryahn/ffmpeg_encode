# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        # Application modules
        'gui',
        'gui.main_window',
        'gui.tabs',
        'gui.tabs.files_tab',
        'gui.tabs.ffmpeg_tab',
        'gui.tabs.handbrake_tab',
        'gui.tabs.settings_tab',
        'gui.tabs.debug_tab',
        'gui.widgets',
        'gui.widgets.file_list',
        'gui.widgets.log_viewer',
        'gui.widgets.progress_bar',
        'core',
        'core.encoder',
        'core.ffmpeg_translator',
        'core.file_scanner',
        'core.package_manager',
        'core.preset_parser',
        'core.track_analyzer',
        'utils',
        'utils.config',
        'utils.logger',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ffmpeg_encode',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

