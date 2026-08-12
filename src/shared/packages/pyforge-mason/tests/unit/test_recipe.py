"""Story 2.6 -- `recipe.py::build()`: the first `recipe` verb's use-case
module.

Resolves the CFE root and raises `CfeUnresolvedError` before any subprocess
spawns when it cannot be found; otherwise dispatches to `cfe.build_native`
(default) or `cfe.build_docker` (`docker=True`) -- proven against Story
1.9's `fake_cfe_root` fixture, real subprocess, no mocking (mirrors this
suite's established fixture-round-trip style for a CFE-dependent
use-case, e.g. `test_cfe.py`'s `validate_recipe`/`submit_pr` coverage)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pyforge.mason.errors import CfeUnresolvedError
from pyforge.mason.models import BuildResult
from pyforge.mason.recipe import build

_FIXTURE_ENV_VARS = ("MASON_FIXTURE_STDOUT", "MASON_FIXTURE_EXIT_CODE", "MASON_FIXTURE_PROGRESS_LINE")


def _clear_fixture_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _FIXTURE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# --- I/O & Edge-Case Matrix --------------------------------------------------

def test_build_native_happy_path_against_fake_cfe_root(fake_cfe_root, monkeypatch):
    _clear_fixture_env(monkeypatch)
    monkeypatch.setattr("pyforge.mason.cfe.detect_native_build_config", lambda: "linux64")

    result = build(
        "recipes/foo",
        docker=False,
        config=None,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=None,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=Path("/does/not/matter"),
    )

    assert isinstance(result, BuildResult)
    assert result.mode == "native"
    assert result.config == "linux64"
    assert result.artifact_dir == "build_artifacts/linux64"
    assert result.returncode == 0


def test_build_docker_happy_path_against_fake_cfe_root(fake_cfe_root, monkeypatch):
    _clear_fixture_env(monkeypatch)

    result = build(
        "recipes/foo",
        docker=True,
        config="linux64",
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=sys.executable,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=Path("/does/not/matter"),
    )

    assert isinstance(result, BuildResult)
    assert result.mode == "docker"
    assert result.config == "linux64"
    assert result.artifact_dir == "build_artifacts/linux64"
    assert result.returncode == 0


def test_build_propagates_cfe_unresolved_error_before_any_subprocess_spawns(tmp_path):
    """No `.claude/scripts/conda-forge-expert/` marker anywhere under
    `tmp_path` -- `ensure_cfe_root` must raise before either adapter is ever
    reached."""
    with pytest.raises(CfeUnresolvedError):
        build(
            "recipes/foo",
            docker=False,
            config=None,
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=tmp_path,
        )


def test_build_docker_propagates_cfe_unresolved_error_too(tmp_path):
    with pytest.raises(CfeUnresolvedError):
        build(
            "recipes/foo",
            docker=True,
            config="linux64",
            cfe_root_arg=None,
            cfe_python_arg=None,
            cfe_timeout_arg=None,
            environ={},
            start_directory=tmp_path,
        )


def test_build_native_never_resolves_a_cfe_interpreter(fake_cfe_root, monkeypatch):
    """spec Always boundary: the native path invokes its script through
    `bash`, never a resolved CFE interpreter -- resolving one for this path
    would be dead work."""
    _clear_fixture_env(monkeypatch)
    monkeypatch.setattr("pyforge.mason.cfe.detect_native_build_config", lambda: None)

    def _boom(*args, **kwargs):
        raise AssertionError("resolve_cfe_interpreter must not be called for the native path")

    monkeypatch.setattr("pyforge.mason.recipe.resolve_cfe_interpreter", _boom)

    result = build(
        "recipes/foo",
        docker=False,
        config=None,
        cfe_root_arg=str(fake_cfe_root),
        cfe_python_arg=None,
        cfe_timeout_arg=15.0,
        environ={},
        start_directory=Path("/does/not/matter"),
    )

    assert result.mode == "native"


def test_build_docker_resolves_a_cfe_interpreter_from_the_flag(fake_cfe_root, monkeypatch):
    """`cfe_python_arg` reaches `cfe.build_docker`'s `interpreter=` --
    proven by pointing it at a nonexistent interpreter and observing the
    resulting `OSError` propagate, rather than the fixture's real
    `sys.executable` silently being used instead."""
    _clear_fixture_env(monkeypatch)

    with pytest.raises(OSError):
        build(
            "recipes/foo",
            docker=True,
            config="linux64",
            cfe_root_arg=str(fake_cfe_root),
            cfe_python_arg="/definitely/not/a/real/interpreter",
            cfe_timeout_arg=15.0,
            environ={},
            start_directory=Path("/does/not/matter"),
        )
