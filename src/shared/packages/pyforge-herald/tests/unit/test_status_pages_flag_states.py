"""Story 42.1 (spec-pyforge-herald CAP-60): the fleet board and guild status pages render at build.

The render (``docsite/build.py``'s ``render_status_pages``) takes the flag state as an argument, so
the two-state test drives both values; the reading of the inputs is ``docsite/tools/status_pages.py``
(the fleet board) and ``docsite/tools/ci_surfaces_tile.py`` (the guild status page, CAP-59's one
reading of ``ci-status.json``). Fixtures: the 2026-10-14 ledgers reshaped as steward's
``sprint-ledger-query --format json`` names them, and a snapshot with one row per verdict.
"""

from __future__ import annotations

import ast
import filecmp
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.herald.status_pages import STATUS_PAGES_FLAG, status_pages_enabled

_FLAG = "pyforge.herald.status_pages"

flag_provider = make_flag_provider_fixture()

REPO_ROOT = Path(__file__).resolve().parents[6]
_TOOLS = REPO_ROOT / "docsite" / "tools"
_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_FLEET = _FIXTURES / "fleet-status-2026-10-14.json"
_CI = _FIXTURES / "ci-status-every-verdict.json"
_SITE_YML = REPO_ROOT / "docsite" / "content" / "site.yml"

#: AC1: the 2026-10-14 counts, station by station, and the bar widths they give.
_STATIONS = ["atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden"]
_WIDTHS = [99, 100, 100, 99, 98, 100, 95, 100]
#: AC4: CAP-59's verdict order, an unknown verdict after it, then live (by id within a verdict).
_GUILD_ORDER = [
    "surface.drift",
    "surface.stuck",
    "surface.overdue",
    "surface.paused",
    "surface.paused-manually",
    "surface.opt-in-off",
    "surface.retired",
    "surface.quarantined",
    "surface.a-live",
    "surface.live",
]


def _tools():
    if str(_TOOLS) not in sys.path:
        sys.path.insert(0, str(_TOOLS))
    import ci_surfaces_tile
    import status_pages

    return status_pages, ci_surfaces_tile


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def build_mod():
    _tools()
    return _load(REPO_ROOT / "docsite" / "build.py", "docsite_build_status_under_test")


def _site_cfg() -> dict:
    return yaml.safe_load(_SITE_YML.read_text(encoding="utf-8"))


def _render(build_mod, tmp_path: Path, *, flag_enabled: bool, fleet: Path = _FLEET, ci: Path = _CI):
    status_out = tmp_path / "site" / "status"
    written = build_mod.render_status_pages(
        flag_enabled=flag_enabled,
        status_out=status_out,
        herald_out=tmp_path / "site" / "herald",
        fleet_status=fleet,
        ci_status=ci,
        site_cfg=_site_cfg(),
        built_at="2026-10-15",
        commit="abc1234",
    )
    return status_out, written


def _write(tmp_path: Path, payload: object, name: str = "fleet-status.json") -> Path:
    path = tmp_path / name
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return path


def _fleet() -> dict:
    return json.loads(_FLEET.read_text(encoding="utf-8"))


def _section(html: str, cls: str) -> str:
    match = re.search(rf'<section class="{cls}">(.*?)</section>', html, re.S)
    assert match, cls
    return match.group(1)


# --- the flag -------------------------------------------------------------------------------------


def test_the_key_is_the_one_the_tree_declares() -> None:
    assert STATUS_PAGES_FLAG == _FLAG
    tree = json.loads((REPO_ROOT / "src/platform/config/flags.json").read_text(encoding="utf-8"))["flags"][_FLAG]
    assert tree["defaultVariant"] == "off"
    assert tree["metadata"]["owner"] == "herald"
    assert tree["metadata"]["story"] == "42-1-the-fleet-board-and-guild-status-pages-render-at-build"
    overlays = json.loads((REPO_ROOT / "src/platform/config/flag-overlays.json").read_text(encoding="utf-8"))
    assert {env: overlays[env][_FLAG] for env in ("dev", "staging", "production")} == {
        "dev": "on",
        "staging": "off",
        "production": "off",
    }


