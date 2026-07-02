@echo off
REM Tilion Fortress launcher (Windows). Applies a coherent default Windows persona via
REM --uxr-* switches + enables WebGPU presence, then runs chrome.exe with all passthrough args.
REM Windows uses system fonts (which already match the spoofed OS), so no fontconfig bundle.
REM Override: pass your own --uxr-* flags, or set TILION_NO_DEFAULTS=1 for a bare launch.
setlocal
set HERE=%~dp0
set VK_ICD_FILENAMES=%HERE%vk_swiftshader_icd.json
set DEF=
if not defined TILION_NO_DEFAULTS set DEF=^
 --uxr-platform=Win32 --uxr-ua-platform=Windows "--uxr-ua-os=Windows NT 10.0; Win64; x64"^
 --uxr-ua-arch=x86 --uxr-ua-bitness=64 --uxr-ua-platform-version=15.0.0 "--uxr-ua-brand=Google Chrome"^
 --uxr-hw-concurrency=16 --uxr-device-memory=8^
 "--uxr-webgl-vendor=Google Inc. (NVIDIA)"^
 "--uxr-webgl-renderer=ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"^
 --uxr-webgl-fullparams=1 --uxr-canvas-seed=778899 --uxr-audio-seed=445566^
 --uxr-timezone=America/New_York --uxr-languages=en-US,en --accept-lang=en-US,en^
 --uxr-screen-width=1920 --uxr-screen-height=1080^
 --uxr-webrtc-policy=disable_non_proxied_udp^
 --enable-unsafe-webgpu --enable-features=Vulkan --use-webgpu-adapter=swiftshader^
 --enable-dawn-features=use_vulkan --uxr-webgpu-vendor=nvidia --uxr-webgpu-architecture=ampere "--uxr-webgpu-description=NVIDIA GeForce RTX 3060"
"%HERE%chrome.exe" %DEF% %*
endlocal
