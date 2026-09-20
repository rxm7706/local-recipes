"""Per-module coverage floors (marshal Story 53.2 landing, 2026-09-20): a
dated, story-bound exception for one module that can only lower the
station floor, is never anonymous, and is named on the gate's OK line."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.coverage_gate import (
    ModuleFloor,
    evaluate_coverage_payload,
    evaluate_suite,
    floor_for_module,
    load_module_floors,
    modules_below_threshold,
)

TOML = """[defaults]
unit = 80.0
integration = 70.0

[modules."pyforge.marshal.big"]
unit = 35.0
until = "marshal Story 99.9"
story = "99-9-big-reaches-the-floor"
"""


def test_load_module_floors_reads_a_dated_story_bound_entry(tmp_path: Path) -> None:
    p = tmp_path / "t.toml"
    p.write_text(TOML, encoding="utf-8")
    floors = load_module_floors(p)
    assert floors == {
        "pyforge.marshal.big": ModuleFloor(
            module="pyforge.marshal.big",
            unit=35.0,
            integration=None,
            until="marshal Story 99.9",
            story="99-9-big-reaches-the-floor",
        )
    }
    assert load_module_floors(tmp_path / "absent.toml") == {}


def test_an_anonymous_exception_is_refused(tmp_path: Path) -> None:
    p = tmp_path / "t.toml"
    p.write_text('[modules."x.y"]\nunit = 10.0\n', encoding="utf-8")
    with pytest.raises(ValueError, match="never anonymous"):
        load_module_floors(p)


def test_an_exception_can_only_lower_the_floor() -> None:
    floors = {
        "m": ModuleFloor(module="m", unit=90.0, until="d", story="s"),
        "n": ModuleFloor(module="n", unit=35.0, until="d", story="s"),
    }
    assert floor_for_module("m", 80.0, suite="unit", module_floors=floors) == 80.0  # above the station floor: ignored
    assert floor_for_module("n", 80.0, suite="unit", module_floors=floors) == 35.0
    assert floor_for_module("n", 70.0, suite="integration", module_floors=floors) == 70.0  # no integration entry
    assert floor_for_module("other", 80.0, suite="unit", module_floors=floors) == 80.0


def test_evaluation_holds_the_module_to_its_exception_and_names_it() -> None:
    floors = {
        "pyforge.marshal.big": ModuleFloor(
            module="pyforge.marshal.big", unit=35.0, until="marshal Story 99.9", story="99-9-big-reaches-the-floor"
        )
    }
    percents = {"pyforge.marshal.big": 36.0, "pyforge.marshal.small": 91.0}
    assert modules_below_threshold(percents, 80.0, suite="unit", module_floors=floors) == []
    ok, message = evaluate_suite(percents, suite="unit", threshold=80.0, station="marshal", module_floors=floors)
    assert (
        ok
        and "1 under a dated exception" in message
        and "pyforge.marshal.big (36.0% ≥ 35%, until marshal Story 99.9, 99-9-big-reaches-the-floor)" in message
    )
    below = modules_below_threshold({"pyforge.marshal.big": 34.0}, 80.0, suite="unit", module_floors=floors)
    assert [(f.module, f.threshold) for f in below] == [("pyforge.marshal.big", 35.0)]


def test_evaluate_coverage_payload_reads_the_exceptions_from_the_thresholds_file(tmp_path: Path) -> None:
    p = tmp_path / "t.toml"
    p.write_text(TOML, encoding="utf-8")
    payload = {"pyforge.marshal.big": 36.0, "pyforge.marshal.small": 91.0}
    ok, message = evaluate_coverage_payload(payload, station="marshal", suite="unit", thresholds_path=p)
    assert ok and "under a dated exception" in message
    ok, message = evaluate_coverage_payload(
        {"pyforge.marshal.small": 50.0}, station="marshal", suite="unit", thresholds_path=p
    )
    assert not ok and "pyforge.marshal.small" in message


def test_the_live_file_names_the_supervisor_exception_with_its_story() -> None:
    floors = load_module_floors()
    entry = floors["pyforge.marshal.dispatch_supervisor.__main__"]
    assert entry.unit == 35.0 and entry.story == "53-3-the-supervisor-entrypoint-reaches-the-floor" and entry.until
