"""
Tests for tools/verify_release.py — the release consistency checker.

evaluate() is pure: it takes an already-fetched release dict + SHA256SUMS body and returns
a Report, so every failure mode (missing asset, wrong hash, orphan checksum line, mismatched
SDK tables) can be driven offline without touching the GitHub API.

Run:  pytest tools/tests -q
"""
from __future__ import annotations
import copy
import hashlib
import json
import sys
import zipfile
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


def test_release_names_keep_legacy_channels_compatible():
    assert vr.release_asset_names("v151.0.7908.0", SDK_ASSETS) == SDK_ASSETS


def test_release_names_support_current_versioned_bundles():
    names = vr.release_asset_names("v153.0.8010.68", SDK_ASSETS)
    assert names["linux-x64"] == "fortress-v153-linux-x64.tar.gz"
    assert names["win-x64"] == "fortress-v153-win-x64.zip"
    assert names["mac-arm64"] == "fortress-v153-mac-arm64.tar.gz"
    assert vr.release_asset_names("v156.0.8078.47", SDK_ASSETS)["linux-arm64"] == "fortress-v156-linux-arm64.tar.gz"


def test_versioned_release_verifies_without_legacy_filenames():
    names = vr.release_asset_names("v153.0.8010.68", SDK_ASSETS)
    rel = release(asset("SHA256SUMS"), asset(names["linux-x64"], digest=H_LINUX),
                  asset(names["win-x64"], digest=H_WIN))
    rep = vr.evaluate(rel, sums((H_LINUX, names["linux-x64"]), (H_WIN, names["win-x64"])),
                      names, required={"linux-x64", "win-x64"})
    assert rep.failures == []


def candidate_record():
    folder = Path(__file__).resolve().parents[2] / "releases/v153.0.8010.68"
    return json.loads((folder / "manifest.json").read_text()), (folder / "SHA256SUMS").read_text()


def test_checked_in_candidate_is_internally_consistent():
    manifest, text = candidate_record()
    assert vr.evaluate_manifest(manifest, text).failures == []


def test_candidate_rejects_missing_required_windows_build():
    manifest, text = candidate_record()
    manifest["assets"] = manifest["assets"][:1]
    assert "required platforms present" in vr.evaluate_manifest(manifest, text).failures


def test_candidate_rejects_license_bypass():
    manifest, text = candidate_record()
    manifest["license"]["bypass_enabled"] = True
    assert "native license bypass disabled" in vr.evaluate_manifest(manifest, text).failures


def test_candidate_rejects_duplicate_checksum_entries():
    manifest, text = candidate_record()
    assert "unique checksum entries" in vr.evaluate_manifest(manifest, text + text).failures


def test_candidate_rejects_unsafe_asset_paths():
    manifest, text = candidate_record()
    manifest["assets"][0]["name"] = "../fortress-v153-linux-x64.tar.gz"
    assert "manifest asset name: linux-x64" in vr.evaluate_manifest(manifest, text).failures


def test_candidate_checks_native_payload_and_excludes_personal_keys(tmp_path):
    name = "fortress-v153-win-x64.zip"
    engine = b"native engine fixture"
    client = b"activation client fixture"
    archive_path = tmp_path / name
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("fortress-v153-win-x64\\chrome.dll", engine)
        archive.writestr("fortress-v153-win-x64\\tilion_activate.py", client)
    manifest = {
        "tag": "v153.0.8010.68", "chromium_version": "153.0.8010.68", "required_platforms": ["win-x64"],
        "license": {"bypass_enabled": False, "personal_keys_bundled": False,
                    "activation_client_sha256": hashlib.sha256(client).hexdigest()},
        "assets": [{"platform": "win-x64", "name": name, "bytes": archive_path.stat().st_size,
                    "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                    "engine_file": "fortress-v153-win-x64/chrome.dll",
                    "engine_sha256": hashlib.sha256(engine).hexdigest()}],
    }
    text = sums((manifest["assets"][0]["sha256"], name))
    assert vr.evaluate_manifest(manifest, text, tmp_path).failures == []
    wrong_engine = copy.deepcopy(manifest)
    wrong_engine["assets"][0]["engine_sha256"] = "0" * 64
    assert f"native engine sha256: {name}" in vr.evaluate_manifest(wrong_engine, text, tmp_path).failures
    with zipfile.ZipFile(archive_path, "a") as archive:
        archive.writestr("fortress-v153-win-x64/license.jwt", b"must not ship")
    manifest["assets"][0].update(bytes=archive_path.stat().st_size,
                                  sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest())
    text = sums((manifest["assets"][0]["sha256"], name))
    assert f"archive paths and credential exclusion: {name}" in vr.evaluate_manifest(manifest, text, tmp_path).failures
