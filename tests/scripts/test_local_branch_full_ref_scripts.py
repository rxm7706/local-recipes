"""Marshal Story 61.1 (CAP-271): marshal's repo-root scripts read its local branches by full ref.

Story 61.1 review 1 probed each: with a tag named like the branch on another commit,
`scripts/fleet_scan.py` read the tag's history (landed stories dropped out of the dashboard),
`scripts/bmad-loop-worktree` attached a loop home DETACHED at a same-named tag or refused to mint
from `main` as ambiguous, `scripts/fleet_picture.py` counted the primary checkout behind a remote
it matched, and `scripts/unpushed_work_check.py` reported a fully pushed branch as absent from
origin. Each case builds a scratch repository; each script is loaded from the repo (or, for the
one that binds its root to its own location, copied into the scratch repo) and run there.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _commit(repo: Path, name: str, message: str) -> str:
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(f"{message}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def _load(name: str, path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)  # dataclasses resolve their module by name
    loader.exec_module(module)
    return module


@pytest.fixture
def clone(tmp_path: Path) -> tuple[Path, str, str]:
    """A clone of a bare remote: `main` at `landed` (pushed), and a tag named `main` on `base`.
    Returns (clone, base, landed)."""
    remote, repo = tmp_path / "remote.git", tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    base = _commit(repo, "README.md", "base")
    landed = _commit(repo, "landed.txt", "marshal: story 61.1 landed")
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "tag", "main", base)  # the trap
    return repo, base, landed


def test_fleet_scan_reads_the_landings_on_the_branch_not_the_tag(clone, monkeypatch) -> None:
    repo, _base, _landed = clone
    fleet_scan = _load("fleet_scan_61_1", SCRIPTS / "fleet_scan.py", monkeypatch)
    monkeypatch.chdir(repo)  # done_ids_from_git runs git in the working directory

    assert "61.1" in fleet_scan.done_ids_from_git("main", ("marshal",))["marshal"]


def test_fleet_picture_counts_the_primary_checkout_current_beside_a_tag_named_main(clone, monkeypatch) -> None:
    repo, _base, _landed = clone
    fleet_picture = _load("fleet_picture_61_1", SCRIPTS / "fleet_picture.py", monkeypatch)

    assert fleet_picture.primary_checkout_staleness(repo) is None  # main == origin/main: nothing behind


def test_fleet_picture_sees_the_checkout_behind_beside_a_tag_on_the_remote_named_main(
    clone, tmp_path, monkeypatch
) -> None:
    """Review 2: `git fetch origin main` fetched the remote's TAG `main` into FETCH_HEAD only, so
    `refs/remotes/origin/main` stayed stale and the checkout read as current."""
    repo, base, _landed = clone
    remote = tmp_path / "remote.git"
    other = tmp_path / "other"
    subprocess.run(["git", "clone", "-q", str(remote), str(other)], check=True, capture_output=True)
    _git(other, "config", "user.email", "t@example.com")
    _git(other, "config", "user.name", "T")
    _commit(other, "elsewhere.txt", "landed elsewhere")
    _git(other, "push", "-q", "origin", "refs/heads/main:refs/heads/main", f"{base}:refs/tags/main")
    fleet_picture = _load("fleet_picture_61_1_remote_tag", SCRIPTS / "fleet_picture.py", monkeypatch)

    assert fleet_picture.primary_checkout_staleness(repo) == 1


def _provision(clone_repo: Path, tmp_path: Path, monkeypatch) -> tuple[ModuleType, Path]:
    """`bmad-loop-worktree` against the scratch repo, with a `bmad-switch` stub the home runs."""
    (clone_repo / "_bmad-output" / "projects" / "acme").mkdir(parents=True)
    (clone_repo / "_bmad-output" / "projects" / "acme" / ".keep").write_text("", encoding="utf-8")
    (clone_repo / "scripts").mkdir()
    (clone_repo / "scripts" / "bmad-switch").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    return _load("bmad_loop_worktree_61_1", SCRIPTS / "bmad-loop-worktree", monkeypatch), tmp_path / "loop-homes"


def test_bmad_loop_worktree_mints_from_the_branch_beside_a_tag_named_main(clone, tmp_path, monkeypatch) -> None:
    repo, base, _landed = clone
    worktree, _homes = _provision(repo, tmp_path, monkeypatch)
    tip = _commit(repo, "stub.txt", "the stub and project dir")  # main moves on; the tag stays on base

    home = worktree.provision(repo, "acme")

    assert home is not None  # the bare `main` start point refused as ambiguous
    assert _git(home, "rev-parse", "HEAD") == tip != base
    assert _git(home, "branch", "--show-current") == "loop/acme"


def test_bmad_loop_worktree_mints_the_branch_when_only_a_tag_carries_its_name(clone, tmp_path, monkeypatch) -> None:
    repo, base, _landed = clone
    worktree, _homes = _provision(repo, tmp_path, monkeypatch)
    tip = _commit(repo, "stub.txt", "the stub and project dir")
    _git(repo, "tag", "loop/acme", base)  # the bare check read this as the branch existing

    home = worktree.provision(repo, "acme")

    assert home is not None
    assert _git(home, "branch", "--show-current") == "loop/acme"  # not detached at the tag
    assert _git(home, "rev-parse", "HEAD") == tip


def test_worktree_sweep_never_reads_a_feature_as_merged_through_a_stray_tag_main(clone, tmp_path, monkeypatch) -> None:
    """Review 3: a stray `git tag main` on a feature commit (a tag AHEAD of the branch) made the
    feature an ancestor of "main" -- its worktree classified merged and its branch deleted."""
    repo, _base, _landed = clone
    home = tmp_path / "feature-home"
    _git(repo, "worktree", "add", "-q", "-b", "feature", str(home), "refs/heads/main")
    _git(home, "config", "user.email", "t@example.com")
    feature = _commit(home, "feature.txt", "feature work, never merged")
    _git(repo, "tag", "-f", "main", feature)  # the stray tag, ahead of the branch
    sweep = _load("worktree_sweep_61_1", SCRIPTS / "worktree_sweep.py", monkeypatch)
    monkeypatch.setattr(sweep, "REPO_ROOT", repo)

    wt = sweep.gather(sweep.Worktree(path=str(home), branch="feature", category="scratch"), [], {}, set())
    assert (wt.merged, wt.unmerged_commits) == (False, 1)
    _git(repo, "worktree", "remove", "--force", str(home))
    deleted, _kept = sweep.delete_merged_local_branches()

    assert deleted == 0
    assert _git(repo, "rev-parse", "refs/heads/feature") == feature


def _unpushed(repo: Path) -> dict:
    (repo / "scripts").mkdir(exist_ok=True)
    shutil.copy2(SCRIPTS / "unpushed_work_check.py", repo / "scripts" / "unpushed_work_check.py")
    run = subprocess.run(
        [sys.executable, str(repo / "scripts" / "unpushed_work_check.py"), "--json", "--branches-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    return json.loads(run.stdout)


def test_unpushed_work_check_matches_a_pushed_branch_beside_a_same_named_tag(clone) -> None:
    repo, base, _landed = clone
    _git(repo, "checkout", "-q", "-b", "work")
    _commit(repo, "work.txt", "pushed work")
    _git(repo, "push", "-q", "origin", "work")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "tag", "work", base)  # `refname:short` then printed `heads/work`

    refs = [f.get("ref") for f in _unpushed(repo)["findings"]]
    assert "work" not in refs and "heads/work" not in refs


def test_unpushed_work_check_still_reports_unpushed_work_beside_a_same_named_tag(clone) -> None:
    repo, base, _landed = clone
    _git(repo, "checkout", "-q", "-b", "work")
    _commit(repo, "work.txt", "work nowhere else")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "tag", "work", base)

    findings = _unpushed(repo)["findings"]
    assert [f.get("ref") for f in findings if f.get("kind") == "unpushed-branch"] == ["work"]
    assert findings[0]["files"] == 1  # the bare name diffed the tag (the base): empty, so never reported
    assert findings[0]["remedy"] == "git push origin refs/heads/work:refs/heads/work"  # review 2: runnable beside the tag
