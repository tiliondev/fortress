#!/usr/bin/env bash
# Fortress — native linux/arm64 (aarch64) build.
#
# Chromium ships NO prebuilt aarch64-linux clang or rust, so a native arm64 build
# must build the clang toolchain from source and supply an arm64 rust. This script
# encodes every arm64-specific step so the max-stealth Fortress Chromium (all 34+
# C++ patches, unchanged) can be reproduced on an aarch64 host (e.g. AWS Graviton,
# or a Linux arm64 VM for running under Lima/QEMU on Apple Silicon).
#
# Requirements: aarch64 Ubuntu 22.04/24.04 host, ~200 GB free disk, many cores,
# passwordless sudo (for apt). Usage:  build/build-arm64.sh [workdir]
#
# The stealth C++ patches are architecture-neutral (JS fingerprint surfaces) and
# apply unchanged; only the toolchain/build plumbing below is arm64-specific.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${1:-$REPO/.fortress-build}"
VER="${CHROMIUM_VERSION:-$(cat "$REPO/CHROMIUM_VERSION")}"
OUT="Fortress"
# Rust nightly matching the DATE of Chromium's pinned rust commit (tools/rust/update_rust.py).
# For Chromium 151.0.7908.0 that commit is dated 2026-06-16 -> nightly-2026-06-17.
RUST_DATE="${RUST_DATE:-2026-06-17}"
RUST_TC="$HOME/.rustup/toolchains/nightly-${RUST_DATE}-aarch64-unknown-linux-gnu"
export TMPDIR="${TMPDIR:-$WORK/tmp}"
mkdir -p "$WORK" "$TMPDIR"
export GCLIENT_SUPPRESS_GIT_VERSION_WARNING=1
ts(){ date -u +%H:%M:%S; }
[ "$(uname -m)" = "aarch64" ] || { echo "This script is for aarch64 hosts."; exit 1; }
echo "==> Fortress arm64 build | Chromium $VER | workdir $WORK"

# 0. Host packages: toolchain build prerequisites. The target libraries come from
#    Chromium's arm64 sysroot (installed below), so the -dev libs here are only
#    belt-and-suspenders for host tools; harmless to keep.
echo "[$(ts)] apt prerequisites"
sudo apt-get update -y
sudo apt-get install -y \
  cmake ninja-build lld gperf libclang-dev curl xz-utils python3 git pkg-config \
  libpipewire-0.3-dev libva-dev libgbm-dev libdrm-dev libpulse-dev libspeechd-dev \
  libxkbcommon-dev libxdamage-dev libxrandr-dev libxcomposite-dev libxcursor-dev \
  libxtst-dev libxss-dev libcups2-dev libgtk-3-dev libnss3-dev libasound2-dev \
  libatk1.0-dev libatk-bridge2.0-dev libpango1.0-dev libcairo2-dev libatspi2.0-dev \
  libdbus-1-dev libudev-dev libwayland-dev libglib2.0-dev libkrb5-dev libncurses-dev \
  libxshmfence-dev libx11-xcb-dev libxcb-dri3-dev

# 1. depot_tools
if [ ! -d "$WORK/depot_tools" ]; then
  git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git "$WORK/depot_tools"
fi
export PATH="$WORK/depot_tools:$HOME/.cargo/bin:$PATH"

# 2. fetch Chromium + sync (with the arm64 workarounds)
if [ ! -d "$WORK/chromium/src" ]; then
  mkdir -p "$WORK/chromium"
  # `fetch` runs an internal `gclient sync` that aborts on the gperf CIPD gap
  # (there is no linux-arm64 gperf package). That abort is expected and harmless
  # here: fetch has already checked out src/ + DEPS by the time cipd runs, which is
  # all we need before we patch DEPS and run our own sync below. Tolerate the exit.
  ( cd "$WORK/chromium" && fetch --nohooks --no-history chromium ) || true
  [ -f "$WORK/chromium/src/DEPS" ] || { echo "fetch did not lay down src/DEPS"; exit 1; }
