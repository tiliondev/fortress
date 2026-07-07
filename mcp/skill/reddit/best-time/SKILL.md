---
name: reddit-best-time-to-post
description: >-
  Use when someone wants the best day and time to post in a subreddit, or asks to
  analyze a subreddit's posting-time patterns. Drives the Fortress stealth engine to
  read a subreddit's top posts (all/year/month/week) from old.reddit, extracts each
  post's exact submission time and score, and reports the day-of-week and hour-of-day
  distribution of the winners in any timezone. Takes two inputs: the subreddit and the
  number of posts to analyze.
---

# Reddit best-time-to-post skill

## When to use this
Someone asks a version of "when should I post in r/X" or "what's the best time to post
in this subreddit," or wants the posting-time pattern of a community. This skill answers
it from data rather than folklore.

## Inputs
- **subreddit** (required): the community, without `r/` (for example `DataHoarder`).
- **posts** (required): how many top posts to analyze. 300 to 700 gives a stable pattern.
  Fewer is faster but noisier; more flattens out past a few hundred.
- **tz** (optional): the IANA timezone for the report, default `America/New_York`. Use the
  timezone the person cares about, for example `America/Los_Angeles` for Pacific.

## Why this works, and its one limit
Reddit's top listings are the posts that won. Reading when those posts were submitted gives
a strong proxy for the best time to post. The limit is survivorship: the data shows when
hits landed, not the posts that flopped at the same hours. Treat the result as "when
successful posts tend to go up," not a guarantee.

Source is `old.reddit.com`, not the `.json` API. Reddit's JSON endpoint and normal request
paths hard-block datacenter and flagged IPs, but old.reddit's HTML carries exact
`data-timestamp` (epoch milliseconds) and `data-score` attributes, so the times are precise
instead of relative estimates like "3 hours ago." The Fortress stealth engine loads
old.reddit without tripping the block page.

## Setup
```bash
pip install "tilion[mcp]" playwright
```
No `playwright install` is needed. The script connects to Fortress over CDP rather than
launching Playwright's own browser. On macOS the engine runs as a Docker image, so a Docker
daemon must be running (`colima start` if you use Colima). See [`mcp/README.md`](../../README.md#macos-setup-apple-silicon-and-intel).

## Run it
```bash
python best_time.py --subreddit DataHoarder --posts 600 --tz America/Los_Angeles
```
The script starts a Fortress instance on port 9400 (override with `--port` if that is taken),
pages through the top listings until it has the requested number of unique posts, and prints
the analysis. Roughly 100 posts per page load, with a short politeness pause between pages,
so 600 posts takes well under a minute once the engine is warm.

## Reading the output
The report has three parts and a recommendation:
- **Day of week**: the share of top posts on each day, plus the average score. The day with
  the largest share is the safest bet.
- **Hour of day**: the share of top posts in each hour, in the requested timezone. Look for
  the plateau of high-share hours, not a single spike.
- **Top three-hour windows**: the day-and-hour blocks that produced the most top posts. The
  first row is the single strongest window.

The final `RECOMMENDATION` line names the best day and the best three-hour window. Ignore any
hour that shows a high average score but a tiny post count, since one viral thread skews it.

## If it returns nothing
The subreddit may be private or quarantined, or the engine may be down. On macOS the usual
cause is a stopped Docker daemon, so run `colima start` and retry. For a genuinely hard block,
route the engine through a residential proxy with `TILION_PROXY` before running.

## Reference
Fortress tools and setup: [`mcp/README.md`](../../README.md).
General stealth-browser skill: [`mcp/skill/SKILL.md`](../../skill/SKILL.md).
