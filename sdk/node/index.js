// tilion-fortress (Node) — install & drive the Fortress stealth Chromium engine.
// Ships the prebuilt binary only (no engine source). Detects platform, downloads the
// matching bundle from the GitHub Release, verifies SHA256, caches it, launches with CDP.
// macOS/Windows fall back to the Docker image until native binaries are published.
import { spawn, spawnSync } from "node:child_process";
import { createWriteStream, existsSync, chmodSync, mkdirSync, createReadStream } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { pipeline } from "node:stream/promises";
import { createHash } from "node:crypto";

export const VERSION = "151.0.7908.0";
const REPO = "tiliondev/fortress";
// Two release channels. "stable" = Chromium 149 (recommended default — matches the Chrome version
// the mass of real users run). "latest" = 151 (newest engine). Override with { channel } or the
// FORTRESS_CHANNEL env var.
export const CHANNELS = {
  stable: { tag: "v149.0.7827.232", docker: "tilion/fortress:149" },
  latest: { tag: "v151.0.7908.0",   docker: "tilion/fortress:151" },
};
const DEFAULT_CHANNEL = process.env.FORTRESS_CHANNEL || "stable";
const CACHE = process.env.FORTRESS_BROWSERS_PATH || join(homedir(), ".cache", "tilion-fortress");
const hostFor = (tag) => process.env.FORTRESS_DOWNLOAD_HOST || `https://github.com/${REPO}/releases/download/${tag}`;

// platform key -> { asset, kind, launcher }
export const ASSETS = {
  "linux-x64": { asset: "tilion-fortress-linux-x64.tar.gz", kind: "tar", launcher: "tilion-fortress/tilion" },
  "win-x64":   { asset: "tilion-fortress-win-x64.zip",       kind: "zip", launcher: "tilion-fortress/tilion.cmd" },
  "mac-arm64": { asset: "tilion-fortress-mac-arm64.tar.gz",  kind: "tar", launcher: "tilion-fortress/tilion" },
  "mac-x64":   { asset: "tilion-fortress-mac-x64.tar.gz",    kind: "tar", launcher: "tilion-fortress/tilion" },
};

export function resolvePlatform() {
  const { platform, arch } = process;
  if (platform === "linux" && arch === "x64") return "linux-x64";
  if (platform === "win32" && arch === "x64") return "win-x64";
  if (platform === "darwin") return arch === "arm64" ? "mac-arm64" : "mac-x64";
  return null;
}

export function personaArgs(persona) {
  if (!persona) return [];
  const map = { platform: "--uxr-platform", timezone: "--uxr-timezone", languages: "--uxr-languages",
    webglRenderer: "--uxr-webgl-renderer", webglVendor: "--uxr-webgl-vendor",
    hwConcurrency: "--uxr-hw-concurrency", deviceMemory: "--uxr-device-memory",
    screenWidth: "--uxr-screen-width", screenHeight: "--uxr-screen-height", canvasSeed: "--uxr-canvas-seed" };
  return Object.entries(persona).map(([k, v]) => `${map[k] || `--uxr-${k}`}=${v}`);
}

export async function sha256(path) {
  const h = createHash("sha256");
  await pipeline(createReadStream(path), h);
  return h.digest("hex");
}

export async function expectedSha(asset, host) {
  try {
    const r = await fetch(`${host}/SHA256SUMS`);
    if (!r.ok) return null;
    for (const line of (await r.text()).split("\n")) {
      const p = line.trim().split(/\s+/);
      if (p.length === 2 && p[1].replace(/^\*/, "") === asset) return p[0].toLowerCase();
    }
  } catch { /* none */ }
  return null;
}

