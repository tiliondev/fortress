Tilion Fortress - stealth Chromium 151 (Linux x64)
===================================================

RUN (browser):       ./tilion https://example.com

RUN (automation):    ./tilion --headless=new --remote-debugging-port=9222 --user-data-dir=/tmp/p
   then in code:     playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
   OR point your driver's executablePath at ./tilion (it forwards all flags).

The default Windows persona + bundled fonts are applied automatically.
Override: pass your own --uxr-* flags, or set TILION_NO_DEFAULTS=1 for a bare launch.
Tweak:    TILION_TZ=America/Chicago   TILION_LANG=en-GB,en

This is the max-stealth Fortress flavor of the Tilion engine. See the repo for
build-from-source, the patch series, and the detection-suite results:
https://github.com/tiliondev/fortress

LICENSE
This bundle is licensed under the Fortress Source Available License 1.1 (see
LICENSE). Development, testing and evaluation are free at any size. Production
use is free for individuals and for organizations under US$500,000 in cumulative
funding and US$300,000 or less in ARR; other organizations need one Fortress
subscription from https://tilion.dev/pricing. Chromium and the bundled fonts keep
their own licenses (NOTICE). Earlier BSD releases keep their BSD terms
(LICENSE-BSD-LEGACY).
