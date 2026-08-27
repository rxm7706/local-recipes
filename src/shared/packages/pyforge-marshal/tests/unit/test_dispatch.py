"""Unit tests for ``marshal factory dispatch`` (Story 22.1)."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli.dispatch import run_dispatch
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.status import FleetHomeFacts, build_fleet_row
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.build_harness import (
    DispatchLaunchResult,
    HarnessCandidateSkip,
    HarnessResolution,
)


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "dispatch@test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "dispatch"],
        cwd=path,
        check=True,
        capture_output=True,
    )


class FakeFs:
    def __init__(self) -> None:
        self.dirs: set[Path] = set()
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []

    def is_dir(self, path: Path) -> bool:
        return path in self.dirs

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def create_dir_exclusive(self, path: Path) -> None:
        self.dirs.add(path)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        return self.files.get(path)


class FakeVcs:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.added: list[tuple[Path, Path, str, str]] = []

    def repo_common_root(self, _cwd: Path) -> Path:
        return self.repo_root

    def worktree_path_for_branch(self, _repo_root: Path, _branch: str) -> Path | None:
        return None

    def add_worktree(
        self, repo_root: Path, home: Path, branch: str, *, base: str
    ) -> None:
        self.added.append((repo_root, home, branch, base))
        home.mkdir(parents=True, exist_ok=True)

    def worktree_head_sha(self, _worktree: Path) -> str:
        return "baseline0001"


class FakeBuildHarness:
    def __init__(self, *, present: bool = True, pid: int = 4242) -> None:
        self.present = present
        self.pid = pid
        self.calls: list[dict[str, object]] = []
        self.preference_seen: tuple[str, ...] | None = None

    def binary_present(self, preference=(), repo_root=None) -> HarnessResolution:
        self.preference_seen = tuple(preference)
        if not self.present:
            return HarnessResolution(
                profile=None,
                skipped=tuple(
                    HarnessCandidateSkip(
                        profile=name, reason=f"binary {name!r} not found on PATH"
                    )
                    for name in preference
                ),
            )
        chosen = next(iter(preference), "claude")
        return HarnessResolution(profile=chosen, binary_path=f"/usr/bin/{chosen}")

    def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
        self.calls.append({"worktree": worktree, **kwargs})
        resolution = kwargs.get("resolution")
        return DispatchLaunchResult(
            pid=self.pid,
            command=("fake-harness",),
            model=kwargs.get("model"),
            budget_env=dict(kwargs.get("budget_env") or {}),
            profile=resolution.profile if resolution is not None else None,
        )


class FakeProcess:
    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive

    def is_alive(self, _pid: int) -> bool:
        return self.alive

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        return 4243


def test_resolve_story_spec_path_finds_tracked_spec(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n", encoding="utf-8")
    resolved = dispatch_core.resolve_story_spec_path(tmp_path, slug, story)
    assert resolved == spec


def test_build_fleet_row_surfaces_live_dispatch(tmp_path: Path) -> None:
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="22-1-example",
        dispatch_engine_alive=True,
        dispatch_elapsed_seconds=12.5,
        dispatch_run_id="pyforge-marshal-20260823T000000000Z-deadbeef",
    )
    row, finding = build_fleet_row(facts)
    assert finding is None
    assert row["state"] == "running"
    assert row["current_story"] == "22-1-example"
    assert row["elapsed_seconds"] == 12.5


def test_run_dispatch_journals_and_returns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n# spec\n", encoding="utf-8")

    fs = FakeFs()
    vcs = FakeVcs(tmp_path)
    harness = FakeBuildHarness()
    process = FakeProcess()

    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=vcs,
        build_harness=harness,
        process=process,
    )
    assert code == EXIT_OK
    assert harness.calls
    assert harness.calls[0]["project_slug"] == slug
    assert fs.appended
    assert any("dispatch-launch" in line for _, line, _ in fs.appended)


def test_run_dispatch_refuses_missing_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    args = argparse.Namespace(slug=slug, story=story, format="text")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(present=False),
        process=FakeProcess(),
    )
    assert code != EXIT_OK


def test_run_dispatch_carries_profile_and_reports_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Story 22.8: the envelope names the resolved profile; every skipped
    preference candidate surfaces as a structured MRS-DISP-027 WARN."""
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-8-the-session-harness-is-profile-driven-across-agent-clis"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    import json

    from pyforge.marshal.ports.build_harness import (
        HarnessCandidateSkip as Skip,
    )
    from pyforge.marshal.ports.build_harness import (
        HarnessResolution as Resolution,
    )

    class SkippingHarness(FakeBuildHarness):
        def binary_present(self, preference=(), repo_root=None):
            self.preference_seen = tuple(preference)
            return Resolution(
                profile="claude",
                binary_path="/usr/bin/claude",
                skipped=(
                    Skip(profile="cursor", reason="authcheck exited 1 (auth required)"),
                ),
            )

    harness = SkippingHarness()
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert code == EXIT_OK
    # the policy default preference reached the resolution profile-first
    assert harness.preference_seen == ("claude", "cursor", "copilot", "gemini", "devin")
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["harness_profile"] == "claude"
    skips = [f for f in payload["findings"] if f["code"] == "MRS-DISP-027"]
    assert len(skips) == 1 and "cursor" in skips[0]["message"]
    assert harness.calls and harness.calls[0]["resolution"].profile == "claude"


def test_run_dispatch_refusal_names_every_candidate_tried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """MRS-DISP-003 must say what was tried and why each candidate was
    skipped -- the 2026-08-27 silent cursor-auth death, made loud."""
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-8-the-session-harness-is-profile-driven-across-agent-clis"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    import json

    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(present=False),
        process=FakeProcess(),
    )
    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    refusals = [f for f in payload["findings"] if f["code"] == "MRS-DISP-003"]
    assert len(refusals) == 1
    message = refusals[0]["message"]
    assert "no dispatchable session-harness profile" in message
    for name in ("claude", "cursor", "copilot", "gemini", "devin"):
        assert name in message
