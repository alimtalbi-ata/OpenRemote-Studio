# Windows-only integration check: lock contention, release after exit, independent logs.
param([int]$HoldSeconds = 8)
$ErrorActionPreference = 'Stop'
if ($HoldSeconds -lt 4 -or $HoldSeconds -gt 60) { throw 'HoldSeconds must be 4..60' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script = Join-Path $root 'Application\windows\bootstrap-and-build.ps1'
$binary = Join-Path $root 'Binary'
New-Item -ItemType Directory -Force -Path $binary | Out-Null
$before = @(Get-ChildItem $binary -Filter 'build-*.log' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
$first = Start-Process powershell.exe -PassThru -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$script+'"'),'-LockProbeHoldSeconds',"$HoldSeconds")
try {
  $lock = Join-Path $binary '.windows-build.lock'
  $acquired = $false
  for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 100
    if ($first.HasExited) { throw 'First probe exited before acquiring lock' }
    if (Test-Path $lock) {
      try { $handle = [IO.File]::Open($lock,'Open','ReadWrite','None'); $handle.Dispose() }
      catch [IO.IOException] { $acquired = $true; break }
    }
  }
  if (-not $acquired) { throw 'First probe did not acquire lock' }
  $second = Start-Process powershell.exe -PassThru -Wait -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$script+'"'),'-LockProbeHoldSeconds','1')
  if ($second.ExitCode -eq 0) { throw 'Concurrent build unexpectedly acquired lock' }
  if (-not $first.WaitForExit(($HoldSeconds + 10) * 1000)) { throw 'First probe timeout' }
  if ($first.ExitCode -ne 0) { throw 'First probe failed' }
  $third = Start-Process powershell.exe -PassThru -Wait -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$script+'"'),'-LockProbeHoldSeconds','1')
  if ($third.ExitCode -ne 0) { throw 'Lock not released after successful exit' }
  $after = @(Get-ChildItem $binary -Filter 'build-*.log' | Select-Object -ExpandProperty FullName)
  $newLogs = @($after | Where-Object { $_ -notin $before })
  if ($newLogs.Count -lt 2) { throw 'Expected at least two independent build logs' }
  Write-Host 'PASS: contention rejected, lock released, independent logs recorded'
  # Crash-recovery scenario: forcibly terminate a lock owner and confirm OS lock release.
  $crashProbe = Start-Process powershell.exe -PassThru -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$script+'"'),'-LockProbeHoldSeconds','30')
  try {
    $crashAcquired = $false
    for ($i=0; $i -lt 100; $i++) {
      Start-Sleep -Milliseconds 100
      if ($crashProbe.HasExited) { throw 'Crash probe exited before acquiring lock' }
      if (Test-Path $lock) {
        try { $h = [IO.File]::Open($lock,'Open','ReadWrite','None'); $h.Dispose() }
        catch [IO.IOException] { $crashAcquired = $true; break }
      }
    }
    if (-not $crashAcquired) { throw 'Crash probe did not acquire lock' }
    Stop-Process -Id $crashProbe.Id -Force -ErrorAction Stop
    if (-not $crashProbe.WaitForExit(10000)) { throw 'Crash probe did not terminate' }
    $recovered = Start-Process powershell.exe -PassThru -Wait -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$script+'"'),'-LockProbeHoldSeconds','1')
    if ($recovered.ExitCode -ne 0) { throw 'Lock not released after forced process termination' }
    Write-Host 'PASS: forced termination releases OS lock and permits recovery'
  } finally {
    if (-not $crashProbe.HasExited) { Stop-Process -Id $crashProbe.Id -Force -ErrorAction SilentlyContinue }
  }
} finally {
  if (-not $first.HasExited) { Stop-Process -Id $first.Id -Force -ErrorAction SilentlyContinue }
}
