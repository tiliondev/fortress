#!/usr/bin/env bash
# Fortress native macOS build.
#
# Prereqs (see docs/BUILD_NATIVE.md):
#   - Xcode + `xcode-select --install`
#   - ~100 GB free disk, long build time
#   - git, python3
#
# Usage:
#   build/macos/build.sh [workdir] [arm64|x64]
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="${1:-$REPO/.fortress-build-mac}"
ARCH="${2:-arm64}"
VER="${CHROMIUM_VERSION:-$(cat "$REPO/CHROMIUM_VERSION")}"
mkdir -p "$WORK"

echo "==> Fortress macOS build | Chromium $VER | $ARCH | $WORK"

# 1. depot_tools
if [ ! -d "$WORK/depot_tools" ]; then
  git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git "$WORK/depot_tools"
fi
export PATH="$WORK/depot_tools:$PATH"

# 2. fetch + sync
if [ ! -d "$WORK/chromium/src" ]; then
  mkdir -p "$WORK/chromium"; ( cd "$WORK/chromium" && fetch --nohooks --no-history chromium )
fi
cd "$WORK/chromium/src"
git fetch --depth 1 origin "refs/tags/$VER:refs/tags/$VER"
git checkout -f "tags/$VER"
gclient sync -D --no-history --reset

# 3. apply Fortress patches
"$REPO/build/apply-patches.sh" "$WORK/chromium/src"

# 4. configure (override target_cpu for Intel) + build
ARGS="$(cat "$REPO/build/args.macos.gn")"
[ "$ARCH" = "x64" ] && ARGS="${ARGS/target_cpu = \"arm64\"/target_cpu = \"x64\"}"
gn gen out/Fortress --args="$ARGS"
autoninja -C out/Fortress chrome

echo "==> Done: $WORK/chromium/src/out/Fortress/Chromium.app"
