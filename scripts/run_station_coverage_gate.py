#!/usr/bin/env python3
"""Full-package coverage gate for one station (pixi ``*-test-coverage``).

Unlike ``scripts/coverage_gates_ci.py`` (PR path-filtered / touched-module
mode), this evaluates *every* measured module against the station floors so
operators get the complete named-module failure list (Story 19.3 / FR-131).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# coverage_gate.py is a scripts/ sibling (spec-coverage-gate-independence
# CAP-1, doctor Story 24.1: the evaluator moved out of pyforge.marshal so no
# station governs its own CI gate). Insert this file's own directory
# explicitly so the import resolves whether this driver is executed directly
# (`python scripts/run_station_coverage_gate.py`, which Python already
# prepends) or loaded via importlib (test harnesses, which do not).
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from coverage_gate import (  # noqa: E402
    evaluate_coverage_payload,
    package_root,
    package_src,
    thresholds_for,
)


def _suite_test_paths(root: Path, suite: str) -> list[Path]:
    # Story 32.5 (spec-fleet-consistency-standard CAP-2): the fleet speaks one
    # suite vocabulary -- unit/ + integration/ + meta/ -- so this map needs no
    # per-station special case. It previously named `contract` (marshal-only, a
    # one-file placeholder) and knew neither spelling of `conformance`, which is
    # why steward's 32 CLI-contract tests and warden's 19 oracle gates were
    # measured by nothing at all. They now live in unit/ and integration/.
    if suite == "unit":
        names = ("unit", "meta")
    elif suite == "integration":
        names = ("integration",)
    else:
        names = (suite,)
    return [root / "tests" / name for name in names if (root / "tests" / name).is_dir()]


def _run_suite(station: str, suite: str, report: Path) -> tuple[str, int]:
    """Return ``(status, pytest_rc)`` — ``skipped`` means do not evaluate."""
    root = package_root(REPO, station)
    src = package_src(REPO, station)
    test_paths = _suite_test_paths(root, suite)
    if not test_paths:
        print(f"skip {station} {suite}: no matching tests/", flush=True)
        return "skipped", 0
    if not src.is_dir():
        print(f"skip {station} {suite}: missing src at {src}", flush=True)
        return "skipped", 0
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *[str(p) for p in test_paths],
        "-q",
        "-m",
        "not slow",
        f"--cov=pyforge.{station}",
        "--cov-branch",
        f"--cov-report=json:{report}",
        "--cov-report=term-missing:skip-covered",
    ]
    print("+", " ".join(cmd), flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "src"), str(_SCRIPTS_DIR), env.get("PYTHONPATH", "")]
    )
    return "ran", subprocess.run(cmd, cwd=REPO, env=env, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", required=True)
    parser.add_argument(
        "--suites",
        default="unit,integration",
        help="Comma-separated suites (default: unit,integration)",
    )
    args = parser.parse_args(argv)
    station = args.station
    suites = [s.strip() for s in args.suites.split(",") if s.strip()]
    rc = 0
    with tempfile.TemporaryDirectory(prefix=f"cov-{station}-") as tmp:
        tmp_path = Path(tmp)
        for suite in suites:
            if suite not in ("unit", "integration"):
                print(f"unknown suite {suite!r}; expected unit|integration", flush=True)
                return 2
            report = tmp_path / f"{suite}.json"
            status, pytest_rc = _run_suite(station, suite, report)
            if status == "skipped":
                continue
            if pytest_rc != 0:
                print(f"pytest failed for {station} {suite} (exit {pytest_rc})")
                rc = 1
                if not report.is_file():
                    continue
            try:
                payload = json.loads(report.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"unreadable coverage JSON for {station} {suite}: {exc}")
                rc = 1
                continue
            ok, message = evaluate_coverage_payload(
                payload,
                station=station,
                suite=suite,  # type: ignore[arg-type]
            )
            print(message, flush=True)
            thr = thresholds_for(station).for_suite(suite)  # type: ignore[arg-type]
            print(f"pyforge-{station} {suite} floor: {thr:.0f}%", flush=True)
            if not ok:
                rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