def test_on_and_off_trees_read_through_flags_path(tmp_path: Path) -> None:
    on = flagd_tree(tmp_path, {_FLAG: "on"}, name="on.json")
    off = flagd_tree(tmp_path, {_FLAG: "off"}, name="off.json")
    assert status_pages_enabled(flags_path=on) is True
    assert status_pages_enabled(flags_path=off) is False


def test_the_site_build_reads_the_exported_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    sp, _ = _tools()
    for value, expected in (("1", True), ("true", True), ("0", False), ("", False)):
        monkeypatch.setenv(sp.ENV_STATUS_PAGES, value)
        assert sp.enabled_from_env() is expected
    monkeypatch.delenv(sp.ENV_STATUS_PAGES)
    assert sp.enabled_from_env() is False


# --- AC9: two states ------------------------------------------------------------------------------


@flag_states("pyforge.herald.status_pages")
def test_ac9_render_follows_flag_state(
    flag_provider: dict[str, bool], build_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    enabled = flag_provider[_FLAG]
    sp, _ = _tools()
    if not enabled:  # AC7: off, the input is never opened
        monkeypatch.setattr(sp, "load_fleet_status", lambda path: pytest.fail(f"opened {path} with the flag off"))
    status_out, written = _render(build_mod, tmp_path, flag_enabled=enabled)
    if enabled:
        assert written == [status_out / "index.html", status_out / "ci" / "index.html"]
        board = (status_out / "index.html").read_text(encoding="utf-8")
        assert re.findall(r'data-width="(\d+)"', board) == [str(w) for w in _WIDTHS]
        guild = (status_out / "ci" / "index.html").read_text(encoding="utf-8")
        assert re.findall(r'data-surface="([^"]+)"', guild) == _GUILD_ORDER
    else:
        assert written is None
        assert not status_out.exists()


# --- AC1-AC3: the fleet board ---------------------------------------------------------------------


def test_ac1_one_row_per_station(build_mod, tmp_path: Path) -> None:
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True)
    board = (status_out / "index.html").read_text(encoding="utf-8")
    rows = re.findall(r'<tr data-station="([^"]+)">(.*?)</tr>', board, re.S)
    assert [name for name, _ in rows] == [f"pyforge-{s}" for s in _STATIONS]
    for (name, body), station, width in zip(rows, _fleet()["stations"], _WIDTHS, strict=True):
        cells = re.findall(r'<td class="num">([^<]*)</td>', body)
        assert cells == [
            str(station["epics"]),
            f"{station['done']} / {station['total']}",
            str(station["in_progress"]),
            str(station["backlog"]),
            str(station["blocked"]),
        ], name
        assert f'data-width="{width}" style="width:{width}%"' in body, name


@pytest.mark.parametrize(
    ("done", "total", "width"),
    [(104, 105, 99), (152, 152, 100), (351, 369, 95), (0, 0, 0), (5, 0, 0), (0, 7, 0), (9, 8, 100)],
)
def test_bar_width_is_the_floored_integer_percentage(done: int, total: int, width: int) -> None:
    sp, _ = _tools()
    assert sp.bar_width(done, total) == width


def test_a_station_with_total_zero_shows_its_counts_and_an_empty_bar(build_mod, tmp_path: Path) -> None:
    payload = {"generated_at": "t", "stations": [{"station": "pyforge-new", "done": 0, "total": 0, "epics": 1}]}
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True, fleet=_write(tmp_path, payload))
    board = (status_out / "index.html").read_text(encoding="utf-8")
    assert 'data-width="0" style="width:0%"' in board
    assert '<td class="num">0 / 0</td>' in board
    # Counts steward's JSON did not give read as a dash, never as a guess.
    assert board.count('<td class="num">—</td>') == 3


