# Fortress Persona Engine

Every Fortress launch presents a **unique, coherent, real-looking device** — a fresh fingerprint that looks like an ordinary person's machine, generated inside the browser engine before any page script runs.

This page describes *what* the persona engine does. The generator, its calibration data, and the engine-level delivery are Fortress's core technology and are not part of the open distribution.

## What you get

- **A different identity every launch.** No two sessions share a fingerprint by default, so sites can't link your sessions to one operator. The identity space is effectively unlimited.
- **Coherent, not random.** The *whole* device agrees with itself — GPU, screen, CPU/RAM, user-agent, timezone, language and fonts are mutually consistent, and impossible combinations never occur. Detectors that cross-check one surface against another find nothing out of place.
- **Real, not exotic.** Personas are drawn to match the *actual* population of real browsers, so each one blends into the crowd instead of standing out as unusual.
- **Native — no JavaScript injection.** Values are correct at the C++ engine level before a single line of page script executes. There are no wrapped functions or shimmed prototypes to catch, so native-integrity checks (`toString`, descriptors, prototype chains) pass by construction — including inside Web Workers and nested frames.
- **Zero-config.** A bare launch just works. Optionally pin a seed for a reproducible sticky identity, or pin a country so the persona's geo matches your proxy exit.

## Behavior

| Launch | Result |
|---|---|
| bare (no flags) | a fresh coherent persona, **different every time** |
| pinned seed | the **same** persona every time — a stable, reproducible identity |
| pinned country | timezone / language / fonts match that country; everything else stays seed-driven |

Nothing about the persona is exposed on the process command line, and no host-machine value ever leaks through.

## Why it stands out

Most stealth tooling randomizes fingerprints per-surface, which produces *individually plausible but jointly impossible* devices — a signal in itself. Fortress generates each persona as a **whole coherent machine calibrated to real-world data**, with a very large identity space and reproducible sticky identities when you want them. Because everything happens in the compiled engine, it is a **real browser**, not an instrumented one.

## Using it

Fortress is a drop-in for Playwright / Puppeteer — connect to its CDP endpoint and drive it exactly as you would Chrome. See the SDK in [`sdk/`](../sdk) and the project [README](../README.md). The persona engine is always on; you don't configure it unless you want a pinned seed or country.
