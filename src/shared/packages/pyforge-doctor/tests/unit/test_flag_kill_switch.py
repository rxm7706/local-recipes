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


_DJANGO_PYFORGE_SRC = Path(__file__).resolve().parents[3] / "django-pyforge" / "src"


def test_cli_kill_switch_edits_the_tree_itself_not_a_rendered_copy(tmp_path: Path, monkeypatch, capsys):
    """Story 76.1: with no ``--flags-path`` the actuator resolves the tree through
    ``django_pyforge.flags.resolve_tree_path``. ``resolve_flags_path`` now returns the
    per-environment rendering (a temp copy) whenever ``flag-overlays.json`` sits beside the
    tree, and a kill switch that edited the copy would report success and change nothing."""
    from pyforge.doctor.__main__ import main

    monkeypatch.syspath_prepend(str(_DJANGO_PYFORGE_SRC))  # django_pyforge.flags imports no Django at module top
    tree = tmp_path / "flags.json"
    tree.write_text(json.dumps(_sample_tree(), indent=2) + "\n", encoding="utf-8")
    (tmp_path / "flag-overlays.json").write_text(
        json.dumps({env: {"pyforge.three_surfaces": "on"} for env in ("dev", "staging", "production")}),
        encoding="utf-8",
    )
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.delenv("FLAGD_OFFLINE_FLAG_SOURCE_PATH", raising=False)
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)

    rc = main(["flags", "kill-switch", "--flag", "pyforge.three_surfaces", "--reason", "test"])

    assert rc == 0
    assert json.loads(tree.read_text(encoding="utf-8"))["flags"]["pyforge.three_surfaces"]["state"] == "DISABLED"
    assert str(tree) in capsys.readouterr().out
    # the overlay is a value document: the actuator leaves it alone
    assert json.loads((tmp_path / "flag-overlays.json").read_text(encoding="utf-8"))["production"] == {
        "pyforge.three_surfaces": "on"
    }


_SHIPPED_CONFIG = Path(__file__).resolve().parents[6] / "src" / "platform" / "config"


def test_killing_the_dated_shipped_flag_leaves_the_tree_composable_and_reads_off(tmp_path: Path, monkeypatch):
    """Story 76.2: ``disable_flag`` sets only ``state``. ``pyforge.three_surfaces`` carries a dated clock
    (``on_everywhere``), so a clock check that judged ``state`` would refuse every flag read of the
    killed tree, the sibling flags' included. It judges the rendered variant, so the kill composes."""
    from pyforge.core import flags

    tree = tmp_path / "flags.json"
    for name in ("flags.json", flags.OVERLAYS_FILE_NAME):
        source = _SHIPPED_CONFIG / name
        if not source.is_file():
            pytest.skip(f"{name} is not in this checkout")
        (tmp_path / name).write_bytes(source.read_bytes())

    disable_flag(tree, "pyforge.three_surfaces")

    killed = json.loads(tree.read_text(encoding="utf-8"))["flags"]["pyforge.three_surfaces"]
    assert killed["state"] == "DISABLED"
    assert killed["metadata"]["on_everywhere"] == "2026-08-25"  # the clock is left as it was
    for environment in flags.ENVIRONMENTS:
        monkeypatch.setenv(flags.ENV_ENVIRONMENT, environment)
        assert flags.read_boolean("pyforge.three_surfaces", True, flags_path=tree) is False, environment
        assert flags.read_boolean("pyforge.steward.ghe_fleet_credentials", flags_path=tree) is False, environment
