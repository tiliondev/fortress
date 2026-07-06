# Phase 2 — ARCHITECT

**Repository:** `fortress` (tiliondev/fortress)
**Date:** 2026-07-05
**Analyst:** J1-PIPELINE ARCHITECT

---

## Architecture Overview

Fortress is a **stealth Chromium fork** — a set of C++ patches applied to a pinned Chromium checkout that correct browser fingerprint surfaces at the engine level. It exposes a raw Chrome DevTools Protocol (CDP) endpoint, making it a drop-in replacement for any CDP-based automation tool.

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CONSUMPTION LAYER                         │
│  Playwright / Puppeteer / browser-use / Crawl4AI / Stagehand │
│  ─── connect_over_cdp("http://localhost:9222") ─────────────  │
└──────────────────────────┬──────────────────────────────────┘
                           │ CDP WebSocket
┌──────────────────────────▼──────────────────────────────────┐
│                    CDP ENDPOINT LAYER                        │
│  socat bridge (Docker: 0.0.0.0:9222 → 127.0.0.1:9223)      │
│  OR direct binding (native: 127.0.0.1:9222)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    FORTRESS BINARY LAYER                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  tilion launcher (packaging/tilion)                   │   │
│  │  Applies --uxr-* persona flags → spawns chrome        │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Chromium (patched)                                  │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  UxrConfig Singleton (base/uxr_config.*)     │   │   │
│  │  │  Process-global C++ config, populated from    │   │   │
│  │  │  --uxr-* flags or IPC                         │   │   │
│  │  └──────────┬──────────────────┬─────────────────┘   │   │
│  │             │                  │                       │   │
│  │  ┌──────────▼──────────┐  ┌───▼──────────────────┐   │   │
│  │  │  Blink Patches     │  │  V8 Patches          │   │   │
│  │  │  (navigator,       │  │  (canvas, WebGL,     │   │   │
│  │  │   screen, fonts,   │  │   audio, WebGPU,     │   │   │
│  │  │   timezone, etc.)  │  │   text metrics)      │   │   │
│  │  └────────────────────┘  └──────────────────────┘   │   │
│  │  ┌────────────────────┐  ┌──────────────────────┐   │   │
│  │  │  BoringSSL Patches │  │  Content/Patches     │   │   │
│  │  │  (TLS shape)       │  │  (UA, platform,      │   │   │
│  │  │                     │  │   WebRTC, CDP)       │   │   │
│  │  └────────────────────┘  └──────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    BUILD LAYER                               │
│  depot_tools → fetch Chromium tag → apply patches →         │
│  gn gen → ninja → stripped official binary                  │
│  build/build.sh, build/apply-patches.sh, build/args.gn      │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    PACKAGING LAYER                           │
│  Docker image (multi-stage, Debian-based)                   │
│  Portable bundle (tar.gz for Linux, zip for Windows)        │
│  .deb package (Debian/Ubuntu)                               │
│  SDK packages (PyPI: tilion-fortress, npm: tilion-fortress) │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

### 1. C++ Patches, Not JavaScript Injection
**Decision:** All fingerprint corrections are applied as C++ patches to Chromium's source tree.
**Rationale:** JavaScript overrides self-reveal via `toString()` and realm re-acquisition (iframe/worker). C++ getters are indistinguishable from native code across all realms.
**Risk:** Requires a full Chromium rebuild for every change. Mitigated by single-surface patches that re-apply cleanly across version bumps.

### 2. Single-Surface Patch Design
**Decision:** Each patch touches exactly one file (one `diff --git`).
**Rationale:** Rebases stay legible; each patch is readable in a minute; the series is the source of truth.
**Risk:** 35 patches means 35 potential merge conflicts on rebase. Mitigated by small, focused diffs.

### 3. UxrConfig Singleton Pattern
**Decision:** A process-global C++ singleton (`base/uxr_config.*`) read by every patched surface.
**Rationale:** Single source of truth for persona configuration. Populated from `--uxr-*` command-line flags.
**Risk:** The persona lives on the command line (`/proc/<pid>/cmdline`) in v1 — visible to other processes. The v2 MaskConfig will deliver personas over IPC.

