# tilion-fortress (Python)

Install and drive the **Fortress** stealth browser — no build, no source.

```bash
pip install tilion-fortress
```

On first use it downloads the prebuilt Fortress binary for your platform from the
official GitHub Release (verified by SHA-256) and caches it. No Chromium source,
no compilation.

```python
from tilion_fortress import Fortress

with Fortress() as f:                       # launches headless + a CDP endpoint
    print(f.cdp_url)                         # ws://127.0.0.1:<port>/devtools/browser/...
    # drive it with your favourite CDP client:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f.cdp_url)
        page = browser.new_page()
        page.goto("https://abrahamjuliot.github.io/creepjs/")
```

Custom persona / extra flags:

```python
Fortress(persona={"timezone": "America/Chicago", "languages": "en-GB,en"},
         extra_args=["--window-size=1280,800"])
```

> Linux x64 has a native prebuilt. On macOS/Windows the package transparently runs
> Fortress via the official Docker image (`arham766/fortress`) — Docker is the
> cross-OS vehicle until native Win/Mac builds ship.
