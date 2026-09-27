"""Story 31.1 (spec-pyforge-doctor CAP-85): every Doctor source names the branch it reads by its
full refname.

Git resolves a short name through ``refs/<n>``, ``refs/tags/<n>``, ``refs/heads/<n>``, then
``refs/remotes/<n>``: a local branch or tag named ``origin/main`` stands in for the remote, and a
tag named ``main`` for the local branch. Each test builds a real repository with such a stray ref
and shows the source reaching the verdict it reaches without it -- and records, where it is
cheap, what the short name did instead. The story-status source's route 3 is covered in
``test_sources_marshal_story_status.py``; the meta test pins that no module spells a bare ref.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.refs import MAIN, ORIGIN_MAIN, display_ref, local_branch_ref, remote_tracking_ref
from pyforge.doctor.sources import frozen_path, ledger
from pyforge.doctor.sources import live_proof_surfaces as lps

_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def test_the_refs_are_full_refnames_and_display_short() -> None:
    assert MAIN == local_branch_ref("main") == "refs/heads/main"
    assert ORIGIN_MAIN == remote_tracking_ref("main") == "refs/remotes/origin/main"
    assert remote_tracking_ref("release", remote="upstream") == "refs/remotes/upstream/release"
    assert (display_ref(MAIN), display_ref(ORIGIN_MAIN)) == ("main", "origin/main")
    assert display_ref("0123abcd") == "0123abcd"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")
    return repo


def _ledger(repo: Path, project: str, statuses: dict[str, str]) -> None:
    path = repo / "_bmad-output" / "projects" / project / "planning-artifacts" / "sprint-status-ledger.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("development_status:\n" + "".join(f"  {k}: {v}\n" for k, v in statuses.items()), encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_ledger_regression_sees_a_regression_past_a_local_origin_main(repo: Path, kind: str) -> None:
    """A shadow built on HEAD makes the short name's merge-base HEAD itself: the range is empty
    and the regression HEAD made reads clean. The remote-tracking ref still sees it."""
    _ledger(repo, "pyforge-doctor", {"1-1-foo": "done"})
    base = _commit(repo, "seed ledger")
    _git(repo, "update-ref", "refs/remotes/origin/main", base)
    _ledger(repo, "pyforge-doctor", {"1-1-foo": "in-progress"})
    _commit(repo, "un-finish the story")
    _git(repo, "checkout", "-q", "--detach", "HEAD")
    shadow = _commit(repo, "unrelated work on top")
    _git(repo, kind, "origin/main", shadow)
    _git(repo, "checkout", "-q", "main")

    assert [f.status for f in ledger.gather(repo, base="origin/main")] == [DoctorStatus.OK]  # the trap
    findings = ledger.gather(repo)

    assert [(f.status, f.check) for f in findings] == [(DoctorStatus.FAIL, "done-key-regressed")]
    assert findings[0].evidence["base"] == "origin/main"  # people still read the short name


def test_ledger_direction_reads_the_branch_not_a_tag_named_main(repo: Path) -> None:
    """With a tag `main` on a commit where the story was not yet done, the short name read the
    ledger at the tag and called a promoted story done-but-unmerged."""
    _ledger(repo, "pyforge-marshal", {"32-1-consistency": "in-progress"})
    older = _commit(repo, "before the promotion")
    _ledger(repo, "pyforge-marshal", {"32-1-consistency": "done"})
    _commit(repo, "seed")
    _commit(repo, "Merge pull request #1082 from rxm7706/chore/fleet-consistency-2026-09-07")
    _git(repo, "tag", "main", older)
    _git(repo, "checkout", "-q", "-b", "work")

    trap = ledger.gather_direction(repo, base_ref="main")
    assert [f.status for f in trap] == [DoctorStatus.WARN]  # the trap, for the record
    findings = ledger.gather_direction(repo)

    assert [f.status for f in findings] == [DoctorStatus.OK]
    assert findings[0].evidence["base_ref"] == "main"


@pytest.mark.parametrize("changed_paths", [frozen_path._changed_paths, lps._changed_paths])
@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_the_diff_base_is_the_remote_tracking_ref(repo: Path, changed_paths, kind: str) -> None:
    """`frozen-path-changed` and `live-proof-surface` diff `origin/main..HEAD`: a shadow at HEAD
    made the short name's diff empty -- every frozen or catalogued path invisible."""
    base = _commit(repo, "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", base)
    (repo / "frozen.txt").write_text("changed\n", encoding="utf-8")
    head = _commit(repo, "touch a frozen path")
    _git(repo, kind, "origin/main", head)

    assert list(changed_paths(repo, base="origin/main")) == []  # the trap
    assert list(changed_paths(repo)) == ["frozen.txt"]