### 4. Raw CDP, Not ChromeDriver
**Decision:** Expose raw CDP on `:9222` instead of using ChromeDriver.
**Rationale:** ChromeDriver leaves `cdc_` variables and WebDriver protocol surface that detectors read. Raw CDP has no such artifacts.
**Risk:** The CDP channel itself can leak automation signals (e.g., `Runtime.enable`). Mitigated by avoiding `Runtime.enable` and using `Runtime.addBinding` + isolated worlds.

### 5. Default Windows Persona
**Decision:** The default persona is a coherent Windows identity.
**Rationale:** Windows is the most common desktop platform. A Windows fingerprint on any OS is fine for JS surfaces.
**Risk:** TLS shape and some OS-facing signals follow the machine underneath. Mitigated by matching persona to egress OS.

### 6. Monthly Chromium Rebase
**Decision:** Track the latest Chromium stable monthly.
**Rationale:** Detection moves fast; a stale engine is a detectable engine.
**Risk:** Monthly rebase is labor-intensive. Mitigated by single-surface patches that re-apply cleanly.

### 7. Gauntlet-Gated Releases
**Decision:** Every release must pass CreepJS, Sannysoft, and BrowserScan before shipping.
**Rationale:** Empirical verification against live detectors is the only reliable test.
**Risk:** Detectors change their behavior between runs. Mitigated by dated, reproducible gauntlet results.

### 8. Zero Runtime Dependencies for SDKs
**Decision:** Both Python and Node SDKs use pure stdlib — no external packages.
**Rationale:** Minimal attack surface, no supply chain risk, instant install.
**Risk:** More code to maintain. Mitigated by small, focused SDKs.

### 9. De-branded Switch Prefix
**Decision:** All runtime overrides use the `--uxr-*` prefix (neutral token).
**Rationale:** The binary carries no product string a detector could match.
**Risk:** None — this is a well-executed design choice.

### 10. Docker socat Bridge
**Decision:** Docker container runs Chrome on internal port 9223, bridges to 9222 via socat.
**Rationale:** Chromium 151 binds DevTools to 127.0.0.1 only. Docker port forwarding goes to the container's veth IP, not localhost. socat bridges the gap.
**Risk:** socat is an additional process. Mitigated by `dumb-init` for proper signal handling.

---

## Patch Surface Map

