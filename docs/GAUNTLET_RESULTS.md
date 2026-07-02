# Detection gauntlet — results

Run on the **official Fortress binary** (Chromium 151.0.7908.0, `is_official_build`,
non-component, stripped) with the full default persona + bundled fonts +
`--uxr-webrtc-policy=disable_non_proxied_udp`.

## CreepJS (`abrahamjuliot.github.io/creepjs`)
- **0% headless**
- **0% stealth** (no stealth-tooling signatures)
- WebRTC: host connection **blocked**, foundation/IP unsupported/blocked (no IP leak)
- Worker signals coherent with main thread: `en-US` / `America/New_York`
- ("38% like headless" is CreepJS's fuzzy resemblance score, not the hard headless flag, which is 0%)

## bot.sannysoft.com
- **0 failed tests**
- WebDriver Advanced: **passed**; `navigator.webdriver = false`
- WebGL Vendor: `Google Inc. (NVIDIA)`
- WebGL Renderer: `ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)`
- Permissions: `HEADCHR_PERMISSIONS ok`

## browserscan.net/bot-detection
- Verdict: **"No bots detected — the visitor could be a human using a regular browser."**

## Build-quality checks (official binary)
- De-brand: **0** occurrences of the internal codename in the binary
- Single non-component binary (only ANGLE/SwiftShader graphics `.so`s, as any Chrome)
- Codecs: `canPlayType('video/mp4; codecs="avc1.42E01E")` → **"probably"**
  (stock Chromium returns `""` — a headless tell; fixed via `ffmpeg_branding="Chrome"` + `proprietary_codecs`)
- Emoji: `document.fonts.check('Segoe UI Emoji')` → **true**, renders full color (no tofu)

## Scope
These suites test the **browser fingerprint + automation surface**, which Fortress fully defeats.
They do **not** test **IP reputation** — a datacenter IP is still a datacenter IP regardless of a
perfect fingerprint. For real-world stealth, pair Fortress with residential/mobile proxy egress.

Reproduce: `tools/gauntlet.py --bundle /path/to/tilion-fortress`
