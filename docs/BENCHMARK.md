# Fortress launch benchmark: 92 protected sites, eight stacks, all headless

**2026-09-28 · US-EAST (IAD) · Fortress (build `v153.0.8010.36-linux-3`) and seven other browser stacks on 92 protected sites, every tool headless.**

Every tool loaded every target twice, logged out, each time on a new cloud machine that was destroyed afterwards. A run counts as served only if the real page loaded, with no challenge or deny page showing.

| | |
|---|---|
| Machines | 1,584, one per tool × target × rep |
| Scored runs | 1,472 |
| Design | 8 tools × 92 targets × 2 reps |
| Concurrency | at most 100 machines alive, at most 2 on any one site |
| Egress | datacenter, no proxies |
| Mode | every tool headless |

## Result · pages served across all 92 targets

| Tool | Version | Served | n | 95% range |
|---|---|:---:|:---:|:---:|
| **Fortress** | `v153.0.8010.36-linux-3` · `tilion` 0.1.14 `Tilion.fetch` (the `fetch_protected_page` path) | **86.4%** | 159/184 | 81 to 91 |
| Camoufox | 0.5.6 (browser 152.0.4-beta.31) · geoip persona | 74.5% | 137/184 | 68 to 80 |
| puppeteer-extra + stealth | 3.3.6 / 2.11.2 · Chrome 153.0.8010.52 | 72.3% | 133/184 | 65 to 78 |
| Brave | 154.1.96.59 (Chromium 154.0.8037.58) · shields default · raw CDP | 36.4% | 67/184 | 30 to 44 |
| nodriver | 0.50.3 · Chrome for Testing 153.0.8010.52 | 35.9% | 66/184 | 29 to 43 |
| stock Chrome | Chrome for Testing 153.0.8010.52 · raw CDP | 34.2% | 63/184 | 28 to 41 |
| patchright | 1.63.0 · Chrome 153.0.8010.52 | 34.2% | 63/184 | 28 to 41 |
| undetected-chromedriver | 3.5.5 + selenium 4.49.0 · Chrome 153.0.8010.52 | 33.7% | 62/184 | 27 to 41 |

The range is the 95% Wilson interval. Fortress's interval (81 to 91) does not overlap the next stack's (68 to 80).

