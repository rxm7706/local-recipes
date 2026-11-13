"""Story 62.3 — the tracked measure catalog allows an ``on`` cite (spec-build-league-scorecard CAP-3).

Moved from ``test_league_measure.py`` with their names unchanged (Story 117.1,
spec-pyforge-core:CAP-14): both read steward's tracked ``measure-catalog.md``,
outside this package, so they run in the core suite's live-tree half. The root
comes from this file's own location, never ``Path.cwd()``, and the catalog is
read through its literal path, so steward's station-tests trigger map derives
the read; ``test_cite_on_allowed`` hands the root to ``validate_measure_cite``.
The module stays under ``tests/unit`` so the pip-install lane, which runs
``tests/unit`` whole, keeps running it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.core.league_measure import MeasureCiteVerdict, parse_measure_catalog, validate_measure_cite

pytestmark = pytest.mark.live_tree

# tests/unit -> tests -> pyforge-core -> packages -> shared -> src -> repo root. A bare copy of the package can sit
# shallower than that; the module still imports (it holds path constants only) and its tests are live_tree.
try:
    REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    REPO_ROOT = None


def test_cite_on_allowed() -> None:
    verdict = validate_measure_cite("warden-verdict", repo_root=REPO_ROOT)
    assert verdict == MeasureCiteVerdict(allowed=True, measure_id="warden-verdict", state="on", reason=None)


def test_live_repo_catalog_has_eight_on_rows() -> None:
    catalog = (
        REPO_ROOT
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/measure-catalog.md"
    )
    states = parse_measure_catalog(catalog.read_text(encoding="utf-8"))
    assert len(states) == 8  # noqa: PLR2004
    assert all(state == "on" for state in states.values())
