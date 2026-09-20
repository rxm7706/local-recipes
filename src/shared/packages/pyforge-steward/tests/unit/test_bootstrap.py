"""Story 17.1 — steward init / shell-init bootstrap verbs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.steward.bootstrap import (
    check_prereq,
    format_init_report,
    format_shell_init,
    gather_prereqs,
    pixi_floor_version,
    shell_init_script,
)
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main


def test_pixi_floor_matches_registry_master(repo_root: Path) -> None:
    import sys

    scripts = repo_root / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        from pixi_version_registry import master_version
    finally:
        sys.path.pop(0)

    assert pixi_floor_version(root=repo_root) == master_version()


def test_init_reports_all_prereqs(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._tool_version",
        lambda _name, _path: "99.0.0",
    )
    results = gather_prereqs(root=repo_root)
    assert [r.name for r in results] == ["pixi", "git", "gh", "podman"]
    assert all(r.ok for r in results)


def test_init_failure_names_remedy_not_silent(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.bootstrap.shutil.which", lambda name: None)
    results = gather_prereqs(root=repo_root)
    for row in results:
        assert not row.ok
        assert row.remedy is not None
        assert ":" in row.remedy


def test_pixi_below_floor_names_upgrade_remedy(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    floor = pixi_floor_version(root=repo_root)

    def fake_which(name: str) -> str | None:
        return f"/usr/bin/{name}" if name == "pixi" else f"/usr/bin/{name}"

    monkeypatch.setattr("pyforge.steward.bootstrap.shutil.which", fake_which)
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._tool_version",
        lambda name, _path: "0.0.1" if name == "pixi" else "99.0.0",
    )
    pixi = check_prereq("pixi", pixi_floor=floor)
    assert not pixi.ok
    assert pixi.remedy is not None
    assert pixi.remedy.startswith("upgrade-pixi:")


def test_init_json_shape(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._tool_version",
        lambda _name, _path: "99.0.0",
    )
    payload = json.loads(format_init_report(gather_prereqs(root=repo_root), as_json=True))
    assert payload["ok"] is True
    assert len(payload["prereqs"]) == 4


def test_init_idempotent_text_report(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._tool_version",
        lambda _name, _path: "99.0.0",
    )
    first = format_init_report(gather_prereqs(root=repo_root), as_json=False)
    second = format_init_report(gather_prereqs(root=repo_root), as_json=False)
    assert first == second


def test_shell_init_emits_path_env_and_completion(repo_root: Path) -> None:
    script = shell_init_script(root=repo_root)
    assert "PYFORGE_REPO_ROOT=" in script
    assert ".pixi/bin" in script
    assert "_pyforge_steward_complete" in script


def test_shell_init_idempotent(repo_root: Path) -> None:
    assert shell_init_script(root=repo_root) == shell_init_script(root=repo_root)


def test_shell_init_json_includes_script(repo_root: Path) -> None:
    payload = json.loads(format_shell_init(as_json=True, root=repo_root))
    assert payload["completions"] == "bash"
    assert "PYFORGE_REPO_ROOT" in payload["env"]
    assert payload["script"] == shell_init_script(root=repo_root)


def test_cli_init_and_shell_init_exit_codes(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        "pyforge.steward.bootstrap._tool_version",
        lambda _name, _path: "99.0.0",
    )
    assert main(["init"]) == EXIT_OK
    assert main(["shell-init"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "PYFORGE_REPO_ROOT" in out


def test_cli_init_failure_projects_exit_1(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr("pyforge.steward.bootstrap.shutil.which", lambda _name: None)
    assert main(["init"]) == EXIT_FAILED


@pytest.fixture
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "scripts" / "bmad-loop-worktree").is_file():
            return ancestor
    pytest.fail("could not locate local-recipes repo root from test file location")
