"""Story 17.1 — steward init / shell-init bootstrap verbs.

Story 135.1 (spec-pyforge-steward CAP-183): ``init`` reads its checks from ``docs/governance/machine-readiness.yaml``
and ``gather_prereqs`` is that file's default-profile software rows, so no container engine is a prerequisite of
``validate-fast`` or ``initrepo``. The probes themselves are held by ``test_machine.py``; this module runs the verb
over the tracked data file.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.steward import machine
from pyforge.steward.bootstrap import (
    check_prereq,
    format_shell_init,
    gather_prereqs,
    pixi_floor_version,
    shell_init_script,
    validate_fast_steps,
)
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


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
    assert [r.name for r in results] == ["pixi", "git", "gh"]
    assert all(r.ok for r in results)


def test_gather_prereqs_returns_no_container_engine(repo_root: Path) -> None:
    """Story 135.1 AC3: an engine is the container profile's, never a prerequisite of desktop work."""
    assert not {"docker", "podman"} & {r.name for r in gather_prereqs(root=repo_root)}


def test_validate_fast_passes_its_prereqs_with_no_container_engine_on_path(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 135.1 AC3: ``validate-fast`` (and ``initrepo``, which runs it) no longer fails on podman alone."""
    monkeypatch.setattr(
        "pyforge.steward.bootstrap.shutil.which",
        lambda name: None if name in ("docker", "podman") else f"/usr/bin/{name}",
    )
    monkeypatch.setattr("pyforge.steward.bootstrap._tool_version", lambda _name, _path: "99.0.0")
    monkeypatch.setattr("pyforge.steward.bootstrap.check_environment_sync", lambda **_k: (True, ""))
    monkeypatch.setattr("pyforge.steward.bootstrap._run_steward_version", lambda **_k: "steward 0.1.0")
    steps = validate_fast_steps(root=repo_root, env="pyforge-guild")
    assert [(step.name, step.ok) for step in steps] == [("prereqs", True), ("env-sync", True), ("steward-cli", True)]


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


def _tools(present: bool):
    """Production seams over the tracked data file, with every tool on PATH (or none) and no real subprocess."""

    def deps(root: Path) -> machine.MachineDeps:
        return machine.MachineDeps(
            root=root,
            runner=lambda argv, _cwd, _timeout: subprocess.CompletedProcess(
                list(argv), 0, stdout="tool 99.0.0", stderr=""
            ),
            which=lambda name: f"/usr/bin/{name}" if present else None,
        )

    return deps


def test_init_json_shape(repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(machine, "production_deps", _tools(present=True))
    assert main(["init", "--repo", str(repo_root), "--class", "software", "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert [row["name"] for row in payload["prereqs"]] == ["pixi", "git", "gh"]
    assert set(payload["prereqs"][0]) == {"name", "ok", "found", "required", "remedy"}
    assert [(p["id"], p["ready"], p["supported"]) for p in payload["profiles"]] == [("desktop", True, True)]
    assert [check["id"] for check in payload["checks"]] == ["pixi", "git", "gh"]


def test_init_idempotent_text_report(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(machine, "production_deps", _tools(present=True))
    assert main(["init", "--repo", str(repo_root), "--class", "software"]) == EXIT_OK
    first = capsys.readouterr().out
    assert main(["init", "--repo", str(repo_root), "--class", "software"]) == EXIT_OK
    assert capsys.readouterr().out == first
    assert first.rstrip().endswith("steward init: desktop READY (software checks only)")


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
    monkeypatch.setattr(machine, "production_deps", _tools(present=True))
    assert main(["init", "--class", "software"]) == EXIT_OK
    assert main(["shell-init"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "PYFORGE_REPO_ROOT" in out


def test_cli_init_failure_projects_exit_1(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(machine, "production_deps", _tools(present=False))
    assert main(["init", "--class", "software"]) == EXIT_FAILED
    out = capsys.readouterr().out
    assert "  FAIL    pixi: pixi is not on PATH" in out
    assert "          remedy (operator): curl -fsSL https://pixi.sh/install.sh | sh" in out
    assert out.rstrip().endswith("steward init: desktop NOT READY (software checks only; not ok: pixi, git, gh)")


def test_cli_init_list_probes_nothing_and_an_unknown_profile_is_usage(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Story 135.1 AC4 and AC5, over the tracked data file."""
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(machine, "production_deps", _tools(present=False))
    assert main(["init", "--list"]) == EXIT_OK
    assert "(nothing is probed)" in capsys.readouterr().out
    assert main(["init", "--profile", "no-such-profile"]) == EXIT_USAGE
    assert "unknown profile no-such-profile" in capsys.readouterr().err


@pytest.fixture
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "scripts" / "bmad-loop-worktree").is_file():
            return ancestor
    pytest.fail("could not locate local-recipes repo root from test file location")
