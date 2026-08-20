"""Meta-test: `bmad_core_drift_findings()` in fleet_picture.py.

Story 10.3 wires `Source.BMAD_METHOD_VERSION_DRIFT` (Story 10.1/10.2's
`bmad_method.gather`) into `fleet_picture.py`'s ATTENTION block: a small,
separately-callable, testable function -- mirroring
`loop_home_staleness()`'s own extracted shape -- that shells out to
`sys.executable -m pyforge.doctor.sources bmad-method-version-drift --json`
and returns only the `status == "warn"` findings. `main()`'s own ATTENTION
block wraps the call in a `try/except Exception: watch.append(...)` idiom
(same as every other ATTENTION probe in that file); this function itself
does NOT catch failures -- it raises, and degrading to a "could not check"
line is the caller's job (spec Boundaries).

Same `_load_fleet_picture()` harness as
`test_fleet_picture_loop_home_staleness.py` (that file isn't a package, so
it's loaded via `importlib.util.spec_from_file_location`). `subprocess.run`
is monkeypatched rather than actually invoking `python -m
pyforge.doctor.sources` -- no real npm network call or real pixi.toml/
manifest.yaml drift state is needed to exercise this function.
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
    bmad-method-version-drift --json` invocation would print."""

    def _run(cmd, **kwargs):
        assert cmd[0] == sys.executable
        assert cmd[1:4] == ["-m", "pyforge.doctor.sources", "bmad-method-version-drift"]
        assert "--json" in cmd
        return _FakeCompletedProcess(json.dumps(findings))

    return _run


def test_a_real_warn_finding_is_returned(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([
            {"source": "bmad-method-version-drift", "check": "bmad-method-version-drift",
             "status": "warn",
             "message": "installed bmad-method 6.9.0 is behind pixi.toml's "
                        "declared floor >=6.11.0",
             "evidence": {}},
        ]),
    )

    result = mod.bmad_core_drift_findings()

    assert len(result) == 1
    assert result[0]["status"] == "warn"


def test_no_drift_all_ok_returns_empty(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        _fake_run([
            {"source": "bmad-method-version-drift", "check": "bmad-method-version-drift",
             "status": "ok", "message": "meets floor", "evidence": {}},
        ]),
    )

    result = mod.bmad_core_drift_findings()

    assert result == []


def test_no_drift_empty_findings_returns_empty(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(mod.subprocess, "run", _fake_run([]))

    result = mod.bmad_core_drift_findings()

    assert result == []


def test_subprocess_failure_raises_the_caller_degrades(monkeypatch):
    """`bmad_core_drift_findings()` itself does NOT catch a subprocess
    failure -- it raises (`check=True` -> `CalledProcessError`). Degrading
    to a "could not check" watch line is `main()`'s own job, matching the
    documented Boundaries."""
    mod = _load_fleet_picture()

    def _boom(cmd, **kwargs):
        raise subprocess.CalledProcessError(2, cmd)

    monkeypatch.setattr(mod.subprocess, "run", _boom)

    with pytest.raises(subprocess.CalledProcessError):
        mod.bmad_core_drift_findings()


def test_malformed_json_raises(monkeypatch):
    mod = _load_fleet_picture()
    monkeypatch.setattr(
        mod.subprocess, "run",
        lambda cmd, **kwargs: _FakeCompletedProcess("not json"),
    )

    with pytest.raises(json.JSONDecodeError):
        mod.bmad_core_drift_findings()
