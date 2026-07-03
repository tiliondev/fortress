<p align="center">
  <img src="https://raw.githubusercontent.com/tiliondev/fortress/main/docs/assets/dockerhub-banner.png" width="100%" alt="Fortress — stealth Chromium engine">
</p>

<h1 align="center">tilion-fortress</h1>

<p align="center"><b>Drive the Fortress stealth Chromium engine with one line — no build, no Chromium source.</b></p>

<p align="center">
  <a href="https://www.npmjs.com/package/tilion-fortress"><img src="https://img.shields.io/npm/v/tilion-fortress?logo=npm" alt="npm"></a>
  <a href="https://www.npmjs.com/package/tilion-fortress"><img src="https://img.shields.io/node/v/tilion-fortress?logo=node.js&logoColor=white" alt="node"></a>
  <a href="https://hub.docker.com/r/tilion/fortress"><img src="https://img.shields.io/docker/pulls/tilion/fortress?logo=docker&logoColor=white&label=docker%20pulls" alt="Docker Pulls"></a>
  <a href="https://github.com/tiliondev/fortress"><img src="https://img.shields.io/github/stars/tiliondev/fortress?style=social" alt="Stars"></a>
  <a href="https://github.com/tiliondev/fortress/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-BSD--3--Clause-blue" alt="License"></a>
</p>

---

**Stop getting blocked — without `puppeteer-stealth`.** JavaScript stealth patches self-reveal: a detector checks whether a getter is native code and catches the override. Fortress compiles the fingerprint correction into Chromium's **C++**, so a page inspecting itself sees stock Chrome. It clears **CreepJS**, **Sannysoft**, **BrowserScan**, and live **Cloudflare** as a normal Chrome install.

## Install

```bash
npm install tilion-fortress
```

On first launch it fetches the prebuilt Fortress binary for your platform from the official GitHub Release (SHA-256 verified) and caches it. No Chromium source, no compilation.

## Quick start

```js
import { Fortress } from "tilion-fortress";
import puppeteer from "puppeteer-core";

const f = await Fortress.launch();                       // stealth engine on a CDP endpoint
const browser = await puppeteer.connect({ browserURL: f.cdpUrl });
const page = await browser.newPage();
await page.goto("https://bot.sannysoft.com");
await page.screenshot({ path: "all-green.png" });
await browser.close();
await f.close();
```

Keep your existing Puppeteer / Playwright / CDP code — just point it at `f.cdpUrl`. Works the same under **browser-use**, **Crawl4AI**, **Stagehand**, and **LangChain**.

## Verified against live detectors

| Suite | Result |
|---|---|
| **CreepJS** | 0% headless · 0% stealth |
| **bot.sannysoft.com** | 0 failed · all green · WebGL = NVIDIA RTX 3060 / ANGLE D3D11 |
| **browserscan.net** | "No bots detected, could be a human" |
| **rebrowser bot-detector** | no `Runtime.enable` leak · `webdriver=false` |
| **Cloudflare Turnstile** | cleared a live challenge |

## Custom persona

The default persona is a coherent Windows identity. Override any surface:

```js
const f = await Fortress.launch({
  persona: { timezone: "America/Chicago", languages: "en-GB,en", hwConcurrency: 16 },
  extraArgs: ["--window-size=1280,800"],
});
```

## Platform support

Linux x64 has a native prebuilt binary. On macOS / Windows the package transparently runs Fortress via the official Docker image (`tilion/fortress`) — Docker is the cross-OS vehicle until native Win/Mac builds ship.

> **Still blocked?** ~90% of the time it's your **IP**, not your fingerprint — datacenter ranges are flagged before any page script runs. Route egress through a residential or mobile proxy and retry.

## Links

- **Source & docs:** https://github.com/tiliondev/fortress
- **Agent guide:** https://github.com/tiliondev/fortress/blob/main/AGENTS.md
- **Docker image:** https://hub.docker.com/r/tilion/fortress

BSD-3-Clause · reproducible from source · monthly Chromium rebase · **Blink · V8 · BoringSSL** patched in-tree.
