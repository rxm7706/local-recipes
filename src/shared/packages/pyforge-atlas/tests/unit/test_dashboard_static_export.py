"""Unit coverage for ``pyforge.atlas.dashboard.static_export`` (Story 30.2, CAP-63).

The export's end-to-end gates (``tests/integration/dashboard/test_vizro_static_export.py``) run
over the full dashboard ``build_dashboard`` assembles, but they live under ``tests/integration``,
which the diff-scoped ``unit`` coverage gate (``scripts/coverage_gates_ci.py``) never measures.
These tests drive the module's own helpers, and ``export_boards`` over a two-board dashboard
built here from small frames (``build_dashboard`` monkeypatched to return it), so the module's
real rendering, refusals and directory swap count toward that gate. Every export writes under
``tmp_path``; nothing starts a server or a process.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
import vizro.models as vm
import vizro.plotly.express as px
from pyforge.core.errors import PyforgeError
from vizro import Vizro
from vizro.managers import data_manager
from vizro.tables import dash_ag_grid

from pyforge.atlas.dashboard import app as _app
from pyforge.atlas.dashboard import static_export

TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import vizro_static_export as cli  # noqa: E402

SHA = "0123456789abcdef0123456789abcdef01234567"
STAMP = "2026-10-01T08:00:00Z"
LATER_STAMP = "1999-01-01T00:00:00Z"  # a later Card's AD-17 line never overrides the first one's
EXPORTED_AT = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
EXPORTED_TEXT = "2026-10-15T12:00:00Z"
BOARD = "tiny-board"
SCAN = "tiny-scan"
SCAN_NOTE = "a new scan is submitted through the live dashboard's Run button"
INVENTORY = (
    _app.PageDef(BOARD, "Tiny <Board> & Co", "tiny", "grounded-data"),
    _app.PageDef(SCAN, "Tiny Scan", "tiny-scan", "live-scan-artifact", note=SCAN_NOTE),
)
ROWS = pd.DataFrame({"name": ["alpha", "beta"], "count": [3, 5]})


@pytest.fixture(autouse=True)
def _fresh_vizro_managers():
    """Each test builds its own models and data sources; none leaks into the next."""
    Vizro._reset()
    yield
    Vizro._reset()


def _tiny_dashboard(data_root: Path, *, chart: str = "bar", board_extra: tuple = ()) -> vm.Dashboard:
    """A two-board dashboard shaped like ``build_dashboard``'s: a grounded board (Card, grid,
    chart) and a live-scan board (Card, its submit controls, grid)."""
    Vizro._reset()
    data_manager[f"data::{BOARD}"] = lambda: ROWS
    data_manager[f"data::{SCAN}"] = lambda: pd.DataFrame({"finding": ["<none>"]})
    if chart == "geo":
        figure = px.scatter_geo(f"data::{BOARD}", lat="count", lon="count")
    else:
        figure = px.bar(f"data::{BOARD}", x="name", y="count")
    board = vm.Page(
        id=BOARD,
        title="Tiny <Board> & Co",
        components=[
            vm.Card(
                id=f"{BOARD}--about",
                text=(
                    "### About this board\n\n"
                    f"**Data build stamp (AD-17):** `{STAMP}`\n\n"
                    f"Backing file: `{data_root / 'tiny.parquet'}`\n\n"
                    "| Column | Meaning |\n|---|---|\n| name | the <b>package</b> |"
                ),
            ),
            vm.AgGrid(id=f"{BOARD}--grid", figure=dash_ag_grid(f"data::{BOARD}")),
            vm.Graph(id=f"{BOARD}--chart", figure=figure),
            vm.Card(id=f"{BOARD}--later", text=f"**Build timestamp (AD-17):** `{LATER_STAMP}`"),
            *board_extra,
        ],
    )
    scan = vm.Page(
        id=SCAN,
        title="Tiny Scan",
        components=[
            vm.Card(
                id=f"{SCAN}--about",
                text=f"**Data build stamp (AD-17):** unavailable (no scan cached yet)\n\n**Data gap:** {SCAN_NOTE}",
            ),
            vm.UserInput(id=f"{SCAN}--path", title="Project path"),
            vm.Button(id=f"{SCAN}--submit", text="Run scan"),
            vm.Text(id=f"{SCAN}--status", text="No scan submitted yet in this session."),
            vm.AgGrid(id=f"{SCAN}--grid", figure=dash_ag_grid(f"data::{SCAN}")),
        ],
    )
    return vm.Dashboard(pages=[board, scan])


@pytest.fixture()
def tiny(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Patch ``build_dashboard`` to build the two-board dashboard; returns each call's kwargs."""
    calls: list[dict] = []

    def build_dashboard(**kwargs):
        calls.append(kwargs)
        return _tiny_dashboard(kwargs["data_root"])

    monkeypatch.setattr(static_export._app, "build_dashboard", build_dashboard)
    return calls


