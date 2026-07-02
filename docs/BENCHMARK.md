# Fortress — Benchmark

Measured on a datacenter Linux x86-64 host (**no GPU**), driving each `chrome` binary over
CDP at 1280×800. Captured 2026-06-24. No mock-ups — every number is a live read.

## Engine vs stock Chromium (raw, over CDP)

| Signal | Vanilla Chromium (no stealth) | **Fortress** |
|---|---|---|
| Browser | Chrome 148 | **Chrome 151** |
| CDP `User-Agent` (`/json/version`) | `HeadlessChrome/148 … X11; Linux x86_64` 🚩 | `Chrome/151 … Windows NT 10.0; Win64; x64` ✅ |
| `navigator.platform` | `Linux x86_64` 🚩 | `Win32` ✅ |
| timezone | `UTC` 🚩 | `America/New_York` ✅ |
| `hardwareConcurrency` | 12 (real host) | 16 |
| WebGL renderer | `ANGLE … SwiftShader` 🚩🚩 (no-GPU datacenter tell) | `ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 …)` ✅ |
| getter nativeness | native | **native** (C++ — not a JS override) |
| cold launch | 0.28 s | 0.27 s |
| RSS | 1264 MB | 1391 MB (+10%) |

Naked Chromium leaks "headless Linux SwiftShader bot" on every axis; Fortress presents a
coherent Windows / NVIDIA-desktop identity **natively** — real native getters, no JS
injection, no `Runtime.enable` — at the same launch speed and ~10% more RAM.

## Detection panels (Fortress, datacenter IP)

| Test | Result |
|---|---|
| bot.sannysoft.com | all checks **pass** — WebDriver missing, Chrome present, NVIDIA WebGL, all `PHANTOM_*` |
| browserscan.net/bot-detection | **Normal — "No bots detected"** (Webdriver / User-Agent / CDP / Navigator) |
| CreepJS | renders a coherent, stable fingerprint |

Screenshots: `docs/assets/sannysoft.png`, `browserscan.png`, `creepjs.png`.

## Running inside the Tilion stack (drop-in engine)

One env var; the rest of the stack (REST API, sessions, live-view, self-heal) is unchanged:

    TILION_ENGINE_BINARY=/path/to/tilion-fortress/tilion   # launch Fortress, not bundled Chromium
    TILION_NATIVE_STEALTH=1                                # skip Tilion JS injection — Fortress spoofs in C++

Verified end-to-end: a fetch through Tilion's `/v1/fetch` on Fortress is seen by the origin
as `Chrome/151 … Windows NT 10.0`; the fingerprint battery on the **live session** browser
returns `platform=Win32`, `webgl=NVIDIA RTX 3060`, all native getters.

> A flawless fingerprint still meets an image challenge from a **datacenter IP** on Google
> reCAPTCHA v2 / Cloudflare managed — that gate is the egress IP, not the browser. Route
> through residential/mobile egress for a silent pass.
