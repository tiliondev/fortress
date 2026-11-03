#!/usr/bin/env python3
"""`tilion activate` — the ~10-second device flow that unlocks Fortress v3.

Zero third-party deps (stdlib only) so it drops into the tarball and the Docker
image as-is. The engine (binary gate) is what actually verifies the token's
signature at launch; this client just runs the flow and saves the key, so its
own checks (presence + expiry) are deliberately lightweight.

    tilion activate                 run the device flow, open the browser
    tilion activate --headless      print the URL instead of opening a browser (SSH / remote)
    tilion activate --if-needed     activate only if no live key is present (launcher hook)
    tilion activate --token <JWT>   save a key non-interactively — no browser (CI / AI agents)
    tilion license status [--json]  show the saved key's tier + expiry (--json for machines)
    tilion license refresh          re-issue the key before it expires
    tilion license logout           remove the saved key (drops to v1)

Env: TILION_API_URL (default https://fortress.tilion.dev), TILION_LICENSE_KEY (overrides the file).

For headless automation / AI agents: the simplest path needs NO flow at all — set
TILION_LICENSE_KEY=<jwt> in the environment (the engine reads it directly and verifies
offline), or persist one once with `tilion activate --token <jwt>`. The interactive
device flow is only for a human at a terminal.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
import webbrowser

API = os.environ.get("TILION_API_URL", "https://fortress.tilion.dev").rstrip("/")
KEY_PATH = os.path.join(os.path.expanduser("~"), ".tilion", "license.jwt")


def _post(path: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
    except urllib.error.URLError as e:
        print(f"tilion: cannot reach {API} ({e.reason})", file=sys.stderr)
        sys.exit(3)


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _claims(token: str) -> dict | None:
    """Decode the payload WITHOUT verifying (the engine verifies at launch)."""
    try:
        return json.loads(_b64d(token.split(".")[1]))
    except Exception:
        return None


def _saved_key() -> str | None:
    k = os.environ.get("TILION_LICENSE_KEY")
    if k and k.strip():
        return k.strip()
    try:
        with open(KEY_PATH, encoding="utf-8") as f:
            v = f.read().strip()
            return v or None
    except OSError:
        return None


def _live(token: str | None) -> bool:
    c = _claims(token) if token else None
    return bool(c and int(c.get("exp", 0)) > time.time())


def _save(token: str) -> None:
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    with open(KEY_PATH, "w", encoding="utf-8") as f:
        f.write(token)
    try:
        os.chmod(KEY_PATH, 0o600)
    except OSError:
        pass


def activate(headless: bool = False, if_needed: bool = False,
             token: str | None = None) -> int:
    if if_needed and _live(_saved_key()):
        return 0  # already unlocked; say nothing (launcher path)
    if token:  # non-interactive import (CI / AI agents / an org key handed to a fleet)
        token = token.strip()
        if token.count(".") != 2 or not _claims(token):
            print("tilion: that doesn't look like a license token.", file=sys.stderr)
            return 1
        _save(token)
        c = _claims(token) or {}
        live = int(c.get("exp", 0)) > time.time()
        print(f"saved key ({c.get('tier','?')}, {'live' if live else 'EXPIRED'}) to {KEY_PATH}"
              + ("" if live else " — it is expired; the engine will run v1."))
        return 0 if live else 1
    status, r = _post("/v1/activate/start", {})
    if status != 200:
        print(f"tilion: activation start failed ({status})", file=sys.stderr)
        return 1
    uri, code = r["verification_uri"], r["user_code"]
    interval, deadline = r.get("interval", 5), time.time() + r.get("expires_in", 900)
    print(f"\n  To unlock Fortress v3, approve this device:\n\n    {uri}\n"
          f"    code: {code}\n")
    if not headless:
        try:
            webbrowser.open(uri)
        except Exception:
            pass
    print("  Waiting for approval… (Ctrl-C to cancel)")
    while time.time() < deadline:
        time.sleep(interval)
        st, pr = _post("/v1/activate/poll", {"device_code": r["device_code"]})
        if st == 200 and pr.get("license"):
            _save(pr["license"])
            c = _claims(pr["license"]) or {}
            print(f"\n  ✓ Activated ({c.get('tier', '?')}). Fortress v3 unlocked.\n"
                  f"    key saved to {KEY_PATH}\n")
            return 0
        if st == 410:
            break
    print("tilion: activation timed out — run `tilion activate` again.", file=sys.stderr)
    return 1


def license_status(as_json: bool = False) -> int:
    tok = _saved_key()
    c = _claims(tok) if tok else None
    exp = int(c.get("exp", 0)) if c else 0
    live = bool(c) and exp > time.time()
    src = ("env:TILION_LICENSE_KEY" if os.environ.get("TILION_LICENSE_KEY")
           else KEY_PATH if tok else None)
    if as_json:
        print(json.dumps({"licensed": live, "mode": "v3" if live else "v1",
                          "tier": (c or {}).get("tier"), "exp": exp or None, "source": src}))
        return 0
    if not c:
        print("no license key — Fortress runs in v1 (first-gen) mode. `tilion activate` to unlock v3.")
        return 0
    when = time.strftime("%Y-%m-%d", time.gmtime(exp))
    print(f"tier: {c.get('tier', '?')}   {'expires' if live else 'EXPIRED'} {when}   ({src})")
    print("(the engine verifies the signature at launch)")
    return 0


def license_refresh() -> int:
    tok = _saved_key()
    if not tok:
        print("tilion: no key to refresh — run `tilion activate`.", file=sys.stderr)
        return 1
    st, r = _post("/v1/license/refresh", {"license": tok})
    if st == 200 and r.get("license"):
        _save(r["license"])
        print("✓ license refreshed.")
        return 0
    print(f"tilion: refresh failed ({st}) — `tilion activate` to re-activate.", file=sys.stderr)
    return 1


def license_logout() -> int:
    try:
        os.remove(KEY_PATH)
        print("removed saved key — Fortress will run in v1 mode.")
    except FileNotFoundError:
        print("no saved key.")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="tilion")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("activate")
    a.add_argument("--headless", action="store_true")
    a.add_argument("--if-needed", action="store_true")
    a.add_argument("--token", help="save this key non-interactively (CI / AI agents)")
    lic = sub.add_parser("license")
    lic.add_argument("action", choices=["status", "refresh", "logout"])
    lic.add_argument("--json", action="store_true", help="machine-readable status")
    args = ap.parse_args(argv)
    if args.cmd == "activate":
        return activate(headless=args.headless, if_needed=args.if_needed, token=args.token)
    if args.cmd == "license":
        if args.action == "status":
            return license_status(as_json=args.json)
        return {"refresh": license_refresh, "logout": license_logout}[args.action]()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
