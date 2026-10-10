"""Story 89.1: land-only spec gate and Review Triage Log ordering."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.adapters.vcs_git import GitVcs, _parse_blame_porcelain
from pyforge.marshal.core.dispatch_harness_done import (
    LineBlameFact,
    evaluate_land_only_spec_gate,
    iter_review_triage_heading_lines,
    latest_review_triage_headings,
    review_triage_heading_records_failure,
)


def test_review_triage_heading_failure_detection() -> None:
    assert review_triage_heading_records_failure("2026-10-10 — Independent review: FAIL (3 high)")
    assert review_triage_heading_records_failure("Landing review — sent back")
    assert not review_triage_heading_records_failure("Review pass (send-back guard)")
    assert not review_triage_heading_records_failure("2026-10-10 — Review pass [patch]")


def test_iter_review_triage_heading_lines() -> None:
    text = (
        "---\nstatus: in-progress\n---\n\n"
        "## Review Triage Log\n\n"
        "### 2026-10-10 — FAIL (1 high)\n\n"
        "body\n\n"
        "## Verification\n\n"
        "### should not appear\n"
    )
    headings = iter_review_triage_heading_lines(text)
    assert len(headings) == 1
    assert headings[0][1] == "2026-10-10 — FAIL (1 high)"


def test_latest_by_blame_commits_not_file_order() -> None:
    headings = ((10, "pass"), (5, "FAIL (1 high)"))
    blame = {
        5: LineBlameFact(commit="aaa", committer_time=100),
        10: LineBlameFact(commit="bbb", committer_time=200),
    }
    assert latest_review_triage_headings(headings, blame) == ("pass",)


def test_latest_by_blame_fails_when_later_commit_is_failure() -> None:
    headings = ((10, "pass"), (5, "FAIL (1 high)"))
    blame = {
        5: LineBlameFact(commit="bbb", committer_time=200),
        10: LineBlameFact(commit="aaa", committer_time=100),
    }
    latest = latest_review_triage_headings(headings, blame)
    assert latest == ("FAIL (1 high)",)


def test_uncommitted_blame_is_newest() -> None:
    zero = "0" * 40
    headings = ((8, "FAIL"), (12, "Review pass"))
    blame = {
        8: LineBlameFact(commit="aaa", committer_time=50),
        12: LineBlameFact(commit=zero, committer_time=0),
    }
    assert latest_review_triage_headings(headings, blame) == ("Review pass",)


def test_evaluate_gate_refuses_in_progress_without_failed_review() -> None:
    text = "---\nstatus: in-progress\n---\n\n## Review Triage Log\n\n"
    verdict = evaluate_land_only_spec_gate(spec_text=text, spec_status="in-progress", blame={})
    assert not verdict.permitted
    assert verdict.failed_heading is None


def test_evaluate_gate_permits_in_review_empty_log() -> None:
    text = "---\nstatus: in-review\n---\n\n"
    verdict = evaluate_land_only_spec_gate(spec_text=text, spec_status="in-review", blame={})
    assert verdict.permitted


def test_parse_blame_porcelain_sample() -> None:
    sample = (
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 1 1 1\n"
        "author Author\n"
        "committer-time 1700000000\n"
        "\tline one\n"
    )
    facts = _parse_blame_porcelain(sample)
    assert facts[1] == ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1700000000)


def _git_run(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_git_blame_orders_triage_headings(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_run(repo, "init")
    _git_run(repo, "config", "user.email", "t@test")
    _git_run(repo, "config", "user.name", "t")
    spec = repo / "spec.md"
    spec.write_text("## Review Triage Log\n\n### old pass\n", encoding="utf-8")
    _git_run(repo, "add", "spec.md")
    _git_run(repo, "commit", "-m", "first")
    spec.write_text(
        "## Review Triage Log\n\n### old pass\n\n### newer FAIL (1 high)\n",
        encoding="utf-8",
    )
    _git_run(repo, "add", "spec.md")
    _git_run(repo, "commit", "-m", "second")
    vcs = GitVcs()
    blame = vcs.line_blame_facts(repo_root=repo, path="spec.md", worktree=repo)
    headings = iter_review_triage_heading_lines(spec.read_text(encoding="utf-8"))
    blame_facts = {k: LineBlameFact(c, t) for k, (c, t) in blame.items()}
    latest = latest_review_triage_headings(headings, blame_facts)
    assert latest is not None and any("FAIL" in h for h in latest)
