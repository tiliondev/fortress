#!/usr/bin/env bash
# Fortress full build: fetch depot_tools, sync Chromium to the pinned tag,
# apply patches, configure, and compile the stripped official binary.
#
# Usage:  build/build.sh [workdir]
#   workdir defaults to ./.fortress-build  (needs ~100GB free + many hours)
#
# Env:  CHROMIUM_VERSION  (defaults to the CHROMIUM_VERSION file)
#       TMPDIR            (point at a real disk; /tmp tmpfs will fill and fail)
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${1:-$REPO/.fortress-build}"
# Select GN args by host architecture. args.arm64.gn is identical to args.gn
# except for the architecture-bound bits (target_cpu + no x86 baseline cflags);
# all stealth patches are architecture-neutral. Override with ARGS_FILE=... .
case "$(uname -m)" in
  aarch64|arm64) ARGS_FILE="${ARGS_FILE:-$REPO/build/args.arm64.gn}" ;;
  *)             ARGS_FILE="${ARGS_FILE:-$REPO/build/args.gn}" ;;
esac
OUT="Fortress"
VER="${CHROMIUM_VERSION:-$(cat "$REPO/CHROMIUM_VERSION")}"
export TMPDIR="${TMPDIR:-$WORK/tmp}"
mkdir -p "$WORK" "$TMPDIR"

echo "==> Fortress build | Chromium $VER | out/$OUT | workdir $WORK"

# 1. depot_tools
if [ ! -d "$WORK/depot_tools" ]; then
  git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git "$WORK/depot_tools"
fi
export PATH="$WORK/depot_tools:$PATH"

# 2. fetch + sync to the pinned tag
if [ ! -d "$WORK/chromium/src" ]; then
  mkdir -p "$WORK/chromium"
  ( cd "$WORK/chromium" && fetch --nohooks --no-history chromium )
fi
cd "$WORK/chromium/src"
git fetch --depth 1 origin "refs/tags/$VER:refs/tags/$VER"
git checkout -f "tags/$VER"
gclient sync -D --no-history --with_branch_heads --reset

# 3. install build deps (first run; harmless to repeat)
./build/install-build-deps.sh --no-prompt || true

# 4. apply Fortress patches
"$REPO/build/apply-patches.sh" "$WORK/chromium/src"

# 5. configure + build
gn gen "out/$OUT" --args="$(cat "$ARGS_FILE")"
autoninja -C "out/$OUT" chrome chrome_crashpad_handler

echo "==> Done: $WORK/chromium/src/out/$OUT/chrome"
"$WORK/chromium/src/out/$OUT/chrome" --version
