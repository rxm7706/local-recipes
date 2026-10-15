"""Story 42.1 (spec-pyforge-herald CAP-60): the fleet board and guild status pages render at build.

Since Story 43.7 they are Astro pages (``docs-site/src/pages/status/``) over ``docs-site/src/lib/status.ts``, which
reads and shapes both inputs: ``fleet-status.json`` (steward's ``sprint-ledger-query --format json``, reshaped) and the
committed ``ci-status.json`` (CAP-59's one reading). The flag reaches the build as ``PYFORGE_STATUS_PAGES``, exported by
``python -m pyforge.herald.pages_env`` from the flag tree. The model runs through node with type stripping (no
``node_modules``); the built pages are ``test_one_generator.py``'s and ``test_pages_artifact.py``'s. Fixtures: the
2026-10-14 ledgers reshaped as steward names them, and a snapshot with one row per verdict.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.herald import pages_env
from pyforge.herald.status_pages import STATUS_PAGES_FLAG, status_pages_enabled

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "meta"))
from pages_astro import DOCS_SITE, REPO_ROOT, needs_node, ts  # noqa: E402 -- the shared Pages helpers

_FLAG = "pyforge.herald.status_pages"
flag_provider = make_flag_provider_fixture()

STATUS_TS = DOCS_SITE / "src" / "lib" / "status.ts"
FLAGS_TS = DOCS_SITE / "src" / "lib" / "flags.ts"
_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_FLEET = _FIXTURES / "fleet-status-2026-10-14.json"
_CI = _FIXTURES / "ci-status-every-verdict.json"

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


def _board(data: object) -> object:
    return ts(STATUS_TS, "m.validateFleetStatus(inp.data, 'fleet-status.json'); return m.board(inp.data);", data=data)


def _fleet() -> dict:
    return json.loads(_FLEET.read_text(encoding="utf-8"))


# --- the flag -------------------------------------------------------------------------------------------------------


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


@flag_states("pyforge.herald.status_pages")
def test_ac9_the_build_env_and_the_pages_follow_the_flag_state(flag_provider: dict[str, bool], tmp_path: Path) -> None:
    """Two states: the Guild step's export says the flag's state (``pages_env``), and the docs-site reads that
    variable as the flag -- on, the three ``/status/`` pages are routes and the menu's Status section shows; off,
    neither."""
    enabled = flag_provider[_FLAG]
    tree = flagd_tree(tmp_path, {_FLAG: "on" if enabled else "off"})
    env = pages_env.build_env(flags_path=tree)
    assert env["PYFORGE_STATUS_PAGES"] == ("1" if enabled else "0")
    assert ts(FLAGS_TS, "return m.envFlagOn('PYFORGE_STATUS_PAGES', inp.env);", env=env) is enabled
    sections = ts(
        DOCS_SITE / "src" / "lib" / "nav.ts",
        "const sections = [{key: 'status', label: 'Status', href: 'status/', owner: 'herald', order: 20}];"
        "return m.siteSections(sections, {mounted: () => false, flag: (key) => inp.on && key === inp.key});",
        on=enabled,
        key=_FLAG,
    )
    assert [s["key"] for s in sections] == (["status"] if enabled else [])
    for page in ("status/[...index].astro", "status/ci/[...index].astro", "status/runs/[...index].astro"):
        source = (DOCS_SITE / "src" / "pages" / page).read_text(encoding="utf-8")
        assert "return statusPages() ? [{ params: { index: undefined } }] : [];" in source, page


def test_the_export_prints_one_line_per_build_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tree = flagd_tree(tmp_path, {_FLAG: "on", "pyforge.herald.ci_surfaces_tile": "off"})
    assert pages_env.build_env(flags_path=tree) == {"PYFORGE_STATUS_PAGES": "1", "PYFORGE_CI_SURFACES_TILE": "0"}
    assert pages_env.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line.split("=")[0] for line in lines] == ["PYFORGE_STATUS_PAGES", "PYFORGE_CI_SURFACES_TILE"]
    assert all(re.fullmatch(r"PYFORGE_\w+=[01]", line) for line in lines)


# --- AC1-AC3: the fleet board ---------------------------------------------------------------------------------------


@needs_node
def test_ac1_one_row_per_station_with_its_bar() -> None:
    board = _board(_fleet())
    assert [row["name"] for row in board["stations"]] == [f"pyforge-{s}" for s in _STATIONS]
    assert [row["width"] for row in board["stations"]] == _WIDTHS
    assert board["generatedAt"] == _fleet()["generated_at"]


@needs_node
@pytest.mark.parametrize(("done", "total", "width"), [(0, 0, 0), (1, 3, 33), (2, 3, 66), (3, 3, 100), (5, 4, 100)])
def test_bar_width_is_the_floored_integer_percentage(done: int, total: int, width: int) -> None:
    assert ts(STATUS_TS, "return m.barWidth(inp.done, inp.total);", done=done, total=total) == width


def _station(name: str, **counts: int) -> dict:
    return {"station": name, "done": 1, "total": 2, **counts}


@needs_node
def test_ac2_the_attention_block_lists_each_blocked_then_backlog_key_once() -> None:
    data = {
        "stations": [_station("pyforge-a", blocked=1, backlog=1)],
        "stories": [
            {"story_id": "1.2", "station": "pyforge-a", "status": "backlog", "title": "later"},
            {"story_id": "1.1", "station": "pyforge-a", "status": "blocked", "title": "stuck"},
            {"story_id": "1.1", "station": "pyforge-a", "status": "blocked", "title": "stuck again"},
            {"story_id": "1.3", "station": "pyforge-a", "status": "done"},
        ],
    }
    board = _board(data)
    assert [(a["story_id"], a["status"]) for a in board["attention"]] == [("1.1", "blocked"), ("1.2", "backlog")]
    assert board["attentionNote"] is None


@needs_node
@pytest.mark.parametrize(
    ("stations", "stories", "note"),
    [
        ([_station("a", blocked=0, backlog=0)], [], "Nothing needs attention: no story is blocked or in the backlog."),
        ([_station("a", blocked=2, backlog=1)], [], "The input lists none of the 2 blocked / 1 backlog stories"),
        ([_station("a")], [], "its station counts do not say whether any exist"),
        (
            [_station("a", blocked=1, backlog=0), _station("b", blocked=0, backlog=1)],
            [
                {"story_id": "1", "station": "a", "status": "blocked"},
                {"story_id": "2", "station": "a", "status": "blocked"},
            ],
            "a: 2 blocked listed, 1 counted; b: 0 backlog listed, 1 counted",
        ),
        (
            [_station("a", blocked=0, backlog=0)],
            [{"story_id": "9", "station": "ghost", "status": "blocked"}],
            "ghost: 1 blocked listed, no station row counts them",
        ),
    ],
    ids=["all-clear", "none-listed", "counts-unknown", "per-station", "unknown-station"],
)
def test_ac2_the_note_never_claims_an_all_clear_the_counts_contradict(stations: list, stories: list, note: str) -> None:
    board = _board({"stations": stations, "stories": stories})
    assert note in (board["attentionNote"] or ""), board


@needs_node
@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "fleet-status.json: envelope is not a JSON object"),
        ({}, "fleet-status.json: missing stations"),
        ({"stations": {}}, "stations is not a list"),
        ({"stations": [{"station": "a", "total": 1}]}, "station 0 (a) missing done"),
        ({"stations": [{"done": -1, "total": 1}]}, "station 0 done is not a non-negative integer"),
        ({"stations": [{"done": 1.5, "total": 2}]}, "station 0 done is not a non-negative integer"),
        ({"stations": [{"done": 3, "total": 2}]}, "station 0 done 3 is more than total 2"),
        ({"stations": [], "stories": {}}, "stories is not a list"),
        ({"stations": [], "stories": [{"status": "blocked"}]}, "story 0 missing story_id"),
    ],
)
def test_ac5_a_malformed_input_is_refused_naming_the_file(data: object, message: str) -> None:
    result = _board(data)
    assert result == {"error": "StatusInputShapeError", "message": result["message"]}
    assert message in result["message"]


@needs_node
def test_ac5_a_missing_or_unreadable_input_names_the_path(tmp_path: Path) -> None:
    absent = ts(STATUS_TS, "return m.loadFleetStatus(inp.file);", file=str(tmp_path / "fleet-status.json"))
    assert (
        absent["error"] == "StatusInputShapeError"
        and "fleet-status.json: fleet-status input missing" in absent["message"]
    )
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    result = ts(STATUS_TS, "return m.loadFleetStatus(inp.file);", file=str(broken))
    assert "broken.json: not valid JSON" in result["message"]


@needs_node
def test_ac3_lane1_is_linked_only_by_an_absolute_url() -> None:
    hrefs = ["/console/", "console/", "//lane1.example/", "https://lane1.example/console/", None]
    links = ts(
        DOCS_SITE / "src" / "lib" / "agent-surface.ts",
        "return inp.hrefs.map((href) => m.lane1Link(href === null ? null : { label: 'Live', href }));",
        hrefs=hrefs,
    )
    assert links == [None, None, None, {"href": "https://lane1.example/console/", "label": "Live"}, None]


# --- AC4: the guild status page ---------------------------------------------------------------------------------------


@needs_node
def test_ac4_every_row_in_the_tiles_order_with_live_last() -> None:
    rows = ts(STATUS_TS, "return m.guildRows(m.loadCiStatus(inp.file));", file=str(_CI))
    assert [row["id"] for row in rows] == _GUILD_ORDER
    assert set(rows[0]) == {"id", "verdict", "switch", "paused_since", "review_by", "owner", "detail"}
    assert all(isinstance(v, str) for row in rows for v in row.values())


def test_ac8_no_steward_import_and_no_gh_call_in_the_status_code() -> None:
    """Herald reads steward's output as data: the status code imports no station and runs no process."""
    for rel in ("src/lib/status.ts", "src/pages/status/[...index].astro", "src/pages/status/ci/[...index].astro"):
        text = (DOCS_SITE / rel).read_text(encoding="utf-8")
        imports = re.findall(r"^import .* from '([^']+)';", text, re.M)
        assert all(source.startswith(("node:", "../", "./", "@astrojs/")) for source in imports), (rel, imports)
        assert "child_process" not in text and "spawn" not in text and "execFile" not in text, rel
