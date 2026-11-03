"""Exercise the actual bundled launchers without a browser or network request."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def bundle(tmp_path):
    directory = tmp_path / "portable bundle"
    directory.mkdir()
    for name in ("tilion", "tilion.cmd", "tilion-activate", "tilion-activate.cmd", "tilion_activate.py"):
        shutil.copy2(REPO / "packaging" / name, directory / name)
    environment = dict(os.environ, HOME=str(tmp_path / "home"), USERPROFILE=str(tmp_path / "home"))
    environment.pop("TILION_LICENSE_KEY", None)
    return directory, environment


def invoke(bundle, *arguments):
    directory, environment = bundle
    if sys.platform == "win32":
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c",
                   f'call "{directory / "tilion.cmd"}" ' + " ".join(arguments)]
    else:
        command = ["bash", str(directory / "tilion"), *arguments]
    return subprocess.run(command, env=environment, text=True, encoding="utf-8",
                          capture_output=True, timeout=20)


def test_license_status_dispatches_before_browser_setup(bundle):
    result = invoke(bundle, "license", "status", "--json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "licensed": False, "mode": "v1", "tier": None, "exp": None, "source": None,
    }


def test_plain_license_status_handles_unicode_on_windows(bundle):
    result = invoke(bundle, "license", "status")
    assert result.returncode == 0, result.stderr
    assert "no license key" in result.stdout


def test_activation_rejects_malformed_tokens_without_writing_a_key(bundle):
    result = invoke(bundle, "activate", "--token", "not-a-license")
    assert result.returncode == 1
    assert "doesn't look like a license token" in result.stderr
    assert not (Path(bundle[1]["HOME"]) / ".tilion/license.jwt").exists()
