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
