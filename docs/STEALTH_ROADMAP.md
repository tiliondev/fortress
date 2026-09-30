# Fortress — Stealth Hardening & Cross-Platform Roadmap

Synthesis of a 5-agent deep-research pass (2026-06-24). Every claim is sourced; the priorities are
ranked by **real detection impact in 2025-2026**, not by how interesting the engineering is.

## The one-paragraph strategic picture

The browser-fingerprint war is **largely won** — Fortress already scores 0% CreepJS / Sannysoft-clean /
BrowserScan-"Normal", and its **C++ (non-JS-injection) approach is a genuine moat** that beats the
prototype-poisoning / "this-is-a-stealth-library" detection that kills puppeteer-stealth. The remaining
**~90% of real-world block risk now lives in three places that are NOT more fingerprint patches**:

1. **Egress IP** (datacenter ASN) — the single biggest needle-mover. *Config, not code.*
2. **The CDP driver channel** (how Tillion talks to the browser) — `Runtime.enable` & friends leak regardless of how good the binary is. *Driver layer, not engine.*
3. **Human behavior** (mouse/keystroke/scroll biometrics + PoW timing) — the deciding signal for HUMAN/DataDome-enterprise/Kasada. *Driver + a few engine input patches.*

Two myths to kill: **(a) the network layer (TLS/HTTP-2/QUIC) is a NON-gap** — being real Chromium, Fortress emits a genuine Chrome JA4/H2 fingerprint for free; hand-patching it would *create* a unique tell. **(b) More noise ≠ more stealth** — coherence across surfaces beats randomization (Brave concedes randomization alone still leaks).

---

## Priority matrix

| Pri | Item | Layer | Why | Effort |
|---|---|---|---|---|
| **P0** | Residential/mobile egress | Network/config | Datacenter IP = **71–78% block** regardless of fingerprint; residential → 14–22%, mobile → 4–9% | Low (creds) |
| **P0** | nodriver-style CDP client (no `Runtime.enable`) | Driver | Caught regardless of binary quality; nodriver beats Patchright on hardest CF targets *because* of this | Med |
| **P0** | WebGPU spoof, coherent with WebGL | Engine | New surface; cross-checked vs WebGL → mismatch = instant flag | Med |
| **P0** | Native-code integrity audit of the 31 patches | Engine | CreepJS lies-module checks `toString()===[native code]` + prototype chain of every getter | Low |
| **P0** | Gen-1 behavior (ghost-cursor + keystroke timing) | Driver | Deciding signal for behavior-ML vendors | Med |
| **P1** | plugins/mimeTypes, fonts-enumeration, permissions, battery, storage-quota, TextMetrics/getClientRects | Engine | The comprehensive-checker gap vs Camoufox/CloakBrowser | Med |
| **P1** | CDP input realism (coalesced pointer events, intermediate event chain, timing jitter) | Engine | The one behavior problem better solved in C++ | Med |
| **P1** | Per-OS persona coherence (UA↔platform↔WebGL↔fonts↔DPR) | Engine/launcher | Win persona must never emit Metal; Mac never D3D11 | Med |
| **P1** | Native Windows + macOS builds | Build | `pip install` / `npm install` on all OSes | High |
| **P1** | Decouple binary from SDK packages (download-on-install) | Distribution | Makes Win/Mac "just another asset" | Low |
| **P2** | TCP/IP (JA4T) OS alignment | Host/network | Linux host + Windows persona = JA4T mismatch (DataDome) | Med |
| **P2** | Gen-2 behavior (DMTG diffusion) | ML | Beats behavior-ML-first vendors; non-repeating trajectories | High |
| **P2** | WebGL ext-order/precision, Media Capabilities, Math/Date ULP, Intl full, worker/iframe consistency | Engine | Defense-in-depth | Med |

---

## 1. Network layer — DO NOT patch it (verified non-gap)

