# Fortress v3 (Chromium 153.0.8010.36)

Fortress is a recompiled Chromium that corrects its own fingerprint in C++ (canvas, WebGL, WebGPU, audio, fonts, navigator, and 40 more surfaces) and exposes raw CDP, a drop-in for Playwright and Puppeteer. This release is the v3 engine, the offline license gate, and a new license.

## Highlights

- **A distinct machine every launch.** Each start mints a fresh, coherent persona across canvas, WebGL, WebGPU, audio, fonts, navigator, and hardware, verified 48 of 48 distinct across a clone fleet.
- **Recorded-human mouse motion.** A bank of real human cursor trajectories drives movement inside the engine, not a JavaScript overlay.
- **Widevine EME** on the Linux x64, Windows x64, and macOS builds for DRM playback.
- **Native per platform.** The same engine ships as a native binary for each OS, now including native Apple Silicon. A Windows build draws Windows personas (Win32, D3D11 GPUs), a Mac build draws Mac personas (Apple GPU, Metal), a real OS story a single host cannot fully emulate.
- **Free for developers, unlocked in one command.** `tilion activate` runs a browser sign-in that takes about ten seconds and saves your key to `~/.tilion/license.jwt`. The key is verified offline after that; Fortress never phones home or reports usage. Skip activation and it still runs, printing one notice and falling back to the public first-generation engine.
- **A new license.** Fortress moves from BSD to the Fortress Source Available License 1.1. Development, testing and evaluation stay free at any company size; production is free for individuals and for organizations under US$500,000 in cumulative funding and US$300,000 or less in ARR; every other organization buys one flat subscription.

## Downloads

Every bundle carries the license gate and the production key, and ships the launcher plus a bundled activator, so `tilion activate` works with no extra install.

| Platform | Artifact | Widevine |
|---|---|:---:|
| Linux x64 | `fortress-v153-linux-x64.tar.gz` | yes |
| Windows x64 | `fortress-v153-win-x64.zip` | yes |
| macOS arm64 (Apple Silicon) | `fortress-v153-mac-arm64.tar.gz` | yes |
| Linux arm64 | `fortress-v153-linux-arm64.tar.gz` | no |
| Linux x86 (32-bit) | `fortress-v153-linux-x86.tar.gz` | no |
| Linux armhf (32-bit ARM) | `fortress-v153-linux-armhf.tar.gz` | no |

macOS Intel (x64) follows in a later build.

### SHA-256

```
857c29ca7297488ebc87b64fdd80fd4acd417bfe7600d7ce4d16b601a84088e2  fortress-v153-linux-x64.tar.gz
0d8c8eaf9aa3e201a45d25f88734275722b228d11ff6ab03cd3183c5a7db14f4  fortress-v153-win-x64.zip
86b58d426291ec5d2ee503bd141596bb1f03d9fdb17a95b94d10b7ea5a431d0f  fortress-v153-mac-arm64.tar.gz
120f7e3de536b2fee57f29b9e3b6314ee39f088f3797d9fdad546e453cd070c4  fortress-v153-linux-arm64.tar.gz
35fab97ad4168a28d93b73866f30d610d34a3dbbc7cfa28f1fe6ea17fe2f370f  fortress-v153-linux-x86.tar.gz
55040c6c525ce95825194cea7ab222ebf0d0991cc691ff04274998ef8d2603d9  fortress-v153-linux-armhf.tar.gz
```

Downloads through the SDK are verified against `SHA256SUMS` automatically.

## Install

```bash
# Python / Node: prebuilt native binary auto-fetched, SHA-256 verified
pip install tilion-fortress
npm install tilion-fortress

# Any OS via Docker: raw CDP on :9222
docker run --rm -p 9222:9222 tilion/fortress:latest

# Portable tarball (Linux x64 / arm64 / x86 / armhf)
tar xzf fortress-v153-linux-x64.tar.gz
./fortress-v153/tilion https://example.com

# macOS arm64: extract in Terminal (avoids Gatekeeper quarantine)
tar xzf fortress-v153-mac-arm64.tar.gz
./fortress-v153/tilion --remote-debugging-port=9222 --user-data-dir=~/tf-profile

# Native Windows x64 (raw CDP, same --uxr-* overrides)
#   fortress-v153-win-x64\tillion.cmd --headless=new --remote-debugging-port=9222 --user-data-dir=C:\tmp\p
```

## The `tilion` CLI

Installing the SDK (`pip install tilion-fortress` or `npm install tilion-fortress`) puts the `tilion` command on your `PATH`. The portable tarball and the Docker image bundle the same activator, so it works everywhere with no extra install.

```bash
tilion activate                 # unlock v3: opens your browser, sign in, done
tilion activate --headless      # SSH or remote host: prints the URL and code to enter
tilion activate --token <jwt>   # CI, Docker, agents: save a key with no browser
tilion license status           # show the saved key's tier and expiry
tilion license refresh          # re-issue the key before it expires
tilion license logout           # remove the key and drop back to v1
tilion get [platform]           # download the build for this host ('tilion get list' shows all)
tilion mcp                      # run the Fortress MCP server (stealth browsing as agent tools)
tilion                          # launch the engine and print the CDP endpoint
```

Activation captures a verified name and email through one click (GitHub, Google, or email) and saves the key to `~/.tilion/license.jwt`. Each developer gets a unique key that auto-refreshes, so you activate once. For a fleet with no browser (CI, Docker, agents), set `TILION_LICENSE_KEY=<key>` in the environment, or run `tilion activate --token <key>`; one key covers the fleet. A valid key runs the full v3 engine; with no key Fortress runs the public first-generation engine after a single notice.

## Verify it is ours

```bash
sha256sum fortress-v153-linux-x64.tar.gz   # compare against the SHA-256 list above
```

## Notes

- The 32-bit builds (x86, armhf) and the Linux arm64 cross-build ship without the bundled Widevine CDM.
- The macOS build is Apple Silicon (arm64), ad-hoc signed; if you extract it in Finder rather than Terminal, clear quarantine once with `xattr -dr com.apple.quarantine fortress-v153`. macOS Intel (x64) follows later.
