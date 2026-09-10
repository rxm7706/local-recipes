"""Unit tests for ``sources.status_body_consistency`` CAP-4 (Story 21.15)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import status_body_consistency as sbc

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "status_body"


def _write_ledger(repo: Path, project: str, statuses: dict[str, str]) -> None:
    ledger_path = (
        repo
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "sprint-status-ledger.yaml"
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:"]
    lines.extend(f"  {key}: {value}" for key, value in sorted(statuses.items()))
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _status_comment_repo(tmp_path: Path) -> Path:
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    shutil.copy(_FIXTURES / "contradiction-dream.md", dreams / "contradiction.md")
    shutil.copy(_FIXTURES / "no-key-dream.md", dreams / "no-key.md")
    shutil.copy(_FIXTURES / "unresolvable-dream.md", dreams / "unresolvable.md")
    shutil.copy(_FIXTURES / "agreement-dream.md", dreams / "agreement.md")
    _write_ledger(
        tmp_path,
        "pyforge-doctor",
        {
            "epic-10": "done",
            "epic-14": "done",
            "21-15-fixture-story": "backlog",
        },
    )
    return tmp_path


def test_status_comment_text_collects_continuation_lines():
    text = (
        "---\n"
        "status: realized   # first line\n"
        "                   # → Epic 14 backlog\n"
        "---\n"
    )
    comment, line_no = sbc.status_comment_text(text)
    assert line_no == 2
    assert "Epic 14 backlog" in comment


def test_parse_status_comment_references_epic_and_story():
    refs = sbc.parse_status_comment_references(
        "suite extension → Epic 14 backlog; Story 21.15 backlog"
    )
    assert len(refs) == 2
    assert refs[0].ledger_key == "epic-14"
    assert refs[0].claimed_status == "backlog"
    assert refs[1].ledger_key == "21-15"
    assert refs[1].claimed_status == "backlog"


def test_parse_status_comment_references_ignores_keyless_comment():
    assert sbc.parse_status_comment_references(
        "2026-08-22 — decomposed into the station backlog same day"
    ) == ()


def test_gather_status_comment_fires_on_contradiction(tmp_path: Path):
    repo = _status_comment_repo(tmp_path)
    findings = sbc.gather_status_comment_reconcile(repo)
    hits = [f for f in findings if f.check == sbc._CHECK_STATUS_COMMENT]
    assert len(hits) == 1
    hit = hits[0]
    assert hit.status == DoctorStatus.WARN
    assert hit.evidence["ledger_key"] == "epic-14"
    assert hit.evidence["claimed_status"] == "backlog"
    assert hit.evidence["ledger_status"] == "done"
    assert "Epic 14 backlog" in hit.message
    assert "epic-14" in hit.message


def test_gather_status_comment_ignores_no_key_comment(tmp_path: Path):
    repo = _status_comment_repo(tmp_path)
    findings = sbc.gather_status_comment_reconcile(repo)
    no_key_paths = [
        f for f in findings if f.evidence.get("path", "").endswith("no-key.md")
    ]
    assert not no_key_paths


def test_gather_status_comment_reports_unresolvable_key(tmp_path: Path):
    repo = _status_comment_repo(tmp_path)
    findings = sbc.gather_status_comment_reconcile(repo)
    hits = [
        f
        for f in findings
        if f.check == sbc._CHECK_STATUS_COMMENT_UNRESOLVABLE
    ]
    assert len(hits) == 1
    assert hits[0].evidence["ledger_key"] == "epic-99"
    assert "epic-99" in hits[0].message


def test_gather_status_comment_silent_when_comment_agrees(tmp_path: Path):
    repo = _status_comment_repo(tmp_path)
    findings = sbc.gather_status_comment_reconcile(repo)
    agreement_paths = [
        f for f in findings if f.evidence.get("path", "").endswith("agreement.md")
    ]
    assert not agreement_paths


def test_gather_live_bmad_method_version_drift_case():
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather_status_comment_reconcile(repo_root)
    hits = [
        f
        for f in findings
        if f.check == sbc._CHECK_STATUS_COMMENT
        and f.evidence.get("path") == "docs/dreams/bmad-method-version-drift.md"
    ]
    assert hits, "expected live bmad-method-version-drift status-comment finding"
    assert hits[0].evidence["ledger_key"] == "epic-14"
    assert hits[0].evidence["claimed_status"] == "backlog"
    assert hits[0].evidence["ledger_status"] == "done"


def test_gather_combined_includes_cap4(tmp_path: Path):
    repo = _status_comment_repo(tmp_path)
    findings = sbc.gather(repo)
    assert any(f.check == sbc._CHECK_STATUS_COMMENT for f in findings)


def test_gather_degrades_on_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    repo = _status_comment_repo(tmp_path)

    def _boom(_target: Path) -> tuple[()]:
        raise RuntimeError("simulated")

    monkeypatch.setattr(sbc, "_gather_all", _boom)
    findings = sbc.gather(repo)
    assert len(findings) == 1
    assert findings[0].source == Source.STATUS_BODY_CONSISTENCY
    assert findings[0].status == DoctorStatus.WARN
