#!/usr/bin/env bash
# Build a .deb that installs Fortress to /opt/tilion with a `tilion` command on PATH.
# Usage:  packaging/build-deb.sh <tilion-fortress bundle dir> <version> [dest dir]
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE="${1:?path to an extracted tilion-fortress/ bundle}"
VER="${2:?version, e.g. 151.0.7908.0}"
DEST="${3:-$(pwd)}"
PKG="$DEST/tilion-fortress_${VER}_amd64"

rm -rf "$PKG"; mkdir -p "$PKG/opt/tilion" "$PKG/usr/bin" "$PKG/DEBIAN"
cp -a "$BUNDLE/." "$PKG/opt/tilion/"
ln -sf /opt/tilion/tilion "$PKG/usr/bin/tilion"

INSTALLED_KB=$(du -sk "$PKG/opt" | cut -f1)
cat > "$PKG/DEBIAN/control" <<CTRL
Package: tilion-fortress
Version: $VER
Section: web
Priority: optional
Architecture: amd64
Maintainer: arham766 <arhamislam766@yahoo.com>
Installed-Size: $INSTALLED_KB
Depends: libnss3, libnspr4, libatk1.0-0, libatk-bridge2.0-0, libcups2, libdrm2, libxkbcommon0, libxcomposite1, libxdamage1, libxfixes3, libxrandr2, libgbm1, libpango-1.0-0, libcairo2, libasound2, libxshmfence1, libglib2.0-0, libvulkan1, fontconfig
Description: Fortress - stealth Chromium engine (Tilion)
 C++-patched Chromium engineered to be undetectable by anti-bot systems.
 Installs to /opt/tilion with a 'tilion' launcher on PATH that applies a
 coherent default Windows persona and bundled fonts.
CTRL

dpkg-deb --build --root-owner-group "$PKG" >/dev/null
echo "==> deb: ${PKG}.deb ($(du -h "${PKG}.deb" | cut -f1))"