def _export(out: Path, data_root: Path, **kwargs) -> dict:
    kwargs.setdefault("export_commit", SHA)
    kwargs.setdefault("exported_at", EXPORTED_AT)
    kwargs.setdefault("inventory", INVENTORY)
    return static_export.export_boards(out, data_root=data_root, **kwargs)


def _siblings(parent: Path, out: Path) -> list[str]:
    """Staging or set-aside directories ``_write_tree`` left beside ``out``."""
    return sorted(p.name for p in parent.iterdir() if p.name.startswith(f".{out.name}-"))


# --- the Card markdown subset ------------------------------------------------------------------------


def test_markdown_headings_paragraphs_and_inline_forms() -> None:
    html = static_export._markdown(
        "# Top\n\n#### Four\n\n####### seven hashes is text\n\n"
        "first line of a paragraph\n  second **bold** line with `code`\n\n\n"
        "# a heading line\nfollowed by text is a paragraph"
    )
    assert html.split("\n") == [
        "<h2>Top</h2>",  # the page's own <h1> is its title, so a Card heading starts at <h2>
        "<h3>Four</h3>",
        "<p>####### seven hashes is text</p>",
        "<p>first line of a paragraph second <strong>bold</strong> line with <code>code</code></p>",
        "<p># a heading line followed by text is a paragraph</p>",
    ]
    assert static_export._markdown("") == ""
    assert static_export._markdown("\n  \n") == ""


def test_markdown_pipe_tables_with_and_without_a_separator_row() -> None:
    separated = static_export._markdown("| Source | Rows |\n|:---|---:|\n| `a` | **1** |\n| b | 2 |")
    assert separated == (
        '<table><thead><tr><th scope="col">Source</th><th scope="col">Rows</th></tr></thead>'
        "<tbody><tr><td><code>a</code></td><td><strong>1</strong></td></tr><tr><td>b</td><td>2</td></tr></tbody></table>"
    )
    bare = static_export._markdown("| h |\n| --x-- |")
    assert bare == '<table><thead><tr><th scope="col">h</th></tr></thead><tbody><tr><td>--x--</td></tr></tbody></table>'


def test_markdown_escapes_hostile_text_and_never_emits_its_markup() -> None:
    html = static_export._markdown(
        "## <img src=x onerror=alert(1)>\n\n"
        "**<b>bold</b>** and `<i>code</i>` & \"quotes\" 'single'\n\n"
        "<script>alert('x')</script>\n\n"
        "| <x> | y |\n|---|---|\n| <script> | a & b |"
    )
    for raw in ("<img", "<script", "<b>", "<i>", "<x>"):
        assert raw not in html
    assert "<h2>&lt;img src=x onerror=alert(1)&gt;</h2>" in html
    assert "<strong>&lt;b&gt;bold&lt;/b&gt;</strong>" in html
    assert "<code>&lt;i&gt;code&lt;/i&gt;</code> &amp; &quot;quotes&quot; &#x27;single&#x27;" in html
    assert "<p>&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;</p>" in html
    assert '<th scope="col">&lt;x&gt;</th>' in html and "<td>&lt;script&gt;</td><td>a &amp; b</td>" in html


# --- grids as HTML tables ------------------------------------------------------------------------------


def test_a_grid_renders_every_row_and_column_escaped() -> None:
    hostile_column = 'col"><img src=x onerror=alert(1)>'
    data_manager["data::hostile"] = lambda: pd.DataFrame(
        {
            hostile_column: ['</td><script>alert("x")</script>', "a & b", None],
            "<th>": [pd.NA, ["x", "<y>"], 7],
        },
        dtype=object,
    )
    grid = vm.AgGrid(id="hostile--grid", figure=dash_ag_grid("data::hostile"))
    table = static_export._render_table(grid, {})
    assert "<script>" not in table and "<img" not in table and "<th>" not in table
    assert '<th scope="col">col&quot;&gt;&lt;img src=x onerror=alert(1)&gt;</th>' in table
    assert '<th scope="col">&lt;th&gt;</th>' in table
    assert "<td>&lt;/td&gt;&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;</td><td></td>" in table
    assert "<td>a &amp; b</td><td>[&#x27;x&#x27;, &#x27;&lt;y&gt;&#x27;]</td>" in table
    assert "<tr><td></td><td>7</td></tr>" in table  # a missing value is a blank cell, never "None"
    assert table.startswith('<table id="hostile--grid">\n<caption>3 rows</caption>')


@pytest.mark.parametrize(
    ("value", "shown"),
    [(None, ""), (pd.NA, ""), (float("nan"), ""), (pd.NaT, ""), (0, "0"), ("x", "x"), ([1, 2], "[1, 2]")],
)
def test_a_cell_shows_its_value_and_a_missing_value_blank(value, shown: str) -> None:
    assert static_export._cell(value) == shown


