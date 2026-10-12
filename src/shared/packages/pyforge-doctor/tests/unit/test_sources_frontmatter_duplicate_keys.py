"""Unit tests for ``frontmatter_duplicate_keys.gather`` (Story 42.1)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dataclasses import replace

from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.sources import __main__ as dispatch
from pyforge.doctor.sources import frontmatter_duplicate_keys
from pyforge.doctor.verdict import exit_code_for

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


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _add_commit(repo: Path, message: str = "commit") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _story_spec_path(repo: Path, project: str, filename: str) -> Path:
    return (
        repo
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "specs"
        / filename
    )


def _write_story_spec(repo: Path, project: str, filename: str, body: str) -> Path:
    path = _story_spec_path(repo, project, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_ac1_top_level_repeat_fails_with_lines_and_values(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(
        repo,
        "pyforge-herald",
        "spec-29-2-example.md",
        "---\n"
        "title: Example\n"
        "type: feature\n"
        "created: '2026-10-11'\n"
        "status: ready-for-dev\n"
        "followup_review_recommended: true\n"
        "review_loop_iteration: 0\n"
        "flag-exempt: detector-or-gate\n"
        "context: []\n"
        "followup_review_recommended: false\n"
        "---\n\n# Body\n",
    )
    _add_commit(repo)

    findings = frontmatter_duplicate_keys.gather(repo)
    fails = [f for f in findings if f.check == "frontmatter-duplicate-key"]
    assert len(fails) == 1
    fail = fails[0]
    assert fail.status is DoctorStatus.FAIL
    assert fail.evidence["key"] == "followup_review_recommended"
    assert fail.evidence["lines"] == [6, 10]
    assert fail.evidence["values"] == ["true", "false"]
    assert fail.status is DoctorStatus.FAIL


def test_ac2_nested_dotted_path_and_quoted_bare_spelling(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-nested.md",
        "---\n"
        "flag:\n"
        "  key: first\n"
        "  key: second\n"
        "---\n\n# Body\n",
    )
    _add_commit(repo, "nested")

    nested_findings = frontmatter_duplicate_keys.gather(repo)
    nested = [f for f in nested_findings if f.check == "frontmatter-duplicate-key"][0]
    assert nested.evidence["key"] == "flag.key"

    _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-quoted.md",
        "---\n"
        '"status": draft\n'
        "status: ready\n"
        "---\n\n# Body\n",
    )
    _add_commit(repo, "quoted")

    quoted = [
        f
        for f in frontmatter_duplicate_keys.gather(repo)
        if f.evidence.get("path", "").endswith("spec-quoted.md")
    ][0]
    assert quoted.evidence["key"] == "status"


def test_ac2_banner_topped_block_is_read(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(
        repo,
        "pyforge-steward",
        "spec-banner.md",
        "<!-- provenance -->\n"
        "---\n"
        "status: draft\n"
        "status: ready\n"
        "---\n\n# Body\n",
    )
    _add_commit(repo)

    findings = frontmatter_duplicate_keys.gather(repo)
    assert any(f.check == "frontmatter-duplicate-key" for f in findings)


def test_ac3_scope_untracked_spec_md_and_outside_specs_ignored(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    tracked = _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-clean.md",
        "---\nstatus: draft\n---\n\n# Clean\n",
    )
    spec_md = _story_spec_path(repo, "pyforge-doctor", "spec-pyforge-doctor") / "SPEC.md"
    spec_md.parent.mkdir(parents=True, exist_ok=True)
    spec_md.write_text("---\nstatus: a\nstatus: b\n---\n", encoding="utf-8")
    outside = repo / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts" / "epics.md"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("---\nstatus: a\nstatus: b\n---\n", encoding="utf-8")
    _git(repo, "add", str(tracked.relative_to(repo)))
    _git(repo, "add", str(spec_md.relative_to(repo)))
    _git(repo, "add", str(outside.relative_to(repo)))
    _add_commit(repo)
    _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-untracked-dup.md",
        "---\nstatus: a\nstatus: b\n---\n\n# Untracked\n",
    )

    tracked_paths = {repo / p for p in frontmatter_duplicate_keys._iter_tracked_story_specs(repo)}
    assert (repo / "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-untracked-dup.md") not in tracked_paths
    findings = frontmatter_duplicate_keys.gather(repo)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence["story_spec_count"] == 1


def test_ac4_unclosed_fence_and_invalid_yaml_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-unclosed.md",
        "---\nstatus: draft\n",
    )
    _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-invalid.md",
        "---\nstatus: [unclosed\n---\n",
    )
    _add_commit(repo)

    findings = frontmatter_duplicate_keys.gather(repo)
    warns = [f for f in findings if f.check == "frontmatter-unreadable"]
    assert len(warns) == 2
    assert all(f.status is DoctorStatus.WARN for f in warns)
    assert exit_code_for(findings) == 0


def test_ac4_no_frontmatter_is_silent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(repo, "pyforge-doctor", "spec-prose.md", "# No frontmatter\n")
    _add_commit(repo)

    findings = frontmatter_duplicate_keys.gather(repo)
    assert findings[0].status is DoctorStatus.OK


def test_ac5_dispatch_and_detectors_fixture_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-dup.md",
        "---\nreview_loop_iteration: 0\nreview_loop_iteration: 1\n---\n",
    )
    _add_commit(repo)

    assert "frontmatter-duplicate-keys" in dispatch.DISPATCH
    dup_findings = frontmatter_duplicate_keys.gather(repo)
    doctor_src = Path(__file__).resolve().parents[2] / "src"
    proc = subprocess.run(
        [sys.executable, "-m", "pyforge.doctor.sources", "frontmatter-duplicate-keys"],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(doctor_src)},
    )
    assert proc.returncode == exit_code_for(dup_findings)
    assert "frontmatter-duplicate-key" in proc.stdout + proc.stderr

    repo_root = Path(__file__).resolve().parents[6]
    sys.path.insert(0, str(repo_root / "scripts"))
    doctor_src = Path(__file__).resolve().parents[2] / "src"
    if str(doctor_src) not in sys.path:
        sys.path.insert(0, str(doctor_src))
    import detectors  # noqa: PLC0415

    monkeypatch.setattr(detectors, "ROOT", repo)
    monkeypatch.setattr(
        detectors,
        "_DOCTOR_SOURCE_TASKS",
        (("frontmatter-duplicate-keys", "frontmatter-duplicate-keys-check"),),
    )
    (row,) = detectors._run_doctor_sources("repo")
    assert row["name"] == "frontmatter-duplicate-keys"
    assert row["rc"] == 1


def test_matrix_ok_row_when_clean(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(repo, "pyforge-marshal", "spec-ok.md", "---\nstatus: draft\n---\n")
    _add_commit(repo)

    findings = frontmatter_duplicate_keys.gather(repo)
    assert findings[0].status is DoctorStatus.OK
    assert exit_code_for(findings) == 0


def test_ac8_mutation_removing_duplicate_scan_yields_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-dup.md",
        "---\nfollowup_review_recommended: true\nfollowup_review_recommended: false\n---\n",
    )
    _add_commit(repo)

    monkeypatch.setattr(frontmatter_duplicate_keys, "_find_duplicate_keys", lambda _b, _s: [])
    findings = frontmatter_duplicate_keys.gather(repo)
    assert findings[0].status is DoctorStatus.OK


def test_ac8_mutation_warn_instead_of_fail_breaks_exit_code(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_story_spec(
        repo,
        "pyforge-doctor",
        "spec-dup.md",
        "---\nfollowup_review_recommended: true\nfollowup_review_recommended: false\n---\n",
    )
    _add_commit(repo)

    findings = frontmatter_duplicate_keys.gather(repo)
    warnified = tuple(
        f if f.status is not DoctorStatus.FAIL else replace(f, status=DoctorStatus.WARN) for f in findings
    )
    assert exit_code_for(warnified) == 0
