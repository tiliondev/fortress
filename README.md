<div align="center">

<img alt="Fortress" src="docs/assets/banner-fortress.png" width="100%">


### Stealth Chromium engine

**Stop getting blocked — without `puppeteer-stealth`.** JS stealth patches self-reveal: the page checks whether the getter is native code and catches the override. Fortress compiles the fingerprint correction into Chromium's **C++**, so a page inspecting itself sees stock Chrome. Drop it in under the Playwright or Puppeteer you already use.

<sub>**Blink · V8 · BoringSSL** patched in-tree · **ANGLE / D3D11**-backed WebGL · **JA3/JA4-coherent** TLS · **monthly** upstream rebase · **reproducible, gauntlet-gated** releases</sub>

[![Chromium](https://img.shields.io/badge/chromium-151.0.7908.0-4285F4?logo=googlechrome&logoColor=white)](CHROMIUM_VERSION)
[![PyPI](https://img.shields.io/pypi/v/tilion-fortress?logo=pypi&logoColor=white&label=pip)](https://pypi.org/project/tilion-fortress/)
[![npm](https://img.shields.io/npm/v/tilion-fortress?logo=npm&label=npm)](https://www.npmjs.com/package/tilion-fortress)
[![Docker Pulls](https://img.shields.io/docker/pulls/tilion/fortress?logo=docker&logoColor=white&label=docker%20pulls)](https://hub.docker.com/r/tilion/fortress)
[![CreepJS](https://img.shields.io/badge/CreepJS-0%25%20headless-2ea44f)](docs/GAUNTLET_RESULTS.md)
[![Runtime.enable leak](https://img.shields.io/badge/Runtime.enable-no%20leak-2ea44f)](docs/GAUNTLET_RESULTS.md)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue)](LICENSE)
[![Stars](https://img.shields.io/github/stars/tiliondev/fortress?style=social)](https://github.com/tiliondev/fortress/stargazers)

<table align="center"><tr>
<td align="center" width="150"><h3>34</h3><sub>single-surface<br/>C++ patches</sub></td>
<td align="center" width="150"><h3>0%</h3><sub>CreepJS<br/>headless / stealth</sub></td>
<td align="center" width="160"><h3><code>[native&nbsp;code]</code></h3><sub>across every<br/>realm</sub></td>
<td align="center" width="150"><h3>BSD-3</h3><sub>open engine,<br/>rebuild it yourself</sub></td>
</tr></table>

<img src="docs/assets/demo.gif" alt="Fortress clearing a live Cloudflare challenge, then passing sannysoft and BrowserScan" width="720"/>

<sub><i>Unedited capture of the Fortress binary in a real window: it clears a live <b>Cloudflare</b> challenge, turns <b>bot.sannysoft.com</b> all green, then reads <b>BrowserScan</b> “Normal”. Reproduce with <code>tools/gauntlet.py</code>.</i></sub>

<br/>

<a href="#install--use">Install</a> · <a href="#why-an-engine-fork-js-injection-is-self-revealing">Why an engine</a> · <a href="#how-fortress-compares">Compare</a> · <a href="#detection-results-official-binary-chromium-151">Results</a> · <a href="#build-from-source">Build</a> · <a href="#faq">FAQ</a>

</div>

<table>
<tr>
<td width="33%" valign="top">

#### Native-code parity
Every spoofed getter *is* a C++ getter — `toString` returns `[native code]`, **realm-invariant** across main frame, iframes, and Web Workers.

</td>
<td width="33%" valign="top">

#### Drop-in CDP
**nodriver-style** raw CDP on `:9222` — no `Runtime.enable` leak. Keep Playwright, Puppeteer, or any CDP client; swap the browser, keep your code.

</td>
<td width="33%" valign="top">

#### Clears the gauntlet
**0% headless** on CreepJS; Sannysoft, BrowserScan, and live Cloudflare Turnstile cleared — as a stock Chrome install.

</td>
</tr>
<tr>
<td width="33%" valign="top">

#### Auditable patches
34 small single-purpose diffs in `patches/`. Read one in a minute; rebuild the engine with one script.

</td>
<td width="33%" valign="top">

#### Coherent by construction
Real V8, Blink, and BoringSSL keep engine, user-agent, and **JA3/JA4 TLS shape** in agreement — a Windows persona on a matching stack.

</td>
<td width="33%" valign="top">

#### Coherent persona
One binary, a **coherence-checked** Windows identity; `--uxr-*` switches override any surface — GPU, screen, timezone, hardware, Client-Hints.

</td>
</tr>
</table>

### What it is
Fortress is a Chromium fork that corrects the browser fingerprint surfaces bot detectors read (canvas, WebGL, audio, fonts, navigator, and about thirty more) in the engine's C++. It ships as an ordinary binary with a CDP endpoint, so you keep Playwright, Puppeteer, or any CDP client and point it at Fortress. Swap the browser, keep your code.

JavaScript stealth has a ceiling. Tools like puppeteer-stealth overwrite properties after the page loads, but a detector checks whether the function returning a value is native code. An injected override gives itself away: `.toString()` shows its source, and re-grabbing the same primitive from an iframe or worker reaches a realm past the patch's reach. The extra layer is the tell.

Fortress moves the correction into the engine, so `navigator.vendor` resolves to the real C++ getter. It reports `[native code]` and reads the same across the main frame, iframes, and workers. A page inspecting itself sees stock Chromium.

In practice your scraper or agent gets blocked less. It clears CreepJS, Sannysoft, BrowserScan, and live Cloudflare Turnstile as a normal Chrome install, and whatever blocking is left traces to your proxies and behavior.

```python
from tilion_fortress import Fortress
from playwright.sync_api import sync_playwright

with Fortress() as f:                                   # launches the stealth engine on a CDP endpoint
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f.cdp_url)
        page = browser.new_page()
        page.goto("https://bot.sannysoft.com")
        page.screenshot(path="all-green.png")
```
```js
import { Fortress } from "tilion-fortress";
import { chromium } from "playwright";

const f = await Fortress.launch();                      // stealth engine on a CDP endpoint
const browser = await chromium.connectOverCDP(f.cdpUrl);
const page = await browser.newPage();
await page.goto("https://browserscan.net");
await browser.close();
await f.close();
```

---

### Install & use

<div align="center"><img src="docs/assets/install-strip.svg" alt="pip install tilion-fortress — CreepJS 0%, Sannysoft all-green, BrowserScan human" width="100%"/></div>

```bash
# Python / Node: prebuilt binary auto-fetched (Linux x64) or Docker (macOS/Windows)
pip install tilion-fortress
npm  install tilion-fortress

# Any OS via Docker: raw CDP on :9222  (~302 MB pull / 851 MB on disk, stripped)
docker run --rm -p 9222:9222 tilion/fortress:latest

# Portable tarball (Linux x64): use it like a Chromium snapshot
tar xzf tilion-fortress-linux-x64.tar.gz
./tilion-fortress/tilion https://example.com
./tilion-fortress/tilion --headless=new --remote-debugging-port=9222 --user-data-dir=/tmp/p

# Debian / Ubuntu
sudo apt install ./tilion-fortress_151.0.7908.0_amd64.deb && tilion https://example.com
```

> [!TIP]
> The SDK ships the compiled build **plus `patches/`**, so you can rebuild the engine yourself and verify every surface correction against the source.

#### The persona (`--uxr-*` switches)

The binary carries zero brand strings; the launcher applies a coherent default Windows persona.
Override any surface, or set `TILION_NO_DEFAULTS=1` for a bare launch.

```
--uxr-platform / --uxr-ua-platform / --uxr-ua-os / --uxr-ua-arch / --uxr-ua-bitness
--uxr-ua-platform-version / --uxr-ua-brand / --uxr-hw-concurrency / --uxr-device-memory
--uxr-webgl-vendor / --uxr-webgl-renderer / --uxr-webgl-fullparams
--uxr-canvas-seed / --uxr-audio-seed / --uxr-timezone / --uxr-languages
--uxr-screen-width / --uxr-screen-height / --uxr-webrtc-policy=disable_non_proxied_udp
```

| Env var | Purpose |
|---|---|
| `TILION_NO_DEFAULTS=1` | Skip the default persona (bare launch) |
| `TILION_TZ` / `TILION_LANG` | Quick timezone / language override |

> [!NOTE]
> **Architecture in motion — persona transport v2.** Today the persona is delivered through `--uxr-*`
> switches, world-readable via `/proc/<pid>/cmdline` (a process-level artifact, one persona per launch).
> Shipping next: an **IPC-delivered, seed-driven persona graph** feeding a process-global C++
> `MaskConfig` singleton (the Camoufox model) — one binary, thousands of **coherence-invariant**
> fingerprints, **per-`BrowserContext` identity isolation**, and **zero footprint on the command line**.

---

### Works with your stack
Fortress exposes raw CDP on `:9222`, so it drops in under anything that speaks Playwright, Puppeteer,
or CDP. Keep your framework, swap the browser.

| | connect via |
|---|---|
| [**browser-use**](https://github.com/browser-use/browser-use) (~70k stars) | `cdp_url="http://localhost:9222"` |
| [**Crawl4AI**](https://github.com/unclecode/crawl4ai) (~58k stars) | CDP endpoint |
| [**Stagehand**](https://github.com/browserbase/stagehand) (~21k stars) | `connectOverCDP` |
| [**LangChain**](https://github.com/langchain-ai/langchain) PlayWright toolkit | Playwright CDP |
| **Playwright / Puppeteer** (Python & JS) | `connect_over_cdp` / `connect` |

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")   # Fortress under the hood
```

---

### Use it with your AI agent

Building an agent that browses? Fortress *is* the browser — raw CDP on `:9222`, no stealth plugins to wire up. **Copy the prompt below into Claude Code, Cursor, or any coding agent** (hover the block, hit the copy button) and it wires everything up:

```text
Set up Fortress (open-source stealth Chromium) for my browser automation.
1. Launch:  docker run -d --rm -p 9222:9222 tilion/fortress:latest
2. Connect my Playwright/Puppeteer code over CDP to http://localhost:9222
   (Python: chromium.connect_over_cdp("http://localhost:9222")
    Node:   puppeteer.connect({ browserURL: "http://localhost:9222" }))
3. Keep my existing automation logic — just point the browser at that endpoint.
Do NOT add puppeteer-stealth or JS fingerprint patches — Fortress spoofs the fingerprint in the
engine's C++; extra JS patching self-reveals and undoes it. If a site still blocks me, it's the IP
(datacenter), not the fingerprint — route egress through a residential proxy.
Reference: https://github.com/tiliondev/fortress/blob/main/AGENTS.md
```

Full agent guide → **[AGENTS.md](AGENTS.md)**

---

### What you get
- 34 single-surface C++ patches cover canvas, WebGL, audio, fonts, GPU, screen, timezone, WebRTC, navigator, plugins, and Client-Hints. Every one lives in `patches/`, so you can read and audit them.
- Every spoofed getter is native C++, so `toString`, property descriptors, `failsTypeError`, and realm re-acquisition from iframes and workers all report `[native code]`.
- Fortress keeps the `Runtime.enable` leak, the top automation tell, out of the CDP-client layer (drive it raw-CDP, nodriver-style). Verified on [rebrowser bot-detector](https://bot-detector.rebrowser.net/).
- Real Chromium/V8 and BoringSSL keep the engine, user-agent, and TLS shape in agreement, so a Windows persona rides on a matching engine.
- Real GPU / ANGLE WebGL gives a genuine renderer string that matches the spoofed OS.
- One binary ships a coherent default Windows identity, and `--uxr-*` flags override any surface.
- BSD-3 licensed and self-hosted, so it runs on your own infrastructure.
- Raw CDP on `:9222` makes it a drop-in under Playwright, Puppeteer, and anything built on them.

---

### The three layers of bot detection, and where Fortress fits
Modern anti-bots (Cloudflare, DataDome, Kasada, HUMAN, Akamai) read three structurally different
surfaces, in three separate places. One tool rarely fixes all three. Here is how they map:

| Layer | The tells | Where the fix lives | Fortress |
|---|---|---|---|
| **A: driver / binary artifacts** | `cdc_` ChromeDriver vars, WebDriver protocol surface | Drive raw CDP, skip chromedriver | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> built to be driven this way |
| **B: CDP side-effects** | `Runtime.enable` and friends leak through sourceURL and init-script footprints, however clean the binary is | The control / CDP-client layer: hold back `Runtime.enable`, use `Runtime.addBinding` and isolated worlds | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> no leak (verified) |
| **C: fingerprint surface** | canvas, WebGL, audio, fonts, navigator, across main frame, iframes, and workers | The engine (C++), because JS overrides self-reveal | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> this is Fortress |

Fortress is the Layer-C engine, built to be driven so A and B hold too. The binary alone leaves the
CDP channel open. That part is on the control layer, and pretending otherwise is how you get caught.

---

### Why an engine fork? (JS injection is self-revealing)
The usual approach patches `navigator.webdriver`, spoofs the WebGL vendor, and overrides
`navigator.plugins` from script. CreepJS and similar detectors still flag it, and the reason is
structural rather than one more property left uncovered.

A JavaScript spoof is a function standing where a native one belongs. Detectors set the returned
value aside and check whether the thing returning it is native:

- `toString` self-reveal: a native method stringifies to `function get vendor() { [native code] }`, while your override stringifies to its own source, so one `.toString()` catches it.
- Descriptor and `hasOwnProperty` tells: `getOwnPropertyDescriptor` exposes redefined props, and `hasOwnProperty('toString')` returns `true` on a tampered function, `false` on a native one.
- `failsTypeError`: native getters throw a specific `TypeError` on the wrong `this`, and a naive shim stays quiet, so the silence is the signal.
- Realm re-acquisition defeats every main-world patch. A detector grabs a pristine primitive from another realm and turns it on your function:

  ```js
  const iframe = document.createElement('iframe'); document.body.appendChild(iframe);
  const realToString = iframe.contentWindow.Function.prototype.toString;
  realToString.call(navigator.__lookupGetter__('vendor')); // returns your source code. Caught.
  ```

  Your main-world patch lives in a different realm from that iframe. The same trap fires from a Web
  Worker, a thread your main-thread shim runs beside rather than inside.

Fortress has no such layer. The getter for `navigator.vendor` is the C++ getter. It reports
`[native code]` because it is native code, identical across every realm. Camoufox puts it well:
*"there is no JavaScript hijacking to be detected."* Fortress applies the same idea to V8 and Blink
in place of Gecko.

---

### How Fortress compares
| | Stock Playwright | puppeteer-extra-stealth | undetected-chromedriver | Camoufox | CloakBrowser | **Fortress** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Spoof layer | none | JS injection | CDP/config patch | **C++ engine** | **C++ engine** | **C++ engine** |
| `toString` yields `[native code]` | n/a | <img src="docs/assets/icons/x.svg" width="15" alt="no"> | n/a | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |
| Survives realm re-acquisition (iframe/worker) | <img src="docs/assets/icons/x.svg" width="15" alt="no"> | <img src="docs/assets/icons/x.svg" width="15" alt="no"> | <img src="docs/assets/icons/x.svg" width="15" alt="no"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |
| No `Runtime.enable` leak | <img src="docs/assets/icons/x.svg" width="15" alt="no"> | <img src="docs/assets/icons/x.svg" width="15" alt="no"> | <img src="docs/assets/icons/warn.svg" width="15" alt="partial"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |
| Engine = Chrome / **V8** (majority traffic) | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/x.svg" width="15" alt="no"> Firefox | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |
| Coherent Chromium TLS shape | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/x.svg" width="15" alt="no"> Firefox | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |
| **Fully open-source engine** | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/warn.svg" width="15" alt="partial"> latest major paywalled | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |
| Published, auditable patch series | n/a | n/a | n/a | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/warn.svg" width="15" alt="partial"> binary only | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |
| Reproducible from-source build | n/a | n/a | n/a | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/x.svg" width="15" alt="no"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |
| **States its own limits** | n/a | n/a | n/a | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> | <img src="docs/assets/icons/x.svg" width="15" alt="no"> | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> |

Fortress builds on real prior art.
[`fingerprint-chromium`](https://github.com/adryfish/fingerprint-chromium),
[`ChromiumFish`](https://github.com/arman-bd/chromiumfish), and CloakBrowser came first, and
commercial vendors (Multilogin, Kameleo, GoLogin, AdsPower, Browserbase, Surfsky) recompile Chromium
behind closed source. Most of that work stays closed. The paywalled forks hand you a binary and ask
you to trust it, and the vendors keep their patches in-house.

Fortress goes the other way, because a stealth engine only stays useful when the people relying on it
can see how it works. Every surface correction lives in `patches/` as a small, single-purpose diff
you can read in a minute, and the whole engine rebuilds from source with one script. When a detector
finds a new tell, you can trace the fix, patch it, and send it back. That feedback loop is the point,
and it only works while the engine stays open enough to read, extend, and rebuild.

---

### Detection results (official binary, Chromium 151)
*Reproduce any row with `tools/gauntlet.py --bundle ./tilion-fortress`. Verified against live detectors; re-run dated in [docs/GAUNTLET_RESULTS.md](docs/GAUNTLET_RESULTS.md).*

| Suite | Stock Chromium | **Fortress** |
|---|:---:|:---:|
| **CreepJS** | flagged headless | **0% headless · 0% stealth**, worker signals coherent |
| **bot.sannysoft.com** | red rows | **0 failed** · WebDriver Advanced passed · WebGL = NVIDIA RTX 3060 / ANGLE D3D11 |
| **browserscan.net** | bot detected | **“No bots detected, could be a human”** |
| **rebrowser bot-detector** | `Runtime.enable` LEAK | **no leak** · `webdriver=false` · clean init-scripts (raw CDP) |
| **Cloudflare Turnstile** | blocked | **bypassed**, a human click cleared a live challenge (headed, datacenter IP) |

<details open><summary>Proof, real unedited screenshots</summary>

<img src="docs/assets/sannysoft_top.png" width="680"/>

| BrowserScan | CreepJS | Cloudflare |
|:---:|:---:|:---:|
| <img src="docs/assets/browserscan_top.png" width="240"/> | <img src="docs/assets/creepjs.png" width="240"/> | <img src="docs/assets/cloudflare_bypass.gif" width="240"/> |

</details>

---

### Build from source
```bash
export CHROMIUM_VERSION=$(cat CHROMIUM_VERSION)
build/build.sh                         # depot_tools, sync the tag, apply patches, gn gen, ninja
build/rebase-monthly.sh 152.0.XXXX.0   # bump + 3-way apply + rebuild + gauntlet-gate
```
Output: `out/Fortress/chrome`. The fork is 34 small single-surface patches (`patches/`), so most
re-apply cleanly across upstream releases; the gauntlet then gates the release on any regression.

| Platform | Status |
|---|---|
| Linux x64 (native) · any OS via Docker | <img src="docs/assets/icons/check.svg" width="15" alt="yes"> shipping |
| Windows x64 `.exe` · macOS `.app` (signed) | in progress |

---

### Verify it's really ours

Fortress ships from four official channels — treat anything else as untrusted:

| | Official source |
|---|---|
| **Source** | [github.com/tiliondev/fortress](https://github.com/tiliondev/fortress) |
| **Docker** | [`tilion/fortress`](https://hub.docker.com/r/tilion/fortress) |
| **Python** | [`tilion-fortress`](https://pypi.org/project/tilion-fortress/) |
| **Node** | [`tilion-fortress`](https://www.npmjs.com/package/tilion-fortress) |

**Verify a download** — every release ships `SHA256SUMS`; check your file against it (the `pip`/`npm` SDKs do this automatically on install):

```bash
BASE=https://github.com/tiliondev/fortress/releases/download/v151.0.7908.0
curl -LO $BASE/tilion-fortress-linux-x64.tar.gz
curl -Ls $BASE/SHA256SUMS | sha256sum -c --ignore-missing     # -> OK
```

**Verify the Docker image** by digest (not just the tag):

```bash
docker pull tilion/fortress:151.0.7908.0
docker inspect --format '{{index .RepoDigests 0}}' tilion/fortress:151.0.7908.0
# compare the printed sha256:... against the digest in the GitHub Release notes
```

**Or trust nothing and rebuild it.** The whole fork is 34 readable patches in `patches/`; `build/build.sh` reproduces the binary from Chromium source, so you can diff what you built against what we ship.

---

### Troubleshooting
**Still blocked on Cloudflare, DataDome, or Kasada.** Most of the time this is your IP, not your
fingerprint. A datacenter range gets flagged before any page script runs. Route egress through
residential or mobile proxies and retry; if it clears, the fingerprint was fine.

**The fingerprint looks off on a Linux host.** The default persona is Windows, but the TLS shape and
some OS-facing signals follow the machine underneath. Match the persona to your egress OS, or set the
relevant `--uxr-*` flags so the OS story agrees with where the traffic leaves from.

**macOS or Windows pulls a Docker image.** Native Win/Mac binaries are still in progress, so the SDK
runs Fortress through the official Docker image on those platforms. Install Docker Desktop, or run on
Linux x64 for the native binary.

**The persona shows up in `/proc/<pid>/cmdline`.** The `--uxr-*` flags are readable by other processes
on the host, one persona per launch. Until the runtime `MaskConfig` lands, keep one persona per
process and avoid sharing the host with untrusted code.

**A detector flags something the gauntlet passes.** Detection moves. Confirm you are on the current
Chromium rebase, then open an issue with the test page. That page becomes the next patch.

---

### FAQ
**Is this legal?** Fortress is a browser engineering project for legitimate automation, testing, and
scraping of publicly available data. Respect each site's ToS and the law in your jurisdiction.

**Is it really free?** Yes. BSD-3, fully open, and self-hostable. The patch series is published, so
you can build the current engine from source yourself.

**Why not just use puppeteer-stealth or undetected-chromedriver?** They patch the JS/CDP layer after
the page can inspect the browser, so they self-reveal via `toString` and realm re-acquisition.
Fortress moves the spoof into C++, where the page finds native code. (See "Why an engine fork.")

**How is this different from Camoufox?** Same C++-interception idea. Camoufox forks Firefox (~3% of
traffic, a standing anomaly) while Fortress forks Chromium and V8 (the majority engine), so a Chrome
user-agent is coherent by construction.

**Will it pass everything forever?** No. Detection is an arms race, so we ship a dated, reproducible
gauntlet and a monthly Chromium rebase, and you can always see exactly what passes today.

**I'm still getting blocked.** Roughly 90% of the time it is Layer 1, your IP (datacenter range),
ahead of your fingerprint. Route egress through residential or mobile proxies and retry.

---

### Roadmap
- [ ] Runtime JSON config into a C++ `MaskConfig` (one binary, many coherent fingerprints, nothing on the command line)
- [ ] First-party MCP server plus Puppeteer / raw-CDP SDKs (drop-in for AI agents)
- [ ] Native signed Windows `.exe` and macOS `.app`; `linux/arm64` Docker
- [ ] Migrate `patches/` to Brave-style `chromium_src/` overrides
- [ ] Published reCAPTCHA v3 / DataDome / Kasada benchmark rows (dated, reproducible)

---

### Repo layout
```
patches/     34 per-surface C++ patches (+ series), the source of truth for the fork
build/       args.gn, build.sh, apply-patches.sh, rebase-monthly.sh, windows/, macos/
packaging/   tilion launcher, fonts.conf, Dockerfile, .deb + bundle builders
fonts/       33 metric-compatible Windows-named fonts (incl. color emoji)
sdk/         python + node (tilion-fortress) prebuilt-binary SDKs
tools/       gauntlet.py, the CreepJS / Sannysoft / BrowserScan CI gate
docs/        GAUNTLET_RESULTS, BUILD_NATIVE, BENCHMARK
```

### Contributing
Found a detection vector or a leak we missed? Open an issue with a reproducible test page. A page that
reliably flags Fortress is the most valuable thing you can send, because it becomes the next patch.
Two house rules. Every capability claim ships with a command that reproduces it, and every limit is
written down. The word "undetectable" stays out of the repo.

### License
BSD-3-Clause for the Fortress patches and tooling (matching Chromium). Chromium and the bundled fonts
retain their own licenses, see [LICENSE](LICENSE) and [NOTICE](NOTICE). The patch series is published,
so you can audit and rebuild the engine yourself.

---

<div align="center">

### Coming in the next drops

</div>

> [!IMPORTANT]
> **`v2` — MaskConfig runtime personas** *(the big one)*. An **IPC-delivered, seed-driven persona graph**
> feeding a process-global C++ `MaskConfig` singleton — **thousands of coherence-invariant fingerprints
> from a single binary**, **per-`BrowserContext` identity isolation**, and **zero command-line footprint**.
> One browser, an entire population of coherent identities.

<table>
<tr>
<td width="20%" align="center"><b>Native</b></td>
<td>Signed <b>Windows <code>.exe</code></b> + <b>macOS <code>.app</code></b>, and <code>linux/arm64</code> Docker — no container hop on Mac/Win.</td>
</tr>
<tr>
<td width="20%" align="center"><b>Agent-native</b></td>
<td>First-party <b>MCP server</b> + raw-CDP / Puppeteer SDKs — drop-in for autonomous browser agents.</td>
</tr>
<tr>
<td width="20%" align="center"><b><code>chromium_src</code></b></td>
<td>Brave-style in-tree overrides for near-zero-conflict monthly rebases.</td>
</tr>
<tr>
<td width="20%" align="center"><b>Benchmarks</b></td>
<td>Dated, reproducible <b>reCAPTCHA v3 / DataDome / Kasada</b> result rows.</td>
</tr>
</table>

<div align="center">

### Star Fortress — and watch the arms race

Detection never stops moving, and neither does Fortress — a **monthly Chromium rebase**, a fresh gauntlet, and the next patch every time a detector finds a tell.

**[Star the repo](https://github.com/tiliondev/fortress/stargazers)** to back the work · **[Watch → Releases](https://github.com/tiliondev/fortress/releases)** to catch the `v2` MaskConfig drop the day it lands.

<a href="https://star-history.com/#tiliondev/fortress&Date">
  <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=tiliondev/fortress&type=Date" width="600"/>
</a>

<br/>

<em>Stealth you can read, rebuild, and run yourself.</em>

</div>
