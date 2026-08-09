"""Meta-test: `unpushed-work-check` measures durability by TIP, not by name.

Story 3.10 / FR-171 (`docs/dreams/durable-runs.md`). `find_unpushed` used to
skip any local branch whose NAME existed on origin:

    if not br or br in remote:
        continue

which answers *"does a remote copy exist?"* while the detector presents itself
as answering *"is the work safe?"*. A long-lived branch whose remote copy had
fallen arbitrarily far behind therefore reported clean. Measured live on
2026-08-09: `loop/pyforge-doctor` sat on origin at `3f43f486c9` while the local
branch stood 8 PRs ahead at `cbd965110b`, and this detector said nothing — on
the very day its own Dream was reopened for durability. Station branches are the
structural blind spot: their names always exist remotely, so a name check can
never see them fall behind.

These tests build a real git repo with a real "origin" so the behaviour is
exercised through actual git plumbing rather than a mocked `git()`.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
CHECKER = REPO_ROOT / "scripts" / "unpushed_work_check.py"


def _load_checker(repo: Path):
    """Import the checker with its module-level ROOT bound to `repo`."""
    src = CHECKER.read_text(encoding="utf-8").replace(
        "ROOT = pathlib.Path(__file__).resolve().parent.parent",
        f"ROOT = pathlib.Path({str(repo)!r})",
    )
    mod_path = repo / "_checker_under_test.py"
    mod_path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("checker_under_test", mod_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["checker_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    return p.stdout.strip()


def _repo_with_origin(tmp_path: Path) -> tuple[Path, Path]:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp_path / "work"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(repo), "config", k, v], check=True)
    (repo / "a.txt").write_text("1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "origin", "main")
    return repo, origin


def test_a_branch_whose_remote_copy_is_behind_is_reported(tmp_path: Path):
    """The live case, replayed. The branch NAME is on origin the whole time —
    only the tip is stale — so the old membership check was structurally
    incapable of seeing it."""
    repo, _ = _repo_with_origin(tmp_path)
    _git(repo, "checkout", "-qb", "loop/station")
    (repo / "b.txt").write_text("first\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "landed on the remote")
    _git(repo, "push", "-q", "origin", "loop/station")

    # ...and now the local branch moves on, exactly as a loop home does.
    (repo / "c.txt").write_text("local only\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "local-only work")

    mod = _load_checker(repo)
    remote = mod.remote_branches()
    assert "loop/station" in remote, "the NAME is on origin — that was the trap"

    findings = mod.find_unpushed("origin/main", remote)
    refs = {f["ref"] for f in findings}
    assert "loop/station" in refs, (
        "a branch whose remote copy is behind is unpushed work; a remote copy "
        "existing is not the work being safe:\n" + repr(findings))
    entry = next(f for f in findings if f["ref"] == "loop/station")
    assert "behind by 1 commit(s)" in entry["detail"], entry


def test_a_branch_in_sync_with_its_remote_stays_silent(tmp_path: Path):
    """The fix must not turn every branch into a finding — otherwise it is
    noise, and a noisy durability gate is one nobody reads."""
    repo, _ = _repo_with_origin(tmp_path)
    _git(repo, "checkout", "-qb", "loop/synced")
    (repo / "b.txt").write_text("all pushed\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "work")
    _git(repo, "push", "-q", "origin", "loop/synced")

    mod = _load_checker(repo)
    findings = mod.find_unpushed("origin/main", mod.remote_branches())
    assert "loop/synced" not in {f["ref"] for f in findings}, findings


def test_a_branch_with_no_remote_at_all_is_still_reported(tmp_path: Path):
    """The pre-existing behaviour must survive the change — this is a
    widening, not a replacement."""
    repo, _ = _repo_with_origin(tmp_path)
    _git(repo, "checkout", "-qb", "feat/never-pushed")
    (repo / "b.txt").write_text("brand new\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "work")

    mod = _load_checker(repo)
    findings = mod.find_unpushed("origin/main", mod.remote_branches())
    entry = next((f for f in findings if f["ref"] == "feat/never-pushed"), None)
    assert entry is not None, findings
    assert "no branch of this name on origin at all" in entry["detail"]
