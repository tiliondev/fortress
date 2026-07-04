"""
Unit tests for the tilion_fortress SDK.

These cover the pure, release-critical logic that decides *which* bundle a user gets and
whether it is trusted — the platform resolver, the persona->flag mapping, and the
SHA256SUMS parser — with no network and no browser launch. A regression here silently
ships the wrong binary or skips checksum verification, so it is worth gating in CI.

Run:  pytest sdk/python/tests -q
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

# Make `import tilion_fortress` work when tests run from the repo root or from sdk/python.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tilion_fortress as tf  # noqa: E402


# --------------------------------------------------------------------------- platform
@pytest.mark.parametrize("sysname,machine,expected", [
    ("Linux",   "x86_64", "linux-x64"),
    ("Linux",   "amd64",  "linux-x64"),
    ("Windows", "AMD64",  "win-x64"),
    ("Windows", "x86_64", "win-x64"),
    ("Darwin",  "arm64",  "mac-arm64"),
    ("Darwin",  "aarch64","mac-arm64"),
    ("Darwin",  "x86_64", "mac-x64"),
    ("Linux",   "aarch64", None),   # no arm64 Linux bundle yet -> unsupported
    ("Linux",   "armv7l",  None),
    ("FreeBSD", "amd64",   None),
])
def test_resolve_platform(monkeypatch, sysname, machine, expected):
    monkeypatch.setattr(tf.platform, "system", lambda: sysname)
    monkeypatch.setattr(tf.platform, "machine", lambda: machine)
    assert tf.resolve_platform() == expected


def test_every_resolvable_platform_has_an_asset():
    # Any key resolve_platform() can return must exist in the _ASSETS table, and every
    # launcher path must live under the bundle dir so extraction lands where _download expects.
    resolvable = {"linux-x64", "win-x64", "mac-arm64", "mac-x64"}
    assert resolvable <= set(tf._ASSETS)
    for plat, (asset, kind, launcher) in tf._ASSETS.items():
        assert asset.startswith("tilion-fortress-") and plat in asset
        assert kind in ("tar", "zip")
        assert launcher.startswith("tilion-fortress/")


# --------------------------------------------------------------------------- persona
def test_persona_args_empty():
    assert tf._persona_args(None) == []
    assert tf._persona_args({}) == []


def test_persona_args_known_keys_map_to_uxr_flags():
    args = tf._persona_args({"timezone": "America/New_York", "hw_concurrency": 16})
    assert "--uxr-timezone=America/New_York" in args
    assert "--uxr-hw-concurrency=16" in args


def test_persona_args_unknown_key_falls_back_to_uxr_prefix():
    # Unknown keys still become --uxr-<key-with-dashes>, never a bare or branded flag.
    args = tf._persona_args({"some_new_surface": "v"})
    assert args == ["--uxr-some-new-surface=v"]


def test_persona_args_are_all_uxr_prefixed():
    persona = {"platform": "Win32", "timezone": "UTC", "webgl_renderer": "ANGLE",
               "device_memory": 8, "screen_width": 1920, "canvas_seed": 42, "weird_key": "x"}
    for a in tf._persona_args(persona):
        assert a.startswith("--uxr-"), a


# --------------------------------------------------------------------------- checksums
def test_sha256_matches_hashlib(tmp_path):
    import hashlib
    f = tmp_path / "blob.bin"
    data = b"fortress" * 4096
    f.write_bytes(data)
    assert tf._sha256(f) == hashlib.sha256(data).hexdigest()


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body
    def read(self) -> bytes:
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False


def test_expected_sha_parses_matching_asset(monkeypatch):
    asset = tf._ASSETS["linux-x64"][0]
    body = (
        f"aa11bb22  {asset}\n"
        f"deadbeef  tilion-fortress-win-x64.zip\n"
    ).encode()
    monkeypatch.setattr(tf.urllib.request, "urlopen", lambda *a, **k: _FakeResp(body))
    assert tf._expected_sha(asset, "https://h") == "aa11bb22"


def test_expected_sha_handles_starred_binary_marker(monkeypatch):
    # `sha256sum` writes "<hash> *<file>" in binary mode; the parser strips the leading '*'.
    asset = tf._ASSETS["linux-x64"][0]
    body = f"cafef00d *{asset}\n".encode()
    monkeypatch.setattr(tf.urllib.request, "urlopen", lambda *a, **k: _FakeResp(body))
    assert tf._expected_sha(asset, "https://h") == "cafef00d"


def test_expected_sha_returns_none_when_absent(monkeypatch):
    body = b"aa11bb22  some-other-asset.tar.gz\n"
    monkeypatch.setattr(tf.urllib.request, "urlopen", lambda *a, **k: _FakeResp(body))
    assert tf._expected_sha(tf._ASSETS["linux-x64"][0], "https://h") is None


def test_expected_sha_swallows_network_error(monkeypatch):
    def boom(*a, **k):
        raise OSError("network down")
    monkeypatch.setattr(tf.urllib.request, "urlopen", boom)
    # Must degrade to None (caller then warns + skips), never raise.
    assert tf._expected_sha("anything", "https://h") is None


# --------------------------------------------------------------------------- release wiring
def test_channels_are_coherent():
    import re
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", tf.__version__)
    assert tf._REPO == "tiliondev/fortress"
    assert tf._DEFAULT_CHANNEL in tf._CHANNELS
    assert tf._DEFAULT_CHANNEL == "stable"          # 149 is the recommended default
    for ch, cfg in tf._CHANNELS.items():
        assert re.fullmatch(r"v\d+\.\d+\.\d+\.\d+", cfg["tag"])
        assert cfg["docker"].startswith("tilion/fortress")
    assert tf._CHANNELS["stable"]["tag"].startswith("v149")
    assert tf._CHANNELS["latest"]["tag"].startswith("v151")


def test_channel_resolution():
    assert tf.Fortress(channel="stable")._tag == "v149.0.7827.232"
    assert tf.Fortress(channel="latest")._tag == "v151.0.7908.0"
    assert tf.Fortress()._tag == tf.Fortress(channel=tf._DEFAULT_CHANNEL)._tag
    try:
        tf.Fortress(channel="nope"); assert False
    except ValueError:
        pass
