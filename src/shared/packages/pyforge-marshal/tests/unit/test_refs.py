"""Story 60.1 (CAP-270): every remote-tracking read names the full ref.

``test_every_call_site_reads_the_full_ref`` pins that each call site takes its ref from
``core/refs.py``; the meta test pins that no module spells a short one. The real-git tests show
what that buys, per git operation those call sites make: with a local branch or tag named
``origin/main`` on another commit, the full refname still reaches the remote's tip -- and each
also records what the short name would have done. The publish test drives the adapter method
(``commit_paths_onto_remote_tip``) that was itself a short-name call site until review 1, and
pushed a shadow's commit onto the remote's ``main``.
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal import dispatch_land, dispatch_verify
from pyforge.marshal.adapters import vcs_git
from pyforge.marshal.adapters.vcs_git import GitVcs
from pyforge.marshal.cli import deploy as cli_deploy
from pyforge.marshal.cli import dispatch as cli_dispatch
from pyforge.marshal.core import dispatch as core_dispatch
from pyforge.marshal.core.egress import to_redacted_text
from pyforge.marshal.core.refs import ORIGIN_MAIN, ORIGIN_MAIN_SHORT, display_ref, remote_tracking_ref
from pyforge.marshal.dispatch_supervisor import __main__ as dispatch_supervisor
from pyforge.marshal.ports.commit import VcsRef


def test_remote_tracking_ref_is_the_full_refname() -> None:
    assert remote_tracking_ref("main") == "refs/remotes/origin/main"
    assert remote_tracking_ref("release", remote="upstream") == "refs/remotes/upstream/release"
    assert ORIGIN_MAIN == "refs/remotes/origin/main"
    assert ORIGIN_MAIN_SHORT == display_ref("main") == "origin/main"


def test_every_call_site_reads_the_full_ref() -> None:
    assert dispatch_verify._SCOPE_BASE == ORIGIN_MAIN
    assert dispatch_land._ORIGIN_MAIN == ORIGIN_MAIN
    assert dispatch_supervisor._BASE_REF == ORIGIN_MAIN
    assert cli_dispatch._BASE_REF == ORIGIN_MAIN
    assert cli_deploy._PUSH_REF == ORIGIN_MAIN
    assert vcs_git._ORIGIN_MAIN_REF == ORIGIN_MAIN
    assert inspect.signature(core_dispatch.spec_text_at_ref).parameters["ref"].default == ORIGIN_MAIN


# --- real git: a local `origin/main` shadow no longer steers what marshal reads ---------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _commit(repo: Path, name: str, message: str) -> str:
    (repo / name).write_text(f"{message}\n", encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, Path]:
    """A clone of a bare remote with one base commit pushed. Returns (remote, clone)."""
    remote, clone = tmp_path / "remote.git", tmp_path / "clone"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True, capture_output=True)
    _git(clone, "config", "user.email", "t@example.com")
    _git(clone, "config", "user.name", "T")
    _commit(clone, "README.md", "base")
    _git(clone, "push", "-q", "origin", "main")
    return remote, clone


def _shadow(clone: Path, on: str, *, kind: str = "branch") -> str:
    """The trap: a LOCAL branch (or tag) named `origin/main`, on an unverified commit built on `on`."""
    _git(clone, "checkout", "-q", "--detach", on)
    shadow = _commit(clone, "unverified.txt", "unverified, never pushed")
    _git(clone, kind, "origin/main", shadow)
    _git(clone, "checkout", "-q", "main")
    return shadow


def test_the_scope_diff_sees_the_homes_work_despite_a_shadow_on_top_of_it(repo, tmp_path: Path) -> None:
    """Dispatch verify's scope check diffs `base...HEAD`. A shadow built on the home's own work
    makes the short name's diff EMPTY -- every out-of-scope file invisible; the full ref sees it."""
    _remote, clone = repo
    home = tmp_path / "home"
    _git(clone, "worktree", "add", "-q", "-b", "dispatch/acme/1.1", str(home), "main")
    _git(home, "config", "user.email", "t@example.com")
    work = _commit(home, "out-of-scope.txt", "the story's work")
    _shadow(clone, work)
    vcs = GitVcs()

    assert vcs.changed_files(clone, home, base="origin/main") == ()  # the trap, for the record
    assert vcs.changed_files(clone, home, base=ORIGIN_MAIN) == ("out-of-scope.txt",)


def test_the_behind_count_and_merge_preview_use_the_remote_tip(repo, tmp_path: Path) -> None:
    """A shadow sitting where the home already is: the short name counts 0 behind (the stale
    home looks current) and previews a merge without the remote's commit."""
    _remote, clone = repo
    home = tmp_path / "home"
    _git(clone, "worktree", "add", "-q", "-b", "dispatch/acme/1.2", str(home), "main")
    base = _git(clone, "rev-parse", "main")
    _commit(clone, "landed.txt", "landed on the remote")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")
    _git(clone, "branch", "origin/main", base)  # the shadow: where the home already is
    vcs = GitVcs()

    assert vcs.commits_behind(home, "origin/main") == 0  # the trap, for the record
    assert vcs.commits_behind(home, ORIGIN_MAIN) == 1
    tree = vcs.merge_tree_write(clone, ORIGIN_MAIN, "dispatch/acme/1.2")
    assert "landed.txt" in _git(clone, "ls-tree", "--name-only", str(tree)).split()


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_a_loop_home_fast_forwards_to_the_remote_tip_not_the_shadow(repo, tmp_path: Path, kind: str) -> None:
    _remote, clone = repo
    home = tmp_path / "home"
    _git(clone, "worktree", "add", "-q", "-b", "loop/acme", str(home), "main")
    remote_tip = _commit(clone, "landed.txt", "landed on the remote")
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "fetch", "-q", "origin")
    shadow = _shadow(clone, remote_tip, kind=kind)  # AHEAD of the remote: the short name would ff onto it

    new_head = GitVcs().fast_forward(home, remote_tracking_ref("main"))
    assert new_head == remote_tip and new_head != shadow


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_publishing_onto_the_remote_tip_never_carries_a_shadow(repo, kind: str) -> None:
    """Review 1 (high): the ledger-promotion publish built on `<remote>/<ref>` by short name and
    PUSHED -- with a shadow one commit ahead, the unverified commit landed on the remote's main."""
    remote, clone = repo
    shadow = _shadow(clone, "main", kind=kind)

    GitVcs().commit_paths_onto_remote_tip(
        clone,
        remote=VcsRef("origin"),
        ref=VcsRef("main"),
        writes=(("ledger.yaml", "development_status: {}\n"),),
        message=to_redacted_text("promote"),
    )

    remote_log = _git(remote, "log", "--format=%H", "main").split()
    assert shadow not in remote_log
    assert _git(remote, "show", "main:ledger.yaml") == "development_status: {}"
