#!/usr/bin/env python3
"""Render the README star-history chart from live stargazer data.

star-history.com caches repo data server-side for 24h, so its embed lags
badly during a spike. This renders the same cumulative-stars curve straight
from the GitHub API into docs/assets/star-history-{dark,light}.svg, which the
README references directly. Run hourly by .github/workflows/star-history.yml.

Output is deterministic for a given star count (no timestamps, x-domain ends
at the last star event, y-max rounded to a tick step), so the workflow's
"commit only if changed" check stays quiet between new stars.

Stdlib only — no pip install on the runner.

Usage: GITHUB_TOKEN=... python3 tools/star_history.py [owner/repo] [outdir]
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

REPO = sys.argv[1] if len(sys.argv) > 1 else "tiliondev/fortress"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "docs/assets"

# The stargazers listing is capped at 400 pages (40k stars) by GitHub.
PER_PAGE = 100
MAX_PAGES = 400
MAX_POINTS = 240  # downsample the curve beyond this; keeps SVGs small

W, H = 800, 420
MARGIN = {"top": 44, "right": 40, "bottom": 52, "left": 60}

THEMES = {
    "dark": {
        "text": "#9198a1",
        "strong": "#e6edf3",
        "grid": "#30363d",
        "line": "#e3b341",
        "fill": "#e3b341",
    },
    "light": {
        "text": "#59636e",
        "strong": "#1f2328",
        "grid": "#d1d9e0",
        "line": "#9a6700",
        "fill": "#bf8700",
    },
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_star_times(repo, token):
    """Return sorted list of starred_at datetimes for every stargazer."""
    times = []
    for page in range(1, MAX_PAGES + 1):
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/stargazers"
            f"?per_page={PER_PAGE}&page={page}",
            headers={
                # star+json includes starred_at timestamps
                "Accept": "application/vnd.github.star+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            batch = json.load(resp)
        if not batch:
            break
        times += [
            datetime.strptime(s["starred_at"], "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=timezone.utc)
            for s in batch
        ]
        if len(batch) < PER_PAGE:
            break
    times.sort()
    return times


def nice_step(target):
    """Smallest 1/2/5 x 10^k step >= target, for clean y-axis ticks."""
    if target <= 1:
        return 1
    mag = 1
    while True:
        for m in (1, 2, 5):
            if m * mag >= target:
                return m * mag
        mag *= 10


def build_series(times):
    """(datetime, cumulative_count) points, downsampled but keeping endpoints."""
    pts = [(t, i + 1) for i, t in enumerate(times)]
    if len(pts) > MAX_POINTS:
        idx = {round(i * (len(pts) - 1) / (MAX_POINTS - 1)) for i in range(MAX_POINTS)}
        pts = [pts[i] for i in sorted(idx)]
    return pts


def fmt_date(dt, span_days):
    if span_days > 300:
        return f"{MONTHS[dt.month - 1]} {dt.year}"
    return f"{MONTHS[dt.month - 1]} {dt.day}"


def render(pts, theme, repo):
    c = THEMES[theme]
    x0, x1 = pts[0][0].timestamp(), pts[-1][0].timestamp()
    if x1 == x0:
        x1 = x0 + 1
    total = pts[-1][1]
    step = nice_step(total / 4)
    ymax = max(step, ((total + step - 1) // step) * step)

    px0, px1 = MARGIN["left"], W - MARGIN["right"]
    py0, py1 = H - MARGIN["bottom"], MARGIN["top"]

    def X(t):
        return px0 + (t.timestamp() - x0) / (x1 - x0) * (px1 - px0)

    def Y(n):
        return py0 - n / ymax * (py0 - py1)

    span_days = (x1 - x0) / 86400
    path = " ".join(
        f"{'M' if i == 0 else 'L'}{X(t):.1f} {Y(n):.1f}" for i, (t, n) in enumerate(pts)
    )
    area = f"{path} L{X(pts[-1][0]):.1f} {py0} L{X(pts[0][0]):.1f} {py0} Z"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">',
        f'<text x="{px0}" y="26" font-size="15" font-weight="600" '
        f'fill="{c["strong"]}">{repo} — GitHub stars</text>',
    ]

    for n in range(0, ymax + 1, step):
        y = Y(n)
        parts.append(
            f'<line x1="{px0}" y1="{y:.1f}" x2="{px1}" y2="{y:.1f}" '
            f'stroke="{c["grid"]}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{px0 - 8}" y="{y + 4:.1f}" font-size="12" '
            f'text-anchor="end" fill="{c["text"]}">{n}</text>'
        )

    n_xticks = 5
    for i in range(n_xticks):
        ts = x0 + (x1 - x0) * i / (n_xticks - 1)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        anchor = "start" if i == 0 else "end" if i == n_xticks - 1 else "middle"
        parts.append(
            f'<text x="{px0 + (px1 - px0) * i / (n_xticks - 1):.1f}" y="{py0 + 22}" '
            f'font-size="12" text-anchor="{anchor}" fill="{c["text"]}">'
            f"{fmt_date(dt, span_days)}</text>"
        )

    lx, ly = X(pts[-1][0]), Y(total)
    parts += [
        f'<path d="{area}" fill="{c["fill"]}" opacity="0.12"/>',
        f'<path d="{path}" fill="none" stroke="{c["line"]}" '
        f'stroke-width="2.5" stroke-linejoin="round"/>',
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4" fill="{c["line"]}"/>',
        f'<text x="{lx - 8:.1f}" y="{ly - 10:.1f}" font-size="13" font-weight="600" '
        f'text-anchor="end" fill="{c["strong"]}">{total}</text>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required (stargazer pagination needs auth)")
    times = fetch_star_times(REPO, token)
    if not times:
        sys.exit(f"no stargazers returned for {REPO}")
    pts = build_series(times)
    os.makedirs(OUTDIR, exist_ok=True)
    for theme in THEMES:
        out = os.path.join(OUTDIR, f"star-history-{theme}.svg")
        with open(out, "w") as f:
            f.write(render(pts, theme, REPO))
        print(f"wrote {out} ({pts[-1][1]} stars)")


if __name__ == "__main__":
    main()
