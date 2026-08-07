"""`build_dashboard` + `deploy dashboard --build` CLI dispatch — Story 2.1.

Covers the I/O matrix's happy-path build, underlying-task-failure, and
bare-`deploy`-degrade rows, both at the primitive level (`build_dashboard`
directly) and through the CLI (`main(["deploy", "dashboard", "--build"])`).
The real `pixi run -e local-recipes dashboard-gen` invocation is never
exercised here — `cmd` is overridden with a fast fixture command (this
story's own spec, "Design Notes": the real `local-recipes` env is ~9.8GB).
"""

from __future__ import annotations

import subprocess
import sys

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.deploy import DeployDuty, build_dashboard


def test_build_dashboard_runs_the_given_command_and_succeeds(tmp_path):
    marker = tmp_path / "built.txt"
    result = build_dashboard(
        cwd=tmp_path,
        cmd=[sys.executable, "-c", f"open({str(marker)!r}, 'w').write('ok')"],
    )
    assert result.returncode == 0
    assert marker.read_text() == "ok"


def test_build_dashboard_propagates_a_nonzero_exit(tmp_path):
    import pytest

    with pytest.raises(subprocess.CalledProcessError):
        build_dashboard(cwd=tmp_path, cmd=[sys.executable, "-c", "import sys; sys.exit(3)"])


def test_deploy_dashboard_build_via_cli_round_trips(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pyforge.steward.deploy.repo_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", "pass"),
    )

    rc = main(["deploy", "dashboard", "--build"])

    assert rc == EXIT_OK


def test_deploy_dashboard_build_surfaces_a_task_failure_as_exit_failed(tmp_path, monkeypatch):
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        "pyforge.steward.deploy._DEFAULT_BUILD_CMD",
        (sys.executable, "-c", "import sys; sys.exit(1)"),
    )

    rc = main(["deploy", "dashboard", "--build"])

    assert rc == EXIT_FAILED


def test_deploy_duty_run_reports_ok_false_with_clear_summary_on_task_failure(tmp_path):
    import argparse

    duty = DeployDuty()
    ns = argparse.Namespace(deploy_verb="dashboard", build=True)

    original_build = build_dashboard

    def _failing_build(*, cwd, cmd=None):  # noqa: ARG001
        raise subprocess.CalledProcessError(
            returncode=7, cmd=["pixi", "run", "-e", "local-recipes", "dashboard-gen"], stderr="boom"
        )

    import pyforge.steward.deploy as deploy_module

    deploy_module.build_dashboard = _failing_build
    try:
        result = duty.run(ns)
    finally:
        deploy_module.build_dashboard = original_build

    assert result.ok is False
    assert "deploy dashboard" in result.summary
    assert "boom" in result.summary


def test_bare_deploy_degrades_and_names_available_verbs():
    duty = DeployDuty()
    import argparse

    result = duty.run(argparse.Namespace())

    assert result.ok is True
    assert "dashboard" in result.summary
