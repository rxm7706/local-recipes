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
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli.init import run_init
from pyforge.marshal.core.verdict import EXIT_OK

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
        self.fail_read_text: Exception | None = None
        self.fail_write_text: Exception | None = None
        self.fail_read_symlink: Exception | None = None
        self.fail_repoint: Exception | None = None
        self.fail_ensure_dir: Exception | None = None
        self.fail_remove_empty_dir: Exception | None = None

    def is_dir(self, path: Path) -> bool:
        self.calls.append("is_dir")
        return path in self.dirs

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
