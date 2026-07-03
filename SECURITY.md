# Security Policy

## What counts as what

Fortress is a stealth Chromium engine, so please route two very different things to two
different places:

- **A detection vector** — a page or script that fingerprints Fortress and tells it apart from
  real Chrome — is **not** a security vulnerability. It is exactly what the project wants, and it
  belongs in a **public issue** (use the "Detection vector" template). The more reproducible, the
  better.
- **A vulnerability in Fortress itself** — a way to crash the binary, escape the sandbox, leak the
  host (files, environment, real IP outside the configured proxy), or compromise a machine running
  it — is a **security issue**. Report it **privately** (below), not in a public issue.

## Reporting a vulnerability

Please use **GitHub's private vulnerability reporting**: the **Security** tab of this repository →
**Report a vulnerability**. That keeps the report private to the maintainers while it is triaged.

Include, as far as you can:

- affected version (Docker tag, `pip`/`npm` version, or bundle + Chromium version from `CHROMIUM_VERSION`),
- the platform, and
- a minimal reproduction and the impact.

We aim to acknowledge a report within a few days and to keep you updated as we work on a fix.
Please give us a reasonable window to release a fix before disclosing publicly.

## Supported versions

Fortress tracks stable Chromium and is released from the tip of `main`. Security fixes land on the
**latest** release; older tagged releases are not maintained. Always verify a download against the
release `SHA256SUMS` (the `pip`/`npm` SDKs do this automatically).
