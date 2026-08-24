"""Unit tests for Story 22.5 station in-flight guard and overlap advisory."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli.dispatch import (
    cross_station_surface_overlap_advisories,
    run_dispatch,
    station_in_flight_conflict,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.build_harness import DispatchLaunchResult


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
        return path in self.dirs or path.is_dir()

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def create_dir_exclusive(self, path: Path) -> None:
        self.dirs.add(path)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))
        self.files[path] = self.files.get(path, "") + line

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        if path in self.files:
            return self.files[path]
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None


class FakeVcs:
    def __init__(self, repo_root: Path, *, head_sha: str = "baseline1234") -> None:
        self.repo_root = repo_root
        self.head_sha = head_sha
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
        return self.head_sha


class FakeBuildHarness:
    def binary_present(self) -> bool:
        return True

    def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
        return DispatchLaunchResult(
            pid=6060,
            command=("cursor", "agent"),
            model=kwargs.get("model"),
            budget_env=dict(kwargs.get("budget_env") or {}),
        )


class FakeProcess:
    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive

    def is_alive(self, _pid: int) -> bool:
        return self.alive

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        return 6061


def _seed_live_dispatch_journal(
    tmp_path: Path,
    fs: FakeFs,
    *,
    slug: str,
    run_id: str,
    story_key: str,
    session_pid: int = 42,
) -> Path:
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_path = run_dir / "journal.jsonl"
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-08-23T00:00:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": story_key,
                "worktree_path": str(tmp_path / "wt"),
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-08-23T00:00:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": session_pid},
        )
    ).line
    journal_text = intent + "\n" + outcome + "\n"
    journal_path.write_text(journal_text, encoding="utf-8")
    fs.files[journal_path] = journal_text
    return run_dir


def test_declared_globs_overlap_detects_shared_prefix() -> None:
    assert dispatch_core.declared_globs_overlap("src/pkg/**", "src/pkg/foo.py")
    assert not dispatch_core.declared_globs_overlap("src/a/**", "src/b/**")


def test_station_refuses_different_story_while_another_in_flight(tmp_path: Path) -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy

    slug = "pyforge-marshal"
    fs = FakeFs()
    _seed_live_dispatch_journal(
        tmp_path, fs, slug=slug, run_id="run-live", story_key="22.1"
    )

    class LiveVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            return ("src/changed.py",)

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

        def worktree_head_sha(self, worktree_path: Path) -> str:
            return "bbb222"

    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=LiveVcs(tmp_path),
        process=FakeProcess(alive=False),
        repo_root=tmp_path,
        slug=slug,
        story_key="22-5-one-story-in-flight",
        effective_policy=_compose_policy(slug),
    )
    assert conflict is not None
    assert conflict.code == "MRS-DISP-021"
    assert conflict.in_flight_story_key == "22.1"
    assert "22.1" in conflict.message


def test_cross_station_dispatch_allowed_when_other_station_busy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    busy_slug = "pyforge-marshal"
    free_slug = "pyforge-doctor"
    fs = FakeFs()
    _seed_live_dispatch_journal(
        tmp_path, fs, slug=busy_slug, run_id="run-busy", story_key="22.1"
    )

    story = "22-5-one-story-in-flight-per-station-stations-in-parallel-overlap-is-loud"
    for slug in (busy_slug, free_slug):
        specs = dispatch_core.planning_specs_dir(tmp_path, slug)
        specs.mkdir(parents=True, exist_ok=True)
        (specs / f"spec-{story}.md").write_text(
            '---\ndifficulty: medium\nsurface: ["src/free/**"]\n---\n',
            encoding="utf-8",
        )
    (tmp_path / "_bmad-output" / "projects" / free_slug).mkdir(parents=True, exist_ok=True)

    class LiveVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            if "marshal" in str(worktree_path):
                return ("src/changed.py",)
            return ()

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

        def worktree_head_sha(self, worktree_path: Path) -> str:
            if "marshal" in str(worktree_path):
                return "bbb222"
            return self.head_sha

    args = argparse.Namespace(slug=free_slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=LiveVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert code == EXIT_OK


def test_overlap_advisory_is_warn_and_dispatch_proceeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    slug_a = "pyforge-marshal"
    slug_b = "pyforge-doctor"
    fs = FakeFs()
    _seed_live_dispatch_journal(
        tmp_path,
        fs,
        slug=slug_a,
        run_id="run-a",
        story_key="22.1",
        session_pid=99,
    )

    in_flight_story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    requested_story = "22-5-one-story-in-flight-per-station-stations-in-parallel-overlap-is-loud"
    shared_surface = 'surface: ["src/shared/**"]'
    for slug, story_name in (
        (slug_a, in_flight_story),
        (slug_b, requested_story),
    ):
        specs = dispatch_core.planning_specs_dir(tmp_path, slug)
        specs.mkdir(parents=True, exist_ok=True)
        (specs / f"spec-{story_name}.md").write_text(
            f"---\ndifficulty: medium\n{shared_surface}\n---\n",
            encoding="utf-8",
        )
        (tmp_path / "_bmad-output" / "projects" / slug).mkdir(parents=True, exist_ok=True)

    class LiveVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            return ()

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

    advisories = cross_station_surface_overlap_advisories(
        fs=fs,
        vcs=LiveVcs(tmp_path),
        process=FakeProcess(alive=True),
        repo_root=tmp_path,
        requested_slug=slug_b,
        requested_story_key=requested_story,
        requested_spec_text=f"---\n{shared_surface}\n---\n",
    )
    assert advisories
    assert advisories[0].code == "MRS-DISP-022"
    assert "LOUD ADVISORY" in advisories[0].message

    args = argparse.Namespace(slug=slug_b, story=requested_story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=LiveVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert code == EXIT_OK
