"""Story 48.5 flag kill-switch actuator tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.actuators.flag_kill_switch import (
    disable_flag,
    kill_switch,
    record_kill_switch_metric,
)


def _sample_tree() -> dict:
    return {
        "flags": {
            "pyforge.three_surfaces": {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": "on",
            }
        }
    }


def test_disable_flag_writes_disabled_state(tmp_path: Path):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    result = disable_flag(path, "pyforge.three_surfaces")
    assert result.new_state == "DISABLED"
    updated = json.loads(path.read_text(encoding="utf-8"))
    assert updated["flags"]["pyforge.three_surfaces"]["state"] == "DISABLED"


def test_kill_switch_records_metric(tmp_path: Path, monkeypatch):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    calls: list[tuple[str, str]] = []

    def _record(flag: str, reason: str) -> None:
        calls.append((flag, reason))

    monkeypatch.setattr(
        "pyforge.doctor.actuators.flag_kill_switch.record_kill_switch_metric",
        _record,
    )
    kill_switch(path, "pyforge.three_surfaces", "test")
    assert calls == [("pyforge.three_surfaces", "test")]


def test_disable_flag_missing_key_raises(tmp_path: Path):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    with pytest.raises(KeyError):
        disable_flag(path, "missing.flag")


def test_record_kill_switch_metric_noop_without_prometheus(monkeypatch):
    monkeypatch.setattr(
        "pyforge.doctor.actuators.flag_kill_switch._KILL_SWITCH_TOTAL",
        None,
    )
    record_kill_switch_metric("pyforge.three_surfaces", "test")
