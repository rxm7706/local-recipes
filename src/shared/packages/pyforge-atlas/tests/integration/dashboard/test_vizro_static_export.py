"""Story 30.2 (CAP-63): the Vizro boards export as static pages under ``docs/dashboard/vizro/``.

Every export here runs against the dryrun gate's fixture root (``/nonexistent-data-root``: every
BSL-wired page honest-empty) or ``test_dashboard_provenance``'s stamped root, and writes under
``tmp_path`` -- never into the checkout's ``docs/dashboard/vizro/``. Page counts and ids come from
the ``Dashboard`` object, never a literal.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.resources
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd
import pytest
from pyforge.testing_kit.flags import flagd_tree

from pyforge.atlas.dashboard import app, static_export

from . import test_dashboard_provenance as _provenance
from .test_dashboard_provenance import NO_FILE_PAGES, PAGE_PARQUET_CONSTANT, TWO_FILE_PAGES, _iso

# The provenance gate's stamped data root, reused as a fixture here (AC3).
stamped_root = _provenance.stamped_root

MEMBER_DIR = Path(__file__).resolve().parents[3]
TOOLS = MEMBER_DIR / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import vizro_static_export as cli  # noqa: E402

FIXTURE_ROOT = "/nonexistent-data-root"  # the dashboard-dryrun gate's root
NOW = 1_700_000_000
SHA = "a" * 40
EXPORTED_AT = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
EXPORTED_TEXT = "2026-10-15T12:00:00Z"
FLAG = "pyforge.atlas.vizro_static_boards"
LIVE_SCAN_PAGES = ("scan-project", "env-inspect")
SHELL_PAGES = ("behind-upstream", "whodepends")
# The page template's stamp line; the Card's own line is checked separately (`_card_shows`).
_STAMP_IN_PAGE = re.compile(r"Data build stamp \(AD-17\): (\S+?)\. Filters")


COMMIT_TIME = "2026-10-15T09:30:00Z"


def _fake_committer_time(monkeypatch: pytest.MonkeyPatch, sha: str) -> None:
    """A fake ``GITHUB_SHA`` has no commit to read a committer time from; answer for it."""

    def committer_time(commit: str) -> str:
        assert commit == sha
        return COMMIT_TIME

    monkeypatch.setattr(cli.viz_manifest, "_committer_date_iso_utc", committer_time)


def _page_ids() -> list[str]:
    dashboard = app.build_dashboard(build_stamp=EXPORTED_TEXT, data_root=FIXTURE_ROOT, now=NOW)
    return [page.id for page in dashboard.pages]


def _export(out: Path, bmad_fixture: dict, **kwargs) -> dict:
    return static_export.export_boards(
        out,
        export_commit=kwargs.pop("export_commit", SHA),
        exported_at=EXPORTED_AT,
        data_root=kwargs.pop("data_root", FIXTURE_ROOT),
        now=NOW,
        sprint_status_path=bmad_fixture["sprint"],
        epics_path=bmad_fixture["epics"],
        **kwargs,
    )


@pytest.fixture()
def exported(tmp_path: Path, bmad_fixture: dict) -> tuple[Path, dict]:
    out = tmp_path / "vizro"
    return out, _export(out, bmad_fixture)


class _Refs(HTMLParser):
    """Every resource a page loads (``<script src>``, ``<link href>``) and every ``<a href>``."""

    def __init__(self) -> None:
        super().__init__()
        self.loads: list[str] = []
        self.anchors: list[str] = []
        self.scripts = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "script":
            self.scripts += 1
            if values.get("src"):
                self.loads.append(values["src"] or "")
        elif tag == "link" and values.get("href"):
            self.loads.append(values["href"] or "")
        elif tag == "a" and values.get("href"):
            self.anchors.append(values["href"] or "")


def _refs(path: Path) -> _Refs:
    parser = _Refs()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _html_files(out: Path) -> list[Path]:
    return sorted(out.rglob("*.html"))


def _plotly_bytes() -> bytes:
    return (importlib.resources.files("plotly") / "package_data" / "plotly.min.js").read_bytes()


def _card_shows(page_text: str, stamp: str) -> bool:
    """The page's own legibility Card shows ``stamp`` on its AD-17 line (as ``app`` writes it)."""
    if stamp == static_export.UNAVAILABLE:
        return "<strong>Data build stamp (AD-17):</strong> unavailable" in page_text
    return any(
        f"<strong>{label} (AD-17):</strong> <code>{stamp}</code>" in page_text
        for label in ("Data build stamp", "Build timestamp")
    )


