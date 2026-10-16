"""CI surfaces tile flag states and render (Story 39.1, CAP-59).

Since Story 43.7 the tile is shaped at build by ``docs-site/src/lib/status.ts`` (``tileBlock``; the retired Jinja
path's ``ci_surfaces_tile.py`` rules, ported), applied by the dossier loader with ``pyforge.herald.ci_surfaces_tile``
on, which the Guild step exports as ``PYFORGE_CI_SURFACES_TILE`` (``python -m pyforge.herald.pages_env``). The model
runs through node with type stripping (no ``node_modules``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.herald import pages_env
from pyforge.herald.ci_surfaces_tile import CI_SURFACES_TILE_FLAG, ci_surfaces_tile_enabled

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "meta"))
from pages_astro import DOCS_SITE, needs_node, ts  # noqa: E402 -- the shared Pages helpers

flag_provider = make_flag_provider_fixture()

STATUS_TS = DOCS_SITE / "src" / "lib" / "status.ts"
LOADER = DOCS_SITE / "src" / "loaders" / "dossier-loader.ts"
VERDICT_ORDER = ("drift", "stuck", "overdue", "paused", "paused-manually", "opt-in-off", "retired")


def _row(row_id: str, verdict: str, **extra: object) -> dict:
    row = {
        "id": row_id,
        "switch": f"SW_{verdict.upper()}",
        "declared_state": "paused",
        "live_switch_value": "true",
        "paused_since": "2026-10-01",
        "review_by": "2026-10-15",
        "review_days_left": 1,
        "owner": "pyforge-steward",
        "last_green_run": None,
        "verdict": verdict,
    }
    return {**row, **extra}


def _snapshot(rows: list[dict]) -> dict:
    return {"fetched_at": "2026-10-14T12:00:00+00:00", "repo": "rxm7706/local-recipes", "rows": rows}


def _every_verdict() -> dict:
    rows = [_row(f"surface.{v}", v) for v in VERDICT_ORDER]
    rows.append(_row("surface.live", "live", declared_state="live", review_days_left=None))
    rows.append(_row("surface.quarantined", "quarantined", detail="synthetic unknown verdict"))
    return _snapshot(rows)


def _tile(data: dict) -> dict:
    result = ts(STATUS_TS, "m.validateCiStatus(inp.data, 'ci-status.json'); return m.tileBlock(inp.data);", data=data)
    assert isinstance(result, dict) and "error" not in result, result
    return result


@needs_node
def test_ac1_one_line_per_surface_that_is_not_live_in_the_tiles_order() -> None:
    block = _tile(_every_verdict())
    assert block["type"] == "ci_surfaces" and block["fetched_at"] == "2026-10-14T12:00:00+00:00"
    assert len(block["lines"]) == len(VERDICT_ORDER) + 1
    for index, verdict in enumerate(VERDICT_ORDER):
        assert block["lines"][index].startswith(f"**surface.{verdict}** · {verdict} · switch SW_{verdict.upper()}")
    assert block["lines"][-1].endswith("· synthetic unknown verdict")
    assert "surface.live" not in "".join(block["lines"]) and block["all_live"] is False


@needs_node
def test_ac2_all_live_is_one_line() -> None:
    block = _tile(_snapshot([_row("a", "live")]))
    assert block == {
        "type": "ci_surfaces",
        "fetched_at": "2026-10-14T12:00:00+00:00",
        "lines": ["All CI surfaces reported **live** at capture."],
        "all_live": True,
    }


@flag_states(CI_SURFACES_TILE_FLAG)
def test_ac8_the_tile_follows_the_flag_state(flag_provider: dict[str, bool], tmp_path: Path) -> None:
    """Two states: the Guild step's export says the flag's state, and the dossier loader applies the tile only when
    the variable it hands reads on (``flags.ts``'s ``ciSurfacesTile``), else drops the block."""
    enabled = flag_provider[CI_SURFACES_TILE_FLAG]
    tree = flagd_tree(tmp_path, {CI_SURFACES_TILE_FLAG: "on" if enabled else "off"})
    assert ci_surfaces_tile_enabled(flags_path=tree) is enabled
    env = pages_env.build_env(flags_path=tree)
    assert env["PYFORGE_CI_SURFACES_TILE"] == ("1" if enabled else "0")
    on = ts(DOCS_SITE / "src" / "lib" / "flags.ts", "return m.envFlagOn('PYFORGE_CI_SURFACES_TILE', inp.env);", env=env)
    assert on is enabled
    loader = LOADER.read_text(encoding="utf-8")
    assert "const payload = ciSurfacesTile() ? tileBlock(loadCiStatus(CI_STATUS)) : null;" in loader
    assert "blocks.filter((b) => b.type !== 'ci_surfaces')" in loader


@needs_node
@pytest.mark.parametrize(("left", "text"), [(-3, "3 days overdue"), (0, "due today"), (5, "5 days left"), (None, "—")])
def test_days_left_reads_as_the_tile_says_it(left: int | None, text: str) -> None:
    assert f"· {text} ·" in ts(STATUS_TS, "return m.tileLine(inp.row);", row=_row("x", "paused", review_days_left=left))


@needs_node
@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({}, "missing fetched_at"),
        ({"rows": []}, "missing fetched_at"),
        ({"fetched_at": "t"}, "missing rows"),
        ({"fetched_at": "t", "rows": {}}, "rows is not a list"),
        ({"fetched_at": "t", "rows": [{"verdict": "paused"}]}, "row 0 missing id"),
        ({"fetched_at": "t", "rows": [{"id": "dashboard.deploy"}]}, "row 0 (dashboard.deploy) missing verdict"),
    ],
)
def test_ac4_shape_refusals(data: dict, message: str) -> None:
    result = ts(STATUS_TS, "m.validateCiStatus(inp.data, 'ci-status.json');", data=data)
    assert result["error"] == "StatusInputShapeError" and message in result["message"], result


@needs_node
def test_ac4_a_missing_or_broken_snapshot_names_the_file(tmp_path: Path) -> None:
    missing = ts(STATUS_TS, "return m.loadCiStatus(inp.file);", file=str(tmp_path / "ci-status.json"))
    assert "ci-status.json: snapshot missing" in missing["message"]
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert "not valid JSON" in ts(STATUS_TS, "return m.loadCiStatus(inp.file);", file=str(broken))["message"]


def test_the_committed_snapshot_parses() -> None:
    data = json.loads((DOCS_SITE / "src" / "content" / "ci-status.json").read_text(encoding="utf-8"))
    assert {"fetched_at", "rows"} <= set(data) and all({"id", "verdict"} <= set(row) for row in data["rows"])
