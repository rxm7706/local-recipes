"""Unit-suite fixtures (Story 82.9, FR-25).

``marshal gate evaluate --story`` and ``marshal deploy land-story`` write a redacted gate record into the
project's loop home (``<loop-home-root>/<slug>/...``) whenever their ``fs`` is the real ``LocalFs``. A test that
reaches either with a default ``LocalFs`` and does not name its own loop-home root would resolve the operator's
real ``~/.bmad-loops`` -- and write under it if a project of that name is provisioned there. This fixture
points every unit test's loop-home root at a fresh, empty directory instead, so no test can touch the real one
and a gate evaluation that finds no provisioned home takes the documented ``MRS-GATE-017`` no-record path.
A test that names its own root (``monkeypatch.setenv``) or wants the default (``monkeypatch.delenv``) simply
overrides this after it runs.
"""

from __future__ import annotations

import pytest

from pyforge.marshal.cli.init import ENV_LOOP_HOME_ROOT

@pytest.fixture(autouse=True)
def _pin_loop_home_root_under_tmp(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_LOOP_HOME_ROOT, str(tmp_path_factory.mktemp("loop-home-root")))


@pytest.fixture(autouse=True)
def _pin_cursor_config_dir_under_tmp(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 83.25: every Cursor launch copies the operator's ``cli-config.json`` from ``$CURSOR_CONFIG_DIR``
    (else ``$XDG_CONFIG_HOME/cursor``, else ``~/.cursor``). A unit test that reaches a Cursor launch must never
    read the operator's real config, and a CI runner has none, so the launch refused with MRS-DISP-061 there
    (#1867's first CI run). Point it at a minimal config under tmp; a test of the lookup order overrides it."""
    config_dir = tmp_path_factory.mktemp("cursor-config")
    (config_dir / "cli-config.json").write_text('{"version": 1}\n', encoding="utf-8")
    monkeypatch.setenv("CURSOR_CONFIG_DIR", str(config_dir))
