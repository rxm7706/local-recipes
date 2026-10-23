"""Vizro boards as static pages under ``docs/dashboard/vizro/`` (Story 30.2, CAP-63).

Exports the same ``Dashboard`` object the live server runs: ``build_dashboard`` builds it
offline (no ``.run()``), exactly as the ``dashboard-dryrun`` gate does, and each page is
rendered from its own components -- its Cards' text, its grids' frames and its declared
chart -- with every frame read through the loader ``build_dashboard`` registered for it
(``dashboard.data``, the AD-8 BSL seam). Nothing is re-derived for the export.

* **One vendored plotly.js.** Every chart is ``Figure.to_html(full_html=False,
  include_plotlyjs="../assets/plotly.min.js")``: one copy of plotly's own
  ``package_data/plotly.min.js``, read from the env, never fetched, never ``'cdn'``, never
  inlined (``True``) and never one copy per directory (``'directory'``) -- herald AD-21: no
  third-party origin in the Pages artifact.
* **What is not exported.** The path field and Run button of the two live-scan pages (they
  submit work through the live dashboard) and every filter: a static page has no server and
  no viewer, so it renders the frame its loader returns, unfiltered, and the live-scan pages
  carry one line saying they show the latest cached result.
* **Tables: sorted, at most** :data:`STATIC_ROW_CAP` **rows** (Story 37.2, DW-atlas-37-3-1). Over a
  full data root two loaders return 448,301 and 210,170 rows, which wrote 37.2 MB and 23.1 MB pages.
  Every table is sorted -- by the page's chart measure, largest first, when it varies, then by every
  column -- so one commit's export is byte-identical whatever order a loader returns. A larger
  frame keeps its first rows in that order, and the caption says how many it holds of how many.
* **Charts: the whole frame.** A chart sums its measure per bar over every row, never the capped
  table, and keeps at most :data:`STATIC_ROW_CAP` bars, the largest, saying so beside the chart.
* **The refusal.** A board that declares an access column (``PageDef.access_column``)
  refuses the whole export before anything is written -- ``sld:AD-10``: static export and
  role isolation are mutually exclusive, refused rather than warned. The rule is applied
  here, not imported from steward.
* **Nothing partial.** Every page is rendered in memory first, then written to a sibling
  temporary directory that replaces the output directory only once complete.

The flag (``pyforge.atlas.vizro_static_boards``) and ``export_commit`` are resolved by the
``vizro-static-export`` task's CLI (``tools/vizro_static_export.py``); this module never
starts a process.
"""

from __future__ import annotations

import html
import importlib.resources
import json
import re
import shutil
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import vizro.models as vm
from pyforge.core.errors import PyforgeError
from vizro.managers import data_manager

from . import app as _app
from . import data as _data

__all__ = (
    "ASSET_DIR",
    "MANIFEST_NAME",
    "PLOTLY_ASSET",
    "PLOTLY_CONFIG",
    "STATIC_ROW_CAP",
    "STATIC_SCAN_NOTICE",
    "THIRD_PARTY_TRACE_TYPES",
    "UNAVAILABLE",
    "AccessColumnRefusedError",
    "StaticExportError",
    "access_column_boards",
    "export_boards",
    "plotly_bundle",
    "refuse_access_columns",
)

