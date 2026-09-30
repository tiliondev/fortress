# Fortress persona configuration (`--uxr-*`)

Fortress ships one binary that mints a **fresh, coherent persona per launch** from a seed. You normally set **nothing** — the launcher applies a realistic default and every surface is generated to agree with every other. When you *do* need to pin or override a surface (a specific OS, a fixed GPU, a chosen timezone, a reproducible seed), you use the `--uxr-*` switches or a handful of `TILION_*` environment variables below.

> **Two rules the engine enforces for you**
> 1. **Coherence.** Platform ⇔ User-Agent ⇔ Client-Hints ⇔ WebGL/WebGPU GPU ⇔ fonts ⇔ screen/DPR ⇔ timezone ⇔ language are kept mutually consistent. Override one and the engine re-derives the rest; override *incoherently* (e.g. a macOS platform with an NVIDIA D3D11 GPU) and you create your own tell.
> 2. **Egress coherence.** Timezone / locale / WebRTC follow your exit IP's country. Match the persona to where the traffic actually leaves from (or let `--uxr-country` drive it).

---

## Quick start

```bash
# Default coherent Windows persona (fresh identity each launch):
./tilion https://example.com

# Reproducible identity (same machine every time) — pin the seed:
./tilion --uxr-seed=42 https://example.com

# A macOS persona in Rome, Italian:
./tilion --uxr-platform=MacIntel --uxr-country=IT https://example.com

# Bare launch (no persona at all):
TILION_NO_DEFAULTS=1 ./tilion https://example.com

# Drive it from your own stack over CDP (persona still applies):
./tilion --headless=new --remote-debugging-port=9222 --user-data-dir=/tmp/p
```

---

## Generation inputs (drive the whole persona)

| Flag | Example | What it does |
|---|---|---|
| `--uxr-seed=<n>` | `--uxr-seed=42` | Pins the persona's **structural machine** (GPU · screen · CPU · fonts · OS · timezone · languages) to a seed — the same hardware identity every launch (reproducible sessions / sticky account identity). **Canvas/audio noise is always fresh per launch** (see [Rendering noise](#rendering-noise-always-fresh)) — a seed reproduces the *machine*, not the pixel-level noise. Omit it for a fully random persona each launch. |
| `--uxr-country=<ISO>` | `--uxr-country=DE` | Drives the geo cluster — timezone, language, keyboard layout, and WebRTC policy all derive from the country (keep it aligned with your egress IP). |
| `--uxr-platform=<v>` | `--uxr-platform=MacIntel` | Forces the OS family: `Win32` / `MacIntel`. Everything OS-derived (UA, GPU backend, fonts, scrollbars, DRM story) follows. |

## User-Agent & Client-Hints

| Flag | Example | What it does |
|---|---|---|
| `--uxr-ua-platform=<v>` | `"Windows"` / `"macOS"` | `navigator.userAgentData.platform` + `Sec-CH-UA-Platform`. |
| `--uxr-ua-os=<v>` | `"Windows NT 10.0"` | The OS token inside the UA string. |
| `--uxr-ua-arch=<v>` | `"x86"` / `"arm"` | `Sec-CH-UA-Arch`. |
| `--uxr-ua-bitness=<v>` | `"64"` | `Sec-CH-UA-Bitness`. |
| `--uxr-ua-platform-version=<v>` | `"15.0.0"` | `Sec-CH-UA-Platform-Version`. |
| `--uxr-ua-brand=<v>` | `"Google Chrome"` | The brand in `Sec-CH-UA` / `userAgentData.brands`. |

*(The full UA string, `Sec-CH-UA-Full-Version-List`, `wow64`, and the model are derived to stay consistent.)*

## Hardware

| Flag | Example | What it does |
|---|---|---|
| `--uxr-hw-concurrency=<n>` | `8` | `navigator.hardwareConcurrency` (logical cores). |
| `--uxr-device-memory=<n>` | `16` | `navigator.deviceMemory` **and** the `Device-Memory` client hint, kept in agreement. |

## GPU — WebGL & WebGPU

| Flag | Example | What it does |
|---|---|---|
| `--uxr-webgl-vendor=<v>` | `"Google Inc. (NVIDIA)"` | `UNMASKED_VENDOR_WEBGL`. |
| `--uxr-webgl-renderer=<v>` | `"ANGLE (NVIDIA, … Direct3D11 …)"` | `UNMASKED_RENDERER_WEBGL`. |
| `--uxr-webgl-fullparams` | *(flag)* | Also aligns the numeric WebGL parameters (limits, precision, extensions) to the chosen GPU — so the numbers match the renderer string, not the software backend. |
| `--uxr-webgpu-vendor=<v>` | `"nvidia"` | `navigator.gpu` adapter vendor. |
| `--uxr-webgpu-architecture=<v>` | `"ampere"` | Adapter architecture. |
| `--uxr-webgpu-description=<v>` | *(usually empty)* | Adapter description (real Chrome returns `""` to normal pages). |

