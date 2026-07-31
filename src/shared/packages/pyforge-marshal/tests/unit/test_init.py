"""Unit tests for ``pyforge.marshal.cli.init`` (Story 1.4, AD-11/AD-21) --
``run_init``'s reconcile-then-act orchestration against the I/O & Edge-Case
Matrix, driven entirely through FAKE ``VcsPort``/``FsPort`` implementations
(no real ``git``/filesystem I/O -- that lives in ``test_vcs_git.py``/
``test_fs_local.py`` and the real end-to-end
``tests/integration/test_init_worktree.py``). Every fake call is recorded in
``.calls`` so "no I/O attempted" scenarios (malformed slug) can be asserted
exactly, not just inferred from the outcome.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema
import pytest

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.harness_bmadloop import HarnessError
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import init as init_module
from pyforge.marshal.cli.init import run_homes, run_init, run_preflight
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.vcs import WorktreeEntry

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "pyforge"
    / "marshal"
    / "schemas"
    / "envelope.v1.json"
)


class FakeVcs:
    def __init__(self, *, repo_root: Path, worktree_dirs: set[Path] | None = None) -> None:
        self.repo_root = repo_root
        self.branches: set[str] = {"main"}
        self.worktrees: dict[str, Path] = {}
        self.calls: list[str] = []
        self.fail_repo_common_root: Exception | None = None
        self.fail_worktree_path_for_branch: Exception | None = None
        self.fail_add_worktree: Exception | None = None
        self.fail_list_worktrees: Exception | None = None
        # Story 1.6: list_worktrees derives its entries from the SAME
        # self.worktrees dict every other FakeVcs method already maintains,
        # plus one synthesized entry for the main checkout itself.
        self.main_branch: str | None = "main"
        self.omit_main_worktree_entry: bool = False
        # Entries appended verbatim (after the dict-derived ones) so a test
        # can model worktrees the loop toolchain never mints: detached HEAD
        # (branch=None) or a non-loop/* branch (review finding: the
        # discovery filter's exclusion branches had no CLI-layer coverage).
        self.extra_worktree_entries: list[WorktreeEntry] = []
        self.add_worktree_calls: list[tuple[Path, Path, str, str]] = []
        # Optionally the SAME set object as a FakeFs.dirs, so a successful
        # add_worktree here makes fs.is_dir(home) true too -- mirrors what a
        # real `git worktree add` does to the real filesystem. Every test
        # whose run reaches the worktree step needs this link now: the
        # in-home project gate probes fs.is_dir(<home planning dir>) right
        # after the worktree step.
        self.worktree_dirs: set[Path] = worktree_dirs if worktree_dirs is not None else set()
        # Mirrors the checked-out tree CONTAINING the project (the normal
        # case: the project is committed on main). The in-home dangling-
        # symlink test flips this off to model an uncommitted project.
        self.populate_home_project_dir = True

    def repo_common_root(self, start: Path) -> Path:
        self.calls.append("repo_common_root")
        if self.fail_repo_common_root:
            raise self.fail_repo_common_root
        return self.repo_root

    def branch_exists(self, repo_root: Path, branch: str) -> bool:
        self.calls.append("branch_exists")
        return branch in self.branches

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        self.calls.append("worktree_path_for_branch")
        if self.fail_worktree_path_for_branch:
            raise self.fail_worktree_path_for_branch
        return self.worktrees.get(branch)

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        self.calls.append("add_worktree")
        self.add_worktree_calls.append((repo_root, home, branch, base))
        if self.fail_add_worktree:
            raise self.fail_add_worktree
        self.branches.add(branch)
        self.worktrees[branch] = home
        self.worktree_dirs.add(home)
        if self.populate_home_project_dir:
            slug = branch.removeprefix("loop/")
            self.worktree_dirs.add(
                home / "_bmad-output" / "projects" / slug / "planning-artifacts"
            )

    def list_worktrees(self, repo_root: Path) -> tuple[WorktreeEntry, ...]:
        self.calls.append("list_worktrees")
        if self.fail_list_worktrees:
            raise self.fail_list_worktrees
        entries: list[WorktreeEntry] = []
        if not self.omit_main_worktree_entry:
            entries.append(WorktreeEntry(path=self.repo_root, branch=self.main_branch))
        for branch, path in self.worktrees.items():
            entries.append(WorktreeEntry(path=path, branch=branch))
        entries.extend(self.extra_worktree_entries)
        return tuple(entries)


class FakeFs:
    def __init__(self, *, project_dirs: set[Path] | None = None) -> None:
        self.dirs: set[Path] = set(project_dirs or set())
        # A subset of `dirs` treated as a real, NON-EMPTY directory by
        # `remove_empty_dir` (Story 1.5) -- a dir in `dirs` but absent here
        # is a real, EMPTY directory.
        self.non_empty_dirs: set[Path] = set()
        self.texts: dict[Path, str] = {}
        self.symlinks: dict[Path, Path] = {}
        self.calls: list[str] = []
        self.write_calls: list[Path] = []
        self.repoint_calls: list[Path] = []
        self.ensure_dir_calls: list[Path] = []
        self.remove_empty_dir_calls: list[Path] = []
        # Story 1.7: paths created via copy_file -- a distinct membership set
        # from `texts` (marker/ack-file WRITES) so a seed-file source/
        # destination can be modeled as "a real file exists here" without
        # also satisfying read_text's contract (copy_file's caller never
        # reads the bytes back through this fake).
        self.files: set[Path] = set()
        self.copy_file_calls: list[tuple[Path, Path]] = []
        self.fail_read_text: Exception | None = None
        self.fail_write_text: Exception | None = None
        self.fail_read_symlink: Exception | None = None
        self.fail_repoint: Exception | None = None
        self.fail_ensure_dir: Exception | None = None
        self.fail_remove_empty_dir: Exception | None = None
        self.fail_resolve_path: Exception | None = None
        self.fail_copy_file: Exception | None = None

    def is_dir(self, path: Path) -> bool:
        self.calls.append("is_dir")
        return path in self.dirs

    def exists(self, path: Path) -> bool:
        """Story 1.6: occupancy probe -- anything this fake knows about
        (a dir, a text file, or a symlink entry) exists. run_homes only
        calls this AFTER read_symlink_target returned None, so the symlink
        membership never masks the real-occupant distinction there. Story
        1.7 extends membership to `files` (copy_file's own destinations/
        pre-seeded sources) -- run_preflight's seed-file loop is this
        method's other caller."""
        self.calls.append("exists")
        return (
            path in self.dirs
            or path in self.texts
            or path in self.symlinks
            or path in self.files
        )

    def read_text(self, path: Path) -> str | None:
        self.calls.append("read_text")
        if self.fail_read_text:
            raise self.fail_read_text
        return self.texts.get(path)

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.calls.append("write_text_atomic")
        self.write_calls.append(path)
        if self.fail_write_text:
            raise self.fail_write_text
        self.texts[path] = content

    def read_symlink_target(self, path: Path) -> Path | None:
        self.calls.append("read_symlink_target")
        if self.fail_read_symlink:
            raise self.fail_read_symlink
        return self.symlinks.get(path)

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        self.calls.append("repoint_symlink_atomic")
        self.repoint_calls.append(path)
        if self.fail_repoint:
            raise self.fail_repoint
        self.symlinks[path] = target

    def is_symlink(self, path: Path) -> bool:  # pragma: no cover - convenience only
        return path in self.symlinks

    def ensure_dir(self, path: Path) -> None:
        self.calls.append("ensure_dir")
        self.ensure_dir_calls.append(path)
        if self.fail_ensure_dir:
            raise self.fail_ensure_dir
        self.dirs.add(path)

    def remove_empty_dir(self, path: Path) -> bool:
        self.calls.append("remove_empty_dir")
        self.remove_empty_dir_calls.append(path)
        if self.fail_remove_empty_dir:
            raise self.fail_remove_empty_dir
        if path in self.non_empty_dirs:
            return False
        self.dirs.discard(path)
        return True

    def resolve_path(self, path: Path) -> Path:
        """Story 1.6: a lightweight realpath fake -- chases `self.symlinks`
        (relative targets joined against the link's own parent, exactly
        like a real symlink) until it lands on a non-symlink path. A path
        never in `self.symlinks` (a plain directory, or one this fake has
        no knowledge of) resolves to itself, matching real
        `Path.resolve()`'s behavior for a path with nothing left to
        follow."""
        self.calls.append("resolve_path")
        if self.fail_resolve_path:
            raise self.fail_resolve_path
        current = path
        seen: set[Path] = set()
        while current in self.symlinks and current not in seen:
            seen.add(current)
            target = self.symlinks[current]
            current = target if target.is_absolute() else (current.parent / target)
        return current

    def copy_file(self, src: Path, dst: Path) -> None:
        self.calls.append("copy_file")
        self.copy_file_calls.append((src, dst))
        if self.fail_copy_file:
            raise self.fail_copy_file
        self.files.add(dst)