ASSET_DIR = "assets"
PLOTLY_ASSET = "plotly.min.js"
MANIFEST_NAME = "manifest.json"
INDEX_NAME = "index.html"
#: A static page renders at most this many rows of a frame (Story 37.2, DW-atlas-37-3-1).
STATIC_ROW_CAP = 5_000
UNAVAILABLE = "unavailable"
#: What a page shows in place of the data root's absolute path (no build host's path is published).
DATA_ROOT_TOKEN = "<data-root>"
#: What a page's own directory reaches the one vendored plotly.js by.
PLOTLY_SRC_FROM_PAGE = f"../{ASSET_DIR}/{PLOTLY_ASSET}"
#: The one line each live-scan page carries in place of its path field and Run button.
STATIC_SCAN_NOTICE = (
    "Latest cached result only: a static page cannot start a scan. Run a new one from the live dashboard or the CLI."
)
_LIVE_SCAN_KIND = "live-scan-artifact"
#: plotly.js trace types that fetch from a third-party origin at runtime: geo traces load topojson from
#: ``cdn.plot.ly``; map/mapbox traces load tiles, fonts, sprites and icons from map providers. The
#: vendored bundle carries those URLs, so a board drawing one of these is refused (herald AD-21: no
#: runtime cross-origin call), and the bundle's exemption in ``pages-check`` rests on this refusal.
THIRD_PARTY_TRACE_TYPES = frozenset(
    {
        "scattergeo",
        "choropleth",
        "scattermap",
        "choroplethmap",
        "densitymap",
        "scattermapbox",
        "choroplethmapbox",
        "densitymapbox",
    }
)
#: The figure config every chart is written with: no plotly logo link, and no Chart Studio links
#: (``showLink`` / ``showEditInChartStudio`` would point at ``cloud.plotly.com``).
PLOTLY_CONFIG = {"displaylogo": False, "showLink": False, "showEditInChartStudio": False}
_SUBMISSION_COMPONENTS = (vm.UserInput, vm.Button, vm.Text)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PAGE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# The AD-17 line every legibility Card carries (`app._provenance_line`), and the factory
# page's build-stamp Card (`app._factory_page`).
_STAMP_RE = re.compile(r"\*\*(?:Data build stamp|Build timestamp) \(AD-17\):\*\*\s+`([^`]+)`")
_UNAVAILABLE_RE = re.compile(r"\*\*Data build stamp \(AD-17\):\*\*\s+unavailable\b")
_CSS = (
    "body{font-family:system-ui,sans-serif;margin:0 auto;max-width:72rem;padding:1rem;line-height:1.5}"
    "nav{margin-bottom:1rem}table{border-collapse:collapse;margin:.5rem 0 1.5rem;font-size:.9rem}"
    "th,td{border:1px solid #ccc;padding:.25rem .5rem;text-align:left;vertical-align:top}"
    "caption{text-align:left;font-style:italic;padding:.25rem 0}.card{margin:1rem 0}"
    ".export-note{color:#555}.read-error{color:#a00}"
)
_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - cf_atlas boards</title>
<style>{css}</style>
</head>
<body>
<nav aria-label="Boards"><a href="{nav_href}">{nav_text}</a></nav>
<main>
<h1>{title}</h1>
{body}
</main>
</body>
</html>
"""


class StaticExportError(PyforgeError):
    """The export could not run; nothing was written. The message names the cause."""


class AccessColumnRefusedError(StaticExportError):
    """A board declares an access column (``sld:AD-10``): the whole export is refused."""

    def __init__(self, boards: Sequence[tuple[str, str]]) -> None:
        self.boards = tuple(boards)
        named = ", ".join(f"{board!r} (access column {column!r})" for board, column in self.boards)
        super().__init__(
            f"refused: board(s) {named} declare an access column; a static export has no viewer "
            "to restrict rows for (sld:AD-10); nothing written"
        )


@dataclass(frozen=True)
class _RenderedBoard:
    id: str
    title: str
    path: str
    data_build_timestamp: str
    html: str


def access_column_boards(inventory: Iterable[_app.PageDef] | None = None) -> list[tuple[str, str]]:
    """``(page id, column)`` for every page that declares an access column."""
    pages = _app.PAGE_INVENTORY if inventory is None else tuple(inventory)
    return [(page.id, page.access_column) for page in pages if page.access_column]


def refuse_access_columns(inventory: Iterable[_app.PageDef] | None = None) -> None:
    """Raise :class:`AccessColumnRefusedError` when any page declares an access column."""
    declared = access_column_boards(inventory)
    if declared:
        raise AccessColumnRefusedError(declared)


def plotly_bundle() -> bytes:
    """The bytes of plotly's own ``package_data/plotly.min.js`` in this env (never fetched).

    ``plotly`` reaches atlas through vizro, a declared dependency, so it is looked up here as a
    resource and never imported at module level.
    """
    where = f"plotly/package_data/{PLOTLY_ASSET}"
    try:
        resource = importlib.resources.files("plotly") / "package_data" / PLOTLY_ASSET
    except ModuleNotFoundError as exc:
        raise StaticExportError(f"{where} not found: plotly is not installed in this env; nothing written") from exc
    if not resource.is_file():
        raise StaticExportError(f"{where} not found in this env's plotly; nothing written")
    return resource.read_bytes()


def export_boards(
    out_dir: str | Path,
    *,
    export_commit: str,
    exported_at: datetime | None = None,
    data_root: str | Path | None = None,
    now: int | None = None,
    sprint_status_path: str | Path | None = None,
    epics_path: str | Path | None = None,
    inventory: Iterable[_app.PageDef] | None = None,
    flags_path: str | Path | None = None,
) -> dict[str, Any]:
    """Write the static boards to ``out_dir`` and return the manifest written beside them.

    ``flags_path`` is the flag tree ``pyforge.atlas.board_projections`` is read from (Story 37.4),
    the same tree the export task read ``pyforge.atlas.vizro_static_boards`` from.

    Order: the access-column refusal, plotly's bundle and ``export_commit`` are checked, then
    every page is rendered in memory, and only then is anything written. ``out_dir`` is
    replaced wholesale. Raises :class:`StaticExportError` (nothing written) on any refusal.
    """
    # Story 37.4: one read of `pyforge.atlas.board_projections` decides both the declared pages and the build
    projected = _data.board_projections(flags_path=flags_path)
    pages_declared = _app.page_inventory(projected=projected) if inventory is None else tuple(inventory)
    refuse_access_columns(pages_declared)
    bundle = plotly_bundle()
    if not _SHA_RE.fullmatch(export_commit or ""):
        raise StaticExportError(f"export_commit {export_commit!r} is not a 40-hex commit; nothing written")
    moment = (exported_at or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    exported_text = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    # The staleness models' clock is the export's own moment (the export commit's committer time when
    # the task runs), never the wall clock: one commit's export is byte-identical on every run, with
    # materialized data as with honest-empty data (30.2's re-review).
    now = int(moment.timestamp()) if now is None else now

    root = Path(data_root) if data_root is not None else _data.default_data_root()
    dashboard = _app.build_dashboard(
        build_stamp=exported_text,
        data_root=root,
        now=now,
        sprint_status_path=sprint_status_path,
        epics_path=epics_path,
        board_projections=projected,
    )
    declared_by_id = {page.id: page for page in pages_declared}
    scrub = _data_root_scrubber(root)
    boards = [
        _render_board(
            page,
            declared_by_id.get(page.id),
            exported_text=exported_text,
            export_commit=export_commit,
            scrub=scrub,
        )
        for page in dashboard.pages
    ]
    manifest: dict[str, Any] = {
        "exported_at": exported_text,
        "export_commit": export_commit,
        "boards": [
            {
                "id": board.id,
                "title": board.title,
                "path": board.path,
                "data_build_timestamp": board.data_build_timestamp,
            }
            for board in boards
        ],
    }
    index_html = _render_index(boards, exported_text=exported_text, export_commit=export_commit)
    _write_tree(Path(out_dir), boards=boards, index_html=index_html, manifest=manifest, bundle=bundle)
    return manifest


# --- rendering ----------------------------------------------------------------------------------


def _data_root_scrubber(root: Path) -> Callable[[str], str]:
    """Replace the data root's absolute path in a page's HTML with :data:`DATA_ROOT_TOKEN`.

    An honest-empty page names the file it did not find (``provenance.resolve_for_file``); on a
    static page an absolute root would publish the exporting host's checkout path. Only an absolute
    spelling is replaced, and only as a whole path -- not followed by a path character (a word
    character or ``-``, or a ``.`` that continues the name) -- so a relative root (``data``) never
    rewrites the word ``data`` in a figure's JSON, ``/data`` never rewrites ``/database`` or
    ``/data.bak``, and a root followed by ``)``, ``,``, ``:`` or a sentence's ``.`` is still replaced.
    A relative root prints relative, leaking nothing."""
    resolved = str(root.resolve())
    raw = {resolved, *([str(root)] if root.is_absolute() else [])} - {"", "/"}
    if not raw:
        return lambda text: text
    spellings = sorted(raw | {_esc(spelling) for spelling in raw}, key=len, reverse=True)
    pattern = re.compile("(?:" + "|".join(re.escape(spelling) for spelling in spellings) + r")(?![\w-]|\.[\w-])")
    token = _esc(DATA_ROOT_TOKEN)

    def scrub(text: str) -> str:
        return pattern.sub(token, text)

    return scrub


def _render_board(
    page: vm.Page,
    declared: _app.PageDef | None,
    *,
    exported_text: str,
    export_commit: str,
    scrub: Callable[[str], str] = lambda text: text,
) -> _RenderedBoard:
    if not _PAGE_ID_RE.fullmatch(page.id):
        raise StaticExportError(f"board id {page.id!r} is not a path-safe slug; nothing written")
    live_scan = declared is not None and declared.kind == _LIVE_SCAN_KIND
    chart = declared.chart if declared is not None else None
    sort_by = chart.y if chart is not None else None
    frames: dict[str, Any] = {}
    parts: list[str] = []
    stamp: str | None = None
    for component in page.components:
        if isinstance(component, vm.Card):
            text = component.text
            if stamp is None:
                stamp = _stamp_from_card(text)
            if live_scan and declared is not None and declared.note:
                # The note describes the live page's submit path; the static page has none.
                for label in (_app.NOTE_LABEL, _app.GAP_LABEL):
                    text = text.replace(f"**{label}:** {declared.note}", "")
            parts.append(f'<section class="card" id="{_esc(component.id)}">\n{_markdown(text)}\n</section>')
        elif isinstance(component, (vm.AgGrid, vm.Table)):
            parts.append(_render_table(component, frames, sort_by=sort_by))
        elif isinstance(component, vm.Graph):
            parts.append(_render_chart(component, frames, board=page.id, chart=chart))
        elif live_scan and isinstance(component, _SUBMISSION_COMPONENTS):
            continue  # the path field, Run button and its status line submit work: not exported
        else:
            raise StaticExportError(
                f"board {page.id!r}: component {type(component).__name__} {component.id!r} has no "
                "static rendering; nothing written"
            )
    if stamp is None:
        raise StaticExportError(f"board {page.id!r} carries no AD-17 stamp line; nothing written")
    header = [
        f'<p class="export-note">Static export of board <code>{_esc(page.id)}</code>, built {_esc(exported_text)} '
        f"from commit <code>{_esc(export_commit[:12])}</code>. Data build stamp (AD-17): {_esc(stamp)}. "
        f"Filters are not part of a static page; every table shows its loader's frame, up to {STATIC_ROW_CAP:,} "
        "rows, and every chart sums its measure over all of them.</p>",
    ]
    if live_scan:
        header.append(f'<p class="export-note" role="note">{_esc(STATIC_SCAN_NOTICE)}</p>')
    body = "\n".join([*header, *parts])
    page_html = _PAGE_TEMPLATE.format(
        title=_esc(page.title),
        css=_CSS,
        nav_href=f"../{INDEX_NAME}",
        nav_text="All boards",
        body=body,
    )
    return _RenderedBoard(
        id=page.id,
        title=page.title,
        path=f"{page.id}/{INDEX_NAME}",
        data_build_timestamp=stamp,
        html=scrub(page_html),
    )


def _stamp_from_card(text: str) -> str | None:
    match = _STAMP_RE.search(text)
    if match is not None:
        return match.group(1)
    if _UNAVAILABLE_RE.search(text):
        return UNAVAILABLE
    return None


def _frame_for(component: Any, frames: dict[str, Any]) -> Any:
    """The component's whole frame through the loader ``build_dashboard`` registered (read once per key)."""
    key = component.figure["data_frame"]
    if key not in frames:
        try:
            frames[key] = data_manager[key].load()
        except Exception as exc:  # noqa: BLE001 -- the page reports its own read failure, as live
            frames[key] = exc
    return frames[key]


