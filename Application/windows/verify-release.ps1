# Verify release artifacts after packaging. No installation performed.
param([string]$ReleaseDir = (Join-Path $PSScriptRoot '..\..\Binary'), [switch]$SkipInstaller, [switch]$SingleExe)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$releaseVersion = (Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\..\VERSION.txt') -Raw).Trim()
$portable = Join-Path $ReleaseDir "Portable\OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip"
if (-not (Test-Path $portable)) { throw "Portable archive missing: $portable" }
Add-Type -AssemblyName System.IO.Compression
$archive = [IO.Compression.ZipFile]::OpenRead($portable)
try {
  $exe = @($archive.Entries | Where-Object { $_.FullName.Replace('\','/') -match '(^|/)OpenRemoteStudio\.exe
  if ($exe.Count -ne 1 -or $exe[0].Length -le 0) { throw 'Portable ZIP lacks a nonempty OpenRemoteStudio.exe' }
  # Fail closed when the portable build misses the Qt Windows platform plugin
  # or the embedded Python runtime. The ZIP must run without system Python.
  $files = @($archive.Entries | Where-Object { -not $_.FullName.EndsWith('/') })
  $qtPlatforms = @($files | Where-Object { $_.FullName.Replace('\','/') -match '(^|/)platforms/qwindows\.dll$' -and $_.Length -gt 0 })
  if (-not $SingleExe -and $qtPlatforms.Count -ne 1) { throw 'Portable ZIP must contain exactly one nonempty Qt platforms/qwindows.dll' }
  $pythonRuntime = @($files | Where-Object { $_.Name -match '^python3[0-9]+\.dll$' -and $_.Length -gt 0 })
  if (-not $SingleExe -and $pythonRuntime.Count -lt 1) { throw 'Portable ZIP lacks an embedded Python runtime DLL' }
  if ($SingleExe -and $files.Count -ne 1) { throw 'Single EXE portable ZIP must contain only OpenRemoteStudio.exe' }
  # Check every entry, not only the presence of the executable: reject traversal,
  # duplicate names and corrupted compressed payloads before publishing a release.
  $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
  foreach ($entry in $archive.Entries) {
    $name = $entry.FullName.Replace('\','/')
    if ([string]::IsNullOrWhiteSpace($name) -or $name.StartsWith('/') -or $name -match '(^|/)\.\.(/|$)' -or $name -match '^[A-Za-z]:') {
      throw "Unsafe portable ZIP path: $name"
    }
    if (-not $seen.Add($name)) { throw "Duplicate portable ZIP entry: $name" }
    if ($name.EndsWith('/')) { continue }
    $stream = $entry.Open()
    try {
      $buffer = New-Object byte[] 65536
      $total = [long]0
      while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) { $total += $read }
      if ($total -ne $entry.Length) { throw "Portable ZIP truncated: $name" }
    } finally { $stream.Dispose() }
  }
} finally { $archive.Dispose() }
if (-not $SkipInstaller) {
  $setup = Join-Path $ReleaseDir "Installer\OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe"
  if (-not (Test-Path $setup) -or (Get-Item $setup).Length -le 0) { throw "Installer missing or empty: $setup" }
}
# Verify hashes, not only file existence. Reject stale, missing, duplicated or tampered entries.
$manifest = Join-Path $ReleaseDir 'SHA256SUMS.txt'
if (-not (Test-Path -LiteralPath $manifest)) { throw 'SHA256 manifest missing' }
$expected = @{}
foreach ($line in (Get-Content -LiteralPath $manifest)) {
  if ($line -notmatch '^([A-Fa-f0-9]{64})  (.+)$') { throw "Invalid SHA256 manifest entry: $line" }
  $name = $Matches[2]
  if ($expected.ContainsKey($name)) { throw "Duplicate SHA256 manifest entry: $name" }
  $expected[$name] = $Matches[1].ToUpperInvariant()
}
$required = @("Portable/OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip")
if (-not $SkipInstaller) { $required += "Installer/OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe" }
# The manifest is a closed inventory: every named artifact must exist and be
# hashed, and every published artifact must have exactly one manifest entry.
$allowed = @($required + @('SHA256SUMS.txt','build-log.txt'))
$published = @(Get-ChildItem -LiteralPath $ReleaseDir -File -Recurse)
foreach ($artifact in $published) {
  if ($artifact.Name -eq 'README.txt') { continue }; $relative = $artifact.FullName.Substring($ReleaseDir.Length + 1).Replace('\','/'); if ($relative -notin $allowed -and $artifact.Name -notin @('SHA256SUMS.txt','build-log.txt')) { throw "Unexpected release artifact: $relative" }
}
foreach ($name in @($expected.Keys)) {
  if ($name -notin $required) { throw "Unexpected SHA256 manifest entry: $name" }
  $path = Join-Path $ReleaseDir ($name.Replace('/','\'))
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Manifest artifact missing: $name" }
  if ((Get-Item -LiteralPath $path).Length -le 0) { throw "Empty release artifact: $name" }
  $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if ($actual -ne $expected[$name]) { throw "SHA256 mismatch: $name" }
}
foreach ($name in $required) {
  if (-not $expected.ContainsKey($name)) { throw "Missing SHA256 entry: $name" }
}
Write-Host 'Release artifact structural verification PASS'
exit 0
 })
  if ($exe.Count -ne 1 -or $exe[0].Length -le 0) { throw 'Portable ZIP lacks a nonempty OpenRemoteStudio.exe' }
  # Fail closed when the portable build misses the Qt Windows platform plugin
  # or the embedded Python runtime. The ZIP must run without system Python.
  $files = @($archive.Entries | Where-Object { -not $_.FullName.EndsWith('/') })
  $qtPlatforms = @($files | Where-Object { $_.FullName.Replace('\','/') -match '(^|/)platforms/qwindows\.dll$' -and $_.Length -gt 0 })
  if (-not $SingleExe -and $qtPlatforms.Count -ne 1) { throw 'Portable ZIP must contain exactly one nonempty Qt platforms/qwindows.dll' }
  $pythonRuntime = @($files | Where-Object { $_.Name -match '^python3[0-9]+\.dll$' -and $_.Length -gt 0 })
  if (-not $SingleExe -and $pythonRuntime.Count -lt 1) { throw 'Portable ZIP lacks an embedded Python runtime DLL' }
  if ($SingleExe -and $files.Count -ne 1) { throw 'Single EXE portable ZIP must contain only OpenRemoteStudio.exe' }
  # Check every entry, not only the presence of the executable: reject traversal,
  # duplicate names and corrupted compressed payloads before publishing a release.
  $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
  foreach ($entry in $archive.Entries) {
    $name = $entry.FullName.Replace('\','/')
    if ([string]::IsNullOrWhiteSpace($name) -or $name.StartsWith('/') -or $name -match '(^|/)\.\.(/|$)' -or $name -match '^[A-Za-z]:') {
      throw "Unsafe portable ZIP path: $name"
    }
    if (-not $seen.Add($name)) { throw "Duplicate portable ZIP entry: $name" }
    if ($name.EndsWith('/')) { continue }
    $stream = $entry.Open()
    try {
      $buffer = New-Object byte[] 65536
      $total = [long]0
      while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) { $total += $read }
      if ($total -ne $entry.Length) { throw "Portable ZIP truncated: $name" }
    } finally { $stream.Dispose() }
  }
} finally { $archive.Dispose() }
if (-not $SkipInstaller) {
  $setup = Join-Path $ReleaseDir "Installer\OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe"
  if (-not (Test-Path $setup) -or (Get-Item $setup).Length -le 0) { throw "Installer missing or empty: $setup" }
}
# Verify hashes, not only file existence. Reject stale, missing, duplicated or tampered entries.
$manifest = Join-Path $ReleaseDir 'SHA256SUMS.txt'
if (-not (Test-Path -LiteralPath $manifest)) { throw 'SHA256 manifest missing' }
$expected = @{}
foreach ($line in (Get-Content -LiteralPath $manifest)) {
  if ($line -notmatch '^([A-Fa-f0-9]{64})  (.+)$') { throw "Invalid SHA256 manifest entry: $line" }
  $name = $Matches[2]
  if ($expected.ContainsKey($name)) { throw "Duplicate SHA256 manifest entry: $name" }
  $expected[$name] = $Matches[1].ToUpperInvariant()
}
$required = @("Portable/OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip")
if (-not $SkipInstaller) { $required += "Installer/OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe" }
# The manifest is a closed inventory: every named artifact must exist and be
# hashed, and every published artifact must have exactly one manifest entry.
$allowed = @($required + @('SHA256SUMS.txt','build-log.txt'))
$published = @(Get-ChildItem -LiteralPath $ReleaseDir -File -Recurse)
foreach ($artifact in $published) {
  if ($artifact.Name -eq 'README.txt') { continue }; $relative = $artifact.FullName.Substring($ReleaseDir.Length + 1).Replace('\','/'); if ($relative -notin $allowed -and $artifact.Name -notin @('SHA256SUMS.txt','build-log.txt')) { throw "Unexpected release artifact: $relative" }
}
foreach ($name in @($expected.Keys)) {
  if ($name -notin $required) { throw "Unexpected SHA256 manifest entry: $name" }
  $path = Join-Path $ReleaseDir ($name.Replace('/','\'))
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Manifest artifact missing: $name" }
  if ((Get-Item -LiteralPath $path).Length -le 0) { throw "Empty release artifact: $name" }
  $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if ($actual -ne $expected[$name]) { throw "SHA256 mismatch: $name" }
}
foreach ($name in $required) {
  if (-not $expected.ContainsKey($name)) { throw "Missing SHA256 entry: $name" }
}
Write-Host 'Release artifact structural verification PASS'
exit 0
 })
  if ($exe.Count -ne 1 -or $exe[0].Length -le 0) { throw 'Portable ZIP lacks a nonempty OpenRemoteStudio.exe' }
  # Fail closed when the portable build misses the Qt Windows platform plugin
  # or the embedded Python runtime. The ZIP must run without system Python.
  $files = @($archive.Entries | Where-Object { -not $_.FullName.EndsWith('/') })
  $qtPlatforms = @($files | Where-Object { $_.FullName.Replace('\','/') -match '(^|/)platforms/qwindows\.dll$' -and $_.Length -gt 0 })
  if (-not $SingleExe -and $qtPlatforms.Count -ne 1) { throw 'Portable ZIP must contain exactly one nonempty Qt platforms/qwindows.dll' }
  $pythonRuntime = @($files | Where-Object { $_.Name -match '^python3[0-9]+\.dll$' -and $_.Length -gt 0 })
  if (-not $SingleExe -and $pythonRuntime.Count -lt 1) { throw 'Portable ZIP lacks an embedded Python runtime DLL' }
  if ($SingleExe -and $files.Count -ne 1) { throw 'Single EXE portable ZIP must contain only OpenRemoteStudio.exe' }
  # Check every entry, not only the presence of the executable: reject traversal,
  # duplicate names and corrupted compressed payloads before publishing a release.
  $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
  foreach ($entry in $archive.Entries) {
    $name = $entry.FullName.Replace('\','/')
    if ([string]::IsNullOrWhiteSpace($name) -or $name.StartsWith('/') -or $name -match '(^|/)\.\.(/|$)' -or $name -match '^[A-Za-z]:') {
      throw "Unsafe portable ZIP path: $name"
    }
    if (-not $seen.Add($name)) { throw "Duplicate portable ZIP entry: $name" }
    if ($name.EndsWith('/')) { continue }
    $stream = $entry.Open()
    try {
      $buffer = New-Object byte[] 65536
      $total = [long]0
      while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) { $total += $read }
      if ($total -ne $entry.Length) { throw "Portable ZIP truncated: $name" }
    } finally { $stream.Dispose() }
  }
} finally { $archive.Dispose() }
if (-not $SkipInstaller) {
  $setup = Join-Path $ReleaseDir "Installer\OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe"
  if (-not (Test-Path $setup) -or (Get-Item $setup).Length -le 0) { throw "Installer missing or empty: $setup" }
}
# Verify hashes, not only file existence. Reject stale, missing, duplicated or tampered entries.
$manifest = Join-Path $ReleaseDir 'SHA256SUMS.txt'
if (-not (Test-Path -LiteralPath $manifest)) { throw 'SHA256 manifest missing' }
$expected = @{}
foreach ($line in (Get-Content -LiteralPath $manifest)) {
  if ($line -notmatch '^([A-Fa-f0-9]{64})  (.+)$') { throw "Invalid SHA256 manifest entry: $line" }
  $name = $Matches[2]
  if ($expected.ContainsKey($name)) { throw "Duplicate SHA256 manifest entry: $name" }
  $expected[$name] = $Matches[1].ToUpperInvariant()
}
$required = @("Portable/OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip")
if (-not $SkipInstaller) { $required += "Installer/OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe" }
# The manifest is a closed inventory: every named artifact must exist and be
# hashed, and every published artifact must have exactly one manifest entry.
$allowed = @($required + @('SHA256SUMS.txt','build-log.txt'))
$published = @(Get-ChildItem -LiteralPath $ReleaseDir -File -Recurse)
foreach ($artifact in $published) {
  if ($artifact.Name -eq 'README.txt') { continue }; $relative = $artifact.FullName.Substring($ReleaseDir.Length + 1).Replace('\','/'); if ($relative -notin $allowed -and $artifact.Name -notin @('SHA256SUMS.txt','build-log.txt')) { throw "Unexpected release artifact: $relative" }
}
foreach ($name in @($expected.Keys)) {
  if ($name -notin $required) { throw "Unexpected SHA256 manifest entry: $name" }
  $path = Join-Path $ReleaseDir ($name.Replace('/','\'))
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Manifest artifact missing: $name" }
  if ((Get-Item -LiteralPath $path).Length -le 0) { throw "Empty release artifact: $name" }
  $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if ($actual -ne $expected[$name]) { throw "SHA256 mismatch: $name" }
}
foreach ($name in $required) {
  if (-not $expected.ContainsKey($name)) { throw "Missing SHA256 entry: $name" }
}
Write-Host 'Release artifact structural verification PASS'
exit 0
 })
  if ($exe.Count -ne 1 -or $exe[0].Length -le 0) { throw 'Portable ZIP lacks a nonempty OpenRemoteStudio.exe' }
  # Fail closed when the portable build misses the Qt Windows platform plugin
  # or the embedded Python runtime. The ZIP must run without system Python.
  $files = @($archive.Entries | Where-Object { -not $_.FullName.EndsWith('/') })
  $qtPlatforms = @($files | Where-Object { $_.FullName.Replace('\','/') -match '(^|/)platforms/qwindows\.dll$' -and $_.Length -gt 0 })
  if (-not $SingleExe -and $qtPlatforms.Count -ne 1) { throw 'Portable ZIP must contain exactly one nonempty Qt platforms/qwindows.dll' }
  $pythonRuntime = @($files | Where-Object { $_.Name -match '^python3[0-9]+\.dll$' -and $_.Length -gt 0 })
  if (-not $SingleExe -and $pythonRuntime.Count -lt 1) { throw 'Portable ZIP lacks an embedded Python runtime DLL' }
  if ($SingleExe -and $files.Count -ne 1) { throw 'Single EXE portable ZIP must contain only OpenRemoteStudio.exe' }
  # Check every entry, not only the presence of the executable: reject traversal,
  # duplicate names and corrupted compressed payloads before publishing a release.
  $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
  foreach ($entry in $archive.Entries) {
    $name = $entry.FullName.Replace('\','/')
    if ([string]::IsNullOrWhiteSpace($name) -or $name.StartsWith('/') -or $name -match '(^|/)\.\.(/|$)' -or $name -match '^[A-Za-z]:') {
      throw "Unsafe portable ZIP path: $name"
    }
    if (-not $seen.Add($name)) { throw "Duplicate portable ZIP entry: $name" }
    if ($name.EndsWith('/')) { continue }
    $stream = $entry.Open()
    try {
      $buffer = New-Object byte[] 65536
      $total = [long]0
      while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) { $total += $read }
      if ($total -ne $entry.Length) { throw "Portable ZIP truncated: $name" }
    } finally { $stream.Dispose() }
  }
} finally { $archive.Dispose() }
if (-not $SkipInstaller) {
  $setup = Join-Path $ReleaseDir "Installer\OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe"
  if (-not (Test-Path $setup) -or (Get-Item $setup).Length -le 0) { throw "Installer missing or empty: $setup" }
}
# Verify hashes, not only file existence. Reject stale, missing, duplicated or tampered entries.
$manifest = Join-Path $ReleaseDir 'SHA256SUMS.txt'
if (-not (Test-Path -LiteralPath $manifest)) { throw 'SHA256 manifest missing' }
$expected = @{}
foreach ($line in (Get-Content -LiteralPath $manifest)) {
  if ($line -notmatch '^([A-Fa-f0-9]{64})  (.+)$') { throw "Invalid SHA256 manifest entry: $line" }
  $name = $Matches[2]
  if ($expected.ContainsKey($name)) { throw "Duplicate SHA256 manifest entry: $name" }
  $expected[$name] = $Matches[1].ToUpperInvariant()
}
$required = @("Portable/OpenRemoteStudio-V${releaseVersion}-Windows-Portable.zip")
if (-not $SkipInstaller) { $required += "Installer/OpenRemoteStudio-V${releaseVersion}-Windows-Setup.exe" }
# The manifest is a closed inventory: every named artifact must exist and be
# hashed, and every published artifact must have exactly one manifest entry.
$allowed = @($required + @('SHA256SUMS.txt','build-log.txt'))
$published = @(Get-ChildItem -LiteralPath $ReleaseDir -File -Recurse)
foreach ($artifact in $published) {
  if ($artifact.Name -eq 'README.txt') { continue }; $relative = $artifact.FullName.Substring($ReleaseDir.Length + 1).Replace('\','/'); if ($relative -notin $allowed -and $artifact.Name -notin @('SHA256SUMS.txt','build-log.txt')) { throw "Unexpected release artifact: $relative" }
}
foreach ($name in @($expected.Keys)) {
  if ($name -notin $required) { throw "Unexpected SHA256 manifest entry: $name" }
  $path = Join-Path $ReleaseDir ($name.Replace('/','\'))
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Manifest artifact missing: $name" }
  if ((Get-Item -LiteralPath $path).Length -le 0) { throw "Empty release artifact: $name" }
  $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if ($actual -ne $expected[$name]) { throw "SHA256 mismatch: $name" }
}
foreach ($name in $required) {
  if (-not $expected.ContainsKey($name)) { throw "Missing SHA256 entry: $name" }
}
Write-Host 'Release artifact structural verification PASS'
exit 0
