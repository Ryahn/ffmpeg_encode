$ErrorActionPreference = 'Stop'
$toolsDir = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"

$version = $env:chocolateyPackageVersion
$versionTag = if ($version -match '^v') { $version } else { "v$version" }
$url = "https://github.com/Ryahn/ffmpeg_encode/releases/download/$versionTag/ffmpeg_encode-Setup.exe"

# Update checksum when publishing a new release (after building installer and uploading to GitHub releases)
$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url           = $url
  url64bit      = $url
  softwareName  = 'ffmpeg_encode*'
  checksum      = 'DC4EC82A1C0F1B9BEC55464DFD130FA23348E8F4A36C5F28CBC95FCA48F9EA4F'
  checksumType  = 'sha256'
  checksum64    = 'DC4EC82A1C0F1B9BEC55464DFD130FA23348E8F4A36C5F28CBC95FCA48F9EA4F'
  checksumType64= 'sha256'
  silentArgs    = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
  validExitCodes= @(0, 3010, 1641)
}

Install-ChocolateyPackage @packageArgs
