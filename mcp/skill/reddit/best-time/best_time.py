#!/usr/bin/env python3
"""Best time to post in a subreddit, inferred from when its top posts were submitted.

Pulls the subreddit's top listings (all / year / month / week) through the Fortress
stealth engine, reads each post's exact submission time and score, and reports the
day-of-week and hour-of-day distribution of the winners.

Why old.reddit: Reddit's `.json` API and normal request paths hard-block datacenter and
flagged IPs, but old.reddit's HTML carries exact `data-timestamp` (epoch ms) and
`data-score` attributes, so the times are precise rather than "3 hours ago" estimates.

Usage:
    python best_time.py --subreddit DataHoarder --posts 600
    python best_time.py --subreddit selfhosted --posts 300 --tz America/Los_Angeles

Requires:  pip install "tilion[mcp]" playwright
    (no `playwright install` needed — it connects to Fortress over CDP, it does not
     launch Playwright's own browser.)
"""
import argparse, sys, time, collections
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from tilion_fortress import Fortress
from playwright.sync_api import sync_playwright

FRAMES = ["all", "year", "month", "week"]  # widest first: biggest hits lead the sample
MAX_PAGES_PER_FRAME = 10                    # Reddit caps top pagination near 1000 posts
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

EXTRACT = """() => {
  const out = [];
  document.querySelectorAll('div.thing[data-timestamp]').forEach(el => {
    if (el.getAttribute('data-promoted') === 'true') return;   // skip ads
    out.push({ts:  +el.getAttribute('data-timestamp'),
              score:+el.getAttribute('data-score'),
              id:    el.getAttribute('data-fullname')});
  });
  return out;
}"""


def scrape(subreddit, target, port, pause):
    """Return {id: (ts_ms, score)} until `target` unique posts or the listings run dry."""
    posts = {}
    with Fortress(port=port) as f:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f.cdp_url)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            for t in FRAMES:
                after, count = "", 0
                for _ in range(MAX_PAGES_PER_FRAME):
                    url = (f"https://old.reddit.com/r/{subreddit}/top/?sort=top&t={t}"
                           f"&limit=100&count={count}" + (f"&after={after}" if after else ""))
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    try:
                        page.wait_for_selector("div.thing[data-timestamp]", timeout=15000)
                    except Exception:
                        break  # blocked or empty listing for this frame
                    rows = page.evaluate(EXTRACT)
                    if not rows:
                        break
                    for r in rows:
                        posts.setdefault(r["id"], (r["ts"], r["score"]))
                    after, count = rows[-1]["id"], count + len(rows)
                    time.sleep(pause)
                    if len(posts) >= target:
                        return posts
                print(f"  [{t}] running total: {len(posts)} unique", file=sys.stderr)
                if len(posts) >= target:
                    break
    return posts


def report(posts, subreddit, tzname):
    tz = ZoneInfo(tzname)
    dow_c, dow_s = collections.Counter(), collections.Counter()
    hr_c, hr_s = collections.Counter(), collections.Counter()
    slot = collections.Counter()
    for ts, score in posts.values():
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone(tz)
        dow_c[dt.weekday()] += 1; dow_s[dt.weekday()] += score
        hr_c[dt.hour] += 1;       hr_s[dt.hour] += score
        slot[(dt.weekday(), dt.hour // 3 * 3)] += 1

    total = len(posts)
    print(f"\n===== r/{subreddit}: {total} unique top posts (times in {tzname}) =====\n")

    print("DAY OF WEEK        share of top posts        avg score")
    peak = max(dow_c.values())
    for d in range(7):
        c = dow_c[d]; avg = dow_s[d] / c if c else 0
        print(f"  {DOW[d]}  {c:4d} ({c/total*100:4.1f}%)  {'#'*round(c/peak*30):30s}  {avg:6.0f}")

    print(f"\nHOUR OF DAY ({tzname})   share                avg score")
    peak = max(hr_c.values())
    for h in range(24):
        c = hr_c[h]
        if not c:
            continue
        print(f"  {h:02d}:00  {c:4d} ({c/total*100:4.1f}%)  {'#'*round(c/peak*24):24s}  {hr_s[h]/c:6.0f}")

    print("\nTOP THREE-HOUR WINDOWS BY COUNT")
    for (d, hb), c in slot.most_common(9):
        print(f"  {DOW[d]} {hb:02d}:00-{hb+3:02d}:00   {c:3d} posts ({c/total*100:.1f}%)")

    best_day = max(range(7), key=lambda d: dow_c[d])
    (bd, bh), _ = slot.most_common(1)[0]
    print(f"\nRECOMMENDATION: best day is {DOW[best_day]}; single best window is "
          f"{DOW[bd]} {bh:02d}:00-{bh+3:02d}:00 {tzname}.")
    print("Note: this is when winning posts were submitted (survivorship). Windows with a "
          "high avg score but few posts are outliers, not targets.")


def main():
    ap = argparse.ArgumentParser(description="Find the best time to post in a subreddit.")
    ap.add_argument("--subreddit", required=True, help="subreddit name without r/ (e.g. DataHoarder)")
    ap.add_argument("--posts", type=int, default=500, help="target number of top posts to analyze")
    ap.add_argument("--tz", default="America/New_York", help="IANA timezone for the report")
    ap.add_argument("--port", type=int, default=9400, help="Fortress port (avoid 9222 if the MCP server is up)")
    ap.add_argument("--pause", type=float, default=1.5, help="seconds between page loads (politeness)")
    args = ap.parse_args()

    print(f"Scraping up to {args.posts} top posts from r/{args.subreddit} ...", file=sys.stderr)
    posts = scrape(args.subreddit, args.posts, args.port, args.pause)
    if not posts:
        print("No posts scraped. The subreddit may be private/blocked, or the engine is down "
              "(on macOS check `colima start`).", file=sys.stderr)
        sys.exit(1)
    report(posts, args.subreddit, args.tz)


if __name__ == "__main__":
    main()