class FakeHarness:
    """Story 1.7: a fake ``HarnessPort`` implementation -- drives
    ``run_preflight``'s I/O & Edge-Case Matrix without touching a real
    ``bmad_loop`` install (that lives in
    ``test_harness_bmadloop_preflight.py``). Every call is recorded in
    ``.calls`` for "no further checks ran" assertions, matching
    ``FakeVcs``/``FakeFs``'s own convention."""

    def __init__(self) -> None:
        self.binaries_present: set[str] = set()
        self.version: str | None = "0.9.0"
        self.multiplexer: tuple[str, bool] = ("tmux", True)
        self.fail_multiplexer: Exception | None = None
        self.adapter_binaries: dict[str, str] = {"claude": "claude"}
        self.adapter_seed_files_map: dict[str, tuple[str, ...]] = {"claude": ()}
        self.adapter_first_run_notes: dict[str, str] = {
            "claude": "run `claude` once in the project to accept workspace trust"
        }
        self.fail_adapter: Exception | None = None
        self.feed_error: str | None = None
        self.calls: list[str] = []

    def binary_present(self, binary: str) -> bool:
        self.calls.append(f"binary_present:{binary}")
        return binary in self.binaries_present

    def harness_version(self) -> str | None:
        self.calls.append("harness_version")
        return self.version

    def multiplexer_backend_available(self) -> tuple[str, bool]:
        self.calls.append("multiplexer_backend_available")
        if self.fail_multiplexer:
            raise self.fail_multiplexer
        return self.multiplexer

    def adapter_binary(self, adapter_name: str, project: Path) -> str:
        self.calls.append(f"adapter_binary:{adapter_name}")
        if self.fail_adapter:
            raise self.fail_adapter
        return self.adapter_binaries[adapter_name]

    def adapter_seed_files(self, adapter_name: str, project: Path) -> tuple[str, ...]:
        self.calls.append(f"adapter_seed_files:{adapter_name}")
        if self.fail_adapter:
            raise self.fail_adapter
        return self.adapter_seed_files_map.get(adapter_name, ())

    def adapter_first_run_note(self, adapter_name: str, project: Path) -> str:
        self.calls.append(f"adapter_first_run_note:{adapter_name}")
        if self.fail_adapter:
            raise self.fail_adapter
        return self.adapter_first_run_notes.get(adapter_name, "")

    def story_feed_error(self, project: Path) -> str | None:
        self.calls.append("story_feed_error")
        return self.feed_error


def _namespace(slug: str, *, fmt: str = "text") -> argparse.Namespace:
    return argparse.Namespace(slug=slug, format=fmt)


@pytest.fixture(autouse=True)
def _sandbox_loop_home_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file drives ``cli/init.py``'s pure home-path
    arithmetic through the real ``BMAD_LOOP_HOME_ROOT`` env-var read (the
    one CLI-boundary I/O this module does even with fake ports injected) --
    pinned under ``tmp_path`` so no test can ever compute a path under the
    REAL ``~/.bmad-loops``."""
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))


@pytest.fixture(autouse=True)
def _sandbox_state_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 1.7: same rationale as ``_sandbox_loop_home_root`` above, for
    ``run_preflight``'s ``MARSHAL_STATE_HOME`` read -- pinned under
    ``tmp_path`` so no preflight test can ever touch the REAL
    ``~/.local/state/pyforge-marshal/adapter-acknowledgements.json``."""
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(tmp_path / "state-home"))


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path / "repo"


def _provisioned_project(repo_root: Path, slug: str) -> set[Path]:
    return {repo_root / "_bmad-output" / "projects" / slug / "planning-artifacts"}


def _home_with_project(home: Path, slug: str) -> set[Path]:
    """A pre-existing home directory whose checked-out tree contains the
    project -- what the in-home project gate probes after the worktree
    step reports skipped."""
    return {home, home / "_bmad-output" / "projects" / slug / "planning-artifacts"}


def _tier3_paths(repo_root: Path, home: Path, slug: str) -> tuple[Path, Path]:
    """(canonical, local) Tier-3 paths for `slug`, matching `cli/init.py`'s
    own computation."""
    canonical = repo_root / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    local = home / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    return canonical, local


def _converge_tier3(fs: FakeFs, repo_root: Path, home: Path, slug: str) -> None:
    """Pre-seed `fs` so the `tier3_backlink` step is already converged
    (matching symlink + canonical dir present) -- used by tests that need
    to isolate the planning-artifacts marker/symlink pair from this new
    step's own writes, which otherwise land in the SAME `repoint_calls`
    list (both steps call `repoint_symlink_atomic`)."""
    canonical, local = _tier3_paths(repo_root, home, slug)
    fs.dirs.add(canonical)
    fs.symlinks[local] = canonical


# --- fresh provision -----------------------------------------------------------


def test_fresh_provision_all_steps_done(repo_root, capsys):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "worktree: done" in out
    assert "tier3_backlink: done" in out
    assert "symlink: done" in out
    assert "marker: done" in out
    assert vcs.add_worktree_calls == [(repo_root, vcs.worktrees["loop/acme"], "loop/acme", "main")]


def test_fresh_provision_prints_launch_line(repo_root, capsys):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "export BMAD_ACTIVE_PROJECT=acme" in out
    assert "cd " in out


def test_launch_line_quotes_a_home_path_with_spaces(repo_root, tmp_path, monkeypatch, capsys):
    """Review finding: the launch line embedded the home path unquoted, so
    a BMAD_LOOP_HOME_ROOT override containing a space produced a line that
    word-splits on paste instead of the AC's directly-pasteable command."""
    import shlex

    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "my loops"))
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    home = vcs.worktrees["loop/acme"]
    assert f"cd {shlex.quote(str(home))} && export BMAD_ACTIVE_PROJECT=acme" in out


def test_fresh_provision_writes_symlink_before_marker(repo_root):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    run_init(_namespace("acme"), vcs=vcs, fs=fs)
    # symlink write recorded strictly before the marker write
    assert fs.calls.index("repoint_symlink_atomic") < fs.calls.index("write_text_atomic")


