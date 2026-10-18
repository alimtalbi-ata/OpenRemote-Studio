# OpenRemote Studio V31.3 - native Windows release qualification.
# Author: Abdelhalim Talbi. Run on Windows 10/11 x64.
param([switch]$Build, [switch]$SkipInstaller, [switch]$SkipInstallSmoke, [switch]$SkipConcurrency)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'This qualification must run on Windows.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$version = (Get-Content -LiteralPath (Join-Path $root 'VERSION.txt') -Raw).Trim()
if ($version -ne '31.3') { throw "Expected V31.3, got $version" }
$logDir = Join-Path $root 'Binary\Qualification'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$report = Join-Path $logDir "V31.3-$stamp.txt"
$results = New-Object System.Collections.Generic.List[string]
$records = New-Object System.Collections.Generic.List[object]
$overallStart = Get-Date
function Step([string]$name, [scriptblock]$action) {
  $start = Get-Date
  try {
    & $action
    if (-not $?) { throw "$name returned failure" }
    $elapsed = [math]::Round(((Get-Date)-$start).TotalSeconds,1)
    $results.Add("PASS | $name | $elapsed s")
    $records.Add([pscustomobject]@{ name=$name; status='PASS'; seconds=$elapsed; error=$null })
  } catch {
    $results.Add("FAIL | $name | $($_.Exception.Message)")
    $records.Add([pscustomobject]@{ name=$name; status='FAIL'; seconds=[math]::Round(((Get-Date)-$start).TotalSeconds,1); error=$_.Exception.Message })
    throw
  }
}
try {
  if ($Build) {
    Step 'Build and artifact gates' {
      & (Join-Path $root '02-Compilation\BUILD-WINDOWS.cmd')
      if ($LASTEXITCODE -ne 0) { throw "Build failed with exit code $LASTEXITCODE" }
    }
  }
  $published = Join-Path $root "Binary\V$version"
  $portable = Join-Path $published "Portable\OpenRemoteStudio-V$version-Windows-Portable.zip"
  $setup = Join-Path $published "Installer\OpenRemoteStudio-V$version-Windows-Setup.exe"
  Step 'Published release exists' {
    if (-not (Test-Path -LiteralPath $published -PathType Container)) { throw "Missing $published; use -Build" }
    if (-not (Test-Path -LiteralPath $portable -PathType Leaf)) { throw "Missing $portable" }
    if (-not $SkipInstaller -and -not (Test-Path -LiteralPath $setup -PathType Leaf)) { throw "Missing $setup" }
  }
  Step 'Release manifest and binary validation' {
    & (Join-Path $root 'Application\windows\verify-release.ps1') -ReleaseDir $published -SkipInstaller:$SkipInstaller
    if (-not $?) { throw 'Release manifest validation failed' }
    $python = Join-Path $root 'Application\.venv-build\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Build Python environment missing' }
    $args = @((Join-Path $root 'Application\windows\verify-binary-artifacts.py'),'--portable',$portable)
    if (-not $SkipInstaller) { $args += @('--installer',$setup) }
    & $python @args
    if ($LASTEXITCODE -ne 0) { throw 'Binary validation failed' }
  }
  Step 'Extracted portable GUI startup' {
    $temp = Join-Path $env:TEMP ('ORS-qa-' + [guid]::NewGuid().ToString('N'))
    try {
      Expand-Archive -LiteralPath $portable -DestinationPath $temp -ErrorAction Stop
      $exes = @(Get-ChildItem -LiteralPath $temp -Filter OpenRemoteStudio.exe -Recurse -File)
      if ($exes.Count -ne 1) { throw 'Portable executable count is not 1' }
      & (Join-Path $root 'Application\windows\smoke-windows.ps1') -Exe $exes[0].FullName -TimeoutSeconds 30
      if (-not $?) { throw 'Portable startup failed' }
    } finally { Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue }
  }
  if (-not $SkipInstaller -and -not $SkipInstallSmoke) {
    Step 'Install, launch and uninstall' {
      & (Join-Path $root 'Application\windows\install-smoke-windows.ps1') -SetupExe $setup -TimeoutSeconds 180
      if (-not $?) { throw 'Install smoke failed' }
    }
  }
  if (-not $SkipConcurrency) {
    Step 'Build lock concurrency and recovery' {
      & (Join-Path $root '02-Compilation\TEST-CONCURRENCE-WINDOWS.ps1')
      if (-not $?) { throw 'Concurrency test failed' }
    }
  }
} catch {
  if (@($results | Where-Object { $_ -like 'FAIL*' }).Count -eq 0) {
    $results.Add("FAIL | Qualification | $($_.Exception.Message)")
    $records.Add([pscustomobject]@{ name='Qualification'; status='FAIL'; seconds=0; error=$_.Exception.Message })
  }
} finally {
  $results | Set-Content -LiteralPath $report -Encoding UTF8
  $jsonPath = [IO.Path]::ChangeExtension($report, '.json')
  $summary = [pscustomobject]@{
    version = $version
    generatedUtc = (Get-Date).ToUniversalTime().ToString('o')
    durationSeconds = [math]::Round(((Get-Date)-$overallStart).TotalSeconds,1)
    passed = @($records | Where-Object status -eq 'PASS').Count
    failed = @($results | Where-Object { $_ -like 'FAIL*' }).Count
    skipped = @(
      $(if (-not $Build) { 'Build' })
      $(if ($SkipInstaller) { 'Installer validation' })
      $(if ($SkipInstallSmoke) { 'Installation smoke' })
      $(if ($SkipConcurrency) { 'Concurrency' })
    ) | Where-Object { $_ }
    steps = @($records.ToArray())
    qualificationStatus = $(if (@($results | Where-Object { $_ -like 'FAIL*' }).Count -gt 0) { 'FAIL' } else { 'PASS' })
  }
  $summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
  Write-Host "Qualification JSON: $jsonPath"
  Write-Host "Qualification report: $report"
  $results | ForEach-Object { Write-Host $_ }
}
if (@($results | Where-Object { $_ -like 'FAIL*' }).Count -gt 0) { exit 1 }
if ($results.Count -eq 0) { exit 2 }
exit 0
