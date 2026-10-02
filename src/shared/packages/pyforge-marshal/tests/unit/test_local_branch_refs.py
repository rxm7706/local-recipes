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
from pyforge.marshal.core.egress import to_redacted_text
from pyforge.marshal.core.refs import ORIGIN_MAIN, local_branch_ref
from pyforge.marshal.dispatch_land_heal import DispatchLandHealResult, try_heal_dispatch_land_merge
from pyforge.marshal.ports.commit import VcsRef
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


@pytest.mark.parametrize("upstream", [True, False])
def test_a_push_succeeds_beside_a_tag_on_the_remote_named_like_the_branch(repo, upstream: bool) -> None:
    """Review 1: a bare destination was ambiguous once the REMOTE carried a same-named tag (a
    `git push --tags` puts one there), with or without a configured upstream."""
    remote, clone, base, _landed = repo
    _git(clone, "checkout", "-q", "-b", "loop/acme")
    _git(clone, "push", "-q", "origin", "refs/heads/loop/acme:refs/heads/loop/acme")
    _git(clone, "push", "-q", "origin", f"{base}:refs/tags/loop/acme")  # the remote's tag
    if upstream:
        _git(clone, "branch", "-q", "--set-upstream-to=origin/loop/acme", "loop/acme")
    tip = _commit(clone, "story.txt", "the story's work")

    assert (
        "matches more than one" in _git(clone, "push", "origin", "refs/heads/loop/acme:loop/acme", check=False).stderr
    )
    GitVcs().push(clone, "loop/acme")

    assert _git(remote, "rev-parse", "refs/heads/loop/acme").stdout.strip() == tip
    assert _git(remote, "rev-parse", "refs/tags/loop/acme").stdout.strip() == base  # the tag untouched


def _remote_moves_on_beside_a_remote_tag_main(remote: Path, clone: Path, base: str, tmp_path: Path) -> str:
    """Another clone lands a commit on the remote's `main`; the remote also carries a tag `main`
    on `base`. Returns the remote's new tip (not yet fetched into `clone`)."""
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(remote), str(other)], check=True, capture_output=True)
    _git(other, "config", "user.email", "t@example.com")
    _git(other, "config", "user.name", "T")
    tip = _commit(other, "elsewhere.txt", "landed elsewhere")
    _git(other, "push", "-q", "origin", "refs/heads/main:refs/heads/main", f"{base}:refs/tags/main")
    return tip


def test_a_fetch_updates_the_remote_tracking_ref_beside_a_tag_on_the_remote_named_main(repo, tmp_path) -> None:
    """Review 2: the remote resolved the short source `main` to its TAG, which landed in FETCH_HEAD
    only -- the fetch exited 0 and `refs/remotes/origin/main` stayed stale."""
    remote, clone, base, landed = repo
    tip = _remote_moves_on_beside_a_remote_tag_main(remote, clone, base, tmp_path)

    _git(clone, "fetch", "-q", "origin", "main")  # the trap, for the record
    assert _git(clone, "rev-parse", ORIGIN_MAIN).stdout.strip() == landed  # stale
    GitVcs().fetch(clone, "origin", "main")

    assert _git(clone, "rev-parse", ORIGIN_MAIN).stdout.strip() == tip


def test_the_ledger_publish_lands_beside_a_tag_on_the_remote_named_main(repo, tmp_path) -> None:
    """The promotion publish fetches, builds on the tracking ref and pushes: on the stale ref every
    push was rejected as a non-fast-forward, so no promotion ever landed."""
    remote, clone, base, _landed = repo
    tip = _remote_moves_on_beside_a_remote_tag_main(remote, clone, base, tmp_path)

    GitVcs().commit_paths_onto_remote_tip(
        clone,
        remote=VcsRef("origin"),
        ref=VcsRef("main"),
        writes=(("ledger.yaml", "development_status: {}\n"),),
        message=to_redacted_text("promote"),
    )

    assert _git(remote, "rev-parse", "refs/heads/main^").stdout.strip() == tip
    assert _git(remote, "show", "refs/heads/main:ledger.yaml").stdout.strip() == "development_status: {}"


def test_a_push_reads_its_upstream_beside_a_local_origin_branch_shadow(repo) -> None:
    """Review 2: with a local tag named `origin/loop/acme`, `--abbrev-ref <b>@{upstream}` answered
    `remotes/origin/loop/acme` and the push went to a remote called `remotes`."""
    remote, clone, base, _landed = repo
    _git(clone, "checkout", "-q", "-b", "loop/acme")
    _git(clone, "push", "-q", "-u", "origin", "refs/heads/loop/acme:refs/heads/loop/acme")
    _git(clone, "tag", "origin/loop/acme", base)  # the Story 60.1-class shadow
    tip = _commit(clone, "story.txt", "the story's work")

    assert _git(clone, "rev-parse", "--abbrev-ref", "loop/acme@{upstream}").stdout.strip() == "remotes/origin/loop/acme"
    GitVcs().push(clone, "loop/acme")

    assert _git(remote, "rev-parse", "refs/heads/loop/acme").stdout.strip() == tip


@pytest.mark.parametrize("layout", ["custom-tracking-namespace", "remote-name-with-a-slash"])
def test_a_push_takes_its_target_from_the_branch_config(repo, layout: str) -> None:
    """Review 3: parsing the tracking ref's name refused a fetch refspec mapping outside
    `refs/remotes/` (which `--abbrev-ref` had pushed fine), and split a remote named `foo/bar`
    at its slash. The branch's own config names both exactly."""
    remote, clone, _base, _landed = repo
    name = "origin" if layout == "custom-tracking-namespace" else "foo/bar"
    if layout == "custom-tracking-namespace":
        _git(clone, "config", "remote.origin.fetch", "+refs/heads/*:refs/origin/*")
    else:
        _git(clone, "remote", "add", name, str(remote))
    _git(clone, "fetch", "-q", name)
    _git(clone, "checkout", "-q", "-b", "loop/acme")
    _git(clone, "push", "-q", name, "refs/heads/loop/acme:refs/heads/loop/acme")
    _git(clone, "fetch", "-q", name)
    _git(clone, "config", "branch.loop/acme.remote", name)
    _git(clone, "config", "branch.loop/acme.merge", "refs/heads/loop/acme")
    tip = _commit(clone, "story.txt", "the story's work")

    GitVcs().push(clone, "loop/acme")

    assert _git(remote, "rev-parse", "refs/heads/loop/acme").stdout.strip() == tip


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
