"""Story 83.25: run-scoped Cursor config with attribution off."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pyforge.marshal.adapters.cursor_launch_config import (
    CursorLaunchConfigError,
    cursor_launch_env_overlay,
)
from pyforge.marshal.adapters.harness_bmadbuild import BmadBuildHarness, BuildHarnessError
from pyforge.marshal.adapters.skill_invoke_harness import HarnessSkillInvoker
from pyforge.marshal.core.cursor_launch_config import (
    CURSOR_ATTRIBUTION_OFF_FINDING,
    effective_cursor_config_dir,
    run_scoped_cursor_config_dir,
)
from pyforge.marshal.core.harness_profile import WireWrap, parse_profile
from pyforge.marshal.ports.build_harness import HarnessResolution


def test_effective_cursor_config_dir_honors_cursor_config_dir(tmp_path: Path) -> None:
    custom = tmp_path / "cfg"
    env = {"CURSOR_CONFIG_DIR": str(custom), "XDG_CONFIG_HOME": "/ignored"}
    assert effective_cursor_config_dir(env) == custom


def test_effective_cursor_config_dir_honors_xdg_config_home(tmp_path: Path) -> None:
    xdg = tmp_path / "xdg"
    assert effective_cursor_config_dir({"XDG_CONFIG_HOME": str(xdg)}) == xdg / "cursor"


def test_cursor_launch_env_overlay_forces_attribution_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    operator_dir = tmp_path / "operator-cursor"
    operator_dir.mkdir()
    operator_config = {
        "permissions": {"allow": ["Shell"]},
        "attribution": {"attributeCommitsToAgent": True, "attributePRsToAgent": True},
    }
    config_path = operator_dir / "cli-config.json"
    config_path.write_text(json.dumps(operator_config), encoding="utf-8")
    before = config_path.read_bytes()

    worktree = tmp_path / "wt"
    worktree.mkdir()
    monkeypatch.setenv("CURSOR_CONFIG_DIR", str(operator_dir))

    overlay = cursor_launch_env_overlay(worktree, os.environ)
    assert overlay["CURSOR_CONFIG_DIR"] == str(run_scoped_cursor_config_dir(worktree))

    run_config = json.loads((run_scoped_cursor_config_dir(worktree) / "cli-config.json").read_text(encoding="utf-8"))
    assert run_config["permissions"] == operator_config["permissions"]
    assert run_config["attribution"]["attributeCommitsToAgent"] is False
    assert run_config["attribution"]["attributePRsToAgent"] is False
    assert config_path.read_bytes() == before


def test_cursor_launch_env_overlay_refuses_unreadable_operator_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    operator_dir = tmp_path / "missing"
    monkeypatch.setenv("CURSOR_CONFIG_DIR", str(operator_dir))
    worktree = tmp_path / "wt"
    worktree.mkdir()
    with pytest.raises(CursorLaunchConfigError, match=CURSOR_ATTRIBUTION_OFF_FINDING):
        cursor_launch_env_overlay(worktree, os.environ)


def test_launch_argv_sets_cursor_config_dir_for_cursor_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    operator_dir = tmp_path / "operator-cursor"
    operator_dir.mkdir()
    (operator_dir / "cli-config.json").write_text(
        json.dumps({"attribution": {"attributeCommitsToAgent": True}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("CURSOR_CONFIG_DIR", str(operator_dir))

    seen: dict[str, str] = {}

    def _popen(argv: list[str], **kwargs: object) -> object:
        env = kwargs["env"]
        assert isinstance(env, dict)
        seen.update(env)

        class _Proc:
            pid = 99

        return _Proc()

    from pyforge.marshal.adapters import harness_bmadbuild

    monkeypatch.setattr(harness_bmadbuild.subprocess, "Popen", _popen)
    profile = parse_profile({"name": "cursor", "binary": "cursor-agent", "argv": ["{prompt}"]}, source="test")
    resolution = HarnessResolution(profile="cursor", spec=profile, binary_path="/bin/cursor-agent")

    BmadBuildHarness().launch_argv(
        ["/bin/cursor-agent"],
        worktree=tmp_path / "wt",
        profile=profile,
        resolution=resolution,
        log_path=tmp_path / "log",
        wire=WireWrap(applied=False, reason=None),
        budget_env={},
        project_slug="pyforge-marshal",
    )

    run_dir = run_scoped_cursor_config_dir(tmp_path / "wt")
    assert seen["CURSOR_CONFIG_DIR"] == str(run_dir)
    run_cfg = json.loads((run_dir / "cli-config.json").read_text(encoding="utf-8"))
    assert run_cfg["attribution"]["attributeCommitsToAgent"] is False


def test_launch_argv_cursor_attribution_overlay_mutation_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Removing the overlay leaves CURSOR_CONFIG_DIR unset on the child env."""
    operator_dir = tmp_path / "operator-cursor"
    operator_dir.mkdir()
    (operator_dir / "cli-config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("CURSOR_CONFIG_DIR", str(operator_dir))

    seen: dict[str, str] = {}

    def _popen(argv: list[str], **kwargs: object) -> object:
        env = kwargs["env"]
        assert isinstance(env, dict)
        seen.update(env)

        class _Proc:
            pid = 99

        return _Proc()

    from pyforge.marshal.adapters import cursor_launch_config, harness_bmadbuild

    monkeypatch.setattr(harness_bmadbuild.subprocess, "Popen", _popen)
    monkeypatch.setattr(cursor_launch_config, "cursor_launch_env_overlay", lambda _wt, _env: {})

    profile = parse_profile({"name": "cursor", "binary": "cursor-agent", "argv": ["{prompt}"]}, source="test")
    resolution = HarnessResolution(profile="cursor", spec=profile, binary_path="/bin/cursor-agent")
    worktree = tmp_path / "wt"
    worktree.mkdir()

    BmadBuildHarness().launch_argv(
        ["/bin/cursor-agent"],
        worktree=worktree,
        profile=profile,
        resolution=resolution,
        log_path=tmp_path / "log",
        wire=WireWrap(applied=False, reason=None),
        budget_env={},
        project_slug="pyforge-marshal",
    )

    assert seen.get("CURSOR_CONFIG_DIR") == str(run_scoped_cursor_config_dir(worktree))


def test_harness_skill_invoker_applies_cursor_config_overlay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    operator_dir = tmp_path / "operator-cursor"
    operator_dir.mkdir()
    (operator_dir / "cli-config.json").write_text(
        json.dumps({"attribution": {"attributeCommitsToAgent": True}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("CURSOR_CONFIG_DIR", str(operator_dir))

    seen: dict[str, str] = {}

    def _run(argv: list[str], **kwargs: object) -> object:
        env = kwargs["env"]
        assert isinstance(env, dict)
        seen.update(env)
        log_path = kwargs.get("stdout")
        if hasattr(log_path, "write"):
            log_path.write(b"STATUS:complete\n")

        class _Completed:
            returncode = 0

        return _Completed()

    monkeypatch.setattr("pyforge.marshal.adapters.skill_invoke_harness.shutil.which", lambda _name: "/bin/cursor")
    monkeypatch.setattr("pyforge.marshal.adapters.skill_invoke_harness.subprocess.run", _run)

    root = tmp_path / "repo"
    root.mkdir()
    run_dir = tmp_path / "run"
    dream = root / "docs" / "dreams" / "x.md"
    dream.parent.mkdir(parents=True)
    dream.write_text("dream", encoding="utf-8")
    (root / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts").mkdir(parents=True)

    result = HarnessSkillInvoker(live=True).invoke_planning_skill(
        "bmad-spec",
        root=root,
        project="pyforge-marshal",
        dream=dream,
        phase="spec",
        run_dir=run_dir,
    )
    assert result.status == "complete"
    run_dir_cfg = run_scoped_cursor_config_dir(root)
    assert seen["CURSOR_CONFIG_DIR"] == str(run_dir_cfg)


def test_harness_skill_invoker_refuses_when_operator_config_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CURSOR_CONFIG_DIR", str(tmp_path / "nope"))
    monkeypatch.setattr("pyforge.marshal.adapters.skill_invoke_harness.shutil.which", lambda _name: "/bin/cursor")

    root = tmp_path / "repo"
    root.mkdir()
    dream = root / "docs" / "dreams" / "x.md"
    dream.parent.mkdir(parents=True)
    dream.write_text("dream", encoding="utf-8")

    result = HarnessSkillInvoker(live=True).invoke_planning_skill(
        "bmad-spec",
        root=root,
        project="pyforge-marshal",
        dream=dream,
        phase="spec",
        run_dir=tmp_path / "run",
    )
    assert result.status == "failed"
    assert CURSOR_ATTRIBUTION_OFF_FINDING in result.detail


def test_dispatch_raises_build_harness_error_when_cursor_config_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CURSOR_CONFIG_DIR", str(tmp_path / "missing"))
    profile = parse_profile({"name": "cursor", "binary": "cursor-agent", "argv": ["{prompt}"]}, source="test")
    resolution = HarnessResolution(profile="cursor", spec=profile, binary_path="/bin/cursor-agent")
    worktree = tmp_path / "wt"
    worktree.mkdir()
    spec = worktree / "spec.md"
    spec.write_text("---\nstatus: ready\n---\n", encoding="utf-8")

    with pytest.raises(BuildHarnessError, match=CURSOR_ATTRIBUTION_OFF_FINDING):
        BmadBuildHarness().dispatch(
            worktree,
            resolution=resolution,
            project_slug="pyforge-marshal",
            story_key="83.25",
            spec_path=spec,
            model=None,
            budget_env={},
            log_path=worktree / "log",
        )