def test_fresh_provision_marker_and_symlink_agree_with_slug(repo_root):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    run_init(_namespace("acme"), vcs=vcs, fs=fs)
    home = vcs.worktrees["loop/acme"]
    marker_path = home / "_bmad" / "custom" / ".active-project"
    link_path = home / "_bmad-output" / "planning-artifacts"
    assert fs.texts[marker_path].strip() == "acme"
    assert fs.symlinks[link_path] == Path("projects/acme/planning-artifacts")


# --- idempotent re-run -----------------------------------------------------------


def test_idempotent_rerun_all_steps_skipped_and_zero_writes(repo_root, capsys):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    # worktree_dirs=fs.dirs: a successful add_worktree marks `home` as a
    # real dir on the SAME fake fs, exactly like a real `git worktree add`
    # would -- needed for the re-run's stale/prunable-worktree guard to see
    # the (fake) worktree as genuinely present, not phantom.
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    first_exit = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert first_exit == EXIT_OK
    first_out = capsys.readouterr().out  # drain first run's output
    assert "tier3_backlink: done" in first_out

    writes_before = list(fs.write_calls)
    repoints_before = list(fs.repoint_calls)
    ensure_dir_calls_before = list(fs.ensure_dir_calls)
    remove_empty_dir_calls_before = list(fs.remove_empty_dir_calls)
    add_worktree_calls_before = list(vcs.add_worktree_calls)

    second_exit = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert second_exit == EXIT_OK
    out = capsys.readouterr().out
    assert "worktree: skipped" in out
    assert "tier3_backlink: skipped" in out
    assert "symlink: skipped" in out
    assert "marker: skipped" in out
    # zero NEW writes on the second call
    assert fs.write_calls == writes_before
    assert fs.repoint_calls == repoints_before
    assert fs.ensure_dir_calls == ensure_dir_calls_before
    assert fs.remove_empty_dir_calls == remove_empty_dir_calls_before
    assert vcs.add_worktree_calls == add_worktree_calls_before


# --- malformed slug: MRS-INIT-001, no I/O at all --------------------------------


