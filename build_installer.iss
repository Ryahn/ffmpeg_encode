[Setup]
AppName=ffmpeg_encode
; Setup (installer) version. CI passes /DMyAppVersion when building from a tag.
#ifndef MyAppVersion
  #define MyAppVersion "1.8.3"
#endif
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\ffmpeg_encode
DefaultGroupName=ffmpeg_encode
UninstallDisplayIcon={app}\ffmpeg_encode.exe
SetupIconFile=src\gui\icon.ico
Compression=lzma2
SolidCompression=yes
OutputDir=dist_installer
; CI passes /DMyAppVersion from the git tag (e.g. 1.8.1) so the file is ffmpeg_encode-Setup-1.8.1.exe
OutputBaseFilename=ffmpeg_encode-Setup-{#MyAppVersion}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ffmpeg_encode\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ffmpeg_encode"; Filename: "{app}\ffmpeg_encode.exe"
Name: "{group}\{cm:UninstallProgram,ffmpeg_encode}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ffmpeg_encode"; Filename: "{app}\ffmpeg_encode.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ffmpeg_encode.exe"; Description: "{cm:LaunchProgram,ffmpeg_encode}"; Flags: nowait postinstall skipifsilent

