# Validate the real packaged GUI with an enforced deadline and isolated profile.
param(
  [string]$Exe = (Join-Path $PSScriptRoot '..\dist\OpenRemoteStudio\OpenRemoteStudio.exe'),
  [ValidateRange(5,120)][int]$TimeoutSeconds = 60
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Executable missing: $Exe" }
$smokeRoot = Join-Path $env:TEMP ('OpenRemoteStudio-smoke-' + [guid]::NewGuid().ToString('N'))
$oldAppData = $env:APPDATA
$oldLocalAppData = $env:LOCALAPPDATA
$process = $null
$passed = $false
$failureCode = 'launch_failure'
try {
  $env:APPDATA = Join-Path $smokeRoot 'Roaming'
  $env:LOCALAPPDATA = Join-Path $smokeRoot 'Local'
  New-Item -ItemType Directory -Force -Path $env:APPDATA,$env:LOCALAPPDATA | Out-Null
  $process = Start-Process -FilePath (Resolve-Path -LiteralPath $Exe).Path -ArgumentList '--smoke-gui' -PassThru
  if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    $failureCode = 'timeout'
    $process.Kill()
    $process.WaitForExit()
    throw "Packaged GUI smoke timeout after $TimeoutSeconds seconds"
  }
  if ($process.ExitCode -ne 0) { $failureCode = 'nonzero_exit'; throw "Packaged GUI smoke failed: $($process.ExitCode)" }
  $passed = $true
  Write-Host 'Windows packaged GUI startup smoke PASS (isolated profile, deadline enforced).'
} finally {
  if ($null -ne $process) {
    try { if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() } } catch { }
    $process.Dispose()
  }
  if ($passed) {
    $env:APPDATA = $oldAppData
    $env:LOCALAPPDATA = $oldLocalAppData
    Remove-Item -LiteralPath $smokeRoot -Recurse -Force -ErrorAction SilentlyContinue
  } else {
    # Export only the application's already-redacted stage/status journal.
    # Keep evidence under Binary/Qualification so the failure artifact uploads it.
    try {
      $diagnosticSource = Join-Path $env:LOCALAPPDATA 'OpenRemoteStudio\diagnostics\startup.jsonl'
      $evidenceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\Binary\Qualification\Packaged-GUI-Smoke'))
      New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
      $copied = $false
      if (Test-Path -LiteralPath $diagnosticSource -PathType Leaf) {
        Copy-Item -LiteralPath $diagnosticSource -Destination (Join-Path $evidenceRoot 'startup.jsonl') -Force
        $copied = $true
      }
      $evidence = [ordered]@{
        schema = 'openremote.packaged-gui-smoke.v1'
        generated_utc = (Get-Date).ToUniversalTime().ToString('o')
        timeout_seconds = $TimeoutSeconds
        failure_code = $failureCode
        redacted_startup_journal_copied = $copied
      }
      $evidence | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'smoke-result.json') -Encoding UTF8
      Write-Warning "Sanitized startup evidence exported to Binary/Qualification/Packaged-GUI-Smoke (journal=$copied)."
    } catch {
      # Do not mask the original smoke failure or emit path/exception details.
      Write-Warning 'Sanitized startup evidence could not be exported.'
    } finally {
      $env:APPDATA = $oldAppData
      $env:LOCALAPPDATA = $oldLocalAppData
    }
  }
}