@pytest.mark.parametrize(
    "bad_slug", ["", "../evil", "a/b", ".", "..", "has space", "a\\b"]
)
def test_malformed_slug_reports_finding_with_zero_io(repo_root, bad_slug, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    fs = FakeFs()
    exit_code = run_init(_namespace(bad_slug), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-001" in out
    assert vcs.calls == []
    assert fs.calls == []


# --- unknown project: MRS-INIT-002, no worktree created -------------------------


def test_unknown_project_reports_finding_and_creates_no_worktree(repo_root, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    fs = FakeFs()  # no project dirs registered
    exit_code = run_init(_namespace("ghost-project"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-002" in out
    assert vcs.add_worktree_calls == []
    assert "worktree_path_for_branch" not in vcs.calls


def test_project_dir_without_planning_artifacts_reports_mrs_init_002(repo_root, capsys):
    """Review finding: the project dir existing is not enough -- without
    this check, a project missing its planning-artifacts subdirectory would
    pass this gate and the symlink step would create a DANGLING link."""
    vcs = FakeVcs(repo_root=repo_root)
    fs = FakeFs(project_dirs={repo_root / "_bmad-output" / "projects" / "acme"})
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-002" in out
    assert vcs.add_worktree_calls == []


# --- worktree op fails: MRS-INIT-004 --------------------------------------------


def test_worktree_add_failure_reports_finding_and_stops(repo_root, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    vcs.fail_add_worktree = VcsCommandError("locked index")
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "worktree: failed" in out
    assert "symlink: failed" in out
    assert "marker: failed" in out
    assert fs.write_calls == []
    assert fs.repoint_calls == []


def test_repo_root_resolution_failure_reports_mrs_init_004(repo_root, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    vcs.fail_repo_common_root = VcsCommandError("not a git repo")
    fs = FakeFs()
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert fs.calls == []  # never got far enough to check the project dir


def test_worktree_conflict_at_a_different_path_reports_mrs_init_004(repo_root, tmp_path, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    elsewhere = tmp_path / "elsewhere"
    vcs.worktrees["loop/acme"] = elsewhere
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert vcs.add_worktree_calls == []


def test_stale_worktree_entry_reports_finding_instead_of_skipping(repo_root, tmp_path, capsys):
    """Review finding: git can still register a worktree whose directory was
    deleted by hand rather than via `git worktree remove` (this repo's own
    history: a failed removal still de-registers). Trusting the git record
    alone would silently write marker/symlink into a phantom path."""
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))  # home NOT in fs.dirs
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "prune" in out
    assert fs.write_calls == []
    assert fs.repoint_calls == []


# --- marker/symlink desync: MRS-INIT-003, blocking before any write ------------


def test_marker_symlink_desync_blocks_before_any_write(repo_root, tmp_path, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs = FakeFs(
        project_dirs=_provisioned_project(repo_root, "acme") | _home_with_project(home, "acme")
    )
    # Pre-converge the (independent) tier3_backlink step so its own write
    # doesn't land in the same fs.repoint_calls list this test inspects --
    # this test's own concern is the planning-artifacts marker/symlink pair.
    _converge_tier3(fs, repo_root, home, "acme")
    fs.texts[home / "_bmad" / "custom" / ".active-project"] = "other-project\n"
    fs.symlinks[home / "_bmad-output" / "planning-artifacts"] = Path(
        "projects/yet-another/planning-artifacts"
    )
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-003" in out
    assert "tier3_backlink: skipped" in out
    assert fs.write_calls == []
    assert fs.repoint_calls == []


def test_marker_alone_with_no_symlink_is_not_a_desync(repo_root, tmp_path):
    """Only ONE of marker/symlink present is a partial (not-yet-converged)
    state, not a desync -- the blocking check requires BOTH to disagree."""
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs = FakeFs(
        project_dirs=_provisioned_project(repo_root, "acme") | _home_with_project(home, "acme")
    )
    fs.texts[home / "_bmad" / "custom" / ".active-project"] = "some-stale-value\n"
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    assert fs.repoint_calls  # symlink still got written
    assert fs.write_calls  # marker got corrected to acme


# --- symlink/marker write failures: MRS-INIT-004 --------------------------------


def test_symlink_write_failure_stops_before_marker(repo_root, tmp_path, capsys):
    home = tmp_path / "loop-homes" / "acme"
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    vcs.worktrees["loop/acme"] = home
    fs.dirs |= _home_with_project(home, "acme")
    # Pre-converge tier3_backlink so `fail_repoint` (which fails EVERY
    # repoint_symlink_atomic call, tier3's included) hits the
    # planning-artifacts symlink step specifically, not this independent one.
    _converge_tier3(fs, repo_root, home, "acme")
    fs.fail_repoint = FsError("disk full")
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "symlink: failed" in out
    assert "marker: failed" in out
    assert fs.write_calls == []  # marker was never attempted


def test_marker_write_failure_reports_finding(repo_root, capsys):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    fs.fail_write_text = FsError("disk full")
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "symlink: done" in out
    assert "marker: failed" in out


# --- JSON envelope + schema validation -------------------------------------------


def test_json_format_emits_a_schema_valid_envelope(repo_root):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        exit_code = run_init(_namespace("acme", fmt="json"), vcs=vcs, fs=fs)
    finally:
        sys.stdout = old_stdout
    assert exit_code == EXIT_OK
    payload = json.loads(captured.getvalue())
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)
    assert payload["command"] == "init"
    assert payload["status"] == "ok"
    assert payload["data"]["launch_line"] == (
        f"cd {vcs.worktrees['loop/acme']} && export BMAD_ACTIVE_PROJECT=acme"
    )


def test_json_format_error_path_has_no_launch_line(repo_root):
    vcs = FakeVcs(repo_root=repo_root)
    fs = FakeFs()  # unknown project
    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        exit_code = run_init(_namespace("ghost", fmt="json"), vcs=vcs, fs=fs)
    finally:
        sys.stdout = old_stdout
    assert exit_code != EXIT_OK
    payload = json.loads(captured.getvalue())
    assert "launch_line" not in payload["data"]
    assert payload["findings"][0]["code"] == "MRS-INIT-002"


# --- in-home project gate: the tree the symlink resolves in ---------------------


def test_project_missing_from_home_tree_blocks_before_symlink(repo_root, capsys):
    """Review finding: the pre-flight gate checks the MAIN CHECKOUT's tree,
    but the symlink resolves inside the HOME's tree (minted from `main` or a
    pre-existing loop branch). An uncommitted brand-new project passed the
    pre-flight and init exited 0 having written a DANGLING symlink."""
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    vcs.populate_home_project_dir = False  # `main` does not carry the project
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "planning-artifacts" in out
    assert fs.write_calls == []
    assert fs.repoint_calls == []


def test_project_missing_from_a_preexisting_home_tree_blocks_too(repo_root, tmp_path, capsys):
    """Attach path: a stale loop/<slug> branch whose tree no longer carries
    the project must block the same way, not report all-skipped."""
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme") | {home})
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert fs.write_calls == []
    assert fs.repoint_calls == []


# --- unrecognized symlink target: blocked, never silently repointed -------------


def test_unparseable_symlink_target_blocks_as_desync(repo_root, tmp_path, capsys):
    """Review finding: a symlink whose target does not parse as
    projects/<slug>/planning-artifacts (hand repair, older tooling) slipped
    past the both-slugs-parse desync check and was silently repointed --
    exactly the overwrite MRS-INIT-003 exists to refuse."""
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs = FakeFs(
        project_dirs=_provisioned_project(repo_root, "acme") | _home_with_project(home, "acme")
    )
    # Pre-converge the independent tier3_backlink step -- see the comment in
    # test_marker_symlink_desync_blocks_before_any_write.
    _converge_tier3(fs, repo_root, home, "acme")
    fs.symlinks[home / "_bmad-output" / "planning-artifacts"] = Path(
        "/somewhere/else/planning-artifacts"
    )
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-003" in out
    assert fs.write_calls == []
    assert fs.repoint_calls == []


# --- environment failures land in the envelope, never a raw traceback -----------


def test_deleted_cwd_reports_mrs_init_004(repo_root, capsys, monkeypatch):
    """Review finding: Path.cwd() raises OSError when the invocation
    directory was deleted underneath the process (routine around concurrent
    worktree teardown) -- previously escaped as a raw traceback."""

    def _cwd_gone(cls):
        raise FileNotFoundError("current working directory was deleted")

    monkeypatch.setattr("pathlib.Path.cwd", classmethod(_cwd_gone))
    vcs = FakeVcs(repo_root=repo_root)
    fs = FakeFs()
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "working directory" in out
    assert vcs.calls == []


def test_unresolvable_home_reports_mrs_init_004(repo_root, capsys, monkeypatch):
    """Review finding: with BMAD_LOOP_HOME_ROOT unset and HOME unresolvable
    (cron/systemd -- Marshal's own unattended context), Path.home() raises
    RuntimeError -- previously escaped as a raw traceback."""
    monkeypatch.delenv("BMAD_LOOP_HOME_ROOT")

    def _no_home(cls):
        raise RuntimeError("could not determine a home directory")

    monkeypatch.setattr("pathlib.Path.home", classmethod(_no_home))
    vcs = FakeVcs(repo_root=repo_root)
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "loop-home root" in out
    assert vcs.add_worktree_calls == []


# --- git-ref-invalid slug shapes: crisp MRS-INIT-001, no I/O --------------------


@pytest.mark.parametrize("bad_slug", ["x.lock", ".foo", "foo.", "a..b"])
def test_git_ref_invalid_slug_shapes_report_mrs_init_001(repo_root, bad_slug, capsys):
    """Review finding: these pass the shared slug shape check but git
    refuses them inside loop/<slug> -- they died later as an opaque
    MRS-INIT-004 carrying raw git stderr instead of this pre-I/O
    rejection."""
    vcs = FakeVcs(repo_root=repo_root)
    fs = FakeFs()
    exit_code = run_init(_namespace(bad_slug), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-001" in out
    assert "branch" in out
    assert vcs.calls == []
    assert fs.calls == []


# --- relative BMAD_LOOP_HOME_ROOT is anchored before any writer sees it ---------


def test_relative_loop_home_root_is_anchored_absolute(repo_root, tmp_path, monkeypatch):
    """Review finding: a relative override was resolved against repo_root
    by `git -C` but against the CWD by LocalFs -- two writers, two homes,
    exit 0. Anchoring to the CWD once keeps every consumer on one path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", "rel-loop-homes")
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    (_, home, _, _) = vcs.add_worktree_calls[0]
    assert home.is_absolute()
    assert home == tmp_path / "rel-loop-homes" / "acme"


# --- tier3_backlink (Story 1.5): the full I/O & Edge-Case Matrix ---------------


def test_tier3_backlink_fresh_creates_canonical_and_symlink(repo_root, capsys):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "tier3_backlink: done" in out
    home = vcs.worktrees["loop/acme"]
    canonical, local = _tier3_paths(repo_root, home, "acme")
    assert canonical in fs.dirs
    assert fs.symlinks[local] == canonical


def test_tier3_backlink_self_heal_recreates_missing_canonical_dir(repo_root, tmp_path, capsys):
    """Symlink target already matches canonical, but the canonical directory
    itself is missing on disk (e.g. hand-deleted) -- recreated, symlink
    rewritten, still reports `done` (not `skipped`)."""
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    canonical, local = _tier3_paths(repo_root, home, "acme")
    fs = FakeFs(
        project_dirs=_provisioned_project(repo_root, "acme") | _home_with_project(home, "acme")
    )
    fs.symlinks[local] = canonical  # matches, but canonical dir absent from fs.dirs
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "tier3_backlink: done" in out
    assert canonical in fs.dirs
    assert fs.symlinks[local] == canonical


def test_tier3_backlink_stale_empty_local_dir_is_replaced(repo_root, tmp_path, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    canonical, local = _tier3_paths(repo_root, home, "acme")
    fs = FakeFs(
        project_dirs=_provisioned_project(repo_root, "acme")
        | _home_with_project(home, "acme")
        | {local}  # a real, empty local directory -- no symlink
    )
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "tier3_backlink: done" in out
    assert local in fs.remove_empty_dir_calls
    assert fs.symlinks[local] == canonical


def test_tier3_backlink_real_nonempty_local_dir_reports_mrs_init_005(repo_root, tmp_path, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    canonical, local = _tier3_paths(repo_root, home, "acme")
    fs = FakeFs(
        project_dirs=_provisioned_project(repo_root, "acme")
        | _home_with_project(home, "acme")
        | {local}
    )
    fs.non_empty_dirs.add(local)
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-005" in out
    assert str(local) in out
    assert str(canonical) in out
    # left untouched: no write attempted, the directory is still present
    assert local in fs.dirs
    assert fs.ensure_dir_calls == []
    assert local not in fs.symlinks


def test_tier3_backlink_wrong_target_symlink_is_repointed_silently(repo_root, tmp_path, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    canonical, local = _tier3_paths(repo_root, home, "acme")
    fs = FakeFs(
        project_dirs=_provisioned_project(repo_root, "acme") | _home_with_project(home, "acme")
    )
    fs.symlinks[local] = Path("/somewhere/else/implementation-artifacts")
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "tier3_backlink: done" in out
    assert fs.symlinks[local] == canonical


def test_tier3_backlink_read_symlink_failure_reports_mrs_init_004(repo_root, capsys):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    fs.fail_read_symlink = FsError("permission denied")
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "tier3_backlink: failed" in out


def test_tier3_backlink_remove_empty_dir_failure_reports_mrs_init_004(repo_root, tmp_path, capsys):
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    _, local = _tier3_paths(repo_root, home, "acme")
    fs = FakeFs(
        project_dirs=_provisioned_project(repo_root, "acme")
        | _home_with_project(home, "acme")
        | {local}
    )
    fs.fail_remove_empty_dir = FsError("permission denied")
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "tier3_backlink: failed" in out


def test_tier3_backlink_ensure_dir_failure_reports_mrs_init_004(repo_root, capsys):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    fs.fail_ensure_dir = FsError("disk full")
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "tier3_backlink: failed" in out
    assert fs.repoint_calls == []  # never reached


def test_tier3_backlink_repoint_failure_reports_mrs_init_004(repo_root, capsys):
    fs = FakeFs(project_dirs=_provisioned_project(repo_root, "acme"))
    vcs = FakeVcs(repo_root=repo_root, worktree_dirs=fs.dirs)
    fs.fail_repoint = FsError("disk full")
    exit_code = run_init(_namespace("acme"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-INIT-004" in out
    assert "tier3_backlink: failed" in out
    assert "symlink: failed" in out
    assert "marker: failed" in out
    assert fs.write_calls == []


# --- verdict classification of the five new codes --------------------------------


def test_init_finding_codes_classify_as_documented():
    from pyforge.marshal.core.model import Verdict
    from pyforge.marshal.core.verdict import classify

    assert classify("MRS-INIT-001") == Verdict.UNEVALUABLE
    assert classify("MRS-INIT-002") == Verdict.UNEVALUABLE
    assert classify("MRS-INIT-003") == Verdict.ERROR
    assert classify("MRS-INIT-004") == Verdict.ERROR
    assert classify("MRS-INIT-005") == Verdict.ERROR
    assert classify("MRS-HOMES-001") == Verdict.ERROR
    assert classify("MRS-HOMES-002") == Verdict.ERROR
    assert classify("MRS-HOMES-003") == Verdict.ERROR


# =====================================================================
# ``run_homes`` (Story 1.6, FR-4/FR-8) -- CLI-layer coverage of the same
# I/O & Edge-Case Matrix core/status.py's own tests exercise at the pure
# logic layer (tests/unit/test_status.py); this file drives the full
# gather -> evaluate -> envelope path through the FakeVcs/FakeFs seam.
# =====================================================================


def _homes_namespace(*, fmt: str = "text") -> argparse.Namespace:
    return argparse.Namespace(format=fmt)


def _seed_clean_home(fs: FakeFs, vcs: FakeVcs, repo_root: Path, home: Path, slug: str) -> None:
    branch = f"loop/{slug}"
    vcs.worktrees[branch] = home
    # A REAL `marshal init`-provisioned home's directory always exists on
    # disk -- without this, run_homes's phantom/prunable-worktree guard
    # (review finding) would treat every one of these fixtures as stale.
    fs.dirs.add(home)
    marker_path = home / "_bmad" / "custom" / ".active-project"
    link_path = home / "_bmad-output" / "planning-artifacts"
    canonical, local = _tier3_paths(repo_root, home, slug)
    fs.texts[marker_path] = f"{slug}\n"
    fs.symlinks[link_path] = Path(f"projects/{slug}/planning-artifacts")
    fs.symlinks[local] = canonical
    # The canonical store really exists for a clean home -- without this,
    # the dangling-backlink check (review finding) would flag every one of
    # these fixtures as MRS-HOMES-002.
    fs.dirs.add(canonical)


def test_homes_lists_two_clean_provisioned_homes(repo_root, tmp_path):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    _seed_clean_home(fs, vcs, repo_root, tmp_path / "loop-homes" / "acme", "acme")
    _seed_clean_home(fs, vcs, repo_root, tmp_path / "loop-homes" / "beta", "beta")

    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        exit_code = run_homes(_homes_namespace(fmt="json"), vcs=vcs, fs=fs)
    finally:
        sys.stdout = old_stdout
    assert exit_code == EXIT_OK
    payload = json.loads(captured.getvalue())
    homes = {row["slug"]: row for row in payload["data"]["homes"]}
    assert set(homes) == {"acme", "beta"}
    assert all(not row["desynced"] for row in homes.values())
    assert payload["data"]["main_checkout"]["desynced"] is False
    assert payload["findings"] == []


def test_homes_zero_loop_worktrees_reports_only_main_checkout(repo_root):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)

    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        exit_code = run_homes(_homes_namespace(fmt="json"), vcs=vcs, fs=fs)
    finally:
        sys.stdout = old_stdout
    assert exit_code == EXIT_OK
    payload = json.loads(captured.getvalue())
    assert payload["data"]["homes"] == []
    assert payload["data"]["main_checkout"]["path"] == str(repo_root)


def test_homes_reports_marker_symlink_desync(repo_root, tmp_path, capsys):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs.dirs.add(home)
    marker_path = home / "_bmad" / "custom" / ".active-project"
    link_path = home / "_bmad-output" / "planning-artifacts"
    canonical, local = _tier3_paths(repo_root, home, "acme")
    fs.texts[marker_path] = "other-project\n"
    fs.symlinks[link_path] = Path("projects/yet-another/planning-artifacts")
    fs.symlinks[local] = canonical
    fs.dirs.add(canonical)  # healthy Tier-3, so only the slug desync fires

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-001" in out


def test_homes_reports_the_branch_agreement_blind_spot(repo_root, tmp_path, capsys):
    """Marker and symlink agree with EACH OTHER but not with the home's own
    branch -- exactly the deferred-work blind spot MRS-INIT-003's own
    two-way check would miss."""
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "bar"
    vcs.worktrees["loop/bar"] = home
    fs.dirs.add(home)
    marker_path = home / "_bmad" / "custom" / ".active-project"
    link_path = home / "_bmad-output" / "planning-artifacts"
    fs.texts[marker_path] = "foo\n"
    fs.symlinks[link_path] = Path("projects/foo/planning-artifacts")

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-001" in out
    assert "foo" in out
    assert "bar" in out


def test_homes_reports_tier3_mismatch(repo_root, tmp_path, capsys):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs.dirs.add(home)
    marker_path = home / "_bmad" / "custom" / ".active-project"
    link_path = home / "_bmad-output" / "planning-artifacts"
    _, local = _tier3_paths(repo_root, home, "acme")
    fs.texts[marker_path] = "acme\n"
    fs.symlinks[link_path] = Path("projects/acme/planning-artifacts")
    fs.symlinks[local] = tmp_path / "somewhere-else"

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-002" in out


def test_homes_reports_a_real_non_symlink_tier3_occupant(repo_root, tmp_path, capsys):
    """A real, non-symlink directory left at the local Tier-3 path (e.g. by
    init's own MRS-INIT-005 refusal) is NOT 'never provisioned' -- it means
    Tier-3 is not single-sourced for this home, and must be flagged, not
    silently treated as absent (review finding)."""
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs.dirs.add(home)
    marker_path = home / "_bmad" / "custom" / ".active-project"
    link_path = home / "_bmad-output" / "planning-artifacts"
    _, local = _tier3_paths(repo_root, home, "acme")
    fs.texts[marker_path] = "acme\n"
    fs.symlinks[link_path] = Path("projects/acme/planning-artifacts")
    # `local` is a REAL directory (in `fs.dirs`), deliberately NOT a symlink
    # (absent from `fs.symlinks`) -- exactly the MRS-INIT-005 leftover state.
    fs.dirs.add(local)

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-002" in out


def test_homes_reports_a_phantom_prunable_worktree(repo_root, tmp_path, capsys):
    """git still registers a `loop/<slug>` worktree, but its directory was
    deleted by hand rather than via `git worktree remove` -- must be named
    as its own finding, never silently reported as a clean, unprovisioned
    home (review finding; mirrors run_init's own identical guard)."""
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    ghost = tmp_path / "loop-homes" / "ghost"
    vcs.worktrees["loop/ghost"] = ghost
    # Deliberately NOT added to fs.dirs -- the directory is gone on disk.

    exit_code = run_homes(_homes_namespace(fmt="json"), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["homes"] == []
    assert any(f["code"] == "MRS-HOMES-003" for f in payload["findings"])
    assert any("ghost" in f["message"] for f in payload["findings"])


def test_homes_reports_main_checkout_desync(repo_root, capsys):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    repo_marker = repo_root / "_bmad" / "custom" / ".active-project"
    repo_link = repo_root / "_bmad-output" / "planning-artifacts"
    fs.texts[repo_marker] = "other\n"
    fs.symlinks[repo_link] = Path("projects/elsewhere/planning-artifacts")

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-001" in out
    assert str(repo_root) in out


def test_homes_list_worktrees_failure_reports_mrs_homes_003(repo_root, capsys):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    vcs.fail_list_worktrees = VcsCommandError("git worktree list failed")

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-003" in out


def test_homes_repo_root_resolution_failure_reports_mrs_homes_003(repo_root, capsys):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    vcs.fail_repo_common_root = VcsCommandError("not a git repo")

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-003" in out


def test_homes_missing_main_checkout_entry_reports_mrs_homes_003(repo_root, capsys):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    vcs.omit_main_worktree_entry = True

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-003" in out


def test_homes_resolve_path_failure_reports_mrs_homes_003(repo_root, capsys):
    fs = FakeFs()
    fs.fail_resolve_path = FsError("permission denied")
    vcs = FakeVcs(repo_root=repo_root)

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-003" in out


def test_homes_read_text_failure_reports_mrs_homes_003(repo_root, tmp_path, capsys):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    # Home directory exists (else the new phantom-worktree guard would skip
    # it before ever reaching fs.read_text, testing the wrong code path).
    fs.dirs.add(home)
    fs.fail_read_text = FsError("permission denied")

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-003" in out


def test_homes_performs_zero_writes(repo_root, tmp_path):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs.dirs.add(home)

    run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert fs.write_calls == []
    assert fs.repoint_calls == []
    assert fs.ensure_dir_calls == []
    assert fs.remove_empty_dir_calls == []
    assert vcs.add_worktree_calls == []


def test_homes_json_format_emits_a_schema_valid_envelope(repo_root, tmp_path):
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    _seed_clean_home(fs, vcs, repo_root, tmp_path / "loop-homes" / "acme", "acme")

    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        exit_code = run_homes(_homes_namespace(fmt="json"), vcs=vcs, fs=fs)
    finally:
        sys.stdout = old_stdout
    assert exit_code == EXIT_OK
    payload = json.loads(captured.getvalue())
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)
    assert payload["command"] == "homes"
    assert payload["status"] == "ok"


def test_homes_parser_rejects_a_positional_argument(capsys):
    """FR-8: full enumeration only, no selection flags -- proven against
    the REAL parser via cli.main (review finding: the earlier version of
    this test asserted a property of this file's own namespace helper,
    which could never fail regardless of what add_homes_subparser does).
    argparse rejects the stray positional before any handler runs, and
    main relays its exit code 2."""
    from pyforge.marshal.cli.main import main

    assert main(["homes", "stray-slug"]) == 2
    err = capsys.readouterr().err
    assert "stray-slug" in err


def test_homes_excludes_detached_head_and_non_loop_worktrees(repo_root, tmp_path, capsys):
    """The discovery filter's exclusion branches (review finding: previously
    untested at the CLI layer): a detached-HEAD worktree (branch=None --
    exercising the filter's own None guard) and a non-loop/* linked worktree
    are neither homes nor the main checkout, so they produce no row, no
    finding, and no gathered reads."""
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    _seed_clean_home(fs, vcs, repo_root, tmp_path / "loop-homes" / "acme", "acme")
    vcs.extra_worktree_entries = [
        WorktreeEntry(path=tmp_path / "detached-worktree", branch=None),
        WorktreeEntry(path=tmp_path / "feature-worktree", branch="feature/x"),
    ]

    exit_code = run_homes(_homes_namespace(fmt="json"), vcs=vcs, fs=fs)
    assert exit_code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert [row["slug"] for row in payload["data"]["homes"]] == ["acme"]
    assert payload["findings"] == []


def test_homes_reports_a_real_directory_at_planning_artifacts(repo_root, tmp_path, capsys):
    """A real (non-symlink) directory materialized where a home's
    planning-artifacts symlink belongs previously read as benign absence
    (review finding) -- it means writes no longer reach the canonical
    project tree, exactly the MRS-HOMES-001 violation class."""
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs.dirs.add(home)
    fs.texts[home / "_bmad" / "custom" / ".active-project"] = "acme\n"
    # The link path is a REAL directory (in fs.dirs), deliberately NOT a
    # symlink entry.
    fs.dirs.add(home / "_bmad-output" / "planning-artifacts")

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-001" in out
    assert "occupied" in out


def test_homes_reports_a_real_directory_at_main_checkout_planning_artifacts(
    repo_root, capsys
):
    """Same occupancy blind spot on the main checkout's own link (review
    finding): the two-way rule must name a real-directory occupant, not
    read it as 'symlink absent'."""
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    fs.dirs.add(repo_root / "_bmad-output" / "planning-artifacts")

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-001" in out
    assert str(repo_root) in out
    assert "occupied" in out


def test_homes_reports_a_plain_file_occupying_tier3(repo_root, tmp_path, capsys):
    """A regular FILE at the local Tier-3 path is the third occupied state
    (review finding: the first occupancy fix probed is_dir only) -- it
    blocks any future backlink exactly like a directory occupant and must
    surface as MRS-HOMES-002, never as 'never provisioned'."""
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs.dirs.add(home)
    fs.texts[home / "_bmad" / "custom" / ".active-project"] = "acme\n"
    fs.symlinks[home / "_bmad-output" / "planning-artifacts"] = Path(
        "projects/acme/planning-artifacts"
    )
    _, local = _tier3_paths(repo_root, home, "acme")
    # A plain file (in fs.texts), neither a symlink nor a directory.
    fs.texts[local] = "stray content\n"

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-002" in out


def test_homes_reports_a_backlink_dangling_at_the_canonical_path(
    repo_root, tmp_path, capsys
):
    """A backlink that resolves to the RIGHT canonical path whose store was
    deleted after provisioning previously reported clean (review finding),
    though every write through it would fail and marshal init's own
    convergence check (is_dir(canonical)) rejects the same state."""
    fs = FakeFs()
    vcs = FakeVcs(repo_root=repo_root)
    home = tmp_path / "loop-homes" / "acme"
    vcs.worktrees["loop/acme"] = home
    fs.dirs.add(home)
    fs.texts[home / "_bmad" / "custom" / ".active-project"] = "acme\n"
    fs.symlinks[home / "_bmad-output" / "planning-artifacts"] = Path(
        "projects/acme/planning-artifacts"
    )
    canonical, local = _tier3_paths(repo_root, home, "acme")
    fs.symlinks[local] = canonical
    # canonical deliberately NOT in fs.dirs -- the store is gone.

    exit_code = run_homes(_homes_namespace(), vcs=vcs, fs=fs)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-HOMES-002" in out
    assert "does not exist" in out


# =====================================================================
# ``run_preflight`` (Story 1.7, FR-7/FR-47/FR-52) -- CLI-layer coverage of
# the full I/O & Edge-Case Matrix, driven through Fake{Vcs,Fs,Harness}. The
# real ``BmadLoopHarness`` against the installed ``bmad_loop`` package is
# covered separately in ``test_harness_bmadloop_preflight.py``; the real
# end-to-end pass (real git, real harness on PATH) is
# ``tests/integration/test_init_worktree.py``.
#
# ``conventional_project_policy_path`` (``cli/config.py``) is NOT
# DI-injectable -- it resolves from THIS PACKAGE's own on-disk location, not
# from ``tmp_path`` -- so every test below uses the slug "acme" (confirmed
# absent from this repo's real ``_bmad-output/projects/``), which makes
# ``policy_path.is_file()`` False and composition fall through to Marshal's
# bare ``DEFAULT_POLICY`` (``verify_commands=()``, adapter always resolves
# to the template baseline "claude"). Tests that need a NON-bare policy
# layer (an unknown key, a bad verify command, a bricking attempt count)
# monkeypatch ``init_module.conventional_project_policy_path`` to point at a
# real ``tmp_path`` TOML file instead of writing into the real repo tree.
# =====================================================================


def _preflight_namespace(
    slug: str, *, acknowledge: str | None = None, fmt: str = "text"
) -> argparse.Namespace:
    return argparse.Namespace(slug=slug, acknowledge=acknowledge, format=fmt)


def _seed_acknowledged(fs: FakeFs, tmp_path: Path, names: list[str]) -> Path:
    """Pre-seed the (sandboxed, per ``_sandbox_state_home``) ack state file
    as already carrying ``names``. Returns the path, for assertions."""
    ack_path = tmp_path / "state-home" / "adapter-acknowledgements.json"
    fs.texts[ack_path] = json.dumps(names)
    return ack_path


def _converged_harness() -> FakeHarness:
    harness = FakeHarness()
    harness.binaries_present = {"bmad-loop", "claude"}
    return harness


# --- fully converged: zero findings, exit 0 --------------------------------


def test_preflight_fully_converged_reports_zero_findings(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "findings:" not in out
    assert "harness_version: 0.9.0" in out
    assert "multiplexer: backend='tmux' available=True" in out
    assert "adapter: name='claude' binary_present=True" in out
    assert "story_feed: resolvable=True error=None" in out
    assert "main_checked_out_once: True" in out
    assert "first_run_acknowledged: True" in out


def test_preflight_fully_converged_json_matches_schema(repo_root, tmp_path):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    _seed_acknowledged(fs, tmp_path, ["claude"])

    import io
    import sys

    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        exit_code = run_preflight(
            _preflight_namespace(slug, fmt="json"), vcs=vcs, fs=fs, harness=harness
        )
    finally:
        sys.stdout = old_stdout
    assert exit_code == EXIT_OK
    payload = json.loads(captured.getvalue())
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=payload, schema=schema)
    assert payload["command"] == "preflight"
    assert payload["status"] == "ok"
    assert payload["findings"] == []
    assert payload["data"]["seed_files"] == []
    assert payload["data"]["verify_commands"] == []


# --- loop home not provisioned: MRS-PREFLIGHT-009, no further checks ------


def test_preflight_loop_home_not_provisioned_reports_finding_with_no_further_checks(
    repo_root, tmp_path, capsys
):
    fs = FakeFs()  # home NOT registered as a dir
    vcs = FakeVcs(repo_root=repo_root)
    harness = FakeHarness()

    exit_code = run_preflight(_preflight_namespace("acme"), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-009" in out
    assert "marshal init" in out
    assert harness.calls == []
    assert vcs.calls == []


# --- harness binary absent: MRS-PREFLIGHT-001 -------------------------------


def test_preflight_harness_binary_absent_reports_finding(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.binaries_present.discard("bmad-loop")
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-001" in out
    assert "harness_version: None" in out


# --- harness version outside range: MRS-PREFLIGHT-002 ----------------------


def test_preflight_harness_version_outside_range_reports_finding(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.version = "0.10.2"
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-002" in out
    assert "0.10.2" in out
    assert ">=0.9.0,<0.10" in out


def test_preflight_harness_version_unparseable_reports_finding(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.version = None  # binary present but --version could not be determined
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-002" in out


# --- multiplexer unavailable: MRS-PREFLIGHT-003 -----------------------------


def test_preflight_multiplexer_unavailable_reports_finding(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.multiplexer = ("tmux", False)
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-003" in out
    assert "'tmux'" in out


def test_preflight_multiplexer_harness_error_reports_finding(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.fail_multiplexer = HarnessError("bmad_loop is not importable: boom")
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-003" in out
    assert "not importable" in out
    assert "multiplexer: backend='' available=False" in out


# --- adapter binary absent: MRS-PREFLIGHT-004 -------------------------------


def test_preflight_adapter_binary_absent_reports_finding(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.binaries_present.discard("claude")
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-004" in out
    assert "'claude'" in out
    assert "adapter: name='claude' binary_present=False" in out


def test_preflight_adapter_resolution_harness_error_reports_finding(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.fail_adapter = HarnessError("unknown CLI profile: 'claude'")
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-004" in out
    assert "adapter: name='claude' binary_present=False" in out


# --- unacknowledged adapter: MRS-PREFLIGHT-008 ------------------------------


def test_preflight_unacknowledged_adapter_reports_finding_naming_note_and_caveat(
    repo_root, tmp_path, capsys
):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    # no ack file seeded -- absent from it entirely

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-008" in out
    assert "workspace trust" in out  # the fake adapter's own first-run note
    assert "unattended" in out  # the sustained-automation caveat text
    assert "first_run_acknowledged: False" in out


# --- --acknowledge records first, then passes in the SAME invocation ------


def test_preflight_acknowledge_flag_records_and_passes_same_invocation(
    repo_root, tmp_path, capsys
):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()

    exit_code = run_preflight(
        _preflight_namespace(slug, acknowledge="claude"), vcs=vcs, fs=fs, harness=harness
    )
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-008" not in out
    assert "first_run_acknowledged: True" in out

    ack_path = tmp_path / "state-home" / "adapter-acknowledgements.json"
    assert json.loads(fs.texts[ack_path]) == ["claude"]


def test_preflight_acknowledge_is_idempotent_on_a_rerun(repo_root, tmp_path, capsys):
    """A prior acknowledgement persists into a later invocation with no
    --acknowledge flag at all -- the state file, not the flag, is what the
    first-run check reads."""
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()

    first_exit = run_preflight(
        _preflight_namespace(slug, acknowledge="claude"), vcs=vcs, fs=fs, harness=harness
    )
    assert first_exit == EXIT_OK
    capsys.readouterr()
    writes_after_first = list(fs.write_calls)

    second_exit = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert second_exit == EXIT_OK
    out = capsys.readouterr().out
    assert "first_run_acknowledged: True" in out
    # idempotent: the second run's ack is already satisfied, no new write
    assert fs.write_calls == writes_after_first


def test_preflight_acknowledging_a_different_adapter_does_not_satisfy_the_configured_one(
    repo_root, tmp_path, capsys
):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()

    exit_code = run_preflight(
        _preflight_namespace(slug, acknowledge="codex"), vcs=vcs, fs=fs, harness=harness
    )
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-008" in out
    assert "first_run_acknowledged: False" in out
    ack_path = tmp_path / "state-home" / "adapter-acknowledgements.json"
    assert json.loads(fs.texts[ack_path]) == ["codex"]  # recorded, but for a different adapter


# --- seed files: already present -> skipped, no write ----------------------


def test_preflight_seed_file_already_present_is_skipped(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.adapter_seed_files_map["claude"] = (".mcp.json",)
    fs.files.add(home / ".mcp.json")  # already present in the home
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "  .mcp.json: skipped" in out
    assert fs.copy_file_calls == []


# --- seed files: absent in home, present in main checkout -> copied --------


def test_preflight_seed_file_absent_is_copied_from_main_checkout(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.adapter_seed_files_map["claude"] = (".mcp.json",)
    fs.files.add(repo_root / ".mcp.json")  # present in the main checkout
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "  .mcp.json: copied" in out
    assert fs.copy_file_calls == [(repo_root / ".mcp.json", home / ".mcp.json")]


def test_preflight_seed_file_absent_in_both_home_and_main_is_skipped_not_failed(
    repo_root, tmp_path, capsys
):
    """Mirrors bmad_loop.install.provision_worktree's own copy-when-absent
    semantics: nothing to seed is not a failure -- an operator who never
    made a given optional config file must not fail preflight over it."""
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.adapter_seed_files_map["claude"] = (".mcp.json",)
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "  .mcp.json: skipped" in out
    assert fs.copy_file_calls == []


# --- seed file copy fails: MRS-PREFLIGHT-009, halts further attempts -------


def test_preflight_seed_file_copy_failure_reports_finding_and_halts(repo_root, tmp_path, capsys):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.adapter_seed_files_map["claude"] = (".mcp.json", ".claude/settings.json")
    fs.files.add(repo_root / ".mcp.json")
    fs.files.add(repo_root / ".claude" / "settings.json")
    fs.fail_copy_file = FsError("disk full")
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-009" in out
    assert str(home / ".mcp.json") in out
    assert "  .mcp.json: failed" in out
    # the SECOND seed file is never attempted -- reported failed too, one halt
    assert "  .claude/settings.json: failed" in out
    assert len(fs.copy_file_calls) == 1


# --- main checked out twice: MRS-PREFLIGHT-007 ------------------------------


def test_preflight_main_checked_out_twice_reports_finding_naming_both_paths(
    repo_root, tmp_path, capsys
):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    other = tmp_path / "elsewhere-main"
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    vcs.extra_worktree_entries = [WorktreeEntry(path=other, branch="main")]
    harness = _converged_harness()
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-007" in out
    assert str(repo_root) in out
    assert str(other) in out
    assert "main_checked_out_once: False" in out


def test_preflight_main_checked_out_twice_list_worktrees_failure_reports_finding(
    repo_root, tmp_path, capsys
):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    vcs.fail_list_worktrees = VcsCommandError("git worktree list failed")
    harness = _converged_harness()
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-007" in out
    assert "main_checked_out_once: False" in out


# --- story feed missing/unparseable: MRS-PREFLIGHT-005 ----------------------


def test_preflight_story_feed_error_reports_the_harnesss_own_error_text(
    repo_root, tmp_path, capsys
):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.feed_error = "sprint status file not found: /nowhere/sprint-status.yaml"
    _seed_acknowledged(fs, tmp_path, ["claude"])

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-005" in out
    assert "sprint status file not found" in out
    assert "story_feed: resolvable=False" in out


# --- verify command unresolvable: MRS-PREFLIGHT-006 -------------------------


def test_preflight_verify_command_unresolvable_reports_finding(
    repo_root, tmp_path, capsys, monkeypatch
):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    _seed_acknowledged(fs, tmp_path, ["claude"])

    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text(
        'verify_commands = ["definitely-not-a-real-binary-xyz --flag"]\n', encoding="utf-8"
    )
    monkeypatch.setattr(
        init_module, "conventional_project_policy_path", lambda slug: policy_path
    )

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-006" in out
    assert "definitely-not-a-real-binary-xyz --flag" in out


def test_preflight_verify_command_resolvable_reports_no_finding(
    repo_root, tmp_path, capsys, monkeypatch
):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    harness.binaries_present.add("pytest")
    _seed_acknowledged(fs, tmp_path, ["claude"])

    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('verify_commands = ["pytest -q"]\n', encoding="utf-8")
    monkeypatch.setattr(
        init_module, "conventional_project_policy_path", lambda slug: policy_path
    )

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-006" not in out
    assert "'pytest -q': resolvable=True" in out


# --- policy composition findings merge into preflight's own list -----------


def test_preflight_merges_policy_composition_findings(repo_root, tmp_path, capsys, monkeypatch):
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    _seed_acknowledged(fs, tmp_path, ["claude"])

    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('not_a_real_policy_key = "x"\n', encoding="utf-8")
    monkeypatch.setattr(
        init_module, "conventional_project_policy_path", lambda slug: policy_path
    )

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-POLICY-001" in out
    assert "not_a_real_policy_key" in out


def test_preflight_adapter_resolution_render_failure_reports_finding(
    repo_root, tmp_path, capsys, monkeypatch
):
    """``render_policy_toml`` raises ``ValueError`` when a seed attempt-count
    is 0 (Marshal permits it; bmad-loop 0.9.0's loader does not) -- folded
    into the adapter check's own code since resolving the adapter NAME is
    exactly what failed."""
    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    _seed_acknowledged(fs, tmp_path, ["claude"])

    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text("max_dev_attempts = 0\n", encoding="utf-8")
    monkeypatch.setattr(
        init_module, "conventional_project_policy_path", lambda slug: policy_path
    )

    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    assert exit_code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-004" in out
    assert "adapter: name=None" in out
    # no adapter resolved -- the first-run check has nothing to report on
    assert "MRS-PREFLIGHT-008" not in out


# --- timing: presence/resolvability checks only, well under NFR-14's 10s ---


def test_preflight_completes_well_under_ten_seconds(repo_root, tmp_path, capsys):
    import time

    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = FakeFs(project_dirs={home})
    vcs = FakeVcs(repo_root=repo_root)
    harness = _converged_harness()
    _seed_acknowledged(fs, tmp_path, ["claude"])

    started = time.perf_counter()
    exit_code = run_preflight(_preflight_namespace(slug), vcs=vcs, fs=fs, harness=harness)
    elapsed = time.perf_counter() - started
    assert exit_code == EXIT_OK
    assert elapsed < 10.0


# --- verdict classification of the nine new codes ---------------------------


def test_preflight_finding_codes_classify_as_documented():
    from pyforge.marshal.core.model import Verdict
    from pyforge.marshal.core.verdict import classify

    for code in (
        "MRS-PREFLIGHT-001",
        "MRS-PREFLIGHT-002",
        "MRS-PREFLIGHT-003",
        "MRS-PREFLIGHT-004",
        "MRS-PREFLIGHT-005",
        "MRS-PREFLIGHT-006",
        "MRS-PREFLIGHT-007",
        "MRS-PREFLIGHT-008",
        "MRS-PREFLIGHT-009",
    ):
        assert classify(code) == Verdict.ERROR