async function ensureNative(plat, host, tag) {
  const { asset, kind, launcher } = ASSETS[plat];
  const root = join(CACHE, tag, plat);   // cache per release tag so channels don't collide
  const launcherPath = join(root, launcher);
  if (existsSync(launcherPath)) return launcherPath;
  mkdirSync(root, { recursive: true });
  const archive = join(root, asset);
  process.stderr.write(`[tilion-fortress] downloading ${host}/${asset} ...\n`);
  const res = await fetch(`${host}/${asset}`);
  if (!res.ok) throw new Error(`download failed: ${res.status}`);
  await pipeline(res.body, createWriteStream(archive));

  const exp = await expectedSha(asset, host);
  if (exp) {
    const act = await sha256(archive);
    if (act !== exp) throw new Error(`SHA256 mismatch for ${asset}: expected ${exp}, got ${act}`);
    process.stderr.write("[tilion-fortress] SHA256 verified\n");
  } else {
    process.stderr.write("[tilion-fortress] WARNING: no SHA256SUMS published; skipping verification\n");
  }

  if (kind === "tar") {
    if (spawnSync("tar", ["xzf", archive, "-C", root], { stdio: "inherit" }).status !== 0)
      throw new Error("tar extraction failed");
  } else { // zip (Windows): use PowerShell Expand-Archive
    if (spawnSync("powershell", ["-NoProfile", "-Command",
        `Expand-Archive -Force -LiteralPath '${archive}' -DestinationPath '${root}'`],
        { stdio: "inherit" }).status !== 0) throw new Error("zip extraction failed");
  }
  if (!launcher.endsWith(".cmd") && existsSync(launcherPath)) chmodSync(launcherPath, 0o755);
  if (!existsSync(launcherPath)) throw new Error(`launcher missing after extract: ${launcherPath}`);
  return launcherPath;
}

async function assetExists(plat, host) {
  try { return (await fetch(`${host}/${ASSETS[plat].asset}`, { method: "HEAD" })).ok; }
  catch { return false; }
}

async function waitCdp(port, timeoutMs = 40000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try { const r = await fetch(`http://127.0.0.1:${port}/json/version`); if (r.ok) return (await r.json()).webSocketDebuggerUrl; }
    catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("Fortress CDP endpoint did not come up");
}

export class Fortress {
  constructor({ port = 9222, persona = null, extraArgs = [], headless = true, channel = DEFAULT_CHANNEL } = {}) {
    if (!CHANNELS[channel]) throw new Error(`unknown channel '${channel}'; use one of ${Object.keys(CHANNELS)}`);
    const { tag, docker } = CHANNELS[channel];
    Object.assign(this, { port, persona, extraArgs, headless, channel, tag, docker, host: hostFor(tag),
                          proc: null, dockerName: null, cdpUrl: null });
  }
  static async launch(opts) { return new Fortress(opts).start(); }

  async start() {
    const plat = resolvePlatform();
    const native = plat && (plat === "linux-x64" || await assetExists(plat, this.host));
    if (native) await this._startNative(plat); else this._startDocker();
    this.cdpUrl = await waitCdp(this.port);
    return this;
  }

  async _startNative(plat) {
    const launcher = await ensureNative(plat, this.host, this.tag);
    const args = [];
    if (this.headless) args.push("--headless=new", "--no-sandbox");
    args.push(`--remote-debugging-port=${this.port}`, `--user-data-dir=${join(CACHE, "profile")}`,
              ...personaArgs(this.persona), ...this.extraArgs);
    this.proc = spawn(launcher, args, { stdio: "ignore", shell: launcher.endsWith(".cmd") });
  }

  _startDocker() {
    if (spawnSync("docker", ["--version"]).status !== 0)
      throw new Error("No native binary for this platform yet and Docker not installed. Install Docker Desktop or use Linux x64.");
    this.dockerName = `tilion-fortress-${process.pid}-${this.port}`;
    const args = ["run", "-d", "--rm", "--name", this.dockerName, "-p", `${this.port}:9222`, this.docker,
      ...personaArgs(this.persona), ...this.extraArgs];
    if (spawnSync("docker", args, { stdio: "ignore" }).status !== 0) throw new Error("docker run failed");
  }

  async close() {
    if (this.proc) { this.proc.kill(); this.proc = null; }
    if (this.dockerName) { spawnSync("docker", ["rm", "-f", this.dockerName], { stdio: "ignore" }); this.dockerName = null; }
  }
}
export default Fortress;
