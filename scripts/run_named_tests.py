"""Run the pytest node ids named on the command line, and fail when one of them skips.

Steward Story 136.6 (spec-pyforge-steward CAP-175): seven tests skipped in the only environment their
suite runs in, so no CI job ran them. Each now runs by node id, in an environment that holds its
imports, through a pixi task that calls this script: ``steward-share-tree-test`` (``-e pyforge-guild``)
and ``scribe-plane-and-portal-test`` (``-e pyforge-foundry-full``).

pytest exits 0 when every selected test skips, so a later import change would turn such a step into a
silent pass. This script reads the run's JUnit report instead and exits:

* pytest's own exit code, when pytest fails (a failing test, or a node id that no longer exists);
* 1, when a named test skipped, or when fewer tests ran than node ids were named;
* 0, when every named test ran and passed.

Usage: ``python scripts/run_named_tests.py <node id> [<node id> ...]``. Standard library only.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path

USAGE_EXIT = 2


def skipped_cases(report: Path) -> tuple[int, list[str]]:
    """The number of test cases in a JUnit report, and one line per case that skipped."""
    cases = list(ET.parse(report).getroot().iter("testcase"))
    skipped: list[str] = []
    for case in cases:
        skip = case.find("skipped")
        if skip is not None:
            name = f"{case.get('classname', '')}::{case.get('name', '')}"
            skipped.append(f"{name}: {skip.get('message', '')}")
    return len(cases), skipped


def verdict(node_ids: Sequence[str], pytest_exit: int, ran: int, skipped: Sequence[str]) -> tuple[int, list[str]]:
    """The exit code for a run, and the lines that explain a non-zero one."""
    if pytest_exit != 0:
        return pytest_exit, [f"pytest exited {pytest_exit}"]
    problems = [f"skipped, and a skip fails this run: {line}" for line in skipped]
    if ran < len(node_ids):
        problems.append(f"{len(node_ids)} node ids were named and {ran} tests ran")
    return (1 if problems else 0), problems


def main(argv: Sequence[str] | None = None) -> int:
    node_ids = list(sys.argv[1:] if argv is None else argv)
    if not node_ids or any(arg.startswith("-") for arg in node_ids):
        print("usage: run_named_tests.py <pytest node id> [<pytest node id> ...]", file=sys.stderr)
        return USAGE_EXIT
    with tempfile.TemporaryDirectory() as scratch:
        report = Path(scratch) / "junit.xml"
        command = [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", f"--junitxml={report}"]
        pytest_exit = subprocess.run([*command, *node_ids], check=False).returncode
        ran, skipped = skipped_cases(report) if report.is_file() else (0, [])
    code, problems = verdict(node_ids, pytest_exit, ran, skipped)
    for line in problems:
        print(f"run_named_tests: {line}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
