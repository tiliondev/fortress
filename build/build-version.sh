#!/usr/bin/env bash
# Build a specific Chromium version of Fortress into its OWN tree/out/bundle, so multiple
# versions (e.g. 149 stable + 151 latest) coexist without clobbering each other.
#
# Usage:  build/build-version.sh <chromium-version> [platform]
#   e.g.  build/build-version.sh 149.0.7827.200 linux-x64
#         build/build-version.sh 151.0.7908.0   linux-x64
#
# Each version gets its own workdir  .fortress-build-<major>/  (each needs ~100GB + hours).
# The patch series is 3-way applied; if a patch fails on an older/newer tree, re-anchor it
# (see DUAL_VERSION_BUILD.md) and re-run.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VER="${1:?usage: build-version.sh <chromium-version> [platform]}"
PLATFORM="${2:-linux-x64}"
MAJOR="${VER%%.*}"
WORK="$REPO/.fortress-build-$MAJOR"

echo "==> Fortress $MAJOR | Chromium $VER | workdir $WORK"

# Build the versioned tree (build.sh reads CHROMIUM_VERSION from the env).
CHROMIUM_VERSION="$VER" "$REPO/build/build.sh" "$WORK"

# Bundle with a VERSION-TAGGED asset name so both majors can ship in one release:
#   tilion-fortress-<major>-<platform>.tar.gz
DEST="$WORK/dist"
"$REPO/packaging/build-bundle.sh" "$WORK/chromium/src/out/Fortress" "$REPO/fonts" "$DEST" "$MAJOR-$PLATFORM"

echo "==> built: $WORK/chromium/src/out/Fortress/chrome"
echo "==> bundle: $DEST/tilion-fortress-$MAJOR-$PLATFORM.tar.gz"
echo "==> verify:  python3 $REPO/tools/gauntlet.py --bundle $DEST/tilion-fortress"
