# Phase 0 — CLASSIFIER

**Repository:** `fortress` (tiliondev/fortress)
**Date:** 2026-07-05
**Analyst:** J1-PIPELINE CLASSIFIER

---

## PROJECT_CLASS Determination

| Dimension | Value | Evidence |
|-----------|-------|----------|
| Primary | **Web** | Stealth Chromium engine — a browser binary exposing CDP on `:9222` |
| Secondary | **C++** | 35 C++ patches to Blink, V8, BoringSSL (`patches/`) |
| Secondary | **Python** | Python SDK (`sdk/python/`) — `tilion-fortress` PyPI package |
| Secondary | **Docker** | Multi-stage Dockerfile (`packaging/Dockerfile`), published as `tilion/fortress` |
| Secondary | **Security** | Fingerprint spoofing, anti-detection, stealth engine |
| Secondary | **Agent** | Drop-in browser for AI agent frameworks (browser-use, Crawl4AI, Stagehand, LangChain) |

### Classification: `Web, C++, Python, Docker, Security, Agent`

---

## Supporting Evidence

- **35 C++ patches** in `patches/` — single-surface diffs to Blink, V8, BoringSSL
- **Python SDK** at `sdk/python/` — `tilion-fortress` on PyPI, auto-downloads prebuilt binary
- **Node SDK** at `sdk/node/` — `tilion-fortress` on npm
- **Docker image** at `packaging/Dockerfile` — multi-stage Debian-based, non-root user
- **CI/CD** at `.github/workflows/ci.yml` — patch integrity, Python SDK tests, shellcheck, Node syntax
- **CodeQL** at `.github/workflows/codeql.yml` — Python, JavaScript, TypeScript analysis
- **Gauntlet** at `tools/gauntlet.py` — live detection test harness (CreepJS, Sannysoft, BrowserScan)
- **AGENTS.md** — dedicated agent setup guide for AI frameworks
- **llms.txt** — LLM-friendly summary for AI agent consumption

---

## j1.yaml

```yaml
repo: fortress
class: Web, C++, Python, Docker, Security, Agent
org: tiliondev
owner: arham766
license: BSD-3-Clause
production_score: 0
last_audit: 2026-07-05
standards_version: "2.1"
dependencies: []
deploy_target: production
tailscale_only: false
public_facing: true
```
