"""Driver-level contracts for scripts/coverage_gates_ci.py (Story 19.3)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[6]
DRIVER = REPO / "scripts" / "coverage_gates_ci.py"


def _load_driver():
    spec = importlib.util.spec_from_file_location("coverage_gates_ci", DRIVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def driver():
    return _load_driver()


def test_normalize_base_keeps_revisions_and_prefixes_bare_branch_names(driver):
    """A bare sha (the push workflow's `git rev-parse HEAD~1`) is a revision
    already; only a bare branch name (GITHUB_BASE_REF) gets `origin/`."""
    sha = "f619eae05a233024bf43cc6b68d717fcfffefbaa"
    assert driver._normalize_base(sha) == sha
    assert driver._normalize_base(sha[:10]) == sha[:10]
    assert driver._normalize_base("main") == "origin/main"
    assert driver._normalize_base("origin/main") == "origin/main"
    assert driver._normalize_base("upstream/main") == "upstream/main"
    assert driver._normalize_base("") == ""


def test_suite_test_paths_skips_missing_integration(driver, tmp_path: Path):
    root = tmp_path / "pkg"
    (root / "tests" / "unit").mkdir(parents=True)
    assert driver._suite_test_paths(root, "unit") == [root / "tests" / "unit"]
    assert driver._suite_test_paths(root, "integration") == []


def test_skipped_suite_does_not_evaluate(driver, tmp_path: Path, monkeypatch, capsys):
    """N/A suites (no tests/integration) must not zero-fill touched modules."""
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text(
        "src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli.py\n",
        encoding="utf-8",
    )

    def fake_run(*, station, suite, report):
        assert suite == "integration"
        return "skipped", 0

    evaluated: list[tuple[str, str]] = []

    def fake_evaluate(*, station, suite, report, modules):
        evaluated.append((station, suite))
        return 0

    monkeypatch.setattr(driver, "_run_pytest_cov", fake_run)
    monkeypatch.setattr(driver, "_evaluate", fake_evaluate)
    monkeypatch.delenv("COVERAGE_GATES_STATIONS", raising=False)

    rc = driver.main(["--paths-file", str(paths_file), "--suites", "integration"])
    assert rc == 0
    assert evaluated == []
    out = capsys.readouterr().out
    assert "skip doctor integration" in out or "touched stations" in out


def test_pytest_failure_sets_nonzero_rc(driver, tmp_path: Path, monkeypatch):
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text(
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_gate.py\n",
        encoding="utf-8",
    )
    report_payload = {
        "files": {
            "src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_gate.py": {
                "summary": {"percent_covered": 99.0}
            }
        }
    }

    def fake_run(*, station, suite, report):
        report.write_text(json.dumps(report_payload), encoding="utf-8")
        return "ran", 1  # test failures

    monkeypatch.setattr(driver, "_run_pytest_cov", fake_run)
    monkeypatch.setenv("COVERAGE_GATES_STATIONS", "marshal")

    rc = driver.main(["--paths-file", str(paths_file), "--suites", "unit"])
    assert rc == 1


def test_allow_list_skips_foreign_station(driver, tmp_path: Path, monkeypatch, capsys):
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text(
        "src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli.py\n",
        encoding="utf-8",
    )
    called = []

    def boom(*, station, suite, report):
        called.append(station)
        return "ran", 0

    monkeypatch.setattr(driver, "_run_pytest_cov", boom)
    monkeypatch.setenv("COVERAGE_GATES_STATIONS", "marshal")

    rc = driver.main(["--paths-file", str(paths_file), "--suites", "unit"])
    assert rc == 0
    assert called == []
    assert "skipping pyforge-doctor" in capsys.readouterr().out
