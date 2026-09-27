"""Story 61.1 (CAP-271): every local-branch read names the full ref.

The meta test pins that no git read receives a bare local branch name; the fakes in the call
sites' own tests pin each argument. These real-git tests show what that buys, per git operation
those call sites make: with a tag named like the branch on another commit, ``refs/heads/<branch>``
still reads the branch -- and each records what the short name did instead (a warning and the
tag's commit, or an outright "ambiguous" refusal). The heal tests drive the landing heal end to
end, since it reads the dispatch branch four ways and then pushes ``main``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.core.refs import ORIGIN_MAIN, local_branch_ref
from pyforge.marshal.dispatch_land_heal import DispatchLandHealResult, try_heal_dispatch_land_merge
from pyforge.marshal.ports.forge import ForgeCommandError, PrInfo

_HEAD = "dispatch/pyforge-marshal/61.1"
_LEDGER = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"


def test_local_branch_ref_is_the_full_refname() -> None:
    assert local_branch_ref("main") == "refs/heads/main"
    assert local_branch_ref("loop/pyforge-marshal") == "refs/heads/loop/pyforge-marshal"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], check=check, capture_output=True, text=True)


def _commit(repo: Path, name: str, message: str) -> str:
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(f"{message}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    """A clone of a bare remote: `main` at `landed` (pushed), a tag named `main` on `base`
    (one commit older). Returns (remote, clone, base, landed)."""
    remote, clone = tmp_path / "remote.git", tmp_path / "clone"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True, capture_output=True)
    _git(clone, "config", "user.email", "t@example.com")
    _git(clone, "config", "user.name", "T")
    base = _commit(clone, "README.md", "base")
    landed = _commit(clone, "landed.txt", "Merge 60.1 into main")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "tag", "main", base)  # the trap
    return remote, clone, base, landed


def test_the_landing_subjects_read_the_branch_not_the_tag(repo) -> None:
    """status / deploy / retire / dispatch land classify landings from these subjects: the tag's
    history is missing the landing, so a landed story read as not landed."""
    _remote, clone, _base, _landed = repo
    vcs = GitVcs()

    assert vcs.commit_subjects(clone, "main") == ("base",)  # the trap, for the record
    assert vcs.commit_subjects(clone, local_branch_ref("main")) == ("Merge 60.1 into main", "base")


def test_a_branch_minted_from_main_starts_at_the_branch_tip(repo, tmp_path: Path) -> None:
    """init, the loop-home adapter and dispatch mint a branch from `main`."""
    _remote, clone, _base, landed = repo
    vcs = GitVcs()

    with pytest.raises(VcsCommandError, match="ambiguous"):  # the trap: the mint refuses outright
        vcs.add_worktree(clone, tmp_path / "short", "loop/short", base="main")
    vcs.add_worktree(clone, tmp_path / "home", "loop/acme", base=local_branch_ref("main"))

    assert _git(tmp_path / "home", "rev-parse", "HEAD").stdout.strip() == landed
    assert _git(tmp_path / "home", "branch", "--show-current").stdout.strip() == "loop/acme"
    assert _git(clone, "rev-parse", "--abbrev-ref", "loop/acme@{upstream}", check=False).returncode != 0  # no-track


def test_the_scope_diff_and_merge_base_read_the_branch(repo, tmp_path: Path) -> None:
    """The gate's scope check and deploy's / land's changed files diff `base...HEAD`: against the
    tag, main's own landed commit reads as the home's change -- a scope violation it never made."""
    _remote, clone, base, landed = repo
    home = tmp_path / "home"
    _git(clone, "worktree", "add", "-q", "-b", "loop/acme", str(home), local_branch_ref("main"))
    _git(home, "config", "user.email", "t@example.com")
    _commit(home, "work.txt", "the story's work")
    vcs = GitVcs()

    assert vcs.changed_files(clone, home, base="main") == ("landed.txt", "work.txt")  # the trap
    assert vcs.changed_files(clone, home, base=local_branch_ref("main")) == ("work.txt",)
    assert vcs.merge_base(clone, "loop/acme", "main") == base  # the trap
    assert vcs.merge_base(clone, local_branch_ref("loop/acme"), local_branch_ref("main")) == landed


def test_a_push_succeeds_beside_a_tag_named_like_the_branch(repo) -> None:
    """The local-main advance pushes `main` by name; with a tag `main`, git refused the bare
    source as ambiguous. `<branch>@{upstream}` still resolves by the bare name."""
    remote, clone, _base, _landed = repo
    tip = _commit(clone, "next.txt", "next")

    assert "matches more than one" in _git(clone, "push", "origin", "main:main", check=False).stderr  # the trap
    GitVcs().push(clone, "main")

    assert _git(remote, "rev-parse", "refs/heads/main").stdout.strip() == tip


# --- the landing heal, end to end ------------------------------------------------------------------


class _Forge:
    """GitHub says DIRTY (stale mergeability) and merges only a clean `merge-tree` of the pushed
    head into the remote's main -- what the heal's two paths each end in."""

    def __init__(self, clone: Path, state: str) -> None:
        self.clone, self.state, self.merge_calls, self.closed = clone, state, 0, []

    def pr_merge_state(self, _repo, _number):
        return self.state

    def merge_pr(self, _repo, _number, _strategy, *, expected_head_sha, delete_branch, subject):
        self.merge_calls += 1
        _git(self.clone, "fetch", "-q", "origin")
        clean = _git(self.clone, "merge-tree", "--write-tree", ORIGIN_MAIN, f"refs/remotes/origin/{_HEAD}", check=False)
        if clean.returncode != 0:
            raise ForgeCommandError("Pull request is not mergeable")

    def close_pr(self, _repo, number):
        self.closed.append(number)


def _landing(tmp_path: Path, *, main_ledger: str | None, branch_ledger: str | None) -> tuple[Path, Path, Path, str]:
    """A bare remote, a clone and a dispatch worktree on `_HEAD` (pushed), main moved on (pushed),
    and the trap: a tag named `main` and a tag named `_HEAD`, both on the base commit.
    Returns (remote, clone, worktree, base)."""
    remote, clone, wt = tmp_path / "remote.git", tmp_path / "clone", tmp_path / "wt"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True, capture_output=True)
    _git(clone, "config", "user.email", "t@example.com")
    _git(clone, "config", "user.name", "T")
    ledger = clone / _LEDGER
    ledger.parent.mkdir(parents=True)
    ledger.write_text("development_status:\n  60-1-a: done\n", encoding="utf-8")
    base = _commit(clone, "README.md", "base")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "worktree", "add", "-q", "-b", _HEAD, str(wt), local_branch_ref("main"))
    if branch_ledger is not None:
        (wt / _LEDGER).write_text(branch_ledger, encoding="utf-8")
    _commit(wt, "story.txt", "the story's work")
    _git(wt, "push", "-q", "-u", "origin", _HEAD)
    if main_ledger is not None:
        ledger.write_text(main_ledger, encoding="utf-8")
    _commit(clone, "main.txt", "main moves on")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")
    _git(clone, "tag", "main", base)
    _git(clone, "tag", _HEAD, base)
    return remote, clone, wt, base


def _heal(clone: Path, wt: Path, forge: _Forge) -> DispatchLandHealResult:
    return try_heal_dispatch_land_merge(
        project_slug="pyforge-marshal",
        git_repo_root=clone,
        worktree=wt,
        base="main",
        head_branch=_HEAD,
        head_sha="unused",
        subject="Merge 61.1 into main",
        merge_strategy="merge",
        delete_branch=False,
        repo_ref=type("R", (), {"value": "rxm7706/local-recipes"})(),
        pr=PrInfo(number=61, url="https://example/pr/61", state="open", base="main"),
        fs=None,
        vcs=GitVcs(),
        forge=forge,
        probe_ref=ORIGIN_MAIN,
    )


def test_the_local_main_advance_merges_the_branch_and_pushes_beside_both_tags(tmp_path: Path) -> None:
    """No conflict and a stale DIRTY state: the heal merges the dispatch branch into `main` and
    pushes it. The bare names merged the tag (the base -- nothing) and could not push at all."""
    remote, clone, _wt, _base = _landing(tmp_path, main_ledger=None, branch_ledger=None)
    forge = _Forge(clone, "DIRTY")

    assert _heal(clone, _wt, forge) == DispatchLandHealResult(healed=True, landed_via_local_merge=True)
    files = _git(remote, "ls-tree", "--name-only", "refs/heads/main").stdout.split()
    assert "story.txt" in files and "main.txt" in files
    assert forge.closed == [61]


def test_the_union_heal_reads_the_branchs_ledger_beside_a_tag_named_like_it(tmp_path: Path) -> None:
    """A ledger-only conflict: the heal must see it (the tag on the base shows none), read the
    branch's ledger (the tag's is the base's) and merge the remote's main into the branch."""
    remote, clone, wt, _base = _landing(
        tmp_path,
        main_ledger="development_status:\n  60-1-a: done\n  61-2-x: backlog\n",
        branch_ledger="development_status:\n  60-1-a: done\n  61-1-y: done\n",
    )
    forge = _Forge(clone, "CONFLICTING")

    assert _heal(clone, wt, forge) == DispatchLandHealResult(healed=True, retried_forge_merge=True)
    ledger = _git(remote, "show", f"refs/heads/{_HEAD}:{_LEDGER}").stdout
    assert "61-2-x: backlog" in ledger and "61-1-y: done" in ledger