def test_captions_count_rows_and_name_an_honest_empty_frame() -> None:
    data_manager["data::one"] = pd.DataFrame({"a": [1]})
    data_manager["data::none"] = pd.DataFrame({"a": []})
    one = static_export._render_table(vm.AgGrid(id="one--grid", figure=dash_ag_grid("data::one")), {})
    none = static_export._render_table(vm.AgGrid(id="none--grid", figure=dash_ag_grid("data::none")), {})
    assert "<caption>1 row</caption>" in one
    assert "<caption>0 rows: the backing dataset holds no rows yet (honest-empty)</caption>" in none
    assert "<tbody>\n\n</tbody>" in none


# --- the row cap (Story 37.2, DW-atlas-37-3-1) ----------------------------------------------------------

BIG = pd.DataFrame({"name": ["a", "b", "c", "d"], "count": [3, 9, 5, 9]})


def test_a_frame_over_the_cap_keeps_its_largest_rows_by_the_chart_measure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(static_export, "STATIC_ROW_CAP", 3)
    data_manager["data::big"] = lambda: BIG
    frames: dict = {}
    table = static_export._render_table(
        vm.AgGrid(id="big--grid", figure=dash_ag_grid("data::big")), frames, sort_by="count"
    )
    assert "<caption>3 of 4 rows, the largest count first; the live dashboard holds every row</caption>" in table
    # ties break on the other columns, so the same data always keeps the same rows
    assert (
        table.index("<td>b</td>") < table.index("<td>d</td>") < table.index("<td>c</td>") and "<td>a</td>" not in table
    )


