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
import shutil
from pathlib import Path

import pandas as pd
import pytest
from vizro import Vizro
from vizro.managers import model_manager

from pyforge.atlas.dashboard import app

_DESIGN_RELPATH = "_bmad-output/projects/pyforge-atlas/planning-artifacts/DESIGN.md"


def _design_md() -> Path:
    """Walk up to the repo root rather than counting ``parents[n]`` -- the package
    sits seven levels down and a move would silently re-point the constant."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / _DESIGN_RELPATH
        if candidate.is_file():
            return candidate
    pytest.skip(f"{_DESIGN_RELPATH} not reachable (installed package, no planning tree)")


DESIGN_MD = _design_md()

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


def test_a_declared_filter_column_the_loader_never_projects_refuses_loudly() -> None:
    """The one way a typo in ``PageDef.filters`` could hide: ``_declared_filters``
    skips a column with no non-null values (vizro cannot build a Filter over one),
    so an absent column must be told apart from an empty one and refused."""
    page = app.PageDef("probe", "Probe", "probe", "bsl-shell", filters=("facet",))

    # An honest-empty frame still projects its declared column -> no Filter, no raise.
    assert app._declared_filters(page, lambda: pd.DataFrame({"facet": []})) == []

    # A frame missing the column altogether is a declaration bug.
    with pytest.raises(ValueError, match="does not project"):
        app._declared_filters(page, lambda: pd.DataFrame({"other": [1]}))

    # And with rows, the Filter really is built.
    built = app._declared_filters(page, lambda: pd.DataFrame({"facet": ["platform"]}))
    assert [f.id for f in built] == ["probe--filter-facet"]


_FIXTURE_DATA_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "data"


def test_distribution_breakdown_facet_filter_builds_against_fixture_rows(tmp_path: Path) -> None:
    """Story 27.5 / DW-atlas-27-3-1: the facet filter must not be ``_dynamic`` — Vizro
    hides dynamic filter selectors until a clientside reload, which e2e saw as an empty
    ``#distribution-breakdown--filter-facet`` container."""
    data_root = tmp_path / "data"
    shutil.copytree(
        _FIXTURE_DATA_ROOT,
        data_root,
        ignore=shutil.ignore_patterns("*.py", "*.md", "__pycache__"),
    )
    dashboard = app.build_dashboard(
        build_stamp="2026-07-18T12:00:00Z",
        data_root=data_root,
        now=1_700_000_000,
        reset=True,
    )
    Vizro().build(dashboard)
    filt = model_manager["distribution-breakdown--filter-facet"]
    assert filt._dynamic is False
    assert sorted(filt.selector.options) == ["platform", "python-version"]


def test_the_two_live_scan_pages_declare_no_vizro_filter() -> None:
    """Their input is a path field, not a selector over an existing frame."""
    for page_id in _PATH_INPUT_PAGES:
        page = INVENTORY[page_id]
        assert page.kind == "live-scan-artifact"
        assert page.filters == ()
        assert page.chart is None