**Per site.** Fortress served 159/184, Camoufox 137/184 and puppeteer-stealth 133/184. Fortress got 2/2 on ten sites where neither of those two got more than 1/2 (WSJ, Marriott, Macy's, easyJet, PayPal sign-in, Tripadvisor, Monster, Zoopla, datadome.co, AutoZone), and there is no site where it got 0/2 while either of them got 2/2.

**Chrome-based stacks.** nodriver, undetected-chromedriver and patchright send `HeadlessChrome/153` in their user agent when run headless and served 34 to 36%, the same as unmodified headless Chrome. puppeteer-stealth rewrites the user agent; Camoufox is a Firefox build with no headless marker.

**Repeat run.** The same design was run twice on the same day. Fortress, headless in both, served 85.3% (157/184) and 86.4% (159/184). Stock Chrome and Brave, also identical in both runs, moved by 1.1 and 2.7 points. Fortress's Cloudflare result moved from 13/22 to 16/22 between the two runs.

**Fingerprint checkers.** Fortress and Camoufox had zero failures on bot.sannysoft.com and an all-green rebrowser bot detector. Stock Chrome and Brave were flagged "Robot" by BrowserScan and 67% headless by CreepJS. All Chromium-based tools shared Chrome's JA4 family.

## Targets

| Group | Sites |
|---|---|
| Cloudflare · 11 | bhphotovideo.com · cars.com · coinbase.com · doordash.com · economist.com · indeed.com · lufthansa.com · norwegian.com · quora.com · ziprecruiter.com · zoopla.co.uk |
| DataDome · 13 | datadome.co · etsy.com · g2.com · leboncoin.fr · monster.com · nytimes.com · petco.com · reuters.com · seatgeek.com · stubhub.com · tripadvisor.com · viagogo.com · wsj.com |
| Akamai Bot Manager · 12 | aa.com · apartments.com · autozone.com · easyjet.com · gap.com · homedepot.com · joann.com · kohls.com · macys.com · marriott.com · michaels.com · uniqlo.com |
| HUMAN (PerimeterX) · 9 | bloomberg.com · harborfreight.com · priceline.com · rei.com · skyscanner.com · target.com · truecar.com · walmart.com · zillow.com |
| Kasada · 5 | vercel.com · costco.com · hyatt.com · nike.com · sephora.com |
| Imperva · 4 | albertsons.com · copart.com · hertz.com · iaai.com |
| AWS WAF · 4 | booking.com · immobilienscout24.de · redfin.com · similarweb.com |
| Arkose Labs · 3 | expedia.com · hotels.com · ubereats.com |
| reCAPTCHA · 6 | academy.com · advanceautoparts.com · enterprise.com · kayak.com · staples.com · t-mobile.com |
| Arkose login/signup (load only) · 20 | battle.net login · Snapchat signup · OpenAI log-in · Adobe sign-in · GitHub signup · Sony sign-in · Bank of America sign-in · EA login · signup.live.com · tinder.com · Dropbox register · Expedia login · Hotels.com login · LinkedIn login · PayPal sign-in · Roblox login · Twitch login · Uber Eats login · Zillow login · X signup |
| Control · 5 | developer.mozilla.org · example.com · httpbin.org/html · iana.org/domains/reserved · wikipedia.org |

Vendor groups follow the benchmark spec; on the day, autozone.com (listed under Akamai) served a DataDome captcha page to every tool. Control sites passed 10/10 for every tool. Kasada and Arkose enforce on submit, which this benchmark never does, so those groups mostly measure the site's other bot layer.

## Probed, not scored · fingerprint checkers

| Tool | sannysoft fails | rebrowser red | CreepJS headless | BrowserScan | JA4 (tls.peet.ws) |
|---|:---:|:---:|:---:|:---:|---|
| **Fortress** | 0 | 0 | 0% | Normal | `t13d1517h2_8daaf6152771_cb7bf5808d99` |
| nodriver | 2 | 1 | 0% | Normal | `t13d1518h2_8daaf6152771_4980c97edce0` |
| undetected-chromedriver | 2 | 1 | 0% | Normal | `t13d1518h2_8daaf6152771_4980c97edce0` |
| patchright | 2 | 1 | 0% | Normal | `t13d1517h2_8daaf6152771_cb7bf5808d99` |
| puppeteer-extra + stealth | 2 | 1 | 0% | Normal | `t13d1518h2_8daaf6152771_4980c97edce0` |
| Camoufox | 0 | 0 | 0% | Normal | `t13d1617h2_86a278354501_3cbfd9057e0d` |
| stock Chrome | 3 | 1 | 67% | Robot | `t13d1518h2_8daaf6152771_4980c97edce0` |
| Brave | 3 | 1 | 67% | Robot | `t13d1516h2_8daaf6152771_806a8c22fdea` |

User agents seen on the checkers: Fortress `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36`; Camoufox `Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:152.0) Gecko/20100101 Firefox/152.0`. Pixelscan and browserleaks pages were saved but did not yield a comparable summary line.

## Known issues found by this run

**Checker persona incoherence.** Fortress's checker persona paired a macOS user agent with an NVIDIA GTX 1060 WebGL renderer, a combination Macs never shipped with. Tracked as a coherence rule.

## How it was run

**Machines and egress.** One Fly.io machine (shared-cpu-2x, 4 GB, iad) per tool × target × rep, auto-destroyed on exit. An orchestrator machine kept at most 100 alive and at most 2 on any one site, in a shuffled order so no tool always ran first or last against a site. No proxies: each machine went out on the IP Fly gave it. 1,584 machines drew 213 distinct IPv4 addresses from a handful of blocks; 68 scored runs landed on an IP that had already hit the same site and are marked in the per-run matrix. Excluding them moves no tool by more than a point. The IP check records IPv4 only; sites reached over IPv6 (Lufthansa showed one) saw a different address, so the reuse marker is a lower bound.

**Same rules for every tool.** Every tool headless: Chrome's headless mode for nodriver, undetected-chromedriver, patchright and puppeteer-stealth, Camoufox's headless mode, raw CDP for stock Chrome and Brave. Load the page, then check every 2 s until it has real text and no challenge marker, or 30 s have passed since navigation. No clicks, no typing, no Press & Hold. Fortress is driven the way its MCP tool drives it: `Tilion.fetch(url)` from `tilion` 0.1.14, headless, with no captcha solver key. That includes its own wait and vendor-aware settle logic. Verdicts are decided afterwards by one classifier over the saved HTML, status and title, then checked by hand: false passes found in review (browser error pages, Macy's and Hyatt deny pages) became rules before the final numbers. Both reps agreed on the verdict for 673/736 tool and target pairs.

**Harness adjustments.** nodriver gives up connecting to a new browser after about 2.75 s, shorter than Chrome's first launch on a fresh machine. The runner opens and closes Chrome once on `about:blank` first, and retries nodriver's own start; nodriver's launch settings are untouched. Font caches are built into the image so no tool pays for them on first launch.

**Code and raw verdicts.** Runner, orchestrator, classifier and `verdicts.json`: `turing-provider/bench/2026-09-28/fortress-launch/`. Screenshots, HTML and cookies for every run: the `fortress-bench-0928` bucket under `full-1/runs/`.
