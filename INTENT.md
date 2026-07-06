# INTENT.md — Fortress (ORACLE Phase -1)

> **Repository**: `/home/j1coder/projects/j1-workspace/fortress`  
> **Upstream**: https://github.com/tiliondev/fortress  
> **Analysis date**: 2026-07-05  
> **Classification**: **Production** — shipping via Docker, PyPI, npm, and portable binaries with monthly CI-gated releases

---

## What this system does

Fortress is an **open-source stealth Chromium engine** — a fork of Chromium patched at the C++ level to correct the browser fingerprint surfaces that bot detectors read. It exposes a raw Chrome DevTools Protocol (CDP) endpoint on `http://localhost:9222`, making it a **drop-in replacement** for any Playwright, Puppeteer, or CDP-based automation tool.

### Technical architecture

| Layer | What it does |
|---|---|
| **35 C++ patches** (`patches/`) | Single-purpose diffs to Blink, V8, and BoringSSL that spoof fingerprint surfaces at the engine level — no JavaScript patch layer |
| **`UxrConfig` singleton** (`base/uxr_config.*`) | Process-global C++ config read by every patched surface; populated from `--uxr-*` command-line flags or IPC |
| **Persona system** (`--uxr-*` flags) | Tunable identity: platform, UA, WebGL vendor/renderer, canvas seed, audio seed, timezone, languages, screen, hardware concurrency, device memory, WebRTC policy |
| **SDKs** (`sdk/python/`, `sdk/node/`) | `tilion-fortress` packages that auto-download, SHA-256-verify, cache, and launch the prebuilt binary |
| **Docker image** (`packaging/Dockerfile`) | Multi-stage Debian-based image, stripped binary, bundled Windows fonts, non-root user |
| **Build system** (`build/`) | `depot_tools` + GN + ninja; `build/build.sh` fetches Chromium at the pinned tag, applies patches, and compiles |
| **Gauntlet** (`tools/gauntlet.py`) | CI gate that launches the binary headless and asserts stealth invariants against live detectors (CreepJS, Sannysoft, BrowserScan) via raw CDP WebSocket |
| **Monthly rebase** (`build/rebase-monthly.sh`) | Bumps the Chromium tag, 3-way applies patches, rebuilds, and re-runs the gauntlet |

### Fingerprint surfaces corrected (35 patches)

- **`navigator.webdriver`** → always `false` (C++, ignores CDP `ApplyAutomationOverride`)
- **User-Agent** → no "Headless" prefix; full Chrome brand list via Sec-CH-UA
- **`navigator.platform`** → "Win32" (default Windows persona)
- **WebGL** → spoofed renderer ("NVIDIA GeForce RTX 3060 / ANGLE D3D11"), vendor, GL_VERSION, GLSL version, shader precision, max texture sizes — all coherent with a real desktop GPU
- **Canvas 2D** → seeded sub-pixel noise on `getImageData` (defeats canvas fingerprinting)
- **WebGL readback** → seeded sub-pixel farble on `ReadPixels`
- **Audio** → seeded sub-perceptual noise on `AudioBuffer` data (defeats audio fingerprinting)
- **DOMRect** → seeded sub-pixel jitter on `getClientRects`/`getBoundingClientRect`
- **WebRTC** → `disable_non_proxied_udp` policy to prevent IP leaks
- **Screen** → spoofed width/height/colorDepth
- **Timezone** → spoofed via `Intl.DateTimeFormat` + timezone controller
- **Languages** → spoofed `navigator.languages`
- **Hardware concurrency** → spoofed `navigator.hardwareConcurrency`
- **Device memory** → spoofed `navigator.deviceMemory`
- **Fonts** → 33 bundled Windows metric-compatible fonts (including Segoe UI Emoji)
- **Media codecs** → `ffmpeg_branding="Chrome"` + `proprietary_codecs` so `canPlayType('video/mp4')` returns "probably" (stock Chromium returns "" — a headless tell)
- **Keyboard layout** → spoofed
- **Network information** → spoofed
- **Speech synthesis** → spoofed voices
- **WebGPU** → spoofed adapter info
- **Storage quota** → spoofed
- **Pointer event manager** → spoofed
- **Text metrics** → spoofed

### Operational role

Fortress is the **browser engine layer** in a stack that looks like:

```
Your automation code (scraper / AI agent)
  → Playwright / Puppeteer / CDP client
    → Fortress (stealth Chromium engine, CDP on :9222)
      → Residential/mobile proxy egress
        → Target website
```

It solves **Layer C** (fingerprint surface) of the three-layer bot-detection model:
- **Layer A** (driver/binary artifacts): solved by driving raw CDP instead of chromedriver
- **Layer B** (CDP side-effects): solved by avoiding `Runtime.enable` leaks
- **Layer C** (fingerprint surface): **this is Fortress** — C++-level spoofing

---

## Why this was built

### The real problem

Browser automation (scraping, AI agents, testing) is increasingly blocked by anti-bot systems (Cloudflare, DataDome, Kasada, HUMAN, Akamai). These systems don't just check IP reputation — they read the browser fingerprint to distinguish automated browsers from real users. Existing stealth approaches fail structurally:

