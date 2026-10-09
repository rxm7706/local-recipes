"""Suite-lane reduction when coverage gate overlaps (Story 71.4, CAP-159)."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyforge.steward import preflight, preflight_suite_reduction as psr

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


def _fixture_station_no_slow(repo: Path, name: str = "noslow") -> Path:
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
            def test_fast_{suite}():
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
    assert task_ids
    assert gate_ids
    assert reduced_ids
    assert gate_ids.isdisjoint(reduced_ids)
    assert gate_ids | reduced_ids == task_ids


def _run_reduced_lane_via_preflight(
    repo: Path,
    *,
    station: str,
    env: str,
    override: psr.SuiteLaneOverride,
    task: str,
    task_cmd: str | None = None,
) -> tuple[int, dict]:
    coord = preflight._RunCoordinator(
        repo_root=repo,
        run_id="test",
        run_start=0.0,
        jobs=1,
        keep_going=False,
    )
    lane_dir = repo / "scratch" / task
    log_path = repo / "scratch" / f"{task}.log"
    ctx = preflight.LaneRunContext(
        lane=preflight.Lane(task=task, environment=env),
        scratch_dir=lane_dir,
        log_path=log_path,
        env=os.environ.copy(),
    )

    resolved_task_cmd = task_cmd or ""

    def _direct_pixi_argv(_coord, _ctx, argv, log_handle):
        if argv[-1] == "--collect-only":
            assert resolved_task_cmd
            parsed = psr._parse_single_pytest(resolved_task_cmd)
            assert parsed
            rel = [str(Path(p).resolve().relative_to(repo)) if not Path(p).is_absolute() else str(p) for p in parsed.test_paths]
            seg = [sys.executable, "-m", "pytest", "--collect-only", "-q", *rel, *parsed.suffix]
            if parsed.marker_expr:
                seg.extend(["-m", parsed.marker_expr])
        else:
            dash = argv.index("--")
            seg = [sys.executable, "-m", *argv[dash + 1 :]]
        proc = subprocess.run(
            seg,
            cwd=repo,
            env=_ctx.env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )
        return int(proc.returncode)

    with patch.object(preflight, "_run_pixi_argv", side_effect=_direct_pixi_argv):
        code = preflight._subprocess_reduced_suite_lane(coord, ctx, override)
    extra = coord.suite_reduction_runtime_journal[task]
    return code, extra


def test_empty_gate_directory_segment_passes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    station_pkg = _fixture_station_no_slow(repo, "heraldish")
    tests = station_pkg / "tests"
    parsed = psr._parse_single_pytest(f"pytest {tests} -q")
    assert parsed is not None
    gate_run = _gate_unit_run(repo, station_pkg) | {"station": "heraldish"}
    segments = psr._build_reduced_segments(parsed, repo, gate_run)
    assert segments is not None
    override = psr.SuiteLaneOverride(
        segments=tuple(segments),
        journal={"suite_reduction": True},
    )
    code, journal = _run_reduced_lane_via_preflight(
        repo,
        station="heraldish",
        env="pyforge-heraldish",
        override=override,
        task="pyforge-heraldish-test",
    )
    assert code == 0
    rows = {row["label"]: row for row in journal["suite_reduction_segments"]}
    assert rows["rest-of-task"]["outcome"] == "passed"
    assert rows["gate-dirs-complement"]["outcome"] == "no-tests-selected"
    assert rows["gate-dirs-complement"]["exit_code"] == psr.PYTEST_EXIT_NO_TESTS_COLLECTED


def test_failing_segment_still_reds_lane(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    station_pkg = _fixture_station_no_slow(repo, "fail")
    tests = station_pkg / "tests"
    _write(
        tests / "integration" / "test_fail.py",
        """
        def test_will_fail():
            assert False
        """,
    )
    parsed = psr._parse_single_pytest(f"pytest {tests} -q")
    gate_run = _gate_unit_run(repo, station_pkg) | {"station": "fail"}
    segments = psr._build_reduced_segments(parsed, repo, gate_run)
    assert segments
    override = psr.SuiteLaneOverride(segments=tuple(segments), journal={"suite_reduction": True})
    code, journal = _run_reduced_lane_via_preflight(
        repo,
        station="fail",
        env="pyforge-fail",
        override=override,
        task="pyforge-fail-test",
    )
    assert code == 1
    rows = {row["label"]: row for row in journal["suite_reduction_segments"]}
    assert rows["rest-of-task"]["outcome"] == "failed"
    assert rows["gate-dirs-complement"]["outcome"] == "not-run"


def test_doctor_shape_single_complement_no_tests_selected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    station_pkg = _fixture_station_no_slow(repo, "doctorish")
    tests = station_pkg / "tests"
    shutil.rmtree(tests / "integration")
    parsed = psr._parse_single_pytest(f"pytest {tests} -q")
    gate_run = _gate_unit_run(repo, station_pkg) | {"station": "doctorish"}
    gate_run["test_paths"] = [
        str((tests / "unit").relative_to(repo)),
        str((tests / "meta").relative_to(repo)),
    ]
    segments = psr._build_reduced_segments(parsed, repo, gate_run)
    assert segments and len(segments) == 1
    assert segments[0].label == "gate-dirs-complement"
    override = psr.SuiteLaneOverride(segments=tuple(segments), journal={"suite_reduction": True})
    code, journal = _run_reduced_lane_via_preflight(
        repo,
        station="doctorish",
        env="pyforge-doctorish",
        override=override,
        task="pyforge-doctorish-test",
    )
    assert code == 0
    assert journal["suite_reduction_task_collect_exit"] == 0
    assert journal["suite_reduction_segments"][0]["outcome"] == "no-tests-selected"


def test_all_segments_no_tests_and_task_collects_nothing_reds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    station_pkg = _fixture_station_no_slow(repo, "empty")
    tests = station_pkg / "tests"
    task_cmd = f'pytest {tests} -q -m "never_pick_abcdef"'
    parsed = psr._parse_single_pytest(task_cmd)
    assert parsed
    gate_run = _gate_unit_run(repo, station_pkg) | {"station": "empty"}
    segments = psr._build_reduced_segments(parsed, repo, gate_run)
    assert segments
    override = psr.SuiteLaneOverride(segments=tuple(segments), journal={"suite_reduction": True})
    code, journal = _run_reduced_lane_via_preflight(
        repo,
        station="empty",
        env="pyforge-empty",
        override=override,
        task="pyforge-empty-test",
        task_cmd=task_cmd,
    )
    assert code == psr.PYTEST_EXIT_NO_TESTS_COLLECTED
    assert all(row["outcome"] == "no-tests-selected" for row in journal["suite_reduction_segments"])
    assert journal["suite_reduction_task_collect_exit"] == psr.PYTEST_EXIT_NO_TESTS_COLLECTED


def test_equal_marker_omits_gate_complement_segment(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    station_pkg = _fixture_station(repo, "equal")
    tests = station_pkg / "tests"
    task_cmd = f'pytest {tests} -q -m "not slow"'
    parsed = psr._parse_single_pytest(task_cmd)
    assert parsed
    gate_run = _gate_unit_run(repo, station_pkg) | {"station": "equal"}
    segments = psr._build_reduced_segments(parsed, repo, gate_run)
    assert segments
    assert all(seg.label != "gate-dirs-complement" for seg in segments)
    reduced_shell = psr._build_reduced_shell_cmd(parsed, repo, gate_run)
    assert reduced_shell
    task_ids = psr.collect_pytest_node_ids(repo, task_cmd)
    gate_ids = psr.collect_pytest_node_ids(repo, psr.gate_collect_shell(repo, gate_run))
    reduced_ids = psr.collect_pytest_node_ids(repo, reduced_shell)
    assert task_ids and gate_ids and reduced_ids
    slow_unit = f"{tests / 'unit' / 'test_unit_sample.py'}::test_slow_unit"
    assert slow_unit not in task_ids
    assert slow_unit not in gate_ids
    assert slow_unit not in reduced_ids
    assert gate_ids.isdisjoint(reduced_ids)
    assert gate_ids | reduced_ids == task_ids


def test_collect_pytest_node_ids_exit_five_is_empty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    station_pkg = _fixture_station_no_slow(repo, "coll")
    tests = station_pkg / "tests"
    cmd = f"pytest {tests / 'unit'} {tests / 'meta'} -q -m slow"
    assert psr.collect_pytest_node_ids(repo, cmd) == set()


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
    assert psr._complement_marker("not slow", "not slow") is None
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
