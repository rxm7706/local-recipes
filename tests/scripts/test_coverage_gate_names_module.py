"""Story 19.3 / FR-131 — coverage gates that *name* the uncovered module.

Fixtures prove a below-threshold run fails naming modules, not only an
aggregate percentage. Live threshold defaults and touched-station discovery
are locked here too.

Moved from pyforge-marshal's own test suite 2026-09-20 (doctor Story 24.1,
spec-coverage-gate-independence CAP-1): the module under test moved to
scripts/coverage_gate.py, outside every pyforge.<station> package, so this
suite moved with it rather than importing a package that no longer ships it.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COVERAGE_GATE_PATH = REPO_ROOT / "scripts" / "coverage_gate.py"


def _load_coverage_gate():
    spec = importlib.util.spec_from_file_location("coverage_gate_names_module_test", COVERAGE_GATE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_coverage_gate = _load_coverage_gate()
DEFAULT_INTEGRATION_THRESHOLD = _coverage_gate.DEFAULT_INTEGRATION_THRESHOLD
DEFAULT_UNIT_THRESHOLD = _coverage_gate.DEFAULT_UNIT_THRESHOLD
STATIONS = _coverage_gate.STATIONS
ModuleFailure = _coverage_gate.ModuleFailure
evaluate_coverage_payload = _coverage_gate.evaluate_coverage_payload
evaluate_suite = _coverage_gate.evaluate_suite
filter_percents = _coverage_gate.filter_percents
format_failure_message = _coverage_gate.format_failure_message
load_thresholds = _coverage_gate.load_thresholds
main = _coverage_gate.main
module_percents_from_coverage_json = _coverage_gate.module_percents_from_coverage_json
modules_below_threshold = _coverage_gate.modules_below_threshold
package_root = _coverage_gate.package_root
package_src = _coverage_gate.package_src
thresholds_for = _coverage_gate.thresholds_for
touched_source_modules = _coverage_gate.touched_source_modules
touched_stations = _coverage_gate.touched_stations


def test_fleet_defaults_are_unit_80_integration_70():
    assert DEFAULT_UNIT_THRESHOLD == 80.0
    assert DEFAULT_INTEGRATION_THRESHOLD == 70.0
    thr = thresholds_for("marshal")
    assert thr.unit == 80.0
    assert thr.integration == 70.0


def test_packaged_thresholds_cover_all_eight_stations():
    table = load_thresholds()
    for slug in STATIONS:
        assert slug in table
        assert table[slug].unit == 80.0
        assert table[slug].integration == 70.0


def test_station_override_from_thresholds_toml(tmp_path: Path):
    path = tmp_path / "thresholds.toml"
    path.write_text(
        "\n".join(
            [
                "[defaults]",
                "unit = 80.0",
                "integration = 70.0",
                "",
                "[stations.scribe]",
                "unit = 60.0",
                "integration = 50.0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    scribe = thresholds_for("scribe", path=path)
    marshal = thresholds_for("marshal", path=path)
    assert scribe.unit == 60.0 and scribe.integration == 50.0
    assert marshal.unit == 80.0 and marshal.integration == 70.0


def test_named_module_failure_message_lists_modules_not_only_percent():
    """FR-131: failure output names uncovered modules (not bare %)."""
    failures = [
        ModuleFailure(
            module="pyforge.marshal.cli.spin",
            percent=42.0,
            threshold=80.0,
            suite="unit",
        ),
        ModuleFailure(
            module="pyforge.marshal.core.policy",
            percent=71.5,
            threshold=80.0,
            suite="unit",
        ),
    ]
    msg = format_failure_message(
        failures,
        station="marshal",
        suite="unit",
        threshold=80.0,
        percents={
            "pyforge.marshal.cli.spin": 42.0,
            "pyforge.marshal.core.policy": 71.5,
            "pyforge.marshal.core.gate": 95.0,
        },
    )
    assert "pyforge.marshal.cli.spin" in msg
    assert "pyforge.marshal.core.policy" in msg
    assert "under-threshold modules:" in msg
    assert "42.0%" in msg
    assert "threshold 80% unit" in msg


def test_evaluate_suite_fails_naming_module_below_unit_threshold():
    ok, msg = evaluate_suite(
        {
            "pyforge.marshal.cli.spin": 50.0,
            "pyforge.marshal.core.gate": 99.0,
        },
        suite="unit",
        threshold=80.0,
        station="marshal",
    )
    assert ok is False
    assert "pyforge.marshal.cli.spin" in msg
    named_block = msg.split("under-threshold modules:")[1]
    assert "pyforge.marshal.cli.spin" in named_block
    assert "pyforge.marshal.core.gate" not in named_block
    assert "FAILED" in msg


def test_evaluate_suite_passes_when_all_modules_meet_floor():
    ok, msg = evaluate_suite(
        {
            "pyforge.marshal.cli.spin": 80.0,
            "pyforge.marshal.core.gate": 90.0,
        },
        suite="unit",
        threshold=80.0,
        station="marshal",
    )
    assert ok is True
    assert "OK" in msg


def test_integration_threshold_is_70():
    failures = modules_below_threshold(
        {"pkg.a": 69.9, "pkg.b": 70.0},
        70.0,
        suite="integration",
    )
    assert [f.module for f in failures] == ["pkg.a"]


def test_coverage_json_files_shape_is_accepted():
    payload = {
        "files": {
            "/repo/src/pyforge/marshal/cli/spin.py": {"summary": {"percent_covered": 55.0}},
            "/repo/src/pyforge/marshal/core/gate.py": {"summary": {"percent_covered": 88.0}},
        }
    }
    percents = module_percents_from_coverage_json(payload)
    assert percents["pyforge.marshal.cli.spin"] == 55.0
    assert percents["pyforge.marshal.core.gate"] == 88.0


def test_evaluate_coverage_payload_fixture_json():
    payload = {
        "pyforge.marshal.cli.spin": 40.0,
        "pyforge.marshal.core.gate": 95.0,
    }
    ok, msg = evaluate_coverage_payload(payload, station="marshal", suite="unit")
    assert ok is False
    assert "pyforge.marshal.cli.spin" in msg


def test_touched_stations_from_package_paths():
    paths = [
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_gate.py",
        "src/shared/packages/pyforge-warden/tests/unit/test_report.py",
        "docs/dreams/pyforge-marshal.md",
        "src/shared/packages/pyforge-core/src/pyforge/core/atomic.py",
    ]
    assert touched_stations(paths) == frozenset({"marshal", "warden"})


def test_touched_source_modules_maps_paths_to_dotted_names():
    paths = [
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_gate.py",
        "src/shared/packages/pyforge-marshal/tests/meta/test_coverage_gate_names_module.py",
        "src/shared/packages/pyforge-warden/src/pyforge/warden/report.py",
    ]
    assert touched_source_modules(paths) == frozenset(
        {
            "pyforge.marshal.coverage_gate",
            "pyforge.warden.report",
        }
    )


def test_evaluate_only_modules_skips_unmeasured_touched_modules():
    """Touched modules absent from this suite's report are N/A (not zero-filled)."""
    ok, msg = evaluate_coverage_payload(
        {"pyforge.marshal.core.gate": 99.0},
        station="marshal",
        suite="unit",
        only_modules=["pyforge.marshal.coverage_gate"],
    )
    assert ok is True
    assert "OK" in msg


