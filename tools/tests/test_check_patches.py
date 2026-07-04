"""
Tests for tools/check_patches.py — the patch-set integrity linter.

The linter gates every PR, so a regression in it could silently start passing bad patches:
the one thing it exists to prevent. Each test builds a tiny fixture patch-set in a temp
directory and asserts that a given check fails on exactly the violation it targets — and
that a clean set passes every check.

Run:  pytest tools/tests -q
"""
from __future__ import annotations
import sys
from pathlib import Path

# Make `import check_patches` work when tests run from the repo root or from tools/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_patches as cp  # noqa: E402


# --------------------------------------------------------------------------- fixture helpers
def make_patch(path="src/foo.cc", added=("  int x = 0;",), *,
               hunk=True, headers=True, second_file=None) -> str:
    """Build a unified-diff patch. Defaults are clean and well-formed; the keyword args let a
    test break exactly one property (drop the hunk / the file headers, add a second file)."""
    lines = [f"diff --git a/{path} b/{path}", "index 1234567..89abcde 100644"]
    if headers:
        lines += [f"--- a/{path}", f"+++ b/{path}"]
    if hunk:
        lines.append(f"@@ -1,2 +1,{2 + len(added)} @@")
        lines.append(" context above")
        lines += [f"+{a}" for a in added]
        lines.append(" context below")
    if second_file:  # a second `diff --git` -> two surfaces in one patch
        lines += [f"diff --git a/{second_file} b/{second_file}",
                  f"--- a/{second_file}", f"+++ b/{second_file}",
                  "@@ -1 +1,2 @@", " ctx", "+  added"]
    return "\n".join(lines) + "\n"


def write_set(root: Path, patches: dict[str, str], series: list[str] | None = None) -> Path:
    """Write patch files + a series into `root`. Series defaults to the files in sorted order."""
    for name, body in patches.items():
        (root / name).write_text(body, encoding="utf-8")
    if series is None:
        series = sorted(patches)
    (root / "series").write_text("\n".join(series) + "\n", encoding="utf-8")
    return root


# A clean two-patch set: contiguous numbering, in-sync series, one file each, well-formed,
# a uxr- switch (exercises the uxr-only pass path), no brand literals.
def clean_patches() -> dict[str, str]:
    return {
        "0001-alpha.patch": make_patch("core/alpha.cc",
                                        added=('  if (cmd.HasSwitch("uxr-alpha")) return;',)),
        "0002-beta.patch": make_patch("core/beta.cc", added=("  int y = 1;",)),
    }


# --------------------------------------------------------------------------- the clean baseline
def test_clean_set_passes_every_check(tmp_path):
    rep = cp.run_checks(write_set(tmp_path, clean_patches()))
    assert rep.failures == []


# --------------------------------------------------------------------------- series-sync
def test_series_sync_missing_entry(tmp_path):
    # A patch file exists but is not listed -> apply-patches.sh would silently skip it.
    write_set(tmp_path, clean_patches(), series=["0001-alpha.patch"])
    assert cp.run_checks(tmp_path).failures == ["series-sync"]


def test_series_sync_missing_file(tmp_path):
    # Series lists a patch with no backing file -> the build breaks.
    write_set(tmp_path, clean_patches(),
              series=["0001-alpha.patch", "0002-beta.patch", "0003-ghost.patch"])
    assert cp.run_checks(tmp_path).failures == ["series-sync"]


def test_series_sync_duplicate_entry(tmp_path):
    write_set(tmp_path, clean_patches(),
              series=["0001-alpha.patch", "0001-alpha.patch", "0002-beta.patch"])
    assert cp.run_checks(tmp_path).failures == ["series-sync"]


def test_series_sync_wrong_order(tmp_path):
    write_set(tmp_path, clean_patches(), series=["0002-beta.patch", "0001-alpha.patch"])
    assert cp.run_checks(tmp_path).failures == ["series-sync"]


# --------------------------------------------------------------------------- numbering
def test_numbering_gap(tmp_path):
    patches = {"0001-alpha.patch": make_patch("core/alpha.cc"),
               "0003-gamma.patch": make_patch("core/gamma.cc")}
    write_set(tmp_path, patches)  # series auto-syncs, so only numbering should trip
    assert cp.run_checks(tmp_path).failures == ["numbering"]


def test_numbering_duplicate_number(tmp_path):
    patches = {"0001-alpha.patch": make_patch("core/alpha.cc"),
               "0002-beta.patch": make_patch("core/beta.cc"),
               "0002-clone.patch": make_patch("core/clone.cc")}
    rep = cp.run_checks(write_set(tmp_path, patches))
    assert rep.failures == ["numbering"]


def test_numbering_non_conforming_name(tmp_path):
    patches = {"0001-alpha.patch": make_patch("core/alpha.cc"),
               "not-a-numbered.patch": make_patch("core/other.cc")}
    assert cp.run_checks(write_set(tmp_path, patches)).failures == ["numbering"]


# --------------------------------------------------------------------------- single-surface
def test_single_surface_two_files(tmp_path):
    patches = {"0001-alpha.patch": make_patch("core/one.cc", second_file="core/two.cc")}
    assert cp.run_checks(write_set(tmp_path, patches)).failures == ["single-surface"]


# --------------------------------------------------------------------------- well-formed
def test_well_formed_missing_hunk(tmp_path):
    patches = {"0001-alpha.patch": make_patch("core/alpha.cc", hunk=False)}
    assert cp.run_checks(write_set(tmp_path, patches)).failures == ["well-formed"]


def test_well_formed_missing_headers(tmp_path):
    patches = {"0001-alpha.patch": make_patch("core/alpha.cc", headers=False)}
    assert cp.run_checks(write_set(tmp_path, patches)).failures == ["well-formed"]


# --------------------------------------------------------------------------- uxr-only-switches
def test_uxr_only_rejects_non_uxr_switch(tmp_path):
    patches = {"0001-alpha.patch": make_patch(
        "core/alpha.cc", added=('  if (cmd.HasSwitch("legacy-mode")) return;',))}
    assert cp.run_checks(write_set(tmp_path, patches)).failures == ["uxr-only-switches"]


# --------------------------------------------------------------------------- no-brand-literals
def test_no_brand_literal_in_added_code(tmp_path):
    patches = {"0001-alpha.patch": make_patch(
        "core/alpha.cc", added=('  const char* k = "fortress-build";',))}
    assert cp.run_checks(write_set(tmp_path, patches)).failures == ["no-brand-literals"]


def test_brand_token_in_comment_is_allowed(tmp_path):
    # A `//` comment mentioning a brand does not ship as a string literal, so it must pass.
    patches = {"0001-alpha.patch": make_patch(
        "core/alpha.cc", added=("  int z = 0;  // fortress tweak",))}
    assert cp.run_checks(write_set(tmp_path, patches)).failures == []
