# Offline smoke of the packaged WinRM Python dependency graph; no network calls.
param([Parameter(Mandatory=$true)][string]$Exe, [ValidateRange(5,60)][int]$TimeoutSeconds = 30)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw 'WinRM runtime smoke: executable missing' }
$process = $null
try {
  $process = Start-Process -FilePath (Resolve-Path -LiteralPath $Exe).Path -ArgumentList '--check-winrm-runtime' -PassThru
  if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    $process.Kill()
    $process.WaitForExit()
    throw 'WinRM runtime smoke timed out'
  }
  if ($process.ExitCode -ne 0) { throw "WinRM runtime dependency smoke failed (exit $($process.ExitCode))" }
  Write-Host 'Packaged WinRM runtime dependencies PASS (offline; no Windows Server tested).'
} finally {
  if ($null -ne $process) {
    try { if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() } } catch { }
    $process.Dispose()
  }
}
