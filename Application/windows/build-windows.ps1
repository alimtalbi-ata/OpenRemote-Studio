# Build on Windows 10/11 x64 using Python 3.11+ and optional Inno Setup 6.
param([switch]$SkipInstaller, [switch]$SkipTests, [switch]$SkipPreflight, [switch]$RunInstallSmoke, [switch]$SingleExe, [ValidateRange(30,600)][int]$InstallSmokeTimeoutSeconds = 180)
if ($RunInstallSmoke -and $SkipInstaller) { throw "RunInstallSmoke requires installer" }
# Installer and portable are published only after both builds and validation succeed.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$releaseVersion = (Get-Content -LiteralPath (Join-Path (Split-Path $root -Parent) 'VERSION.txt') -Raw).Trim()
if ($releaseVersion -notmatch '^[0-9]+\.[0-9]+$') { throw 'Invalid VERSION.txt' }
Set-Location $root
# Build into a private staging directory. Published artifacts remain untouched on failure.
$binaryRoot = Join-Path (Split-Path $root -Parent) 'Binary'
New-Item -ItemType Directory -Force -Path $binaryRoot | Out-Null
# Fail early rather than spending time compiling a version that cannot be published.
$published = Join-Path $binaryRoot ('V' + $releaseVersion)
if (Test-Path -LiteralPath $published) { throw "Release V$releaseVersion already published: $published" }
$release = Join-Path $binaryRoot ('.staging-V' + $releaseVersion + '-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $release | Out-Null
if (-not $SkipPreflight) {
  & (Join-Path $PSScriptRoot 'preflight-windows.ps1') -SkipInstaller:$SkipInstaller
  if (-not $?) { throw 'Windows preflight failed' }
}
$venv = Join-Path $root '.venv-build'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
  py -3 -m venv $venv
  if ($LASTEXITCODE -ne 0) { throw 'Python 3 absent ou venv impossible' }
}
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed' }
& $python -m pip install -r requirements.txt 'pyinstaller>=6.10,<7'
if ($LASTEXITCODE -ne 0) { throw 'dependency install failed' }
if (-not $SkipTests) {
  & $python -m unittest discover -s tests -q
  if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed' }
}
# Prevent stale dist artifacts from satisfying smoke tests after a partial build.
# Only delete PyInstaller's generated output, never user profiles or source files.
$distDir = Join-Path $root 'dist'
$workDir = Join-Path $root 'build'
foreach ($generated in @($distDir, $workDir)) {
  if (Test-Path -LiteralPath $generated) {
    Remove-Item -LiteralPath $generated -Recurse -Force -ErrorAction Stop
  }
}
$spec = if ($SingleExe) { 'OpenRemoteStudio-onefile.spec' } else { 'OpenRemoteStudio.spec' }
& $python -m PyInstaller --noconfirm --clean --distpath (Join-Path $root 'dist') --workpath (Join-Path $root 'build') (Join-Path $PSScriptRoot $spec)
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
$exe = if ($SingleExe) { Join-Path $root 'dist\OpenRemoteStudio.exe' } else { Join-Path $root 'dist\OpenRemoteStudio\OpenRemoteStudio.exe' }
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Missing Windows executable' }
# Validate the PE signature (MZ and PE\0\0) before the GUI smoke test.
$exeStream = [IO.File]::OpenRead($exe)
try {
  if ($exeStream.Length -lt 512) { throw 'Windows executable is too small' }
  $reader = New-Object IO.BinaryReader($exeStream)
  if ($reader.ReadUInt16() -ne 0x5A4D) { throw 'Windows executable lacks MZ header' }
  $exeStream.Position = 0x3C
  $peOffset = $reader.ReadInt32()
  if ($peOffset -lt 64 -or $peOffset -gt ($exeStream.Length - 4)) { throw 'Invalid Windows PE header offset' }
  $exeStream.Position = $peOffset
  if ($reader.ReadUInt32() -ne 0x00004550) { throw 'Windows executable lacks PE signature' }
} finally { $exeStream.Dispose() }

