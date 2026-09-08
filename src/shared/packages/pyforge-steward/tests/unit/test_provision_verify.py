"""`check_environment_sync` + `provision --verify` CLI dispatch — Story 3.4.

The real `pixi project export conda-environment -e build` invocation is
never exercised here — `subprocess.run` is monkeypatched to return a fixed
export string, mirroring `test_deploy_build.py`'s own rationale, so both
matrix rows (clean/drift) are driven deterministically.
"""

from __future__ import annotations

import subprocess

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.provision import check_environment_sync


def _fake_export(text):
    def _run(cmd, **kwargs):  # noqa: ARG001
        return subprocess.CompletedProcess(cmd, 0, stdout=text, stderr="")

    return _run


def test_check_environment_sync_reports_in_sync_when_identical(tmp_path, monkeypatch):
    (tmp_path / "environment.yaml").write_text("name: build\ndependencies:\n  - python\n")
    monkeypatch.setattr(subprocess, "run", _fake_export("name: build\ndependencies:\n  - python\n"))

    in_sync, diff = check_environment_sync(cwd=tmp_path)

    assert in_sync is True
    assert diff == ""


def test_check_environment_sync_ignores_trailing_whitespace_like_the_linter_does(tmp_path, monkeypatch):
    (tmp_path / "environment.yaml").write_text("name: build\ndependencies:\n  - python\n\n\n")
    monkeypatch.setattr(subprocess, "run", _fake_export("name: build\ndependencies:\n  - python\n"))

    in_sync, _ = check_environment_sync(cwd=tmp_path)

    assert in_sync is True


def test_check_environment_sync_reports_drift_with_a_unified_diff(tmp_path, monkeypatch):
    (tmp_path / "environment.yaml").write_text("name: build\ndependencies:\n  - python\n")
    monkeypatch.setattr(
        subprocess, "run", _fake_export("name: build\ndependencies:\n  - python\n  - pip\n")
    )

    in_sync, diff = check_environment_sync(cwd=tmp_path)

    assert in_sync is False
    assert "pip" in diff


def test_check_environment_sync_raises_file_not_found_for_a_missing_environment_yaml(tmp_path):
    with pytest.raises(FileNotFoundError):
        check_environment_sync(cwd=tmp_path)


def test_check_environment_sync_propagates_an_export_failure(tmp_path, monkeypatch):
    (tmp_path / "environment.yaml").write_text("name: build\n")

    def _fake_run(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="unknown environment 'build'")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        check_environment_sync(cwd=tmp_path)


def test_provision_verify_via_cli_reports_clean_and_exits_ok(tmp_path, monkeypatch):
    (tmp_path / "environment.yaml").write_text("name: build\ndependencies:\n  - python\n")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(subprocess, "run", _fake_export("name: build\ndependencies:\n  - python\n"))

    rc = main(["provision", "--verify"])

    assert rc == EXIT_OK


def test_provision_verify_via_cli_reports_drift_and_exits_failed(tmp_path, monkeypatch):
    (tmp_path / "environment.yaml").write_text("name: build\ndependencies:\n  - python\n")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        subprocess, "run", _fake_export("name: build\ndependencies:\n  - python\n  - pip\n")
    )

    rc = main(["provision", "--verify"])

    assert rc == EXIT_FAILED


def test_provision_verify_never_writes_environment_yaml(tmp_path, monkeypatch):
    (tmp_path / "environment.yaml").write_text("name: build\ndependencies:\n  - python\n")
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        subprocess, "run", _fake_export("name: build\ndependencies:\n  - python\n  - pip\n")
    )
    before = (tmp_path / "environment.yaml").read_text()

    main(["provision", "--verify"])

    assert (tmp_path / "environment.yaml").read_text() == before