def test_a_chart_sums_its_measure_over_the_whole_frame_not_the_capped_table(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(static_export, "STATIC_ROW_CAP", 2)
    data_manager["data::stage"] = lambda: pd.DataFrame({"stage": ["a", "a", "a", "b", "b", "c"], "n": [1] * 6})
    chart = static_export._render_chart(
        vm.Graph(id="stage--chart", figure=px.bar("data::stage", x="stage", y="n")),
        {},
        chart=_app.ChartDef("bar", x="stage", y="n"),
    )
    bars, _note = static_export._chart_frame(data_manager["data::stage"].load(), _app.ChartDef("bar", x="stage", y="n"))
    assert bars.to_dict("records") == [{"stage": "a", "n": 3}, {"stage": "b", "n": 2}]  # the whole frame, summed
    assert "sums n per stage over all 6 rows and shows the 2 largest of 3 bars" in chart


def test_a_chart_under_the_cap_draws_every_bar_without_a_note(monkeypatch: pytest.MonkeyPatch) -> None:
    data_manager["data::stage"] = lambda: pd.DataFrame({"stage": ["a", "b", "a"], "n": [1, 1, 1]})
    frame, note = static_export._chart_frame(data_manager["data::stage"].load(), _app.ChartDef("bar", x="stage", y="n"))
    assert frame.to_dict("records") == [{"stage": "a", "n": 2}, {"stage": "b", "n": 1}] and note == ""
    whole = pd.DataFrame({"x": [1]})
    assert static_export._chart_frame(whole, None) == (whole, "")  # no declared chart: the frame as it is


def test_a_measure_equal_on_every_row_is_not_claimed_as_the_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(static_export, "STATIC_ROW_CAP", 2)
    frame = pd.DataFrame({"name": ["c", "a", "b"], "package_count": [1, 1, 1]})
    capped = static_export._capped(frame, "package_count")
    assert capped["name"].tolist() == ["a", "b"] and capped.attrs["static_sorted_by"] is None


def test_every_table_is_sorted_so_the_export_is_reproducible() -> None:
    one = static_export._capped(pd.DataFrame({"k": ["b", "a"], "v": [1, 2]}), None)
    two = static_export._capped(pd.DataFrame({"k": ["a", "b"], "v": [2, 1]}), None)
    assert one.equals(two) and one["k"].tolist() == ["a", "b"] and one.attrs == {}  # under the cap: no caption change


def test_without_a_chart_measure_the_cap_keeps_the_first_rows_in_column_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(static_export, "STATIC_ROW_CAP", 2)
    data_manager["data::big"] = lambda: BIG.iloc[::-1]
    table = static_export._render_table(vm.AgGrid(id="big--grid", figure=dash_ag_grid("data::big")), {})
    assert "<caption>2 of 4 rows, the first in column order; the live dashboard holds every row</caption>" in table
    assert "<td>a</td>" in table and "<td>b</td>" in table and "<td>c</td>" not in table


def test_a_measure_the_frame_lacks_sorts_as_if_none_were_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(static_export, "STATIC_ROW_CAP", 2)
    capped = static_export._capped(BIG, "downloads")
    assert capped["name"].tolist() == ["a", "b"] and capped.attrs == {"static_total_rows": 4, "static_sorted_by": None}


def test_a_column_that_does_not_compare_falls_back_to_the_measure_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(static_export, "STATIC_ROW_CAP", 2)
    frame = pd.DataFrame({"tags": [["x"], [1], ["y"]], "count": [1, 3, 2]})
    assert static_export._capped(frame, "count")["count"].tolist() == [3, 2]
    assert static_export._capped(frame, None)["count"].tolist() == [1, 3]  # nothing to sort on: as loaded


def test_a_frame_at_the_cap_keeps_every_row_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(static_export, "STATIC_ROW_CAP", 4)
    capped = static_export._capped(BIG, "count")
    assert len(capped) == 4 and capped.attrs == {} and capped["name"].tolist() == ["b", "d", "c", "a"]
    assert static_export._capped(OSError("x"), "count").args == ("x",)
    assert static_export.STATIC_ROW_CAP == 4 and "STATIC_ROW_CAP" in static_export.__all__


def test_the_shipped_cap_is_five_thousand_rows() -> None:
    assert static_export.STATIC_ROW_CAP == 5_000


def test_a_board_caps_its_frame_by_its_declared_chart_measure(
    tmp_path: Path, tiny: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(static_export, "STATIC_ROW_CAP", 1)
    inventory = (
        _app.PageDef(BOARD, "Tiny", "tiny", "grounded-data", chart=_app.ChartDef("bar", x="name", y="count")),
        INVENTORY[1],
    )
    out = tmp_path / "vizro"
    _export(out, tmp_path / "data", inventory=inventory)
    page = (out / BOARD / "index.html").read_text(encoding="utf-8")
    assert "<caption>1 of 2 rows, the largest count first; the live dashboard holds every row</caption>" in page
    assert "<tr><td>beta</td><td>5</td></tr>" in page and "<td>alpha</td>" not in page
    assert "every table shows its loader's frame, up to 1 rows" in page


def test_a_loader_that_raises_is_reported_on_its_page_and_read_once() -> None:
    reads: list[int] = []

    def broken() -> pd.DataFrame:
        reads.append(1)
        raise OSError("<missing> & gone")

    data_manager["data::broken"] = broken
    grid = vm.AgGrid(id="broken--grid", figure=dash_ag_grid("data::broken"))
    chart = vm.Graph(id="broken--chart", figure=px.bar("data::broken", x="a", y="b"))
    frames: dict = {}
    table = static_export._render_table(grid, frames)
    drawn = static_export._render_chart(chart, frames, board="broken")
    assert reads == [1]  # one read per data key, shared by every component on it
    for html, component_id in ((table, "broken--grid"), (drawn, "broken--chart")):
        assert html == (
            f'<p class="read-error" role="alert" id="{component_id}">Data could not be read at export time '
            "(OSError: &lt;missing&gt; &amp; gone).</p>"
        )


# --- charts: the vendored bundle, PLOTLY_CONFIG and the third-party-trace refusal ----------------------


def test_plotly_config_writes_off_the_logo_and_chart_studio_links() -> None:
    assert static_export.PLOTLY_CONFIG == {"displaylogo": False, "showLink": False, "showEditInChartStudio": False}
    data_manager["data::rows"] = ROWS
    chart = vm.Graph(id="rows--chart", figure=px.bar("data::rows", x="name", y="count"))
    html = static_export._render_chart(chart, {}, board="rows")
    assert '<script charset="utf-8" src="../assets/plotly.min.js"></script>' in html
    assert html.count("<script") == 3  # plotly's config line, the vendored bundle, newPlot: nothing inlined
    assert '<div id="rows--chart" class="plotly-graph-div"' in html
    assert '"displaylogo": false' in html and '"showLink": false' in html and '"showEditInChartStudio": false' in html
    assert "cdn.plot.ly" not in html and "https://" not in html and "http://" not in html
    assert "height:420px; width:100%;" in html
    assert static_export.PLOTLY_CONFIG == {"displaylogo": False, "showLink": False, "showEditInChartStudio": False}


def test_a_chart_that_cannot_be_drawn_is_reported_not_raised() -> None:
    data_manager["data::rows"] = ROWS
    chart = vm.Graph(id="rows--chart", figure=px.bar("data::rows", x="name", y="no<such>column"))
    html = static_export._render_chart(chart, {}, board="rows")
    assert html.startswith('<p class="read-error" role="alert" id="rows--chart">Chart could not be drawn at export ')
    assert "(ValueError: " in html and "no&lt;such&gt;column" in html and "<such>" not in html


def test_the_third_party_trace_types_are_the_geo_and_map_traces() -> None:
    assert {"scattergeo", "choropleth"} <= static_export.THIRD_PARTY_TRACE_TYPES
    assert {"scattermap", "choroplethmap", "densitymap"} <= static_export.THIRD_PARTY_TRACE_TYPES
    assert {"scattermapbox", "choroplethmapbox", "densitymapbox"} <= static_export.THIRD_PARTY_TRACE_TYPES
    assert not {"bar", "scatter", "histogram", "pie"} & static_export.THIRD_PARTY_TRACE_TYPES


def test_a_board_drawing_a_third_party_trace_refuses_the_whole_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        static_export._app, "build_dashboard", lambda **kwargs: _tiny_dashboard(kwargs["data_root"], chart="geo")
    )
    out = tmp_path / "vizro"
    with pytest.raises(static_export.StaticExportError) as refused:
        _export(out, tmp_path / "data")
    assert str(refused.value) == (
        f"board {BOARD!r}: chart '{BOARD}--chart' draws scattergeo, which loads from a third-party origin at "
        "runtime; nothing written"
    )
    assert not out.exists() and _siblings(tmp_path, out) == []


# --- the data-root scrub -----------------------------------------------------------------------------------


def test_the_scrub_replaces_an_absolute_root_only_as_a_whole_path(tmp_path: Path) -> None:
    root = tmp_path / "data"
    scrub = static_export._data_root_scrubber(root)
    token = "&lt;data-root&gt;"
    assert scrub(f"{root}/core.parquet") == f"{token}/core.parquet"
    assert scrub(f'"{root}" ({root}) {root}, {root}: under {root}.') == (
        f'"{token}" ({token}) {token}, {token}: under {token}.'
    )
    untouched = f"{root}.bak {root}-old {root}_2 {root}base {root}.d/x {tmp_path}/database"
    assert scrub(untouched) == untouched


def test_the_scrub_replaces_both_spellings_of_a_symlinked_root_and_their_escaped_forms(tmp_path: Path) -> None:
    tmp_path = tmp_path.resolve()
    real = tmp_path / "real&root"
    real.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)
    scrub = static_export._data_root_scrubber(link)
    escaped_real = str(real).replace("&", "&amp;")
    text = f"{link}/a.parquet | {real}/b.parquet | {escaped_real}/c.parquet"
    assert scrub(text) == "&lt;data-root&gt;/a.parquet | &lt;data-root&gt;/b.parquet | &lt;data-root&gt;/c.parquet"


