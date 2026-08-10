"""Suite-wide pytest fixtures for pyforge-mason (Story 1.9, AD-16).

`fake_cfe_root` exposes the on-disk fixture CFE root the whole suite can
resolve/invoke against instead of a real conda-forge-expert install.

`_restore_root_logging` (autouse) contains Story 1.10's `_configure_logging`
side effects to the test that caused them."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest


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
