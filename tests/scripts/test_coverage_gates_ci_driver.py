"""Driver-level contracts for scripts/coverage_gates_ci.py (Story 19.3).

Moved from pyforge-marshal's own test suite 2026-09-20 (doctor Story 24.1,
spec-coverage-gate-independence CAP-1): the driver's own coverage_gate.py
import moved to a scripts/ sibling, outside every pyforge.<station> package.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
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


def test_normalize_base_keeps_revisions_and_names_the_remote_tracking_ref(driver):
    """A bare sha (the push workflow's `git rev-parse HEAD~1`) is a revision
    already; a bare branch name (GITHUB_BASE_REF) and `origin/<name>` (the
    pixi tasks) become `refs/remotes/origin/<name>` -- doctor Story 32.1
    (spec-coverage-gate-independence CAP-4): never the short name a local ref
    can wear."""
    sha = "f619eae05a233024bf43cc6b68d717fcfffefbaa"
    assert driver._normalize_base(sha) == sha
    assert driver._normalize_base(sha[:10]) == sha[:10]
    assert driver._normalize_base("main") == "refs/remotes/origin/main"
    assert driver._normalize_base("origin/main") == "refs/remotes/origin/main"
    assert driver._normalize_base("origin/release/2026") == "refs/remotes/origin/release/2026"
    assert driver._normalize_base("refs/remotes/origin/main") == "refs/remotes/origin/main"
    assert driver._normalize_base("origin/main~1") == "refs/remotes/origin/main~1"
    assert driver._normalize_base("origin/main@{1}") == "refs/remotes/origin/main@{1}"
    assert driver._normalize_base("user@feature") == "refs/remotes/origin/user@feature"
    assert driver._normalize_base("HEAD~1") == "HEAD~1"
    assert driver._normalize_base("HEAD^") == "HEAD^"
    assert driver._normalize_base("@{u}") == "@{u}"
    assert driver._normalize_base("upstream/main") == "upstream/main"
    assert driver._normalize_base("") == ""


@pytest.mark.parametrize("kind", ["branch", "tag"])
@pytest.mark.parametrize("given", ["origin/main", "main", "origin/main~0"])
def test_a_local_origin_main_at_head_no_longer_empties_the_touched_list(driver, tmp_path, monkeypatch, kind, given):
    """The trap CAP-4 closes: a local branch or tag `origin/main` at HEAD made `origin/main...HEAD` empty, so the
    gate judged no module. The normalized base reads the remote-tracking ref instead."""
    import subprocess

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()

    git("init", "-q", "--initial-branch=main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "T")
    git("commit", "-q", "--allow-empty", "-m", "base")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    (tmp_path / "touched.py").write_text("x = 1\n", encoding="utf-8")
    git("add", "touched.py")
    git("commit", "-q", "-m", "touch a module")
    git(kind, "origin/main", "HEAD")  # the shadow
    monkeypatch.setattr(driver, "REPO", tmp_path)

    assert driver._git_diff_names("origin/main", "HEAD") == []  # the trap, for the record
    assert driver._git_diff_names(driver._normalize_base(given), "HEAD") == ["touched.py"]


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
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py\n",
        encoding="utf-8",
    )
    report_payload = {
        "files": {
            "src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py": {
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


def test_plan_prints_json_without_pytest(driver, tmp_path: Path, monkeypatch, capsys):
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text(
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py\n",
        encoding="utf-8",
    )
    ran = []

    def fake_run(*, station, suite, report):
        ran.append((station, suite))
        return "ran", 0

    monkeypatch.setattr(driver, "_run_pytest_cov", fake_run)
    monkeypatch.setenv("COVERAGE_GATES_STATIONS", "marshal")

    rc = driver.main(["--plan", "--paths-file", str(paths_file), "--suites", "unit"])
    assert rc == 0
    assert ran == []
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["touched_stations"] == ["marshal"]
    assert len(payload["runs"]) == 1
    run = payload["runs"][0]
    assert run["station"] == "marshal"
    assert run["suite"] == "unit"
    assert run["marker_expr"] == "not slow"
    assert any("tests/unit" in p for p in run["test_paths"])
    assert any("tests/meta" in p for p in run["test_paths"])


def test_plan_stdout_stays_json_when_format_only_paths_skipped(driver, monkeypatch, capsys):
    """format-only diagnostics must not precede JSON (Story 71.4 preflight parses stdout)."""

    def fake_drop(paths, base, head, *, quiet=False):
        assert quiet is True
        return paths

    monkeypatch.setattr(driver, "_drop_format_only", fake_drop)
    rc = driver.main(["--plan", "--paths-file", "/dev/null", "--suites", "unit"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    json.loads(out)


def test_run_pytest_cov_carries_station_test_task_xdist_flags(driver, monkeypatch):
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        class _Proc:
            returncode = 0

        return _Proc()

    monkeypatch.setattr("subprocess.run", fake_run)
    root = REPO / "src" / "shared" / "packages" / "pyforge-marshal"
    report = REPO / ".coverage-report-marshal-unit.json"
    try:
        driver._run_pytest_cov(station="marshal", suite="unit", report=report)
    finally:
        report.unlink(missing_ok=True)
    assert captured
    cmd = captured[0]
    assert "-n" in cmd and "auto" in cmd
    assert "--dist" in cmd and "loadgroup" in cmd


def test_plan_empty_when_no_station_touched(driver, tmp_path: Path, capsys):
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("pixi.toml\n", encoding="utf-8")
    rc = driver.main(["--plan", "--paths-file", str(paths_file), "--suites", "unit"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["runs"] == []