def test_a_relative_root_never_rewrites_its_name_and_the_filesystem_root_is_inert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path = tmp_path.resolve()
    monkeypatch.chdir(tmp_path)
    scrub = static_export._data_root_scrubber(Path("data"))
    figure_json = '{"data": [{"type": "bar"}], "layout": {}} and data/core.parquet'
    assert scrub(figure_json) == figure_json  # a relative root prints relative, leaking nothing
    assert scrub(f"{tmp_path}/data/core.parquet") == "&lt;data-root&gt;/core.parquet"
    assert static_export._data_root_scrubber(Path("/"))("/ and /data and /") == "/ and /data and /"


# --- the access-column refusal (sld:AD-10) -------------------------------------------------------------------


def test_access_column_boards_names_every_declaring_board_in_order() -> None:
    inventory = (
        _app.PageDef("first", "First", "first", "grounded-data", access_column="org"),
        _app.PageDef("second", "Second", "second", "grounded-data"),
        _app.PageDef("third", "Third", "third", "grounded-data", access_column="team"),
    )
    assert static_export.access_column_boards(inventory) == [("first", "org"), ("third", "team")]
    assert static_export.access_column_boards(INVENTORY) == []
    assert static_export.access_column_boards() == []  # no shipped board declares one today
    static_export.refuse_access_columns(INVENTORY)  # nothing declared: no refusal


def test_an_access_column_refuses_before_anything_is_built_or_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def must_not_run(*args, **kwargs):
        raise AssertionError("the refusal comes first")

    monkeypatch.setattr(static_export._app, "build_dashboard", must_not_run)
    monkeypatch.setattr(static_export, "plotly_bundle", must_not_run)
    inventory = (INVENTORY[0], _app.PageDef(SCAN, "Tiny Scan", "tiny-scan", "live-scan-artifact", access_column="org"))
    out = tmp_path / "vizro"
    with pytest.raises(static_export.AccessColumnRefusedError) as refused:
        _export(out, tmp_path / "data", inventory=inventory)
    assert isinstance(refused.value, static_export.StaticExportError) and isinstance(refused.value, PyforgeError)
    assert refused.value.boards == ((SCAN, "org"),)
    assert str(refused.value) == (
        f"refused: board(s) {SCAN!r} (access column 'org') declare an access column; a static export has no "
        "viewer to restrict rows for (sld:AD-10); nothing written"
    )
    assert sorted(p.name for p in tmp_path.iterdir()) == []


# --- export_boards: the tree, the manifest, exported_at --------------------------------------------------------