def assert_export_shape(out: Path, page_ids: list[str]) -> dict:
    """AC1-AC4 on one written export; returns the parsed manifest."""
    # AC1 -- the tree.
    assert (out / "index.html").is_file()
    bundles = sorted(out.rglob("plotly.min.js"))
    assert bundles == [out / "assets" / "plotly.min.js"]
    assert bundles[0].read_bytes() == _plotly_bytes()
    assert sorted(p.parent.name for p in out.glob("*/index.html")) == sorted(page_ids)
    assert {p.name for p in out.iterdir()} == {*page_ids, "assets", "index.html", "manifest.json"}
    assert sorted(p.name for p in (out / "assets").iterdir()) == [
        "plotly.min.js"
    ]  # the bundle's exemption is this file

    # AC2 -- no third-party origin in any page; every load resolves inside the export.
    for page in _html_files(out):
        text = page.read_text(encoding="utf-8")
        assert "cdn.plot.ly" not in text, page
        assert "https://" not in text and "http://" not in text, page
        for src in _refs(page).loads:
            target = (page.parent / src).resolve()
            assert target.is_relative_to(out.resolve()) and target.is_file(), f"{page}: {src}"

    # AC3 -- the manifest.
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"exported_at", "export_commit", "boards"}
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", manifest["exported_at"])
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["export_commit"])
    assert [board["id"] for board in manifest["boards"]] == page_ids
    for board in manifest["boards"]:
        assert set(board) == {"id", "title", "path", "data_build_timestamp"}
        page = out / board["path"]
        assert board["path"] == f"{board['id']}/index.html" and page.is_file()
        text = page.read_text(encoding="utf-8")
        shown = _STAMP_IN_PAGE.search(text)
        assert shown is not None and shown.group(1) == board["data_build_timestamp"], board["id"]
        assert _card_shows(text, board["data_build_timestamp"]), board["id"]

    # AC4 -- what is not exported.
    for page_id in LIVE_SCAN_PAGES:
        text = (out / page_id / "index.html").read_text(encoding="utf-8")
        assert "<input" not in text and "<button" not in text and "scan_submit" not in text
        assert static_export.STATIC_SCAN_NOTICE in text
    for page in _html_files(out):
        text = page.read_text(encoding="utf-8")
        assert "<select" not in text, page
        refs = _refs(page)
        # A page carries scripts only for its plotly chart: the config line, the bundle, newPlot.
        assert refs.scripts in (0, 3), f"{page}: {refs.scripts} script tags"
        assert refs.loads in ([], ["../assets/plotly.min.js"]), page
    return manifest


# --- AC1-AC4 --------------------------------------------------------------------------------------


def test_ac1_to_ac4_the_export_on_the_dryrun_fixture_root(exported: tuple[Path, dict]) -> None:
    out, returned = exported
    manifest = assert_export_shape(out, _page_ids())
    assert manifest == returned
    assert manifest["exported_at"] == EXPORTED_TEXT
    assert manifest["export_commit"] == SHA


def test_ac1_charted_pages_load_the_one_vendored_bundle(exported: tuple[Path, dict]) -> None:
    out, _ = exported
    charted = [page.id for page in app.PAGE_INVENTORY if page.chart is not None]
    assert charted
    for page_id in charted:
        assert _refs(out / page_id / "index.html").loads == ["../assets/plotly.min.js"], page_id


def test_ac2_the_vendored_bundle_is_the_envs_own_bytes(exported: tuple[Path, dict]) -> None:
    """The bundle is plotly's file byte for byte (AC1). It carries plotly's own default
    topojson URL (``cdn.plot.ly/un/``, fetched only by geo traces, which no board draws), so the
    third-party-origin rule is judged on the pages, which reference no origin at all."""
    out, _ = exported
    assert (out / "assets" / "plotly.min.js").read_bytes() == _plotly_bytes()


def test_ac3_honest_empty_boards_read_unavailable_and_factory_reads_the_export_stamp(
    exported: tuple[Path, dict],
) -> None:
    _, manifest = exported
    stamps = {board["id"]: board["data_build_timestamp"] for board in manifest["boards"]}
    assert stamps.pop("factory-status") == EXPORTED_TEXT
    assert set(stamps.values()) == {static_export.UNAVAILABLE}