1. **JavaScript stealth patches self-reveal.** `puppeteer-stealth`, `undetected-chromedriver`, and similar tools override getters from JavaScript. Detectors can:
   - Call `.toString()` on the overridden getter and see the override source code instead of `[native code]`
   - Grab a pristine `Function.prototype.toString` from an iframe or Web Worker (realm re-acquisition) and turn it on the main-world override
   - Check `hasOwnProperty` on tampered functions
   - Test `TypeError` behavior on wrong `this` — native getters throw a specific error, naive shims stay quiet

2. **Commercial stealth browsers are closed-source.** Multilogin, Kameleo, GoLogin, AdsPower, Browserbase, Surfsky all recompile Chromium behind closed doors. You get a binary and must trust it — you cannot audit the patches, verify what surfaces are corrected, or rebuild from source. The latest major version is often paywalled.

3. **Camoufox forks Firefox (~3% of web traffic).** A Firefox user-agent on a Chrome-dominated web is a standing anomaly. The TLS shape (JA3/JA4) doesn't match Chrome, and many sites optimize for Chromium.

4. **No open, auditable, rebuildable Chromium stealth engine existed.** The prior art (`fingerprint-chromium`, `ChromiumFish`, CloakBrowser) was partial, unmaintained, or closed. The community needed a fork where every surface correction is a readable diff, the whole engine rebuilds from source with one script, and the gauntlet gates every release.

### What triggered development

The rise of sophisticated anti-bot systems (especially Cloudflare Turnstile, Akamai Bot Manager, and DataDome) made JS-level stealth patches increasingly ineffective. AI agent frameworks (browser-use, Crawl4AI, Stagehand, LangChain) created new demand for undetectable browser automation. The existing solutions were either:
- **Fragile** (JS patches that break on detector updates)
- **Closed** (proprietary binaries you can't audit)
- **Mismatched** (Firefox-based stealth on a Chrome web)

Fortress was built to fill this gap with an open, auditable, rebuildable Chromium engine.

### How it fits the JorahOne ecosystem

Fortress is **infrastructure for undetected browser automation**. Within the JorahOne ecosystem, it serves as the browser engine that powers:
- **Web scraping pipelines** that need to bypass bot detection at scale
- **AI agent systems** (browser-use, Crawl4AI, etc.) that drive browsers autonomously
- **Automated testing** of sites protected by anti-bot systems
- **Data collection** from sites that block headless/automated browsers

It is a **foundational dependency** — the browser layer that makes all higher-level automation invisible to anti-bot systems. Without it, automation code running on stock Chromium or Playwright gets flagged immediately by modern detectors.

---

## Key design decisions

| Decision | Rationale |
|---|---|
| **C++ patches, not JS** | JS overrides self-reveal via `toString` and realm re-acquisition; C++ getters are indistinguishable from native code across all realms |
| **Raw CDP, not chromedriver** | ChromeDriver leaves `cdc_` variables and WebDriver protocol surface; raw CDP has no such artifacts |
| **35 small single-purpose patches** | Each patch is readable in a minute; most re-apply cleanly across Chromium version bumps; the series is the source of truth |
| **Monthly Chromium rebase** | Detection moves fast; a stale engine is a detectable engine |
| **Gauntlet-gated releases** | Every release must pass CreepJS, Sannysoft, and BrowserScan before shipping |
| **Default Windows persona** | Windows is the most common desktop platform; a Windows fingerprint on any OS is fine for JS surfaces |
| **Persona on command line (v1)** | Simple, explicit, one persona per process; v2 MaskConfig will deliver personas over IPC for zero cmdline footprint |
| **SHA-256-verified downloads** | Every SDK verifies the binary against the release SHA256SUMS before launching |
| **BSD-3 license** | Matches Chromium's license; fully open, self-hostable, rebuildable |

---

## Operational classification

**Production.** Fortress ships through four official channels (Docker, PyPI, npm, portable binaries) with a monthly release cadence, CI-gated gauntlet, and reproducible builds. It is actively maintained with upstream Chromium rebases and patch updates.

---

## Repository layout

```
patches/      35 per-surface C++ patches (+ series file) — the source of truth
build/        args.gn, build.sh, apply-patches.sh, rebase-monthly.sh
packaging/    tilion launcher, fonts.conf, Dockerfile, .deb + bundle builders
fonts/        33 metric-compatible Windows-named fonts (incl. color emoji)
sdk/          python + node (tilion-fortress) prebuilt-binary SDKs
tools/        gauntlet.py — the CreepJS / Sannysoft / BrowserScan CI gate
docs/         GAUNTLET_RESULTS, BUILD_NATIVE, BENCHMARK
```

---

## Limitations (explicitly stated in the repo)

- Fortress hardens the **browser fingerprint only**. IP reputation and automation behavior are still the caller's responsibility.
- The persona lives on the command line (`/proc/<pid>/cmdline`) in v1 — visible to other processes on the host.
- macOS falls back to Docker (no native binary yet).
- Detection keeps moving — the gauntlet is dated and the engine is only as good as its last rebase.
- The word "undetectable" is deliberately excluded from the repo.
