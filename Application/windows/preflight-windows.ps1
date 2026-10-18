# Read-only preflight for Windows x64 build host.
param([switch]$SkipInstaller)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$problems = @()
if ($env:OS -ne 'Windows_NT') { $problems += 'Windows is required' }
if (-not [Environment]::Is64BitOperatingSystem) { $problems += '64-bit Windows required' }
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $problems += 'Python launcher py.exe missing (Python 3.11+)' }
else {
  & py -3 -c 'import sys; assert sys.version_info >= (3,11); assert sys.maxsize > 2**32'
  if ($LASTEXITCODE -ne 0) { $problems += 'Python 3.11+ 64-bit not available' }
}
if (-not $SkipInstaller) {
  $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
  if (-not $iscc) { $problems += 'Inno Setup 6 not found (or use -SkipInstaller)' }
}
if ($problems.Count) {
  $problems | ForEach-Object { Write-Error $_ -ErrorAction Continue }
  exit 1
}
Write-Host 'Windows x64 build preflight PASS'
exit 0
