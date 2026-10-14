"""CI surfaces tile flag states and render (Story 39.1, CAP-59)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.herald.ci_surfaces_tile import CI_SURFACES_TILE_FLAG

flag_provider = make_flag_provider_fixture()

VERDICT_ORDER = (
    "drift",
    "stuck",
    "overdue",
    "paused",
    "paused-manually",
    "opt-in-off",
    "retired",
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _load_ci_surfaces_tool():
    root = _repo_root()
    tools = root / "docsite" / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    path = tools / "ci_surfaces_tile.py"
    spec = importlib.util.spec_from_file_location("ci_surfaces_tile_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_snapshot(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "ci-status.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fixture_all_verdicts() -> dict:
    rows = []
    for verdict in VERDICT_ORDER:
        rows.append(
            {
                "id": f"surface.{verdict}",
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
        )
    rows.append(
        {
            "id": "surface.live",
            "switch": "SW_LIVE",
            "declared_state": "live",
            "live_switch_value": None,
            "paused_since": None,
            "review_by": None,
            "review_days_left": None,
            "owner": "pyforge-steward",
            "last_green_run": "2026-10-14T00:00:00Z",
            "verdict": "live",
        }
    )
    rows.append(
        {
            "id": "surface.quarantined",
            "switch": None,
            "declared_state": "unknown",
            "live_switch_value": None,
            "paused_since": None,
            "review_by": None,
            "review_days_left": None,
            "owner": None,
            "last_green_run": None,
            "verdict": "quarantined",
            "detail": "synthetic unknown verdict",
        }
    )
    return {
        "fetched_at": "2026-10-14T12:00:00+00:00",
        "repo": "rxm7706/local-recipes",
        "rate_limit": {"core_limit": 5000, "core_remaining": 5000},
        "rows": rows,
    }


def test_ac1_lines_per_verdict_in_order(tmp_path: Path) -> None:
    cst = _load_ci_surfaces_tool()
    snap = _write_snapshot(tmp_path, _fixture_all_verdicts())
    block = cst.render_ci_surfaces_tile(flag_enabled=True, snapshot_path=snap)
    assert block is not None
    assert block["fetched_at"] == "2026-10-14T12:00:00+00:00"
    assert len(block["lines"]) == len(VERDICT_ORDER) + 1
    for index, verdict in enumerate(VERDICT_ORDER):
        assert f"surface.{verdict}" in block["lines"][index]
        assert verdict in block["lines"][index]
    assert "surface.quarantined" in block["lines"][-1]
    assert "surface.live" not in "".join(block["lines"])


def test_ac2_all_live(tmp_path: Path) -> None:
    cst = _load_ci_surfaces_tool()
    payload = {
        "fetched_at": "2026-10-14T12:00:00+00:00",
        "repo": "rxm7706/local-recipes",
        "rate_limit": {"core_limit": 5000, "core_remaining": 5000},
        "rows": [
            {
                "id": "a",
                "switch": None,
                "declared_state": "live",
                "live_switch_value": None,
                "verdict": "live",
            }
        ],
    }
    snap = _write_snapshot(tmp_path, payload)
    block = cst.render_ci_surfaces_tile(flag_enabled=True, snapshot_path=snap)
    assert block is not None
    assert block["all_live"] is True
    assert len(block["lines"]) == 1
    assert "live" in block["lines"][0].lower()


@flag_states(CI_SURFACES_TILE_FLAG)
def test_ac8_render_follows_flag_state(flag_provider: dict[str, bool], tmp_path: Path) -> None:
    cst = _load_ci_surfaces_tool()
    snap = _write_snapshot(tmp_path, _fixture_all_verdicts())
    enabled = flag_provider[CI_SURFACES_TILE_FLAG]
    block = cst.render_ci_surfaces_tile(flag_enabled=enabled, snapshot_path=snap)
    if enabled:
        assert block is not None
        assert block["lines"]
    else:
        assert block is None


def test_overdue_and_due_today_formatting(tmp_path: Path) -> None:
    cst = _load_ci_surfaces_tool()
    assert cst.format_days_left(-3) == "3 days overdue"
    assert cst.format_days_left(0) == "due today"
    assert cst.format_days_left(5) == "5 days left"


def test_ac4_shape_refusals(tmp_path: Path) -> None:
    cst = _load_ci_surfaces_tool()
    path = tmp_path / "ci-status.json"

    with pytest.raises(cst.CiStatusShapeError, match="missing"):
        cst.validate_ci_status_envelope({}, path=str(path))

    with pytest.raises(cst.CiStatusShapeError, match="missing fetched_at"):
        cst.validate_ci_status_envelope({"rows": []}, path=str(path))

    with pytest.raises(cst.CiStatusShapeError, match="missing rows"):
        cst.validate_ci_status_envelope({"fetched_at": "t"}, path=str(path))

    with pytest.raises(cst.CiStatusShapeError, match="rows is not a list"):
        cst.validate_ci_status_envelope({"fetched_at": "t", "rows": {}}, path=str(path))

    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(cst.CiStatusShapeError, match="not valid JSON"):
        cst.load_ci_status_snapshot(path)

    missing = tmp_path / "absent.json"
    with pytest.raises(cst.CiStatusShapeError, match="snapshot missing"):
        cst.load_ci_status_snapshot(missing)

    bad_row = {
        "fetched_at": "t",
        "repo": "r",
        "rate_limit": {"core_limit": 1, "core_remaining": 1},
        "rows": [{"verdict": "paused"}],
    }
    with pytest.raises(cst.CiStatusShapeError, match="row 0 missing id"):
        cst.validate_ci_status_envelope(bad_row, path=str(path))

    bad_verdict = {
        "fetched_at": "t",
        "repo": "r",
        "rate_limit": {"core_limit": 1, "core_remaining": 1},
        "rows": [{"id": "dashboard.deploy"}],
    }
    with pytest.raises(cst.CiStatusShapeError, match="row 0 \\(dashboard.deploy\\) missing verdict"):
        cst.validate_ci_status_envelope(bad_verdict, path=str(path))
