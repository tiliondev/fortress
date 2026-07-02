<#
  Package the native Windows Fortress build into a portable tilion-fortress\ bundle + zip + SHA256.
  Usage: pwsh build\windows\package-win.ps1 -Out <out\Fortress dir> -Dest <dist dir>
#>
param(
  [Parameter(Mandatory)] [string]$Out,
  [Parameter(Mandatory)] [string]$Dest
)
$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path "$PSScriptRoot\..\..").Path
$B = Join-Path $Dest "tilion-fortress"
Remove-Item -Recurse -Force $B -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $B | Out-Null

# Windows runtime set (the files chrome.exe needs at runtime; the rest of out\ is build junk).
$runtime = @(
  "chrome.exe","chrome.dll","chrome_elf.dll","chrome_proxy.exe",
  "chrome_100_percent.pak","chrome_200_percent.pak","resources.pak",
  "icudtl.dat","snapshot_blob.bin","v8_context_snapshot.bin",
  "libEGL.dll","libGLESv2.dll","vk_swiftshader.dll","vk_swiftshader_icd.json","vulkan-1.dll",
  "d3dcompiler_47.dll","dxcompiler.dll","dxil.dll"
)
foreach ($f in $runtime) {
  $src = Join-Path $Out $f
  if (Test-Path $src) { Copy-Item $src (Join-Path $B $f) }
}
# version dir (e.g. 151.0.7908.0) carries more dlls in official builds
Get-ChildItem $Out -Directory | Where-Object { $_.Name -match '^\d+\.\d+\.\d+\.\d+$' } |
  ForEach-Object { Copy-Item $_.FullName (Join-Path $B $_.Name) -Recurse }
Copy-Item (Join-Path $Out "locales") (Join-Path $B "locales") -Recurse

Copy-Item (Join-Path $Repo "packaging\tilion.cmd") (Join-Path $B "tilion.cmd")

$asset = Join-Path $Dest "tilion-fortress-win-x64.zip"
Remove-Item $asset -ErrorAction SilentlyContinue
Compress-Archive -Path $B -DestinationPath $asset
$hash = (Get-FileHash $asset -Algorithm SHA256).Hash.ToLower()
"$hash  tilion-fortress-win-x64.zip" | Out-File -Append -Encoding ascii (Join-Path $Dest "SHA256SUMS")
Write-Host "==> $asset  sha256=$hash"