def _ordered(frame: pd.DataFrame, sort_by: str | None) -> tuple[pd.DataFrame, str | None]:
    """``frame`` sorted by ``sort_by`` (largest first) when it has that column and it varies, then by
    every other column; a column whose values do not compare leaves the measure alone, else the frame
    as loaded. Returns the sorted frame and the measure it led with, if any."""
    try:
        measure = sort_by if sort_by in frame.columns and frame[sort_by].nunique(dropna=True) > 1 else None
    except TypeError, ValueError:  # a list-valued measure, or a column name the frame holds twice
        measure = None
    keys = [measure, *(c for c in frame.columns if c != measure)] if measure else list(frame.columns)
    for attempt in (keys, [measure] if measure else []):
        if not attempt:
            break
        try:
            ordered = frame.sort_values(
                attempt, ascending=[key != measure for key in attempt], kind="stable", na_position="last"
            )
            return ordered.reset_index(drop=True), measure
        except TypeError, ValueError:  # a column whose values do not compare
            continue
    return frame.reset_index(drop=True), measure


def _capped(frame: Any, sort_by: str | None) -> Any:
    """A table's rows: the whole frame sorted (:func:`_ordered`), at most :data:`STATIC_ROW_CAP` of them.
    A frame over the cap keeps the whole count and the measure it was sorted by in ``attrs``, for the
    table's caption."""
    if not isinstance(frame, pd.DataFrame):
        return frame
    ordered, measure = _ordered(frame, sort_by)
    if len(ordered) <= STATIC_ROW_CAP:
        return ordered
    out = ordered.head(STATIC_ROW_CAP)
    out.attrs = {"static_total_rows": len(ordered), "static_sorted_by": measure}
    return out


