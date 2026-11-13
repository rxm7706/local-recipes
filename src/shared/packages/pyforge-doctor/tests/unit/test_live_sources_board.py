"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_board.py``.

These four tests judge ``board`` against this repository's own Specs and
roster (``DEFERRED_SPECS`` live status, the chain-completeness gather, the
roster-derived Spec-status sets), so they run in the station's live-tree half.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.sources import board

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _require_repo_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


def _resolve_spec_md(repo_root: Path, slug: str) -> Path | None:
    """Locate a tracked SPEC.md for ``slug`` under this repository's layout."""
    governance = repo_root / "docs" / "governance" / slug / "SPEC.md"
    if governance.is_file():
        return governance
    matches = sorted(repo_root.glob(f"_bmad-output/projects/*/planning-artifacts/specs/{slug}/SPEC.md"))
    return matches[0] if matches else None


def test_deferred_specs_entries_name_open_specs_live() -> None:
    """Every ``DEFERRED_SPECS`` slug must resolve to a Spec whose live
    ``status:`` is in ``OPEN_SPEC_STATUSES`` — an inert terminal entry fails
    here instead of silently accumulating (Story 21.1)."""
    repo_root = _require_repo_root()
    stale: list[str] = []

    for slug in board.DEFERRED_SPECS:
        spec_md = _resolve_spec_md(repo_root, slug)
        assert spec_md is not None, f"{slug} has no tracked SPEC.md in this repository"
        status = str(board._frontmatter(spec_md).get("status", "")).strip()
        if status not in board.OPEN_SPEC_STATUSES:
            stale.append(f"{slug} (status={status!r} at {spec_md.relative_to(repo_root)})")

    assert not stale, (
        "DEFERRED_SPECS contains entries whose Specs are no longer open — "
        "remove them rather than leaving inert exemptions:\n  " + "\n  ".join(stale)
    )


_STATION_SPECS = (
    "spec-pyforge-atlas",
    "spec-pyforge-doctor",
    "spec-pyforge-marshal",
    "spec-pyforge-scribe",
    "spec-pyforge-steward",
    "spec-pyforge-warden",
)


def test_live_tree_no_spec_not_decomposed_on_station_specs() -> None:
    """Story 41.6: fold-provenance citations in each station's ``epics.md`` cover
    declared CAPs — no false ``spec-not-decomposed`` on the six station Specs."""
    repo_root = _require_repo_root()
    findings = board.gather_chain_completeness(repo_root)
    bad = [f for f in findings if f.check == "spec-not-decomposed" and f.evidence.get("subject") in _STATION_SPECS]
    assert not bad, "live tree still reports spec-not-decomposed on station Specs:\n  " + "\n  ".join(
        f"{f.evidence.get('project')}/{f.evidence.get('subject')}: {f.message}" for f in bad
    )


def test_live_tree_reports_zero_spec_status_missing() -> None:
    """After Class-B status flips, no tracked Spec should lack a ``status:``
    key — the live tree must report zero ``spec-status-missing`` findings."""
    repo_root = _require_repo_root()
    findings = board.gather_chain_completeness(repo_root)
    missing = [f for f in findings if f.check == "spec-status-missing"]
    assert not missing, "live tree still has Specs with no status: key:\n  " + "\n  ".join(
        f"{f.evidence['project']}/{f.evidence['subject']}: {f.message}" for f in missing
    )


def test_live_wiring_matches_module_fallback() -> None:
    """The live-derived open/delivered Spec-status sets -- read from the
    real repo's own ``guild-roster.json`` -- equal ``board``'s own fallback
    constants, proving the wiring actually works and not just the fallback
    path (Story 59.2)."""
    repo_root = _require_repo_root()
    open_statuses, delivered_statuses, degraded = board._spec_status_groups(repo_root)
    assert degraded is None
    assert open_statuses == board.OPEN_SPEC_STATUSES
    assert delivered_statuses == board.DELIVERED_SPEC_STATUSES
