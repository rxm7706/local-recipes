"""The BSL-driven Vizro app factory (Story D2, FR-9, AD-8/AD-17/NFR-8).

``build_dashboard`` assembles a ``vm.Dashboard`` from the honest-core page set and registers
each page's data function in Vizro's ``data_manager``. Data functions are LAZY — Vizro calls
them at render time, not at build — so the dashboard OBJECT builds fully offline with no
server and no migrated data present (the ``dashboard-dryrun`` gate builds the object + asserts
structure, exactly like the C1 ``dagster-dryrun`` / C2 ``viz-loadable`` gates; it never
``.run()``s a server).

Every data function routes through ``dashboard.data`` (the AD-8 BSL seam) or
``dashboard.factory_status``; no metric is computed here.

Page set (honest core; the full 28-page inventory is CIS-two-spine-deferred, DW-D2):
  * GROUNDED data pages — feedstock-health, my-feedstocks (BSL query over a migrated dataset).
  * BSL-WIRED SHELL pages — staleness-report, query-atlas, detail-cf-atlas (wired to
    build_packages_model; render empty until the composed packages store lands, DW-D2).
  * NO-BSL-MODEL SHELL pages — behind-upstream, whodepends (no D1 BSL model exists yet; a
    Card states the gap — no data function, no fabrication).
  * factory-status — the fully-specified BMAD-artifact-state page (AD-17 build stamp).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import vizro.models as vm
from vizro import Vizro
from vizro.managers import data_manager
from vizro.tables import dash_ag_grid

from . import data as _data
from . import factory_status as _fs

# The D2 AC's live-confirmed-first consumer set (order preserved for determinism).
LIVE_CONSUMER_CLIS = (
    "behind-upstream",
    "query-atlas",
    "whodepends",
    "feedstock-health",
    "my-feedstocks",
    "detail-cf-atlas",
    "staleness-report",
)


@dataclass(frozen=True)
class PageDef:
    """Static description of a built page (introspected by the dashboard-dryrun gate)."""

    id: str
    title: str
    cli: str  # the legacy read CLI this page ports (or "factory-status")
    kind: str  # "grounded-data" | "bsl-shell" | "no-bsl-shell" | "factory"
    note: str = ""


PAGE_INVENTORY: tuple[PageDef, ...] = (
    PageDef("feedstock-health", "Feedstock Health", "feedstock-health", "grounded-data"),
    PageDef("my-feedstocks", "My Feedstocks", "my-feedstocks", "grounded-data"),
    PageDef(
        "staleness-report",
        "Staleness Report",
        "staleness-report",
        "bsl-shell",
        note="Wired to build_packages_model.staleness_age_days; renders empty until the "
        "composed packages store lands (latest_conda_upload is not yet migrated — DW-D2).",
    ),
    PageDef(
        "query-atlas",
        "Query Atlas",
        "query-atlas",
        "bsl-shell",
        note="Wired to build_packages_model (is_actionable + adoption stage + downloads); "
        "renders empty until the composed packages store lands (DW-D2).",
    ),
    PageDef(
        "detail-cf-atlas",
        "Package Detail",
        "detail-cf-atlas",
        "bsl-shell",
        note="Wired to build_packages_model (full per-package metric row); renders empty "
        "until the composed packages store lands (DW-D2).",
    ),
    PageDef(
        "behind-upstream",
        "Behind Upstream",
        "behind-upstream",
        "no-bsl-shell",
        note="No D1 BSL model yet: the conda-vs-upstream currency join needs "
        "vcs_upstream_versions ⋈ packages (D1 shipped packages / feedstock_health / "
        "maintainers only). Full page CIS-two-spine-deferred (DW-D2).",
    ),
    PageDef(
        "whodepends",
        "Who Depends",
        "whodepends",
        "no-bsl-shell",
        note="No D1 BSL model yet: the reverse-dependency graph over core_dependencies is "
        "not a declared BSL model. Full page CIS-two-spine-deferred (DW-D2).",
    ),
    PageDef("factory-status", "Factory Status", "factory-status", "factory"),
)

DASHBOARD_ID = "cf-atlas"
DASHBOARD_TITLE = "cf_atlas Factory"


def _legibility_card(page: PageDef, *, grounded: bool) -> vm.Card:
    """A semantic markdown Card carrying the page's provenance + any data-gap note
    (NFR-8 agent-legibility — a deterministic, agent-readable header)."""
    lines = [
        f"### {page.title}",
        "",
        f"Ports the `{page.cli}` read CLI. Data flows through the D1 BSL models (AD-8).",
    ]
    if grounded:
        lines.append("")
        lines.append("**Data:** live — BSL query over the migrated catalog dataset.")
    if page.note:
        lines.append("")
        lines.append(f"**Data gap:** {page.note}")
    return vm.Card(id=f"{page.id}--about", text="\n".join(lines))


def _data_page(page: PageDef, loader: Callable[[], Any], *, grounded: bool) -> vm.Page:
    """A page = a legibility Card + an AgGrid fed by a lazily-registered BSL data function."""
    key = f"data::{page.id}"
    data_manager[key] = loader
    return vm.Page(
        id=page.id,
        title=page.title,
        components=[
            _legibility_card(page, grounded=grounded),
            vm.AgGrid(id=f"{page.id}--grid", figure=dash_ag_grid(key)),
        ],
    )


def _shell_page(page: PageDef) -> vm.Page:
    """A no-BSL-model shell: a Card stating the gap, no data function (no fabrication)."""
    return vm.Page(
        id=page.id,
        title=page.title,
        components=[_legibility_card(page, grounded=False)],
    )


def _factory_page(
    page: PageDef,
    *,
    build_stamp: str,
    sprint_status_path: str | Path | None,
    epics_path: str | Path | None,
    specs_dir: str | Path | None,
) -> vm.Page:
    """factory-status — AD-17 build stamp (in a Card AND row 0 of the table) + the BMAD
    artifact-state table."""
    key = f"data::{page.id}"

    def _loader() -> Any:
        return _fs.build_factory_status_frame(
            build_stamp=build_stamp,
            sprint_status_path=sprint_status_path,
            epics_path=epics_path,
            specs_dir=specs_dir,
        )

    data_manager[key] = _loader
    stamp_card = vm.Card(
        id=f"{page.id}--stamp",
        text=(
            f"### Factory Status\n\n"
            f"**Build timestamp (AD-17):** `{build_stamp}`\n\n"
            "Live BMAD artifact state — sprint-status.yaml `development_status`, "
            "epics.md frontmatter, and each `docs/specs/*.md` status."
        ),
    )
    return vm.Page(
        id=page.id,
        title=page.title,
        components=[stamp_card, vm.AgGrid(id=f"{page.id}--grid", figure=dash_ag_grid(key))],
    )


def build_dashboard(
    *,
    build_stamp: str | None = None,
    data_root: str | Path | None = None,
    now: int | None = None,
    sprint_status_path: str | Path | None = None,
    epics_path: str | Path | None = None,
    specs_dir: str | Path | None = None,
    reset: bool = True,
) -> vm.Dashboard:
    """Assemble the BSL-driven Vizro Dashboard object (OFFLINE — no server, no live data).

    ``build_stamp`` (AD-17) and ``now`` are injectable for determinism; both default to wall
    clock resolved ONCE here (never at import). ``reset`` clears Vizro's global managers so
    repeated builds in one process (the gate) are independent.
    """
    if reset:
        Vizro._reset()
    if build_stamp is None:
        build_stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if now is None:
        now = int(time.time())
    root = Path(data_root) if data_root is not None else _data.default_data_root()

    by_id = {p.id: p for p in PAGE_INVENTORY}
    pages: list[vm.Page] = [
        _data_page(
            by_id["feedstock-health"],
            lambda: _data.load_feedstock_health(root / _data.FEEDSTOCK_HEALTH_PARQUET),
            grounded=True,
        ),
        _data_page(
            by_id["my-feedstocks"],
            lambda: _data.load_my_feedstocks(root / _data.PACKAGE_MAINTAINERS_PARQUET),
            grounded=True,
        ),
        _data_page(
            by_id["staleness-report"],
            lambda: _data.load_staleness(root / _data.PACKAGES_PARQUET, now=now),
            grounded=False,
        ),
        _data_page(
            by_id["query-atlas"],
            lambda: _data.load_query_atlas(root / _data.PACKAGES_PARQUET, now=now),
            grounded=False,
        ),
        _data_page(
            by_id["detail-cf-atlas"],
            lambda: _data.load_detail(root / _data.PACKAGES_PARQUET, now=now),
            grounded=False,
        ),
        _shell_page(by_id["behind-upstream"]),
        _shell_page(by_id["whodepends"]),
        _factory_page(
            by_id["factory-status"],
            build_stamp=build_stamp,
            sprint_status_path=sprint_status_path,
            epics_path=epics_path,
            specs_dir=specs_dir,
        ),
    ]
    return vm.Dashboard(id=DASHBOARD_ID, title=DASHBOARD_TITLE, pages=pages)
