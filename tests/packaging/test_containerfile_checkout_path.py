"""Regression gate for the Containerfile's fixed-short-path `WORKDIR`.

Story 7.1 hardcoded `WORKDIR /pyforge` in both build stages specifically because
`/pyforge` is short, literal, and NOT derived from the build host or a build
ARG/ENV -- it trivially avoids a documented `pixi-build-python` path-length
panic: `pixi-build-backends`' `crates/pixi-build-backend/src/tools.rs::
output_directory` does an unchecked `usize` subtraction that underflows once
`<workspace-root>` plus a per-package build-dir suffix exceeds 255 bytes, which
empirically panics around a ~173-byte workspace root for this repo's
package-name lengths (see `_bmad-output/projects/pyforge-steward/
planning-artifacts/research/technical-steward-pixi-workspace-member-research-
2026-07-25.md` § A3.1).

That rationale is documented as a comment in the Containerfile itself (Story
7.2), but a comment does not stop a future edit from lengthening the path or
swapping it for `ARG CHECKOUT_DIR` / `${SOME_VAR}`. This file is the guard: it
parses the Containerfile text and fails loudly if either stage's `WORKDIR`
stops being the literal `/pyforge`.

**Pure stdlib, by design.** Only `re` + `pathlib` + `pytest`, matching this
repo's other `tests/packaging` gates (see `test_dependency_completeness.py`),
so it runs in the deliberately lean `pyforge-ci` env with zero runtime
libraries installed. No Docker build here -- Story 7.5 owns the build-time
smoke gate; this property (a fixed, short, literal path) is fully verifiable
from the Containerfile text alone.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINERFILE = REPO_ROOT / "Containerfile"

EXPECTED_PATH = "/pyforge"

# The panic ceiling is ~173 bytes (empirically, for this repo's package-name
# lengths -- see the module docstring). 32 bytes is a wide, defensible margin
# well under that ceiling: it is 4x the length of the current `/pyforge` (8
# bytes) and would still catch any realistic regression -- e.g. a rename to
# something like `/home/containeruser/pyforge-checkout` (36 bytes) already
# trips it -- long before the path got anywhere near the actual panic
# threshold.
MAX_SAFE_WORKDIR_BYTES = 32

# Captures everything after `WORKDIR ` to end of line, NOT just a single
# whitespace-free token -- a template-substitution regression like
# `WORKDIR {{ checkout_path }}` contains internal spaces, and a `\S+`-only
# capture would silently fail to match that line at all (so it would never
# reach the derived-path check below). Trailing whitespace is stripped.
WORKDIR_LINE_RE = re.compile(r"^WORKDIR\s+(.+?)\s*$")


def _workdir_lines() -> list[tuple[int, str]]:
    """Every `WORKDIR <value>` directive as (1-indexed line number, value).

    Guards existence here, not only in `test_discovery_is_not_vacuous`, so
    that running any single test in this module in isolation (`pytest -k`,
    xdist sharding) still fails with a clear message instead of an unguarded
    `FileNotFoundError`.
    """
    assert CONTAINERFILE.is_file(), f"Containerfile missing: {CONTAINERFILE}"
    text = CONTAINERFILE.read_text(encoding="utf-8")
    results = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = WORKDIR_LINE_RE.match(line)
        if match:
            results.append((lineno, match.group(1)))
    return results


def test_discovery_is_not_vacuous():
    """If the regex ever stopped matching, every assertion below would iterate
    over an empty list and pass having checked nothing -- the one failure this
    file must never have."""
    assert CONTAINERFILE.is_file(), f"Containerfile missing: {CONTAINERFILE}"
    workdirs = _workdir_lines()
    assert len(workdirs) >= 2, (
        f"expected at least 2 WORKDIR directives (one per build stage), found "
        f"{len(workdirs)}: {workdirs}. Either a stage lost its WORKDIR or the "
        "parsing regex stopped matching -- both are regressions."
    )


def test_every_workdir_is_the_literal_fixed_path():
    """The AC: the checkout root is `/pyforge` in every build stage, and that
    value is a literal, not derived from the build host or a build ARG/ENV."""
    workdirs = _workdir_lines()
    wrong = [
        (lineno, value) for lineno, value in workdirs if value != EXPECTED_PATH
    ]
    assert not wrong, (
        f"Containerfile WORKDIR must be the literal {EXPECTED_PATH!r} in every "
        "stage (Story 7.1/7.2's fixed-short-path decision -- see the rationale "
        "comment above the builder stage's WORKDIR). Offending line(s): "
        + ", ".join(f"line {lineno}: {value!r}" for lineno, value in wrong)
    )


def test_no_workdir_is_host_or_build_derived():
    """`$VAR`, `${VAR}`, or `{{ template }}` in a WORKDIR value would mean the
    path is no longer a hardcoded literal -- exactly the host/build-time
    derivation the AC forbids, even if it happened to resolve to `/pyforge` at
    build time."""
    workdirs = _workdir_lines()
    derived = [
        (lineno, value)
        for lineno, value in workdirs
        if "$" in value or "{{" in value
    ]
    assert not derived, (
        "Containerfile WORKDIR must be a hardcoded literal, not derived from a "
        "build ARG/ENV or template substitution. Offending line(s): "
        + ", ".join(f"line {lineno}: {value!r}" for lineno, value in derived)
    )


def test_workdir_stays_well_under_the_panic_ceiling():
    """Even if a future edit kept the path literal, a materially longer one
    would erode the safety margin under the ~173-byte panic ceiling (see the
    module docstring). This guards the margin itself, not just the exact
    string, so it also catches e.g. `/pyforge-workspace-checkout-v2`."""
    workdirs = _workdir_lines()
    too_long = [
        (lineno, value, len(value.encode("utf-8")))
        for lineno, value in workdirs
        if len(value.encode("utf-8")) > MAX_SAFE_WORKDIR_BYTES
    ]
    assert not too_long, (
        f"Containerfile WORKDIR exceeds the {MAX_SAFE_WORKDIR_BYTES}-byte safety "
        f"margin (chosen well under the ~173-byte pixi-build-python panic "
        "ceiling documented in this file's module docstring). Offending "
        "line(s): "
        + ", ".join(
            f"line {lineno}: {value!r} ({length} bytes)"
            for lineno, value, length in too_long
        )
    )


@pytest.mark.parametrize(
    "line,expect_derived,expect_too_long",
    [
        # Long but literal -- exercises the byte-length check on its own.
        ("WORKDIR /home/containeruser/pyforge-checkout", False, True),
        # `$VAR` derived -- exercises the derived-path check on its own.
        ("WORKDIR ${CHECKOUT_DIR}", True, False),
        # `{{ template }}` derived -- the other derived-path spelling.
        ("WORKDIR {{ checkout_path }}", True, False),
    ],
)
def test_guard_logic_actually_fires_on_synthetic_regressions(
    line, expect_derived, expect_too_long
):
    """The four tests above only ever run against the real, already-correct
    Containerfile, so they never exercise their own failure branches -- a
    broken assertion (see this file's own history: an earlier revision's
    illustrative comment miscalculated a byte length) can ship unnoticed.
    This test drives the same regex and checks the real tests use, but
    against synthetic WORKDIR lines that are never written to disk, so it can
    assert each failure branch actually fires without corrupting the real
    Containerfile."""
    match = WORKDIR_LINE_RE.match(line)
    assert match, f"regex failed to match a syntactically valid WORKDIR line: {line!r}"
    value = match.group(1)

    assert value != EXPECTED_PATH, f"golden-path case leaked into regression cases: {line!r}"

    is_derived = "$" in value or "{{" in value
    is_too_long = len(value.encode("utf-8")) > MAX_SAFE_WORKDIR_BYTES
    assert is_derived == expect_derived, f"derived-path check mismatch for {line!r}"
    assert is_too_long == expect_too_long, f"byte-length check mismatch for {line!r}"
