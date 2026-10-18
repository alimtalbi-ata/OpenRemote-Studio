# Validate the real packaged GUI with an enforced deadline and isolated profile.
param(
  [string]$Exe = (Join-Path $PSScriptRoot '..\dist\OpenRemoteStudio\OpenRemoteStudio.exe'),
  [ValidateRange(5,120)][int]$TimeoutSeconds = 30
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Executable missing: $Exe" }
$smokeRoot = Join-Path $env:TEMP ('OpenRemoteStudio-smoke-' + [guid]::NewGuid().ToString('N'))
$oldAppData = $env:APPDATA
$oldLocalAppData = $env:LOCALAPPDATA
$process = $null
$passed = $false
try {
  $env:APPDATA = Join-Path $smokeRoot 'Roaming'
  $env:LOCALAPPDATA = Join-Path $smokeRoot 'Local'
  New-Item -ItemType Directory -Force -Path $env:APPDATA,$env:LOCALAPPDATA | Out-Null
  $process = Start-Process -FilePath (Resolve-Path -LiteralPath $Exe).Path -ArgumentList '--smoke-gui' -PassThru
  if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    $process.Kill()
    $process.WaitForExit()
    throw "Packaged GUI smoke timeout after $TimeoutSeconds seconds"
  }
  if ($process.ExitCode -ne 0) { throw "Packaged GUI smoke failed: $($process.ExitCode)" }
  $passed = $true
  Write-Host 'Windows packaged GUI startup smoke PASS (isolated profile, deadline enforced).'
} finally {
  if ($null -ne $process) {
    try { if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() } } catch { }
    $process.Dispose()
  }
  $env:APPDATA = $oldAppData
  $env:LOCALAPPDATA = $oldLocalAppData
  if ($passed) { Remove-Item -LiteralPath $smokeRoot -Recurse -Force -ErrorAction SilentlyContinue }
  else { Write-Warning "Startup diagnostics retained: $smokeRoot" }
}
