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
    matches = sorted(
        repo_root.glob(f"_bmad-output/projects/*/planning-artifacts/specs/{slug}/SPEC.md")
    )
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
        text = spec_md.read_text(encoding="utf-8")
        status = str(board._frontmatter_from_text(text).get("status", "")).strip()
        if status not in board.OPEN_SPEC_STATUSES:
            stale.append(f"{slug} (status={status!r} at {spec_md.relative_to(repo_root)})")

    assert not stale, (
        "DEFERRED_SPECS contains entries whose Specs are no longer open — "
        "remove them rather than leaving inert exemptions:\n  "
        + "\n  ".join(stale)
    )
