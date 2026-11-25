"""`scripts/run_named_tests.py` -- a named test that skips fails the run (steward Story 136.6,
`spec-pyforge-steward` CAP-175).

The script is standard library only and drives pytest in a child process, so this module runs in
`pixi run -e pyforge-ci pyforge-doctor-scripts-test` like the rest of `tests/scripts`.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_named_tests.py"

_PLANTED = """\
import pytest


def test_passes():
    assert True


def test_skips():
    pytest.skip("planted skip reason")


def test_skips_for_an_import():
    pytest.importorskip("planted_module_that_does_not_exist")


def test_fails():
    assert False
"""


@pytest.fixture(scope="module")
def runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_named_tests_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def planted(tmp_path: Path) -> Path:
    path = tmp_path / "test_planted.py"
    path.write_text(_PLANTED, encoding="utf-8")
    return path


def _run(planted: Path, *tests: str) -> subprocess.CompletedProcess[str]:
    node_ids = [f"{planted}::{test}" for test in tests]
    return subprocess.run(
        [sys.executable, str(SCRIPT), *node_ids], cwd=planted.parent, capture_output=True, text=True, check=False
    )


def test_every_named_test_passing_exits_zero(planted: Path) -> None:
    done = _run(planted, "test_passes")
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize("skipping", ["test_skips", "test_skips_for_an_import"])
def test_a_named_test_that_skips_fails_the_run_and_is_named(planted: Path, skipping: str) -> None:
    done = _run(planted, "test_passes", skipping)
    assert done.returncode == 1, done.stdout + done.stderr
    assert f"{skipping}: " in done.stderr and "a skip fails this run" in done.stderr


def test_a_failing_test_keeps_pytests_exit_code(planted: Path) -> None:
    done = _run(planted, "test_passes", "test_fails")
    assert done.returncode == 1, done.stdout + done.stderr
    assert "pytest exited 1" in done.stderr


def test_a_node_id_that_no_longer_exists_fails_the_run(planted: Path) -> None:
    done = _run(planted, "test_passes", "test_renamed_away")
    assert done.returncode == 4, done.stdout + done.stderr


@pytest.mark.parametrize("argv", [[], ["-k", "anything"]], ids=("no-node-id", "an-option"))
def test_no_node_id_or_an_option_is_a_usage_error(runner: ModuleType, argv: list[str]) -> None:
    assert runner.main(argv) == runner.USAGE_EXIT


def test_fewer_tests_than_node_ids_fails(runner: ModuleType) -> None:
    code, problems = runner.verdict(["a::one", "a::two"], 0, 1, [])
    assert code == 1 and problems == ["2 node ids were named and 1 tests ran"]


def test_the_report_reader_counts_cases_and_names_each_skip(runner: ModuleType, tmp_path: Path) -> None:
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuites><testsuite><testcase classname="m" name="test_a"/>'
        '<testcase classname="m" name="test_b"><skipped message="why"/></testcase></testsuite></testsuites>',
        encoding="utf-8",
    )
    assert runner.skipped_cases(report) == (2, ["m::test_b: why"])
