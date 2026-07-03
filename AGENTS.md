# Using Fortress from an AI agent

**Fortress is a stealth Chromium engine that exposes raw CDP on `:9222`.** Any agent that drives a
browser through Playwright, Puppeteer, or the Chrome DevTools Protocol can use it as a **drop-in** —
swap the browser, keep your automation code. The fingerprint is corrected in the engine's C++, so you
do **not** need `puppeteer-stealth`, `undetected-chromedriver`, or any post-load JS patching.

## 1. Launch it

Pick one. All expose CDP on `http://localhost:9222`.

```bash
# Docker — any OS, nothing to build
docker run -d --rm -p 9222:9222 tilion/fortress:latest
```
```bash
# Python
pip install tilion-fortress
python -c "from tilion_fortress import Fortress; f=Fortress(); print(f.cdp_url)"
```
```bash
# Node
npm install tilion-fortress
```

## 2. Connect over CDP (`:9222`)

```python
# Python + Playwright
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")   # Fortress under the hood
    page = browser.new_page()
    page.goto("https://bot.sannysoft.com")
```
```js
// Node + Puppeteer
import puppeteer from "puppeteer-core";
const browser = await puppeteer.connect({ browserURL: "http://localhost:9222" });
const page = await browser.newPage();
await page.goto("https://browserscan.net");
```

Works the same under **browser-use**, **Crawl4AI**, **Stagehand**, and **LangChain** — set their CDP
endpoint / `connect_over_cdp` to `http://localhost:9222`.

## 3. Persona (optional)

The launcher applies a coherent default Windows persona. Override any surface with `--uxr-*` switches,
e.g. `--uxr-timezone=America/New_York --uxr-hw-concurrency=16 --uxr-webgl-renderer="..."`.
Full list: see the project README.

## Rules an agent should follow

1. **Drive it over raw CDP** (connect to `:9222`). Don't spawn chromedriver.
2. **Never pass `--user-agent`** — it desyncs the UA string from UA Client Hints and is a tell. Use
   `--uxr-ua-*` instead.
3. **Don't add `puppeteer-stealth` / JS fingerprint patches** — they self-reveal and undo Fortress.
   The spoof is already native C++.
4. **If you still get blocked, it's almost always the IP, not the fingerprint.** Datacenter ranges are
   flagged before any page script runs. Route egress through a residential or mobile proxy and retry.
5. **Verify** with `tools/gauntlet.py` (CreepJS / Sannysoft / BrowserScan) before trusting a run.

Docs & source: https://github.com/tiliondev/fortress