def test_the_export_writes_the_tree_and_a_manifest_with_exactly_its_keys(tmp_path: Path, tiny: list[dict]) -> None:
    out = tmp_path / "site" / "vizro"
    returned = _export(out, tmp_path / "data")
    assert {p.name for p in out.iterdir()} == {"assets", "index.html", "manifest.json", BOARD, SCAN}
    assert [p.name for p in (out / "assets").iterdir()] == ["plotly.min.js"]
    assert (out / "assets" / "plotly.min.js").read_bytes() == static_export.plotly_bundle()
    assert (out.stat().st_mode & 0o777) == 0o755  # mkdtemp's 0700 does not ride the swap into the artifact
    assert _siblings(out.parent, out) == []

    text = (out / "manifest.json").read_text(encoding="utf-8")
    assert text.endswith("}\n") and text.startswith('{\n  "exported_at"')
    manifest = json.loads(text)
    assert manifest == returned
    assert list(manifest) == ["exported_at", "export_commit", "boards"]
    assert manifest["exported_at"] == EXPORTED_TEXT and manifest["export_commit"] == SHA
    assert manifest["boards"] == [
        {"id": BOARD, "title": "Tiny <Board> & Co", "path": f"{BOARD}/index.html", "data_build_timestamp": STAMP},
        {"id": SCAN, "title": "Tiny Scan", "path": f"{SCAN}/index.html", "data_build_timestamp": "unavailable"},
    ]
    for board in manifest["boards"]:
        assert list(board) == ["id", "title", "path", "data_build_timestamp"]
        assert (out / board["path"]).is_file()

    index = (out / "index.html").read_text(encoding="utf-8")
    assert '<nav aria-label="Boards"><a href="../../">Site home</a></nav>' in index
    assert f"2 boards, exported {EXPORTED_TEXT} from commit <code>{SHA}</code>" in index
    assert f'<tr><td><a href="{BOARD}/index.html">Tiny &lt;Board&gt; &amp; Co</a></td>' in index
    assert f"<td><code>{SCAN}/index.html</code></td><td>unavailable</td></tr>" in index


def test_a_board_page_renders_its_card_grid_and_chart(tmp_path: Path, tiny: list[dict]) -> None:
    out = tmp_path / "vizro"
    _export(out, tmp_path / "data")
    page = (out / BOARD / "index.html").read_text(encoding="utf-8")
    assert page.startswith("<!DOCTYPE html>") and "<title>Tiny &lt;Board&gt; &amp; Co - cf_atlas boards</title>" in page
    assert '<nav aria-label="Boards"><a href="../index.html">All boards</a></nav>' in page
    assert (
        f'<p class="export-note">Static export of board <code>{BOARD}</code>, built {EXPORTED_TEXT} from commit '
        f"<code>{SHA[:12]}</code>. Data build stamp (AD-17): {STAMP}. Filters are not part of a static page"
    ) in page
    assert f'<section class="card" id="{BOARD}--about">\n<h2>About this board</h2>' in page
    assert f"<strong>Data build stamp (AD-17):</strong> <code>{STAMP}</code>" in page
    assert "<td>name</td><td>the &lt;b&gt;package&lt;/b&gt;</td>" in page
    assert f'<table id="{BOARD}--grid">\n<caption>2 rows</caption>' in page
    assert "<tr><td>alpha</td><td>3</td></tr>" in page
    assert f'<div id="{BOARD}--chart" class="plotly-graph-div"' in page
    assert f'<section class="card" id="{BOARD}--later">' in page and LATER_STAMP in page  # rendered, not the stamp
    assert static_export.STATIC_SCAN_NOTICE not in page


def test_a_live_scan_board_drops_its_submit_path_and_says_so(tmp_path: Path, tiny: list[dict]) -> None:
    out = tmp_path / "vizro"
    _export(out, tmp_path / "data")
    page = (out / SCAN / "index.html").read_text(encoding="utf-8")
    assert "<input" not in page and "<button" not in page and "Run scan" not in page
    assert "No scan submitted yet" not in page and SCAN_NOTE not in page and "Data gap" not in page
    assert f'<p class="export-note" role="note">{static_export.STATIC_SCAN_NOTICE}</p>' in page
    assert "<strong>Data build stamp (AD-17):</strong> unavailable (no scan cached yet)" in page
    assert "<td>&lt;none&gt;</td>" in page


def test_no_page_publishes_the_exporting_hosts_data_root(tmp_path: Path, tiny: list[dict]) -> None:
    root = tmp_path / "data"
    out = tmp_path / "vizro"
    _export(out, root)
    page = (out / BOARD / "index.html").read_text(encoding="utf-8")
    assert "Backing file: <code>&lt;data-root&gt;/tiny.parquet</code>" in page
    for written in out.rglob("*.html"):
        assert str(root) not in written.read_text(encoding="utf-8"), written
    assert tiny[0]["data_root"] == root


def test_exported_at_is_the_commit_time_in_utc_and_is_the_staleness_clock(tmp_path: Path, tiny: list[dict]) -> None:
    """``exported_at`` is the export commit's committer time (the task resolves it): any offset is
    read in UTC, sub-second precision is dropped, and the BSL staleness models' ``now`` is that moment,
    so one commit's export never changes with the wall clock."""
    committed = datetime(2026, 10, 15, 11, 30, 0, 987654, tzinfo=timezone(timedelta(hours=2)))
    manifest = _export(tmp_path / "vizro", tmp_path / "data", exported_at=committed)
    assert manifest["exported_at"] == "2026-10-15T09:30:00Z"
    moment = int(datetime(2026, 10, 15, 9, 30, tzinfo=UTC).timestamp())
    assert tiny[0]["build_stamp"] == "2026-10-15T09:30:00Z" and tiny[0]["now"] == moment
    assert {"sprint_status_path", "epics_path"} <= set(tiny[0]) and tiny[0]["sprint_status_path"] is None

    _export(tmp_path / "again", tmp_path / "data", exported_at=committed, now=123)
    assert tiny[1]["now"] == 123  # an explicit clock is the caller's


