"""Every bootstrap failure carries a named remedy (Story 17.2's contract for
``setup`` / ``initrepo`` / ``validate-fast``) -- the branches the happy-path
flow test never reaches: a checkout without ``pixi.toml``, a failing
``pixi install``, a failing ``pre-commit install``, unmet prereqs, an
``environment.yaml`` that drifts or cannot be exported, and the two duties
whose ``RuntimeError`` (no repo root) must project as a ``DutyResult``, not a
crash (AD-8). Surfaced by the touched-module coverage floor on Story 63.6
(2026-09-20): ``bootstrap.py`` sat at 79.8% against the 80% unit floor.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest
from pyforge.steward import bootstrap
from pyforge.steward.bootstrap import (
    InitDuty,
    ShellInitDuty,
    _tool_version,
    initrepo_steps,
    setup_steps,
    validate_fast_steps,
)


def _called(cmd: str, *, stderr: str = "", stdout: str = "") -> subprocess.CalledProcessError:
    return subprocess.CalledProcessError(1, cmd, output=stdout, stderr=stderr)


def _raise(exc: BaseException):
    def _inner(*_a, **_k):
        raise exc

    return _inner


def _ns(*, as_json: bool) -> argparse.Namespace:
    return argparse.Namespace(json=as_json)


# ── _tool_version fails open ────────────────────────────────────────────────


def test_tool_version_returns_none_when_the_binary_cannot_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap.subprocess, "run", _raise(OSError("no exec")))
    assert _tool_version("git", "/nonexistent/git") is None
    monkeypatch.setattr(bootstrap.subprocess, "run", _raise(_called("git --version")))
    assert _tool_version("git", "/usr/bin/git") is None


def test_tool_version_falls_back_to_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = subprocess.CompletedProcess(["x", "--version"], 0, stdout="", stderr="tool 3.14.1\n")
    monkeypatch.setattr(bootstrap.subprocess, "run", lambda *a, **k: proc)
    assert _tool_version("tool", "/usr/bin/tool") == "3.14.1"


# ── setup_steps remedies ────────────────────────────────────────────────────


def test_setup_without_pixi_toml_stops_at_pixi_install_with_remedy(tmp_path: Path) -> None:
    steps = setup_steps(dest=tmp_path, url=None, env="pyforge-guild")
    names = [s.name for s in steps]
    assert names == ["clone", "pixi-install"]
    assert steps[0].ok and "skipped" in steps[0].detail
    assert not steps[1].ok
    assert "pixi.toml" in steps[1].detail
    assert steps[1].remedy == "pixi-install: checkout must contain pixi.toml"


def test_setup_pixi_install_failure_names_the_last_stderr_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pixi.toml").write_text("[workspace]\nname='x'\n", encoding="utf-8")
    monkeypatch.setattr(
        bootstrap, "materialize_environment",
        _raise(_called("pixi install", stderr="first line\nsolve failed: conflict\n")),
    )
    steps = setup_steps(dest=tmp_path, url=None, env="pyforge-guild")
    assert [s.name for s in steps] == ["clone", "pixi-install"]
    assert not steps[-1].ok
    assert steps[-1].detail == "solve failed: conflict"
    assert steps[-1].remedy == f"pixi-install: from {tmp_path} run `pixi install -e pyforge-guild`"


def test_setup_hooks_failure_is_a_step_not_a_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pixi.toml").write_text("[workspace]\nname='x'\n", encoding="utf-8")
    (tmp_path / bootstrap._PRE_COMMIT_CONFIG_RELATIVE_PATH).write_text("repos: []\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "materialize_environment", lambda *_a, **_k: None)
    monkeypatch.setattr(
        bootstrap, "_run_pre_commit_install",
        _raise(_called("pre-commit install", stdout="hook install failed\n")),
    )
    steps = setup_steps(dest=tmp_path, url=None, env="pyforge-guild")
    hooks = next(s for s in steps if s.name == "hooks")
    assert not hooks.ok
    assert hooks.detail == "hook install failed"
    assert hooks.remedy == f"hooks: from {tmp_path} run `pixi run -e pyforge-guild pre-commit install`"
    # A hooks failure does not truncate the sequence: pixi-install already passed.
    assert next(s for s in steps if s.name == "pixi-install").ok


def test_setup_without_pre_commit_config_skips_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pixi.toml").write_text("[workspace]\nname='x'\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "materialize_environment", lambda *_a, **_k: None)
    steps = setup_steps(dest=tmp_path, url=None, env="pyforge-guild")
    hooks = next(s for s in steps if s.name == "hooks")
    assert hooks.ok and "skipped" in hooks.detail


# ── validate_fast_steps remedies ────────────────────────────────────────────


def _prereq(name: str, ok: bool, remedy: str | None = None) -> bootstrap.PrereqResult:
    return bootstrap.PrereqResult(name=name, ok=ok, found=None, required=None, remedy=remedy)


def test_validate_fast_unmet_prereqs_name_the_first_remedy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        bootstrap, "gather_prereqs",
        lambda **_k: (_prereq("git", True), _prereq("pixi", False, "pixi: install it"), _prereq("gh", False)),
    )
    steps = validate_fast_steps(root=tmp_path, env="pyforge-guild")
    assert [s.name for s in steps] == ["prereqs"]
    assert not steps[0].ok
    assert steps[0].detail == "pixi, gh"
    assert steps[0].remedy == "pixi: install it"


def test_validate_fast_unmet_prereqs_without_remedy_fall_back_to_steward_init(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bootstrap, "gather_prereqs", lambda **_k: (_prereq("gh", False),))
    (step,) = validate_fast_steps(root=tmp_path, env="pyforge-guild")
    assert step.remedy == "init: run `steward init` and apply remedies"


@pytest.mark.parametrize("exc", [FileNotFoundError("pixi"), _called("pixi project export")])
def test_validate_fast_env_sync_export_failure_names_the_export_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    monkeypatch.setattr(bootstrap, "gather_prereqs", lambda **_k: (_prereq("git", True),))
    (tmp_path / "environment.yaml").write_text("name: x\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "check_environment_sync", _raise(exc))
    steps = validate_fast_steps(root=tmp_path, env="pyforge-guild")
    assert [s.name for s in steps] == ["prereqs", "env-sync"]
    assert not steps[1].ok
    assert "pixi project export conda-environment -e build" in (steps[1].remedy or "")


def test_validate_fast_env_sync_drift_stops_the_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bootstrap, "gather_prereqs", lambda **_k: (_prereq("git", True),))
    (tmp_path / "environment.yaml").write_text("name: x\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "check_environment_sync", lambda **_k: (False, "-a\n+b\n"))
    steps = validate_fast_steps(root=tmp_path, env="pyforge-guild")
    assert steps[-1].name == "env-sync"
    assert not steps[-1].ok
    assert steps[-1].detail == "environment.yaml drift"


def test_validate_fast_without_environment_yaml_skips_env_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bootstrap, "gather_prereqs", lambda **_k: (_prereq("git", True),))
    monkeypatch.setattr(bootstrap, "_run_steward_version", lambda **_k: "steward 0.1.0")
    steps = validate_fast_steps(root=tmp_path, env="pyforge-guild")
    env_sync = next(s for s in steps if s.name == "env-sync")
    assert env_sync.ok and "skipped" in env_sync.detail


# ── initrepo_steps remedies ─────────────────────────────────────────────────


def test_initrepo_pixi_install_failure_names_remedy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pixi.toml").write_text("[workspace]\nname='x'\n", encoding="utf-8")
    monkeypatch.setattr(
        bootstrap, "materialize_environment",
        _raise(_called("pixi install", stderr="no candidates\n")),
    )
    steps = initrepo_steps(root=tmp_path, env="pyforge-guild")
    assert steps[-1].name == "pixi-install"
    assert not steps[-1].ok
    assert steps[-1].detail == "no candidates"
    assert steps[-1].remedy == f"pixi-install: from {tmp_path} run `pixi install -e pyforge-guild`"


# ── duties project RuntimeError as evidence, never a crash (AD-8) ───────────


@pytest.mark.parametrize("as_json", [False, True])
def test_init_duty_reports_a_missing_repo_root(monkeypatch: pytest.MonkeyPatch, as_json: bool) -> None:
    monkeypatch.setattr(bootstrap, "gather_prereqs", _raise(RuntimeError("repo root not found")))
    result = InitDuty().run(_ns(as_json=as_json))
    assert result.ok is False
    if as_json:
        assert json.loads(result.summary) == {"ok": False, "error": "init: repo root not found"}
    else:
        assert result.summary == "init: repo root not found"


@pytest.mark.parametrize("as_json", [False, True])
def test_shell_init_duty_reports_a_missing_repo_root(
    monkeypatch: pytest.MonkeyPatch, as_json: bool
) -> None:
    monkeypatch.setattr(bootstrap, "format_shell_init", _raise(RuntimeError("repo root not found")))
    result = ShellInitDuty().run(_ns(as_json=as_json))
    assert result.ok is False
    if as_json:
        assert json.loads(result.summary) == {"ok": False, "error": "shell-init: repo root not found"}
    else:
        assert result.summary == "shell-init: repo root not found"
