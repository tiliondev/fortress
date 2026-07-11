"""Token cost of giving an AI agent a web page: raw HTML vs the Fortress MCP.

For each URL this prints:
  - raw HTML tokens (what a naive agent dumps into context), or the block status
    a plain HTTP client hits
  - Fortress clean tokens (what the MCP returns), when `tilion` is installed

A built-in web fetch (e.g. Claude Code's WebFetch) sits between these: it summarizes
readable pages cheaply and clears anti-bot on many sites, but it returns nothing on
JavaScript-rendered pages and some hard walls. This script measures the two ends you
can reproduce anywhere; the middle column depends on your client.

Tokens are counted with tiktoken cl100k_base (an approximation for other tokenizers).

    pip install tiktoken
    pip install "tilion[mcp]"        # optional, enables the Fortress column
    python benchmark_tokens.py
    python benchmark_tokens.py --no-fortress   # raw-HTML column only
"""
from __future__ import annotations
import sys

URLS = [
    "https://en.wikipedia.org/wiki/Web_scraping",
    "https://www.nike.com/",
    "https://quotes.toscrape.com/js/",
    "https://www.ticketmaster.com/",
    "https://news.ycombinator.com/",
]

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def ntok(s: str) -> int:
        return len(_enc.encode(s))
except Exception:
    def ntok(s: str) -> int:
        return len(s) // 4  # rough fallback if tiktoken is missing


def raw_html(url: str):
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            return r.read().decode("utf-8", "replace"), None
    except Exception as e:
        return None, type(e).__name__


def fortress_text(url: str):
    """What the Fortress MCP returns for the page. Needs `pip install tilion`."""
    try:
        import asyncio
        from tilion import Tilion
    except Exception:
        return None, "tilion not installed"

    async def run():
        async with Tilion(headless=True) as t:
            r = await t.fetch(url)
            return r.get("text") or r.get("markdown") or ""

    try:
        return asyncio.run(run()), None
    except Exception as e:
        return None, type(e).__name__


def main():
    want_fortress = "--no-fortress" not in sys.argv
    print(f"{'url':46s} {'raw HTML':>18s} {'Fortress MCP':>18s}")
    print("-" * 84)
    for url in URLS:
        html, err = raw_html(url)
        raw_col = f"{ntok(html):,} tok" if html else f"blocked ({err})"
        f_col = ""
        if want_fortress:
            text, ferr = fortress_text(url)
            f_col = f"{ntok(text):,} tok" if text else (ferr or "-")
        print(f"{url:46s} {raw_col:>18s} {f_col:>18s}")


if __name__ == "__main__":
    main()
