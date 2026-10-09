"""Suite-lane reduction when coverage gate overlaps (Story 71.4, CAP-159)."""

from __future__ import annotations

import copy
import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

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
                        "cmd": "pytest a/tests -q && pytest b/tests -q",
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


def test_complement_marker_variants() -> None:
    assert psr._complement_marker("not slow", "not slow") == "slow"
    assert psr._complement_marker("unit", "not slow") == "(unit) and not (not slow)"
    assert psr._complement_marker(None, "not slow") == "slow"


def test_task_helpers_from_pixi() -> None:
    pixi = {
        "feature": {
            "x": {
                "tasks": {
                    "t1": {"cmd": "echo hi", "env": {"A": "1"}},
                    "t2": {"cmd": 42},
                }
            }
        }
    }
    assert psr._task_cmd(pixi, "missing") is None
    assert psr._task_cmd(pixi, "t1") == "echo hi"
    assert psr._task_cmd(pixi, "t2") is None
    assert psr._task_env(pixi, "t1") == {"A": "1"}
    assert psr._task_env(pixi, "missing") == {}
    assert psr._find_task(pixi, "t1") == {"cmd": "echo hi", "env": {"A": "1"}}


def test_parse_single_pytest_flags_and_edge_cases() -> None:
    assert psr._parse_single_pytest("uv run pytest") is None
    assert psr._parse_single_pytest("pytest") is None
    parsed = psr._parse_single_pytest("pytest pkg/tests -q --maxfail 1 -n auto --dist load")
    assert parsed is not None
    assert parsed.marker_expr is None
    assert "pkg/tests" in parsed.test_paths
    assert "--maxfail" in parsed.suffix


def test_scripts_scan_and_import_detection(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "__init__.py").write_text("", encoding="utf-8")
    (scripts / "helper.py").write_text("x = 1\n", encoding="utf-8")
    assert psr._scripts_top_level_modules(repo) == {"helper"}
    assert psr._scripts_top_level_modules(tmp_path / "empty") == set()

    bad = repo / "bad.py"
    bad.write_text("syntax !!!\n", encoding="utf-8")
    assert psr._imports_scripts_module(bad, {"helper"}) is None

    good = repo / "good.py"
    good.write_text("import helper\nfrom helper import x\n", encoding="utf-8")
    hit = psr._imports_scripts_module(good, {"helper"})
    assert hit and "import helper" in hit

    rel = repo / "rel.py"
    rel.write_text("from . import sibling\n", encoding="utf-8")
    rel_hit = psr._imports_scripts_module(rel, set())
    assert rel_hit and "relative import" in rel_hit

    _fixture_station(repo, "scan")
    assert psr._scan_unit_meta_scripts_imports(repo, "scan") is None


def test_discover_test_subdirs_and_gate_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    station = _fixture_station(repo, "disc")
    tests = station / "tests"
    integration = tests / "integration"
    _write(
        integration / "test_only_here.py",
        """
        def test_integration_only():
            assert True
        """,
    )
    parsed = psr._parse_single_pytest(f"pytest {tests} -q")
    assert parsed is not None
    subdirs = psr._discover_test_subdirs(repo, parsed.test_paths)
    names = {p.name for p in subdirs}
    assert "unit" in names
    assert "meta" in names
    assert "integration" in names

    gate_run = {"test_paths": [str(tests / "unit"), "not-a-path", 42], "marker_expr": "not slow"}
    resolved = psr._gate_paths_resolved(repo, gate_run)
    assert len(resolved) == 1


def test_gate_driver_argv_and_unit_run() -> None:
    cmd = "python scripts/coverage_gates_ci.py --base main --head HEAD --suites unit"
    assert psr._gate_driver_argv(cmd) == [
        "python",
        "scripts/coverage_gates_ci.py",
        "--plan",
        "--base",
        "main",
        "--head",
        "HEAD",
        "--suites",
        "unit",
    ]
    alt = "uv run python /abs/coverage_gates_ci.py --suites unit"
    assert psr._gate_driver_argv(alt) is not None
    assert psr._unit_run_for_station({"runs": "nope"}, "x") is None
    plan = {"runs": [{"station": "s", "suite": "unit", "test_paths": []}]}
    assert psr._unit_run_for_station(plan, "s") == plan["runs"][0]


