"""Unit tests for ``pyforge.marshal.adapters.vcs_git`` (Story 1.4, AD-4/AD-11)
-- ``GitVcs`` against REAL temp git repos, matching this package's own
"real I/O against tmp_path, not heavy mocking" convention.
"""

from __future__ import annotations

import errno
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.adapters import vcs_git as vcs_git_module
from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.core.egress import to_redacted_text
from pyforge.marshal.core.refs import ORIGIN_MAIN
from pyforge.marshal.ports.commit import VcsRef
from pyforge.marshal.ports.vcs import WorktreeEntry


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
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


def _worktree_paths(repo: Path) -> list[str]:
    """Every path ``git worktree list --porcelain`` currently registers for
    ``repo`` -- used to prove ``merge_branch``'s own temp detached worktree
    never leaks (code review, 2026-08-06, P1)."""
    result = _git(repo, "worktree", "list", "--porcelain")
    return [line.removeprefix("worktree ") for line in result.stdout.splitlines() if line.startswith("worktree ")]


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


def test_worktree_path_for_branch_raises_on_a_block_without_worktree_line(vcs, repo, monkeypatch):
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


def test_add_worktree_attaches_the_branch_even_when_a_same_named_tag_exists(vcs, repo, tmp_path):
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


def test_add_worktree_from_a_remote_tracking_base_sets_no_upstream(vcs, cloned_repo, tmp_path):
    """Regression (2026-08-30/31): minting a new branch from a
    remote-tracking ``base`` (every dispatch/loop-home caller passes
    ``origin/main``) must NOT auto-configure that branch's upstream to
    ``base`` -- git's own ``branch.autoSetupMerge`` default silently did
    exactly that, and `push()`'s already-has-upstream path then pushed
    ``<branch>:main`` instead of ``<branch>:<branch>``, rejected by the
    remote as non-fast-forward. Three concurrent dispatches all hit this
    identically before `add_worktree` started passing `--no-track`."""
    home = tmp_path / "home"
    vcs.add_worktree(cloned_repo, home, "dispatch/acme/1.1", base="origin/main")
    result = subprocess.run(
        ["git", "-C", str(cloned_repo), "rev-parse", "--abbrev-ref", "dispatch/acme/1.1@{upstream}"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, f"expected no upstream configured, got {result.stdout.strip()!r}"


def test_add_worktree_creates_a_new_branch_when_only_a_same_named_tag_exists(vcs, repo, tmp_path):
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

    result = _run([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xff')"])
    assert result.returncode == 0
    assert result.stdout == "�"


# --- has_uncommitted_changes (Story 1.8) ----------------------------------------


def test_has_uncommitted_changes_false_for_a_clean_worktree(vcs, repo):
    assert vcs.has_uncommitted_changes(repo) is False


def test_has_uncommitted_changes_true_for_an_untracked_file(vcs, repo):
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    assert vcs.has_uncommitted_changes(repo) is True


def test_has_uncommitted_changes_true_for_a_staged_change(vcs, repo):
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    assert vcs.has_uncommitted_changes(repo) is True


def test_has_uncommitted_changes_true_for_an_unstaged_modification(vcs, repo):
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    assert vcs.has_uncommitted_changes(repo) is True


def test_has_uncommitted_changes_false_in_a_clean_linked_worktree(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/clean", base="main")
    assert vcs.has_uncommitted_changes(home) is False


def test_has_uncommitted_changes_raises_outside_a_repo(vcs, tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    with pytest.raises(VcsCommandError):
        vcs.has_uncommitted_changes(outside)


def test_has_uncommitted_changes_true_for_untracked_file_despite_local_config_hiding_it(vcs, repo):
    """Review finding: an operator's LOCAL ``status.showUntrackedFiles=no``
    would otherwise hide an untracked file from plain ``git status
    --porcelain``, silently defeating the refusal this method exists to
    drive. The explicit ``-c status.showUntrackedFiles=normal`` pin must
    override it."""
    _git(repo, "config", "status.showUntrackedFiles", "no")
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    assert vcs.has_uncommitted_changes(repo) is True


# --- is_branch_merged (Story 1.8) -------------------------------------------------


def test_is_branch_merged_true_for_a_branch_with_no_new_commits(vcs, repo):
    _git(repo, "branch", "loop/noop", "main")
    assert vcs.is_branch_merged(repo, "loop/noop", into="main") is True


def test_is_branch_merged_true_for_a_fast_forward_merged_branch(vcs, repo):
    """Cheap ancestry path: main fast-forwards onto the branch tip."""
    _git(repo, "checkout", "-b", "loop/ff")
    (repo / "ff.txt").write_text("ff\n", encoding="utf-8")
    _git(repo, "add", "ff.txt")
    _git(repo, "commit", "-m", "ff commit")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--ff-only", "loop/ff")
    assert vcs.is_branch_merged(repo, "loop/ff", into="main") is True


def test_is_branch_merged_true_for_a_real_merge_commit(vcs, repo):
    """Cheap ancestry path: a real (multi-parent) merge commit."""
    _git(repo, "checkout", "-b", "loop/realmerge")
    (repo / "rm.txt").write_text("rm\n", encoding="utf-8")
    _git(repo, "add", "rm.txt")
    _git(repo, "commit", "-m", "real merge source commit")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "-m", "real merge", "loop/realmerge")
    assert vcs.is_branch_merged(repo, "loop/realmerge", into="main") is True


def test_is_branch_merged_false_for_a_genuinely_unmerged_branch(vcs, repo):
    _git(repo, "checkout", "-b", "loop/unmerged")
    (repo / "never.txt").write_text("never merged\n", encoding="utf-8")
    _git(repo, "add", "never.txt")
    _git(repo, "commit", "-m", "never merged content")
    _git(repo, "checkout", "main")
    assert vcs.is_branch_merged(repo, "loop/unmerged", into="main") is False


def test_is_branch_merged_true_for_a_net_zero_branch(vcs, repo):
    """Follow-up review finding: a branch whose commits cancel out (a
    change plus its revert -- tree IDENTICAL to the merge base's) carries
    nothing ``main`` lacks, but the virtual-commit fallback cannot prove
    it: the virtual commit's diff is empty, and ``git cherry`` reports an
    empty-diff commit as ``+`` (no equivalent patch on ``into``;
    live-verified), which spuriously refused a branch with nothing to
    lose. The tree-equality shortcut answers first."""
    _git(repo, "checkout", "-b", "loop/netzero")
    (repo / "temp.txt").write_text("temporary\n", encoding="utf-8")
    _git(repo, "add", "temp.txt")
    _git(repo, "commit", "-m", "add temp")
    _git(repo, "rm", "-q", "temp.txt")
    _git(repo, "commit", "-m", "revert temp")
    _git(repo, "checkout", "main")

    # Confirms bare ancestry really would misreport this as unmerged (the
    # branch's two commits are not on main), so only the fallback answers.
    ancestry = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", "loop/netzero", "main"],
        capture_output=True,
    )
    assert ancestry.returncode != 0
    # Confirms the trees really are identical -- the exact shape the
    # shortcut exists for.
    branch_tree = _git(repo, "rev-parse", "loop/netzero^{tree}").stdout.strip()
    main_tree = _git(repo, "rev-parse", "main^{tree}").stdout.strip()
    assert branch_tree == main_tree

    assert vcs.is_branch_merged(repo, "loop/netzero", into="main") is True


def test_is_branch_merged_true_for_a_squash_merged_branch(vcs, repo):
    """The story's own central scenario: this repo's own bmad-loop landing
    convention produces a single-parent "squash" commit on `main` whose tip
    is never an ancestor of the branch it replaced -- live-verified during
    planning (`git cat-file -p 7f0bb6b23f` -- exactly one parent line
    despite the message reading "Merge X into Y"). Ancestry alone
    (`git merge-base --is-ancestor`) reports this branch as UNMERGED;
    `is_branch_merged` must not."""
    _git(repo, "checkout", "-b", "loop/squash")
    (repo / "squash.txt").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "squash.txt")
    _git(repo, "commit", "-m", "squash: one")
    (repo / "squash.txt").write_text("one\ntwo\n", encoding="utf-8")
    _git(repo, "add", "squash.txt")
    _git(repo, "commit", "-m", "squash: two")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--squash", "loop/squash")
    _git(repo, "commit", "-m", "Merge loop/squash into main")

    # Confirms the parent count really is 1 -- the exact live-verified shape
    # this method exists to handle.
    show = _git(repo, "cat-file", "-p", "HEAD")
    assert show.stdout.count("\nparent ") + (1 if show.stdout.startswith("parent ") else 0) == 1
    # Confirms bare ancestry really would misreport this as unmerged.
    ancestry = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", "loop/squash", "main"],
        capture_output=True,
    )
    assert ancestry.returncode != 0

    assert vcs.is_branch_merged(repo, "loop/squash", into="main") is True


def test_is_branch_merged_true_for_a_squash_merge_even_after_main_advances_further(vcs, repo):
    """Confirms the live-verified claim from the story's Design Notes: the
    squash-merge recognition survives `main` advancing with further,
    unrelated commits after the squash landed."""
    _git(repo, "checkout", "-b", "loop/squash2")
    (repo / "squash2.txt").write_text("content\n", encoding="utf-8")
    _git(repo, "add", "squash2.txt")
    _git(repo, "commit", "-m", "squash2 content")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--squash", "loop/squash2")
    _git(repo, "commit", "-m", "Merge loop/squash2 into main")
    (repo / "unrelated.txt").write_text("later\n", encoding="utf-8")
    _git(repo, "add", "unrelated.txt")
    _git(repo, "commit", "-m", "unrelated later commit")

    assert vcs.is_branch_merged(repo, "loop/squash2", into="main") is True


def test_is_branch_merged_commit_tree_call_never_depends_on_global_git_identity(vcs, tmp_path, monkeypatch):
    """Boundaries & Constraints: the internal commit-tree call must pin its
    own author/committer identity and disable GPG signing so it never
    depends on the operator's global git config -- proven against a repo/
    environment carrying NO identity anywhere ELSE git would look (no local
    repo config, an isolated HOME/XDG_CONFIG_HOME, GIT_CONFIG_GLOBAL/SYSTEM
    pointed at nonexistent files, no GIT_AUTHOR_*/GIT_COMMITTER_* env vars)."""
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / "config"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(fake_home / "no-such-gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(fake_home / "no-such-system-gitconfig"))
    for var in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "EMAIL",
    ):
        monkeypatch.delenv(var, raising=False)

    no_identity_repo = tmp_path / "no-identity-repo"
    no_identity_repo.mkdir()

    def _run_git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(no_identity_repo), *args],
            capture_output=True,
            text=True,
        )

    def _setup_commit(*args: str) -> None:
        # -c identity for THIS invocation only -- never persisted to local
        # or global config -- so the fixture's own history is constructible
        # without the environment carrying any ambient identity either.
        result = subprocess.run(
            [
                "git",
                "-C",
                str(no_identity_repo),
                "-c",
                "user.name=setup",
                "-c",
                "user.email=setup@example.com",
                *args,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    assert _run_git("init", "-b", "main").returncode == 0
    (no_identity_repo / "README.md").write_text("hi\n", encoding="utf-8")
    assert _run_git("add", "README.md").returncode == 0
    _setup_commit("commit", "-m", "initial")
    _setup_commit("checkout", "-b", "loop/noidentity")
    (no_identity_repo / "x.txt").write_text("x\n", encoding="utf-8")
    assert _run_git("add", "x.txt").returncode == 0
    _setup_commit("commit", "-m", "unmerged content")
    _setup_commit("checkout", "main")

    # Sanity: an ORDINARY commit in this environment genuinely fails without
    # an explicit -c identity -- proves the isolation above is real, not
    # accidentally leaking some other identity source.
    (no_identity_repo / "y.txt").write_text("y\n", encoding="utf-8")
    assert _run_git("add", "y.txt").returncode == 0
    naked = _run_git("commit", "-m", "no identity")
    assert naked.returncode != 0

    # is_branch_merged's own internal commit-tree call must succeed even
    # here -- if it relied on ambient identity it would raise
    # VcsCommandError instead of returning a bool.
    assert vcs.is_branch_merged(no_identity_repo, "loop/noidentity", into="main") is False


def test_is_branch_merged_raises_on_unknown_branch(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.is_branch_merged(repo, "loop/does-not-exist", into="main")


def test_is_branch_merged_raises_on_empty_cherry_output(vcs, repo, monkeypatch):
    """Review finding: `all()` over an empty sequence is vacuously True --
    a safety gate defaulting to "merged" on unproven zero-line `git cherry`
    output would default to permissive. Every live trial during planning
    produced exactly one line for the one virtual commit; this proves the
    defensive branch fails loud instead of silently reporting "safe to
    delete" on a shape nobody has observed."""
    import subprocess as _subprocess

    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    _git(repo, "checkout", "-q", "-b", "loop/emptycherry", "main")
    (repo / "unmerged.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "unmerged.txt")
    _git(repo, "commit", "-qm", "unmerged commit")
    _git(repo, "checkout", "-q", "main")

    real_run = vcs_git_module._run

    def _fake_run(args, *, timeout_s=vcs_git_module._GIT_TIMEOUT_S):
        if "cherry" in args:
            return _subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")
        return real_run(args, timeout_s=timeout_s)

    monkeypatch.setattr(vcs_git_module, "_run", _fake_run)
    with pytest.raises(VcsCommandError, match="no output"):
        vcs.is_branch_merged(repo, "loop/emptycherry", into="main")


def _repo_with_origin(tmp_path: Path, repo: Path) -> Path:
    """Give ``repo`` a bare ``origin`` carrying ``main``; returns the bare repository."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], capture_output=True, text=True, check=True)
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "origin", "main")
    return origin


def test_is_branch_merged_into_ref_reads_the_remote_tracking_main_a_lagging_local_main_lacks(vcs, repo, tmp_path):
    """Story 72.1 (CAP-280): the branch is merged into `origin/main` and not into local `main` (the
    primary checkout was never fast-forwarded). The full-ref target reads the remote-tracking ref; the
    branch-name form still reads `refs/heads/main` and says unmerged."""
    _repo_with_origin(tmp_path, repo)
    _git(repo, "checkout", "-b", "loop/remote-only")
    (repo / "remote-only.txt").write_text("merged elsewhere\n", encoding="utf-8")
    _git(repo, "add", "remote-only.txt")
    _git(repo, "commit", "-m", "remote-only content")
    _git(repo, "checkout", "main")
    # The story merges on the remote by another route; local `main` stays where it was.
    _git(repo, "push", "origin", "loop/remote-only:main")
    _git(repo, "fetch", "origin", "main")

    assert vcs.is_branch_merged(repo, "loop/remote-only", into="main", into_ref=ORIGIN_MAIN) is True
    assert vcs.is_branch_merged(repo, "loop/remote-only", into="main") is False


def test_is_branch_merged_into_ref_reads_a_squash_merge_on_the_remote_tracking_main(vcs, repo, tmp_path):
    """The patch-id fallback honours `into_ref` too: a branch squash-merged on `origin/main` (a single-
    parent commit, never an ancestor) reads merged through it and unmerged through local `main`."""
    origin = _repo_with_origin(tmp_path, repo)
    _git(repo, "checkout", "-b", "loop/squash-remote")
    (repo / "squash-remote.txt").write_text("squashed elsewhere\n", encoding="utf-8")
    _git(repo, "add", "squash-remote.txt")
    _git(repo, "commit", "-m", "squash-remote content")
    _git(repo, "push", "origin", "loop/squash-remote")
    _git(repo, "checkout", "main")

    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(origin), str(other)], capture_output=True, text=True, check=True)
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "Test")
    _git(other, "merge", "--squash", "origin/loop/squash-remote")
    _git(other, "commit", "-m", "Merge loop/squash-remote into main")
    _git(other, "push", "origin", "main")
    _git(repo, "fetch", "origin", "main")

    assert vcs.is_branch_merged(repo, "loop/squash-remote", into="main", into_ref=ORIGIN_MAIN) is True
    assert vcs.is_branch_merged(repo, "loop/squash-remote", into="main") is False


def test_is_branch_merged_into_ref_raises_on_an_unresolvable_ref(vcs, repo):
    _git(repo, "branch", "loop/noref", "main")
    with pytest.raises(VcsCommandError):
        vcs.is_branch_merged(repo, "loop/noref", into="main", into_ref="refs/remotes/origin/main")


# --- remove_worktree (Story 1.8) --------------------------------------------------


def test_remove_worktree_removes_a_clean_worktree(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/removable", base="main")
    vcs.remove_worktree(repo, home)
    assert not home.exists()
    assert vcs.worktree_path_for_branch(repo, "loop/removable") is None


def test_remove_worktree_refuses_a_dirty_worktree_without_force(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/dirty", base="main")
    (home / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(VcsCommandError):
        vcs.remove_worktree(repo, home)
    assert home.exists()


def test_remove_worktree_force_removes_a_dirty_worktree(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/dirty2", base="main")
    (home / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    vcs.remove_worktree(repo, home, force=True)
    assert not home.exists()


def test_remove_worktree_raises_on_a_nonexistent_worktree(vcs, repo, tmp_path):
    with pytest.raises(VcsCommandError):
        vcs.remove_worktree(repo, tmp_path / "never-existed")


# --- delete_branch (Story 1.8) ----------------------------------------------------


def test_delete_branch_removes_a_merged_branch_without_force(vcs, repo):
    _git(repo, "branch", "loop/mergeddelete", "main")
    vcs.delete_branch(repo, "loop/mergeddelete")
    assert vcs.branch_exists(repo, "loop/mergeddelete") is False


def test_delete_branch_plain_refuses_an_unmerged_branch(vcs, repo):
    _git(repo, "checkout", "-b", "loop/unmergeddelete")
    (repo / "u.txt").write_text("u\n", encoding="utf-8")
    _git(repo, "add", "u.txt")
    _git(repo, "commit", "-m", "unmerged content")
    _git(repo, "checkout", "main")
    with pytest.raises(VcsCommandError):
        vcs.delete_branch(repo, "loop/unmergeddelete")
    assert vcs.branch_exists(repo, "loop/unmergeddelete") is True


def test_delete_branch_force_removes_an_unmerged_branch(vcs, repo):
    _git(repo, "checkout", "-b", "loop/forcedelete")
    (repo / "u2.txt").write_text("u2\n", encoding="utf-8")
    _git(repo, "add", "u2.txt")
    _git(repo, "commit", "-m", "unmerged content 2")
    _git(repo, "checkout", "main")
    vcs.delete_branch(repo, "loop/forcedelete", force=True)
    assert vcs.branch_exists(repo, "loop/forcedelete") is False


def test_delete_branch_force_removes_a_squash_merged_branch_plain_d_would_refuse(vcs, repo):
    """The exact rationale this story's Design Notes give for always using
    -D once Marshal's own merged-check authorizes removal: plain `-d`'s
    ancestry-only heuristic refuses a squash-merged branch even though it is
    genuinely safe."""
    _git(repo, "checkout", "-b", "loop/squashdelete")
    (repo / "sd.txt").write_text("sd\n", encoding="utf-8")
    _git(repo, "add", "sd.txt")
    _git(repo, "commit", "-m", "squash delete content")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--squash", "loop/squashdelete")
    _git(repo, "commit", "-m", "Merge loop/squashdelete into main")

    with pytest.raises(VcsCommandError):
        vcs.delete_branch(repo, "loop/squashdelete")  # plain -d refuses
    assert vcs.branch_exists(repo, "loop/squashdelete") is True

    vcs.delete_branch(repo, "loop/squashdelete", force=True)  # -D succeeds
    assert vcs.branch_exists(repo, "loop/squashdelete") is False


def test_delete_branch_raises_on_unknown_branch(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.delete_branch(repo, "loop/never-existed", force=True)


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


# --- push (Story 3.8, AD-46) ----------------------------------------------------


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    """A bare repo -- ``git push`` needs a real remote target, unlike every
    other ``VcsPort`` method this file exercises against a single local
    repo."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _git(bare, "init", "--bare", "-b", "main")
    return bare


@pytest.fixture
def cloned_repo(remote: Path, tmp_path: Path) -> Path:
    """``repo`` (the module-level fixture) is a fresh ``git init`` with no
    remote at all -- push tests need one already configured with an
    ``origin`` pointing at ``remote``, cloned rather than hand-assembled so
    ``main``'s own upstream is set up exactly the way a real clone does
    it."""
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(remote), str(clone)], capture_output=True, text=True, check=True)
    _git(clone, "config", "user.email", "test@example.com")
    _git(clone, "config", "user.name", "Test")
    (clone / "README.md").write_text("hello\n", encoding="utf-8")
    _git(clone, "add", "README.md")
    _git(clone, "commit", "-m", "initial")
    _git(clone, "push", "origin", "main")
    return clone


def test_push_first_push_of_a_brand_new_branch_uses_origin_branch(vcs, cloned_repo, remote):
    """No upstream configured yet (the ordinary shape for a fresh
    station/per-story branch) -- falls back to `git push origin <branch>`,
    the branch's first push."""
    _git(cloned_repo, "checkout", "-b", "loop/newbranch")
    (cloned_repo / "n.txt").write_text("n\n", encoding="utf-8")
    _git(cloned_repo, "add", "n.txt")
    _git(cloned_repo, "commit", "-m", "new branch content")

    vcs.push(cloned_repo, "loop/newbranch")

    remote_branches = _git(remote, "branch", "--list", "loop/newbranch")
    assert "loop/newbranch" in remote_branches.stdout


def test_push_with_configured_upstream_pushes_new_commits(vcs, cloned_repo, remote):
    """An upstream already exists (`main`, set by the clone/first push
    above) -- a further commit is pushed via the resolved
    `<remote> <branch>:<remote_branch>` refspec."""
    (cloned_repo / "second.txt").write_text("second\n", encoding="utf-8")
    _git(cloned_repo, "add", "second.txt")
    _git(cloned_repo, "commit", "-m", "second commit")
    local_head = _git(cloned_repo, "rev-parse", "HEAD").stdout.strip()

    vcs.push(cloned_repo, "main")

    remote_head = _git(remote, "rev-parse", "main").stdout.strip()
    assert remote_head == local_head


def _record_hook_env(repo: Path) -> Path:
    """A real `pre-push` hook that appends what opt-out variables it received."""
    seen = repo / "hook-env.txt"
    hook = repo / ".git" / "hooks" / "pre-push"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s|%s\\n" "${{PYFORGE_PREFLIGHT_SKIP:-unset}}" "${{PYFORGE_PREFLIGHT_SKIP_REASON:-unset}}" >> {seen}\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    return seen


def test_push_with_a_proven_main_sha_reaches_the_hook_as_the_journaled_opt_out(vcs, cloned_repo, remote):
    """Story 57.1 (CAP-267): a sha on refs/remotes/origin/main -- the proof refresh holds after
    its fast-forward -- is pushed with PYFORGE_PREFLIGHT_SKIP=1 and a reason naming the branch
    and sha; a push without a proof sets neither variable."""
    seen = _record_hook_env(cloned_repo)
    tip = _git(cloned_repo, "rev-parse", "refs/remotes/origin/main").stdout.strip()
    _git(cloned_repo, "branch", "loop/acme", tip)
    vcs.push(cloned_repo, "loop/acme", proven_on_main_sha=tip)
    _git(cloned_repo, "branch", "loop/beta", tip)
    vcs.push(cloned_repo, "loop/beta")

    lines = seen.read_text(encoding="utf-8").splitlines()
    assert lines[0] == (
        f"1|marshal refresh: loop/acme at {tip[:12]} is a fast-forward to origin/main; "
        "every pushed commit is already on origin/main"
    )
    assert lines[1] == "unset|unset"
    assert _git(remote, "rev-parse", "loop/acme").stdout.strip() == tip


def test_push_refuses_the_opt_out_for_a_sha_not_on_origin_main(vcs, cloned_repo, remote):
    """Review 2 (L-B): the proof is re-checked against the FULL refname -- a local branch named
    `origin/main` carrying an unverified commit must not stand in for the remote-tracking ref."""
    _git(cloned_repo, "checkout", "-q", "-b", "loop/acme")
    (cloned_repo / "unverified.txt").write_text("x\n", encoding="utf-8")
    _git(cloned_repo, "add", "unverified.txt")
    _git(cloned_repo, "commit", "-m", "unverified")
    unverified = _git(cloned_repo, "rev-parse", "HEAD").stdout.strip()
    _git(cloned_repo, "branch", "origin/main", unverified)  # the trap: a LOCAL branch of that name

    with pytest.raises(VcsCommandError, match="is not on refs/remotes/origin/main"):
        vcs.push(cloned_repo, "loop/acme", proven_on_main_sha=unverified)
    assert "loop/acme" not in _git(remote, "branch", "--list", "loop/acme").stdout


def test_push_sends_exactly_the_proven_commit_even_if_the_branch_moved(vcs, cloned_repo, remote):
    """Review 2 (L-C): the pushed commit is the proven one, not whatever the branch points at by
    push time -- a commit made after the fast-forward never leaves with the opt-out."""
    seen = _record_hook_env(cloned_repo)
    tip = _git(cloned_repo, "rev-parse", "refs/remotes/origin/main").stdout.strip()
    _git(cloned_repo, "checkout", "-q", "-b", "loop/acme", tip)
    (cloned_repo / "later.txt").write_text("x\n", encoding="utf-8")
    _git(cloned_repo, "add", "later.txt")
    _git(cloned_repo, "commit", "-m", "made after the fast-forward")

    vcs.push(cloned_repo, "loop/acme", proven_on_main_sha=tip)

    assert _git(remote, "rev-parse", "loop/acme").stdout.strip() == tip
    assert seen.read_text(encoding="utf-8").startswith("1|")


def test_push_never_passes_force(vcs, cloned_repo, remote, monkeypatch):
    """Structural proof the port's own contract holds: no invocation this
    method makes ever carries `--force`/`--force-with-lease`, on either the
    upstream-configured or the first-push branch."""
    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    real_run = subprocess.run
    seen_argv: list[list[str]] = []

    def _capture(args, **kwargs):
        seen_argv.append(list(args))
        return real_run(args, **kwargs)

    monkeypatch.setattr(vcs_git_module.subprocess, "run", _capture)

    vcs.push(cloned_repo, "main")
    _git(cloned_repo, "checkout", "-b", "loop/noforce")
    (cloned_repo / "nf.txt").write_text("nf\n", encoding="utf-8")
    _git(cloned_repo, "add", "nf.txt")
    _git(cloned_repo, "commit", "-m", "no-force branch content")
    vcs.push(cloned_repo, "loop/noforce")

    push_invocations = [args for args in seen_argv if "push" in args]
    assert push_invocations, "expected at least one git push invocation to be captured"
    for args in push_invocations:
        assert "--force" not in args
        assert "--force-with-lease" not in args
        assert "-u" not in args
        assert "--set-upstream" not in args


def test_push_does_not_depend_on_repo_root_having_the_branch_checked_out(vcs, cloned_repo, remote):
    """`repo_root` need not have `branch` checked out as HEAD -- refs are
    shared across the repo, and this method names `branch` EXPLICITLY as
    the source refspec rather than relying on a bare `git push`."""
    _git(cloned_repo, "checkout", "-b", "loop/otherbranch")
    (cloned_repo / "ob.txt").write_text("ob\n", encoding="utf-8")
    _git(cloned_repo, "add", "ob.txt")
    _git(cloned_repo, "commit", "-m", "other branch content")
    _git(cloned_repo, "checkout", "main")  # HEAD is now `main`, not `loop/otherbranch`

    vcs.push(cloned_repo, "loop/otherbranch")

    remote_branches = _git(remote, "branch", "--list", "loop/otherbranch")
    assert "loop/otherbranch" in remote_branches.stdout


def test_push_raises_on_no_configured_remote(vcs, repo):
    """`repo` (the module-level fixture) has no remote at all -- the
    "no upstream configured" branch falls back to `git push origin
    <branch>`, which fails because `origin` does not exist."""
    with pytest.raises(VcsCommandError):
        vcs.push(repo, "main")


def test_push_raises_rather_than_falls_back_on_a_non_missing_upstream_rev_parse_failure(vcs, repo, monkeypatch):
    """Review finding (P3, Blind Hunter + Edge Case Hunter): the earlier
    implementation treated ANY non-zero `git rev-parse --abbrev-ref
    <branch>@{upstream}` exit as "no upstream configured" and silently fell
    back to `git push origin <branch>` -- conflating the genuine no-upstream
    case with an ambiguous/corrupted rev-parse failure, which could push to
    a remote/branch the caller never intended. `branch` here does not exist
    locally at all, so `rev-parse` fails with git's own "no such branch"
    wording, NOT "no upstream configured for branch" -- this must raise
    rather than fall back to a first-push attempt."""
    import pyforge.marshal.adapters.vcs_git as vcs_git_module

    real_run = subprocess.run
    push_argv: list[list[str]] = []

    def _capture(args, **kwargs):
        if "push" in args:
            push_argv.append(list(args))
        return real_run(args, **kwargs)

    monkeypatch.setattr(vcs_git_module.subprocess, "run", _capture)

    with pytest.raises(VcsCommandError, match="not the ordinary no-upstream case"):
        vcs.push(repo, "no-such-local-branch")

    # The malformed rev-parse failure must never fall through to an actual
    # push attempt.
    assert push_argv == []


def test_push_raises_on_a_malformed_upstream_with_no_remote_slash(vcs, repo):
    """P6 (Story 3.8 review): the pre-existing "refuse to guess" guard --
    `@{upstream}` resolving to a value with no `<remote>/<remote_branch>`
    shape, e.g. a local branch tracking another LOCAL branch rather than a
    remote-tracking ref -- had no test exercising it before this story's
    review pass. `git branch --set-upstream-to` accepts a local branch as a
    target without complaint; `--abbrev-ref ...@{upstream}` then resolves to
    a bare branch name with no `/` at all, which this method must refuse to
    push against rather than guess a remote."""
    _git(repo, "branch", "other")
    _git(repo, "branch", "--set-upstream-to=other", "main")

    with pytest.raises(VcsCommandError, match="cannot parse upstream"):
        vcs.push(repo, "main")


# --- changed_files (Story 2.3, AD-27) -----------------------------------------


def test_changed_files_clean_worktree_no_commits_ahead_returns_empty(vcs, repo):
    assert vcs.changed_files(repo, repo, base="main") == ()


def test_changed_files_reports_a_committed_change_since_base(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "new-file.txt").write_text("hello\n", encoding="utf-8")
    _git(home, "add", "new-file.txt")
    _git(home, "commit", "-m", "add new-file.txt")

    assert vcs.changed_files(repo, home, base="main") == ("new-file.txt",)


def test_changed_files_reports_an_untracked_file(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")

    assert vcs.changed_files(repo, home, base="main") == ("scratch.txt",)


def test_changed_files_reports_an_uncommitted_modification(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "README.md").write_text("changed\n", encoding="utf-8")

    assert vcs.changed_files(repo, home, base="main") == ("README.md",)


def test_changed_files_is_the_union_of_committed_and_uncommitted(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "committed.txt").write_text("a\n", encoding="utf-8")
    _git(home, "add", "committed.txt")
    _git(home, "commit", "-m", "add committed.txt")
    (home / "dirty.txt").write_text("b\n", encoding="utf-8")

    assert vcs.changed_files(repo, home, base="main") == ("committed.txt", "dirty.txt")


def test_changed_files_a_path_changed_both_ways_is_deduplicated(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "README.md").write_text("commit one\n", encoding="utf-8")
    _git(home, "add", "README.md")
    _git(home, "commit", "-m", "modify README")
    (home / "README.md").write_text("dirty on top\n", encoding="utf-8")

    assert vcs.changed_files(repo, home, base="main") == ("README.md",)


def test_changed_files_a_rename_reports_only_the_new_path(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    _git(home, "mv", "README.md", "RENAMED.md")

    result = vcs.changed_files(repo, home, base="main")
    assert "RENAMED.md" in result
    assert "README.md" not in result


def test_changed_files_a_committed_rename_reports_only_the_new_path(vcs, repo, tmp_path):
    """Review finding (Edge Case Hunter): unlike the uncommitted-rename case
    above (already handled by the porcelain branch's own " -> " parsing), a
    COMMITTED rename is reported by `git diff`, which without rename
    detection (`-M`) shows BOTH the old (now-nonexistent) and new paths as
    separate changed entries."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    _git(home, "mv", "README.md", "COMMITTED-RENAME.md")
    _git(home, "commit", "-m", "rename README")

    result = vcs.changed_files(repo, home, base="main")
    assert "COMMITTED-RENAME.md" in result
    assert "README.md" not in result


def test_changed_files_an_untracked_directory_reports_each_file_individually(vcs, repo, tmp_path):
    """Review finding (Blind Hunter + Edge Case Hunter): git's default
    `--untracked-files=normal` collapses a wholly-new untracked directory
    into a single "dir/" porcelain line -- which never matches a
    file-shaped glob (e.g. "newthing/*.yaml"), silently breaking scope/
    frozen-path checking for every file inside it."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    newdir = home / "newthing"
    newdir.mkdir()
    (newdir / "a.yaml").write_text("a\n", encoding="utf-8")
    (newdir / "b.yaml").write_text("b\n", encoding="utf-8")

    result = vcs.changed_files(repo, home, base="main")
    assert "newthing/a.yaml" in result
    assert "newthing/b.yaml" in result
    assert "newthing" not in result
    assert "newthing/" not in result


def test_changed_files_a_non_ascii_path_round_trips_literally(vcs, repo, tmp_path):
    """Review finding (Blind Hunter + Edge Case Hunter): git's default
    `core.quotePath=true` C-escapes/quotes a non-ASCII path (e.g.
    `"caf\\303\\251.txt"` for `café.txt`) instead of emitting the literal
    UTF-8 path -- a path in that shape never matches its own glob."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "café.txt").write_text("x\n", encoding="utf-8")

    result = vcs.changed_files(repo, home, base="main")
    assert "café.txt" in result


def test_changed_files_git_diff_runs_against_the_worktrees_own_head(vcs, repo, tmp_path):
    """Review-motivated regression: `HEAD` is per-worktree, and `base`/refs
    are shared across every worktree of one repo -- if `changed_files` ran
    `git diff` against `repo_root`'s own checked-out HEAD instead of
    `worktree_path`'s, a commit made only in the LINKED worktree would
    never appear (repo_root's own HEAD never moved)."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "only-in-worktree.txt").write_text("x\n", encoding="utf-8")
    _git(home, "add", "only-in-worktree.txt")
    _git(home, "commit", "-m", "worktree-only commit")

    # repo (the main checkout) never advanced past `main`.
    assert vcs.changed_files(repo, repo, base="main") == ()
    assert vcs.changed_files(repo, home, base="main") == ("only-in-worktree.txt",)


def test_changed_files_raises_on_an_unresolvable_base(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.changed_files(repo, repo, base="no-such-ref")


def test_changed_files_returns_a_sorted_tuple(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "z.txt").write_text("z\n", encoding="utf-8")
    (home / "a.txt").write_text("a\n", encoding="utf-8")

    result = vcs.changed_files(repo, home, base="main")
    assert result == tuple(sorted(result))
    assert result == ("a.txt", "z.txt")


# --- commit_subjects/commit_paths (Story 4.1, AD-29/AD-33) -----------------


def test_commit_subjects_returns_every_subject_reachable_from_ref(vcs, repo):
    _git(repo, "commit", "--allow-empty", "-m", "second commit")
    _git(repo, "commit", "--allow-empty", "-m", "third commit")

    subjects = vcs.commit_subjects(repo, "main")

    assert subjects == ("third commit", "second commit", "initial")


def test_commit_subjects_raises_on_an_unresolvable_ref(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.commit_subjects(repo, "no-such-ref")


def test_commit_subjects_raises_when_no_origin_remote_configured(vcs, repo):
    """The "no origin remote" case that `cli/deploy.py`'s push route treats
    as ordinary/best-effort still raises VcsCommandError from THIS method --
    the port itself makes no distinction; the caller decides how to react."""
    with pytest.raises(VcsCommandError):
        vcs.commit_subjects(repo, "origin/main")


def test_commit_paths_stages_and_commits_only_the_named_paths(vcs, repo):
    (repo / "tracked.txt").write_text("already tracked\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "add tracked.txt")

    # An unrelated change sits in the working tree/index -- proof the commit
    # this method makes contains ONLY the named path, never a pre-existing
    # index (AD-29's own literal requirement).
    (repo / "tracked.txt").write_text("modified but NOT committed\n", encoding="utf-8")
    (repo / "promoted.txt").write_text("promoted content\n", encoding="utf-8")

    sha = vcs.commit_paths(repo, (repo / "promoted.txt",), to_redacted_text("marshal: promote 1 story spec(s)"))

    assert sha == _git(repo, "rev-parse", "HEAD").stdout.strip()
    show = _git(repo, "show", "--name-only", "--format=", "HEAD")
    committed_files = [line for line in show.stdout.splitlines() if line.strip()]
    assert committed_files == ["promoted.txt"]
    # tracked.txt's uncommitted modification is untouched by the commit.
    status = _git(repo, "status", "--porcelain")
    assert "tracked.txt" in status.stdout


def test_commit_paths_commits_multiple_paths_in_one_commit(vcs, repo):
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    (repo / "b.txt").write_text("b\n", encoding="utf-8")

    vcs.commit_paths(repo, (repo / "a.txt", repo / "b.txt"), to_redacted_text("marshal: promote 2 story spec(s)"))

    show = _git(repo, "show", "--name-only", "--format=", "HEAD")
    committed_files = sorted(line for line in show.stdout.splitlines() if line.strip())
    assert committed_files == ["a.txt", "b.txt"]
    log = _git(repo, "log", "-1", "--format=%s")
    assert log.stdout.strip() == "marshal: promote 2 story spec(s)"


def test_commit_paths_raises_on_empty_paths(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.commit_paths(repo, (), to_redacted_text("marshal: promote 0 story spec(s)"))


def test_commit_paths_returns_the_new_commit_sha(vcs, repo):
    (repo / "c.txt").write_text("c\n", encoding="utf-8")

    sha = vcs.commit_paths(repo, (repo / "c.txt",), to_redacted_text("marshal: promote 1 story spec(s)"))

    assert sha == _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert sha != _git(repo, "rev-parse", "HEAD~1").stdout.strip()


def test_path_has_uncommitted_changes_false_for_a_committed_clean_file(vcs, repo):
    (repo / "clean.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "clean.txt")
    _git(repo, "commit", "-m", "add clean.txt")

    assert vcs.path_has_uncommitted_changes(repo, repo / "clean.txt") is False


def test_path_has_uncommitted_changes_true_for_an_untracked_file(vcs, repo):
    (repo / "untracked.txt").write_text("new\n", encoding="utf-8")

    assert vcs.path_has_uncommitted_changes(repo, repo / "untracked.txt") is True


def test_path_has_uncommitted_changes_true_for_a_staged_but_uncommitted_file(vcs, repo):
    """The exact partial-batch-failure shape this method exists to catch:
    a file `git add`ed (as `commit_paths`'s own first phase does) but never
    actually committed."""
    (repo / "staged.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, "add", "staged.txt")

    assert vcs.path_has_uncommitted_changes(repo, repo / "staged.txt") is True


def test_path_has_uncommitted_changes_true_for_a_modified_tracked_file(vcs, repo):
    (repo / "tracked.txt").write_text("v1\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "add tracked.txt")
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")

    assert vcs.path_has_uncommitted_changes(repo, repo / "tracked.txt") is True


def test_path_has_uncommitted_changes_scoped_to_only_the_named_path(vcs, repo):
    """An unrelated dirty file elsewhere in the worktree must not make an
    unrelated, genuinely clean path report dirty -- the whole reason this
    method exists instead of reusing whole-worktree `has_uncommitted_changes`."""
    (repo / "clean.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "clean.txt")
    _git(repo, "commit", "-m", "add clean.txt")
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    assert vcs.path_has_uncommitted_changes(repo, repo / "clean.txt") is False


def test_path_has_uncommitted_changes_raises_outside_a_repo(vcs, tmp_path):
    with pytest.raises(VcsCommandError):
        vcs.path_has_uncommitted_changes(tmp_path, tmp_path / "nope.txt")


# --- merge_base/merge_branch (Story 4.3, FR-27/AD-24) ----------------------


def test_merge_base_returns_the_common_ancestor_sha(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    base_sha = _git(repo, "rev-parse", "main").stdout.strip()
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")

    assert vcs.merge_base(repo, "loop/x", "main") == base_sha


def test_merge_base_raises_when_no_common_history(vcs, repo, tmp_path):
    _git(repo, "checkout", "--orphan", "orphan-branch")
    _git(repo, "commit", "--allow-empty", "-m", "orphan root")
    _git(repo, "checkout", "main")

    with pytest.raises(VcsCommandError):
        vcs.merge_base(repo, "orphan-branch", "main")


def test_merge_base_raises_on_an_unresolvable_ref(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.merge_base(repo, "no-such-ref", "main")


def test_resolve_ref_returns_the_branch_tip_sha(vcs, repo):
    expected = _git(repo, "rev-parse", "main").stdout.strip()
    assert vcs.resolve_ref(repo, "main") == expected


def test_resolve_ref_raises_on_an_unresolvable_branch(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.resolve_ref(repo, "no-such-branch")


def test_merge_branch_merges_cleanly_and_returns_the_new_commit_sha(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")

    sha = vcs.merge_branch(repo, "loop/x", into="main", subject="Merge 1.2 into main")

    # `refs/heads/main` was advanced via `update-ref` -- `rev-parse HEAD`
    # dereferences repo_root's symbolic HEAD -> refs/heads/main, so it
    # reflects the new tip even though repo_root's own working tree/index
    # was never touched by this call (P1: no checkout in repo_root, ever).
    assert sha == _git(repo, "rev-parse", "HEAD").stdout.strip()
    # The new commit's CONTENT is reachable via the ref, even though
    # repo_root's own checked-out files were never refreshed to match it.
    show = _git(repo, "show", f"{sha}:feature.txt")
    assert show.stdout.strip() == "feature"
    log = _git(repo, "log", "-1", "--format=%s", "refs/heads/main")
    assert log.stdout.strip() == "Merge 1.2 into main"
    # --no-ff: a real merge commit, with two parents, even though this was
    # a fast-forward-eligible branch.
    parents = _git(repo, "log", "-1", "--format=%P", "refs/heads/main").stdout.strip().split()
    assert len(parents) == 2


def test_merge_branch_never_touches_repo_roots_own_active_checkout(vcs, repo, tmp_path):
    """P1's own single most severe finding: repo_root is this project's ONE
    shared, currently-active checkout -- merge_branch must never run `git
    checkout` against it, whatever branch it currently has checked out."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")
    _git(repo, "checkout", "-b", "some-other-branch")
    head_before = _git(repo, "rev-parse", "HEAD").stdout.strip()
    symbolic_before = _git(repo, "symbolic-ref", "HEAD").stdout.strip()

    vcs.merge_branch(repo, "loop/x", into="main", subject="Merge 1.2 into main")

    # repo_root's own checked-out branch, and its HEAD commit, are exactly
    # what they were before the call -- `main` was advanced by ref alone.
    assert _git(repo, "symbolic-ref", "HEAD").stdout.strip() == symbolic_before
    assert _git(repo, "branch", "--show-current").stdout.strip() == "some-other-branch"
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == head_before
    # `main` itself DID advance -- that is the one intended write.
    assert _git(repo, "log", "-1", "--format=%s", "refs/heads/main").stdout.strip() == ("Merge 1.2 into main")


def test_merge_branch_never_checks_out_branch_itself(vcs, repo, tmp_path):
    """Read-only against `branch` -- a linked worktree already has it
    checked out throughout, and merge_branch must not disturb that."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")

    vcs.merge_branch(repo, "loop/x", into="main", subject="Merge 1.2 into main")

    # The linked worktree is untouched: still on loop/x, still has its own
    # feature commit as HEAD (never rewritten/rebased by the merge).
    branch_result = _git(home, "branch", "--show-current")
    assert branch_result.stdout.strip() == "loop/x"


def test_merge_branch_leaves_no_temp_worktree_behind_on_success(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")

    vcs.merge_branch(repo, "loop/x", into="main", subject="Merge 1.2 into main")

    assert not any("marshal-land-" in path for path in _worktree_paths(repo))


def test_merge_branch_raises_vcs_command_error_on_conflict(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "README.md").write_text("conflicting change\n", encoding="utf-8")
    _git(home, "add", "README.md")
    _git(home, "commit", "-m", "conflicting commit")
    (repo / "README.md").write_text("a different change\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "main's own change")

    with pytest.raises(VcsCommandError):
        vcs.merge_branch(repo, "loop/x", into="main", subject="Merge 1.2 into main")

    # The temp worktree the conflict happened inside is still cleaned up --
    # no leak, and no conflict-marker state left behind in repo_root itself
    # (the conflict lived only in the now-removed temp worktree).
    assert not any("marshal-land-" in path for path in _worktree_paths(repo))
    status = _git(repo, "status", "--porcelain")
    assert status.stdout.strip() == ""


def test_merge_branch_raises_on_an_unresolvable_branch(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.merge_branch(repo, "no-such-branch", into="main", subject="Merge 1.2 into main")


def test_merge_branch_refuses_when_into_moves_concurrently(vcs, repo, tmp_path, monkeypatch):
    """P4: `into` moving between merge_branch's own read of its tip and the
    write that advances it must never be silently overwritten -- the
    three-arg `update-ref` compare-and-swap must refuse instead."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")

    from pyforge.marshal.adapters import vcs_git as vcs_git_module

    real_run = vcs_git_module._run
    moved = {"done": False}

    def _racy_run(args, *, timeout_s=vcs_git_module._GIT_TIMEOUT_S):
        result = real_run(args, timeout_s=timeout_s)
        if not moved["done"] and "worktree" in args and "--detach" in args:
            # A commit lands directly on `main` in repo_root -- simulating
            # a concurrent write -- right after merge_branch has already
            # pinned its detached worktree to `main`'s OLD tip.
            (repo / "concurrent.txt").write_text("concurrent\n", encoding="utf-8")
            _git(repo, "add", "concurrent.txt")
            _git(repo, "commit", "-m", "a concurrent commit lands on main")
            moved["done"] = True
        return result

    monkeypatch.setattr(vcs_git_module, "_run", _racy_run)

    with pytest.raises(VcsCommandError):
        vcs.merge_branch(repo, "loop/x", into="main", subject="Merge 1.2 into main")

    # The concurrent commit survives untouched -- the CAS refused to
    # overwrite it with the stale merge.
    log = _git(repo, "log", "-1", "--format=%s", "refs/heads/main")
    assert log.stdout.strip() == "a concurrent commit lands on main"
    # ...and the temp worktree is still cleaned up despite the CAS failure.
    assert not any("marshal-land-" in path for path in _worktree_paths(repo))


def test_merge_branch_still_returns_the_sha_if_temp_worktree_cleanup_fails(vcs, repo, tmp_path, monkeypatch):
    """P5: a cosmetic post-merge-success failure (here, the temp worktree's
    own removal) must never mask an already-durable merge -- cleanup is
    best-effort and swallows this class of failure internally, so a
    successfully-landed merge is always reported back to the caller."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")

    from pyforge.marshal.adapters import vcs_git as vcs_git_module

    real_run = vcs_git_module._run

    def _flaky_run(args, *, timeout_s=vcs_git_module._GIT_TIMEOUT_S):
        if "worktree" in args and "remove" in args:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="simulated cleanup failure")
        return real_run(args, timeout_s=timeout_s)

    monkeypatch.setattr(vcs_git_module, "_run", _flaky_run)

    sha = vcs.merge_branch(repo, "loop/x", into="main", subject="Merge 1.2 into main")

    assert sha == _git(repo, "rev-parse", "HEAD").stdout.strip()
    # The fallback cleanup path (raw rmtree + prune) still ran -- no
    # dangling registration survives even though `worktree remove` itself
    # was made to fail.
    assert not any("marshal-land-" in path for path in _worktree_paths(repo))


def test_merge_branch_still_returns_the_sha_if_cleanup_raises_outright(vcs, repo, tmp_path, monkeypatch):
    """P5, the stronger case: `_run` itself can RAISE `VcsCommandError`
    (a launch failure, a timeout) rather than merely returning a non-zero
    exit code -- the `finally` block's own cleanup must swallow that too,
    never letting a cosmetic post-success failure escape and mask an
    already-durable merge."""
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")

    from pyforge.marshal.adapters import vcs_git as vcs_git_module

    real_run = vcs_git_module._run

    def _raising_run(args, *, timeout_s=vcs_git_module._GIT_TIMEOUT_S):
        if "worktree" in args and "remove" in args:
            raise VcsCommandError("simulated: git executable vanished mid-cleanup")
        return real_run(args, timeout_s=timeout_s)

    monkeypatch.setattr(vcs_git_module, "_run", _raising_run)

    sha = vcs.merge_branch(repo, "loop/x", into="main", subject="Merge 1.2 into main")

    assert sha == _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert not any("marshal-land-" in path for path in _worktree_paths(repo))


# --- worktree_head_sha (Story 4.4, code review, 2026-08-06, P5) ------------


def test_worktree_head_sha_returns_the_checked_out_commit(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    expected = _git(home, "rev-parse", "HEAD").stdout.strip()
    assert vcs.worktree_head_sha(home) == expected


def test_worktree_head_sha_reflects_a_new_commit_in_that_worktree(vcs, repo, tmp_path):
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/x", base="main")
    (home / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(home, "add", "feature.txt")
    _git(home, "commit", "-m", "feature commit")
    expected = _git(home, "rev-parse", "HEAD").stdout.strip()
    assert vcs.worktree_head_sha(home) == expected


def test_worktree_head_sha_raises_when_not_a_git_repository(vcs, tmp_path):
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    with pytest.raises(VcsCommandError):
        vcs.worktree_head_sha(not_a_repo)


# --- fetch/fast_forward (Story 4.12, FR-173) --------------------------------


def test_fast_forward_advances_a_behind_branch_to_the_fetched_ref(vcs, repo, remote, tmp_path):
    """The ordinary case: `home` is behind `origin/main` -- `fetch` updates
    `refs/remotes/origin/main`, then `fast_forward` advances `home`'s own
    checked-out branch to it and returns the new HEAD sha."""
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")

    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/behind", base="main")

    (repo / "advance.txt").write_text("advance\n", encoding="utf-8")
    _git(repo, "add", "advance.txt")
    _git(repo, "commit", "-m", "advance main")
    _git(repo, "push", "origin", "main")
    expected = _git(repo, "rev-parse", "main").stdout.strip()

    vcs.fetch(home, "origin", "main")
    new_head = vcs.fast_forward(home, "origin/main")

    assert new_head == expected
    assert _git(home, "rev-parse", "HEAD").stdout.strip() == expected


def test_fast_forward_no_ops_cleanly_when_already_current(vcs, repo, remote, tmp_path):
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")

    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/current", base="main")
    before = _git(home, "rev-parse", "HEAD").stdout.strip()

    vcs.fetch(home, "origin", "main")
    new_head = vcs.fast_forward(home, "origin/main")

    assert new_head == before


def test_fast_forward_refuses_a_diverged_branch(vcs, repo, remote, tmp_path):
    """A branch that has advanced PAST the fetched ref (e.g. a live run
    that kept committing to `loop/<slug>` after the wave was landed) is not
    a fast-forward -- git refuses cleanly, never a forced merge/rebase.
    Genuine divergence needs BOTH sides to carry a commit the other lacks --
    `home`'s branch alone racing ahead of an unmoved `origin/main` is
    trivially still an ancestor relationship (a no-op "already up to
    date"), not a real divergence."""
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")

    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/diverged", base="main")
    (home / "diverged.txt").write_text("diverged\n", encoding="utf-8")
    _git(home, "add", "diverged.txt")
    _git(home, "commit", "-m", "diverged commit never pushed to origin/main")
    home_head_before = _git(home, "rev-parse", "HEAD").stdout.strip()

    # origin/main ALSO advances independently -- neither tip is an ancestor
    # of the other, the genuine "not a fast-forward" shape.
    (repo / "advance.txt").write_text("advance\n", encoding="utf-8")
    _git(repo, "add", "advance.txt")
    _git(repo, "commit", "-m", "origin/main's own independent advance")
    _git(repo, "push", "origin", "main")

    vcs.fetch(home, "origin", "main")
    with pytest.raises(VcsCommandError):
        vcs.fast_forward(home, "origin/main")

    # The branch is left completely untouched on refusal.
    assert _git(home, "rev-parse", "HEAD").stdout.strip() == home_head_before


def test_fast_forward_refuses_a_dirty_working_tree(vcs, repo, remote, tmp_path):
    """A fast-forward that would silently overwrite uncommitted, conflicting
    local content is refused -- the incoming commit touches the SAME file
    `home` carries a conflicting uncommitted edit to (touching a different,
    unrelated file lets git fast-forward cleanly around an unrelated dirty
    file, which would not exercise this refusal at all)."""
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")

    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/dirty", base="main")
    (repo / "README.md").write_text("advanced content\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "advance main")
    _git(repo, "push", "origin", "main")
    (home / "README.md").write_text("uncommitted local edit\n", encoding="utf-8")

    vcs.fetch(home, "origin", "main")
    with pytest.raises(VcsCommandError):
        vcs.fast_forward(home, "origin/main")


def test_fetch_raises_on_an_unknown_remote(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.fetch(repo, "origin", "main")


def test_fetch_raises_when_repo_root_is_not_a_git_repository(vcs, tmp_path):
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    with pytest.raises(VcsCommandError):
        vcs.fetch(not_a_repo, "origin", "main")


def test_fetch_only_updates_the_remote_tracking_ref_never_a_local_branch(vcs, repo, remote, tmp_path):
    """`fetch` alone (no `fast_forward` call) must never move `home`'s own
    checked-out branch -- only `refs/remotes/origin/<ref>` advances."""
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")

    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/untouched", base="main")
    before = _git(home, "rev-parse", "HEAD").stdout.strip()

    (repo / "advance.txt").write_text("advance\n", encoding="utf-8")
    _git(repo, "add", "advance.txt")
    _git(repo, "commit", "-m", "advance main")
    _git(repo, "push", "origin", "main")

    vcs.fetch(home, "origin", "main")

    assert _git(home, "rev-parse", "HEAD").stdout.strip() == before
    assert (
        _git(home, "rev-parse", "refs/remotes/origin/main").stdout.strip()
        == _git(repo, "rev-parse", "main").stdout.strip()
    )


def test_fast_forward_raises_on_an_unresolvable_ref(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.fast_forward(repo, "origin/no-such-branch")


# --- commits_behind (Story 15.1; Story 57.1 review 2 moved refresh to the full refname) ---


def test_commits_behind_counts_against_the_full_remote_tracking_ref_not_a_shadowing_branch(vcs, repo, remote, tmp_path):
    """`refs/remotes/origin/main` is what refresh counts against since review 2 -- a LOCAL
    branch named `origin/main` (which the short name would resolve to first) is ignored."""
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")
    home = tmp_path / "home"
    vcs.add_worktree(repo, home, "loop/behind", base="main")
    for n in (1, 2):
        (repo / f"advance-{n}.txt").write_text(f"{n}\n", encoding="utf-8")
        _git(repo, "add", f"advance-{n}.txt")
        _git(repo, "commit", "-m", f"advance {n}")
    _git(repo, "push", "origin", "main")
    vcs.fetch(home, "origin", "main")
    _git(home, "branch", "origin/main", "HEAD")  # the shadow: 0 behind if it were consulted

    assert vcs.commits_behind(home, "refs/remotes/origin/main") == 2
    assert vcs.commits_behind(home, "origin/main") == 0  # why refresh no longer passes the short name


def test_commits_behind_raises_on_an_unresolvable_ref(vcs, repo):
    with pytest.raises(VcsCommandError, match="rev-list --count"):
        vcs.commits_behind(repo, "refs/remotes/origin/no-such-branch")


def test_push_without_the_env_utility_goes_through_the_preflight(vcs, cloned_repo, remote, monkeypatch):
    """Story 57.1 review 2 (L-D): where the POSIX `env` utility is absent (win-64), a proven
    push still pushes the proven sha, but through the preflight -- no opt-out variables."""
    import pyforge.marshal.adapters.vcs_git as vcs_git

    seen = _record_hook_env(cloned_repo)
    real_which = vcs_git.shutil.which
    monkeypatch.setattr(
        vcs_git.shutil, "which", lambda name, *a, **k: None if name == "env" else real_which(name, *a, **k)
    )
    tip = _git(cloned_repo, "rev-parse", "refs/remotes/origin/main").stdout.strip()
    _git(cloned_repo, "branch", "loop/acme", tip)

    vcs.push(cloned_repo, "loop/acme", proven_on_main_sha=tip)

    assert seen.read_text(encoding="utf-8").splitlines() == ["unset|unset"]
    assert _git(remote, "rev-parse", "loop/acme").stdout.strip() == tip


# --- worktree_unified_patch (Story 22.6) / merge_tree_conflict_paths + file_text_at_ref (Story 28.20) ---


def test_worktree_unified_patch_carries_committed_and_dirty_changes(vcs, repo):
    baseline = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "committed.txt").write_text("committed\n", encoding="utf-8")
    _git(repo, "add", "committed.txt")
    _git(repo, "commit", "-m", "committed change")
    (repo / "README.md").write_text("dirty edit\n", encoding="utf-8")

    patch = vcs.worktree_unified_patch(repo, baseline_sha=baseline)

    assert "+committed" in patch
    assert "+dirty edit" in patch


def test_worktree_unified_patch_is_empty_with_no_change(vcs, repo):
    baseline = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert vcs.worktree_unified_patch(repo, baseline_sha=baseline) == ""


def test_worktree_unified_patch_raises_on_an_unresolvable_baseline(vcs, repo):
    with pytest.raises(VcsCommandError):
        vcs.worktree_unified_patch(repo, baseline_sha="0" * 40)


def _conflicting_branch(repo: Path) -> None:
    """`main` and `feature/conflict` both edit `README.md` and `b c.txt`, both add `e.txt`
    with different content (add/add), and `main` deletes `d.txt`, which `feature/conflict`
    modifies (modify/delete)."""
    (repo / "b c.txt").write_text("b\n", encoding="utf-8")
    (repo / "d.txt").write_text("d\n", encoding="utf-8")
    _git(repo, "add", "b c.txt", "d.txt")
    _git(repo, "commit", "-m", "base files")
    base_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    (repo / "README.md").write_text("main version\n", encoding="utf-8")
    (repo / "b c.txt").write_text("main b\n", encoding="utf-8")
    (repo / "e.txt").write_text("main e\n", encoding="utf-8")
    _git(repo, "rm", "-q", "d.txt")
    _git(repo, "add", "e.txt")
    _git(repo, "commit", "-am", "main edits")
    _git(repo, "checkout", "-q", "-b", "feature/conflict", base_sha)
    (repo / "README.md").write_text("feature version\n", encoding="utf-8")
    (repo / "b c.txt").write_text("feature b\n", encoding="utf-8")
    (repo / "d.txt").write_text("feature d\n", encoding="utf-8")
    (repo / "e.txt").write_text("feature e\n", encoding="utf-8")
    _git(repo, "add", "e.txt")
    _git(repo, "commit", "-am", "feature edits")
    _git(repo, "checkout", "-q", "main")


def test_merge_tree_conflict_paths_names_every_conflicted_file(vcs, repo):
    """Story 58.1 (CAP-268): content, add/add and modify/delete conflicts alike, a space in
    a name intact. The legacy three-arg merge-tree this replaced returned () here."""
    _conflicting_branch(repo)

    assert vcs.merge_tree_conflict_paths(repo, "main", "feature/conflict") == (
        "README.md",
        "b c.txt",
        "d.txt",
        "e.txt",
    )


def test_merge_tree_conflict_paths_refuses_a_conflict_that_names_no_file(vcs, repo):
    """Story 58.1 review (low): git's manual -- "do NOT interpret an empty Conflicted file info
    list as a clean merge". A directory-rename split (main scatters `a/`'s files into `b/` and
    `c/`; the branch adds `a/new.txt`) exits 1 with a tree and no path; it must not read as clean."""
    (repo / "a").mkdir()
    for n in range(1, 5):
        (repo / "a" / f"f{n}").write_text(f"{n}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "base dir")
    _git(repo, "checkout", "-q", "-b", "feature/new-in-a")
    (repo / "a" / "new.txt").write_text("n\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "add a/new.txt")
    _git(repo, "checkout", "-q", "main")
    (repo / "b").mkdir()
    (repo / "c").mkdir()
    for n, dest in ((1, "b"), (2, "b"), (3, "c"), (4, "c")):
        _git(repo, "mv", f"a/f{n}", f"{dest}/f{n}")
    _git(repo, "commit", "-m", "split a/ into b/ and c/")

    with pytest.raises(VcsCommandError, match="names no file"):
        vcs.merge_tree_conflict_paths(repo, "main", "feature/new-in-a")


def test_merge_tree_conflict_paths_never_touches_the_working_tree_or_refs(vcs, repo):
    _conflicting_branch(repo)
    before = _git(repo, "for-each-ref").stdout, _git(repo, "status", "--porcelain").stdout

    vcs.merge_tree_conflict_paths(repo, "main", "feature/conflict")

    assert (_git(repo, "for-each-ref").stdout, _git(repo, "status", "--porcelain").stdout) == before


def test_merge_tree_conflict_paths_raises_on_an_unknown_branch(vcs, repo):
    """An unknown ref also exits 1 -- the conflicted-merge code -- but prints no tree, so it
    is an error, never an empty list that reads as a clean merge."""
    with pytest.raises(VcsCommandError, match="merge-tree --write-tree"):
        vcs.merge_tree_conflict_paths(repo, "main", "no-such-branch")


def test_merge_ref_resolving_commits_a_two_parent_merge_with_the_given_resolution(vcs, repo):
    """Story 59.1 (CAP-269): the conflicted path takes the given text; the result is a real
    merge of the ref, so a later three-way merge against that ref is clean."""
    _conflicting_branch(repo)
    _git(repo, "checkout", "-q", "-b", "readme-only", "feature/conflict~1")
    (repo / "README.md").write_text("readme-only version\n", encoding="utf-8")
    _git(repo, "commit", "-am", "only README differs")
    main_sha = _git(repo, "rev-parse", "main").stdout.strip()
    # main also touched b c.txt / d.txt / e.txt, which this branch never did -> they merge cleanly
    sha = vcs.merge_ref_resolving(
        repo, VcsRef("main"), resolutions={"README.md": "resolved\n"}, message=to_redacted_text("union heal")
    )

    parents = _git(repo, "rev-list", "--parents", "-n", "1", sha).stdout.split()[1:]
    assert parents[1] == main_sha
    assert (repo / "README.md").read_text(encoding="utf-8") == "resolved\n"
    assert _git(repo, "log", "-1", "--format=%s", sha).stdout.strip() == "union heal"
    assert _git(repo, "status", "--porcelain").stdout == ""
    assert vcs.merge_tree_conflict_paths(repo, "main", "readme-only") == ()


def test_merge_ref_resolving_aborts_on_a_conflict_it_cannot_resolve(vcs, repo):
    _conflicting_branch(repo)
    _git(repo, "checkout", "-q", "feature/conflict")
    before = _git(repo, "rev-parse", "HEAD").stdout.strip()

    with pytest.raises(VcsCommandError, match="conflicts outside the resolvable paths: .*README.md"):
        vcs.merge_ref_resolving(
            repo, VcsRef("main"), resolutions={"b c.txt": "x\n"}, message=to_redacted_text("union heal")
        )

    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == before
    assert _git(repo, "status", "--porcelain").stdout == ""
    probe = subprocess.run(["git", "-C", str(repo), "rev-parse", "-q", "--verify", "MERGE_HEAD"], capture_output=True)
    assert probe.returncode != 0  # no merge left in progress


def test_merge_ref_resolving_reports_an_unwritable_resolution_as_a_vcs_error_and_aborts(vcs, repo, monkeypatch):
    """Story 59.1 review 2: an OSError writing the resolution used to escape raw and crash
    `dispatch land`; it is the port's `VcsCommandError`, and the merge is aborted."""
    _conflicting_branch(repo)
    _git(repo, "checkout", "-q", "-b", "readme-only", "feature/conflict~1")
    (repo / "README.md").write_text("readme-only version\n", encoding="utf-8")
    _git(repo, "commit", "-am", "only README differs")
    before = _git(repo, "rev-parse", "HEAD").stdout.strip()

    def _refuse(self, *args, **kwargs):
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "write_text", _refuse)
    with pytest.raises(VcsCommandError, match="cannot write the resolution of README.md"):
        vcs.merge_ref_resolving(
            repo, VcsRef("main"), resolutions={"README.md": "resolved\n"}, message=to_redacted_text("union heal")
        )
    monkeypatch.undo()

    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == before
    assert _git(repo, "status", "--porcelain").stdout == ""


def test_merge_ref_resolving_refuses_and_leaves_a_merge_already_in_progress(vcs, repo):
    """Story 59.1 review: a pending merge in the worktree is someone else's -- never adopted
    (committed under the heal's message) nor aborted (their work lost)."""
    _conflicting_branch(repo)
    _git(repo, "checkout", "-q", "feature/conflict")
    subprocess.run(["git", "-C", str(repo), "merge", "--no-commit", "main"], capture_output=True)  # conflicts
    theirs = _git(repo, "rev-parse", "MERGE_HEAD").stdout.strip()

    with pytest.raises(VcsCommandError, match="already in progress"):
        vcs.merge_ref_resolving(
            repo, VcsRef("main"), resolutions={"README.md": "x\n"}, message=to_redacted_text("union heal")
        )

    assert _git(repo, "rev-parse", "MERGE_HEAD").stdout.strip() == theirs


def test_merge_ref_resolving_is_a_no_op_for_a_ref_already_merged(vcs, repo):
    _git(repo, "checkout", "-q", "-b", "ahead")
    (repo / "ahead.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "ahead.txt")
    _git(repo, "commit", "-m", "ahead of main")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()

    assert vcs.merge_ref_resolving(repo, VcsRef("main"), resolutions={}, message=to_redacted_text("union heal")) == head


def test_merge_ref_resolving_raises_on_an_unknown_ref(vcs, repo):
    with pytest.raises(VcsCommandError, match="git merge --no-commit no-such-ref failed"):
        vcs.merge_ref_resolving(repo, VcsRef("no-such-ref"), resolutions={}, message=to_redacted_text("union heal"))


def test_merge_tree_conflict_paths_is_empty_for_a_clean_merge(vcs, repo):
    _git(repo, "checkout", "-q", "-b", "feature/clean")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "add feature.txt")
    _git(repo, "checkout", "-q", "main")

    assert vcs.merge_tree_conflict_paths(repo, "main", "feature/clean") == ()


def test_file_text_at_ref_reads_a_path_and_returns_none_for_a_missing_one(vcs, repo):
    assert vcs.file_text_at_ref(repo, "main", "README.md") == (repo / "README.md").read_text(encoding="utf-8")
    assert vcs.file_text_at_ref(repo, "main", "no-such-file.txt") is None


def test_file_text_at_ref_raises_on_an_unresolvable_ref(vcs, repo):
    with pytest.raises(VcsCommandError, match="git show"):
        vcs.file_text_at_ref(repo, "no-such-ref", "README.md")


def test_commit_paths_onto_remote_tip_does_not_touch_operator_checkout(vcs, repo, remote):
    """CAP-5: promote publishes on origin/main from a throwaway worktree.
    The operator checkout stays on its pre-promote HEAD, dirty files stay,
    and no detached worktree is leaked."""
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")
    dirty = repo / "scratch.txt"
    dirty.write_text("uncommitted\n", encoding="utf-8")
    before_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    before_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    rel = "_bmad-output/projects/acme/planning-artifacts/sprint-status-ledger.yaml"
    sha = vcs.commit_paths_onto_remote_tip(
        repo,
        remote=VcsRef("origin"),
        ref=VcsRef("main"),
        writes=((rel, "development_status:\n  4-4-batch: done\n"),),
        message=to_redacted_text("marshal: promote sprint-status ledger for 'acme' (1 key(s) -> done)"),
    )
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == before_head
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == before_branch
    assert dirty.read_text(encoding="utf-8") == "uncommitted\n"
    assert not (repo / rel).exists()
    assert not any("marshal-promote-" in path for path in _worktree_paths(repo))
    origin_sha = _git(remote, "rev-parse", "refs/heads/main").stdout.strip()
    assert origin_sha == sha
    shown = _git(repo, "show", f"{sha}:{rel}").stdout
    assert "4-4-batch: done" in shown


def test_commit_paths_onto_remote_tip_refuses_empty_writes(vcs, repo):
    with pytest.raises(VcsCommandError, match="at least one write"):
        vcs.commit_paths_onto_remote_tip(
            repo, remote=VcsRef("origin"), ref=VcsRef("main"), writes=(), message=to_redacted_text("nope")
        )


# --- commit_paths_onto_remote_tip: the proof-carrying pre-push opt-out (Story 68.1, CAP-277) ----
#
# 64.1's landing (2026-09-28): the promotion push ran the repository's `pre-push` preflight, which
# outlasted the publish's git timeout, three times. These tests use a real repository with a real
# bare remote and a real `pre-push` hook -- one that sleeps past the (shortened) push timeout
# unless `PYFORGE_PREFLIGHT_SKIP=1`, and then logs `PYFORGE_PREFLIGHT_SKIP_REASON` -- so the
# adapter's opt-out is proven against git's own hook machinery, not a fake.


@pytest.fixture(autouse=True)
def _no_ambient_preflight_opt_out(monkeypatch):
    """An operator (or a harness) with the pre-push opt-out exported would leak it into every hook the
    tests below observe and fail their `unset` / not-in-`os.environ` assertions (Story 68.1 review)."""
    monkeypatch.delenv("PYFORGE_PREFLIGHT_SKIP", raising=False)
    monkeypatch.delenv("PYFORGE_PREFLIGHT_SKIP_REASON", raising=False)


_LEDGER_REL = "_bmad-output/projects/acme/planning-artifacts/sprint-status-ledger.yaml"
_LEDGER_TEXT = "development_status:\n  64-1-a-landing: done\n"
_SKIP_REASON = "marshal ledger promotion for 'acme', story 64-1-a-landing"
_PUSH_TIMEOUT_S = 2.5


def _publish_setup(repo: Path, remote: Path) -> None:
    """Point ``repo`` at ``remote`` and push ``main`` BEFORE any hook is installed."""
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")


def _install_pre_push_hook(repo: Path, *, sleeps: bool) -> tuple[Path, Path]:
    """A ``pre-push`` hook in ``repo`` that records the opt-out variables it saw in ``env.log``
    and, when ``PYFORGE_PREFLIGHT_SKIP=1``, appends the reason to ``skips.log`` and lets the push
    through (as ``scripts/pre_push_preflight.sh`` does). Without the opt-out it sleeps past the
    push timeout (``sleeps=True``, the stand-in for ``pr-preflight``) or just exits 0.
    Returns ``(skips.log, env.log)``."""
    skip_log = repo.parent / "skips.log"
    seen_log = repo.parent / "env.log"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    # A global `core.hooksPath` would shadow `.git/hooks`; pin this repository's own.
    _git(repo, "config", "core.hooksPath", str(hooks))
    tail = "sleep 8\nexit 1\n" if sleeps else "exit 0\n"
    hook = hooks / "pre-push"
    hook.write_text(
        "#!/bin/sh\n"
        "printf 'SKIP=%s REASON=%s\\n' "
        f'"${{PYFORGE_PREFLIGHT_SKIP-unset}}" "${{PYFORGE_PREFLIGHT_SKIP_REASON-unset}}" >> "{seen_log}"\n'
        'if [ "$PYFORGE_PREFLIGHT_SKIP" = "1" ]; then\n'
        f'  printf \'%s\\n\' "$PYFORGE_PREFLIGHT_SKIP_REASON" >> "{skip_log}"\n'
        "  exit 0\n"
        "fi\n" + tail,
        encoding="utf-8",
    )
    hook.chmod(0o755)
    return skip_log, seen_log


def _remote_main(remote: Path) -> str:
    return _git(remote, "rev-parse", "refs/heads/main").stdout.strip()


def _publish(
    vcs: GitVcs, repo: Path, *, writes=((_LEDGER_REL, _LEDGER_TEXT),), preflight_skip_reason: str | None = None
) -> str:
    return vcs.commit_paths_onto_remote_tip(
        repo,
        remote=VcsRef("origin"),
        ref=VcsRef("main"),
        writes=writes,
        message=to_redacted_text("marshal: promote sprint-status ledger for 'acme' (1 key(s) -> done)"),
        preflight_skip_reason=None if preflight_skip_reason is None else to_redacted_text(preflight_skip_reason),
    )


def test_a_publish_with_a_reason_outruns_a_preflight_that_would_time_out_the_push(vcs, repo, remote, monkeypatch):
    """AC 1: the push completes past a hook that sleeps beyond the push timeout, the remote's main
    holds the commit, and the hook logged a reason naming the sha, the ledger path and the story."""
    _publish_setup(repo, remote)
    skip_log, _seen = _install_pre_push_hook(repo, sleeps=True)
    monkeypatch.setattr(vcs_git_module, "_GIT_FETCH_TIMEOUT_S", _PUSH_TIMEOUT_S)

    sha = _publish(vcs, repo, preflight_skip_reason=_SKIP_REASON)

    assert _remote_main(remote) == sha
    [logged] = skip_log.read_text(encoding="utf-8").splitlines()
    assert sha in logged
    assert _LEDGER_REL in logged
    assert "story 64-1-a-landing" in logged
    # Never process-wide: the opt-out reached that one git process only.
    assert "PYFORGE_PREFLIGHT_SKIP" not in os.environ
    assert "PYFORGE_PREFLIGHT_SKIP_REASON" not in os.environ
    assert not any("marshal-promote-" in path for path in _worktree_paths(repo))


def test_a_publish_without_a_reason_still_runs_the_preflight_and_times_out(vcs, repo, remote, monkeypatch):
    """The 64.1 failure, reproduced: with no reason the push is what it always was -- the hook runs
    with no opt-out variable in its environment, outlasts the timeout, and the remote is untouched."""
    _publish_setup(repo, remote)
    skip_log, seen_log = _install_pre_push_hook(repo, sleeps=True)
    monkeypatch.setattr(vcs_git_module, "_GIT_FETCH_TIMEOUT_S", _PUSH_TIMEOUT_S)
    before = _remote_main(remote)

    with pytest.raises(VcsCommandError, match="timed out"):
        _publish(vcs, repo)

    assert _remote_main(remote) == before
    assert seen_log.read_text(encoding="utf-8").splitlines() == ["SKIP=unset REASON=unset"]
    assert not skip_log.exists()


def test_a_publish_without_a_reason_reaches_the_hook_with_no_opt_out_variables(vcs, repo, remote):
    """AC 3: no reason -> byte-identical push; neither opt-out variable reaches the hook."""
    _publish_setup(repo, remote)
    skip_log, seen_log = _install_pre_push_hook(repo, sleeps=False)

    sha = _publish(vcs, repo)

    assert _remote_main(remote) == sha
    assert seen_log.read_text(encoding="utf-8").splitlines() == ["SKIP=unset REASON=unset"]
    assert not skip_log.exists()


def test_a_publish_with_a_reason_but_no_env_utility_runs_the_preflight(vcs, repo, remote, monkeypatch):
    """I/O matrix, 'no env utility': the opt-out needs POSIX `env`; without it the push goes
    through the preflight -- slower, never unchecked."""
    _publish_setup(repo, remote)
    skip_log, seen_log = _install_pre_push_hook(repo, sleeps=False)
    real_which = shutil.which
    monkeypatch.setattr(
        vcs_git_module.shutil, "which", lambda name, *a, **k: None if name == "env" else real_which(name, *a, **k)
    )

    sha = _publish(vcs, repo, preflight_skip_reason=_SKIP_REASON)

    assert _remote_main(remote) == sha
    assert seen_log.read_text(encoding="utf-8").splitlines() == ["SKIP=unset REASON=unset"]
    assert not skip_log.exists()


@pytest.mark.parametrize(
    "bad_path",
    [
        "src/pyforge/marshal/cli/land.py",
        "_bmad-output/projects/acme/implementation-artifacts/sprint-status.yaml",
        "_bmad-output/projects/acme/planning-artifacts/../../../../escape.txt",
        "_bmad-output/projects/acme/planning-artifacts/./sprint-status-ledger.yaml",
        "_bmad-output/projects//planning-artifacts/sprint-status-ledger.yaml",
        "_bmad-output/projects/acme/planning-artifacts/",
        "_bmad-output/projects/acme/planning-artifacts",
        "/etc/planning-artifacts/x.yaml",
        "_bmad-output\\projects\\acme\\planning-artifacts\\x.yaml",
        "_bmad-output/projects/acme/planning-artifacts/tab\tname.yaml",
        "_bmad-output/projects/acme/planning-artifacts/line\nbreak.yaml",
        "_bmad-output/projects/acme/planning-artifacts/.git/config",
        "",
    ],
)
def test_a_reason_refuses_a_written_path_outside_planning_artifacts_before_any_fetch_or_write(
    vcs, repo, remote, monkeypatch, bad_path
):
    """AC 2 / I/O matrix 'path outside planning-artifacts': refused before any fetch, write or push
    -- a `../` path would otherwise be written before the post-commit check ever saw it."""
    _publish_setup(repo, remote)
    _skip_log, seen_log = _install_pre_push_hook(repo, sleeps=False)
    fetches: list[tuple] = []
    monkeypatch.setattr(GitVcs, "fetch", lambda self, *args: fetches.append(args))
    before = _remote_main(remote)

    with pytest.raises(VcsCommandError, match="planning-artifacts"):
        _publish(
            vcs,
            repo,
            writes=((_LEDGER_REL, _LEDGER_TEXT), (bad_path, "x\n")),
            preflight_skip_reason=_SKIP_REASON,
        )

    assert fetches == []
    assert _remote_main(remote) == before
    assert not seen_log.exists()
    assert not any("marshal-promote-" in path for path in _worktree_paths(repo))


@pytest.mark.parametrize("failing_step", ["mkdtemp", "write_text"])
def test_an_oserror_building_the_publish_worktree_is_a_vcs_command_error(vcs, repo, remote, monkeypatch, failing_step):
    """Story 68.1 review (AD-6): a full disk or a bad TMPDIR while the adapter makes its scratch directory or
    writes the files is a publish failure the caller journals as `MRS-LAND-011` -- never a raw `OSError` that
    crashes `_promote_sprint_ledger` with its INTENT unpaired. Nothing is pushed and no scratch worktree
    or directory is left behind."""
    _publish_setup(repo, remote)
    before = _remote_main(remote)
    written: list[Path] = []
    if failing_step == "mkdtemp":

        def failing_mkdtemp(*args, **kwargs):
            raise OSError(errno.ENOSPC, "No space left on device")

        monkeypatch.setattr(vcs_git_module.tempfile, "mkdtemp", failing_mkdtemp)
    else:
        real_write_text = Path.write_text

        def failing_write_text(self, *args, **kwargs):
            if "marshal-promote-" in str(self):
                written.append(self)
                raise OSError(errno.ENOSPC, "No space left on device")
            return real_write_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", failing_write_text)

    with pytest.raises(VcsCommandError, match="No space left on device") as excinfo:
        _publish(vcs, repo)

    assert isinstance(excinfo.value.__cause__, OSError)
    assert _remote_main(remote) == before
    assert not any("marshal-promote-" in path for path in _worktree_paths(repo))
    if failing_step == "write_text":
        [attempted] = written
        scratch = next(parent for parent in attempted.parents if parent.name.startswith("marshal-promote-"))
        assert not scratch.exists()


@pytest.mark.parametrize("empty", ["", "   ", "\n\t"])
def test_an_empty_reason_is_refused_never_a_blanket_skip(vcs, repo, remote, empty):
    _publish_setup(repo, remote)
    before = _remote_main(remote)

    with pytest.raises(VcsCommandError, match="reason is empty"):
        _publish(vcs, repo, preflight_skip_reason=empty)

    assert _remote_main(remote) == before


def _commit_everything(self, repo_root, paths, message):
    """A stand-in `commit_paths` that sweeps in whatever else is in the worktree -- the shape the
    adapter's post-commit path proof exists to catch (the real `commit_paths` commits only `paths`)."""
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-m", message.text)
    return _git(repo_root, "rev-parse", "HEAD").stdout.strip()


@pytest.mark.parametrize("stray", ["added", "deleted"])
def test_a_commit_naming_a_path_outside_the_written_set_is_refused_before_any_push(
    vcs, repo, remote, monkeypatch, stray
):
    """AC 2 / I/O matrix 'extra path in the commit': an added path and a deleted one both fail the
    proof; the remote's main is unchanged and the hook never ran (no push was attempted)."""
    _publish_setup(repo, remote)
    _skip_log, seen_log = _install_pre_push_hook(repo, sleeps=False)
    before = _remote_main(remote)

    def sneaky_commit(self, repo_root, paths, message):
        if stray == "added":
            (repo_root / "src").mkdir()
            (repo_root / "src" / "evil.py").write_text("print('evil')\n", encoding="utf-8")
        else:
            (repo_root / "README.md").unlink()
        return _commit_everything(self, repo_root, paths, message)

    monkeypatch.setattr(GitVcs, "commit_paths", sneaky_commit)

    with pytest.raises(VcsCommandError, match="outside the written set"):
        _publish(vcs, repo, preflight_skip_reason=_SKIP_REASON)

    assert _remote_main(remote) == before
    assert not seen_log.exists()
    assert not any("marshal-promote-" in path for path in _worktree_paths(repo))


def test_a_rename_pairing_cannot_hide_a_deleted_unwritten_file_behind_a_written_path(vcs, repo, remote, monkeypatch):
    """`git diff --name-only` pairs a deleted file with an added one of identical content as a rename and
    lists only the NEW name -- so without `--no-renames` a commit that deletes an unwritten tracked file
    while adding the written ledger path with the same bytes would pass the path proof. Both ends must be
    named: the deletion is refused and the remote's main is unchanged."""
    unwritten = "notes/old-ledger.yaml"
    (repo / "notes").mkdir()
    (repo / unwritten).write_text(_LEDGER_TEXT, encoding="utf-8")
    _git(repo, "add", unwritten)
    _git(repo, "commit", "-m", "an unrelated tracked file whose bytes equal the ledger's")
    _publish_setup(repo, remote)
    _skip_log, seen_log = _install_pre_push_hook(repo, sleeps=False)
    before = _remote_main(remote)

    def rename_shaped_commit(self, repo_root, paths, message):
        _git(repo_root, "rm", "-q", unwritten)
        return _commit_everything(self, repo_root, paths, message)

    monkeypatch.setattr(GitVcs, "commit_paths", rename_shaped_commit)

    with pytest.raises(VcsCommandError, match="outside the written set") as excinfo:
        _publish(vcs, repo, preflight_skip_reason=_SKIP_REASON)

    assert unwritten in str(excinfo.value)
    assert _remote_main(remote) == before
    assert not seen_log.exists()
    assert not any("marshal-promote-" in path for path in _worktree_paths(repo))


def test_the_same_extra_path_commit_is_not_judged_without_a_reason(vcs, repo, remote, monkeypatch):
    """With no reason the adapter makes no claim about the commit's paths -- the proof belongs to the
    opt-out, and the push is unchanged (the hook decides)."""
    _publish_setup(repo, remote)
    _install_pre_push_hook(repo, sleeps=False)

    def sneaky_commit(self, repo_root, paths, message):
        (repo_root / "extra.txt").write_text("extra\n", encoding="utf-8")
        return _commit_everything(self, repo_root, paths, message)

    monkeypatch.setattr(GitVcs, "commit_paths", sneaky_commit)

    sha = _publish(vcs, repo)

    assert _remote_main(remote) == sha


def test_a_reason_is_one_line_however_the_caller_wrote_it(vcs, repo, remote):
    """The hook's skip journal is tab-separated, one line per push -- no tab or newline survives."""
    _publish_setup(repo, remote)
    skip_log, _seen = _install_pre_push_hook(repo, sleeps=False)

    sha = _publish(vcs, repo, preflight_skip_reason="story 64-1\tpromoted\nby marshal\r\n\x07")

    text = skip_log.read_text(encoding="utf-8")
    assert text.count("\n") == 1
    assert "\t" not in text
    assert "\r" not in text
    assert sha in text
    assert "story 64-1 promoted by marshal" in text


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml", True),
        ("_bmad-output/projects/acme/planning-artifacts/specs/spec-1-1.md", True),
        ("_bmad-output/projects/acme/planning-artifacts/deferred-work-ledger.md", True),
        ("_bmad-output/projects/acme/planning-artifacts", False),
        ("_bmad-output/projects/acme/planning-artifacts/", False),
        ("_bmad-output/projects/acme/implementation-artifacts/x.md", False),
        ("_bmad-output/projects/../planning-artifacts/x.md", False),
        ("_bmad-output/projects/./planning-artifacts/x.md", False),
        ("_bmad-output/planning-artifacts/x.md", False),
        ("_bmad-output/projects/acme/planning-artifacts/../x.md", False),
        ("./_bmad-output/projects/acme/planning-artifacts/x.md", False),
        ("/_bmad-output/projects/acme/planning-artifacts/x.md", False),
        ("_bmad-output/projects/acme/planning-artifacts/x.md\x00", False),
        ("_bmad-output/projects/acme/planning-artifacts/.GIT/x", False),
        ("src/planning-artifacts/x.md", False),
        ("", False),
    ],
)
def test_is_planning_artifact_path(rel, expected):
    assert vcs_git_module._is_planning_artifact_path(rel) is expected


# --- merge_tree_write / add_worktree_for_tree (Story 51.1) --------------------
#
# Review finding (2026-09-19): these two methods -- the actual git mechanics
# this story's whole fix depends on -- had no real-git coverage at all, only
# a hand-rolled fake in test_dispatch_landing.py. Added here to match this
# module's own established convention (add_worktree, is_branch_merged) of
# testing GitVcs against real temp git repos.


def test_merge_tree_write_returns_tree_oid_for_a_clean_merge(vcs, repo):
    _git(repo, "checkout", "-b", "feature/clean")
    (repo / "feature.txt").write_text("feature content\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "add feature.txt")
    _git(repo, "checkout", "main")
    (repo / "main-only.txt").write_text("main content\n", encoding="utf-8")
    _git(repo, "add", "main-only.txt")
    _git(repo, "commit", "-m", "add main-only.txt")

    tree_oid = vcs.merge_tree_write(repo, "main", "feature/clean")

    assert tree_oid is not None
    assert _git(repo, "cat-file", "-t", tree_oid).stdout.strip() == "tree"
    names = _git(repo, "ls-tree", "-r", "--name-only", tree_oid).stdout.split()
    assert "feature.txt" in names
    assert "main-only.txt" in names


def test_merge_tree_write_returns_none_on_a_real_conflict(vcs, repo):
    _git(repo, "commit", "--allow-empty", "-m", "checkpoint")
    base_sha = _git(repo, "rev-parse", "HEAD~1").stdout.strip()
    (repo / "README.md").write_text("main version\n", encoding="utf-8")
    _git(repo, "commit", "-am", "main edits README")
    _git(repo, "checkout", "-b", "feature/conflict", base_sha)
    (repo / "README.md").write_text("feature version\n", encoding="utf-8")
    _git(repo, "commit", "-am", "feature edits README")

    assert vcs.merge_tree_write(repo, "main", "feature/conflict") is None


def test_add_worktree_for_tree_checks_out_the_merged_content(vcs, repo, tmp_path):
    _git(repo, "checkout", "-b", "feature/clean")
    (repo / "feature.txt").write_text("feature content\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "add feature.txt")
    feature_sha = _git(repo, "rev-parse", "feature/clean").stdout.strip()
    _git(repo, "checkout", "main")
    (repo / "main-only.txt").write_text("main content\n", encoding="utf-8")
    _git(repo, "add", "main-only.txt")
    _git(repo, "commit", "-m", "add main-only.txt")

    tree_oid = vcs.merge_tree_write(repo, "main", "feature/clean")
    assert tree_oid is not None

    home = tmp_path / "merge-tree-preview-home"
    vcs.add_worktree_for_tree(repo, home, tree_oid, parent=feature_sha)

    assert (home / "feature.txt").read_text(encoding="utf-8") == "feature content\n"
    assert (home / "main-only.txt").read_text(encoding="utf-8") == "main content\n"
    assert any("merge-tree-preview-home" in path for path in _worktree_paths(repo))

    # the synthetic wrapper commit is never referenced by any branch or tag.
    synthetic_sha = _git(home, "rev-parse", "HEAD").stdout.strip()
    assert synthetic_sha != feature_sha
    contains = _git(repo, "for-each-ref", "--contains", synthetic_sha)
    assert contains.stdout.strip() == ""

    vcs.remove_worktree(repo, home, force=True)
    assert not any("merge-tree-preview-home" in path for path in _worktree_paths(repo))


def test_add_worktree_for_tree_raises_vcs_command_error_on_an_unresolvable_parent(vcs, repo, tmp_path):
    tree_oid = _git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
    home = tmp_path / "merge-tree-preview-home"
    with pytest.raises(VcsCommandError):
        vcs.add_worktree_for_tree(repo, home, tree_oid, parent="no-such-ref")


def test_merge_tree_preview_two_parent_commit_scopes_changed_files_to_the_branch(
    vcs, repo, tmp_path
) -> None:
    """Story 83.12: GitHub-style merge parents so ``origin/main...HEAD`` is the story diff."""
    from pyforge.marshal.dispatch_verify import coverage_gate_commands_for_changed_files

    _git(repo, "checkout", "-b", "feature/scribe")
    scribe_rel = "src/shared/packages/pyforge-scribe/src/pyforge/scribe/story_only.py"
    scribe_path = repo / scribe_rel
    scribe_path.parent.mkdir(parents=True, exist_ok=True)
    scribe_path.write_text("# story\n", encoding="utf-8")
    _git(repo, "add", scribe_rel)
    _git(repo, "commit", "-m", "scribe story change")
    feature_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()

    _git(repo, "checkout", "main")
    doctor_rel = "src/shared/packages/pyforge-doctor/src/pyforge/doctor/main_only.py"
    doctor_path = repo / doctor_rel
    doctor_path.parent.mkdir(parents=True, exist_ok=True)
    doctor_path.write_text("# main\n", encoding="utf-8")
    _git(repo, "add", doctor_rel)
    _git(repo, "commit", "-m", "main-only doctor change")
    main_sha = _git(repo, "rev-parse", "main").stdout.strip()

    tree_oid = vcs.merge_tree_write(repo, "main", feature_sha)
    assert tree_oid is not None

    home = tmp_path / "merge-tree-preview-two-parent"
    vcs.add_worktree_for_tree(repo, home, tree_oid, parent=main_sha, second_parent=feature_sha)

    changed = vcs.changed_files(repo, home, base="main")
    assert scribe_rel in changed
    assert doctor_rel not in changed
    assert coverage_gate_commands_for_changed_files(changed) == (
        "pixi run --frozen -e pyforge-scribe pyforge-scribe-coverage-gate",
    )

    vcs.remove_worktree(repo, home, force=True)


# --- Story 82.9 (DW-FU-2-6-4): commit text is declared egress ------------------
#
# `CommitPort` is classified egress (AD-34): the message is `Redacted`, every other text
# parameter a `VcsRef`, and `GitVcs` refuses anything else with a `TypeError` BEFORE any git
# invocation -- the type only, never the value. Real git throughout: what is asserted is what
# `git log` stores.

_SECRET = "ghp_" + "a" * 36
_REDACTED = "***REDACTED***"


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _stored_message(repo: Path, sha: str) -> str:
    return _git(repo, "log", "-1", "--format=%B", sha).stdout


def test_commit_paths_stores_the_redacted_form_of_a_token_shaped_message(vcs, repo):
    (repo / "promoted.txt").write_text("promoted\n", encoding="utf-8")

    sha = vcs.commit_paths(repo, (repo / "promoted.txt",), to_redacted_text(f"marshal: carry {_SECRET} forward"))

    stored = _stored_message(repo, sha)
    assert _REDACTED in stored
    assert _SECRET not in stored
    assert "ghp_" not in stored


def test_merge_ref_resolving_stores_the_redacted_form_of_a_token_shaped_message(vcs, repo):
    _conflicting_branch(repo)
    _git(repo, "checkout", "-q", "-b", "readme-only", "feature/conflict~1")
    (repo / "README.md").write_text("readme-only version\n", encoding="utf-8")
    _git(repo, "commit", "-am", "only README differs")

    sha = vcs.merge_ref_resolving(
        repo,
        VcsRef("main"),
        resolutions={"README.md": "resolved\n"},
        message=to_redacted_text(f"union heal {_SECRET}"),
    )

    stored = _stored_message(repo, sha)
    assert _REDACTED in stored
    assert _SECRET not in stored


def test_commit_paths_onto_remote_tip_stores_the_redacted_form_of_a_token_shaped_message(vcs, repo, remote):
    _publish_setup(repo, remote)

    sha = _publish_text(vcs, repo, f"marshal: promote {_SECRET}")

    stored = _stored_message(repo, sha)
    assert _REDACTED in stored
    assert _SECRET not in stored
    assert _SECRET not in _git(remote, "log", "-1", "--format=%B", "main").stdout


def _publish_text(vcs: GitVcs, repo: Path, text: str) -> str:
    return vcs.commit_paths_onto_remote_tip(
        repo,
        remote=VcsRef("origin"),
        ref=VcsRef("main"),
        writes=((_LEDGER_REL, _LEDGER_TEXT),),
        message=to_redacted_text(text),
    )


def test_commit_paths_rejects_a_bare_str_message_and_commits_nothing(vcs, repo):
    (repo / "promoted.txt").write_text("promoted\n", encoding="utf-8")
    before = _head(repo)

    with pytest.raises(TypeError, match="message must be a Redacted") as excinfo:
        vcs.commit_paths(repo, (repo / "promoted.txt",), f"carry {_SECRET}")  # type: ignore[arg-type]

    assert _SECRET not in str(excinfo.value)  # the type only, never the value
    assert _head(repo) == before
    assert "promoted.txt" not in _git(repo, "ls-files").stdout  # refused before `git add`


def test_merge_ref_resolving_rejects_a_bare_str_message_and_a_bare_str_ref(vcs, repo):
    _conflicting_branch(repo)
    before = _head(repo)

    with pytest.raises(TypeError, match="message must be a Redacted") as excinfo:
        vcs.merge_ref_resolving(repo, VcsRef("main"), resolutions={}, message=f"heal {_SECRET}")  # type: ignore[arg-type]
    assert _SECRET not in str(excinfo.value)
    with pytest.raises(TypeError, match="ref must be a VcsRef"):
        vcs.merge_ref_resolving(repo, "main", resolutions={}, message=to_redacted_text("heal"))  # type: ignore[arg-type]

    assert _head(repo) == before
    assert not (repo / ".git" / "MERGE_HEAD").exists()  # refused before any merge started


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"message": "plain"}, "message must be a Redacted"),
        ({"preflight_skip_reason": "plain"}, "preflight_skip_reason must be a Redacted"),
        ({"remote": "origin"}, "remote must be a VcsRef"),
        ({"ref": "main"}, "ref must be a VcsRef"),
    ],
)
def test_commit_paths_onto_remote_tip_rejects_a_bare_str_for_every_text_parameter(vcs, repo, remote, override, match):
    _publish_setup(repo, remote)
    before = _git(remote, "rev-parse", "main").stdout.strip()
    kwargs = {
        "remote": VcsRef("origin"),
        "ref": VcsRef("main"),
        "writes": ((_LEDGER_REL, _LEDGER_TEXT),),
        "message": to_redacted_text("marshal: promote"),
        **override,
    }

    with pytest.raises(TypeError, match=match):
        vcs.commit_paths_onto_remote_tip(repo, **kwargs)

    assert _git(remote, "rev-parse", "main").stdout.strip() == before
    assert not any("marshal-promote-" in path for path in _worktree_paths(repo))  # no scratch worktree was made


def test_a_vcs_ref_is_a_non_empty_str():
    assert VcsRef("origin").value == "origin"
    for bad in ("", None, 3):
        with pytest.raises(ValueError, match="non-empty str"):
            VcsRef(bad)  # type: ignore[arg-type]


def test_to_redacted_text_redacts_shape_and_rejects_a_non_str():
    wrapped = to_redacted_text(f"a {_SECRET} b")
    assert wrapped.text == f"a {_REDACTED} b"
    assert to_redacted_text("nothing secret here").text == "nothing secret here"
    with pytest.raises(TypeError, match="text must be a str, got bytes") as excinfo:
        to_redacted_text(b"secret-bytes")  # type: ignore[arg-type]
    assert "secret-bytes" not in str(excinfo.value)  # the type only, never the value


def test_the_worktree_checkpoint_call_site_commits_the_redacted_form_of_its_story_key(vcs, repo):
    """The call-site half of the acceptance criterion: `commit_worktree_checkpoint` builds its subject
    from a caller-supplied story key and routes it through `to_redacted_text` itself, so a credential
    in the key never reaches `git log`. Reverting the wrap makes `CommitPort` refuse the bare `str`
    (a `TypeError` the checkpoint reports as skipped), so `committed` is `False` and this fails."""
    from pyforge.marshal.core.worktree_checkpoint import commit_worktree_checkpoint

    (repo / "wip.txt").write_text("work in progress\n", encoding="utf-8")

    result = commit_worktree_checkpoint(vcs, repo_root=repo, worktree=repo, story_key=f"82.9 {_SECRET}")

    assert result.committed is True, result.skipped_reason
    stored = _stored_message(repo, result.head_sha)
    assert _REDACTED in stored
    assert _SECRET not in stored
