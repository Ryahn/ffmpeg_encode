[Setup]
AppName=ffmpeg_encode
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\ffmpeg_encode
DefaultGroupName=ffmpeg_encode
UninstallDisplayIcon={app}\ffmpeg_encode.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist_installer
OutputBaseFilename=ffmpeg_encode-Setup
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\ffmpeg_encode.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ffmpeg_encode"; Filename: "{app}\ffmpeg_encode.exe"
Name: "{group}\{cm:UninstallProgram,ffmpeg_encode}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\ffmpeg_encode"; Filename: "{app}\ffmpeg_encode.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ffmpeg_encode.exe"; Description: "{cm:LaunchProgram,ffmpeg_encode}"; Flags: nowait postinstall skipifsilent

