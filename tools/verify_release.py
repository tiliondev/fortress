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
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

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


def release_asset_names(tag: str, legacy_assets: dict[str, str]) -> dict[str, str]:
    """Resolve the published naming convention independently of SDK channel pins."""
    match = re.fullmatch(r"v(\d+)\.\d+\.\d+\.\d+(?:[-+].+)?", tag)
    if not match or int(match.group(1)) < 153:
        return dict(legacy_assets)
    prefix = f"fortress-v{match.group(1)}"
    platforms = ("linux-x64", "linux-arm64", "linux-armhf", "linux-x86", "win-x64", "mac-arm64", "mac-x64")
    return {platform: f"{prefix}-{platform}.{'zip' if platform == 'win-x64' else 'tar.gz'}"
            for platform in platforms}


def _file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def _archive_identity(path: Path, engine_file: str) -> tuple[str | None, str | None, bool]:
    """Read selected members without extracting the archive."""
    engine_hash = client_hash = None
    clean = True
    seen = set()

    def inspect(name, stream):
        nonlocal engine_hash, client_hash, clean
        normalized = PurePosixPath(name.replace("\\", "/"))
        key = normalized.as_posix().casefold() if path.suffix == ".zip" else normalized.as_posix()
        if normalized.is_absolute() or ".." in normalized.parts or ":" in name or key in seen:
            clean = False
        seen.add(key)
        if normalized.suffix.lower() == ".jwt":
            clean = False
        if stream is not None and (normalized.as_posix() == engine_file or normalized.name == "tilion_activate.py"):
            value = hashlib.sha256()
            for block in iter(lambda: stream.read(1 << 20), b""):
                value.update(block)
            if normalized.as_posix() == engine_file:
                engine_hash = value.hexdigest()
            else:
                client_hash = value.hexdigest()

    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                with archive.open(item) as stream:
                    inspect(item.filename, stream)
    else:
        with tarfile.open(path, "r:gz") as archive:
            for item in archive:
                if item.isfile():
                    with archive.extractfile(item) as stream:
                        inspect(item.name, stream)
                elif item.issym() or item.islnk():
                    inspect(item.name, None)
    return engine_hash, client_hash, clean


def evaluate_manifest(manifest: dict, sums_text: str, artifacts_dir: Path | None = None) -> Report:
    """Validate a candidate record, optionally against the actual retained archives."""
    report = Report()
    tag = manifest.get("tag", "")
    report.check("manifest tag matches version", tag == "v" + manifest.get("chromium_version", ""))
    names = release_asset_names(tag, {})
    license_info = manifest.get("license", {})
    report.check("native license bypass disabled", license_info.get("bypass_enabled") is False)
    report.check("personal keys excluded", license_info.get("personal_keys_bundled") is False)
    sums = parse_sha256sums(sums_text)
    checksum_names = [line.split()[1].lstrip("*") for line in sums_text.splitlines() if len(line.split()) == 2]
    report.check("unique checksum entries", len(checksum_names) == len(set(checksum_names)))
    assets = manifest.get("assets", [])
    platforms = [asset.get("platform") for asset in assets]
    report.check("unique manifest platforms", len(platforms) == len(set(platforms)))
    required = manifest.get("required_platforms", [])
    report.check("required platforms present", bool(required) and set(required).issubset(platforms))
    report.check("checksums cover exactly the manifest", set(sums) == {asset.get("name") for asset in assets})
    for asset in assets:
        platform, name = asset.get("platform"), asset.get("name", "")
        valid_name = bool(name) and name == names.get(platform) and PurePosixPath(name).name == name and "\\" not in name
        report.check("manifest asset name: " + str(platform), valid_name)
        valid_digest = bool(re.fullmatch(r"[0-9a-f]{64}", asset.get("sha256", "")))
        report.check("manifest sha256: " + name, valid_digest and sums.get(name) == asset.get("sha256"))
        report.check("manifest size: " + name, type(asset.get("bytes")) is int and asset["bytes"] > 0)
        engine_file = asset.get("engine_file", "")
        engine_path = PurePosixPath(engine_file)
        valid_engine = bool(engine_file) and not engine_path.is_absolute() and ".." not in engine_path.parts
        report.check("manifest engine identity: " + name,
                     valid_engine and bool(re.fullmatch(r"[0-9a-f]{64}", asset.get("engine_sha256", ""))))
        if artifacts_dir is None or not valid_name:
            continue
        path = artifacts_dir / name
        if not path.is_file():
            path = artifacts_dir / platform / name
        present = path.is_file()
        report.check("local archive present: " + name, present)
        if not present:
            continue
        report.check("local archive size: " + name, path.stat().st_size == asset["bytes"])
        digest = _file_sha256(path)
        report.check("local archive sha256: " + name, digest == asset["sha256"])
        if digest != asset["sha256"]:
            continue
        engine, client, clean = _archive_identity(path, engine_file)
        report.check("archive paths and credential exclusion: " + name, clean)
        report.check("native engine sha256: " + name, engine == asset["engine_sha256"])
        report.check("activation client sha256: " + name, client == license_info.get("activation_client_sha256"))
    if artifacts_dir is None:
        report.note("candidate metadata only", "pass --artifacts-dir to verify the native archive bytes")
    return report


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
    ap.add_argument("--manifest", type=Path, help="validate a local candidate manifest without fetching a release")
    ap.add_argument("--artifacts-dir", type=Path, help="directory containing the candidate archives")
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN")

    if args.manifest:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        sums_text = args.manifest.with_name("SHA256SUMS").read_text(encoding="utf-8")
        rep = evaluate_manifest(manifest, sums_text, args.artifacts_dir)
        rep.check("requested tag matches manifest", args.tag == manifest.get("tag"))
        return 1 if rep.failures else 0
    if args.artifacts_dir:
        ap.error("--artifacts-dir requires --manifest")

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
    asset_names = release_asset_names(args.tag, sdk_assets)
    required = REQUIRED
    manifest_path = REPO_ROOT / "releases" / args.tag / "manifest.json"
    manifest_report = None
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        required = set(manifest["required_platforms"])
        manifest_report = evaluate_manifest(manifest, sums_text)
    hasher = make_hasher(assets, token) if args.full else None

    rep = evaluate(release, sums_text, asset_names, required=required,
                   full=args.full, hasher=hasher)
    if node_names is not None:
        rep.check("SDK asset tables agree (python == node)", node_names == set(sdk_assets.values()))
    if manifest_report is not None:
        rep.failures.extend(manifest_report.failures)

    print("-" * 60)
    if rep.failures:
        print(f"FAILED: {len(rep.failures)} check(s): {', '.join(rep.failures)}")
        return 1
    print(f"OK: release {args.tag} is consistent"
          + (" (assets re-hashed)" if args.full else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
