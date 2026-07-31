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


def test_has_uncommitted_changes_true_for_untracked_file_despite_local_config_hiding_it(
    vcs, repo
):
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
    assert show.stdout.count("\nparent ") + (
        1 if show.stdout.startswith("parent ") else 0
    ) == 1
    # Confirms bare ancestry really would misreport this as unmerged.
    ancestry = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", "loop/squash", "main"],
        capture_output=True,
    )
    assert ancestry.returncode != 0

    assert vcs.is_branch_merged(repo, "loop/squash", into="main") is True


def test_is_branch_merged_true_for_a_squash_merge_even_after_main_advances_further(
    vcs, repo
):
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


def test_is_branch_merged_commit_tree_call_never_depends_on_global_git_identity(
    vcs, tmp_path, monkeypatch
):
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
    assert (
        vcs.is_branch_merged(no_identity_repo, "loop/noidentity", into="main") is False
    )


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


def test_delete_branch_force_removes_a_squash_merged_branch_plain_d_would_refuse(
    vcs, repo
):
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
