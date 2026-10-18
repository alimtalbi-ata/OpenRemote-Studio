# Optional, destructive ONLY inside a newly created temporary install directory.
# Qualifies install -> installed GUI smoke -> uninstall. Does not touch user profiles.
param(
  [string]$SetupExe = '',
  [ValidateRange(30,600)][int]$TimeoutSeconds = 180
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$releaseVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\..\VERSION.txt') -Raw).Trim()
if (-not $SetupExe) { $SetupExe = Join-Path $PSScriptRoot ('..\release\OpenRemoteStudio-V' + $releaseVersion + '-Windows-Setup.exe') }
if ($env:OS -ne 'Windows_NT') { throw 'Windows only' }
if (-not (Test-Path -LiteralPath $SetupExe -PathType Leaf)) { throw "Installer missing: $SetupExe" }
$SetupExe = (Resolve-Path -LiteralPath $SetupExe).Path
if ((Get-Item -LiteralPath $SetupExe).Length -lt 512) { throw 'Installer is empty or truncated' }
$root = Join-Path $env:TEMP ('OpenRemoteStudio-install-smoke-' + [guid]::NewGuid().ToString('N'))
$install = Join-Path $root 'Application'
$roaming = Join-Path $root 'Roaming'
$local = Join-Path $root 'Local'
$log = Join-Path $root 'install.log'
$oldAppData = $env:APPDATA
$oldLocalAppData = $env:LOCALAPPDATA
New-Item -ItemType Directory -Force -Path $root,$roaming,$local | Out-Null
$installed = $false
# Native installers must not run indefinitely in CI or leave orphan processes.
function Invoke-BoundedInstaller([string]$FilePath, [string[]]$Arguments, [string]$Phase) {
  $proc = Start-Process -FilePath $FilePath -ArgumentList $Arguments -PassThru -Wait:$false
  try {
    if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
      try { $proc.Kill(); $proc.WaitForExit() } catch { }
      throw "$Phase timed out after $TimeoutSeconds seconds"
    }
    if ($proc.ExitCode -ne 0) { throw "$Phase failed ($($proc.ExitCode)); log: $log" }
  } finally { $proc.Dispose() }
}
try {
  $env:APPDATA = $roaming
  $env:LOCALAPPDATA = $local
  Invoke-BoundedInstaller -FilePath $SetupExe -Arguments @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS',"/DIR=$install","/LOG=$log") -Phase 'Install' 
  $installed = $true
  $exe = Join-Path $install 'OpenRemoteStudio.exe'
  if (-not (Test-Path $exe)) { throw 'Installed executable missing' }
  & (Join-Path $PSScriptRoot 'smoke-windows.ps1') -Exe $exe -TimeoutSeconds 30
  if (-not $?) { throw 'Installed GUI smoke failed' }
  $uninstaller = Join-Path $install 'unins000.exe'
  if (-not (Test-Path $uninstaller)) { throw 'Uninstaller missing' }
  Invoke-BoundedInstaller -FilePath $uninstaller -Arguments @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Phase 'Uninstall' 
  $installed = $false
  if (Test-Path $exe) { throw 'Executable still present after uninstall' }
  Write-Host 'Windows install / GUI smoke / uninstall PASS'
} finally {
  $env:APPDATA = $oldAppData
  $env:LOCALAPPDATA = $oldLocalAppData
  if ($installed) { Write-Warning "Installation may remain at $install; inspect manually" }
  else { Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue }
}
