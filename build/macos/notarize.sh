#!/usr/bin/env bash
# Codesign + notarize the Fortress macOS app.
# Without notarization, Gatekeeper blocks the app on other Macs.
#
# Requires:
#   - An Apple Developer ID Application certificate in your keychain
#   - An app-specific password / notarytool keychain profile
#
# Usage:
#   build/macos/notarize.sh <Chromium.app> "Developer ID Application: NAME (TEAMID)" <notary-profile>
set -euo pipefail
APP="${1:?path to .app}"
IDENTITY="${2:?Developer ID Application identity}"
PROFILE="${3:?notarytool keychain profile name}"

echo "==> codesign (deep, hardened runtime)"
codesign --force --deep --options runtime --timestamp --sign "$IDENTITY" "$APP"

echo "==> zip + submit to Apple notary service"
ZIP="$(dirname "$APP")/fortress-notarize.zip"
ditto -c -k --keepParent "$APP" "$ZIP"
xcrun notarytool submit "$ZIP" --keychain-profile "$PROFILE" --wait

echo "==> staple the ticket"
xcrun stapler staple "$APP"
echo "==> Done. Verify: spctl -a -vvv \"$APP\""
