"""Unit tests for ``sources.status_body_consistency`` (Story 21.12 / CAP-1)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import status_body_consistency as sbc

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "status_body"


def _write_roster(target: Path) -> None:
    """A valid ``guild-roster.json`` whose declared terminal/ended-acts values
    derive the same ``{"shipped"}`` Spec-side member ``TERMINAL_STATUSES``
    already carries -- Story 59.2 sources it from this file, read fresh per
    call rather than a hardcoded module constant."""
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


def _mini_repo(tmp_path: Path) -> Path:
    """Fixture tree: one firing Dream, one firing Spec, one silent Dream."""
    _write_roster(tmp_path)
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    shutil.copy(_FIXTURES / "pyforge-scribe-dream.md", dreams / "pyforge-scribe.md")
    shutil.copy(
        _FIXTURES / "complete-realized-dream.md",
        dreams / "complete-station.md",
    )
    shutil.copy(
        _FIXTURES / "unparseable-dream.md",
        dreams / "unparseable.md",
    )
    spec_dir = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-scribe"
        / "planning-artifacts"
        / "specs"
        / "spec-pyforge-scribe"
    )
    spec_dir.mkdir(parents=True)
    shutil.copy(_FIXTURES / "spec-pyforge-scribe" / "SPEC.md", spec_dir / "SPEC.md")
    return tmp_path


def test_scan_body_fires_on_n_of_m_stories_with_n_lt_m():
    matches = sbc.scan_body_for_incomplete_progress("Overall **3 of 9 stories complete** across epics.\n")
    assert len(matches) == 1
    assert matches[0].line_no == 1
    assert matches[0].n == 3
    assert matches[0].m == 9


def test_scan_body_fires_on_hyphenated_n_of_m():
    matches = sbc.scan_body_for_incomplete_progress(
        "A shipped Spec whose § Why described a 3-of-9 station made a reader\n"
    )
    assert len(matches) == 1
    assert matches[0].matched == "3-of-9"


def test_scan_body_fires_on_slash_form_with_context():
    matches = sbc.scan_body_for_incomplete_progress("Progress is 3/9 stories across the backlog.\n")
    assert len(matches) == 1
    assert matches[0].matched == "3/9"


def test_scan_body_silent_on_dotted_story_id_pair():
    # "Stories 20.4/20.5" reads as two dotted epic.story IDs, not a 4/20
    # fraction, even though the bare digits satisfy n < m.
    matches = sbc.scan_body_for_incomplete_progress("Stories 20.4/20.5 are `done`: they park the attempt.\n")
    assert matches == ()


def test_scan_body_silent_on_hyphenated_story_id_pair():
    matches = sbc.scan_body_for_incomplete_progress("for Stories 11-2/11-3/11-4 — Pattern B demonstrated.\n")
    assert matches == ()


def test_scan_body_silent_on_slash_joined_id_list():
    matches = sbc.scan_body_for_incomplete_progress("closes the sibling's own CAP-8/9/10 (Epic 9, in progress).\n")
    assert matches == ()


def test_scan_body_silent_when_n_equals_m():
    assert sbc.scan_body_for_incomplete_progress("All 9 of 9 stories done.\n") == ()


def test_scan_body_silent_when_n_greater_than_m():
    assert sbc.scan_body_for_incomplete_progress("Odd count 10 of 9 stories.\n") == ()


def test_gather_fires_on_fixture_dream_and_spec_and_records_silent_count(tmp_path: Path):
    repo = _mini_repo(tmp_path)
    findings = sbc.gather_progress_phrase(repo)

    progress = [f for f in findings if f.check == sbc._CHECK_PROGRESS]
    assert len(progress) == 2

    dream_hit = next(f for f in progress if f.evidence["path"].endswith("pyforge-scribe.md"))
    assert dream_hit.status == DoctorStatus.WARN
    assert "3 of 9 stories" in dream_hit.evidence["matched"]
    assert "3 of 9 stories" in dream_hit.message
    assert dream_hit.evidence["status"] == "realized"
    assert "wrong" not in dream_hit.message.casefold()
    assert "broken" not in dream_hit.message.casefold()

    spec_hit = next(f for f in progress if "spec-pyforge-scribe" in f.evidence["path"])
    assert spec_hit.evidence["status"] == "shipped"
    assert "3-of-9" in spec_hit.message

    unparseable = [f for f in findings if f.check == sbc._CHECK_UNPARSEABLE]
    assert len(unparseable) == 1
    assert unparseable[0].evidence["path"].endswith("unparseable.md")

    assert progress[0].evidence["scanned_terminal"] == 3
    assert progress[0].evidence["silent"] == 1
    assert progress[0].evidence["fired"] == 2


def test_gather_ok_when_no_terminal_docs(tmp_path: Path):
    repo = tmp_path / "empty"
    repo.mkdir()
    _write_roster(repo)
    (repo / "docs" / "dreams").mkdir(parents=True)
    findings = sbc.gather_progress_phrase(repo)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert findings[0].evidence["scanned_terminal"] == 0
    # Positive proof the live roster was actually read, not a silent
    # degrade-to-fallback that happens to produce the same OK result.
    assert not any(f.check == "spec-status-roster-degraded" for f in findings)


def test_gather_missing_roster_degrades_to_fallback_and_warns(tmp_path: Path):
    """No ``docs/governance/guild-roster.json`` at all still classifies
    terminal statuses correctly -- via ``TERMINAL_STATUSES``, the module's own
    fallback -- and surfaces a ``spec-status-roster-degraded`` WARN rather
    than crashing or degrading silently (Story 59.2)."""
    repo = tmp_path / "no-roster"
    repo.mkdir()
    (repo / "docs" / "dreams").mkdir(parents=True)
    findings = sbc.gather_progress_phrase(repo)
    assert len(findings) == 1
    assert findings[0].check == "spec-status-roster-degraded"
    assert findings[0].status == DoctorStatus.WARN
    assert findings[0].source == Source.STATUS_BODY_CONSISTENCY


def test_gather_live_dream_and_spec_progress_phrases():
    """Re-measured 2026-09-18: the live fleet no longer carries a
    progress-phrase contradiction (herald Dream cleaned; scribe already
    clean). Fixture tests above still prove the detector fires; this live
    pin only asserts the fleet stays silent."""
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather_progress_phrase(repo_root)
    progress = [f for f in findings if f.check == sbc._CHECK_PROGRESS]
    assert progress == []


def test_gather_degrades_on_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    repo = _mini_repo(tmp_path)

    def _boom(_target: Path) -> tuple[()]:
        raise RuntimeError("simulated")

    monkeypatch.setattr(sbc, "gather_progress_phrase", _boom)
    findings = sbc.gather(repo)
    assert len(findings) == 1
    assert findings[0].source == Source.STATUS_BODY_CONSISTENCY
    assert findings[0].status == DoctorStatus.WARN
    assert "status-body-consistency" in findings[0].message
