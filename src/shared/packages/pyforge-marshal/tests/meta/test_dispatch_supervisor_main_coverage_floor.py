"""The supervisor entrypoint's restored floor is re-measured, not remembered.

Story 53.3 deleted the dated ``[modules."pyforge.marshal.dispatch_supervisor.
__main__"] unit = 35.0`` exception from ``coverage_thresholds.toml``, so the
module is held to the station's 80% unit floor again. Nothing else re-measures
that: ``scripts/coverage_gates_ci.py`` evaluates only the source modules a
branch *touches*, and an edit that deletes or guts
``tests/unit/test_dispatch_supervisor_main_loop.py`` touches no ``src/`` file
at all -- the gate would skip evaluate, every lane would stay green, and the
module would drift back toward 35% with the debt re-created silently.

This test runs the suite that produced the number, in a subprocess, with
coverage on, and holds the measured percentage to the same floor the gate
would apply. It is the tripwire for the deletion, so a change that moves the
module below its floor reds here on any marshal change rather than on some
future PR that happens to edit the entrypoint.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

# coverage_gate.py moved outside every pyforge.<station> package 2026-09-20
# (doctor Story 24.1, spec-coverage-gate-independence CAP-1), so this
# marshal-owned test loads its sibling scripts/coverage_gate.py the same way
# other package tests reach a top-level scripts/ module (e.g.
# tests/meta/test_fleet_picture_attention_dispatch_refused.py), rather than
# importing a package that no longer ships it.
_REPO_ROOT = Path(__file__).resolve().parents[6]
_COVERAGE_GATE_PATH = _REPO_ROOT / "scripts" / "coverage_gate.py"


def _load_coverage_gate():
    spec = importlib.util.spec_from_file_location("coverage_gate_under_test", _COVERAGE_GATE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_coverage_gate = _load_coverage_gate()
load_module_floors = _coverage_gate.load_module_floors
thresholds_for = _coverage_gate.thresholds_for

_MODULE = "pyforge.marshal.dispatch_supervisor.__main__"
_STATION = "marshal"
_SUITE_RELATIVE = Path("tests") / "unit" / "test_dispatch_supervisor_main_loop.py"
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_MODULE_TAIL = Path("pyforge") / "marshal" / "dispatch_supervisor" / "__main__.py"


def _child_env() -> dict[str, str]:
    """The parent's environment minus pytest-cov's subprocess hooks.

    ``COV_CORE_*`` makes a child process join the *parent's* coverage run and
    write into its data file; this measurement must stand alone.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith("COV_CORE")}
    env.pop("COVERAGE_PROCESS_START", None)
    return env


def test_the_supervisor_entrypoint_measures_at_or_above_its_floor(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    env = _child_env()
    env["COVERAGE_FILE"] = str(tmp_path / ".coverage")

    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [
            sys.executable,
            "-m",
            "pytest",
            str(_SUITE_RELATIVE),
            "-q",
            "-p",
            "no:randomly",
            f"--cov={_MODULE}",
            "--cov-branch",
            f"--cov-report=json:{report}",
            "--cov-report=",
        ],
        cwd=_PACKAGE_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout[-4000:] + completed.stderr[-2000:]
    payload = json.loads(report.read_text(encoding="utf-8"))
    tail = str(_MODULE_TAIL)
    measured = {path: data for path, data in payload["files"].items() if path.endswith(tail)}
    assert len(measured) == 1, sorted(payload["files"])
    percent = next(iter(measured.values()))["summary"]["percent_covered"]

    # The floor the gate itself would apply: a per-module exception if one is
    # ever held again (none is today -- Story 53.3), else the station floor.
    floor = load_module_floors().get(_MODULE)
    if floor is None:
        floor = thresholds_for(_STATION).for_suite("unit")
    assert percent >= floor, f"{_MODULE} measured {percent:.1f}%, floor {floor:.1f}%"
