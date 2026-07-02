# tilion-fortress (Node.js)

Install and drive the **Fortress** stealth browser — no build, no source.

```bash
npm install tilion-fortress
```

On first launch it fetches the prebuilt Fortress binary for your platform from the
official GitHub Release (SHA-256 verified) and caches it. No Chromium source, no
compilation.

```js
import { Fortress } from "tilion-fortress";
import { chromium } from "playwright";

const f = await Fortress.launch();          // headless + CDP endpoint
const browser = await chromium.connectOverCDP(f.cdpUrl);
const page = await browser.newPage();
await page.goto("https://abrahamjuliot.github.io/creepjs/");
// ...
await f.close();
```

Custom persona / extra flags:

```js
await Fortress.launch({
  persona: { timezone: "America/Chicago", languages: "en-GB,en" },
  extraArgs: ["--window-size=1280,800"],
});
```

> Linux x64 has a native prebuilt. On macOS/Windows the package runs Fortress via the
> official Docker image (`arham766/fortress`) — Docker is the cross-OS vehicle
> until native Win/Mac builds ship. Only the compiled binary is distributed; the engine
> source is not included.
