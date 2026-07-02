#!/usr/bin/env bash
# Chromium 151 binds the DevTools endpoint to 127.0.0.1 only (it ignores
# --remote-debugging-address). Since `docker -p` forwards to the container's
# veth IP rather than its localhost, we run Chrome on an internal localhost
# port and bridge 0.0.0.0:9222 -> 127.0.0.1:9223 with socat. CDP clients that
# resolve the endpoint by URL (Playwright connect_over_cdp, Puppeteer connect)
# work transparently through the bridge.
set -e
INTERNAL=9223
EXTERNAL=9222

/opt/tilion/tilion \
  --headless=new \
  --no-sandbox \
  --enable-unsafe-swiftshader \
  --remote-debugging-port="$INTERNAL" \
  --user-data-dir=/tmp/tilion-profile \
  "$@" &
CHROME_PID=$!
trap 'kill "$CHROME_PID" 2>/dev/null || true' TERM INT

# Wait for Chrome's internal DevTools port to come up.
for _ in $(seq 1 80); do
  if (exec 3<>"/dev/tcp/127.0.0.1/$INTERNAL") 2>/dev/null; then exec 3>&-; break; fi
  sleep 0.5
done

exec socat TCP-LISTEN:"$EXTERNAL",fork,reuseaddr TCP:127.0.0.1:"$INTERNAL"
