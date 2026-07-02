#!/usr/bin/env bash
# Monthly Chromium rebase for Fortress.
#   1. bump CHROMIUM_VERSION to the new stable tag
#   2. sync the tree, 3-way apply the patch series, report any conflicts
#   3. if all patches apply: rebuild + run the detection gauntlet as a gate
#
# Usage:  build/rebase-monthly.sh <new-version> [workdir]
#   e.g.  build/rebase-monthly.sh 152.0.7000.0
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NEW="${1:?usage: rebase-monthly.sh <new-chromium-version> [workdir]}"
WORK="${2:-$REPO/.fortress-build}"

echo "==> Rebasing Fortress: $(cat "$REPO/CHROMIUM_VERSION") -> $NEW"
echo "$NEW" > "$REPO/CHROMIUM_VERSION"

# Build (build.sh applies patches via apply-patches.sh, which reports conflicts).
if ! CHROMIUM_VERSION="$NEW" "$REPO/build/build.sh" "$WORK"; then
  echo "!! Rebase needs manual patch re-anchoring (see [FAIL] lines above)."
  echo "   Re-anchor the flagged patches, then re-run this script."
  exit 2
fi

# Gate: build a bundle and run the gauntlet. Block release on any regression.
"$REPO/packaging/build-bundle.sh" "$WORK/chromium/src/out/Fortress" "$REPO/fonts" "$WORK/dist"
echo "==> Running detection gauntlet gate..."
if python3 "$REPO/tools/gauntlet.py" --bundle "$WORK/dist/tilion-fortress"; then
  echo "==> PASS: $NEW is stealth-clean. Safe to package + publish."
else
  echo "!! FAIL: a fingerprint surface regressed on $NEW. Do NOT publish; investigate."
  exit 3
fi
