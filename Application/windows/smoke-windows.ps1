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
  # A zero exit code alone is insufficient: require evidence that the Qt
  # application actually initialized, showed its main window and ran its loop.
  $startupLog = Join-Path $env:LOCALAPPDATA 'OpenRemoteStudio\diagnostics\startup.jsonl'
  if (-not (Test-Path -LiteralPath $startupLog -PathType Leaf)) {
    throw "Packaged GUI startup evidence missing: $startupLog"
  }
  $events = @(Get-Content -LiteralPath $startupLog | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
  foreach ($stage in @('qt_init','main_window','event_loop')) {
    if (-not @($events | Where-Object { $_.stage -eq $stage -and $_.outcome -eq 'ok' }).Count) {
      throw "Packaged GUI did not confirm startup stage: $stage"
    }
  }
  if (@($events | Where-Object { $_.outcome -eq 'failed' }).Count -gt 0) {
    throw 'Packaged GUI recorded a failed startup stage'
  }
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
