# Building Fortress natively on Windows & macOS

The Fortress patch series is OS-agnostic (it touches Blink/content C++ that compiles on every
platform), so the **same patches** produce native Windows and macOS builds. What differs is the
**build host and the signing pipeline** — and the honest constraint below.

## The hard constraint: you need a same-OS build host
Chromium cannot be practically cross-compiled for Windows/macOS from a Linux box. Each native
target needs a build machine of that OS:

| Target | Build host | Toolchain | Disk / time |
|---|---|---|---|
| Windows x64 | Windows 10/11 | Visual Studio 2022 (Desktop C++) + Win 11 SDK | ~100 GB, several hours |
| macOS arm64 | Apple Silicon Mac | Xcode + CLT | ~100 GB, several hours |
| macOS x64 | Intel Mac (or arm64 cross to x64) | Xcode + CLT | ~100 GB, several hours |

GitHub's hosted `windows-latest` / `macos-latest` runners are too small/slow for a full Chromium
build — use a **large self-hosted runner** or a beefy cloud VM (Windows VM; Mac via MacStadium /
AWS EC2 Mac / a local Mac). The `.github/workflows/build-fortress.yml` matrix is wired for
self-hosted runners.

## Windows
```powershell
# one-time: install VS 2022 + Win 11 SDK, put depot_tools on PATH, set:
$env:DEPOT_TOOLS_WIN_TOOLCHAIN = "0"
# build:
pwsh build\windows\build.ps1 -WorkDir D:\fortress-build
# output: out\Fortress\chrome.exe
```
**Sign** (or SmartScreen warns users): an EV/OV cert or Azure Trusted Signing, then
```powershell
pwsh build\windows\sign.ps1 -ExeDir <out\Fortress> -Pfx cert.pfx -Password ****
```

## macOS
```bash
xcode-select --install
build/macos/build.sh ~/fortress-build arm64        # or: x64
# output: out/Fortress/Chromium.app
```
**Notarize** (or Gatekeeper blocks it): a Developer ID Application cert, then
```bash
build/macos/notarize.sh out/Fortress/Chromium.app "Developer ID Application: NAME (TEAMID)" <profile>
```

## Packaging the native builds
- **Windows:** zip the `out\Fortress` runtime set (mirror `packaging/build-bundle.sh`'s file list,
  Windows equivalents) → optionally an NSIS/MSIX installer. A `tilion.cmd` launcher applies the persona.
- **macOS:** the `.app` is self-contained; ship a `.dmg`. Fonts: macOS uses system fonts, so the
  Linux fontconfig bundle is **not** used — the persona font coherence relies on the OS font set.

## Notes on per-OS persona
- The `--uxr-*` switches work identically on all platforms.
- Font handling differs: Linux uses the bundled `fonts/` + `FONTCONFIG_FILE`; Windows/macOS use the
  native system fonts (which already match the spoofed OS), so no font bundle is needed there.
- WebGL/SwiftShader: native Windows/macOS use the real GPU stack; only the Linux container needs the
  bundled `libvulkan.so.1` + SwiftShader path.
