"""Unit tests for ``pyforge.marshal.adapters.harness_bmadbuild`` (Story
22.8, FR-193 CAP-8) -- the impure half of the profile-driven session
harness: binary/fallback probing, the authcheck subprocess, resolution
order + structured skips, and the detached profile-rendered launch. FAKE
BINARIES ONLY (tmp shell scripts on a controlled PATH) -- no test here ever
invokes a real coding-agent CLI."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from pyforge.marshal.adapters.harness_bmadbuild import (
    BmadBuildHarness,
    BuildHarnessError,
)
from pyforge.marshal.ports.build_harness import HarnessResolution


def _write_script(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _write_overlay(repo_root: Path, name: str, text: str) -> Path:
    overlay = repo_root / "_bmad-output" / "harness-profiles"
    overlay.mkdir(parents=True, exist_ok=True)
    path = overlay / f"{name}.toml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture()
def bare_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A controlled PATH containing only ``bin/`` under tmp -- no real CLI
    can leak into resolution."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir))
    return bin_dir


# --- resolution --------------------------------------------------------------


def test_resolution_skips_missing_binary_then_resolves(
    tmp_path: Path, bare_path: Path
) -> None:
    _write_overlay(
        tmp_path, "one", 'name = "one"\nbinary = "one-cli"\nargv = ["{prompt}"]\n'
    )
    _write_overlay(
        tmp_path, "two", 'name = "two"\nbinary = "two-cli"\nargv = ["{prompt}"]\n'
    )
    _write_script(bare_path, "two-cli", "exit 0")
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("one", "two"), repo_root=tmp_path)
    assert bool(resolution) is True
    assert resolution.profile == "two"
    assert resolution.binary_path == str(bare_path / "two-cli")
    assert [s.profile for s in resolution.skipped] == ["one"]
    assert "not found on PATH" in resolution.skipped[0].reason


def test_resolution_skips_unknown_profile_name(tmp_path: Path, bare_path: Path) -> None:
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("no-such-profile",), repo_root=tmp_path)
    assert not resolution
    assert resolution.skipped[0].profile == "no-such-profile"
    assert "unknown harness profile" in resolution.skipped[0].reason


def test_resolution_authcheck_nonzero_exit_skips(
    tmp_path: Path, bare_path: Path
) -> None:
    _write_overlay(
        tmp_path,
        "authy",
        'name = "authy"\nbinary = "authy-cli"\nargv = ["{prompt}"]\n'
        'authcheck_args = ["status"]\n',
    )
    _write_script(bare_path, "authy-cli", 'echo "Authentication required" >&2\nexit 1')
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("authy",), repo_root=tmp_path)
    assert not resolution
    assert "exited 1" in resolution.skipped[0].reason
    assert "Authentication required" in resolution.skipped[0].reason


def test_resolution_authcheck_pattern_miss_skips_despite_exit_zero(
    tmp_path: Path, bare_path: Path
) -> None:
    """The 2026-08-27 lesson, regression-pinned: cursor's trust prompt and
    gemini's trust refusal both EXIT 0 -- output must confirm, exit code
    alone never suffices."""
    _write_overlay(
        tmp_path,
        "authy",
        'name = "authy"\nbinary = "authy-cli"\nargv = ["{prompt}"]\n'
        'authcheck_args = ["status"]\nauthcheck_ok_pattern = "Logged in as"\n',
    )
    _write_script(bare_path, "authy-cli", 'echo "Not logged in"\nexit 0')
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("authy",), repo_root=tmp_path)
    assert not resolution
    assert "did not confirm login" in resolution.skipped[0].reason


def test_resolution_authcheck_pass_with_pattern(tmp_path: Path, bare_path: Path) -> None:
    _write_overlay(
        tmp_path,
        "authy",
        'name = "authy"\nbinary = "authy-cli"\nargv = ["{prompt}"]\n'
        'authcheck_args = ["status"]\nauthcheck_ok_pattern = "Logged in as"\n',
    )
    _write_script(bare_path, "authy-cli", 'echo "Logged in as someone"\nexit 0')
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("authy",), repo_root=tmp_path)
    assert resolution.profile == "authy"
    assert resolution.skipped == ()


def test_resolution_uses_fallback_bin_dirs(tmp_path: Path, bare_path: Path) -> None:
    """A binary invisible to PATH resolves through the profile's
    repo-root-relative fallback dirs (the pixi-env CLI case)."""
    pixi_bin = tmp_path / "envbin"
    pixi_bin.mkdir()
    _write_script(pixi_bin, "pixi-cli", "exit 0")
    _write_overlay(
        tmp_path,
        "pixied",
        'name = "pixied"\nbinary = "pixi-cli"\nargv = ["{prompt}"]\n'
        'fallback_bin_dirs = ["envbin"]\n',
    )
    harness = BmadBuildHarness()
    resolution = harness.binary_present(("pixied",), repo_root=tmp_path)
    assert resolution.profile == "pixied"
    assert resolution.binary_path == str(pixi_bin / "pixi-cli")


def test_resolution_reports_overlay_load_errors(tmp_path: Path, bare_path: Path) -> None:
    _write_overlay(tmp_path, "broken", "not [ toml")
    harness = BmadBuildHarness()
    resolution = harness.binary_present((), repo_root=tmp_path)
    assert not resolution
    assert len(resolution.profile_errors) == 1
    assert "broken" in resolution.profile_errors[0]


def test_empty_preference_resolves_nothing(tmp_path: Path, bare_path: Path) -> None:
    resolution = BmadBuildHarness().binary_present((), repo_root=tmp_path)
    assert not resolution
    assert resolution.skipped == ()


# --- dispatch launch ---------------------------------------------------------


def _launch_ready_resolution(tmp_path: Path, bare_path: Path) -> HarnessResolution:
    args_file = tmp_path / "seen-args.txt"
    _write_script(
        bare_path,
        "fakecli",
        f'printf \'%s\\n\' "$@" > "{args_file}"\n'
        'echo "session output"\n'
        'echo "PROJ=$BMAD_ACTIVE_PROJECT" ; echo "EXTRA=$FAKE_EXTRA"',
    )
    _write_overlay(
        tmp_path,
        "fakecli",
        'name = "fakecli"\nbinary = "fakecli"\n'
        'argv = ["--flag", "{worktree}", "{model_args}", "{prompt}"]\n'
        'model_args = ["--model", "{model}"]\n'
        'model_map = { opus = "mapped-big" }\n'
        '[env]\nFAKE_EXTRA = "yes"\n',
    )
    return BmadBuildHarness().binary_present(("fakecli",), repo_root=tmp_path)


def test_dispatch_renders_profile_argv_env_and_detaches(
    tmp_path: Path, bare_path: Path
) -> None:
    resolution = _launch_ready_resolution(tmp_path, bare_path)
    assert resolution.profile == "fakecli"
    worktree = tmp_path / "wt"
    worktree.mkdir()
    log_path = tmp_path / "session.log"
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="22-8-example",
        spec_path=tmp_path / "spec.md",
        model="opus",
        budget_env={"MARSHAL_MAX_TOKENS_PER_STORY": "5"},
        log_path=log_path,
    )
    assert result.profile == "fakecli"
    assert result.model == "mapped-big"
    assert result.model_omitted_reason is None
    assert result.command[0] == str(bare_path / "fakecli")
    assert result.command[1:3] == ("--flag", str(worktree))
    assert result.command[3:5] == ("--model", "mapped-big")
    assert "bmad-build-auto" in result.command[5]
    for _ in range(100):
        if (tmp_path / "seen-args.txt").is_file() and log_path.is_file():
            time.sleep(0.05)
            break
        time.sleep(0.05)
    seen = (tmp_path / "seen-args.txt").read_text(encoding="utf-8")
    assert seen.splitlines()[0] == "--flag"
    log_text = log_path.read_text(encoding="utf-8")
    assert "PROJ=pyforge-marshal" in log_text
    assert "EXTRA=yes" in log_text


def test_dispatch_omitted_model_tier_reports_reason(
    tmp_path: Path, bare_path: Path
) -> None:
    resolution = _launch_ready_resolution(tmp_path, bare_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="pyforge-marshal",
        story_key="22-8-example",
        spec_path=tmp_path / "spec.md",
        model="haiku",  # not in fakecli's model_map, no passthrough
        budget_env={},
        log_path=tmp_path / "session.log",
    )
    assert result.model is None
    assert "haiku" in result.model_omitted_reason
    assert "--model" not in result.command


def test_dispatch_refuses_a_falsy_resolution(tmp_path: Path) -> None:
    with pytest.raises(BuildHarnessError, match="no resolved profile"):
        BmadBuildHarness().dispatch(
            tmp_path,
            resolution=HarnessResolution(profile=None),
            project_slug="s",
            story_key="1-1-x",
            spec_path=tmp_path / "spec.md",
            model=None,
            budget_env={},
            log_path=tmp_path / "log",
        )


def test_dispatch_child_survives_via_new_session(
    tmp_path: Path, bare_path: Path
) -> None:
    """The detach decision, pinned: Popen with start_new_session -- the
    returned pid IS the session process (no CLI self-backgrounding
    double-detach), so the dispatch supervisor's liveness probe is
    meaningful."""
    _write_script(bare_path, "sleeper", "sleep 5")
    _write_overlay(
        tmp_path,
        "sleeper",
        'name = "sleeper"\nbinary = "sleeper"\nargv = ["{prompt}"]\n',
    )
    resolution = BmadBuildHarness().binary_present(("sleeper",), repo_root=tmp_path)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result = BmadBuildHarness().dispatch(
        worktree,
        resolution=resolution,
        project_slug="s",
        story_key="1-1-x",
        spec_path=tmp_path / "spec.md",
        model=None,
        budget_env={},
        log_path=tmp_path / "log",
    )
    # pid alive and in its own session (detached from this test process)
    os.kill(result.pid, 0)
    assert os.getsid(result.pid) != os.getsid(0)
    os.kill(result.pid, 15)