# Bound the packaged GUI smoke: an unresponsive application must fail the build.
& (Join-Path $PSScriptRoot 'smoke-windows.ps1') -Exe $exe -TimeoutSeconds 30
if (-not $?) { throw 'Packaged Windows GUI smoke failed' }
# In one-file mode Qt/Python DLLs are embedded in the executable's PyInstaller
# archive and unpacked at launch, so file-system DLL checks apply only to onedir.
# Validate the onedir runtime before creating a portable bundle.
$portable = Join-Path $release "Portable\OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip"
New-Item -ItemType Directory -Force -Path (Split-Path $portable -Parent) | Out-Null
if (Test-Path $portable) { Remove-Item $portable }
if ($SingleExe) {
  $stage = Join-Path $root 'build\portable-onefile'
  if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
  New-Item -ItemType Directory -Path $stage -Force | Out-Null
  Copy-Item -LiteralPath $exe -Destination (Join-Path $stage 'OpenRemoteStudio.exe')
  Compress-Archive -LiteralPath (Join-Path $stage 'OpenRemoteStudio.exe') -DestinationPath $portable
} else {
  $qtPlugin = @(Get-ChildItem -LiteralPath (Join-Path $root 'dist\OpenRemoteStudio') -Filter 'qwindows.dll' -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Directory.Name -eq 'platforms' })
  if ($qtPlugin.Count -ne 1) { throw 'Qt Windows platform plugin missing or duplicated' }
  $pythonDll = @(Get-ChildItem -LiteralPath (Join-Path $root 'dist\OpenRemoteStudio') -Filter 'python3*.dll' -File -Recurse -ErrorAction SilentlyContinue)
  if ($pythonDll.Count -lt 1) { throw 'Embedded Python runtime missing' }
  Compress-Archive -Path (Join-Path $root 'dist\OpenRemoteStudio') -DestinationPath $portable
}
# Qualify the *extracted* portable distribution in a clean directory. A working
# PyInstaller dist folder does not prove the shipped ZIP can launch independently.
$portableSmokeDir = Join-Path $env:TEMP ('OpenRemoteStudio-portable-qa-' + [guid]::NewGuid().ToString('N'))
try {
  New-Item -ItemType Directory -Path $portableSmokeDir -Force | Out-Null
  Expand-Archive -LiteralPath $portable -DestinationPath $portableSmokeDir -ErrorAction Stop
  $portableExecutables = @(Get-ChildItem -LiteralPath $portableSmokeDir -Filter 'OpenRemoteStudio.exe' -File -Recurse)
  if ($portableExecutables.Count -ne 1) { throw 'Extracted portable must contain exactly one OpenRemoteStudio.exe' }
  & (Join-Path $PSScriptRoot 'smoke-windows.ps1') -Exe $portableExecutables[0].FullName -TimeoutSeconds 30
  if (-not $?) { throw 'Extracted portable GUI smoke failed' }
} finally {
  if (Test-Path -LiteralPath $portableSmokeDir) {
    Remove-Item -LiteralPath $portableSmokeDir -Recurse -Force -ErrorAction SilentlyContinue
  }
}
# Inspect the final portable ZIP rather than trusting the staging folder alone.
if (-not (Test-Path -LiteralPath $portable -PathType Leaf)) { throw 'Portable ZIP was not created' }
Add-Type -AssemblyName System.IO.Compression
$archive = [IO.Compression.ZipFile]::OpenRead($portable)
try {
  $entries = @($archive.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) })
  if ($entries.Count -eq 0) { throw 'Portable archive is empty' }
  $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
  foreach ($entry in $entries) {
    $name = $entry.FullName.Replace('\','/')
    if ($name.StartsWith('/') -or $name -match '(^|/)\.\.(/|$)' -or $name -match '^[A-Za-z]:') { throw "Unsafe portable ZIP path: $name" }
    if (-not $seen.Add($name)) { throw "Duplicate portable ZIP path: $name" }
    if ($entry.Name -eq 'OpenRemoteStudio.exe' -and $entry.Length -lt 512) { throw 'Portable executable is empty or invalid' }
    $stream = $entry.Open()
    try {
      $buffer = New-Object byte[] 65536
      while ($stream.Read($buffer, 0, $buffer.Length) -gt 0) { }
    } finally { $stream.Dispose() }
  }
  $exeEntries = @($entries | Where-Object { $_.Name -eq 'OpenRemoteStudio.exe' })
  if ($exeEntries.Count -ne 1) { throw 'Portable archive must contain exactly one application executable' }
  if (-not $SingleExe) {
    $platformEntries = @($entries | Where-Object { $_.Name -eq 'qwindows.dll' -and $_.FullName.Replace('\','/') -match '(^|/)platforms/' })
    if ($platformEntries.Count -ne 1) { throw 'Portable archive missing Qt Windows platform plugin' }
    $runtimeEntries = @($entries | Where-Object { $_.Name -match '^python3[0-9]+\.dll$' })
    if ($runtimeEntries.Count -lt 1) { throw 'Portable archive missing Python runtime' }
  }
} finally { $archive.Dispose() }
if (-not $SkipInstaller) {
  $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
  if (-not $iscc) { throw 'Inno Setup 6 not found; use -SkipInstaller for portable ZIP' }
  # Never accept a stale setup binary from a previous build.
  $setupPath = Join-Path $release "Installer\OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe"
  New-Item -ItemType Directory -Force -Path (Split-Path $setupPath -Parent) | Out-Null
  if (Test-Path -LiteralPath $setupPath) { Remove-Item -LiteralPath $setupPath -Force }
  Set-Content -LiteralPath (Join-Path $PSScriptRoot 'version.generated.iss') -Value ('#define MyAppVersion "' + $releaseVersion + '"') -Encoding ASCII
  $issArgs = @((Join-Path $PSScriptRoot 'OpenRemoteStudio.iss'))
  if ($SingleExe) { $issArgs += '/DSingleExeBuild=1' }
  $issArgs += ('/O' + (Join-Path $release 'Installer'))
  & $iscc @issArgs
  if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed' }
  if (-not (Test-Path -LiteralPath $setupPath -PathType Leaf)) { throw 'Inno Setup returned success but Setup.exe is absent' }
  if ((Get-Item -LiteralPath $setupPath).Length -lt 1024) { throw 'Setup.exe is suspiciously small' }
  # An Inno Setup output must be a Windows PE, not an arbitrary nonempty file.
  $setupBytes = [IO.File]::OpenRead($setupPath)
  try {
    $setupReader = New-Object IO.BinaryReader($setupBytes)
    if ($setupReader.ReadUInt16() -ne 0x5A4D) { throw 'Installer lacks MZ signature' }
    $setupBytes.Position = 0x3C
    $setupPeOffset = $setupReader.ReadInt32()
    if ($setupPeOffset -lt 64 -or $setupPeOffset -gt ($setupBytes.Length - 4)) { throw 'Installer PE offset invalid' }
    $setupBytes.Position = $setupPeOffset
    if ($setupReader.ReadUInt32() -ne 0x00004550) { throw 'Installer lacks PE signature' }
  } finally { $setupBytes.Dispose() }

}
Get-ChildItem $release -File -Recurse | Where-Object { $_.Name -ne 'SHA256SUMS.txt' -and $_.Name -ne 'build-log.txt' -and $_.Name -ne 'README.txt' } | Get-FileHash -Algorithm SHA256 | ForEach-Object { "$($_.Hash)  $($_.Path.Substring($release.Length + 1).Replace('\','/'))" } | Set-Content (Join-Path $release 'SHA256SUMS.txt') -Encoding ascii
& (Join-Path $PSScriptRoot 'verify-release.ps1') -ReleaseDir $release -SkipInstaller:$SkipInstaller -SingleExe:$SingleExe
if (-not $?) { throw 'Release verification failed' }
if ($RunInstallSmoke) {
  & (Join-Path $PSScriptRoot 'install-smoke-windows.ps1') -SetupExe (Join-Path $release "Installer\OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe") -TimeoutSeconds $InstallSmokeTimeoutSeconds
  if (-not $?) { throw 'Installed Windows smoke failed' }
}
# Independent cross-platform binary gate validates the PE embedded in the ZIP.
$binaryGateArgs = @((Join-Path $PSScriptRoot 'verify-binary-artifacts.py'), '--portable', $portable)
if ($SingleExe) { $binaryGateArgs += '--onefile' }
if (-not $SkipInstaller) { $binaryGateArgs += @('--installer', $setupPath) }
& $python @binaryGateArgs
if ($LASTEXITCODE -ne 0) { throw 'Binary artifact validation failed' }
# Publish only after every validation and optional install smoke succeeded.
# A versioned final directory makes replacement a single directory rename.
$published = Join-Path $binaryRoot ('V' + $releaseVersion)
if (Test-Path -LiteralPath $published) {
  throw "Release V$releaseVersion already published. Remove it explicitly before rebuilding. Staging retained: $release"
}
Move-Item -LiteralPath $release -Destination $published -ErrorAction Stop
Write-Host "Validated release published: $published"
Get-ChildItem $published -File -Recurse | Select-Object FullName,Length