| # | File | Surface | Layer |
|---|------|---------|-------|
| 0001 | `base/BUILD.gn` | Build config for UxrConfig | Build |
| 0002 | `base/uxr_config.cc` | UxrConfig implementation | Core |
| 0003 | `base/uxr_config.h` | UxrConfig header | Core |
| 0004 | `components/embedder_support/user_agent_utils.cc` | User-Agent string | Content |
| 0005 | `content/browser/renderer_host/render_process_host_impl.cc` | Render process UA injection | Content |
| 0006 | `content/common/renderer.mojom` | IPC for UA hints | Content |
| 0007 | `content/renderer/render_thread_impl.cc` | Render thread UA setup | Content |
| 0008 | `content/renderer/render_thread_impl.h` | Render thread header | Content |
| 0009 | `content/renderer/renderer_main.cc` | Renderer main entry | Content |
| 0010 | `third_party/blink/renderer/core/dom/element.cc` | DOM element | Blink |
| 0011 | `third_party/blink/.../navigator_base.cc` | Navigator base | Blink |
| 0012 | `third_party/blink/.../local_dom_window.cc` | DOM window | Blink |
| 0013 | `third_party/blink/.../navigator.cc` | Navigator | Blink |
| 0014 | `third_party/blink/.../navigator_concurrent_hardware.cc` | hardwareConcurrency | Blink |
| 0015 | `third_party/blink/.../navigator_device_memory.cc` | deviceMemory | Blink |
| 0016 | `third_party/blink/.../navigator_id.cc` | navigator ID | Blink |
| 0017 | `third_party/blink/.../navigator_language.cc` | navigator.languages | Blink |
| 0018 | `third_party/blink/.../screen.cc` | Screen dimensions | Blink |
| 0019 | `third_party/blink/.../timezone_controller.cc` | Timezone | Blink |
| 0020 | `third_party/blink/.../base_rendering_context_2d.cc` | Canvas 2D | Blink |
| 0021 | `third_party/blink/.../keyboard_layout.cc` | Keyboard layout | Blink |
| 0022 | `third_party/blink/.../media_devices.cc` | Media devices | Blink |
| 0023 | `third_party/blink/.../network_information.cc` | Network info | Blink |
| 0024 | `third_party/blink/.../peer_connection_dependency_factory.cc` | WebRTC | Blink |
| 0025 | `third_party/blink/.../speech_synthesis.cc` | Speech synthesis | Blink |
| 0026 | `third_party/blink/.../audio_buffer.cc` | Audio buffer | Blink |
| 0027 | `third_party/blink/.../audio_buffer.h` | Audio buffer header | Blink |
| 0028 | `third_party/blink/.../realtime_analyser.cc` | Audio analyser | Blink |
| 0029 | `third_party/blink/.../webgl_rendering_context_base.cc` | WebGL | Blink |
| 0030 | `third_party/blink/.../gpu_adapter_info.cc` | WebGPU | Blink |
| 0031 | `third_party/blink/.../image_data_buffer.cc` | Image data | Blink |
| 0032 | `third_party/blink/.../pointer_event_manager.cc` | Pointer events | Blink |
| 0033 | `third_party/blink/.../text_metrics.cc` | Text metrics | Blink |
| 0034 | `third_party/blink/.../storage_manager.cc` | Storage quota | Blink |
| 0035 | `webgl2/getparameter/version/normalize` | WebGL2 version | Blink |

---

## Data Flow

```
1. User launches Fortress (Docker, pip, npm, or portable binary)
2. tilion launcher reads --uxr-* flags (or defaults)
3. UxrConfig singleton is populated from flags
4. Chromium starts with patched surfaces
5. Each patched surface reads UxrConfig for spoof values
6. CDP endpoint becomes available on :9222
7. User connects via Playwright/Puppeteer/CDP client
8. Target website's detector reads fingerprint surfaces
9. Patched surfaces return spoofed values (native C++ getters)
10. Detector sees a normal Chrome install → passes
```

---

## Architecture Score

| Criterion | Score | Notes |
|-----------|-------|-------|
| Separation of concerns | 95/100 | Clean layers: patches, build, packaging, SDKs |
| Single responsibility | 90/100 | Each patch touches one surface |
| Testability | 85/100 | Gauntlet for integration; unit tests for SDK |
| Maintainability | 90/100 | Small patches, clear naming, good docs |
| Extensibility | 85/100 | Adding a new surface = new patch + new --uxr- flag |
| Security posture | 80/100 | De-branded, no runtime deps, non-root Docker |
| Documentation | 95/100 | Excellent README, AGENTS.md, CONTRIBUTING, SECURITY |
| **Overall** | **89/100** | |

---

## Architecture Concerns

1. **Command-line persona visibility (v1)** — The `--uxr-*` flags are world-readable via `/proc/<pid>/cmdline`. The v2 MaskConfig (IPC-delivered) is planned but not yet implemented. This is a known, documented limitation.

2. **Docker socat bridge** — The socat bridge adds complexity and a potential failure point. It's a workaround for Chromium's 127.0.0.1-only binding. A cleaner solution would be to patch Chromium to accept `--remote-debugging-address`.

3. **35 patches on rebase** — While each patch is single-surface, 35 patches means 35 potential merge conflicts on every monthly Chromium rebase. The project's migration to Brave-style `chromium_src/` overrides (on the roadmap) would eliminate this entirely.

4. **No macOS/Windows native binaries yet** — macOS falls back to Docker. Windows native builds exist but are not yet the default. This limits the user experience on those platforms.

5. **SDK version decoupling** — The Python SDK version (`151.0.7908.0.post1`) is decoupled from the engine tag (`v151.0.7908.0`). This is intentional but could cause confusion if the SDK and engine get out of sync.
