# Contributing to Fortress

Fortress is a stealth Chromium engine that corrects fingerprint surfaces in the browser's **C++**,
then exposes raw CDP on `http://localhost:9222` as a drop-in for Playwright and Puppeteer. This
guide covers how to report a detection and how to get a change merged.

## The single most valuable contribution

**A page that reliably flags Fortress.** A minimal, reproducible detector — a URL or short script
that separates Fortress from real Chrome — is worth more than any feature. Open an issue with the
**Detection vector** template.

Before filing, sanity-check it is a **fingerprint** issue and not an **IP** one: roughly 90% of
"it got blocked" reports are the datacenter IP getting flagged before any page script runs. Re-run
through a residential or mobile proxy first — if it clears, the fingerprint was fine. See rule 4 in
[AGENTS.md](AGENTS.md).

## Two house rules

1. **Every claim ships with a way to reproduce it.** A patch that changes a surface comes with the
   command or test page that shows the before/after.
2. **Every limitation is written down.** If a patch is partial, say so in the patch header and the
   docs. The word *undetectable* stays out of this project — we correct specific, named surfaces.

## How the patch set is organized

Fortress is a set of source patches applied to a pinned Chromium checkout (`CHROMIUM_VERSION`), not
a runtime library.

- **`patches/`** — one patch per file, numbered, **single-surface**. `0002`/`0003` are the
  `base::UxrConfig` singleton every override reads from; the rest each touch one place.
- **`patches/series`** — the apply order. **A patch not listed here is silently skipped** by
  `build/apply-patches.sh`, so always add your patch to `series`.
- **`build/apply-patches.sh`** applies the series onto a Chromium `src/`.
- **`tools/gauntlet.py`** — the live detection harness (CreepJS / Sannysoft / BrowserScan).

Full build instructions: [docs/BUILD_NATIVE.md](docs/BUILD_NATIVE.md). Expect a multi-hour first
compile; incremental rebuilds after a one-line patch are minutes.

### The de-branded switch prefix — do not rename it

Runtime overrides are exposed as `--uxr-*` flags read through `base::UxrConfig`. That prefix is
intentional and **must stay `uxr`** — a neutral token so the binary carries no product string a
detector could match. A new surface means a new `--uxr-<surface>` flag; never a `--fortress-*` /
`--tilion-*` flag, and never a brand string literal baked into the binary.

## Before you open a PR — run the checks

CI runs these on every PR; run them locally first (`make check`):

```bash
python tools/check_patches.py      # patch-set integrity (series, numbering, single-surface, uxr-only)
python -m pytest sdk/python/tests -q
```

Optionally install the git hooks so they run automatically:

```bash
pip install pre-commit && pre-commit install
```

## Submitting a change

1. **Open an issue first** for anything beyond a typo, so we can agree on the surface and approach.
2. **Branch** from `main`, focused on one surface / one fix.
3. **One patch per file, single-surface**, and add it to `patches/series`.
4. **Verify** with `tools/gauntlet.py`; paste the before/after into the PR.
5. **Rebase, don't merge** — `git fetch && git rebase origin/main` before pushing. The patch set is
   rebased monthly onto new Chromium; a linear history keeps that sane.

Docs, examples, the gauntlet, packaging, and the SDKs do **not** require a Chromium build — a great
place to start.

## Security

A page that *fingerprints* Fortress is not a security issue — file it in the open. A crash, sandbox
escape, or host leak **is** — report it privately per [SECURITY.md](SECURITY.md).

## Licensing

Fortress is BSD-3-Clause (a Chromium derivative — see [LICENSE](LICENSE) and [NOTICE](NOTICE)). By
contributing, you agree your contribution is licensed under the same terms.
