$ErrorActionPreference = 'Stop'
$toolsDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"

$version = $env:chocolateyPackageVersion
$versionTag = if ($version -match '^v') { $version } else { "v$version" }
$url = "https://github.com/Ryahn/ffmpeg_encode/releases/download/$versionTag/ffmpeg_encode-Setup.exe"

# Update checksum when publishing a new release: build the installer, upload ffmpeg_encode-Setup.exe to GitHub release, then run: Get-FileHash -Algorithm SHA256 .\ffmpeg_encode-Setup.exe
$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url           = $url
  url64bit      = $url
  softwareName  = 'ffmpeg_encode*'
  checksum      = 'F3647EA60FB11792ACF986CFFD81E24702DFEF5735B8EAA560F8CC663389EFC8'
  checksumType  = 'sha256'
  checksum64    = 'F3647EA60FB11792ACF986CFFD81E24702DFEF5735B8EAA560F8CC663389EFC8'
  checksumType64= 'sha256'
  silentArgs    = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs
