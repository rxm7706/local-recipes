"""Meta-test: `verification_staleness_findings()` in fleet_picture.py.

Story 11.7 (CAP-7) wires `Source.DUE_FOR_VERIFICATION`'s new, additive
`verification-coverage` item kind (Story 11.7's own `chain._verification_
coverage`) into `fleet_picture.py`'s ATTENTION block: a small, separately-
callable, testable function -- mirroring `bmad_core_drift_findings()`'s own
extracted shape -- that shells out to `sys.executable -m pyforge.doctor.
sources due-for-verification --json` and returns only the items whose
`check == "verification-coverage"` (filtering OUT the pre-existing
`due-for-verification`/`-unevaluable`/`-cluster` item kinds Stories 11.1-11.6
already produce on that same source). `main()`'s own ATTENTION block wraps
the call in a `try/except Exception: watch.append(...)` idiom (same as every
other ATTENTION probe in that file); this function itself does NOT catch
failures -- it raises, and degrading to a "could not check" line is the
caller's job (spec Boundaries).

Same `_load_fleet_picture()` harness as
`test_fleet_picture_bmad_core_drift.py` (that file isn't a package, so it's
loaded via `importlib.util.spec_from_file_location`). `subprocess.run` is
monkeypatched rather than actually invoking `python -m pyforge.doctor.
sources` -- no real tracked-ledger fleet state is needed to exercise this
function.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_under_test", FLEET_PICTURE
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakeCompletedProcess:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.returncode = 0


def _fake_run(findings: list[dict]):
    """Build a `subprocess.run` stand-in returning `findings` as the
    `--json` stdout a real `python -m pyforge.doctor.sources
    due-for-verification --json` invocation would print."""

    def _run(cmd, **kwargs):
        assert cmd[0] == sys.executable
        assert cmd[1:4] == ["-m", "pyforge.doctor.sources", "due-for-verification"]
        assert "--json" in cmd
        return _FakeCompletedProcess(json.dumps(findings))

    return _run


def _coverage_finding(project: str, total: int, verified_within_window: int, pct: int) -> dict:
    return {
        "source": "due-for-verification",
        "check": "verification-coverage",
        "status": "warn",
        "message": f"{project}: {pct}% of {total} tracked entries verified within 30 days.",
        "evidence": {
            "project": project, "total": total,
            "verified_within_window": verified_within_window,
            "window_days": 30, "pct": pct,
        },
    }


def _due_finding(project: str) -> dict:
    return {
        "source": "due-for-verification",
        "check": "due-for-verification",
        "status": "warn",
        "message": f"{project}/DW-1: no `verified:` line — never re-checked against live code.",
        "evidence": {"reason": "never-verified", "project": project, "id": "DW-1"},
    }


def test_a_real_coverage_finding_is_parsed_and_filtered(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([_coverage_finding("doctor", 42, 16, 38)]),
    )

    result = mod.verification_staleness_findings()

    assert len(result) == 1
    assert result[0]["check"] == "verification-coverage"
    assert result[0]["evidence"]["project"] == "doctor"
    assert result[0]["evidence"]["total"] == 42
    assert result[0]["evidence"]["verified_within_window"] == 16
    assert result[0]["evidence"]["pct"] == 38


def test_multiple_projects_coverage_findings_are_all_returned(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([
            _coverage_finding("alpha", 10, 4, 40),
            _coverage_finding("beta", 5, 5, 100),
        ]),
    )

    result = mod.verification_staleness_findings()

    assert len(result) == 2
    assert {f["evidence"]["project"] for f in result} == {"alpha", "beta"}


def test_non_coverage_check_values_are_filtered_out(monkeypatch):
    """The SAME `due-for-verification` source also returns pre-existing
    per-entry `due-for-verification` items (and `-unevaluable`/`-cluster`
    ones) -- only `verification-coverage` items survive the filter."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([
            _due_finding("alpha"),
            {
                "source": "due-for-verification",
                "check": "due-for-verification-unevaluable",
                "status": "warn",
                "message": "zbroken: could not be evaluated here — RuntimeError: boom",
                "evidence": {"project": "zbroken", "id": ""},
            },
            _coverage_finding("alpha", 10, 4, 40),
        ]),
    )

    result = mod.verification_staleness_findings()

    assert len(result) == 1
    assert result[0]["check"] == "verification-coverage"
    assert result[0]["evidence"]["project"] == "alpha"


def test_empty_findings_returns_empty(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(mod.subprocess, "run", _fake_run([]))

    result = mod.verification_staleness_findings()

    assert result == []


def test_no_coverage_findings_returns_empty(monkeypatch):
    """Only non-coverage item kinds present (e.g. a fleet with due items but
    no eligible tracked-entry projects) -- filters down to `[]`."""
    mod = _load_fleet_picture()
    monkeypatch.setattr(mod.subprocess, "run", _fake_run([_due_finding("alpha")]))

    result = mod.verification_staleness_findings()

    assert result == []


def test_subprocess_failure_raises_the_caller_degrades(monkeypatch):
    """`verification_staleness_findings()` itself does NOT catch a subprocess
    failure -- it raises (`check=True` -> `CalledProcessError`). Degrading to
    a "could not check" watch line is `main()`'s own job, matching the
    documented Boundaries."""
    mod = _load_fleet_picture()

    def _boom(cmd, **kwargs):
        raise subprocess.CalledProcessError(2, cmd)

    monkeypatch.setattr(mod.subprocess, "run", _boom)

    with pytest.raises(subprocess.CalledProcessError):
        mod.verification_staleness_findings()


def test_malformed_json_raises(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        lambda cmd, **kwargs: _FakeCompletedProcess("not json"),
    )

    with pytest.raises(json.JSONDecodeError):
        mod.verification_staleness_findings()
