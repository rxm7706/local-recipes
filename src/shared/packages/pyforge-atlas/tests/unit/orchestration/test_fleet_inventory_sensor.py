"""Story 25.2 — fleet inventory poll-cursor decision logic and sensor wiring."""

from __future__ import annotations

import json
from pathlib import Path

import dagster as dg
import pytest

from pyforge.atlas.orchestration import definitions as D
from pyforge.atlas.orchestration.fleet_inventory_sensor import (
    FLAG_KEY,
    FleetRepoHead,
    evaluate_fleet_inventory,
    evaluate_fleet_inventory_from_raw,
    offline_fleet_inventory_source,
    parse_fleet_inventory,
)
from pyforge.core.flags import read_boolean


def _export(*repos: tuple[str, str]) -> dict:
    return {"repos": [{"full_name": n, "head_sha": sha} for n, sha in repos]}


def _cursor(mapping: dict[str, str]) -> str:
    return json.dumps(mapping, sort_keys=True)


def test_nothing_moved_skips_and_leaves_cursor():
    inv = _export(("org/a", "aaa"), ("org/b", "bbb"), ("org/c", "ccc"))
    cur = _cursor({"org/a": "aaa", "org/b": "bbb", "org/c": "ccc"})
    decision = evaluate_fleet_inventory_from_raw(inv, cur, run_key_prefix="dep")
    assert not decision.run
    assert decision.new_cursor == cur
    assert decision.moved_repos == ()


def test_two_heads_moved_coalesce_one_run():
    inv = _export(("org/a", "aaa2"), ("org/b", "bbb"), ("org/c", "ccc2"))
    cur = _cursor({"org/a": "aaa", "org/b": "bbb", "org/c": "ccc"})
    decision = evaluate_fleet_inventory_from_raw(inv, cur, run_key_prefix="dep")
    assert decision.run
    assert decision.moved_repos == ("org/a", "org/c")
    assert decision.run_key and decision.run_key.startswith("dep:")
    assert json.loads(decision.new_cursor or "{}") == {
        "org/a": "aaa2",
        "org/b": "bbb",
        "org/c": "ccc2",
    }


def test_new_repo_treated_as_moved():
    inv = _export(("org/a", "aaa"), ("org/b", "bbb"), ("org/new", "n1"))
    cur = _cursor({"org/a": "aaa", "org/b": "bbb"})
    decision = evaluate_fleet_inventory_from_raw(inv, cur, run_key_prefix="dep")
    assert decision.run
    assert "org/new" in decision.moved_repos


def test_repo_removed_dropped_from_cursor_no_run():
    inv = _export(("org/a", "aaa"))
    cur = _cursor({"org/a": "aaa", "org/gone": "old"})
    decision = evaluate_fleet_inventory_from_raw(inv, cur, run_key_prefix="dep")
    assert not decision.run
    assert json.loads(decision.new_cursor or "{}") == {"org/a": "aaa"}


def test_malformed_export_skips_cursor_unchanged():
    cur = _cursor({"org/a": "aaa"})
    decision = evaluate_fleet_inventory_from_raw({"repos": "nope"}, cur, run_key_prefix="dep")
    assert not decision.run
    assert decision.new_cursor == cur
    assert "malformed" in (decision.skip_reason or "")


def test_offline_inventory_source_no_network():
    assert offline_fleet_inventory_source() == {"repos": []}


def test_parse_none_is_empty():
    assert parse_fleet_inventory(None) == ()


def _bool_tree(tmp_path: Path, variant: str) -> Path:
    path = tmp_path / "flags.json"
    path.write_text(
        json.dumps(
            {
                "flags": {
                    FLAG_KEY: {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": variant,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_flag_off_skips(defs, tmp_path):
    job = next(j for j in defs.jobs if j.name == D.DEPENDENCY_HISTORY_JOB_NAME)
    tree = _bool_tree(tmp_path, "off")
    sensor = D.build_fleet_inventory_sensor(
        job=job,
        inventory_source=lambda: _export(("org/a", "aaa")),
        flags_path=tree,
    )
    results = list(sensor(dg.build_sensor_context()))
    assert len(results) == 1 and isinstance(results[0], dg.SkipReason)
    assert results[0].skip_message == "flag off"


def test_flag_on_decides_over_fixture_export(defs, tmp_path):
    job = next(j for j in defs.jobs if j.name == D.DEPENDENCY_HISTORY_JOB_NAME)
    tree = _bool_tree(tmp_path, "on")
    assert read_boolean(FLAG_KEY, flags_path=tree) is True
    inv = _export(("org/a", "aaa"))
    sensor = D.build_fleet_inventory_sensor(
        job=job,
        inventory_source=lambda: inv,
        flags_path=tree,
    )
    results = list(sensor(dg.build_sensor_context()))
    runs = [r for r in results if isinstance(r, dg.RunRequest)]
    assert len(runs) == 1


@pytest.mark.parametrize(
    ("heads", "cursor", "expect_run"),
    [
        ([("org/a", "1")], {}, True),  # new repo
        ([("org/a", "1")], {"org/a": "1"}, False),  # unchanged
        ([("org/a", "2")], {"org/a": "1"}, True),  # moved
    ],
)
def test_matrix_rows(heads, cursor, expect_run):
    parsed = tuple(FleetRepoHead(n, s) for n, s in heads)
    decision = evaluate_fleet_inventory(parsed, _cursor(cursor), run_key_prefix="dep")
    assert decision.run is expect_run
