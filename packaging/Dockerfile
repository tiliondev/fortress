# Fortress — stealth Chromium as a CDP endpoint. Works on any OS that runs Docker.
#
# Build (from a dir containing the extracted tilion-fortress/ bundle):
#   docker build -f packaging/Dockerfile -t arham766/fortress:latest .
# Run:
#   docker run --rm -p 9222:9222 arham766/fortress:latest
#   -> connect_over_cdp("http://localhost:9222")
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
COPY tilion-fortress/ /opt/tilion/
COPY packaging/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /opt/tilion/tilion /usr/local/bin/docker-entrypoint.sh \
    && chown -R tilion:tilion /opt/tilion

USER tilion
ENV HOME=/home/tilion
EXPOSE 9222
ENTRYPOINT ["dumb-init", "--", "/usr/local/bin/docker-entrypoint.sh"]