def test_ac2_the_attention_block_lists_each_blocked_and_backlog_key_once(build_mod, tmp_path: Path) -> None:
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True)
    block = _section((status_out / "index.html").read_text(encoding="utf-8"), "status-attention")
    keys = re.findall(r'<li data-key="([^"]+)">', block)
    stories = _fleet()["stories"]
    wanted = [f"{s['station']} {s['story_id']}" for s in stories if s["status"] in ("blocked", "backlog")]
    done = {f"{s['station']} {s['story_id']}" for s in stories if s["status"] == "done"}
    assert wanted and done
    assert sorted(keys) == sorted(set(wanted))
    assert len(keys) == len(set(keys))
    assert not done & set(keys)
    blocked = [k for k in keys if k in {f"{s['station']} {s['story_id']}" for s in stories if s["status"] == "blocked"}]
    assert keys[: len(blocked)] == blocked  # blocked first, then backlog


def test_ac2_a_repeated_key_is_listed_once(build_mod, tmp_path: Path) -> None:
    payload = _fleet()
    payload["stories"] = [*payload["stories"], *payload["stories"]]
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True, fleet=_write(tmp_path, payload))
    keys = re.findall(r'<li data-key="([^"]+)">', (status_out / "index.html").read_text(encoding="utf-8"))
    assert len(keys) == len(set(keys)) == 22


def _attention_block(build_mod, tmp_path: Path, payload: dict) -> str:
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True, fleet=_write(tmp_path, payload))
    return _section((status_out / "index.html").read_text(encoding="utf-8"), "status-attention")


def test_ac2_no_listed_story_under_nonzero_counts_is_not_an_all_clear(build_mod, tmp_path: Path) -> None:
    """The review's regression: the stations count 13 blocked and 9 backlog, the input lists only a
    done story (or no stories at all), so the block says it lists none of them, never the all-clear."""
    for stories in ([{"story_id": "1.1", "status": "done"}], None):
        payload = {"generated_at": "t", "stations": _fleet()["stations"]}
        if stories is not None:
            payload["stories"] = stories
        block = _attention_block(build_mod, tmp_path, payload)
        assert "Nothing needs attention" not in block
        assert "The input lists none of the 13 blocked / 9 backlog stories the station counts show." in block
        assert "<li" not in block


def test_ac2_nothing_needs_attention_when_every_count_is_zero(build_mod, tmp_path: Path) -> None:
    stations = [{**s, "blocked": 0, "backlog": 0} for s in _fleet()["stations"]]
    payload = {"generated_at": "t", "stations": stations, "stories": [{"story_id": "1.1", "status": "done"}]}
    block = _attention_block(build_mod, tmp_path, payload)
    assert "Nothing needs attention: no story is blocked or in the backlog." in block
    assert "<li" not in block


def test_ac2_counts_the_input_does_not_give_are_not_an_all_clear(build_mod, tmp_path: Path) -> None:
    payload = {"generated_at": "t", "stations": [{"station": "pyforge-x", "done": 1, "total": 2}]}
    block = _attention_block(build_mod, tmp_path, payload)
    assert "Nothing needs attention" not in block
    assert "station counts do not say whether any exist" in block


def test_ac2_a_partial_list_says_how_much_it_lists(build_mod, tmp_path: Path) -> None:
    payload = _fleet()
    payload["stories"] = [s for s in payload["stories"] if s["status"] != "backlog"]
    block = _attention_block(build_mod, tmp_path, payload)
    assert len(re.findall(r'<li data-key="', block)) == 13  # noqa: PLR2004
    assert "The input lists 13 of the 13 blocked and 0 of the 9 backlog stories the station counts show." in block


def test_ac2_a_complete_list_carries_no_note(build_mod, tmp_path: Path) -> None:
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True)
    assert "status-attention-note" not in (status_out / "index.html").read_text(encoding="utf-8")


def test_ac3_snapshot_time_and_one_lane1_link(build_mod, tmp_path: Path) -> None:
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True)
    for page in (status_out / "index.html", status_out / "ci" / "index.html"):
        text = page.read_text(encoding="utf-8")
        links = re.findall(r'<a href="/console/">([^<]*)</a>', text)
        assert links == ["Live view on Lane 1"], page
        assert text.count("/console/") == 1, page
        assert "<script src" not in text and "<iframe" not in text and "fetch(" not in text
    board = (status_out / "index.html").read_text(encoding="utf-8")
    assert '<time datetime="2026-10-14T01:56:19+00:00">' in board