> Keep WebGL and WebGPU on the **same GPU family** — a spoofed WebGL GPU next to a software-backend WebGPU adapter is a stronger tell than no spoof at all. The default persona does this for you.

## Rendering noise (always fresh)

Canvas / WebGL-readback and AudioContext noise are generated **per launch** from a cryptographically-random secret, then **domain-keyed** (each site sees its own stable value *within* a session, à la Brave). This is intentional anti-linkability: **two launches never share canvas/audio — even with the same `--uxr-seed` and the same GPU.** A pinned seed reproduces the structural machine; this noise is deliberately never reproducible.

| Flag | Example | What it does |
|---|---|---|
| `--uxr-canvas-seed=<hex>` | `--uxr-canvas-seed=…` | *Advanced / auto-managed.* Feeds the per-persona canvas / WebGL-readback noise (edge-gated, byte-exact across read paths); also keys the TextMetrics variation. |
| `--uxr-audio-seed=<hex>` | `--uxr-audio-seed=…` | *Advanced / auto-managed.* Feeds the per-persona AudioContext variation. |

> These are **not** reproducibility knobs — the launch path re-derives canvas/audio from a fresh random secret every time, by design. Use `--uxr-seed` to reproduce the *machine*; the noise is never linkable across launches.

## Locale, timezone & display preference

| Flag | Example | What it does |
|---|---|---|
| `--uxr-timezone=<TZ>` | `"Europe/Berlin"` | IANA timezone (JS `Intl` + `Date` + workers, coherent). |
| `--uxr-languages=<list>` | `"de-DE,de,en"` | `navigator.languages` **and** `Accept-Language`, kept in sync. |
| `--uxr-color-scheme=<v>` | `dark` / `light` | `prefers-color-scheme` (per-persona; ~1/3 dark by default). |

## Screen

| Flag | Example | What it does |
|---|---|---|
| `--uxr-screen-width=<n>` | `1920` | `screen.width` (CSS px). |
| `--uxr-screen-height=<n>` | `1080` | `screen.height`. |

*(availWidth/availHeight, avail origin, DPR, and window geometry are derived to stay coherent — e.g. taskbar/menu-bar reserve, `outer ≥ inner`.)*

## Network

| Flag | Example | What it does |
|---|---|---|
| `--uxr-webrtc-policy=<v>` | `disable_non_proxied_udp` | Forces WebRTC through the proxy so the real IP never leaks in an SDP candidate (fail-closed on a bare launch). |

---

## Environment variables

These are read by the **`./tilion` launcher** (it maps them to the switches above before exec). `TILION_SEED` and `TILION_COUNTRY` are *also* read directly by the binary; the rest (`TILION_TZ`, `TILION_LANG`, `TILION_NO_DEFAULTS`, `TILION_NO_GEO`, `TILION_EPHEMERAL`) apply only when you launch through `./tilion`, not when you drive the raw `chrome` binary.

| Env var | Effect |
|---|---|
| `TILION_NO_DEFAULTS=1` | Skip the default persona entirely (bare Chromium launch). |
| `TILION_SEED=<n>` | Same as `--uxr-seed` (pin the persona). |
| `TILION_COUNTRY=<ISO>` | Same as `--uxr-country`. |
| `TILION_TZ=<TZ>` | Quick timezone override. |
| `TILION_LANG=<list>` | Quick `navigator.languages` / `Accept-Language` override. |
| `TILION_NO_GEO=1` | Skip the geo-IP → timezone/locale derivation (use the explicit overrides only). |
| `TILION_EPHEMERAL=1` | Treat the profile as throwaway (no persistence between runs). |

---

## What a persona actually covers

Setting a handful of flags above pins the surfaces you care about; the engine still generates **~57 coherent surfaces** for every persona so nothing is left at a host/default value. In broad strokes:

- **Identity:** platform · UA + full Client-Hints · hardware concurrency · device memory
- **Graphics:** WebGL vendor/renderer + numeric parameters/precision/extensions · WebGPU adapter (identity, limits, subgroup sizes) · canvas & WebGL-readback noise
- **Audio:** AudioContext output + timing
- **Fonts:** a 154-family substrate + per-persona metrics, enumeration gated to the persona
- **Display:** screen size / avail geometry / color-depth / DPR · color-gamut · dynamic-range · `prefers-color-scheme`
- **Locale & geo:** timezone · languages / Accept-Language · keyboard layout
- **Device:** media devices · battery (laptop-coherent) · pointer/hover/touch
- **Network:** connection RTT/downlink/effectiveType · WebRTC policy · storage quota
- **Behavior:** coalesced-pointer timing · realtime audio timing

Every one is derived to agree with the others (that's the whole point) and, on snapshot resume, **re-keyed together** so a resumed clone is a genuinely different — but still coherent — machine.

> This document covers the **configuration API**. It intentionally does not describe *how* each surface is implemented — those internals live in the private engine source.
