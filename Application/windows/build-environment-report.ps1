# Read-only build host inventory. No credentials, remote connections or user profile paths in output.
$ErrorActionPreference = 'Stop'
$report = [ordered]@{
  product = 'OpenRemote Studio'
  version = '18.6'
  windows = ($env:OS -eq 'Windows_NT')
  x64 = [Environment]::Is64BitOperatingSystem
  powershell_major = $PSVersionTable.PSVersion.Major
  winget_available = [bool](Get-Command winget -ErrorAction SilentlyContinue)
  python_launcher_available = [bool](Get-Command py -ErrorAction SilentlyContinue)
  inno_compiler_available = [bool](@("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1)
}
$report | ConvertTo-Json -Depth 3
