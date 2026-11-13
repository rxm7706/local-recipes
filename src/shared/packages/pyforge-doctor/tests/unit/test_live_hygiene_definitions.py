"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_hygiene_definitions.py``.

These rows read their fixtures straight off disk: the actual archived and
live artifacts each ``pyforge.doctor.hygiene_definitions`` predicate was
written to classify (this repo's archive-don't-delete convention keeps them
there). They run in the station's live-tree half; every inlined or synthetic
row stays in ``test_hygiene_definitions.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pyforge.doctor import hygiene_definitions as hd

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _require_repo_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


def test_is_dead_test_scaffolding_true_for_the_archived_doctor_test_tree():
    """Positive: ``archive/_bmad-output/projects/pyforge-doctor/tests/``
    holds a ``conftest.py`` plus seven ``__init__.py``-only subpackages and
    zero ``test_*.py`` files (``22da995c``)."""
    repo_root = _require_repo_root()
    fixture_dir = repo_root / "archive" / "_bmad-output" / "projects" / "pyforge-doctor" / "tests"
    relpaths = [str(p.relative_to(fixture_dir)) for p in sorted(fixture_dir.rglob("*.py"))]
    assert relpaths, "the archived fixture tree is unexpectedly empty"
    assert hd.is_dead_test_scaffolding(relpaths) is True


def test_is_hollow_sprint_status_true_for_the_archived_sprint_status():
    """Positive: ``archive/.../pyforge-doctor/planning-artifacts/
    sprint-status.yaml`` carries ``epics: []``, ``stories: []``,
    ``completion_percentage: 0%`` (``f7654a4c``, CAP-2)."""
    repo_root = _require_repo_root()
    fixture = (
        repo_root
        / "archive"
        / "_bmad-output"
        / "projects"
        / "pyforge-doctor"
        / "planning-artifacts"
        / "sprint-status.yaml"
    )
    parsed = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    assert hd.is_hollow_sprint_status(parsed) is True


def test_is_hollow_sprint_status_false_for_the_live_sprint_status_ledger():
    """Negative: the live, tracked ``sprint-status-ledger.yaml`` carries real
    per-story ``done``/``in-progress`` entries, not the ``epics: []``/
    ``stories: []`` shape."""
    repo_root = _require_repo_root()
    fixture = (
        repo_root / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts" / "sprint-status-ledger.yaml"
    )
    parsed = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    assert hd.is_hollow_sprint_status(parsed) is False


def test_is_readme_placeholder_false_for_the_live_readme():
    """Negative: this repo's current, live README carries real per-station
    prose, post-CAP-4."""
    repo_root = _require_repo_root()
    fixture = repo_root / "_bmad-output" / "projects" / "pyforge-doctor" / "README.md"
    content = fixture.read_text(encoding="utf-8")
    assert hd.is_readme_placeholder(content) is False


def test_is_orphan_file_true_for_the_self_marked_closed_resume_doc():
    """Positive: ``archive/_bmad-output/projects/pyforge-atlas/
    RESUME-EPIC-10.md``, self-marked with a "✅ CLOSED" banner, has no
    inbound reference (``f7654a4c``, CAP-5)."""
    repo_root = _require_repo_root()
    fixture = repo_root / "archive" / "_bmad-output" / "projects" / "pyforge-atlas" / "RESUME-EPIC-10.md"
    assert fixture.is_file()
    assert hd.is_orphan_file("RESUME-EPIC-10.md", has_inbound_references=False) is True


def test_is_orphan_file_true_for_the_unbannered_herald_intake_draft():
    """Positive: ``archive/.../pyforge-herald/planning-artifacts/
    intake-video-scripts-manticore-2026-07-31.md`` has NO closure banner at
    all — proves the predicate does not require one (``f7654a4c``, CAP-5)."""
    repo_root = _require_repo_root()
    fixture = (
        repo_root
        / "archive"
        / "_bmad-output"
        / "projects"
        / "pyforge-herald"
        / "planning-artifacts"
        / "intake-video-scripts-manticore-2026-07-31.md"
    )
    content = fixture.read_text(encoding="utf-8")
    assert "closed" not in content.lower() and "retired" not in content.lower()
    relpath = "planning-artifacts/intake-video-scripts-manticore-2026-07-31.md"
    assert hd.is_orphan_file(relpath, has_inbound_references=False) is True
