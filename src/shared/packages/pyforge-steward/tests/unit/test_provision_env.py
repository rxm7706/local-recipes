"""`load_pixi_environments` + `materialize_environment` + `provision --env`
CLI dispatch — Story 3.1.

Covers the I/O matrix's happy-path materialization, unknown-name, and
dogfooding-target rows, both at the primitive level and through the CLI
(`main(["provision", "--env", ...])`). The real `pixi install -e <name>`
invocation is never exercised here — `subprocess.run` is monkeypatched to a
fast fixture (mirrors `test_deploy_build.py`'s own rationale: the real
`pyforge-steward` env resolve is slow/network-dependent in a unit test).
"""

from __future__ import annotations

import argparse
import subprocess

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.provision import (
    ProvisionDuty,
    load_pixi_environments,
    materialize_environment,
)

_PIXI_TOML = """\
[environments]
linux = ["linux", "python"]
build = { features = ["python", "build"] }
pyforge-steward = { features = ["pyforge-steward"], no-default-feature = true }
"""


def _write_pixi_toml(tmp_path):
    (tmp_path / "pixi.toml").write_text(_PIXI_TOML, encoding="utf-8")
    return tmp_path


def test_load_pixi_environments_reads_both_shorthand_and_table_shapes(tmp_path):
    root = _write_pixi_toml(tmp_path)

    environments = load_pixi_environments(cwd=root)

    assert environments["linux"] == ("linux", "python")
    assert environments["build"] == ("python", "build")
    assert environments["pyforge-steward"] == ("pyforge-steward",)


def test_load_pixi_environments_raises_file_not_found_for_a_missing_manifest(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_pixi_environments(cwd=tmp_path)


def test_materialize_environment_runs_pixi_install_and_succeeds(tmp_path, monkeypatch):
    calls = []

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    materialize_environment("pyforge-steward", cwd=tmp_path)

    assert calls == [["pixi", "install", "-e", "pyforge-steward"]]


def test_materialize_environment_propagates_a_nonzero_exit(tmp_path, monkeypatch):
    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="solve failed")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        materialize_environment("pyforge-steward", cwd=tmp_path)


def test_provision_env_via_cli_round_trips(tmp_path, monkeypatch):
    _write_pixi_toml(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),  # noqa: ARG005
    )

    rc = main(["provision", "--env", "pyforge-steward"])

    assert rc == EXIT_OK


def test_provision_env_unknown_name_reports_a_clear_error_not_a_raw_pixi_failure(
    tmp_path, monkeypatch
):
    _write_pixi_toml(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    calls = []
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **kwargs: calls.append(cmd),  # noqa: ARG005
    )

    duty = ProvisionDuty()
    result = duty.run(argparse.Namespace(env="not-a-real-env", runner=None, list=False, verify=False))

    assert result.ok is False
    assert "not-a-real-env" in result.summary
    assert "pyforge-steward" in result.summary  # names a valid environment
    assert calls == [], "an unknown env name must never reach the pixi subprocess"


def test_provision_env_unknown_name_via_cli_exits_failed(tmp_path, monkeypatch):
    _write_pixi_toml(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--env", "not-a-real-env"])

    assert rc == EXIT_FAILED


def test_provision_env_malformed_pixi_toml_is_a_duty_failure_not_a_crash(tmp_path, monkeypatch):
    (tmp_path / "pixi.toml").write_text("this is [ not valid toml", encoding="utf-8")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    rc = main(["provision", "--env", "pyforge-steward"])

    assert rc == EXIT_FAILED


def test_provision_env_task_failure_surfaces_as_duty_failure(tmp_path, monkeypatch):
    _write_pixi_toml(tmp_path)
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="no space left on device")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    rc = main(["provision", "--env", "pyforge-steward"])

    assert rc == EXIT_FAILED


def test_bare_provision_degrades_and_names_available_flags():
    duty = ProvisionDuty()

    result = duty.run(argparse.Namespace())

    assert result.ok is True
    assert "--env" in result.summary