def test_read_gate_plan_subprocess(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    pixi = {
        "feature": {
            "pyforge-steward": {
                "tasks": {
                    "pyforge-steward-coverage-gate": {
                        "cmd": "python scripts/coverage_gates_ci.py --suites unit",
                        "env": {"X": "y"},
                    }
                }
            }
        }
    }
    payload = {"runs": []}
    ok = MagicMock(returncode=0, stdout=json.dumps(payload), stderr="")
    with patch("pyforge.steward.preflight_suite_reduction.subprocess.run", return_value=ok):
        assert psr._read_gate_plan(repo, "pyforge-steward-coverage-gate", pixi) == payload
    bad = MagicMock(returncode=1, stdout="", stderr="fail")
    with patch("pyforge.steward.preflight_suite_reduction.subprocess.run", return_value=bad):
        assert psr._read_gate_plan(repo, "pyforge-steward-coverage-gate", pixi) is None


def test_derive_suite_lane_override_happy_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    station_pkg = _fixture_station(repo, "happy")
    tests = station_pkg / "tests"
    gate_plan = {"runs": [_gate_unit_run(repo, station_pkg) | {"station": "happy"}]}
    pixi = {
        "feature": {
            "pyforge-happy": {
                "tasks": {
                    "pyforge-happy-test": {"cmd": f"pytest {tests} -q -m 'not slow'"},
                }
            }
        }
    }
    override = psr.derive_suite_lane_override(repo, station="happy", pixi_data=pixi, gate_plan=gate_plan)
    assert isinstance(override, psr.SuiteLaneOverride)
    assert override.journal["suite_reduction"] is True


def test_build_suite_lane_overrides_branches(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    station_pkg = _fixture_station(repo, "lane")
    tests = station_pkg / "tests"
    gate_plan = {"runs": [_gate_unit_run(repo, station_pkg) | {"station": "lane"}]}
    pixi = {
        "feature": {
            "pyforge-lane": {
                "tasks": {
                    "pyforge-lane-test": {"cmd": f"pytest {tests} -q -m 'not slow'"},
                    "pyforge-lane-coverage-gate": {
                        "cmd": "python scripts/coverage_gates_ci.py --suites unit",
                    },
                }
            }
        }
    }
    assert psr.build_suite_lane_overrides(repo, selected_task_names=set(), pixi_data=pixi) == {}

    only_test = psr.build_suite_lane_overrides(
        repo,
        selected_task_names={"pyforge-lane-test"},
        pixi_data=pixi,
    )
    assert "pyforge-lane-test" not in only_test

    skip = psr.build_suite_lane_overrides(
        repo,
        selected_task_names={"pyforge-lane-test", "pyforge-other-coverage-gate"},
        pixi_data=pixi,
    )
    assert skip["pyforge-lane-test"]["suite_reduction_reason"] == "coverage gate lane not selected"

    missing_gate = copy.deepcopy(pixi)
    missing_gate["feature"]["pyforge-lane"]["tasks"].pop("pyforge-lane-coverage-gate")
    journal = psr.build_suite_lane_overrides(
        repo,
        selected_task_names={"pyforge-lane-test", "pyforge-lane-coverage-gate"},
        pixi_data=missing_gate,
    )
    assert "missing coverage gate" in journal["pyforge-lane-test"]["suite_reduction_reason"]

    with patch(
        "pyforge.steward.preflight_suite_reduction._read_gate_plan",
        return_value=None,
    ):
        unparsable = psr.build_suite_lane_overrides(
            repo,
            selected_task_names={"pyforge-lane-test", "pyforge-lane-coverage-gate"},
            pixi_data=pixi,
        )
    assert "unparsable" in unparsable["pyforge-lane-test"]["suite_reduction_reason"]

    with patch(
        "pyforge.steward.preflight_suite_reduction._read_gate_plan",
        return_value=gate_plan,
    ):
        reduced = psr.build_suite_lane_overrides(
            repo,
            selected_task_names={"pyforge-lane-test", "pyforge-lane-coverage-gate"},
            pixi_data=pixi,
        )
    assert isinstance(reduced["pyforge-lane-test"], psr.SuiteLaneOverride)

    no_overlap_pixi = {
        "feature": {
            "pyforge-lane": {
                "tasks": {
                    "pyforge-lane-test": {"cmd": "echo not pytest"},
                    "pyforge-lane-coverage-gate": pixi["feature"]["pyforge-lane"]["tasks"][
                        "pyforge-lane-coverage-gate"
                    ],
                }
            }
        }
    }
    with patch(
        "pyforge.steward.preflight_suite_reduction._read_gate_plan",
        return_value={"runs": [{"station": "lane", "suite": "integration", "test_paths": []}]},
    ):
        no_unit = psr.build_suite_lane_overrides(
            repo,
            selected_task_names={"pyforge-lane-test", "pyforge-lane-coverage-gate"},
            pixi_data=pixi,
        )
        non_pytest = psr.build_suite_lane_overrides(
            repo,
            selected_task_names={"pyforge-lane-test", "pyforge-lane-coverage-gate"},
            pixi_data=no_overlap_pixi,
        )
    assert "no reducible overlap" in no_unit["pyforge-lane-test"]["suite_reduction_reason"]
    assert "not a single pytest invocation" in non_pytest["pyforge-lane-test"]["suite_reduction_reason"]


def test_reduction_skip_journal_and_gate_collect_shell(tmp_path: Path) -> None:
    journal = psr.reduction_skip_journal("reason", extra=1)
    assert journal["suite_reduction"] is False
    assert journal["extra"] == 1
    shell = psr.gate_collect_shell(tmp_path, {"test_paths": ["a/b"], "marker_expr": "slow"})
    assert "pytest" in shell and "slow" in shell


def test_collect_pytest_node_ids_raises_on_failure(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        psr.collect_pytest_node_ids(tmp_path, "pytest definitely-not-a-real-path-xyz -q")