def test_ac3_each_board_stamps_its_own_dataset(tmp_path: Path, bmad_fixture: dict, stamped_root) -> None:
    """The provenance gate's stamped root, re-read through the export: every board's
    ``data_build_timestamp`` is its own Parquet file's mtime (``test_dashboard_provenance``'s pin)."""
    _dashboard, mtimes = stamped_root
    out = tmp_path / "vizro"
    manifest = _export(out, bmad_fixture, data_root=tmp_path / "data")
    stamps = {board["id"]: board["data_build_timestamp"] for board in manifest["boards"]}
    for page_id, constant in PAGE_PARQUET_CONSTANT.items():
        assert stamps[page_id] == _iso(mtimes[constant]), page_id
    for page_id, pair in TWO_FILE_PAGES.items():
        assert stamps[page_id] in {_iso(mtimes[constant]) for constant in pair}
    for page_id in NO_FILE_PAGES:
        assert stamps[page_id] == static_export.UNAVAILABLE
    assert stamps["factory-status"] == EXPORTED_TEXT
    assert_export_shape(out, [board["id"] for board in manifest["boards"]])


def test_shell_pages_export_their_card_and_no_figure(exported: tuple[Path, dict]) -> None:
    out, _ = exported
    for page_id in SHELL_PAGES:
        text = (out / page_id / "index.html").read_text(encoding="utf-8")
        assert "No D1 BSL model yet" in text
        assert "<script" not in text and "<table" not in text


def test_honest_empty_tables_say_so(exported: tuple[Path, dict]) -> None:
    out, _ = exported
    text = (out / "feedstock-health" / "index.html").read_text(encoding="utf-8")
    assert "0 rows: the backing dataset holds no rows yet (honest-empty)" in text


def test_card_pipe_tables_render_as_tables(exported: tuple[Path, dict]) -> None:
    out, _ = exported
    text = (out / "identity-workbook" / "index.html").read_text(encoding="utf-8")
    assert '<table><thead><tr><th scope="col">Source</th>' in text
    assert "| Source |" not in text


def test_no_page_publishes_the_exporting_hosts_data_root(tmp_path: Path, bmad_fixture: dict) -> None:
    root = tmp_path / "an-empty-data-root"
    out = tmp_path / "vizro"
    _export(out, bmad_fixture, data_root=root)
    for page in _html_files(out):
        text = page.read_text(encoding="utf-8")
        assert str(root) not in text, page
    assert "backing file not found: &lt;data-root&gt;/" in (out / "feedstock-health" / "index.html").read_text()


def test_a_previous_export_is_replaced_wholesale(tmp_path: Path, bmad_fixture: dict) -> None:
    out = tmp_path / "vizro"
    (out / "stale-board").mkdir(parents=True)
    (out / "stale-board" / "index.html").write_text("stale", encoding="utf-8")
    _export(out, bmad_fixture)
    assert not (out / "stale-board").exists()
    assert (out / "manifest.json").is_file()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".vizro-")] == []


def test_a_failure_while_writing_leaves_nothing(tmp_path: Path, bmad_fixture: dict, monkeypatch) -> None:
    """The manifest is the last file written: a failure there leaves no tree and no staging dir."""
    out = tmp_path / "vizro"

    class _FailingJson:
        @staticmethod
        def dumps(*args, **kwargs):
            raise OSError("disk full")

    monkeypatch.setattr(static_export, "json", _FailingJson)
    with pytest.raises(OSError, match="disk full"):
        _export(out, bmad_fixture)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["epics.md", "sprint-status.yaml"]


# --- AC5: the refusal -------------------------------------------------------------------------------


def _inventory_with_access_column(page_id: str = "feedstock-health") -> tuple[app.PageDef, ...]:
    return tuple(
        dataclasses.replace(page, access_column="org") if page.id == page_id else page for page in app.PAGE_INVENTORY
    )


def test_no_board_declares_an_access_column_today() -> None:
    assert static_export.access_column_boards() == []
    assert all(page.access_column is None for page in app.PAGE_INVENTORY)


def test_ac5_an_access_column_refuses_and_writes_nothing(tmp_path: Path, bmad_fixture: dict) -> None:
    out = tmp_path / "vizro"
    with pytest.raises(static_export.AccessColumnRefusedError) as refused:
        _export(out, bmad_fixture, inventory=_inventory_with_access_column())
    assert "'feedstock-health'" in str(refused.value) and "'org'" in str(refused.value)
    assert refused.value.boards == (("feedstock-health", "org"),)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["epics.md", "sprint-status.yaml"]


def test_ac5_the_task_exits_1_naming_the_board(tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "on"})
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setattr(app, "PAGE_INVENTORY", _inventory_with_access_column("whodepends"))
    code = cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT])
    assert code == 1
    assert "'whodepends'" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize(
    "module",
    [
        MEMBER_DIR / "src/pyforge/atlas/dashboard/static_export.py",
        MEMBER_DIR / "src/pyforge/atlas/vizro_static_boards.py",
        TOOLS / "vizro_static_export.py",
    ],
    ids=lambda path: path.name,
)
def test_ac5_the_exporter_imports_no_steward(module: Path) -> None:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not [name for name in imported if name.startswith("pyforge.steward")]
    if module.is_relative_to(MEMBER_DIR / "src"):
        assert "subprocess" not in imported


