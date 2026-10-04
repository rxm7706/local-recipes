"""Every page's declared controls agree with DESIGN.md's own per-page Layout bullet.

Story 27.3, closing DW-FU-20-5 / DW-FU-20-8. Before this, ``PageDef`` carried no
notion of a filter or a chart at all: every DESIGN.md page whose Layout names a
``Filter`` or a ``Graph`` rendered as a Card + AgGrid and nothing else, and no
gate noticed. ``PageDef.filters`` / ``PageDef.chart`` now declare them and
``app._declared_filters`` / ``app._declared_chart`` render them.

This gate PARSES DESIGN.md rather than restating its table, so it reds on drift
from either side — a Layout bullet that grows a ``Graph`` with no ``ChartDef``,
or a ``ChartDef`` on a page whose Layout never asked for one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyforge.atlas.dashboard import app

DESIGN_MD = (
    Path(__file__).resolve().parents[4].parent
    / "_bmad-output/projects/pyforge-atlas/planning-artifacts/DESIGN.md"
)

# A DESIGN.md page section header: "### 3.1 `cve-watcher` — CVE Watch".
_SECTION = re.compile(r"^#{3}\s+\d+\.\d+\s+`([a-z0-9-]+)`", re.MULTILINE)
_LAYOUT = re.compile(r"^-\s+\*\*Layout:?\*\*:?\s*(.*?)(?=^-\s+\*\*)", re.MULTILINE | re.DOTALL)

# The live-scan pages (§ 3.6, § 3.7) take their input as a path field + Run
# button, not a vm.Filter over an already-materialized frame: the frame does not
# exist until the scan runs. DESIGN.md § 3.6 says so itself ("an upload/path
# `Filter`"), so a Layout Filter on one of these pages is satisfied by that
# control -- see app._scan_page and dashboard/scan_submit.py.
_PATH_INPUT_PAGES = frozenset({"scan-project", "env-inspect"})


def _design_controls() -> dict[str, dict[str, bool]]:
    """Per page id, whether DESIGN.md's Layout bullet names a Filter and a Graph."""
    text = DESIGN_MD.read_text(encoding="utf-8")
    sections: dict[str, dict[str, bool]] = {}
    matches = list(_SECTION.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start() : end]
        layout = _LAYOUT.search(body)
        assert layout is not None, f"DESIGN.md § for {match.group(1)!r} has no Layout bullet"
        bullet = layout.group(1)
        sections[match.group(1)] = {
            "filter": "`Filter`" in bullet,
            "graph": "`Graph`" in bullet,
        }
    return sections


DESIGN_CONTROLS = _design_controls()
INVENTORY = {page.id: page for page in app.PAGE_INVENTORY}


def test_design_md_parses_into_the_nineteen_page_sections() -> None:
    """A parse that silently matched nothing would make every case below vacuous."""
    assert len(DESIGN_CONTROLS) == 19, sorted(DESIGN_CONTROLS)
    assert set(DESIGN_CONTROLS) <= set(INVENTORY), sorted(set(DESIGN_CONTROLS) - set(INVENTORY))
    assert any(spec["filter"] for spec in DESIGN_CONTROLS.values())
    assert any(spec["graph"] for spec in DESIGN_CONTROLS.values())


@pytest.mark.parametrize("page_id", sorted(DESIGN_CONTROLS))
def test_declared_filters_match_the_design_layout_bullet(page_id: str) -> None:
    page = INVENTORY[page_id]
    wants_filter = DESIGN_CONTROLS[page_id]["filter"]
    has_control = bool(page.filters) or (page_id in _PATH_INPUT_PAGES and wants_filter)
    assert has_control == wants_filter, (
        f"{page_id}: DESIGN.md Layout {'names' if wants_filter else 'does not name'} a Filter "
        f"but PageDef.filters is {page.filters!r}"
    )


@pytest.mark.parametrize("page_id", sorted(DESIGN_CONTROLS))
def test_declared_chart_matches_the_design_layout_bullet(page_id: str) -> None:
    page = INVENTORY[page_id]
    wants_graph = DESIGN_CONTROLS[page_id]["graph"]
    assert (page.chart is not None) == wants_graph, (
        f"{page_id}: DESIGN.md Layout {'names' if wants_graph else 'does not name'} a Graph "
        f"but PageDef.chart is {page.chart!r}"
    )


@pytest.mark.parametrize("page_id", sorted(page.id for page in app.PAGE_INVENTORY if page.filters or page.chart))
def test_every_declared_control_names_a_column_the_page_can_actually_serve(page_id: str) -> None:
    """A declared filter column or chart axis that no loader column backs would
    render as nothing (``_declared_filters`` skips an absent column by design, so
    a typo would be invisible). Pin each one against the page's own key columns."""
    page = INVENTORY[page_id]
    declared = set(page.filters)
    if page.chart is not None:
        declared |= {page.chart.x, page.chart.y}
    missing = declared - set(page.columns)
    assert not missing, f"{page_id}: declared control column(s) {sorted(missing)} not in PageDef.columns"


def test_the_two_live_scan_pages_declare_no_vizro_filter() -> None:
    """Their input is a path field, not a selector over an existing frame."""
    for page_id in _PATH_INPUT_PAGES:
        page = INVENTORY[page_id]
        assert page.kind == "live-scan-artifact"
        assert page.filters == ()
        assert page.chart is None
