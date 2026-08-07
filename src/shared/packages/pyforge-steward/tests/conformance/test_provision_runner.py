"""`run_bmad_loop_worktree` + `provision --runner bmad-loop --env` CLI
dispatch — Story 3.2.

The real `scripts/bmad-loop-worktree` subprocess (which itself shells out to
`git worktree add` + `bmad-switch`) is never exercised here — `subprocess.run`
is monkeypatched to a fast fixture, mirroring `test_deploy_build.py`'s own
rationale. `materialize_environment`'s own subprocess call is the SECOND
subprocess call this story composes; both are faked independently so each
row of the I/O matrix can be driven precisely.
"""

from __future__ import annotations

import argparse
import subprocess

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.provision import ProvisionDuty, run_bmad_loop_worktree

_PIXI_TOML = """\
[environments]
pyforge-steward = { features = ["pyforge-steward"], no-default-feature = true }
"""


def _write_repo_fixture(tmp_path):
    (tmp_path / "pixi.toml").write_text(_PIXI_TOML, encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "bmad-loop-worktree").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return tmp_path


def test_run_bmad_loop_worktree_parses_the_provisioned_path(tmp_path, monkeypatch):
    root = _write_repo_fixture(tmp_path)
    worktree_path = str(tmp_path / "loops" / "pyforge-steward")

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        return subprocess.CompletedProcess(
            cmd, 0, stdout=f"worktree: {worktree_path} [loop/pyforge-steward]\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = run_bmad_loop_worktree("pyforge-steward", root=root)

    assert str(result) == worktree_path


def test_run_bmad_loop_worktree_parses_a_reused_worktree_line(tmp_path, monkeypatch):
    root = _write_repo_fixture(tmp_path)
    worktree_path = str(tmp_path / "loops" / "pyforge-steward")

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(  # noqa: ARG005
            cmd, 0, stdout=f"worktree: {worktree_path} (reused)\n", stderr=""
        ),
    )

    result = run_bmad_loop_worktree("pyforge-steward", root=root)

    assert str(result) == worktree_path


def test_run_bmad_loop_worktree_propagates_a_nonzero_exit(tmp_path, monkeypatch):
    root = _write_repo_fixture(tmp_path)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(
            returncode=1, cmd=cmd, stderr="error: no such BMAD project: not-a-project"
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        run_bmad_loop_worktree("not-a-project", root=root)


def test_run_bmad_loop_worktree_raises_on_an_unexpected_stdout_shape(tmp_path, monkeypatch):
    root = _write_repo_fixture(tmp_path)

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="unexpected\n", stderr=""),  # noqa: ARG005
    )

    with pytest.raises(RuntimeError):
        run_bmad_loop_worktree("pyforge-steward", root=root)


def test_provision_runner_bmad_loop_via_cli_round_trips(tmp_path, monkeypatch):
    root = _write_repo_fixture(tmp_path)
    worktree_path = str(tmp_path / "loops" / "pyforge-steward")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: root)

    call_log = []

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        call_log.append(cmd)
        if "bmad-loop-worktree" in cmd[1]:
            return subprocess.CompletedProcess(
                cmd, 0, stdout=f"worktree: {worktree_path} [loop/pyforge-steward]\n", stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    rc = main(["provision", "--runner", "bmad-loop", "--env", "pyforge-steward"])

    assert rc == EXIT_OK
    assert len(call_log) == 2, "expected one bmad-loop-worktree call + one pixi install call"
    assert call_log[1] == ["pixi", "install", "-e", "pyforge-steward"]


def test_provision_runner_bmad_loop_underlying_script_failure_surfaces_clearly(tmp_path, monkeypatch):
    root = _write_repo_fixture(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: root)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(
            returncode=1, cmd=cmd, stderr="error: worktree add failed:\nfatal: some git error"
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    duty = ProvisionDuty()
    result = duty.run(
        argparse.Namespace(runner="bmad-loop", env="pyforge-steward", list=False, verify=False)
    )

    assert result.ok is False
    assert "fatal: some git error" in result.summary


def test_provision_runner_bmad_loop_underlying_script_failure_via_cli_exits_failed(tmp_path, monkeypatch):
    root = _write_repo_fixture(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: root)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kwargs: (_ for _ in ()).throw(  # noqa: ARG005
            subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="boom")
        ),
    )

    rc = main(["provision", "--runner", "bmad-loop", "--env", "pyforge-steward"])

    assert rc == EXIT_FAILED


def test_provision_runner_bmad_loop_env_materialization_failure_names_the_worktree(
    tmp_path, monkeypatch
):
    """A failure materializing the env INSIDE an already-provisioned worktree
    must name the worktree path, not just the failing pixi command — the
    worktree is real, on-disk state that must never be silently unreported.
    """
    root = _write_repo_fixture(tmp_path)
    worktree_path = str(tmp_path / "loops" / "pyforge-steward")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: root)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        if "bmad-loop-worktree" in cmd[1]:
            return subprocess.CompletedProcess(
                cmd, 0, stdout=f"worktree: {worktree_path} [loop/pyforge-steward]\n", stderr=""
            )
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="solve failed")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    duty = ProvisionDuty()
    result = duty.run(
        argparse.Namespace(runner="bmad-loop", env="pyforge-steward", list=False, verify=False)
    )

    assert result.ok is False
    assert worktree_path in result.summary
    assert "solve failed" in result.summary


def test_provision_runner_unsupported_name_reports_a_clear_error():
    duty = ProvisionDuty()

    result = duty.run(
        argparse.Namespace(runner="not-bmad-loop", env="pyforge-steward", list=False, verify=False)
    )

    assert result.ok is False
    assert "not-bmad-loop" in result.summary


def test_provision_runner_unknown_env_name_never_reaches_the_worktree_subprocess(
    tmp_path, monkeypatch
):
    root = _write_repo_fixture(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: root)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))  # noqa: ARG005

    duty = ProvisionDuty()
    result = duty.run(
        argparse.Namespace(runner="bmad-loop", env="not-a-real-env", list=False, verify=False)
    )

    assert result.ok is False
    assert calls == []
