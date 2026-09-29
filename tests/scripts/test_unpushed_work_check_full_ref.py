"""Marshal Story 60.1 (CAP-270): `scripts/unpushed_work_check.py` judges unpushed work against the
remote-tracking ref, never a short name a local ref can shadow.

Story 60.1 review 2 probed it: a local branch named `origin/main` sitting on an unpushed branch
made `git diff origin/main...work` empty, so the unpushed work read as safe. The script binds
its repo root to its own location, so each case copies it into a scratch repository and runs it
there, as `marshal status` does.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "unpushed_work_check.py"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """A clone of a bare remote with `main` pushed, a never-pushed branch `work`, and the script."""
    remote, repo = tmp_path / "remote.git", tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "checkout", "-q", "-b", "work")
    (repo / "unpushed.txt").write_text("work nowhere else\n", encoding="utf-8")
    _git(repo, "add", "unpushed.txt")
    _git(repo, "commit", "-qm", "unpushed work")
    _git(repo, "checkout", "-q", "main")
    (repo / "scripts").mkdir()
    shutil.copy2(SCRIPT, repo / "scripts" / SCRIPT.name)
    return repo


def _findings(repo: Path) -> dict:
    run = subprocess.run(
        [sys.executable, str(repo / "scripts" / SCRIPT.name), "--json", "--branches-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    return json.loads(run.stdout)


def test_unpushed_work_is_reported(clone: Path) -> None:
    report = _findings(clone)
    assert report["base"] == "refs/remotes/origin/main"
    assert [f.get("ref") or f.get("branch") for f in report["findings"]] == ["work"]


@pytest.mark.parametrize("kind", ["branch", "tag"])
def test_a_local_origin_main_on_the_work_does_not_hide_it(clone: Path, kind: str) -> None:
    _git(clone, kind, "origin/main", "work")  # the shadow: short `origin/main...work` diffs empty

    report = _findings(clone)
    # The work is still reported (a branch shadow is itself reported too: it is an unpushed local branch).
    assert "work" in [f.get("ref") or f.get("branch") for f in report["findings"]]
