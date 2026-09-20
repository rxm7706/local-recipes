"""Story 17.2 — steward setup / initrepo / validate-fast bootstrap verbs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.steward.bootstrap import (
    SetupStep,
    ValidateFastStep,
    format_initrepo_report,
    format_validate_fast_report,
    initrepo_steps,
    scaffold_pyforge_toml,
    setup_steps,
    validate_fast_steps,
)
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main


@pytest.fixture
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "scripts" / "bmad-loop-worktree").is_file():
            return ancestor
    pytest.fail("could not locate local-recipes repo root from test file location")


def test_setup_idempotent_on_existing_checkout(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> object:  # noqa: ANN401
        calls.append(cmd)

        class _Proc:
            returncode = 0
            stdout = "steward 0.1.0"
            stderr = ""

        return _Proc()

    monkeypatch.setattr("pyforge.steward.bootstrap.subprocess.run", fake_run)
    steps = setup_steps(dest=repo_root, url=None, env="local-recipes")
    assert steps[0].name == "clone"
    assert steps[0].ok is True
    assert "exists" in steps[0].detail
    assert any(step.name == "pixi-install" and step.ok for step in steps)
    assert any(cmd[:3] == ["pixi", "install", "-e"] for cmd in calls)


def test_setup_clone_failure_names_remedy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "fresh-clone"

    def fake_clone(url: str, _dest: Path) -> None:
        raise subprocess.CalledProcessError(1, ["git", "clone"], stderr="network down")

    monkeypatch.setattr("pyforge.steward.bootstrap._run_git_clone", fake_clone)
    steps = setup_steps(dest=dest, url="https://example.invalid/repo.git", env="local-recipes")
    assert steps[0].name == "clone"
    assert not steps[0].ok
    assert steps[0].remedy is not None
    assert steps[0].remedy.startswith("clone-repo:")


def test_setup_missing_dest_without_url_names_remedy(tmp_path: Path) -> None:
    dest = tmp_path / "missing"
    steps = setup_steps(dest=dest, url=None, env="local-recipes")
    assert len(steps) == 1
    assert steps[0].name == "clone"
    assert not steps[0].ok
    assert steps[0].remedy is not None


def test_scaffold_pyforge_toml_writes_once(tmp_path: Path) -> None:
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    assert scaffold_pyforge_toml(root=tmp_path) is True
    assert (tmp_path / "pyforge.toml").is_file()
    assert scaffold_pyforge_toml(root=tmp_path) is False


def test_validate_fast_json_shape(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._tool_version",
        lambda _name, _path: "99.0.0",
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.check_environment_sync",
        lambda **_: (True, ""),
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._run_steward_version",
        lambda **_: "steward 0.1.0",
    )
    payload = json.loads(
        format_validate_fast_report(
            validate_fast_steps(root=repo_root, env="local-recipes"),
            as_json=True,
        )
    )
    assert payload["ok"] is True
    assert {step["name"] for step in payload["steps"]} >= {"prereqs", "env-sync", "steward-cli"}


def test_initrepo_requires_pixi_project(tmp_path: Path) -> None:
    steps = initrepo_steps(root=tmp_path, env="local-recipes")
    assert len(steps) == 1
    assert steps[0].name == "pixi-project"
    assert not steps[0].ok


def test_initrepo_happy_path_mocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.materialize_environment",
        lambda _name, **_: None,
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.validate_fast_steps",
        lambda **_: (
            ValidateFastStep(name="prereqs", ok=True, detail="ok"),
            ValidateFastStep(name="steward-cli", ok=True, detail="steward 0.1.0"),
        ),
    )
    steps = initrepo_steps(root=tmp_path, env="local-recipes")
    names = [step.name for step in steps]
    assert names[:3] == ["pixi-project", "scaffold", "pixi-install"]
    assert "prereqs" in names
    report = format_initrepo_report(steps, as_json=False)
    assert "steward initrepo: PASS" in report


def test_cli_setup_initrepo_validate_fast_exit_codes(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.setup_steps",
        lambda **_: (SetupStep(name="clone", ok=True, detail="skipped"),),
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.initrepo_steps",
        lambda **_: (SetupStep(name="pixi-project", ok=True, detail="ok"),),
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.validate_fast_steps",
        lambda **_: (ValidateFastStep(name="prereqs", ok=True, detail="ok"),),
    )
    assert main(["setup"]) == EXIT_OK
    assert main(["initrepo"]) == EXIT_OK
    assert main(["validate-fast"]) == EXIT_OK


def test_cli_setup_failure_projects_exit_1(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.setup_steps",
        lambda **_: (
            SetupStep(
                name="pixi-install",
                ok=False,
                detail="boom",
                remedy="pixi-install: fix it",
            ),
        ),
    )
    assert main(["setup"]) == EXIT_FAILED