def test_ac3_an_input_without_a_snapshot_time_says_so(build_mod, tmp_path: Path) -> None:
    payload = {key: value for key, value in _fleet().items() if key != "generated_at"}
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True, fleet=_write(tmp_path, payload))
    assert "Snapshot time not recorded in the input" in (status_out / "index.html").read_text(encoding="utf-8")


def test_the_pages_carry_the_shared_menu_with_status(build_mod, tmp_path: Path) -> None:
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True)
    board = (status_out / "index.html").read_text(encoding="utf-8")
    guild = (status_out / "ci" / "index.html").read_text(encoding="utf-8")
    assert 'data-pf-menu-link href="../herald/../status/index.html" aria-current="page">Status</a>' in board
    assert 'data-pf-menu-link href="../../herald/../status/index.html">Status</a>' in guild
    assert 'href="../herald/assets/site.css"' in board and 'href="../../herald/assets/site.css"' in guild


# --- AC4: the guild status page -------------------------------------------------------------------


def test_ac4_every_row_in_the_tiles_order_with_live_last(build_mod, tmp_path: Path) -> None:
    status_out, _ = _render(build_mod, tmp_path, flag_enabled=True)
    guild = (status_out / "ci" / "index.html").read_text(encoding="utf-8")
    rows = re.findall(r'<tr data-surface="([^"]+)" data-verdict="([^"]+)">(.*?)</tr>', guild, re.S)
    assert [row_id for row_id, _, _ in rows] == _GUILD_ORDER
    snapshot = {row["id"]: row for row in json.loads(_CI.read_text(encoding="utf-8"))["rows"]}
    for row_id, verdict, body in rows:
        cells = [re.sub(r"<[^>]+>", "", cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", body, re.S)]
        assert len(cells) == 7, row_id
        source = snapshot[row_id]
        expected = [source.get(f) for f in ("id", "verdict", "switch", "paused_since", "review_by", "owner")]
        assert cells[:6] == ["—" if v is None else str(v) for v in expected], row_id
        assert verdict == source["verdict"]
    assert '<time datetime="2026-10-14T12:00:00+00:00">' in guild
    # Steward's text is data: escaped, never markup.
    assert "&lt;b&gt;escaped&lt;/b&gt; &amp; kept" in guild


def test_ac4_the_tile_keeps_its_order_and_its_non_live_rows() -> None:
    _, cst = _tools()
    rows = json.loads(_CI.read_text(encoding="utf-8"))["rows"]
    assert [r["id"] for r in cst.select_non_live_rows(rows)] == _GUILD_ORDER[:-2]
    assert [r["id"] for r in cst.order_rows(rows)] == _GUILD_ORDER


# --- AC5: the shape check -------------------------------------------------------------------------


def _station_case(drop: str) -> dict:
    payload = _fleet()
    del payload["stations"][3][drop]
    return payload


_BAD_INPUTS = {
    "no-stations": ({"generated_at": "t"}, "missing stations"),
    "stations-not-a-list": ({"stations": {"pyforge-atlas": {"done": 1, "total": 1}}}, "stations is not a list"),
    "station-without-done": (_station_case("done"), "station 3 (pyforge-marshal) missing done"),
    "station-without-total": (_station_case("total"), "station 3 (pyforge-marshal) missing total"),
    "not-json": ("{stations: [", "not valid JSON"),
}


@pytest.mark.parametrize("case", sorted(_BAD_INPUTS))
def test_ac5_shape_refusals_name_the_file(tmp_path: Path, case: str) -> None:
    sp, _ = _tools()
    payload, message = _BAD_INPUTS[case]
    path = _write(tmp_path, payload)
    with pytest.raises(sp.FleetStatusShapeError) as exc:
        sp.load_fleet_status(path)
    assert str(exc.value).startswith(f"{path}: ")
    assert message in str(exc.value)
    assert sp.collect_shape_problems(path, enabled=True) == [str(exc.value)]
    assert sp.collect_shape_problems(path, enabled=False) == []


def test_ac5_no_input_names_the_path(tmp_path: Path) -> None:
    sp, _ = _tools()
    missing = tmp_path / "fleet-status.json"
    with pytest.raises(sp.FleetStatusShapeError, match="fleet-status input missing"):
        sp.load_fleet_status(missing)
    assert sp.collect_shape_problems(missing, enabled=True) == [f"{missing}: fleet-status input missing"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p["stations"].__setitem__(0, "pyforge-atlas"), "station 0 is not an object"),
        (lambda p: p["stations"][2].__setitem__("done", "132"), "station 2 (pyforge-herald) done is not"),
        (lambda p: p["stations"][2].__setitem__("total", -1), "station 2 (pyforge-herald) total is not"),
        (
            lambda p: p["stations"][3].__setitem__("done", 454),
            "station 3 (pyforge-marshal) done 454 is more than total 453",
        ),
        (lambda p: p.__setitem__("stories", {"x": 1}), "stories is not a list"),
        (lambda p: p["stories"][0].pop("status"), "story 0 missing status"),
    ],
)
def test_ac5_a_value_the_board_cannot_draw_is_refused(tmp_path: Path, mutate, message: str) -> None:
    sp, _ = _tools()
    payload = _fleet()
    mutate(payload)
    with pytest.raises(sp.FleetStatusShapeError, match=re.escape(message)):
        sp.load_fleet_status(_write(tmp_path, payload))