def test_the_task_reads_exported_at_from_the_export_commits_committer_time(
    tmp_path: Path, tiny: list[dict], monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    def committer_time(commit: str) -> str:
        seen.append(commit)
        return "2026-10-15T09:30:00Z"

    monkeypatch.setattr(cli.viz_manifest, "_committer_date_iso_utc", committer_time)
    exported_at = cli._resolve_exported_at(SHA)
    assert seen == [SHA] and exported_at == datetime(2026, 10, 15, 9, 30, tzinfo=UTC)
    assert _export(tmp_path / "vizro", tmp_path / "data", exported_at=exported_at)["exported_at"] == (
        "2026-10-15T09:30:00Z"
    )

    def no_commit(commit: str) -> str:
        raise SystemExit(1)

    monkeypatch.setattr(cli.viz_manifest, "_committer_date_iso_utc", no_commit)
    assert cli._resolve_exported_at(SHA) is None


@pytest.mark.parametrize(("clock", "committer_reads"), [("commit", 1), ("now", 0)])
def test_the_clock_option_picks_the_commit_time_or_the_build_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: str, committer_reads: int
) -> None:
    """Story 37.2: the weekly build stamps its own time (``--clock now``), not the last merge's."""
    reads: list[str] = []
    calls: list[dict] = []
    monkeypatch.setattr(
        cli.viz_manifest, "_committer_date_iso_utc", lambda c: reads.append(c) or "2026-10-15T09:30:00Z"
    )
    monkeypatch.setattr(cli, "_resolve_export_commit", lambda _explicit: SHA)
    monkeypatch.setattr(static_export, "export_boards", lambda out, **kw: calls.append(kw) or {"boards": []})
    monkeypatch.setattr("pyforge.atlas.vizro_static_boards.boards_enabled", lambda **_kw: True)

    args = cli._build_parser().parse_args(["--out", str(tmp_path / "v"), "--clock", clock])
    cli._run(args)

    assert len(reads) == committer_reads
    assert (calls[0]["exported_at"] is None) is (clock == "now")  # None: the export reads the clock once


