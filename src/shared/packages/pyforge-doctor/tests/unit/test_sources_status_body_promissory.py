"""Unit tests for ``sources.status_body_consistency`` CAP-3 (Story 21.14)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import status_body_consistency as sbc

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "status_body"


def _write_roster(target: Path) -> None:
    """A valid ``guild-roster.json`` whose declared terminal/ended-acts values
    derive the same ``{"shipped"}`` Spec-side member ``TERMINAL_STATUSES``
    already carries (Story 59.2) -- keeps CAP-1's own gather silent here so
    ``gather()``'s combined branching (which this file's CAP-3 tests rely on)
    is unaffected by a roster-missing WARN from an unrelated CAP."""
    path = target / "docs" / "governance" / "guild-roster.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "spec_statuses_terminal": [
                    "shipped",
                    "archived",
                    "absorbed",
                    "superseded",
                ],
                "spec_statuses_ended_acts": [
                    "archived",
                    "absorbed",
                    "superseded",
                ],
            }
        ),
        encoding="utf-8",
    )


def _promissory_repo(tmp_path: Path) -> Path:
    _write_roster(tmp_path)
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    shutil.copy(_FIXTURES / "pyforge-herald-dream.md", dreams / "pyforge-herald.md")
    shutil.copy(_FIXTURES / "quiet-realized-dream.md", dreams / "quiet-station.md")
    spec_dir = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-herald"
        / "planning-artifacts"
        / "specs"
        / "spec-pyforge-herald"
    )
    spec_dir.mkdir(parents=True)
    shutil.copy(_FIXTURES / "spec-pyforge-herald" / "SPEC.md", spec_dir / "SPEC.md")
    return tmp_path


def test_scan_body_fires_on_active_now_heading():
    matches = sbc.scan_body_for_promissory_language("## The frontier — Moments 2–4, active now\n\nLead text.\n")
    assert len(matches) == 1
    assert matches[0].pattern_id == "active-now"
    assert matches[0].surface_kind == "heading"


def test_scan_body_fires_on_mid_build_spec_phrase():
    matches = sbc.scan_body_for_promissory_language(
        "## Why\n\n"
        "**Current state (re-grounded; described a mid-build\n"
        "station and contradicted this Spec's own `status: shipped`).**\n"
    )
    assert {m.pattern_id for m in matches} == {
        "mid-build-described",
        "contradicted-shipped-status",
    }


def test_measure_precision_fixture_repo(tmp_path: Path):
    repo = _promissory_repo(tmp_path)
    measurement = sbc.measure_promissory_language_precision(repo)
    assert measurement.scanned_terminal == 3
    assert measurement.herald_pair_fired == 2
    assert measurement.false_positive_documents == 0
    assert measurement.precision == 1.0
    assert measurement.accepted is True


def test_gather_promissory_fires_on_fixture_pair_and_stays_quiet(tmp_path: Path):
    repo = _promissory_repo(tmp_path)
    findings = sbc.gather_promissory_language(repo)
    promissory = [f for f in findings if f.check == sbc._CHECK_PROMISSORY]
    assert promissory
    assert all(f.status == DoctorStatus.WARN for f in promissory)

    dream_paths = {f.evidence["path"] for f in promissory if f.evidence["path"].endswith("pyforge-herald.md")}
    spec_paths = {f.evidence["path"] for f in promissory if "spec-pyforge-herald" in f.evidence["path"]}
    assert dream_paths
    assert spec_paths
    assert promissory[0].evidence["silent"] == 1
    assert promissory[0].evidence["accepted"] is True


def test_gather_live_herald_pair_and_zero_false_positives():
    """Re-measured 2026-09-18 (was herald_pair_fired == 1): the Dream side of
    the known pair was cleaned too -- zero live promissory hits, still zero
    false positives, still `accepted`. Fixture tests above still prove the
    detector fires.

    Re-measured again 2026-09-19: the live scan is now fully clean -- the last
    non-promissory finding (an `unparseable` WARN for the unquoted `title:`
    in `docs/dreams/pyforge-mason-recipe-validator.md`) was reconciled by PR
    #1493 -- so `gather_promissory_language` emits its clean-state OK summary
    (same `check`, `status: OK`, see `test_gather_measured_and_rejected_when_
    not_accepted` for the shape). That summary is the *absence* of a hit, so
    the assertion filters on the WARN status a real hit carries; a bare
    `check ==` filter read the summary as a hit and redded the station gate on
    `main` the moment the tree got clean (doctor dispatch 28.1, MRS-GATE-001)."""
    repo_root = Path(__file__).resolve().parents[6]
    measurement = sbc.measure_promissory_language_precision(repo_root)
    assert measurement.herald_pair_fired == 0
    assert measurement.false_positive_documents == 0
    assert measurement.accepted is True
    assert sbc.PROMISSORY_LANGUAGE_ACCEPTED is True

    findings = sbc.gather_promissory_language(repo_root)
    promissory = [f for f in findings if f.check == sbc._CHECK_PROMISSORY and f.status is DoctorStatus.WARN]
    assert promissory == []
    # Every finding the live gather returns is either the clean-state OK
    # summary or a non-promissory WARN (an unparseable/unreadable document);
    # never a promissory hit.
    assert all(f.status is DoctorStatus.OK or f.check != sbc._CHECK_PROMISSORY for f in findings)


def test_gather_combined_includes_cap3(tmp_path: Path):
    repo = _promissory_repo(tmp_path)
    findings = sbc.gather(repo)
    assert any(f.check == sbc._CHECK_PROMISSORY for f in findings)


def test_scan_body_silent_on_quiet_fixture():
    body = Path(_FIXTURES / "quiet-realized-dream.md").read_text(encoding="utf-8")
    body = sbc._body_after_frontmatter(body)
    assert sbc.scan_body_for_promissory_language(body) == ()


def test_gather_measured_and_rejected_when_not_accepted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    repo = _promissory_repo(tmp_path)
    monkeypatch.setattr(sbc, "PROMISSORY_LANGUAGE_ACCEPTED", False)
    findings = sbc.gather_promissory_language(repo)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert "measured-and-rejected" in findings[0].message
    assert findings[0].evidence["accepted"] is False

    combined = sbc.gather(repo)
    assert len(combined) == 1
    assert "measured-and-rejected" in combined[0].message
    assert combined[0].evidence["accepted"] is False


def test_gather_live_includes_cap1_and_cap3_together():
    """Re-measured 2026-09-18: CAP-1/CAP-3 live hits are zero (fleet cleaned).
    Combined gather still returns other status-body checks; fixture tests
    cover CAP-1/CAP-3 firing."""
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather(repo_root)
    checks = {f.check for f in findings}
    assert sbc._CHECK_PROGRESS not in checks
    assert sbc._CHECK_PROMISSORY not in checks
    assert checks  # still reports other live status-body findings