def test_ac5_extra_keys_change_nothing(build_mod, tmp_path: Path) -> None:
    payload = _fleet()
    payload["a_new_envelope_key"] = {"nested": [1, 2]}
    for station in payload["stations"]:
        station["a_new_station_key"] = "ignored"
    plain, _ = _render(build_mod, tmp_path / "plain", flag_enabled=True)
    extra, _ = _render(build_mod, tmp_path / "extra", flag_enabled=True, fleet=_write(tmp_path, payload))
    assert (plain / "index.html").read_text(encoding="utf-8") == (extra / "index.html").read_text(encoding="utf-8")


def test_ac5_the_build_refuses_before_writing(build_mod, tmp_path: Path) -> None:
    sp, _ = _tools()
    out = tmp_path / "herald"
    bad = _write(tmp_path, _station_case("total"))
    with pytest.raises(sp.FleetStatusShapeError, match="station 3"):
        build_mod.build(
            out,
            REPO_ROOT,
            kedro_viz_export=tmp_path / "no-export",
            status_out=tmp_path / "status",
            fleet_status=bad,
            status_pages=True,
        )
    assert not out.exists() and not (tmp_path / "status").exists()


# --- AC6: the menu --------------------------------------------------------------------------------

_SIX = ["Docs", "Overview", "Dossier", "Infographics", "Decks", "Kedro-Viz"]
_SEVEN = ["Docs", "Overview", "Dossier", "Infographics", "Decks", "Status", "Kedro-Viz"]


def test_ac6_one_nav_list_gains_status_only_with_the_flag() -> None:
    sp, _ = _tools()
    data = _site_cfg()
    entries = [*data["nav"], *data["neighbours"]]
    assert [e["label"] for e in sp.menu_entries(entries, enabled=True)] == _SEVEN
    assert [e["label"] for e in sp.menu_entries(entries, enabled=False)] == _SIX
    status = next(e for e in data["nav"] if e["key"] == "status")
    assert status["href"] == "../status/index.html" and status["flag"] == _FLAG


def test_ac6_an_entry_gated_on_an_unknown_flag_is_refused() -> None:
    sp, _ = _tools()
    with pytest.raises(ValueError, match="unknown flag"):
        sp.menu_entries([{"key": "x", "label": "X", "href": "x/", "flag": "pyforge.herald.other"}], enabled=True)


@pytest.mark.parametrize("enabled", [True, False], ids=["on", "off"])
def test_ac6_the_docs_menus_follow_the_flag(enabled: bool) -> None:
    gen = _load(REPO_ROOT / "docs-site" / "scripts" / "sidebar_from_map.py", "sidebar_from_map_status_under_test")
    menu = gen.load_site_menu(_SITE_YML, status_pages=enabled)
    labels = _SEVEN if enabled else _SIX
    assert [item["label"] for item in gen.top_menu(menu)] == labels
    herald = gen.herald_sidebar_group(menu)
    assert [item["label"] for item in herald["items"]] == labels[1:]
    assert ({"link": "/status/", "label": "Status"} in herald["items"]) is enabled


