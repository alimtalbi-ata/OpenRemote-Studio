# Read-only build host inventory. No credentials, remote connections or user profile paths in output.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$versionPath = Join-Path $repoRoot 'VERSION.txt'
if (-not (Test-Path -LiteralPath $versionPath -PathType Leaf)) {
  [Console]::Error.WriteLine('VERSION.txt missing; build environment report refused.')
  exit 2
}
try {
  $productVersion = (Get-Content -LiteralPath $versionPath -Raw -ErrorAction Stop).Trim()
} catch {
  [Console]::Error.WriteLine('VERSION.txt unreadable; build environment report refused.')
  exit 2
}
if ($productVersion -notmatch '^\d+\.\d+$') {
  [Console]::Error.WriteLine('VERSION.txt invalid; expected canonical major.minor.')
  exit 2
}
$report = [ordered]@{
  product = 'OpenRemote Studio'
  version = $productVersion
  windows = ($env:OS -eq 'Windows_NT')
  x64 = [Environment]::Is64BitOperatingSystem
  powershell_major = $PSVersionTable.PSVersion.Major
  winget_available = [bool](Get-Command winget -ErrorAction SilentlyContinue)
  python_launcher_available = [bool](Get-Command py -ErrorAction SilentlyContinue)
  inno_compiler_available = [bool](@("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1)
}
$report | ConvertTo-Json -Depth 3