def _chart_frame(frame: pd.DataFrame, chart: _app.ChartDef | None) -> tuple[pd.DataFrame, str]:
    """A chart's data: its measure summed per bar over the whole frame, the largest
    :data:`STATIC_ROW_CAP` bars kept; and the note the page shows when bars were left out."""
    if (
        chart is None
        or chart.kind != "bar"  # a bar adds up its rows; another kind is drawn from the frame as it is
        or not {chart.x, chart.y} <= set(frame.columns)
        or not pd.api.types.is_numeric_dtype(frame[chart.y])
    ):
        return frame, ""
    try:
        bars = frame.groupby(chart.x, dropna=False, sort=True)[chart.y].sum().reset_index()
    except TypeError, ValueError:  # a measure that does not add up: the frame as it is
        return frame, ""
    if len(bars) <= STATIC_ROW_CAP:
        return bars, ""
    total = len(bars)
    bars = bars.sort_values([chart.y, chart.x], ascending=[False, True], kind="stable").head(STATIC_ROW_CAP)
    note = (
        f"The chart sums {chart.y} per {chart.x} over all {len(frame):,} rows and shows the "
        f"{STATIC_ROW_CAP:,} largest of {total:,} bars."
    )
    return bars.reset_index(drop=True), note


def _read_error(component: Any, exc: BaseException) -> str:
    return (
        f'<p class="read-error" role="alert" id="{_esc(component.id)}">Data could not be read at export time '
        f"({_esc(type(exc).__name__)}: {_esc(str(exc))}).</p>"
    )


