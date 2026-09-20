"""Unit tests for ``pyforge.doctor.sources.board`` helpers and invariants
(Story 21.1 — ``DEFERRED_SPECS`` live-status reconciliation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.sources import board

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None


def _require_repo_root() -> Path:
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")
    return _REPO_ROOT


def _resolve_spec_md(repo_root: Path, slug: str) -> Path | None:
    """Locate a tracked SPEC.md for ``slug`` under the monorepo layout."""
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
        assert spec_md is not None, f"{slug} has no tracked SPEC.md in the monorepo"
        status = str(board._frontmatter(spec_md).get("status", "")).strip()
        if status not in board.OPEN_SPEC_STATUSES:
            stale.append(f"{slug} (status={status!r} at {spec_md.relative_to(repo_root)})")

    assert not stale, (
        "DEFERRED_SPECS contains entries whose Specs are no longer open — "
        "remove them rather than leaving inert exemptions:\n  " + "\n  ".join(stale)
    )


def test_live_tree_reports_zero_spec_status_missing() -> None:
    """After Class-B status flips, no tracked Spec should lack a ``status:``
    key — the live monorepo must report zero ``spec-status-missing`` findings."""
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


def test_deferred_specs_story_21_1_reconciliation() -> None:
    """Pin Story 21.1 de-registrations and registrations against silent regression."""
    assert "spec-intelligence-hub" not in board.DEFERRED_SPECS
    assert "spec-artifact-chain-reconciliation" not in board.DEFERRED_SPECS
    assert "spec-chain-currency-sweep" not in board.DEFERRED_SPECS
    assert "spec-bmad-cursor-interactive-routing" not in board.DEFERRED_SPECS
    assert "spec-golden-path-conda-blind-spot" not in board.DEFERRED_SPECS
    assert "spec-agentic-sdlc-autonomy" not in board.DEFERRED_SPECS
    assert "spec-pyforge-charter" in board.DEFERRED_SPECS
    assert board.DEFERRED_SPECS["spec-pyforge-charter"] == (
        "a constitutive Spec whose CAP-1/4/5/6/8 are document-integrity properties "
        "no story can pick up; CAP-3 mechanism shipped as doctor 21.4; CAP-7/AUT-3 "
        "wait on the Guildhall referent — do not mint a Charter epic"
    )