def test_without_exported_at_the_export_reads_the_clock_once(tmp_path: Path, tiny: list[dict]) -> None:
    before = datetime.now(UTC).replace(microsecond=0)
    manifest = _export(tmp_path / "vizro", tmp_path / "data", exported_at=None)
    moment = datetime.strptime(manifest["exported_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert before <= moment <= datetime.now(UTC)
    assert tiny[0]["build_stamp"] == manifest["exported_at"] and tiny[0]["now"] == int(moment.timestamp())


@pytest.mark.parametrize("commit", ["", None, "abc", "A" * 40, "g" * 40, SHA + "0", SHA[:-1]])
def test_export_commit_must_be_forty_lowercase_hex(tmp_path: Path, tiny: list[dict], commit) -> None:
    out = tmp_path / "vizro"
    with pytest.raises(static_export.StaticExportError, match="is not a 40-hex commit; nothing written"):
        _export(out, tmp_path / "data", export_commit=commit)
    assert tiny == [] and not out.exists()


# --- a board the export cannot render refuses the whole export --------------------------------------------------


def test_a_board_whose_id_is_not_a_path_safe_slug_refuses() -> None:
    page = vm.Page(id="../escape", title="Escape", components=[vm.Card(text="x")])
    with pytest.raises(static_export.StaticExportError, match="'../escape' is not a path-safe slug"):
        static_export._render_board(page, None, exported_text=EXPORTED_TEXT, export_commit=SHA)


def test_a_component_with_no_static_rendering_refuses_the_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A submit control is dropped only on a live-scan board; anywhere else it has no static form."""
    monkeypatch.setattr(
        static_export._app,
        "build_dashboard",
        lambda **kwargs: _tiny_dashboard(kwargs["data_root"], board_extra=(vm.Button(id="stray--button", text="Go"),)),
    )
    out = tmp_path / "vizro"
    with pytest.raises(static_export.StaticExportError) as refused:
        _export(out, tmp_path / "data")
    assert str(refused.value) == (
        f"board {BOARD!r}: component Button 'stray--button' has no static rendering; nothing written"
    )
    assert not out.exists() and _siblings(tmp_path, out) == []


def test_a_board_without_an_ad17_stamp_refuses() -> None:
    page = vm.Page(id="unstamped", title="Unstamped", components=[vm.Card(id="unstamped--about", text="no stamp")])
    with pytest.raises(static_export.StaticExportError, match="'unstamped' carries no AD-17 stamp line"):
        static_export._render_board(page, None, exported_text=EXPORTED_TEXT, export_commit=SHA)


@pytest.mark.parametrize(
    ("text", "stamp"),
    [
        ("**Data build stamp (AD-17):** `2026-09-01T00:00:00Z` (file mtime)", "2026-09-01T00:00:00Z"),
        ("**Build timestamp (AD-17):**  `2026-09-02T00:00:00Z`", "2026-09-02T00:00:00Z"),
        ("**Data build stamp (AD-17):** unavailable: no backing file", "unavailable"),
        ("**Data build stamp (AD-17):** unavailableish", None),
        ("Data build stamp (AD-17): `2026-09-01T00:00:00Z`", None),
        ("", None),
    ],
)
def test_the_stamp_is_read_from_the_cards_ad17_line(text: str, stamp: str | None) -> None:
    assert static_export._stamp_from_card(text) == stamp


# --- plotly's bundle -------------------------------------------------------------------------------------------


def test_plotly_bundle_is_the_envs_own_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import importlib.resources

    shipped = importlib.resources.files("plotly") / "package_data" / "plotly.min.js"
    assert static_export.plotly_bundle() == shipped.read_bytes()

    empty = tmp_path / "plotly-without-package-data"
    empty.mkdir()
    monkeypatch.setattr(static_export.importlib.resources, "files", lambda package: empty)
    with pytest.raises(static_export.StaticExportError, match="not found in this env's plotly; nothing written"):
        static_export.plotly_bundle()

    def not_installed(package: str):
        raise ModuleNotFoundError(package)

    monkeypatch.setattr(static_export.importlib.resources, "files", not_installed)
    with pytest.raises(static_export.StaticExportError, match="plotly is not installed in this env"):
        static_export.plotly_bundle()


# --- the atomic swap and its rollback ------------------------------------------------------------------------------


def _boards(*ids: str) -> list:
    return [
        static_export._RenderedBoard(
            id=board_id,
            title=board_id,
            path=f"{board_id}/index.html",
            data_build_timestamp=STAMP,
            html=f"<p>{board_id}</p>",
        )
        for board_id in ids
    ]


def _write(out: Path, *ids: str) -> None:
    static_export._write_tree(
        out, boards=_boards(*ids), index_html="<p>index</p>", manifest={"boards": list(ids)}, bundle=b"bundle"
    )


def _tree(out: Path) -> dict[str, bytes]:
    return {p.relative_to(out).as_posix(): p.read_bytes() for p in sorted(out.rglob("*")) if p.is_file()}


def test_the_swap_creates_the_parent_and_writes_the_whole_tree(tmp_path: Path) -> None:
    out = tmp_path / "docs" / "dashboard" / "vizro"
    _write(out, "one", "two")
    assert _tree(out) == {
        "assets/plotly.min.js": b"bundle",
        "index.html": b"<p>index</p>",
        "manifest.json": b'{\n  "boards": [\n    "one",\n    "two"\n  ]\n}\n',
        "one/index.html": b"<p>one</p>",
        "two/index.html": b"<p>two</p>",
    }
    assert (out.stat().st_mode & 0o777) == 0o755 and _siblings(out.parent, out) == []


def test_the_swap_replaces_the_previous_tree_wholesale(tmp_path: Path) -> None:
    out = tmp_path / "vizro"
    _write(out, "old")
    (out / "stray.txt").write_text("left by hand", encoding="utf-8")
    _write(out, "new")
    assert sorted(_tree(out)) == ["assets/plotly.min.js", "index.html", "manifest.json", "new/index.html"]
    assert _siblings(tmp_path, out) == []


def test_a_failure_while_staging_keeps_the_previous_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "vizro"
    _write(out, "old")
    before = _tree(out)
    real_write_text = Path.write_text

    def write_text(self: Path, *args, **kwargs):
        if self.name == "index.html" and self.parent.name.startswith(".vizro-"):
            raise OSError("disk full")
        return real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", write_text)
    with pytest.raises(OSError, match="disk full"):
        _write(out, "new")
    monkeypatch.undo()
    assert _tree(out) == before and _siblings(tmp_path, out) == []


@pytest.mark.parametrize("failing", ["aside", "swap-in"])
def test_a_failed_rename_puts_the_previous_tree_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failing: str
) -> None:
    out = tmp_path / "vizro"
    _write(out, "old")
    before = _tree(out)
    real_rename = Path.rename

    def rename(self: Path, target):
        target = Path(target)
        aside = self == out and target.name.startswith(".vizro-old-")
        swap_in = target == out and not self.name.startswith(".vizro-old-")
        if (failing == "aside" and aside) or (failing == "swap-in" and swap_in):
            raise OSError(f"rename refused ({failing})")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(OSError, match=rf"rename refused \({failing}\)"):
        _write(out, "new")
    monkeypatch.undo()
    assert _tree(out) == before and _siblings(tmp_path, out) == []


def test_a_failed_first_swap_leaves_no_tree_and_no_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "vizro"

    def rename(self: Path, target):
        raise OSError("rename refused")

    monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(OSError, match="rename refused"):
        _write(out, "new")
    monkeypatch.undo()
    assert sorted(p.name for p in tmp_path.iterdir()) == []
