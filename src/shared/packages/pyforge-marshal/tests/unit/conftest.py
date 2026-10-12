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

import sysconfig
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture

from pyforge.marshal import dispatch_verify
from pyforge.marshal.cli.init import ENV_LOOP_HOME_ROOT

flag_provider = make_flag_provider_fixture()


def require_ruff_from_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 95.1: run real-ruff oracles against ``pyforge-marshal``'s ruff only."""
    scripts = Path(sysconfig.get_path("scripts"))
    ruff_exe = scripts / "ruff"
    if not ruff_exe.is_file():
        win_ruff = scripts / "ruff.exe"
        if not win_ruff.is_file():
            pytest.fail(
                "ruff not found under the test interpreter's scripts directory "
                "([feature.pyforge-marshal.dependencies]); run: pixi install -e pyforge-marshal"
            )
        ruff_exe = win_ruff
    monkeypatch.setenv("PATH", str(scripts))


@pytest.fixture
def ruff_from_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Put the test interpreter's ``ruff`` first on ``PATH`` (Story 95.1)."""
    require_ruff_from_test_env(monkeypatch)


class _EmptySessionGroup:
    """Hermetic default: unit tests never scan the host process table (Story 90.1)."""

    def iter_session_group_members(self, _session_leader_pid: int):
        return iter(())


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


@pytest.fixture(autouse=True)
def _hermetic_dispatch_session_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dispatch_verify, "_DEFAULT_SESSION_GROUP", _EmptySessionGroup())
