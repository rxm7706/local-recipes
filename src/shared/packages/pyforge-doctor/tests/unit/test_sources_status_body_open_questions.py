"""Unit tests for ``sources.status_body_consistency`` CAP-2 (Story 21.13)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import status_body_consistency as sbc

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "status_body"


def _open_questions_repo(tmp_path: Path) -> Path:
    specs = tmp_path / "docs" / "governance"
    for name in ("spec-charter-mismatch", "spec-charter-closed", "spec-no-memlog"):
        target = specs / name
        target.mkdir(parents=True)
        shutil.copytree(_FIXTURES / name, target, dirs_exist_ok=True)
    return tmp_path


def test_last_unclosed_memlog_question_returns_open_entry():
    memlog = "- (correction) preamble\n- (open) 2026-07-31 IS `guild` STILL THE RIGHT OWNER VALUE?\n"
    match = sbc.last_unclosed_memlog_question(memlog)
    assert match is not None
    assert match.line_no == 2


def test_last_unclosed_memlog_question_clears_on_decision():
    memlog = "- (open) 2026-07-31 IS `guild` STILL THE RIGHT OWNER VALUE?\n- (decision) 2026-09-09 KEEP `guild`.\n"
    assert sbc.last_unclosed_memlog_question(memlog) is None


def test_last_unclosed_memlog_question_tracks_question_tag():
    memlog = "- (question by claude) 2026-09-09 THE GUILDHALL REFERENT?\n"
    match = sbc.last_unclosed_memlog_question(memlog)
    assert match is not None
    assert match.line_no == 1


def test_open_questions_frontmatter_count_inline_empty():
    text = "---\nopen_questions: []\n---\n"
    count, line_no, unparseable = sbc.open_questions_frontmatter_count(text)
    assert count == 0
    assert line_no == 2
    assert unparseable is False


def test_open_questions_frontmatter_count_block_list():
    text = '---\nopen_questions:\n  - "One open question"\n---\n'
    count, line_no, unparseable = sbc.open_questions_frontmatter_count(text)
    assert count == 1
    assert line_no == 2
    assert unparseable is False


def test_gather_open_questions_fires_on_charter_mismatch_fixture(tmp_path: Path):
    repo = _open_questions_repo(tmp_path)
    findings = sbc.gather_open_questions_reconcile(repo)
    hits = [f for f in findings if f.check == sbc._CHECK_OPEN_QUESTIONS]
    assert len(hits) == 1
    hit = hits[0]
    assert hit.status == DoctorStatus.WARN
    assert hit.evidence["spec_line"] == 5
    assert hit.evidence["memlog_line"] == 7
    assert "open_questions: []" in hit.message
    assert hit.evidence["fired"] == 1
    assert hit.evidence["scanned_specs"] == 2


def test_gather_open_questions_silent_when_question_closed(tmp_path: Path):
    repo = _open_questions_repo(tmp_path)
    findings = sbc.gather_open_questions_reconcile(repo)
    closed_paths = [f for f in findings if "spec-charter-closed" in f.evidence.get("path", "")]
    assert not closed_paths


def test_gather_open_questions_ok_when_no_memlog(tmp_path: Path):
    spec_dir = tmp_path / "docs" / "governance" / "spec-no-memlog"
    spec_dir.mkdir(parents=True)
    shutil.copytree(_FIXTURES / "spec-no-memlog", spec_dir, dirs_exist_ok=True)
    findings = sbc.gather_open_questions_reconcile(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert findings[0].evidence["scanned_specs"] == 0


def test_gather_live_charter_case():
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather_open_questions_reconcile(repo_root)
    charter_hits = [
        f
        for f in findings
        if f.check == sbc._CHECK_OPEN_QUESTIONS and f.evidence.get("path", "").endswith("spec-pyforge-charter/SPEC.md")
    ]
    assert not charter_hits, "live charter was reconciled 2026-09-09; fixture covers the firing case"
    scanned = next(
        (f.evidence.get("scanned_specs") for f in findings if "scanned_specs" in f.evidence),
        None,
    )
    assert scanned and scanned > 0


def test_gather_combined_includes_cap2(tmp_path: Path):
    repo = _open_questions_repo(tmp_path)
    findings = sbc.gather(repo)
    assert any(f.check == sbc._CHECK_OPEN_QUESTIONS for f in findings)


def test_gather_degrades_on_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    repo = _open_questions_repo(tmp_path)

    def _boom(_target: Path) -> tuple[()]:
        raise RuntimeError("simulated")

    monkeypatch.setattr(sbc, "_gather_all", _boom)
    findings = sbc.gather(repo)
    assert len(findings) == 1
    assert findings[0].source == Source.STATUS_BODY_CONSISTENCY
    assert findings[0].status == DoctorStatus.WARN
