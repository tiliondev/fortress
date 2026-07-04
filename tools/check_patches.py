#!/usr/bin/env python3
"""
check_patches.py - integrity linter for the Fortress patch set.

Fortress is a set of source patches applied to a pinned Chromium checkout
(see build/apply-patches.sh + patches/series). Several invariants are load-bearing
but were only ever enforced by human review. This linter enforces them mechanically
so CI can gate every PR:

  1. series-sync    - patches/series lists exactly the patches/*.patch files, once each,
                      in ascending numeric order. A patch that is not in series is silently
                      skipped by apply-patches.sh; an entry with no file breaks the build.
  2. numbering      - files are NNNN-*.patch, contiguous from 0001, no gaps, no duplicates.
  3. single-surface - each patch touches exactly ONE file (one `diff --git`). The project
                      rule is one patch per file so rebases stay legible.
  4. well-formed    - each patch has a `diff --git` header, ---/+++ file headers, and >=1 hunk.
  5. uxr-only       - any command-line switch a patch introduces uses the de-branded `uxr-`
                      prefix. A `--fortress-*` / `--tilion-*` switch would bake a brand token
                      into the binary and is forbidden.
  6. no-brand       - no added line introduces a quoted string literal containing a brand
                      token (tilion/tillion/fortress/phoron/swarm). Such a literal ships in
                      the binary's string table and is fingerprintable. (Comments are fine.)

Exit code 0 if every check passes, 1 otherwise. Pure standard library; no build tree needed.

    python tools/check_patches.py            # from the repo root
    python tools/check_patches.py --verbose
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PATCHES = REPO / "patches"
SERIES = PATCHES / "series"

# Brand tokens that must never appear as a compiled-in string literal.
BRAND_RE = re.compile(r'"[^"\n]*(tilion|tillion|fortress|phoron|swarm)[^"\n]*"', re.IGNORECASE)
# Command-line switch lookups a patch may add.
SWITCH_RE = re.compile(r'(?:HasSwitch|GetSwitchValueASCII|GetSwitchValueNative)\(\s*"([^"]+)"')
PATCH_NAME_RE = re.compile(r"^(\d{4})-.*\.patch$")


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {name}"
        if detail:
            line += f" - {detail}"
        print(line)
        if not ok:
            self.failures.append(name)


def _patch_files(patches_dir: Path) -> list[Path]:
    return sorted(p for p in patches_dir.glob("*.patch"))


def _strip_comment(added: str) -> str:
    """Drop a trailing // line comment so comments never trip the string checks."""
    i = added.find("//")
    return added[:i] if i != -1 else added


def check_series_sync(rep: Report, patches_dir: Path, verbose: bool) -> None:
    series = patches_dir / "series"
    if not series.exists():
        rep.check("series-sync", False, "patches/series is missing")
        return
    listed = [ln.strip() for ln in series.read_text().splitlines()
              if ln.strip() and not ln.strip().startswith("#")]
    listed_names = [Path(x).name for x in listed]
    actual = [p.name for p in _patch_files(patches_dir)]

    dupes = sorted({n for n in listed_names if listed_names.count(n) > 1})
    missing_file = [n for n in listed_names if n not in actual]        # in series, no file
    missing_entry = [n for n in actual if n not in listed_names]       # file, not in series
    ordered = listed_names == sorted(listed_names)

    ok = not dupes and not missing_file and not missing_entry and ordered
    detail = f"{len(listed_names)} entries / {len(actual)} files"
    if dupes:
        detail = f"duplicate series entries: {dupes}"
    elif missing_file:
        detail = f"series lists patches with no file: {missing_file}"
    elif missing_entry:
        detail = f"patch files not listed in series (would be skipped by apply-patches.sh): {missing_entry}"
    elif not ordered:
        detail = "series is not in ascending order"
    rep.check("series-sync", ok, detail)