@pytest.mark.parametrize("enabled", [True, False], ids=["on", "off"])
def test_ac6_pages_check_expects_the_seven_or_six_link_menu(enabled: bool) -> None:
    assemble = _load(_TOOLS / "assemble_pages.py", "assemble_pages_status_under_test")
    labels = [label for label, _ in assemble._expected_menu(status_pages=enabled)]
    assert labels == (_SEVEN if enabled else _SIX)


def test_ac6_pages_check_refuses_a_flag_on_menu_without_status(capsys) -> None:
    assemble = _load(_TOOLS / "assemble_pages.py", "assemble_pages_status_menu_under_test")
    expected = assemble._expected_menu(status_pages=False)
    with pytest.raises(SystemExit) as exc:
        assemble._check_status_menu_entry(expected)
    assert exc.value.code == 1
    assert "no entry linking status/index.html" in capsys.readouterr().err
    assemble._check_status_menu_entry(assemble._expected_menu(status_pages=True))


# --- AC7: flag off --------------------------------------------------------------------------------


@pytest.mark.parametrize("fleet_input", ["valid", "malformed", "absent"])
def test_ac7_flag_off_changes_no_file_and_opens_no_input(
    build_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fleet_input: str
) -> None:
    """Off, every herald file is byte-identical to a build without this story's two templates, no
    status page is written, and the input is never opened (valid, malformed or absent)."""
    sp, cst = _tools()
    fleet = {"valid": _FLEET, "malformed": _write(tmp_path, "{not json"), "absent": tmp_path / "none.json"}[fleet_input]
    monkeypatch.setattr(sp, "load_fleet_status", lambda path: pytest.fail(f"opened {path} with the flag off"))
    kw = {"kedro_viz_export": tmp_path / "no-export", "fleet_status": fleet, "status_pages": False}

    with_story = tmp_path / "with" / "herald"
    build_mod.build(with_story, REPO_ROOT, status_out=tmp_path / "with" / "status", **kw)

    templates = tmp_path / "templates-without-42-1"
    shutil.copytree(build_mod.TEMPLATES, templates)
    for name in ("page_status.html.j2", "page_status_ci.html.j2"):
        (templates / name).unlink()
    monkeypatch.setattr(build_mod, "TEMPLATES", templates)
    without = tmp_path / "without" / "herald"
    build_mod.build(without, REPO_ROOT, **kw)

    assert not (tmp_path / "with" / "status").exists()
    compared = filecmp.dircmp(with_story, without)
    _assert_same_tree(compared)
    for page in with_story.rglob("*.html"):
        assert ">Status</a>" not in page.read_text(encoding="utf-8", errors="replace"), page


def _assert_same_tree(cmp: filecmp.dircmp) -> None:
    assert not cmp.left_only and not cmp.right_only, (cmp.left, cmp.left_only, cmp.right_only)
    _, mismatch, errors = filecmp.cmpfiles(cmp.left, cmp.right, cmp.common_files, shallow=False)
    assert not mismatch and not errors, (cmp.left, mismatch, errors)
    for sub in cmp.subdirs.values():
        _assert_same_tree(sub)


# --- AC8: the boundary ----------------------------------------------------------------------------

_STATUS_MODULES = [
    REPO_ROOT / "src/shared/packages/pyforge-herald/src/pyforge/herald/status_pages.py",
    _TOOLS / "status_pages.py",
    _TOOLS / "export_status_pages_env.py",
    _TOOLS / "ci_surfaces_tile.py",
    _TOOLS / "assemble_pages.py",
    REPO_ROOT / "docsite" / "build.py",
]


@pytest.mark.parametrize("path", _STATUS_MODULES, ids=lambda p: p.name)
def test_ac8_no_steward_import_and_no_gh_call(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(a.name.startswith("pyforge.steward") for a in node.names), path
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("pyforge.steward"), path
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value != "gh", f"{path}: a literal 'gh' argument"
