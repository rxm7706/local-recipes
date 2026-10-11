"""Story 89.1: land-only spec gate and Review Triage Log ordering."""

from __future__ import annotations

import subprocess
from pathlib import Path

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
    sample = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 1 1 1\nauthor Author\ncommitter-time 1700000000\n\tline one\n"
    facts = _parse_blame_porcelain(sample)
    assert facts[1] == ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1700000000)


def _git_run(cwd: Path, *args: str, env: dict[str, str] | None = None) -> None:
    merged = None
    if env is not None:
        import os

        merged = os.environ.copy()
        merged.update(env)
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=merged)


def _git_commit_at(cwd: Path, when: str, message: str) -> str:
    _git_run(
        cwd,
        "commit",
        "-m",
        message,
        env={"GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when},
    )
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def _init_spec_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_run(repo, "init")
    _git_run(repo, "config", "user.email", "t@test")
    _git_run(repo, "config", "user.name", "t")
    spec = repo / "spec.md"
    return repo, spec


def _blame_facts(vcs: GitVcs, repo: Path, spec: Path, *, ref: str | None = None) -> dict[int, LineBlameFact]:
    raw = (
        vcs.line_blame_facts(repo_root=repo, path="spec.md", ref=ref)
        if ref is not None
        else vcs.line_blame_facts(repo_root=repo, path="spec.md", worktree=repo)
    )
    return {k: LineBlameFact(c, t) for k, (c, t) in raw.items()}


def test_parse_blame_porcelain_reuses_committer_time_on_bare_headers() -> None:
    sha = "a" * 40
    sample = (
        f"{sha} 1 1 1\nauthor Author\ncommitter-time 1700000001\n\tfirst\n{sha} 1 2 2\n\tsecond\n{sha} 1 3 3\n\tthird\n"
    )
    facts = _parse_blame_porcelain(sample)
    assert facts[1] == (sha, 1700000001)
    assert facts[2] == (sha, 1700000001)
    assert facts[3] == (sha, 1700000001)


def test_parse_blame_porcelain_omits_committed_lines_without_committer_time() -> None:
    sha = "b" * 40
    sample = f"{sha} 1 1 1\nauthor Author\nsummary line\n\tline one\n"
    facts = _parse_blame_porcelain(sample)
    assert facts == {}


def test_missing_committer_time_makes_gate_unevaluable() -> None:
    text = "---\nstatus: in-review\n---\n\n## Review Triage Log\n\n### 2026-10-11 — Independent review: PASS\n\nbody\n"
    headings = iter_review_triage_heading_lines(text)
    assert headings
    blame: dict[int, LineBlameFact] = {}
    assert latest_review_triage_headings(headings, blame) is None
    verdict = evaluate_land_only_spec_gate(spec_text=text, spec_status="in-review", blame=blame)
    assert not verdict.permitted
    assert verdict.unevaluable


def test_git_blame_orders_triage_headings(tmp_path: Path) -> None:
    repo, spec = _init_spec_repo(tmp_path)
    spec.write_text("## Review Triage Log\n\n### old pass\n", encoding="utf-8")
    _git_run(repo, "add", "spec.md")
    _git_commit_at(repo, "2020-01-01T00:00:00", "first")
    spec.write_text(
        "## Review Triage Log\n\n### old pass\n\n### newer FAIL (1 high)\n",
        encoding="utf-8",
    )
    _git_run(repo, "add", "spec.md")
    sha_second = _git_commit_at(repo, "2020-01-02T00:00:00", "second")
    vcs = GitVcs()
    blame = vcs.line_blame_facts(repo_root=repo, path="spec.md", worktree=repo)
    text = spec.read_text(encoding="utf-8")
    headings = iter_review_triage_heading_lines(text)
    blame_facts = _blame_facts(vcs, repo, spec)
    pass_line = next(ln for ln, h in headings if "pass" in h.lower())
    fail_line = next(ln for ln, h in headings if "FAIL" in h)
    assert blame[pass_line][1] != 0
    assert blame[fail_line][1] != 0
    assert blame[pass_line][1] != blame[fail_line][1]
    latest = latest_review_triage_headings(headings, blame_facts)
    assert latest == ("newer FAIL (1 high)",)
    ct = subprocess.run(
        ["git", "log", "-1", "--format=%ct", sha_second],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert blame[fail_line][1] == int(ct)


def test_ac1_pass_after_send_back_with_frontmatter_edit(tmp_path: Path) -> None:
    repo, spec = _init_spec_repo(tmp_path)
    base = "---\nstatus: 'in-review'\nreview_loop_iteration: 0\n---\n\n## Review Triage Log\n\n"
    spec.write_text(base, encoding="utf-8")
    _git_run(repo, "add", "spec.md")
    _git_commit_at(repo, "2020-01-01T00:00:00", "seed")
    spec.write_text(
        base + "### 2026-10-11 — Independent review, iteration 1: sent back (1 major)\n\ndetails\n",
        encoding="utf-8",
    )
    _git_run(repo, "add", "spec.md")
    _git_commit_at(repo, "2020-01-02T00:00:00", "send-back")
    spec.write_text(
        "---\nstatus: 'in-review'\nreview_loop_iteration: 1\n---\n\n"
        "## Review Triage Log\n\n"
        "### 2026-10-11 — Independent review, iteration 2: PASS\n\n"
        "pass body\n\n"
        "### 2026-10-11 — Independent review, iteration 1: sent back (1 major)\n\n"
        "details\n",
        encoding="utf-8",
    )
    _git_run(repo, "add", "spec.md")
    _git_commit_at(repo, "2020-01-03T00:00:00", "pass")
    text = spec.read_text(encoding="utf-8")
    vcs = GitVcs()
    for ref in (None, "HEAD"):
        blame = _blame_facts(vcs, repo, spec, ref=ref)
        verdict = evaluate_land_only_spec_gate(
            spec_text=text,
            spec_status="in-review",
            blame=blame,
        )
        assert verdict.permitted, ref
        assert verdict.failed_heading is None
        latest = latest_review_triage_headings(iter_review_triage_heading_lines(text), blame)
        assert latest is not None and len(latest) == 1
        assert "PASS" in latest[0]


def test_ac2_fail_after_pass_with_frontmatter_edit(tmp_path: Path) -> None:
    repo, spec = _init_spec_repo(tmp_path)
    base = "---\nstatus: 'in-review'\nreview_loop_iteration: 0\n---\n\n## Review Triage Log\n\n"
    spec.write_text(base, encoding="utf-8")
    _git_run(repo, "add", "spec.md")
    _git_commit_at(repo, "2020-01-01T00:00:00", "seed")
    spec.write_text(
        base + "### Review pass\n\nok\n",
        encoding="utf-8",
    )
    _git_run(repo, "add", "spec.md")
    _git_commit_at(repo, "2020-01-02T00:00:00", "pass")
    spec.write_text(
        "---\nstatus: 'in-review'\nreview_loop_iteration: 1\n---\n\n"
        "## Review Triage Log\n\n"
        "### Review pass\n\nok\n\n"
        "### Independent review: FAIL (1 high)\n\n"
        "fail body\n",
        encoding="utf-8",
    )
    _git_run(repo, "add", "spec.md")
    _git_commit_at(repo, "2020-01-03T00:00:00", "fail")
    text = spec.read_text(encoding="utf-8")
    vcs = GitVcs()
    for ref in (None, "HEAD"):
        blame = _blame_facts(vcs, repo, spec, ref=ref)
        verdict = evaluate_land_only_spec_gate(
            spec_text=text,
            spec_status="in-review",
            blame=blame,
        )
        assert not verdict.permitted
        assert verdict.failed_heading is not None
        assert "FAIL" in verdict.failed_heading
        latest = latest_review_triage_headings(iter_review_triage_heading_lines(text), blame)
        assert latest == (verdict.failed_heading,)


def test_every_line_of_multi_line_commit_shares_committer_time(tmp_path: Path) -> None:
    repo, spec = _init_spec_repo(tmp_path)
    spec.write_text("line1\nline2\nline3\n", encoding="utf-8")
    _git_run(repo, "add", "spec.md")
    sha = _git_commit_at(repo, "2020-06-15T12:00:00", "multi")
    vcs = GitVcs()
    blame = vcs.line_blame_facts(repo_root=repo, path="spec.md", worktree=repo)
    ct = int(
        subprocess.run(
            ["git", "log", "-1", "--format=%ct", sha],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    for line_no in (1, 2, 3):
        assert blame[line_no][1] == ct
        assert blame[line_no][1] != 0