fi
# Unmanaged solution so gclient won't reset our tag checkout / DEPS edit below.
cat > "$WORK/chromium/.gclient" <<'GC'
solutions = [
  { "name": "src",
    "url": "https://chromium.googlesource.com/chromium/src.git",
    "managed": False, "custom_deps": {}, "custom_vars": {} },
]
GC
cd "$WORK/chromium/src"
git fetch --depth 1 origin "refs/tags/$VER:refs/tags/$VER"
git checkout -f "tags/$VER"
# gperf has NO linux-arm64 CIPD package (only linux-amd64), which aborts `gclient sync`.
# Point the dep at linux-amd64 so cipd resolves; we overwrite it with native arm64 gperf.
python3 - <<'PY'
p="DEPS"; s=open(p).read()
o="infra/3pp/tools/gperf/${{platform}}"; n="infra/3pp/tools/gperf/linux-amd64"
open(p,"w").write(s.replace(o,n)) if o in s else None
PY
# gclient sync pulls hundreds of git/CIPD deps and can hit transient network
# failures (busy mirrors, HTTP 429 rate limiting). Retry with backoff; each retry
# resumes where the last left off, so only the incomplete deps are re-fetched.
for attempt in 1 2 3 4 5; do
  gclient sync -D --no-history && break
  [ "$attempt" = 5 ] && { echo "gclient sync failed after 5 attempts"; exit 1; }
  echo "[$(ts)] gclient sync attempt $attempt failed (transient?); retrying in $((attempt*30))s"
  sleep $((attempt*30))
done
gclient runhooks
./build/install-build-deps.sh --no-prompt || true
# Install Chromium's bundled arm64 sysroot (Debian bullseye, glibc 2.31) and build
# against it (use_sysroot=true below) so the binary links to old glibc/libgcc and
# runs on Debian 11/12/13+ — not just this host's glibc. runhooks skips it when the
# host arch != target, so install it explicitly.
python3 build/linux/sysroot_scripts/install-sysroot.py --arch=arm64
# Native arm64 gperf at the path blink's scripts.gni expects.
mkdir -p third_party/gperf/cipd/bin
cp -f "$(command -v gperf)" third_party/gperf/cipd/bin/gperf

# 3. Swap the x64 node for the pinned arm64 node (DEPS ships linux-x64 only).
NODE_VER="$(grep -oE 'NODE_VERSION="v[0-9.]+"' third_party/node/update_node_binaries | head -1 | grep -oE 'v[0-9.]+')"
echo "[$(ts)] node $NODE_VER (arm64 swap)"
curl -fsSL -o "$TMPDIR/node.tar.xz" "https://nodejs.org/dist/${NODE_VER}/node-${NODE_VER}-linux-arm64.tar.xz"
tar -C "$TMPDIR" -xf "$TMPDIR/node.tar.xz"
cp -f "$TMPDIR/node-${NODE_VER}-linux-arm64/bin/node" third_party/node/linux/node-linux-x64/bin/node

# 4. Build clang from source (no aarch64-linux prebuilt exists).
LLVM="third_party/llvm-build/Release+Asserts"
if [ ! -x "$LLVM/bin/clang" ] || [ "$(file -b "$LLVM/bin/clang" | grep -c aarch64)" = 0 ]; then
  echo "[$(ts)] building clang from source (this takes a while)"
  # build.py fetches an x86-64 cmake; replace with a native arm64 cmake at the same path.
  python3 tools/clang/scripts/build.py --without-android --without-fuchsia \
      --host-cc=/usr/bin/gcc --host-cxx=/usr/bin/g++ --disable-asserts \
      --with-ml-inliner-model='' 2>/dev/null || true   # first pass fetches sources, then fails on x86 cmake
  CMV=3.26.4
  if [ -e "third_party/llvm/../llvm-build-tools/cmake-${CMV}-linux-x86_64/bin/cmake" ] && \
     file -b "third_party/llvm/../llvm-build-tools/cmake-${CMV}-linux-x86_64/bin/cmake" | grep -q x86-64; then
    D="third_party/llvm/../llvm-build-tools"; rm -rf "$D/cmake-${CMV}-linux-x86_64"
    curl -fsSL -o "$TMPDIR/cmake.tgz" "https://github.com/Kitware/CMake/releases/download/v${CMV}/cmake-${CMV}-linux-aarch64.tar.gz"
    tar -C "$D" -xf "$TMPDIR/cmake.tgz"; mv "$D/cmake-${CMV}-linux-aarch64" "$D/cmake-${CMV}-linux-x86_64"
  fi
  # --with-ml-inliner-model='' : no arm64 TensorFlow wheel (compiler-internal opt; no effect on output).
  python3 tools/clang/scripts/build.py --without-android --without-fuchsia \
      --host-cc=/usr/bin/gcc --host-cxx=/usr/bin/g++ --disable-asserts \
      --with-ml-inliner-model='' --skip-checkout