# --- AC6 and the matrix's other refusals, through the task's CLI --------------------------------------


def test_ac6_flag_off_refuses_with_the_usage_code_and_writes_nothing(tmp_path: Path, capsys) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "off"})
    code = cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT])
    assert code == cli.EXIT_USAGE == 2
    assert f"flag {FLAG} is off" in capsys.readouterr().err
    assert not out.exists()


def test_the_task_writes_the_export_and_names_github_sha(tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "on"})
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    _fake_committer_time(monkeypatch, "b" * 40)
    assert cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT]) == 0
    manifest = assert_export_shape(out, _page_ids())
    assert manifest["export_commit"] == "b" * 40
    assert manifest["exported_at"] == COMMIT_TIME
    assert "wrote" in capsys.readouterr().out


def test_without_github_sha_the_task_names_head(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "on"})
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.chdir(MEMBER_DIR)  # any directory inside the checkout answers `git rev-parse HEAD`
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    committed = subprocess.run(
        ["git", "show", "-s", "--format=%cI", head], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT]) == 0
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["export_commit"] == head
    # exported_at is the export commit's committer time, so one commit's export is reproducible.
    assert datetime.fromisoformat(manifest["exported_at"]) == datetime.fromisoformat(committed)


def test_an_unresolvable_export_commit_refuses_and_writes_nothing(tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "on"})
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    def _no_git(*args, **kwargs):
        return subprocess.CompletedProcess(args, 128, stdout="", stderr="fatal: not a git repository")

    monkeypatch.setattr(cli.viz_manifest.subprocess, "run", _no_git)
    code = cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT])
    assert code == 1
    assert "export_commit" in capsys.readouterr().err
    assert not out.exists()


def test_a_missing_plotly_bundle_refuses_and_writes_nothing(tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "on"})
    monkeypatch.setenv("GITHUB_SHA", SHA)
    empty = tmp_path / "plotly-without-package-data"
    empty.mkdir()
    monkeypatch.setattr(static_export.importlib.resources, "files", lambda package: empty)
    code = cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT])
    assert code == 1
    assert "plotly/package_data/plotly.min.js" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize(("variant", "expected"), [("on", "enabled=true"), ("off", "enabled=false")])
def test_print_flag_reports_the_resolved_value(tmp_path: Path, capsys, variant: str, expected: str) -> None:
    tree = flagd_tree(tmp_path, {FLAG: variant})
    assert cli.main(["--print-flag", "--flags-path", str(tree)]) == 0
    assert capsys.readouterr().out.strip() == expected


def test_export_commit_must_be_forty_hex(tmp_path: Path, bmad_fixture: dict) -> None:
    out = tmp_path / "vizro"
    with pytest.raises(static_export.StaticExportError, match="export_commit"):
        _export(out, bmad_fixture, export_commit="abc")
    assert not out.exists()


def test_an_unreadable_committer_time_refuses_and_writes_nothing(tmp_path: Path, monkeypatch, capsys) -> None:
    out = tmp_path / "vizro"
    tree = flagd_tree(tmp_path, {FLAG: "on"})
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)

    def no_commit(commit: str) -> str:
        raise SystemExit(1)

    monkeypatch.setattr(cli.viz_manifest, "_committer_date_iso_utc", no_commit)
    assert cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT]) == 1
    assert "exported_at" in capsys.readouterr().err
    assert not out.exists()


def test_one_commits_export_is_byte_identical_on_every_run(tmp_path: Path, monkeypatch) -> None:
    """The Pages build hashes the tree: the same commit and data must export the same bytes."""
    tree = flagd_tree(tmp_path, {FLAG: "on"})
    monkeypatch.setenv("GITHUB_SHA", "e" * 40)
    _fake_committer_time(monkeypatch, "e" * 40)
    first, second = tmp_path / "first", tmp_path / "second"
    for out in (first, second):
        assert cli.main(["--out", str(out), "--flags-path", str(tree), "--data-root", FIXTURE_ROOT]) == 0
    files = sorted(p.relative_to(first) for p in first.rglob("*") if p.is_file())
    assert files == sorted(p.relative_to(second) for p in second.rglob("*") if p.is_file())
    assert [f for f in files if (first / f).read_bytes() != (second / f).read_bytes()] == []


# --- the review's guards (third-party traces, Chart Studio links, the data-root scrub, escaping) ---