def test_evaluate_only_modules_empty_is_ok():
    ok, msg = evaluate_coverage_payload(
        {"pyforge.marshal.cli.spin": 10.0},
        station="marshal",
        suite="unit",
        only_modules=[],
    )
    assert ok is True
    assert "OK" in msg


def test_cli_evaluate_names_module_and_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    report = tmp_path / "cov.json"
    report.write_text(
        json.dumps({"pyforge.marshal.cli.spin": 10.0}),
        encoding="utf-8",
    )
    rc = main(
        [
            "evaluate",
            "--station",
            "marshal",
            "--suite",
            "unit",
            "--coverage-json",
            str(report),
        ]
    )
    assert rc == 1
    out = capsys.readouterr().out
    assert "pyforge.marshal.cli.spin" in out
    assert "FAILED" in out


def test_cli_evaluate_ok_when_above_threshold(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    report = tmp_path / "cov.json"
    report.write_text(
        json.dumps({"pyforge.marshal.cli.spin": 85.0}),
        encoding="utf-8",
    )
    rc = main(
        [
            "evaluate",
            "--station",
            "marshal",
            "--suite",
            "unit",
            "--coverage-json",
            str(report),
        ]
    )
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cli_evaluate_with_only_modules_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    report = tmp_path / "cov.json"
    report.write_text(
        json.dumps(
            {
                "pyforge.marshal.coverage_gate": 90.0,
                "pyforge.marshal.cli.spin": 10.0,
            }
        ),
        encoding="utf-8",
    )
    modules = tmp_path / "mods.txt"
    modules.write_text("pyforge.marshal.coverage_gate\n", encoding="utf-8")
    rc = main(
        [
            "evaluate",
            "--station",
            "marshal",
            "--suite",
            "unit",
            "--coverage-json",
            str(report),
            "--only-modules-file",
            str(modules),
        ]
    )
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cli_touched_json(capsys: pytest.CaptureFixture[str]):
    paths = "src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py\nREADME.md\n"
    old = sys.stdin
    try:
        sys.stdin = io.StringIO(paths)
        rc = main(["touched", "--paths-file", "-", "--json-out"])
    finally:
        sys.stdin = old
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stations"] == ["herald"]


def test_cli_touched_modules_json(capsys: pytest.CaptureFixture[str]):
    paths = "src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py\nREADME.md\n"
    old = sys.stdin
    try:
        sys.stdin = io.StringIO(paths)
        rc = main(["touched", "--paths-file", "-", "--json-out", "--modules"])
    finally:
        sys.stdin = old
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stations"] == ["herald"]
    assert payload["modules"] == ["pyforge.herald.cli"]


def test_cli_touched_modules_plain_list(capsys: pytest.CaptureFixture[str]):
    paths = "src/shared/packages/pyforge-warden/src/pyforge/warden/report.py\n"
    old = sys.stdin
    try:
        sys.stdin = io.StringIO(paths)
        rc = main(["touched", "--paths-file", "-", "--modules"])
    finally:
        sys.stdin = old
    assert rc == 0
    assert capsys.readouterr().out.strip() == "pyforge.warden.report"


def test_cli_show_thresholds(capsys: pytest.CaptureFixture[str]):
    rc = main(["show-thresholds"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "defaults: unit=80" in out
    assert "marshal: unit=80" in out
    assert "integration=70" in out


def test_load_thresholds_falls_back_when_file_missing(tmp_path: Path):
    missing = tmp_path / "nope.toml"
    table = load_thresholds(missing)
    assert table[""].unit == 80.0
    assert table["marshal"].integration == 70.0


def test_package_root_and_src_helpers(tmp_path: Path):
    root = package_root(tmp_path, "marshal")
    src = package_src(tmp_path, "marshal")
    assert root == tmp_path / "src" / "shared" / "packages" / "pyforge-marshal"
    assert src == root / "src" / "pyforge" / "marshal"


def test_filter_percents_keeps_exact_and_prefix():
    kept = filter_percents(
        {
            "pyforge.marshal.coverage_gate": 90.0,
            "pyforge.marshal.coverage_gate.helpers": 50.0,
            "pyforge.marshal.cli.main": 99.0,
        },
        ["pyforge.marshal.coverage_gate"],
    )
    assert set(kept) == {
        "pyforge.marshal.coverage_gate",
        "pyforge.marshal.coverage_gate.helpers",
    }


def test_thresholds_for_unknown_station_uses_defaults():
    thr = thresholds_for("not-a-real-station")
    assert thr.unit == 80.0
    assert thr.integration == 70.0


def test_module_label_from_site_packages_path():
    percents = module_percents_from_coverage_json(
        {
            "files": {
                "/env/lib/python3.14/site-packages/pyforge/marshal/cli/spin.py": {"summary": {"percent_covered": 81.0}}
            }
        }
    )
    assert percents["pyforge.marshal.cli.spin"] == 81.0