def _render_table(component: Any, frames: dict[str, Any], *, sort_by: str | None = None) -> str:
    frame = _frame_for(component, frames)
    if isinstance(frame, BaseException):
        return _read_error(component, frame)
    frame = _capped(frame, sort_by)
    columns = [str(column) for column in frame.columns]
    rows = len(frame)
    caption = f"{rows} row{'' if rows == 1 else 's'}"
    if rows == 0:
        caption += ": the backing dataset holds no rows yet (honest-empty)"
    total = frame.attrs.get("static_total_rows")
    if total is not None:
        sorted_by = frame.attrs.get("static_sorted_by")
        order = f"the largest {sorted_by} first" if sorted_by else "the first in column order"
        caption = f"{rows:,} of {total:,} rows, {order}; the live dashboard holds every row"
    head = "".join(f'<th scope="col">{_esc(column)}</th>' for column in columns)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{_esc(_cell(value))}</td>" for value in row) + "</tr>"
        for row in frame.itertuples(index=False, name=None)
    )
    return (
        f'<table id="{_esc(component.id)}">\n<caption>{_esc(caption)}</caption>\n'
        f"<thead><tr>{head}</tr></thead>\n<tbody>\n{body}\n</tbody>\n</table>"
    )


def _cell(value: Any) -> str:
    try:
        if pd.isna(value):
            return ""
    except TypeError, ValueError:  # list-likes: pd.isna answers per element
        pass
    return str(value)


def _render_chart(
    component: Any, frames: dict[str, Any], *, board: str = "", chart: _app.ChartDef | None = None
) -> str:
    frame = _frame_for(component, frames)
    if isinstance(frame, BaseException):
        return _read_error(component, frame)
    if isinstance(frame, pd.DataFrame):
        frame, note = _chart_frame(frame, chart)
    else:
        note = ""
    try:
        figure = component.figure(data_frame=frame)
    except Exception as exc:  # noqa: BLE001 -- an undrawable chart is reported on its page
        return (
            f'<p class="read-error" role="alert" id="{_esc(component.id)}">Chart could not be drawn at export '
            f"time ({_esc(type(exc).__name__)}: {_esc(str(exc))}).</p>"
        )
    third_party = sorted({str(trace.type) for trace in figure.data} & THIRD_PARTY_TRACE_TYPES)
    if third_party:
        raise StaticExportError(
            f"board {board or component.id!r}: chart {component.id!r} draws {', '.join(third_party)}, which loads "
            "from a third-party origin at runtime; nothing written"
        )
    drawn = str(
        figure.to_html(
            full_html=False,
            include_plotlyjs=PLOTLY_SRC_FROM_PAGE,
            div_id=component.id,
            default_height="420px",
            default_width="100%",
            config=dict(PLOTLY_CONFIG),
        )
    )
    return f'<p class="export-note">{_esc(note)}</p>\n{drawn}' if note else drawn


