param([switch]$SkipInstaller,[switch]$SkipTests,[switch]$RunInstallSmoke,[switch]$NoAutoInstall,[switch]$SingleExe,[int]$LockProbeHoldSeconds = 0)
if ($LockProbeHoldSeconds -lt 0 -or $LockProbeHoldSeconds -gt 120) { throw 'LockProbeHoldSeconds must be 0..120' }
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logDir = Join-Path (Split-Path $root -Parent) 'Binary'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
# Atomic exclusive lock across Windows build processes, held for the entire build.
# FileShare.None prevents concurrent builds even across separate PowerShell sessions.
$lockPath = Join-Path $logDir '.windows-build.lock'
$buildLock = $null
try {
  $buildLock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
} catch [IO.IOException] {
  throw 'Another Windows build is already running (Binary/.windows-build.lock). Wait for completion.'
}
$log = Join-Path $logDir ('build-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.log')
$transcriptStarted = $false
try {
  Start-Transcript -Path $log -ErrorAction Stop | Out-Null
  $transcriptStarted = $true
} catch {
  $buildLock.Dispose()
  throw
}

try {
  if ($LockProbeHoldSeconds -gt 0) {
    Write-Host "LOCK_PROBE_ACQUIRED pid=$PID seconds=$LockProbeHoldSeconds"
    Start-Sleep -Seconds $LockProbeHoldSeconds
    Write-Host 'LOCK_PROBE_RELEASED'
  } else {
  & (Join-Path $PSScriptRoot 'build-environment-report.ps1')
  if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 required' }
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  function PythonReady {
    $p = Get-Command py -ErrorAction SilentlyContinue
    if (-not $p) { return $false }
    & py -3 -c 'import sys; assert sys.version_info >= (3,11) and sys.maxsize > 2**32' 2>$null
    return ($LASTEXITCODE -eq 0)
  }
  if (-not (PythonReady)) {
    if ($NoAutoInstall -or -not $winget) { throw 'Python 3.11+ x64 absent; install Python or enable winget' }
    Write-Host 'Installing build-only Python 3.12 via winget (user scope)'
    & winget install --id Python.Python.3.12 --exact --scope user --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) { throw 'Python install failed' }
    $env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:PATH"
  }
  $python = $null
  if (PythonReady) { $python = 'py' }
  else {
    $candidate = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    if (Test-Path $candidate) { $python = $candidate }
  }
  if (-not $python) { throw 'Python installed but not discoverable; restart terminal then rerun BUILD-WINDOWS.cmd' }
  # Release integrity gate: run after build-only Python discovery/bootstrap,
  # but before installing Inno Setup, creating a venv or compiling.
  $releaseRoot = (Resolve-Path (Join-Path $root '..')).Path
  $verifier = Join-Path $releaseRoot 'VERIFY-RELEASE.py'
  if (-not (Test-Path -LiteralPath $verifier -PathType Leaf)) { throw 'Release verifier missing' }
  if ($python -eq 'py') {
    & py -3 $verifier $releaseRoot
  } else {
    & $python $verifier $releaseRoot
  }
  if ($LASTEXITCODE -ne 0) { throw 'Release integrity verification failed; build blocked' }
  $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
  if (-not $SkipInstaller -and -not $iscc) {
    if ($NoAutoInstall -or -not $winget) { throw 'Inno Setup 6 missing; install it or use -SkipInstaller' }
    Write-Host 'Installing build-only Inno Setup via winget'
    & winget install --id JRSoftware.InnoSetup --exact --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup installation failed' }
    $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $iscc) { throw 'Inno Setup installed but ISCC.exe not found; restart terminal or repair installation' }
  }
  $venv = Join-Path $root '.venv-build'
  if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    if ($python -eq 'py') { & py -3 -m venv $venv } else { & $python -m venv $venv }
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
  }
  & (Join-Path $PSScriptRoot 'build-windows.ps1') -SkipInstaller:$SkipInstaller -SkipTests:$SkipTests -SkipPreflight -RunInstallSmoke:$RunInstallSmoke -SingleExe:$SingleExe
  if (-not $?) { throw 'Windows build script failed' }
  # build-windows.ps1 is a PowerShell script: failures are terminating errors,
  # not necessarily updates to LASTEXITCODE (which may be stale from a native tool).
  Write-Host "SUCCESS: release artifacts in $logDir"
  }
} catch {
  [Console]::Error.WriteLine("BUILD FAILED: $($_.Exception.Message)")
  $script:buildFailed = $true
} finally {
  try { if ($transcriptStarted) { Stop-Transcript | Out-Null } } finally { $buildLock.Dispose() }
}
if ($script:buildFailed) { exit 1 }
exit 0
