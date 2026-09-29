"""Suite-wide pytest fixtures for pyforge-mason (Story 1.9, AD-16).

`fake_cfe_root` exposes the on-disk fixture CFE root the whole suite can
resolve/invoke against instead of a real conda-forge-expert install.

`_restore_root_logging` (autouse) contains Story 1.10's `_configure_logging`
side effects to the test that caused them.

`exclude_cfe_rebuild_equivalence_tests` (Story 12.7, patched post-review) is a
shared helper for the "this story must not touch the CFE surface" story-diff
guards in tests/meta/{test_persona_consults_cfe,test_portal_last_diagnose}.py
-- previously duplicated verbatim in both files. The underlying git mechanics
(`_unsanctioned_cfe_commits`, `_existed_at_origin_main`) moved to
`pyforge.testing_kit.branch_diff_guard` (retro-2026-09-04 action item 11),
which every station's equivalent guard now shares."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from pyforge.testing_kit import existed_at_ref

# The mason-owned CFE-rebuild campaign (SPEC-conda-forge-expert-rebuild) added one
# equivalence-validation test file per compiled slice under CFE's own tests/integration/
# directory by design (Story 6.3 landed test_slice1_equivalence.py; Story 12.7 landed
# test_slice2_equivalence.py). Story 15.1 (2026-09-10) CLOSED the campaign: both compiled
# mirrors (cfe-recipe-generation/cfe-recipe-lifecycle) were retired, not cut over, and both
# equivalence tests were deleted with them -- slices 3-5 were never briefed and are now
# permanently out of scope, so no further test_sliceN_equivalence.py file will ever be
# added. This regex + helper are kept as a no-op historical guard: were such a file ever
# resurrected, it would still not edit SKILL.md, scripts/, reference/, guides/, or config/,
# so it still wouldn't be a "CFE surface replaced" violation of AD-15/FR-45 in the sense the
# two guards below exist to catch.
_CFE_REBUILD_EQUIVALENCE_TEST_RE = re.compile(
    r"^\.claude/skills/conda-forge-expert/tests/integration/test_slice\d+_equivalence\.py$"
)


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
        if _CFE_REBUILD_EQUIVALENCE_TEST_RE.match(p) and not existed_at_ref(root, p):
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
