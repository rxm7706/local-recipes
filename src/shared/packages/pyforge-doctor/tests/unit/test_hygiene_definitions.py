"""Unit tests for ``pyforge.doctor.hygiene_definitions`` (Story 9.1) — one
test per row of the story spec's I/O & Edge-Case Matrix (13 rows; the
story's own Tasks checklist undercounts this as "12" — the table itself is
authoritative, see the story spec's Auto Run Result).

Real positive fixtures are the actual archived/live artifacts each predicate
was written to classify, read straight off disk rather than re-typed by
hand (this repo's archive-don't-delete convention keeps them there). The two
commit-SHA-cited fixtures (the pre-fix README placeholder stub, the stale-
Dream status values) are inlined verbatim per the story spec's own
instruction — no ``git show`` subprocess call at test time; the literal text
was verified once, while writing this file, against the cited commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pyforge.doctor import hygiene_definitions as hd

# Guarded, mirroring `test_check_speed_budget.py`'s own idiom: this file
# sits at the identical `tests/unit/` depth, so `parents[6]` lands at the
# monorepo root. An IndexError (e.g. an extracted sdist, no monorepo
# ancestry) degrades to a skip for the fixtures below rather than a
# collection-time crash for the whole file.
try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None

_THIS_PACKAGE_TESTS = Path(__file__).resolve().parents[1]


def _require_repo_root() -> Path:
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")
    return _REPO_ROOT


# --- HygieneFindingKind: the closed set of five -----------------------------


def test_hygiene_finding_kind_has_exactly_five_members():
    assert len(hd.HygieneFindingKind) == 5


# --- is_dead_test_scaffolding ------------------------------------------------


def test_is_dead_test_scaffolding_true_for_the_archived_doctor_test_tree():
    """Positive: ``archive/_bmad-output/projects/pyforge-doctor/tests/``
    holds a ``conftest.py`` plus seven ``__init__.py``-only subpackages and
    zero ``test_*.py`` files (``22da995c``)."""
    repo_root = _require_repo_root()
    fixture_dir = repo_root / "archive" / "_bmad-output" / "projects" / "pyforge-doctor" / "tests"
    relpaths = [str(p.relative_to(fixture_dir)) for p in sorted(fixture_dir.rglob("*.py"))]
    assert relpaths, "the archived fixture tree is unexpectedly empty"
    assert hd.is_dead_test_scaffolding(relpaths) is True


def test_is_dead_test_scaffolding_false_for_this_packages_real_tests():
    """Negative: this repo's own ``src/shared/packages/pyforge-doctor/
    tests/`` tree holds real ``test_*.py`` files."""
    relpaths = [str(p.relative_to(_THIS_PACKAGE_TESTS)) for p in sorted(_THIS_PACKAGE_TESTS.rglob("*.py"))]
    assert hd.is_dead_test_scaffolding(relpaths) is False


# --- is_hollow_sprint_status --------------------------------------------------


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


def test_is_hollow_sprint_status_false_for_a_partial_match():
    """Negative (mutation-testing guard): only 2 of the 3 required
    conditions hold -- a mutation from `and` to `or` must not pass here."""
    partial = {"epics": [], "stories": [], "summary": {"completion_percentage": "50%"}}
    assert hd.is_hollow_sprint_status(partial) is False


def test_is_hollow_sprint_status_true_for_numeric_zero_completion():
    """Positive: `completion_percentage: 0` (numeric YAML) is the same
    hollow state as the string `"0%"` form the real fixture uses."""
    numeric = {"epics": [], "stories": [], "summary": {"completion_percentage": 0}}
    assert hd.is_hollow_sprint_status(numeric) is True


def test_is_hollow_sprint_status_false_for_none():
    """Negative: `yaml.safe_load` on an empty/whitespace-only file returns
    `None` -- must not raise."""
    assert hd.is_hollow_sprint_status(None) is False


def test_is_hollow_sprint_status_false_for_a_null_summary():
    """Negative: `summary:` present with an explicit `None` value must not
    raise (`dict.get`'s default only covers an absent key)."""
    null_summary = {"epics": [], "stories": [], "summary": None}
    assert hd.is_hollow_sprint_status(null_summary) is False


# --- is_readme_placeholder ----------------------------------------------------


def test_is_readme_placeholder_true_for_the_pre_fix_literal_stub():
    """Positive: verbatim from ``5c5e3727^:_bmad-output/projects/
    pyforge-doctor/README.md`` (CAP-4) — inlined per the story spec, no
    ``git show`` at test time."""
    content = "doctor is a [role] station in the PyForge factory, responsible for [responsibilities]."
    assert hd.is_readme_placeholder(content) is True


def test_is_readme_placeholder_false_for_the_live_readme():
    """Negative: this repo's current, live README carries real per-station
    prose, post-CAP-4."""
    repo_root = _require_repo_root()
    fixture = repo_root / "_bmad-output" / "projects" / "pyforge-doctor" / "README.md"
    content = fixture.read_text(encoding="utf-8")
    assert hd.is_readme_placeholder(content) is False


# --- is_stale_dream_status -----------------------------------------------------


def test_is_stale_dream_status_true_when_specified_and_all_done():
    """Positive: doctor's real state at ``bfa9fd68^`` — 16/16 stories done,
    status still ``specified`` (``bfa9fd68``)."""
    assert hd.is_stale_dream_status("specified", True) is True


def test_is_stale_dream_status_false_when_already_realized():
    """Negative: atlas's real pre-fix state — already ``realized``, never
    flagged regardless of completion."""
    assert hd.is_stale_dream_status("realized", True) is False


def test_is_stale_dream_status_false_when_genuinely_mid_flight():
    """Negative (synthetic, the logical negation of the positive case, not a
    separate shape): ``specified`` but not every story is done yet."""
    assert hd.is_stale_dream_status("specified", False) is False


# --- is_orphan_file --------------------------------------------------------------


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


def test_is_orphan_file_false_for_a_conventional_name_even_unreferenced():
    """Negative: ``epics.md`` is found by directory convention, not inbound
    reference — absence of a reference alone is never sufficient."""
    assert hd.is_orphan_file("planning-artifacts/epics.md", has_inbound_references=False) is False


def test_is_orphan_file_false_for_a_non_conventional_but_referenced_file():
    """Negative (synthetic): a non-conventional name is still not orphaned
    once something else in the repo references it."""
    assert hd.is_orphan_file("planning-artifacts/NOTES-random.md", has_inbound_references=True) is False


def test_is_orphan_file_false_for_a_conventional_directory():
    """Negative: the `_CONVENTIONAL_DIRECTORIES` branch, uncovered by any
    other test -- a file under `specs/` is conventional regardless of its
    own filename."""
    assert hd.is_orphan_file("planning-artifacts/specs/spec-9-1-foo.md", has_inbound_references=False) is False


def test_is_orphan_file_false_for_tea_test_design_artifacts():
    """Negative (Story 31.1, 2026-09-07): TEA's `bmad-testarch-test-design`
    output -- the fixed filenames, the `test-design/` handoff subdirectory,
    and the `reviews/` report directory -- are all conventional regardless
    of inbound reference, same shape as `test-architecture.md` above."""
    assert hd.is_orphan_file("planning-artifacts/test-design-architecture.md", has_inbound_references=False) is False
    assert hd.is_orphan_file("planning-artifacts/test-design-qa.md", has_inbound_references=False) is False
    assert hd.is_orphan_file("planning-artifacts/test-design-progress-system.md", has_inbound_references=False) is False
    assert (
        hd.is_orphan_file(
            "planning-artifacts/test-design/pyforge-marshal-handoff.md",
            has_inbound_references=False,
        )
        is False
    )
    assert (
        hd.is_orphan_file(
            "planning-artifacts/reviews/tea-equivalence-2026-09-07.md",
            has_inbound_references=False,
        )
        is False
    )


def test_is_orphan_file_false_for_a_conventional_filename_glob():
    """Negative: the `_CONVENTIONAL_FILENAME_GLOBS` branch, uncovered by any
    other test -- a dated readiness-report filename is conventional."""
    assert (
        hd.is_orphan_file(
            "planning-artifacts/implementation-readiness-report-2026-08-15.md",
            has_inbound_references=False,
        )
        is False
    )