Because Fortress **is** real Chromium (BoringSSL + Chrome's `net/` stack), its **TLS JA4, HTTP/2 Akamai
fingerprint, and QUIC params are genuine current-Chrome by default**. This is the whole advantage over
`curl-impersonate`/uTLS, which *fake* it and constantly drift/CVE out.

- ❌ **Never hand-reorder TLS ciphers/extensions.** Chrome already permutes extension order per-connection and JA4 sorts before hashing — reordering changes nothing JA4-wise, but touching the cipher set moves you off the stable `8daaf6152771` cipher hash shared by all Chrome 120–151 → you become the *only* "Chrome" with that hash = instant unique bot signal.
- ✅ **Keep post-quantum on** (`X25519MLKEM768`, default since ~Chrome 124). A Chrome-131+ UA *without* the PQ key share is a hard tell — just don't disable it via flag/finch.
- ✅ **Keep spoofed UA version == the build's Chromium milestone** (ship 151 → claim 151). This is the only realistic way real-Chromium TLS/H2 can betray the persona.
- ✅ **Never put a TLS/H2-terminating (MITM) proxy in front** — use SOCKS/CONNECT pass-through so the browser's own handshake reaches the origin.
- ⚠️ **The real residual is TCP/IP (JA4T) + ASN**, both host/network not C++: a Linux host (TTL 64, Linux TCP option order) spoofing Windows mismatches JA4T. Fix by running Windows hosts when spoofing Windows, matching UA to host OS, or a TCP-normalizing egress.
- ✅ **Add a CI check**: after each rebase, assert JA4 == reference Chrome 151 at `tls.peet.ws` and the Akamai H2 string is unchanged. Catches accidental config drift.

Sources: [Cloudflare JA4 signals](https://blog.cloudflare.com/ja4-signals/), [FoxIO JA4](https://github.com/FoxIO-LLC/ja4), [Scrapfly PQ-TLS](https://scrapfly.io/blog/posts/post-quantum-tls-bot-detection), [send.win H2 2026](https://blog.send.win/http2-fingerprinting-browser-detection-browser-isolation-guide-2026/), [ja4db Chromium](https://www.ja4db.com/application/Chromium%20Browser).

## 2. Egress IP — the #1 needle-mover (config, not engine)

Datacenter ASN (Hetzner/AWS/OVH) is pre-classified low-trust *before request data is processed* and
shared across vendor block-lists within hours. Block rates on protected sites (2026): **datacenter 71–78%
· residential 14–22% · mobile 4–9%.** Recommendation: tiered egress — **ISP/static-residential** for easy
targets, **rotating residential** for CF/DataDome/Akamai, **mobile (4G/5G)** for the hardest +
behavior-ML targets. **Session stickiness is mandatory** for authenticated flows (lock IP 10 min–24 h);
avoid non-household request volume per IP.

Sources: [krowdev 2026](https://krowdev.com/article/bot-detection-2026/), [Techicy datacenter-IP 2026](https://www.techicy.com/the-anti-bot-arms-race-of-2026-why-datacenter-ips-are-becoming-useless.html), [DataDome bypass 2026](https://scrapebadger.com/blog/how-to-bypass-datadome-anti-bot-protection-a-complete-2026-guide).

## 3. CDP driver channel — fix in Tillion, NOT the engine

**Critical architectural point:** Fortress's clean binary is wasted if Tillion drives it like vanilla
Playwright. Most CDP tells are properties of *how the control layer talks CDP*, not the engine.

- The classic CDP `.stack`/`console.log` side-effect signal **died May 2025** (V8 `getErrorProperty()` skips user getters) — but a residual **prototype-Proxy `ownKeys` trap** variant still fires, so **still never call `Runtime.enable`**.
- **Architect Tillion's client nodriver-style:** use `Page.createIsolatedWorld` (not `Runtime.enable`); run all injected JS in isolated worlds; don't open `Console`/`Target` unnecessarily; strip `//# sourceURL`; no `__pwInitScripts`/`exposeFunction`/`bypassCsp`; realistic (non-default) viewport. Benchmark proof: nodriver 28/31 vs Cloudflare with zero blocked cells, beating Patchright — *because of the driver layer, not the binary.*

**Engine vs driver split:** Engine owns `navigator.webdriver=false`, UA tokens, `--enable-automation`
neutralization, and **input realism** (below). Driver owns everything in the `Runtime.enable`/isolated-world/
sourceURL/viewport list.

Sources: [Castle — CDP signal died](https://blog.castle.io/why-a-classic-cdp-bot-detection-signal-suddenly-stopped-working-and-nobody-noticed/), [rebrowser Runtime.enable](https://rebrowser.net/blog/how-to-fix-runtime-enable-cdp-detection-of-puppeteer-playwright-and-other-automation-libraries), [rebrowser-bot-detector](https://github.com/rebrowser/rebrowser-bot-detector), [Castle nodriver](https://blog.castle.io/from-puppeteer-stealth-to-nodriver-how-anti-detect-frameworks-evolved-to-evade-bot-detection/), [Paterson benchmark](https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi/).

## 4. Engine patch backlog (additions to the 31)

**P0**
- **WebGPU** (`navigator.gpu`): spoof `GPUAdapterInfo` (vendor/architecture/device/description), `GPUSupportedLimits`, features set, `isFallbackAdapter=false` — driven from the **same profile struct** as WebGL so they agree. C++: `modules/webgpu/gpu_adapter_info.cc`, `gpu_supported_limits.cc`.
- **Native-code integrity audit**: ensure every one of the 31 spoofs is a real C++ binding return (descriptor identical to stock), `toString()===[native code]`, Error.stack unchanged. CreepJS lies-count must be 0.
- **plugins/mimeTypes**: emit Chrome's 5-entry PDF plugin set with correct bidirectional `enabledPlugin` cross-refs + `pdfViewerEnabled=true`. C++: `core/frame/navigator_plugins.cc`.
- **CDP input realism** (the one behavior fix that belongs in C++): synthesize **coalesced pointer-event batches** (`getCoalescedEvents()`), the full intermediate pointer/mouse event chain (over/enter/move/down/up), and per-event timing jitter at the Blink dispatch layer. `isTrusted` is already true over CDP. (CloakBrowser's "4 input patches".)

**P1**
- TextMetrics + `getClientRects` + emoji/SVG geometry — **share the existing DOMRect seed** (`core/html/canvas/text_metrics.cc`, `Element::getClientRects`).
- Font **enumeration** whitelist matching the spoofed OS (distinct from metric noise) — `core/css/font_face_set_document.cc`.
- Permissions defaults + contradictory-state fix (no headless "denied-while-prompt").
- Battery API (coherent static values), storage-quota normalization (incognito defeat).
- WebGL extension-list **order** + shaderPrecisionFormats + contextAttributes + EXT_disjoint_timer_query.

**P2**: Media Capabilities matrix, devicePixelRatio↔screen↔window coherence + `screen.availTop/availLeft`
(taskbar), worker/iframe cross-context consistency (re-probe agreement), CSS system/computed styles +
headless `ActiveText` default, performance.memory, navigator.userActivation, Gamepad/Sensors absence,
Intl full `resolvedOptions`, Math/Date ULP, speech-voice realism flags.

**Governing principle: single-source coherence** — every surface driven from one profile struct so
WebGL↔WebGPU, screen↔DPR↔window, UA↔platform↔plugins↔fonts all tell the same story.

Sources: [Camoufox properties](https://github.com/daijro/camoufox/blob/main/settings/properties.json), [CloakBrowser](https://github.com/CloakHQ/CloakBrowser), [CreepJS](https://github.com/abrahamjuliot/creepjs), [WebGPU FP](https://botbrowser.io/en/blog/webgpu-fingerprinting/), [Brave defenses 2.0](https://brave.com/privacy-updates/4-fingerprinting-defenses-2.0/).

## 5. Behavior layer (driver + ML)

- **Gen-1 (ship now):** port **ghost-cursor** — cubic Bézier paths (control points biased off-line), Fitts's-law duration, bell-curve velocity, overshoot+readjust >500px, in-element offset (not center), session fatigue; keystroke dwell/flight sampled log-normal; pre-click hover dwell. Drive over CDP `Input`. Beats DataDome's general classifier today.
- **Gen-2 (roadmap):** DMTG entropy-controlled diffusion (DDIM U-Net, trained SapiMouse + Open Images, α≈0.2–0.3) — captures directional-acceleration asymmetry + slow initiation, **non-repeating trajectories per run** (defeats replay/clustering), drops detector accuracy 4.75–9.73% vs SapiAgent. Keep the generator pluggable behind one `generate()→events` interface so Gen-2 swaps in cleanly. (This is the **Turing** solver's behavior moat.)
- **PoW timing (Kasada/Turnstile):** *solving too fast flags you.* Run the PoW **inside the real Fortress browser** so timing is inherently browser-realistic; if out-of-band, match a mid-range consumer-CPU distribution with jitter.

Sources: [ghost-cursor](https://github.com/Xetera/ghost-cursor), [DMTG arXiv:2410.18233](https://arxiv.org/abs/2410.18233), [SapiMouse](https://www.researchgate.net/publication/354428956_SapiAgent_A_Bot_Based_on_Deep_Learning_to_Generate_Human-Like_Mouse_Trajectories), [Kasada PoW timing](https://www.kernel.sh/blog/detection), [ZenRows DataDome mouse-curvature](https://www.zenrows.com/blog/datadome-bypass).

## 6. Native Windows & macOS builds

**Patches are OS-agnostic** (Blink/content C++) and apply on all platforms via `git apply --3way`. The hard
part is the build host.

**Windows:** VS 2022 Build Tools (`VCTools` + `ATLMFC`) + matching Win SDK (incl. Debugging Tools),
depot_tools, `DEPOT_TOOLS_WIN_TOOLCHAIN=0`, `core.autocrlf=false`. ~150–200 GB NTFS, 32 GB RAM, 2–6 h.
- **Standard GitHub runners = dead end** (14 GB disk can't hold the checkout). Use **larger runners** (cost) or a **self-hosted Windows box** (keeps checkout warm → incremental builds in minutes).
- **Cross-compile from Linux** (`win_cross.md`) is viable for iteration but loses Crashpad/PDBs + has case-sensitivity pitfalls → **ship the release artifact from a native Windows build**.

**macOS:** full Xcode + matching SDK. Build **two thin per-arch slices** (`arm64`, `x64`) — not a fat
universal binary. **codesign (Developer ID, hardened runtime) → `notarytool submit --wait` → `stapler
staple`**, or Gatekeeper blocks it ("app is damaged"). 14 GB runner disk + 10× minute multiplier make
hosted CI painful → **self-hosted Apple Silicon Mac** (arm64 native + x64 cross slice on the same box).
- **Cross-compile macOS from Linux = dead end** (no redistributable SDK; can't run codesign/notarytool off a Mac). You need a Mac.

Sources: [Chromium win build](https://chromium.googlesource.com/chromium/src/+/main/docs/windows_build_instructions.md), [win_cross](https://chromium.googlesource.com/chromium/src.git/+/master/docs/win_cross.md), [notarytool](https://tonygo.tech/blog/2023/notarization-for-macos-app-with-notarytool), [GHA runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

## 7. pip / npm distribution (download-on-install, copy Camoufox/Playwright)

**Decision: decouple the binary from the language packages.** Don't embed a 300 MB binary in fat wheels —
ship thin packages that download a versioned binary from GitHub Releases (under the 2 GB/asset limit per
platform).

- **Python (`tillion-fortress`):** one pure `py3-none-any` wheel + a `fortress fetch` CLI (and lazy
  auto-fetch) that detects `linux-x64`/`win-x64`/`mac-arm64`/`mac-x64`, downloads `fortress-<ver>-<plat>.tar.xz`
  from the pinned Release, **verifies SHA256** vs a `SHA256SUMS` asset, extracts to the OS cache
  (`~/.cache/tillion-fortress/<ver>/`, `~/Library/Caches/...`, `%LOCALAPPDATA%\...`). Env overrides
  (Playwright-style): `FORTRESS_DOWNLOAD_HOST`, `FORTRESS_BROWSERS_PATH`, `FORTRESS_SKIP_DOWNLOAD`. Pin
  binary version to package version. Optional extras like `tillion-fortress[geoip]`.
- **Node (`@tillion/fortress`):** thin package + same detect→download→verify→cache flow via `postinstall`
  (and `npx tillion-fortress fetch` for `--ignore-scripts`). Prefer this over the `optionalDependencies`
  per-platform-package model so the binary lives **only** in GitHub Releases (one source of truth for both
  ecosystems).
- The current `sdk/python` + `sdk/node` already implement the download-on-install pattern — extend their
  platform matrix to win/mac and add SHA256SUMS verification.

Sources: [Playwright browsers](https://playwright.dev/docs/browsers), [Camoufox PyPI](https://pypi.org/project/camoufox/), [@puppeteer/browsers](https://pptr.dev/browsers-api), [esbuild optionalDeps](https://github.com/evanw/esbuild/issues/789), [GH release size limit](https://github.com/orgs/community/discussions/196657).

## 8. Per-OS persona coherence (add to the launcher)

Add an `os` dimension that drives a coherent bundle so cross-OS leaks can't happen:

| Surface | Linux | Windows | macOS |
|---|---|---|---|
| WebGL/WebGPU renderer | GL/SwiftShader/Vulkan | `ANGLE … Direct3D11` | `ANGLE Metal … Apple Mx` |
| Fonts | bundled (fontconfig) | system Segoe UI set | system SF set |
| `navigator.platform` / uaData | `Linux x86_64` | `Win32`/"Windows" | `MacIntel`/"macOS" |
| DPR / screen | varies | 1.0–1.5 | Retina 2.0 |
| libvulkan.so.1 / SwiftShader | needed | n/a | n/a |

A macOS persona must **never** emit Direct3D; a Windows persona must **never** emit Metal — the #1 cross-OS
leak. Bundle per-OS font sets (Camoufox model). Sources: [Castle WebGL renderer](https://blog.castle.io/the-role-of-webgl-renderer-in-browser-fingerprinting/), [Camoufox fingerprint](https://camoufox.com/fingerprint/).

## 9. Release automation

Tag `v<chromium>-fortress.N` → CI matrix (`linux-x64`, `win-x64`, `mac-arm64`, `mac-x64`; self-hosted for
builds) → each job checks out the pinned 151 src, `git apply --3way patches/*`, `gn gen` + `autoninja`,
(mac: codesign+notarize+staple), tar/zip + `sha256sum` → `gh release` with assets + `SHA256SUMS` → publish
PyPI (Trusted Publishing/OIDC) + npm (`--provenance`) in one flow. The committed
`.github/workflows/build-fortress.yml` is the starting skeleton.

---

## Sequenced execution (what to do, in order)

1. **Residential/mobile egress** (P0, config) — biggest single win; unblocks the real CAPTCHA demo too.
2. **nodriver-style Tillion CDP client** (P0, driver) — no `Runtime.enable`, isolated worlds.
3. **Gen-1 behavior module** (P0, driver) — ghost-cursor + keystroke timing over CDP `Input`.
4. **Engine P0 patches** — WebGPU (coherent), native-code audit, plugins/mimeTypes, CDP input realism.
5. **Decouple SDK ↔ binary** + extend platform matrix (distribution).
6. **Self-hosted Windows + Mac build hosts** → native builds → Release assets → `pip`/`npm` cross-platform.
7. **Engine P1/P2 backlog** to Camoufox/CloakBrowser parity (coherence-first).
8. **Gen-2 DMTG behavior** (Turing solver moat).

**Bottom line:** stop adding fingerprint noise; the leverage is **egress IP + driver channel + behavior +
a handful of coherence-preserving engine patches (WebGPU, plugins, input realism)**. Network stays
untouched — being real Chromium *is* the moat there.
