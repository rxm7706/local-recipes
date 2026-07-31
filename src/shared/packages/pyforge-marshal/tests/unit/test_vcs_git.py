"""Unit tests for ``pyforge.marshal.adapters.vcs_git`` (Story 1.4, AD-4/AD-11)
-- ``GitVcs`` against REAL temp git repos, matching this package's own
"real I/O against tmp_path, not heavy mocking" convention.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.ports.vcs import WorktreeEntry


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    return repo


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _init_repo(tmp_path)


@pytest.fixture
def vcs() -> GitVcs:
    return GitVcs()


# --- repo_common_root ---------------------------------------------------------


def test_repo_common_root_from_repo_dir(vcs, repo):
    assert vcs.repo_common_root(repo) == repo.resolve()


def test_repo_common_root_from_subdirectory(vcs, repo):
    subdir = repo / "subdir"
    subdir.mkdir()
    assert vcs.repo_common_root(subdir) == repo.resolve()


def test_repo_common_root_raises_outside_a_repo(vcs, tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    with pytest.raises(VcsCommandError):
        vcs.repo_common_root(outside)


def test_repo_common_root_from_linked_worktree_resolves_to_main_checkout(vcs, repo, tmp_path):
    """The whole point of --git-common-dir: a linked worktree's common dir
    still points at the MAIN checkout's .git, regardless of which worktree
    the query runs from."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    assert vcs.repo_common_root(home) == repo.resolve()


# --- branch_exists -------------------------------------------------------------


def test_branch_exists_true_for_main(vcs, repo):
    assert vcs.branch_exists(repo, "main") is True


def test_branch_exists_false_for_unknown_branch(vcs, repo):
    assert vcs.branch_exists(repo, "loop/nonexistent") is False


def test_branch_exists_true_after_plain_branch_create(vcs, repo):
    _git(repo, "branch", "loop/created", "main")
    assert vcs.branch_exists(repo, "loop/created") is True


def test_branch_exists_raises_on_a_real_git_failure(vcs, tmp_path):
    """Review finding: only `--verify --quiet`'s exit 1 means the ref is
    absent; any other failure (here: not a repository at all, exit 128 --
    same class as corrupt refs or a held lock) must raise, not silently
    read as branch-absent and send add_worktree down the mint-new path."""
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    with pytest.raises(VcsCommandError):
        vcs.branch_exists(outside, "loop/anything")


# --- worktree_path_for_branch ---------------------------------------------------


def test_worktree_path_for_branch_none_when_absent(vcs, repo):
    assert vcs.worktree_path_for_branch(repo, "loop/absent") is None


