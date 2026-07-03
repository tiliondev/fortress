# syntax=docker/dockerfile:1
# Fortress — stealth Chromium as a CDP endpoint. Works on any OS that runs Docker.
#
# Build (from a dir containing the extracted tilion-fortress/ bundle + packaging/docker-entrypoint.sh):
#   DOCKER_BUILDKIT=1 docker build -f packaging/Dockerfile -t tilion/fortress:latest .
# Run:
#   docker run --rm -p 9222:9222 tilion/fortress:latest
#   -> connect_over_cdp("http://localhost:9222")
#
# Size-optimized: ELF strip + locale trim in a throwaway prep stage (the toolchain never
# ships), and COPY --chown at copy time so the bundle is stored ONCE. (A `chown -R` RUN
# after a COPY rewrites every file's metadata and duplicates the whole bundle into a second
# layer.) Stealth is byte-identical after strip — verified (webdriver=false, persona UA,
# WebGL renderer string all unchanged).

# ---- stage 1: prep (throwaway — the binutils/strip toolchain stays here) ----
FROM debian:bookworm-slim AS prep
RUN apt-get update && apt-get install -y --no-install-recommends binutils \
    && rm -rf /var/lib/apt/lists/*
COPY tilion-fortress/ /opt/tilion/
RUN set -eux; \
    strip --strip-unneeded /opt/tilion/chrome 2>/dev/null || true; \
    strip --strip-unneeded /opt/tilion/chrome_crashpad_handler 2>/dev/null || true; \
    for so in /opt/tilion/*.so /opt/tilion/*.so.1; do strip --strip-unneeded "$so" 2>/dev/null || true; done; \
    find /opt/tilion/locales -type f -name '*.pak' ! -name 'en-US.pak' ! -name 'en-GB.pak' -delete; \
    chmod +x /opt/tilion/tilion /opt/tilion/chrome 2>/dev/null || true

# ---- stage 2: final ----
FROM debian:bookworm-slim
# Runtime libraries headless Chromium needs (fonts are bundled, so no font pkgs).
RUN apt-get update && apt-get install -y --no-install-recommends \
      libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
      libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
      libpango-1.0-0 libcairo2 libasound2 libxshmfence1 libglib2.0-0 \
      libvulkan1 mesa-vulkan-drivers fontconfig ca-certificates dumb-init socat \
    && rm -rf /var/lib/apt/lists/*
# Non-root user (headless Chromium runs unprivileged with --no-sandbox).
RUN useradd -m -u 1000 tilion
COPY --from=prep --chown=tilion:tilion /opt/tilion/ /opt/tilion/
COPY --chmod=0755 packaging/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
USER tilion
ENV HOME=/home/tilion
EXPOSE 9222
ENTRYPOINT ["dumb-init", "--", "/usr/local/bin/docker-entrypoint.sh"]