fi

# 5. Rust: no aarch64-linux prebuilt either. Use a rustup nightly matching Chromium's rust date.
if ! command -v rustup >/dev/null 2>&1; then
  curl -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain none --profile minimal
  export PATH="$HOME/.cargo/bin:$PATH"
fi
rustup toolchain install "nightly-${RUST_DATE}" --profile minimal -c rust-src -c rustfmt \
  --target aarch64-unknown-linux-gnu
BINDGEN_VER="$(grep -oE 'corresponds to [0-9.]+' tools/rust/build_bindgen.py | grep -oE '[0-9.]+' || echo 0.72.1)"
[ -x "$LLVM/bin/bindgen" ] || cargo install "bindgen-cli@${BINDGEN_VER}" --locked --root "$WORK/bindgen"
cp -f "$WORK/bindgen/bin/bindgen" "$LLVM/bin/bindgen" 2>/dev/null || true
# bindgen needs a shared libclang (build.py makes only libclang.a) + rustfmt, at rust_bindgen_root.
ln -sf "$(ls /usr/lib/llvm-*/lib/libclang.so | head -1)" "$LLVM/lib/libclang.so"
ln -sf "$RUST_TC/bin/rustfmt" "$LLVM/bin/rustfmt"

# 6. Apply the Fortress stealth patch series (architecture-neutral, unchanged).
"$REPO/build/apply-patches.sh" "$WORK/chromium/src"

# 6b. bindgen here uses the system libclang (older than the in-tree clang), which
# rejects a few newer clang-only cflags. They are diagnostic/sanitizer/codegen flags
# irrelevant to bindgen's type extraction; drop them in Chromium's clang-arg filter.
FCA="third_party/../build/rust/gni_impl/filter_clang_args.py"
grep -q "fno-lifetime-dse" "$FCA" || python3 - "$FCA" <<'PY'
import sys
p=sys.argv[1]; s=open(p).read()
a="      elif args[i] == '-ftime-trace':\n        pass\n"
add=("      elif args[i] in ('-fdiagnostics-show-inlining-chain', '-fno-lifetime-dse'):\n        pass\n"
     "      elif (args[i].startswith('--warning-suppression-mappings') or\n"
     "            args[i].startswith('-fsanitize-ignore-for-ubsan-feature')):\n        pass\n")
open(p,"w").write(s.replace(a,a+add,1))
PY

# 7. Configure (stealth args + arm64 toolchain args) and build.
# rustc_version must be space-free (custom toolchain uses it verbatim as rustc_revision).
RUSTC_VER="$("$RUST_TC/bin/rustc" -V | sed 's/rustc //; s/[() ]/-/g; s/-\{2,\}/-/g; s/-$//')"
gn gen "out/$OUT" --args="$(cat "$REPO/build/args.arm64.gn")
clang_base_path = \"//third_party/llvm-build/Release+Asserts\"
clang_use_chrome_plugins = false
rust_sysroot_absolute = \"$RUST_TC\"
rustc_version = \"$RUSTC_VER\"
rust_bindgen_root = \"//third_party/llvm-build/Release+Asserts\"
rust_force_head_revision = true
toolchain_supports_rust_thin_lto = false
use_sysroot = true
use_siso = false
treat_warnings_as_errors = false"
autoninja -C "out/$OUT" chrome chrome_crashpad_handler

echo "==> Done: $WORK/chromium/src/out/$OUT/chrome"
"$WORK/chromium/src/out/$OUT/chrome" --version || true
