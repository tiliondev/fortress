# Fortress examples

Runnable examples that drive the Fortress stealth engine over CDP.

## `scrape_demos.py` — live scraping demos (the README GIFs)

Reproduces the animated demos in the main README. Each one drives the real
Fortress engine, overlays a "verification" HUD so you can watch the scrape, and
writes an animated GIF.

```bash
pip install tilion-fortress playwright pillow
playwright install   # the Playwright client only — NOT a browser; Fortress is the browser

python examples/scrape_demos.py structured   # -> fortress-scrape-structured.gif
python examples/scrape_demos.py paginated
python examples/scrape_demos.py detail
python examples/scrape_demos.py js
python examples/scrape_demos.py all
```

| Demo | Site | Pattern |
|---|---|---|
| `structured` | books.toscrape.com | typed records build into a live JSON panel |
| `paginated` | quotes.toscrape.com | auto-pagination across pages 1..3 |
| `detail` | books.toscrape.com | deep detail-page crawl (UPC · price · tax · stock · reviews) |
| `js` | quotes.toscrape.com/js | client-side-rendered DOM captured over CDP |

Fortress spoofs the fingerprint in the engine's C++, so the examples add **no**
JS stealth. If a site still blocks you it's almost always the IP (a datacenter
range) — route egress through a residential or mobile proxy and retry.
