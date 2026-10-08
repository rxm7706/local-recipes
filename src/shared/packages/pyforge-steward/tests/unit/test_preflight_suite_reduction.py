"""Suite-lane reduction when coverage gate overlaps (Story 71.4, CAP-159)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from pyforge.steward import preflight_suite_reduction as psr

REPO_ROOT = Path(__file__).resolve().parents[6]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def _fixture_station(repo: Path, name: str = "alphatest") -> Path:
    pkg = repo / "src" / "shared" / "packages" / f"pyforge-{name}"
    tests = pkg / "tests"
    _write(
        tests / "conftest.py",
        """
        import pytest

        def pytest_configure(config):
            config.addinivalue_line("markers", "slow: slow test")
        """,
    )
    for suite in ("unit", "meta", "integration"):
        _write(
            tests / suite / f"test_{suite}_sample.py",
            f"""
            import pytest

            def test_fast_{suite}():
                assert True

            @pytest.mark.slow
            def test_slow_{suite}():
                assert True
            """,
        )
    return pkg


def _gate_unit_run(repo: Path, station_pkg: Path) -> dict:
    unit = station_pkg / "tests" / "unit"
    meta = station_pkg / "tests" / "meta"
    return {
        "station": "alphatest",
        "suite": "unit",
        "test_paths": [
            str(unit.relative_to(repo)),
            str(meta.relative_to(repo)),
        ],
        "marker_expr": "not slow",
    }


@pytest.mark.parametrize("task_cmd", ['pytest {tests} -q -m "not slow"', "pytest {tests} -q"])
def test_reduced_and_gate_collections_partition_task(tmp_path: Path, task_cmd: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    station_pkg = _fixture_station(repo)
    tests = station_pkg / "tests"
    parsed = psr._parse_single_pytest(task_cmd.format(tests=tests))
    assert parsed is not None
    gate_run = _gate_unit_run(repo, station_pkg)
    reduced_shell = psr._build_reduced_shell_cmd(parsed, repo, gate_run)
    assert reduced_shell
    task_ids = psr.collect_pytest_node_ids(repo, task_cmd.format(tests=tests))
    gate_ids = psr.collect_pytest_node_ids(repo, psr.gate_collect_shell(repo, gate_run))
    reduced_ids = psr.collect_pytest_node_ids(repo, reduced_shell)
    assert gate_ids.isdisjoint(reduced_ids)
    assert gate_ids | reduced_ids == task_ids


def test_two_pytest_task_is_not_reduced(tmp_path: Path) -> None:
    pixi = {
        "feature": {
            "pyforge-mason": {
                "tasks": {
                    "pyforge-mason-test": {
                        "cmd": 'pytest a/tests -q && pytest b/tests -q',
                    },
                    "pyforge-mason-coverage-gate": {
                        "cmd": "python scripts/coverage_gates_ci.py --base origin/main --head HEAD --suites unit",
                        "env": {"COVERAGE_GATES_STATIONS": "mason"},
                    },
                }
            }
        }
    }
    overrides = psr.build_suite_lane_overrides(
        tmp_path,
        selected_task_names={"pyforge-mason-test", "pyforge-mason-coverage-gate"},
        pixi_data=pixi,
    )
    entry = overrides.get("pyforge-mason-test")
    assert isinstance(entry, dict)
    assert entry.get("suite_reduction") is False
    assert "single pytest" in entry.get("suite_reduction_reason", "")


def test_scripts_import_blocks_reduction(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    station_pkg = _fixture_station(repo, name="marshal")
    _write(
        station_pkg / "tests" / "unit" / "test_scripts.py",
        """
        import coverage_gate

        def test_imports_scripts():
            assert True
        """,
    )
    _write(repo / "scripts" / "coverage_gate.py", "x = 1\n")
    hit = psr._scan_unit_meta_scripts_imports(repo, "marshal")
    assert hit and "coverage_gate" in hit


def test_build_suite_lane_overrides_journals_mason_two_command(tmp_path: Path) -> None:
    pixi_path = REPO_ROOT / "pixi.toml"
    if not pixi_path.is_file():
        pytest.skip("repo pixi.toml not available")
    import tomllib

    pixi_data = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    overrides = psr.build_suite_lane_overrides(
        REPO_ROOT,
        selected_task_names={"pyforge-mason-test", "pyforge-mason-coverage-gate"},
        pixi_data=pixi_data,
    )
    entry = overrides["pyforge-mason-test"]
    assert isinstance(entry, dict)
    assert entry["suite_reduction"] is False


def test_parse_single_pytest_rejects_and_accepts() -> None:
    assert psr._parse_single_pytest("pytest foo/tests -q -m slow") is not None
    assert psr._parse_single_pytest("echo && pytest foo") is None
