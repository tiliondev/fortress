"""
tilion-fortress — install and drive the Fortress stealth Chromium engine.

Ships the prebuilt binary only (no engine source). Detects the platform, downloads the
matching bundle from the official GitHub Release, verifies it against SHA256SUMS, caches
it, and launches it with a CDP endpoint. macOS/Windows fall back to the Docker image until
native binaries are published for that platform.

    from tilion_fortress import Fortress
    with Fortress() as f:
        print(f.cdp_url)   # connect any CDP client (Playwright/Puppeteer)
"""
from __future__ import annotations
import hashlib, json, os, platform, shutil, subprocess, sys, tarfile, time, urllib.request, zipfile
from pathlib import Path

__version__ = "151.0.7908.0.post1"
__all__ = ["Fortress", "resolve_platform"]

_REPO = "tiliondev/fortress"
_TAG = "v151.0.7908.0"   # engine release tag (decoupled from package version)
_DOCKER_IMAGE = "tilion/fortress:latest"
_CACHE = Path(os.environ.get("FORTRESS_BROWSERS_PATH",
                             Path.home() / ".cache" / "tilion-fortress"))
_HOST = os.environ.get("FORTRESS_DOWNLOAD_HOST",
                       f"https://github.com/{_REPO}/releases/download/{_TAG}")

# platform key -> (release asset, archive kind, launcher relative path)
_ASSETS = {
    "linux-x64":  ("tilion-fortress-linux-x64.tar.gz", "tar", "tilion-fortress/tilion"),
    "win-x64":    ("tilion-fortress-win-x64.zip",       "zip", "tilion-fortress/tilion.cmd"),
    "mac-arm64":  ("tilion-fortress-mac-arm64.tar.gz",  "tar", "tilion-fortress/tilion"),
    "mac-x64":    ("tilion-fortress-mac-x64.tar.gz",    "tar", "tilion-fortress/tilion"),
}


def resolve_platform() -> str | None:
    sysname, mach = platform.system(), platform.machine().lower()
    if sysname == "Linux" and mach in ("x86_64", "amd64"):
        return "linux-x64"
    if sysname == "Windows" and mach in ("amd64", "x86_64"):
        return "win-x64"
    if sysname == "Darwin":
        return "mac-arm64" if mach in ("arm64", "aarch64") else "mac-x64"
    return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _expected_sha(asset: str) -> str | None:
    """Fetch SHA256SUMS from the release and return the hash for `asset`."""
    try:
        with urllib.request.urlopen(f"{_HOST}/SHA256SUMS", timeout=30) as r:
            for line in r.read().decode().splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].lstrip("*") == asset:
                    return parts[0].lower()
    except Exception:
        return None
    return None


def _download(plat: str) -> Path:
    """Ensure the bundle for `plat` is present + verified; return the launcher path."""
    asset, kind, launcher_rel = _ASSETS[plat]
    root = _CACHE / __version__ / plat
    launcher = root / launcher_rel
    if launcher.exists():
        return launcher
    root.mkdir(parents=True, exist_ok=True)
    archive = root / asset
    url = f"{_HOST}/{asset}"
    sys.stderr.write(f"[tilion-fortress] downloading {url} ...\n")
    urllib.request.urlretrieve(url, archive)

    expected = _expected_sha(asset)
    if expected:
        actual = _sha256(archive)
        if actual != expected:
            archive.unlink(missing_ok=True)
            raise RuntimeError(f"SHA256 mismatch for {asset}: expected {expected}, got {actual}")
        sys.stderr.write("[tilion-fortress] SHA256 verified\n")
    else:
        sys.stderr.write("[tilion-fortress] WARNING: no SHA256SUMS published; skipping verification\n")

    if kind == "tar":
        with tarfile.open(archive) as t:
            t.extractall(root)
    else:
        with zipfile.ZipFile(archive) as z:
            z.extractall(root)
    archive.unlink(missing_ok=True)
    if launcher.exists() and not launcher.name.endswith(".cmd"):
        launcher.chmod(0o755)
    if not launcher.exists():
        raise RuntimeError(f"bundle extracted but launcher missing: {launcher}")
    return launcher


def _persona_args(persona: dict | None) -> list[str]:
    if not persona:
        return []
    mapping = {
        "platform": "--uxr-platform", "timezone": "--uxr-timezone",
        "languages": "--uxr-languages", "webgl_renderer": "--uxr-webgl-renderer",
        "webgl_vendor": "--uxr-webgl-vendor", "hw_concurrency": "--uxr-hw-concurrency",
        "device_memory": "--uxr-device-memory", "screen_width": "--uxr-screen-width",
        "screen_height": "--uxr-screen-height", "canvas_seed": "--uxr-canvas-seed",
    }
    return [f"{mapping.get(k, '--uxr-' + k.replace('_', '-'))}={v}" for k, v in persona.items()]


class Fortress:
    """A running Fortress instance exposing a CDP endpoint at ``cdp_url``."""

    def __init__(self, port: int = 9222, persona: dict | None = None,
                 extra_args: list[str] | None = None, headless: bool = True):
        self.port, self.persona, self.extra_args, self.headless = port, persona, extra_args or [], headless
        self._proc = self._docker_name = self.cdp_url = None

    def start(self) -> "Fortress":
        plat = resolve_platform()
        # native bundle exists for Linux today; native win/mac assets resolve here once published.
        native_ok = plat is not None and (plat == "linux-x64" or self._asset_exists(plat))
        if native_ok:
            self._start_native(plat)
        else:
            self._start_docker()
        self.cdp_url = self._wait_cdp()
        return self

    @staticmethod
    def _asset_exists(plat: str) -> bool:
        asset = _ASSETS[plat][0]
        try:
            req = urllib.request.Request(f"{_HOST}/{asset}", method="HEAD")
            with urllib.request.urlopen(req, timeout=15):
                return True
        except Exception:
            return False

    def _start_native(self, plat: str):
        launcher = _download(plat)
        args = [str(launcher)]
        if self.headless:
            args += ["--headless=new", "--no-sandbox"]
        args += [f"--remote-debugging-port={self.port}", f"--user-data-dir={_CACHE / 'profile'}"]
        args += _persona_args(self.persona) + self.extra_args
        self._proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _start_docker(self):
        if not shutil.which("docker"):
            raise RuntimeError(
                "No native Fortress binary for this platform yet and Docker is not installed. "
                "Install Docker Desktop, or run on Linux x64.")
        self._docker_name = f"tilion-fortress-{os.getpid()}-{self.port}"
        args = ["docker", "run", "-d", "--rm", "--name", self._docker_name,
                "-p", f"{self.port}:9222", _DOCKER_IMAGE] + _persona_args(self.persona) + self.extra_args
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL)

    def _wait_cdp(self, timeout: float = 40.0) -> str:
        deadline = time.time() + timeout
        url = f"http://127.0.0.1:{self.port}/json/version"
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    return json.load(r)["webSocketDebuggerUrl"]
            except Exception:
                time.sleep(0.5)
        raise TimeoutError("Fortress CDP endpoint did not come up")

    def close(self):
        if self._proc:
            self._proc.terminate(); self._proc = None
        if self._docker_name:
            subprocess.run(["docker", "rm", "-f", self._docker_name],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._docker_name = None

    def __enter__(self): return self.start()
    def __exit__(self, *exc): self.close()

    @classmethod
    def launch(cls, **kw) -> "Fortress": return cls(**kw).start()
