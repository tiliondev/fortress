<#
  Authenticode-sign the Fortress Windows binaries.
  Without signing, Windows SmartScreen warns users on first run.

  Requires:
    - An EV or OV code-signing certificate (.pfx) or an Azure Trusted Signing account
    - signtool.exe (ships with the Windows SDK)

  Usage:
    pwsh build\windows\sign.ps1 -ExeDir <out\Fortress dir> -Pfx <cert.pfx> -Password <pw>
#>
param(
  [Parameter(Mandatory)] [string]$ExeDir,
  [Parameter(Mandatory)] [string]$Pfx,
  [Parameter(Mandatory)] [string]$Password,
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)
$ErrorActionPreference = "Stop"
$targets = Get-ChildItem -Path $ExeDir -Recurse -Include *.exe,*.dll
foreach ($t in $targets) {
  & signtool sign /f $Pfx /p $Password /fd SHA256 /tr $TimestampUrl /td SHA256 $t.FullName
}
Write-Host "==> Signed $($targets.Count) binaries. Verify with: signtool verify /pa <file>"