def check_numbering(rep: Report, patches_dir: Path, verbose: bool) -> None:
    nums: list[int] = []
    bad_names: list[str] = []
    for p in _patch_files(patches_dir):
        m = PATCH_NAME_RE.match(p.name)
        if not m:
            bad_names.append(p.name)
        else:
            nums.append(int(m.group(1)))
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    expected = list(range(1, len(nums) + 1)) if nums else []
    gaps = sorted(set(expected) - set(nums))
    ok = not bad_names and not dupes and not gaps
    if bad_names:
        detail = f"non-conforming names: {bad_names}"
    elif dupes:
        detail = f"duplicate numbers: {[f'{n:04d}' for n in dupes]}"
    elif gaps:
        detail = f"missing numbers: {[f'{n:04d}' for n in gaps]}"
    else:
        detail = f"0001..{max(nums):04d} contiguous" if nums else "no patches"
    rep.check("numbering", ok, detail)


def check_bodies(rep: Report, patches_dir: Path, verbose: bool) -> None:
    """single-surface + well-formed + uxr-only + no-brand, per patch."""
    multi_file: list[str] = []
    malformed: list[str] = []
    bad_switch: list[str] = []
    brand_hits: list[str] = []

    for p in _patch_files(patches_dir):
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        diff_headers = [ln for ln in lines if ln.startswith("diff --git ")]
        has_minus = any(ln.startswith("--- ") for ln in lines)
        has_plus = any(ln.startswith("+++ ") for ln in lines)
        has_hunk = any(ln.startswith("@@") for ln in lines)

        if len(diff_headers) != 1:
            multi_file.append(f"{p.name} ({len(diff_headers)} files)")
        if not (diff_headers and has_minus and has_plus and has_hunk):
            malformed.append(p.name)

        for ln in lines:
            if not ln.startswith("+") or ln.startswith("+++"):
                continue
            added = _strip_comment(ln[1:])
            for sw in SWITCH_RE.findall(added):
                if not sw.startswith("uxr-"):
                    bad_switch.append(f"{p.name}: --{sw}")
            if BRAND_RE.search(added):
                brand_hits.append(f"{p.name}: {ln.strip()[:70]}")

    rep.check("single-surface", not multi_file,
              f"all patches touch one file" if not multi_file else f"multi-file: {multi_file}")
    rep.check("well-formed", not malformed,
              "all patches parse" if not malformed else f"malformed: {malformed}")
    rep.check("uxr-only-switches", not bad_switch,
              "all switches use the uxr- prefix" if not bad_switch else f"non-uxr: {bad_switch}")
    rep.check("no-brand-literals", not brand_hits,
              "no brand string literals in added code" if not brand_hits
              else f"brand literal would ship in binary: {brand_hits}")


def run_checks(patches_dir: Path, verbose: bool = False) -> Report:
    """Run every check against `patches_dir` and return the populated Report.

    The one seam the tests use: point this at a fixture directory (holding
    `*.patch` files and a `series`) to exercise each check in isolation.
    """
    rep = Report()
    check_series_sync(rep, patches_dir, verbose)
    check_numbering(rep, patches_dir, verbose)
    check_bodies(rep, patches_dir, verbose)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description="Integrity linter for the Fortress patch set.")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--patches-dir", type=Path, default=PATCHES,
                    help="directory holding the *.patch files and series (default: patches/)")
    args = ap.parse_args()

    patches_dir = args.patches_dir
    if not patches_dir.is_dir():
        print(f"error: {patches_dir} not found (run from the repo root)", file=sys.stderr)
        return 1

    try:
        where = patches_dir.resolve().relative_to(REPO)
    except ValueError:
        where = patches_dir
    print(f"Fortress patch-set linter - {len(_patch_files(patches_dir))} patches in {where}/")
    rep = run_checks(patches_dir, args.verbose)

    print("-" * 60)
    if rep.failures:
        print(f"FAILED: {len(rep.failures)} check(s): {', '.join(rep.failures)}")
        return 1
    print("OK: all patch-set checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
