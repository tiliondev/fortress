<#
  Fortress native Windows build.

  Prereqs (see docs/BUILD_NATIVE.md):
    - Visual Studio 2022 with "Desktop development with C++" + Windows 11 SDK (with Debugging Tools)
    - depot_tools on PATH, set DEPOT_TOOLS_WIN_TOOLCHAIN=0
    - ~100 GB free disk, long build time
    - git, python3

  Usage (from a Developer PowerShell):
    pwsh build\windows\build.ps1 -WorkDir D:\fortress-build
#>
[CmdletBinding()]
param(
  [string]$WorkDir = "$PSScriptRoot\..\..\.fortress-build-win",
  [string]$ChromiumVersion = ""
)
$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path "$PSScriptRoot\..\..").Path
if (-not $ChromiumVersion) { $ChromiumVersion = (Get-Content "$Repo\CHROMIUM_VERSION").Trim() }
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

Write-Host "==> Fortress Windows build | Chromium $ChromiumVersion | $WorkDir"

# 1. depot_tools
if (-not (Test-Path "$WorkDir\depot_tools")) {
  git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git "$WorkDir\depot_tools"
}
$env:PATH = "$WorkDir\depot_tools;$env:PATH"
$env:DEPOT_TOOLS_WIN_TOOLCHAIN = "0"

# 2. fetch + sync to the pinned tag
if (-not (Test-Path "$WorkDir\chromium\src")) {
  New-Item -ItemType Directory -Force -Path "$WorkDir\chromium" | Out-Null
  Push-Location "$WorkDir\chromium"; fetch --nohooks --no-history chromium; Pop-Location
}
Push-Location "$WorkDir\chromium\src"
git fetch --depth 1 origin "refs/tags/${ChromiumVersion}:refs/tags/${ChromiumVersion}"
git checkout -f "tags/$ChromiumVersion"
gclient sync -D --no-history --reset

# 3. apply Fortress patches (git apply works cross-platform)
foreach ($rel in Get-Content "$Repo\patches\series") {
  if (-not $rel.Trim()) { continue }
  $p = Join-Path $Repo $rel
  Write-Host "  applying $rel"
  git apply --3way --whitespace=nowarn $p
  if ($LASTEXITCODE -ne 0) { throw "patch failed (needs re-anchoring on $ChromiumVersion): $rel" }
}

# 4. configure + build
$gnArgs = (Get-Content "$Repo\build\args.windows.gn") -join "`n"
gn gen out\Fortress --args="$gnArgs"
autoninja -C out\Fortress chrome

Pop-Location
Write-Host "==> Done: $WorkDir\chromium\src\out\Fortress\chrome.exe"
& "$WorkDir\chromium\src\out\Fortress\chrome.exe" --version
