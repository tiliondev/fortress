"""
Tests for tools/verify_release.py — the release consistency checker.

evaluate() is pure: it takes an already-fetched release dict + SHA256SUMS body and returns
a Report, so every failure mode (missing asset, wrong hash, orphan checksum line, mismatched
SDK tables) can be driven offline without touching the GitHub API.

Run:  pytest tools/tests -q
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_release as vr  # noqa: E402

# The SDK table the checker validates against (linux is required; win/mac optional-if-present).
SDK_ASSETS = {
    "linux-x64": "tilion-fortress-linux-x64.tar.gz",
    "win-x64": "tilion-fortress-win-x64.zip",
    "mac-arm64": "tilion-fortress-mac-arm64.tar.gz",
    "mac-x64": "tilion-fortress-mac-x64.tar.gz",
}
NODE_NAMES = set(SDK_ASSETS.values())

LINUX = SDK_ASSETS["linux-x64"]
WIN = SDK_ASSETS["win-x64"]
H_LINUX = "f4e0e83a38b08ec62ec07cb7f0c54d8eae5e7260798a91e7d703e547de53207c"
H_WIN = "a538de3341d9e7bf1c87f81b0c6e91ec9c2bde3f80872a8f626dd074d1161a45"


def asset(name, digest=None, size=100, state="uploaded"):
    a = {"name": name, "size": size, "state": state, "url": f"https://api/{name}"}
    if digest:
        a["digest"] = f"sha256:{digest}"
    return a


def release(*assets):
    return {"assets": list(assets)}


def sums(*pairs):
    return "".join(f"{h}  {n}\n" for h, n in pairs)


def evaluate(rel, sums_text, **kw):
    kw.setdefault("node_asset_names", NODE_NAMES)
    return vr.evaluate(rel, sums_text, SDK_ASSETS, **kw)


# --------------------------------------------------------------------------- the happy path
def test_consistent_release_passes():
    # linux + win present and checksummed, SHA256SUMS present, mac absent (optional).
    rel = release(
        asset("SHA256SUMS"),
        asset(LINUX, digest=H_LINUX),
        asset(WIN, digest=H_WIN),
    )
    rep = evaluate(rel, sums((H_LINUX, LINUX), (H_WIN, WIN)))
    assert rep.failures == []


def test_linux_only_release_passes():
    rel = release(asset("SHA256SUMS"), asset(LINUX, digest=H_LINUX))
    rep = evaluate(rel, sums((H_LINUX, LINUX)))
    assert rep.failures == []


# --------------------------------------------------------------------------- missing assets
def test_missing_required_linux_asset_fails():
    rel = release(asset("SHA256SUMS"), asset(WIN, digest=H_WIN))
    rep = evaluate(rel, sums((H_WIN, WIN)))
    assert f"asset present: {LINUX}" in rep.failures


def test_missing_sha256sums_fails():
    rel = release(asset(LINUX, digest=H_LINUX))
    rep = evaluate(rel, sums((H_LINUX, LINUX)))
    assert "SHA256SUMS present" in rep.failures


def test_missing_optional_mac_is_skipped_not_failed():
    rel = release(asset("SHA256SUMS"), asset(LINUX, digest=H_LINUX))
    rep = evaluate(rel, sums((H_LINUX, LINUX)))
    assert rep.failures == []  # mac-arm64 / mac-x64 absent -> skipped, not a failure


# --------------------------------------------------------------------------- checksum problems
def test_wrong_hash_via_api_digest_fails():
    rel = release(asset("SHA256SUMS"), asset(LINUX, digest="deadbeef" * 8))
    rep = evaluate(rel, sums((H_LINUX, LINUX)))
    assert f"sha256 (API digest): {LINUX}" in rep.failures


def test_asset_without_sha256sums_entry_fails():
    rel = release(asset("SHA256SUMS"), asset(LINUX, digest=H_LINUX))
    rep = evaluate(rel, sums())  # empty SHA256SUMS
    assert f"checksummed: {LINUX}" in rep.failures


def test_orphan_sha256sums_entry_fails():
    rel = release(asset("SHA256SUMS"), asset(LINUX, digest=H_LINUX))
    rep = evaluate(rel, sums((H_LINUX, LINUX), ("cafef00d" * 8, "ghost-asset.tar.gz")))
    assert "no orphan SHA256SUMS entries" in rep.failures


def test_unuploaded_or_empty_asset_fails_sanity():
    rel = release(asset("SHA256SUMS"), asset(LINUX, digest=H_LINUX, size=0, state="starter"))
    rep = evaluate(rel, sums((H_LINUX, LINUX)))
    assert f"asset sane: {LINUX}" in rep.failures


# --------------------------------------------------------------------------- --full re-hashing
def test_full_mode_rehash_match_passes():
    rel = release(asset("SHA256SUMS"), asset(LINUX))  # no digest; --full hashes instead
    rep = evaluate(rel, sums((H_LINUX, LINUX)), full=True, hasher=lambda n: H_LINUX)
    assert rep.failures == []


def test_full_mode_rehash_mismatch_fails():
    rel = release(asset("SHA256SUMS"), asset(LINUX))
    rep = evaluate(rel, sums((H_LINUX, LINUX)), full=True, hasher=lambda n: "0" * 64)
    assert f"sha256 (re-hashed): {LINUX}" in rep.failures


# --------------------------------------------------------------------------- SDK table parity
def test_mismatched_sdk_tables_fails():
    rel = release(asset("SHA256SUMS"), asset(LINUX, digest=H_LINUX))
    rep = evaluate(rel, sums((H_LINUX, LINUX)), node_asset_names={"something-else.tar.gz"})
    assert "SDK asset tables agree (python == node)" in rep.failures


# --------------------------------------------------------------------------- parsing
def test_parse_sha256sums_handles_binary_marker_and_case():
    parsed = vr.parse_sha256sums(f"AA11BB22  {LINUX}\ncafef00d *{WIN}\n")
    assert parsed == {LINUX: "aa11bb22", WIN: "cafef00d"}
