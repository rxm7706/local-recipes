"""Unit tests for ``sources.status_body_consistency`` (Story 21.12 / CAP-1)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import status_body_consistency as sbc

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "status_body"


def _mini_repo(tmp_path: Path) -> Path:
    """Fixture tree: one firing Dream, one firing Spec, one silent Dream."""
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
    matches = sbc.scan_body_for_incomplete_progress(
        "Overall **3 of 9 stories complete** across epics.\n"
    )
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
    matches = sbc.scan_body_for_incomplete_progress(
        "Progress is 3/9 stories across the backlog.\n"
    )
    assert len(matches) == 1
    assert matches[0].matched == "3/9"


def test_scan_body_silent_on_dotted_story_id_pair():
    # "Stories 20.4/20.5" reads as two dotted epic.story IDs, not a 4/20
    # fraction, even though the bare digits satisfy n < m.
    matches = sbc.scan_body_for_incomplete_progress(
        "Stories 20.4/20.5 are `done`: they park the attempt.\n"
    )
    assert matches == ()


def test_scan_body_silent_on_hyphenated_story_id_pair():
    matches = sbc.scan_body_for_incomplete_progress(
        "for Stories 11-2/11-3/11-4 — Pattern B demonstrated.\n"
    )
    assert matches == ()


def test_scan_body_silent_on_slash_joined_id_list():
    matches = sbc.scan_body_for_incomplete_progress(
        "closes the sibling's own CAP-8/9/10 (Epic 9, in progress).\n"
    )
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

    dream_hit = next(
        f for f in progress if f.evidence["path"].endswith("pyforge-scribe.md")
    )
    assert dream_hit.status == DoctorStatus.WARN
    assert "3 of 9 stories" in dream_hit.evidence["matched"]
    assert "3 of 9 stories" in dream_hit.message
    assert dream_hit.evidence["status"] == "realized"
    assert "wrong" not in dream_hit.message.casefold()
    assert "broken" not in dream_hit.message.casefold()

    spec_hit = next(
        f for f in progress if "spec-pyforge-scribe" in f.evidence["path"]
    )
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
    (repo / "docs" / "dreams").mkdir(parents=True)
    findings = sbc.gather_progress_phrase(repo)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert findings[0].evidence["scanned_terminal"] == 0


def test_gather_live_pyforge_scribe_cases():
    repo_root = Path(__file__).resolve().parents[6]
    findings = sbc.gather_progress_phrase(repo_root)
    progress = [f for f in findings if f.check == sbc._CHECK_PROGRESS]

    dream_paths = [
        f for f in progress if f.evidence["path"] == "docs/dreams/pyforge-scribe.md"
    ]
    assert dream_paths, "expected live pyforge-scribe Dream finding"
    assert any("3 of 9 stories" in f.evidence["matched"] for f in dream_paths)

    spec_paths = [
        f
        for f in progress
        if f.evidence["path"].endswith("pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md")
    ]
    assert spec_paths, "expected live spec-pyforge-scribe finding"


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
