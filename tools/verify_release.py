#!/usr/bin/env python3
"""
verify_release.py — check that a published Fortress release is internally consistent.

Both SDKs download platform bundles from a GitHub Release and verify them against
SHA256SUMS (sdk/python/tilion_fortress/__init__.py, sdk/node/index.js). Nothing, though,
checks that a *published* release actually holds every expected asset and that its
SHA256SUMS is correct — a missing asset or a checksum mismatch only surfaces when a user's
pip/npm install fails. This tool turns that into a loud, early failure.

For a tag it:
  - fetches the release via the GitHub API;
  - asserts every required platform asset is present, named exactly as the SDK tables
    expect (linux-x64 today; win-x64 / mac-* are verified once published);
  - parses SHA256SUMS and checks every listed hash against the asset — by default against
    the asset's API digest plus a size/state sanity check, and with --full by downloading
    and re-hashing each asset;
  - exits non-zero with a per-check report on any missing asset or mismatch.

    tools/verify_release.py v151.0.7908.0
    tools/verify_release.py v151.0.7908.0 --full     # download + re-hash every asset

Stdlib only. Set GITHUB_TOKEN to raise the GitHub API rate limit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "tiliondev/fortress"
API = "https://api.github.com"
# Platforms whose bundle must exist in every release. Others in the SDK table are optional
# for now (no native binary published yet) and are verified only if present.
REQUIRED = {"linux-x64"}
REPO_ROOT = Path(__file__).resolve().parent.parent


class Report:
    """Collects per-check results; `failures` is the list of failed check names."""

    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self._emit("PASS" if ok else "FAIL", name, detail)
        if not ok:
            self.failures.append(name)

    def skip(self, name: str, detail: str = "") -> None:
        self._emit("SKIP", name, detail)

    def note(self, name: str, detail: str = "") -> None:
        self._emit("NOTE", name, detail)

    @staticmethod
    def _emit(mark: str, name: str, detail: str) -> None:
        line = f"  [{mark}] {name}"
        if detail:
            line += f" - {detail}"
        print(line)


# --------------------------------------------------------------------------- parsing helpers
def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse `<hash>  <name>` lines (tolerating the `*name` binary marker) into {name: hash}."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[1].lstrip("*")] = parts[0].lower()
    return out


def load_sdk_assets() -> dict[str, str]:
    """The authoritative platform->asset-name table, imported from the Python SDK."""
    sys.path.insert(0, str(REPO_ROOT / "sdk" / "python"))
    from tilion_fortress import _ASSETS  # noqa: E402
    return {plat: spec[0] for plat, spec in _ASSETS.items()}


def parse_node_asset_names(path: Path) -> set[str] | None:
    """Pull the asset names out of the Node SDK table so we can confirm the two agree."""
    if not path.exists():
        return None
    return set(re.findall(r'asset:\s*"([^"]+)"', path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- core evaluation
def evaluate(release: dict, sums_text: str, sdk_assets: dict[str, str], *,
             required: set[str] = REQUIRED, full: bool = False,
             hasher=None, node_asset_names: set[str] | None = None) -> Report:
    """Pure check of one release against SHA256SUMS + the SDK tables.

    Everything network-y is resolved by the caller: `release` is the parsed release JSON,
    `sums_text` is the SHA256SUMS body, and `hasher(name) -> hex` (only used with --full)
    downloads + hashes an asset. Keeping this pure is what lets the tests drive every
    failure mode offline.
    """
    rep = Report()
    assets = {a["name"]: a for a in release.get("assets", [])}
    sums = parse_sha256sums(sums_text)

    # The SDK tables must agree, or the two installers expect different asset names.
    if node_asset_names is not None:
        agree = set(sdk_assets.values()) == node_asset_names
        rep.check("SDK asset tables agree (python == node)", agree,
                  "" if agree else f"python={sorted(sdk_assets.values())} node={sorted(node_asset_names)}")

    # SHA256SUMS itself must be a published asset.
    rep.check("SHA256SUMS present", "SHA256SUMS" in assets,
              "" if "SHA256SUMS" in assets else "release has no SHA256SUMS asset")

    for plat, name in sorted(sdk_assets.items()):
        present = name in assets
        if not present:
            if plat in required:
                rep.check(f"asset present: {name}", False, f"required {plat} asset missing from release")
            else:
                rep.skip(f"asset present: {name}", f"optional {plat} asset not published yet")
            continue

        rep.check(f"asset present: {name}", True)

        asset = assets[name]
        sane = asset.get("state") == "uploaded" and asset.get("size", 0) > 0
        rep.check(f"asset sane: {name}", sane,
                  "" if sane else f"state={asset.get('state')!r} size={asset.get('size')}")

        if name not in sums:
            rep.check(f"checksummed: {name}", False, "no SHA256SUMS entry for this asset")
            continue
        rep.check(f"checksummed: {name}", True)
        _verify_hash(rep, name, asset, sums[name], full, hasher)

    # Every SHA256SUMS entry should name a real asset — a stale line means a removed/renamed file.
    orphans = sorted(n for n in sums if n not in assets)
    rep.check("no orphan SHA256SUMS entries", not orphans,
              "" if not orphans else f"listed but not in release: {orphans}")

    return rep


def _verify_hash(rep: Report, name: str, asset: dict, expected: str, full: bool, hasher) -> None:
    if full:
        actual = hasher(name)
        rep.check(f"sha256 (re-hashed): {name}", actual == expected,
                  "" if actual == expected else f"expected {expected}, hashed {actual}")
        return
    digest = str(asset.get("digest") or "")
    if digest.startswith("sha256:"):
        actual = digest.split(":", 1)[1].lower()
        rep.check(f"sha256 (API digest): {name}", actual == expected,
                  "" if actual == expected else f"expected {expected}, API digest {actual}")
    else:
        rep.note(f"sha256: {name}", "API exposes no digest; re-run with --full to hash the asset")


# --------------------------------------------------------------------------- network
def _request(url: str, token: str | None, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "verify_release"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_release(repo: str, tag: str, token: str | None) -> dict:
    return json.loads(_request(f"{API}/repos/{repo}/releases/tags/{tag}", token))


def fetch_asset_bytes(asset: dict, token: str | None) -> bytes:
    # The asset API endpoint with octet-stream works for public and private repos alike.
    return _request(asset["url"], token, accept="application/octet-stream")


def make_hasher(assets: dict, token: str | None):
    def _hash(name: str) -> str:
        h = hashlib.sha256()
        req = urllib.request.Request(assets[name]["url"],
                                     headers={"Accept": "application/octet-stream",
                                              "User-Agent": "verify_release"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=300) as r:
            for chunk in iter(lambda: r.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    return _hash


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a published Fortress release.")
    ap.add_argument("tag", help="release tag to verify, e.g. v151.0.7908.0")
    ap.add_argument("--repo", default=REPO, help=f"owner/name (default: {REPO})")
    ap.add_argument("--full", action="store_true",
                    help="download and re-hash every asset instead of trusting the API digest")
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN")

    try:
        release = fetch_release(args.repo, args.tag, token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"error: release {args.tag} not found in {args.repo}", file=sys.stderr)
        else:
            print(f"error: GitHub API returned {e.code} for {args.tag}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 - surface any transport error as a clean failure
        print(f"error: could not fetch release {args.tag}: {e}", file=sys.stderr)
        return 1

    assets = {a["name"]: a for a in release.get("assets", [])}
    print(f"Fortress release verifier - {args.repo} @ {args.tag} ({len(assets)} assets)")

    if "SHA256SUMS" not in assets:
        Report().check("SHA256SUMS present", False, "release has no SHA256SUMS asset")
        print("-" * 60)
        print("FAILED: cannot verify a release with no SHA256SUMS")
        return 1

    try:
        sums_text = fetch_asset_bytes(assets["SHA256SUMS"], token).decode()
    except Exception as e:  # noqa: BLE001
        print(f"error: could not download SHA256SUMS: {e}", file=sys.stderr)
        return 1

    sdk_assets = load_sdk_assets()
    node_names = parse_node_asset_names(REPO_ROOT / "sdk" / "node" / "index.js")
    hasher = make_hasher(assets, token) if args.full else None

    rep = evaluate(release, sums_text, sdk_assets, required=REQUIRED,
                   full=args.full, hasher=hasher, node_asset_names=node_names)

    print("-" * 60)
    if rep.failures:
        print(f"FAILED: {len(rep.failures)} check(s): {', '.join(rep.failures)}")
        return 1
    print(f"OK: release {args.tag} is consistent"
          + (" (assets re-hashed)" if args.full else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
