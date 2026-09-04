"""Suite-wide pytest fixtures for pyforge-mason (Story 1.9, AD-16).

`fake_cfe_root` exposes the on-disk fixture CFE root the whole suite can
resolve/invoke against instead of a real conda-forge-expert install.

`_restore_root_logging` (autouse) contains Story 1.10's `_configure_logging`
side effects to the test that caused them.

`exclude_cfe_rebuild_equivalence_tests` (Story 12.7, patched post-review) is a
shared helper for the "this story must not touch the CFE surface" story-diff
guards in tests/meta/{test_persona_consults_cfe,test_portal_last_diagnose}.py
-- previously duplicated verbatim in both files."""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

import pytest

# The mason-owned CFE-rebuild campaign (SPEC-conda-forge-expert-rebuild, Epic 12) adds one
# equivalence-validation test file per compiled slice under CFE's own tests/integration/
# directory by design (Story 6.3 landed test_slice1_equivalence.py; Story 12.7 landed
# test_slice2_equivalence.py; slices 3-5 will add their own). These prove the compiled
# replacement matches the live original -- they do not edit SKILL.md, scripts/, reference/,
# guides/, or config/, so a NEWLY ADDED one is not a "CFE surface replaced" violation of
# AD-15/FR-45 in the sense the two guards below exist to catch.
_CFE_REBUILD_EQUIVALENCE_TEST_RE = re.compile(
    r"^\.claude/skills/conda-forge-expert/tests/integration/test_slice\d+_equivalence\.py$"
)


def _existed_at_origin_main(root: Path, path: str) -> bool:
    """True if `path` was already present in `origin/main`'s tree -- i.e. this
    diff MODIFIES an existing file rather than ADDING a new one."""
    result = subprocess.run(
        ["git", "cat-file", "-e", f"origin/main:{path}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


_CFE_SURFACE = ".claude/skills/conda-forge-expert"
_CFE_CHANGELOG = f"{_CFE_SURFACE}/CHANGELOG.md"


def _unsanctioned_cfe_commits(root: Path) -> list[str]:
    """Commits on this branch (``origin/main..HEAD``) that touch the CFE surface
    without being a sanctioned Rule-2 retro -- subject starts ``retro:`` AND the
    CFE CHANGELOG moves in the same commit, the fleet rule
    ``scripts/mason_cfe_surface_check.py`` enforces for mason. Merge commits are
    skipped (they restate their constituents); uncommitted CFE edits count as
    unsanctioned. A station story never touches the surface; a fleet hygiene
    branch may carry the one sanctioned retro (2026-09-04, PR #1043)."""
    shas = subprocess.check_output(
        ["git", "log", "--no-merges", "--format=%H", "origin/main..HEAD", "--", _CFE_SURFACE],
        cwd=root,
        text=True,
    ).split()
    bad: list[str] = []
    for sha in shas:
        subject = subprocess.check_output(
            ["git", "log", "-1", "--format=%s", sha], cwd=root, text=True
        ).strip()
        files = subprocess.check_output(
            ["git", "show", "--format=", "--name-only", sha], cwd=root, text=True
        ).split()
        if not (subject.startswith("retro:") and _CFE_CHANGELOG in files):
            bad.append(f"{sha[:10]} {subject}")
    dirty = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD", "--", _CFE_SURFACE], cwd=root, text=True
    ).split()
    if dirty:
        bad.append("uncommitted: " + ", ".join(dirty))
    return bad


def exclude_cfe_rebuild_equivalence_tests(root: Path, paths: list[str]) -> list[str]:
    """Filter a `_git_diff_names`/`_git_dirty_under` path list, dropping only
    paths that are BOTH (1) named per the sanctioned
    `test_slice<N>_equivalence.py` pattern AND (2) newly added relative to
    `origin/main` -- never an existing file being modified.

    The second condition matters: without it, a future story could silently
    weaken an assertion inside an already-merged `test_sliceN_equivalence.py`
    (the very file this campaign relies on to back its equivalence claims)
    and the "must not touch CFE" guards below would never catch it
    (adversarial review finding, Story 12.7 patch P3).
    """
    kept = []
    for p in paths:
        if _CFE_REBUILD_EQUIVALENCE_TEST_RE.match(p) and not _existed_at_origin_main(root, p):
            continue
        kept.append(p)
    return kept


@pytest.fixture(autouse=True)
def _restore_root_logging():
    """Snapshot and restore the root logger around every test (review pass,
    2026-08-10).

    `cli._configure_logging` calls `logging.basicConfig(..., force=True)`,
    which *removes* every existing root handler and installs its own
    `StreamHandler` bound to whatever `sys.stderr` is at that moment. Any
    test that runs `main()` therefore leaves the root logger holding a
    handler wrapping a per-test capture buffer that is about to be torn
    down, plus that command's level (`ERROR` under `--quiet`), for every
    test that follows.

    Nothing in the package emits a log record yet (Story 1.10's Never
    boundary), so today this leaks nothing visible -- which is exactly why
    it is worth fencing now, before Story 2.1 adds the first real `logging`
    call and the failure arrives as a mystery in an unrelated test.

    What this restores is handler *membership*, not handler *state* (review
    pass, 2026-08-10, second). `basicConfig(force=True)` `close()`s each
    handler it removes, so a saved handler is already dead by the time this
    re-adds it, and nothing can revive it. Harmless for the handlers that
    actually appear here -- pytest's `caplog` handler wraps a `StringIO`
    whose `close()` is a no-op, and a `FileHandler` opened in append mode
    reopens itself on the next record -- but a *write*-mode `FileHandler`,
    which is what `pytest --log-file` installs, stays closed and silently
    drops every record from the first `main()`-calling test onward. Run the
    suite without `--log-file`, or expect a truncated log rather than a
    failure.
    """
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    try:
        yield
    finally:
        for handler in root.handlers[:]:
            if handler not in saved_handlers:
                root.removeHandler(handler)
        for handler in saved_handlers:
            if handler not in root.handlers:
                root.addHandler(handler)
        root.setLevel(saved_level)


@pytest.fixture
def fake_cfe_root() -> Path:
    """Return the path to the fixture CFE root tree
    (`tests/fixtures/fake_cfe_root/`), containing a real
    `.claude/scripts/conda-forge-expert/` marker directory with stub
    scripts."""
    return Path(__file__).parent / "fixtures" / "fake_cfe_root"