def test_every_exported_chart_draws_no_third_party_trace_and_links_no_chart_studio(
    exported: tuple[Path, dict],
) -> None:
    """The vendored bundle's map and geo URLs are reachable only through these trace types and the
    Chart Studio links; the export refuses the first and writes the second off."""
    out, _ = exported
    dashboard = app.build_dashboard(build_stamp=EXPORTED_TEXT, data_root=FIXTURE_ROOT, now=NOW)
    charts = [c for page in dashboard.pages for c in page.components if isinstance(c, static_export.vm.Graph)]
    assert charts
    for chart in charts:
        frame = static_export.data_manager[chart.figure["data_frame"]].load()
        types = {trace.type for trace in chart.figure(data_frame=frame).data}
        assert types and not types & static_export.THIRD_PARTY_TRACE_TYPES, chart.id
    assert static_export.PLOTLY_CONFIG["showLink"] is False
    assert static_export.PLOTLY_CONFIG["showEditInChartStudio"] is False
    for page in _html_files(out):
        text = page.read_text(encoding="utf-8")
        if "Plotly.newPlot" in text:
            assert '"showLink": false' in text and '"showEditInChartStudio": false' in text, page
            assert '"showLink": true' not in text and "plotlyServerURL" not in text, page


# plotly 7 no longer builds the *mapbox traces (a board drawing one shows its "could not be drawn" line
# and fetches nothing); the guard keeps them for an older plotly.
@pytest.mark.parametrize("trace_type", ["choropleth", "choroplethmap", "densitymap", "scattergeo", "scattermap"])
def test_a_chart_drawing_a_third_party_trace_refuses_the_export(trace_type: str) -> None:
    import plotly.graph_objects as go

    frames = {"data::probe": pd.DataFrame({"a": [1]})}
    figure = _Figure(lambda data_frame: go.Figure(data=[{"type": trace_type}]), "data::probe")
    with pytest.raises(static_export.StaticExportError, match=trace_type):
        static_export._render_chart(_Component("probe--chart", figure), frames, board="probe")


class _Figure:
    """A captured-callable stand-in: subscriptable for ``data_frame`` and callable with a frame."""

    def __init__(self, build, key: str) -> None:
        self._build = build
        self._key = key

    def __getitem__(self, name: str) -> str:
        assert name == "data_frame"
        return self._key

    def __call__(self, *, data_frame):
        return self._build(data_frame)


class _Component:
    def __init__(self, component_id: str, figure: object) -> None:
        self.id = component_id
        self.figure = figure


def test_the_scrub_replaces_only_the_absolute_root_as_a_whole_path() -> None:
    scrub = static_export._data_root_scrubber(Path("/data"))
    text = '/database and /data/x and "/data" and /data'
    assert scrub(text) == '/database and &lt;data-root&gt;/x and "&lt;data-root&gt;" and &lt;data-root&gt;'


def test_a_relative_data_root_leaves_the_figures_json_intact(
    tmp_path: Path, bmad_fixture: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--data-root data`` (the member-relative convention) once rewrote every ``"data"`` key."""
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "vizro"
    _export(out, bmad_fixture, data_root="data")
    charted = [page.id for page in app.PAGE_INVENTORY if page.chart is not None]
    for page_id in charted:
        text = (out / page_id / "index.html").read_text(encoding="utf-8")
        assert '"data":' in text or '"data": ' in text, page_id
        assert "&lt;data-root&gt;" not in text, page_id
    assert "backing file not found: data/" in (out / "feedstock-health" / "index.html").read_text()


def test_hostile_cells_columns_ids_and_card_text_are_escaped() -> None:
    hostile = '</td><script>alert("x")</script>'
    frames = {"data::hostile": pd.DataFrame({'col"><img src=x onerror=alert(1)>': [hostile, "a & b"]})}
    table = static_export._render_table(_Component('grid"><script>', _Figure(None, "data::hostile")), frames)
    assert "<script>" not in table and "<img" not in table
    assert "&lt;/td&gt;&lt;script&gt;" in table and "a &amp; b" in table
    assert 'id="grid&quot;&gt;&lt;script&gt;"' in table
    card = static_export._markdown(
        "### <img src=x onerror=alert(1)>\n\n**<b>bold</b>** `<i>code</i>`\n\n| <x> | y |\n|---|---|\n| <script> | z |"
    )
    assert "<img" not in card and "<script>" not in card and "<b>" not in card and "<i>" not in card
    assert "&lt;img src=x onerror=alert(1)&gt;" in card and "<strong>&lt;b&gt;bold&lt;/b&gt;</strong>" in card
