#!/usr/bin/env bash
# Apply the Fortress patch series onto a Chromium src tree.
# Usage:  build/apply-patches.sh /path/to/chromium/src
# Uses 3-way apply so that, after a Chromium version bump, patches that still
# anchor cleanly apply automatically and only genuinely-moved ones are flagged.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:?usage: apply-patches.sh /path/to/chromium/src}"
SERIES="$REPO/patches/series"

cd "$SRC" || { echo "no such src tree: $SRC"; exit 1; }
ok=0; fail=0; failed=()
while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  p="$REPO/$rel"
  if git apply --3way --whitespace=nowarn "$p" 2>/dev/null; then
    ok=$((ok+1)); printf '  [ok]   %s\n' "$(basename "$rel")"
  elif git apply --check "$p" 2>/dev/null && git apply --whitespace=nowarn "$p" 2>/dev/null; then
    ok=$((ok+1)); printf '  [ok]   %s\n' "$(basename "$rel")"
  else
    fail=$((fail+1)); failed+=("$rel"); printf '  [FAIL] %s\n' "$(basename "$rel")"
  fi
done < "$SERIES"

echo "----------------------------------------------"
echo "applied: $ok   failed: $fail"
if [ "$fail" -gt 0 ]; then
  echo "Patches needing re-anchor against this Chromium version:"
  printf '   - %s\n' "${failed[@]}"
  echo "Fix: open the target file, locate the moved code, regenerate the patch with:"
  echo "   git -C \"$SRC\" diff -- <file> > \"$REPO/<patch>\""
  exit 2
fi
echo "All Fortress patches applied cleanly."