def test_worktree_path_for_branch_finds_added_worktree(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/found", base="main")
    found = vcs.worktree_path_for_branch(repo, "loop/found")
    assert found is not None
    assert found.resolve() == home.resolve()


def test_worktree_path_for_branch_ignores_other_branches(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/one", base="main")
    assert vcs.worktree_path_for_branch(repo, "loop/two") is None


def test_worktree_path_for_branch_raises_on_a_block_without_worktree_line(
    vcs, repo, monkeypatch
):
    """Review finding: a porcelain block carrying a `branch` line but no
    `worktree` line (a worktree path containing a blank line splits one
    block in two) raised a raw KeyError instead of the port's error."""
    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    def _mangled_porcelain(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="branch refs/heads/loop/acme\n\n",
            stderr="",
        )

    monkeypatch.setattr(vcs_git_module.subprocess, "run", _mangled_porcelain)
    with pytest.raises(VcsCommandError, match="no worktree line"):
        vcs.worktree_path_for_branch(repo, "loop/acme")


# --- list_worktrees (Story 1.6) --------------------------------------------------


def test_list_worktrees_returns_only_the_main_checkout_when_no_others_exist(vcs, repo):
    entries = vcs.list_worktrees(repo)
    assert len(entries) == 1
    assert entries[0].path.resolve() == repo.resolve()
    assert entries[0].branch == "main"


def test_list_worktrees_includes_every_linked_worktree(vcs, repo, tmp_path):
    home_one = tmp_path / "home-one"
    home_two = tmp_path / "home-two"
    vcs.add_worktree(repo, home_one, "loop/acme", base="main")
    vcs.add_worktree(repo, home_two, "loop/beta", base="main")
    entries = vcs.list_worktrees(repo)
    by_branch = {entry.branch: entry.path.resolve() for entry in entries}
    assert by_branch == {
        "main": repo.resolve(),
        "loop/acme": home_one.resolve(),
        "loop/beta": home_two.resolve(),
    }


def test_list_worktrees_main_checkout_is_listed_first(vcs, repo, tmp_path):
    """Real git's own documented behavior -- not depended on by
    cli/init.py::run_homes (which identifies the main checkout by realpath,
    not list position), but worth pinning as a regression guard."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/acme", base="main")
    entries = vcs.list_worktrees(repo)
    assert entries[0].path.resolve() == repo.resolve()


def test_list_worktrees_reports_none_branch_for_a_detached_head(vcs, repo, tmp_path):
    home = tmp_path / "detached"
    head_commit = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "worktree", "add", "--detach", str(home), head_commit)
    entries = vcs.list_worktrees(repo)
    detached = [entry for entry in entries if entry.path.resolve() == home.resolve()]
    assert len(detached) == 1
    assert detached[0].branch is None


def test_list_worktrees_returns_worktree_entry_instances(vcs, repo):
    entries = vcs.list_worktrees(repo)
    assert entries and all(isinstance(entry, WorktreeEntry) for entry in entries)


def test_list_worktrees_raises_outside_a_repo(vcs, tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    with pytest.raises(VcsCommandError):
        vcs.list_worktrees(outside)


def test_list_worktrees_raises_on_a_block_without_worktree_line(vcs, repo, monkeypatch):
    """Same defect class as worktree_path_for_branch's identical test --
    both methods share _iter_worktree_blocks."""
    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    def _mangled_porcelain(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="branch refs/heads/loop/acme\n\n",
            stderr="",
        )

    monkeypatch.setattr(vcs_git_module.subprocess, "run", _mangled_porcelain)
    with pytest.raises(VcsCommandError, match="no worktree line"):
        vcs.list_worktrees(repo)


# --- add_worktree ----------------------------------------------------------------


def test_add_worktree_creates_new_branch_from_base(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/fresh", base="main")
    assert home.is_dir()
    assert vcs.branch_exists(repo, "loop/fresh") is True
    # the new worktree is ON the new branch, not on base
    result = _git(home, "rev-parse", "--abbrev-ref", "HEAD")
    assert result.stdout.strip() == "loop/fresh"


def test_add_worktree_never_checks_out_base_a_second_time(vcs, repo, tmp_path):
    """Boundaries & Constraints: main is never checked out into the new
    worktree -- proven by main's own worktree (the repo dir) staying
    exclusively on main, unaffected by provisioning a second branch."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/fresh", base="main")
    result = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    assert result.stdout.strip() == "main"


def test_add_worktree_attaches_to_an_existing_branch_without_dash_b(vcs, repo, tmp_path):
    _git(repo, "branch", "loop/attach", "main")
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/attach", base="main")
    assert home.is_dir()
    result = _git(home, "rev-parse", "--abbrev-ref", "HEAD")
    assert result.stdout.strip() == "loop/attach"


def test_add_worktree_raises_vcs_command_error_on_locked_target(vcs, repo, tmp_path):
    """A worktree add that fails (here: the target path already exists as a
    non-empty non-worktree directory) raises VcsCommandError, never a raw
    subprocess exception."""
    home = tmp_path / "home"
    home.mkdir()
    (home / "occupied.txt").write_text("in the way\n", encoding="utf-8")
    with pytest.raises(VcsCommandError):
        vcs.add_worktree(repo, home, "loop/blocked", base="main")


def test_add_worktree_raises_on_branch_checked_out_twice(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/dup", base="main")
    other_home = tmp_path / "other-home"
    with pytest.raises(VcsCommandError):
        vcs.add_worktree(repo, other_home, "loop/dup", base="main")


def test_add_worktree_attaches_the_branch_even_when_a_same_named_tag_exists(
    vcs, repo, tmp_path
):
    """A `loop/<slug>` tag colliding with the branch of the same name must
    not make `add_worktree` attach in detached HEAD instead of the branch
    (empirically: `git worktree add <path> <bare-name>` recognizes the
    branch and checks it out non-detached even with a colliding tag -- see
    `add_worktree`'s own docstring for the live-verified git behavior this
    asserts)."""
    _git(repo, "branch", "loop/tagged", "main")
    _git(repo, "tag", "loop/tagged")  # a same-named tag on the same commit
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/tagged", base="main")
    # symbolic-ref, not --abbrev-ref: with the collision present git's
    # abbreviation algorithm prints the disambiguated "heads/loop/tagged"
    # rather than the short form, but HEAD is still ATTACHED (not detached)
    # to the real branch -- symbolic-ref only succeeds when HEAD is attached.
    result = _git(home, "symbolic-ref", "-q", "HEAD")
    assert result.stdout.strip() == "refs/heads/loop/tagged"


def test_add_worktree_creates_a_new_branch_when_only_a_same_named_tag_exists(
    vcs, repo, tmp_path
):
    """Review finding, the actual bug: with only a TAG present (no branch),
    a bare `rev-parse --verify <branch>` (pre-fix `branch_exists`) resolves
    the tag and reports `True`, so `add_worktree` would take the "attach to
    an existing branch" path against a ref that is not a branch at all --
    checking out that tag detached and never creating `loop/<slug>` as an
    actual branch. `branch_exists` now checks `refs/heads/<branch>`
    specifically, so this must go through the `-b` (mint-new-branch) path."""
    _git(repo, "tag", "loop/tagonly", "main")  # a tag, deliberately no branch
    assert vcs.branch_exists(repo, "loop/tagonly") is False
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/tagonly", base="main")
    # symbolic-ref: HEAD must be ATTACHED to the new branch, not detached
    # onto the tag's commit (symbolic-ref only succeeds when attached).
    result = _git(home, "symbolic-ref", "-q", "HEAD")
    assert result.stdout.strip() == "refs/heads/loop/tagonly"
    assert vcs.branch_exists(repo, "loop/tagonly") is True  # -b actually created it


# --- _run failure translation (review findings: git-not-found, timeout) --------


def test_run_wraps_missing_git_executable(vcs, repo, monkeypatch):
    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    def _raise_not_found(*args, **kwargs):
        raise FileNotFoundError("no such file: git")

    monkeypatch.setattr(vcs_git_module.subprocess, "run", _raise_not_found)
    with pytest.raises(VcsCommandError, match="git executable not found"):
        vcs.repo_common_root(repo)


def test_run_wraps_a_hung_git_process(vcs, repo, monkeypatch):
    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["git"], timeout=30.0)

    monkeypatch.setattr(vcs_git_module.subprocess, "run", _raise_timeout)
    with pytest.raises(VcsCommandError, match="timed out"):
        vcs.repo_common_root(repo)


def test_run_wraps_a_git_launch_permission_error(vcs, repo, monkeypatch):
    """Review finding: `_run` wrapped only FileNotFoundError and
    TimeoutExpired -- a PermissionError (EACCES on a non-executable shim)
    or ENOEXEC OSError from launching git escaped raw, past run_init's
    typed handlers and out of the CLI as a traceback."""
    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    def _raise_eacces(*args, **kwargs):
        raise PermissionError("exec format error: git")

    monkeypatch.setattr(vcs_git_module.subprocess, "run", _raise_eacces)
    with pytest.raises(VcsCommandError, match="cannot launch git"):
        vcs.repo_common_root(repo)


def test_run_replaces_undecodable_git_output(monkeypatch):
    """Review finding: git output undecodable in the process locale (a
    foreign-bytes path or stderr) previously escaped `_run`'s two except
    clauses as a raw UnicodeDecodeError; errors='replace' degrades it to
    replacement characters instead."""
    import sys

    from pyforge.marshal.adapters.vcs_git import _run

    result = _run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xff')"]
    )
    assert result.returncode == 0
    assert result.stdout == "�"


def test_add_worktree_timeout_names_the_cleanup_commands(vcs, repo, tmp_path, monkeypatch):
    """Review finding: the flat 30s timeout could SIGKILL `git worktree
    add` mid-checkout on a large repo. The add now runs under its own
    (much longer) tier, and a timeout there carries operator cleanup
    guidance -- partial state itself is left as-is per the spec's own
    edge-case matrix (never auto-cleaned)."""
    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    real_run = subprocess.run

    def _timeout_only_worktree_add(args, **kwargs):
        if "worktree" in args:
            raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout"))
        return real_run(args, **kwargs)

    monkeypatch.setattr(vcs_git_module.subprocess, "run", _timeout_only_worktree_add)
    home = tmp_path / "home"
    with pytest.raises(VcsCommandError, match="worktree remove --force"):
        vcs.add_worktree(repo, home, "loop/hung", base="main")
