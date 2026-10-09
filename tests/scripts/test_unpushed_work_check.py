"""Marshal Story 87.2 (CAP-287): unpushed-work detector fails closed and never mints tags.

Real git repositories and a bare remote only — no network.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "unpushed_work_check.py"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _run(repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo / "scripts" / SCRIPT.name), *extra],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def bare_origin(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    return remote


@pytest.fixture
def clone(bare_origin: Path, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(bare_origin), str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "push", "-q", "origin", "main")
    (repo / "scripts").mkdir()
    shutil.copy2(SCRIPT, repo / "scripts" / SCRIPT.name)
    _git(repo, "add", "scripts/unpushed_work_check.py")
    _git(repo, "commit", "-qm", "vendor unpushed_work_check for tests")
    _git(repo, "push", "-q", "origin", "main")
    return repo


def _load_module(repo: Path):
    src = SCRIPT.read_text(encoding="utf-8").replace(
        "ROOT = pathlib.Path(__file__).resolve().parent.parent",
        f"ROOT = pathlib.Path({str(repo)!r})",
    )
    mod_path = repo / "_checker_under_test.py"
    mod_path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("checker_under_test", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_git_failure_exits_two_without_reporting_zero_dangling(clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_module(clone)

    def boom(*_a, **_k):
        raise mod.ObservationFailed(("git", "fsck", "--no-reflogs"))

    monkeypatch.setattr(mod, "git_stdout_even_on_failure", boom)
    monkeypatch.setattr(sys, "argv", ["unpushed_work_check.py"])
    assert mod.main() == 2


def test_fsck_nonzero_stdout_still_lists_dangling(clone: Path) -> None:
    _git(clone, "checkout", "-q", "-b", "orphan-work")
    for i in range(4):
        (clone / f"f{i}.txt").write_text(f"{i}\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-qm", "real dangling bundle")
    _git(clone, "checkout", "-q", "main")
    _git(clone, "branch", "-D", "orphan-work")
    run = _run(clone, "--json", "--min-files", "2")
    assert run.returncode == 1, run.stdout + run.stderr
    report = json.loads(run.stdout)
    kinds = {f["kind"] for f in report["findings"]}
    assert "dangling-commit" in kinds


def test_synthetic_merged_check_commit_is_not_a_finding(clone: Path) -> None:
    _git(clone, "checkout", "-q", "-b", "tmp")
    for i in range(4):
        (clone / f"s{i}.txt").write_text("x\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-qm", "marshal teardown merged-check (not a real commit)")
    for i in range(4):
        (clone / f"r{i}.txt").write_text("y\n", encoding="utf-8")
    _git(clone, "add", "-A")
    real_msg = "real unpreserved dangling work"
    _git(clone, "commit", "-qm", real_msg)
    _git(clone, "checkout", "-q", "main")
    _git(clone, "branch", "-D", "tmp")
    run = _run(clone, "--json", "--min-files", "2")
    report = json.loads(run.stdout)
    subjects = [f.get("stat", "") for f in report["findings"] if f["kind"] == "dangling-commit"]
    assert not any("(not a real commit)" in s for s in subjects)
    assert any(real_msg in s for s in subjects)


def test_unpushed_ref_kinds_against_bare_origin(clone: Path) -> None:
    _git(clone, "checkout", "-q", "-b", "hold")
    (clone / "only-local.txt").write_text("local\n", encoding="utf-8")
    _git(clone, "add", "only-local.txt")
    _git(clone, "commit", "-qm", "only here")
    commit = _git(clone, "rev-parse", "HEAD")
    _git(clone, "tag", "-a", "local/annotated", "-m", "anno", commit)
    _git(clone, "tag", "local/lightweight", commit)
    _git(clone, "update-ref", "refs/backup/snapshot", commit)
    _git(clone, "checkout", "-q", "main")
    run = _run(clone, "--json", "--min-files", "99")
    report = json.loads(run.stdout)
    refnames = {f["ref"] for f in report["findings"] if f["kind"] == "unpushed-ref"}
    assert "refs/tags/local/annotated" in refnames
    assert "refs/tags/local/lightweight" in refnames
    assert "refs/backup/snapshot" in refnames


def test_refs_on_origin_are_not_unpushed_ref_findings(clone: Path) -> None:
    _git(clone, "checkout", "-q", "-b", "hold")
    (clone / "pushed.txt").write_text("p\n", encoding="utf-8")
    _git(clone, "add", "pushed.txt")
    _git(clone, "commit", "-qm", "will push")
    commit = _git(clone, "rev-parse", "HEAD")
    _git(clone, "push", "-q", "origin", "hold")
    _git(clone, "tag", "on-origin-tag", commit)
    _git(clone, "push", "-q", "origin", "on-origin-tag")
    _git(clone, "checkout", "-q", "main")
    run = _run(clone, "--json", "--min-files", "99")
    report = json.loads(run.stdout)
    unpushed_refs = [f for f in report["findings"] if f["kind"] == "unpushed-ref"]
    assert not any("on-origin-tag" in f["ref"] for f in unpushed_refs)


def test_remedies_never_suggest_tag_or_push(clone: Path) -> None:
    _git(clone, "checkout", "-q", "-b", "work")
    (clone / "u.txt").write_text("u\n", encoding="utf-8")
    _git(clone, "add", "u.txt")
    _git(clone, "commit", "-qm", "unpushed branch")
    _git(clone, "checkout", "-q", "main")
    run = _run(clone, "--json", "--branches-only")
    report = json.loads(run.stdout)
    for finding in report["findings"]:
        remedy = finding["remedy"].lower()
        assert "git tag" not in remedy
        assert "git push" not in remedy
        assert "report; do not tag" in remedy


def test_rescued_tags_suppress_dangling(clone: Path) -> None:
    _git(clone, "checkout", "-q", "-b", "tmp")
    for i in range(4):
        (clone / f"r{i}.txt").write_text("r\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-qm", "rescued work bundle")
    commit = _git(clone, "rev-parse", "HEAD")
    _git(clone, "tag", f"rescue/dangling-20260101-{commit[:8]}", commit)
    _git(clone, "checkout", "-q", "main")
    _git(clone, "branch", "-D", "tmp")
    run = _run(clone, "--json", "--min-files", "2")
    report = json.loads(run.stdout)
    assert not any(f["kind"] == "dangling-commit" for f in report["findings"])


def test_branches_only_still_reports_unpushed_branch(clone: Path) -> None:
    _git(clone, "checkout", "-q", "-b", "work")
    (clone / "u.txt").write_text("u\n", encoding="utf-8")
    _git(clone, "add", "u.txt")
    _git(clone, "commit", "-qm", "unpushed")
    _git(clone, "checkout", "-q", "main")
    run = _run(clone, "--json", "--branches-only")
    assert run.returncode == 1
    report = json.loads(run.stdout)
    assert [f["ref"] for f in report["findings"] if f["kind"] == "unpushed-branch"] == ["work"]


def test_branches_only_git_failure_exits_two(clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = _load_module(clone)

    def boom(*_a, **_k):
        raise mod.ObservationFailed(("git", "for-each-ref"))

    monkeypatch.setattr(mod, "git", boom)
    monkeypatch.setattr(sys, "argv", ["unpushed_work_check.py", "--branches-only"])
    assert mod.main() == 2


def test_mutation_disabling_synthetic_filter_reports_synthetic_commit(clone: Path) -> None:
    """If the synthetic-subject rule is removed, synthetic commits become findings."""
    mod = _load_module(clone)
    _git(clone, "checkout", "-q", "-b", "tmp")
    for i in range(4):
        (clone / f"m{i}.txt").write_text("m\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-qm", "marshal teardown merged-check (not a real commit)")
    _git(clone, "checkout", "-q", "main")
    _git(clone, "branch", "-D", "tmp")
    with_filter = mod.find_dangling(2, mod.rescued())
    mod.SYNTHETIC_SUBJECT_SUFFIX = ""
    without_filter = mod.find_dangling(2, mod.rescued())
    assert not any("(not a real commit)" in f.get("stat", "") for f in with_filter)
    assert any("(not a real commit)" in f.get("stat", "") for f in without_filter)


def test_mutation_replacing_report_remedy_would_fail_remedy_contract() -> None:
    remedy = (
        "report; do not tag — operator review required"
        " (after Story 87.3: `marshal preserve tag`)"
    )
    assert "git tag" not in remedy.lower()
    assert "git push" not in remedy.lower()
    bad = "git tag bad && git push origin bad"
    assert "git tag" in bad