def _render_index(boards: Sequence[_RenderedBoard], *, exported_text: str, export_commit: str) -> str:
    rows = "\n".join(
        f'<tr><td><a href="{_esc(board.path)}">{_esc(board.title)}</a></td>'
        f"<td><code>{_esc(board.path)}</code></td><td>{_esc(board.data_build_timestamp)}</td></tr>"
        for board in boards
    )
    body = (
        f'<p class="export-note">{len(boards)} boards, exported {_esc(exported_text)} from commit '
        f"<code>{_esc(export_commit)}</code>. Each board is a static page of the cf_atlas Vizro dashboard; "
        "its data build stamp (AD-17) is its own dataset's, and <code>unavailable</code> where that dataset "
        "has not materialized.</p>\n"
        f'<table id="boards">\n<caption>{len(boards)} boards</caption>\n'
        '<thead><tr><th scope="col">Board</th><th scope="col">Path</th>'
        '<th scope="col">Data build stamp (AD-17)</th></tr></thead>\n'
        f"<tbody>\n{rows}\n</tbody>\n</table>"
    )
    return _PAGE_TEMPLATE.format(
        title="cf_atlas boards",
        css=_CSS,
        nav_href="../../",
        nav_text="Site home",
        body=body,
    )


def _write_tree(
    out_dir: Path,
    *,
    boards: Sequence[_RenderedBoard],
    index_html: str,
    manifest: dict[str, Any],
    bundle: bytes,
) -> None:
    """Write everything to a sibling temporary directory, then swap it in for ``out_dir``.

    The previous tree is renamed aside before the new one is renamed into place, and put back if that
    rename fails, so a failed swap never loses the previous export. Both sibling names start with
    ``.<out_dir name>-`` (gitignored beside ``docs/dashboard/vizro/``)."""
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}-", dir=out_dir.parent))
    try:
        (staging / ASSET_DIR).mkdir()
        (staging / ASSET_DIR / PLOTLY_ASSET).write_bytes(bundle)
        for board in boards:
            (staging / board.id).mkdir()
            (staging / board.path).write_text(board.html, encoding="utf-8")
        (staging / INDEX_NAME).write_text(index_html, encoding="utf-8")
        (staging / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        staging.chmod(0o755)  # mkdtemp's 0700 would ride the swap into the artifact
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    previous: Path | None = None
    try:
        if out_dir.exists():
            previous = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}-old-", dir=out_dir.parent))
            previous.rmdir()
            out_dir.rename(previous)
        staging.rename(out_dir)
    except BaseException:
        # Either rename failed: the previous tree goes back where it was (if it was moved aside), and
        # the finished staging directory never outlives the call (30.2's re-review).
        if previous is not None and previous.exists() and not out_dir.exists():
            previous.rename(out_dir)
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if previous is not None:
        shutil.rmtree(previous, ignore_errors=True)


# --- the Card markdown subset -------------------------------------------------------------------


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _inline(text: str) -> str:
    """Escape, then the two inline forms the Cards use: `code` and **bold**."""
    out = _esc(text)
    out = _CODE_RE.sub(lambda match: f"<code>{match.group(1)}</code>", out)
    return _BOLD_RE.sub(lambda match: f"<strong>{match.group(1)}</strong>", out)


def _markdown(text: str) -> str:
    """The Card text as HTML: headings, paragraphs and pipe tables -- the subset ``app`` writes.

    Anything else stays as escaped paragraph text (never dropped, never interpreted as HTML).
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip():
            current.append(line.rstrip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    out: list[str] = []
    for block in blocks:
        heading = re.match(r"^(#{1,6})\s+(.*)$", block[0])
        if len(block) == 1 and heading:
            level = min(6, max(2, len(heading.group(1)) - 1))  # the page's own <h1> is the title
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif all(line.lstrip().startswith("|") for line in block):
            out.append(_pipe_table(block))
        else:
            out.append(f"<p>{_inline(' '.join(line.strip() for line in block))}</p>")
    return "\n".join(out)


def _pipe_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _pipe_table(block: list[str]) -> str:
    header = _pipe_cells(block[0])
    body_lines = block[1:]
    if body_lines and all(re.fullmatch(r":?-{3,}:?", cell) for cell in _pipe_cells(body_lines[0])):
        body_lines = body_lines[1:]
    head = "".join(f'<th scope="col">{_inline(cell)}</th>' for cell in header)
    rows = "".join(
        "<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in _pipe_cells(line)) + "</tr>" for line in body_lines
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
