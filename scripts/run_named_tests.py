"""Run the pytest node ids named on the command line, and fail when one of them skips.

Steward Story 136.6 (spec-pyforge-steward CAP-175): seven tests skipped in the only environment their
suite runs in, so no CI job ran them. Each now runs by node id, in an environment that holds its
imports, through a pixi task that calls this script: ``steward-share-tree-test`` (``-e pyforge-guild``)
and ``scribe-plane-and-portal-test`` (``-e pyforge-foundry-full``).

pytest exits 0 when every selected test skips, so a later import change would turn such a step into a
silent pass. This script reads the run's JUnit report instead and exits:

* pytest's own exit code, when pytest fails (a failing test, or a node id that no longer exists);
* 1, when a named test skipped, or when a named node id has no case in the report (deselected, say);
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


def _case_matches(node_id: str, classname: str, name: str) -> bool:
    """Whether a JUnit case is the test ``node_id`` names (a parametrized case keeps its ``[...]``)."""
    path, _, rest = node_id.partition("::")
    parts = rest.split("::") if rest else []
    if not parts:
        return False
    module = path.removesuffix(".py").replace("/", ".").replace("\\", ".").strip(".")
    expected = ".".join([module, *parts[:-1]])
    # pytest writes the class name from its own root, so either dotted name may be the longer one.
    same_place = (
        classname == expected
        or expected.endswith("." + classname)
        or classname.endswith("." + expected)
    )
    return same_place and name.split("[", 1)[0] == parts[-1].split("[", 1)[0]


def read_report(report: Path, node_ids: Sequence[str]) -> tuple[list[str], list[str]]:
    """The node ids no case of a JUnit report ran, and one line per case that skipped."""
    cases = list(ET.parse(report).getroot().iter("testcase"))
    skipped: list[str] = []
    for case in cases:
        skip = case.find("skipped")
        if skip is not None:
            name = f"{case.get('classname', '')}::{case.get('name', '')}"
            skipped.append(f"{name}: {skip.get('message', '')}")
    not_run = [
        node_id
        for node_id in node_ids
        if not any(
            _case_matches(node_id, case.get("classname", ""), case.get("name", ""))
            for case in cases
        )
    ]
    return not_run, skipped


def verdict(
    pytest_exit: int, not_run: Sequence[str], skipped: Sequence[str]
) -> tuple[int, list[str]]:
    """The exit code for a run, and the lines that explain a non-zero one."""
    if pytest_exit != 0:
        return pytest_exit, [f"pytest exited {pytest_exit}"]
    problems = [f"skipped, and a skip fails this run: {line}" for line in skipped]
    problems += [f"named and did not run: {node_id}" for node_id in not_run]
    return (1 if problems else 0), problems


def main(argv: Sequence[str] | None = None) -> int:
    node_ids = list(sys.argv[1:] if argv is None else argv)
    if not node_ids or any(arg.startswith("-") for arg in node_ids):
        print(
            "usage: run_named_tests.py <pytest node id> [<pytest node id> ...]",
            file=sys.stderr,
        )
        return USAGE_EXIT
    with tempfile.TemporaryDirectory() as scratch:
        report = Path(scratch) / "junit.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-rs",
            "-p",
            "no:cacheprovider",
            f"--junitxml={report}",
        ]
        pytest_exit = subprocess.run([*command, *node_ids], check=False).returncode
        not_run, skipped = (
            read_report(report, node_ids) if report.is_file() else (list(node_ids), [])
        )
    code, problems = verdict(pytest_exit, not_run, skipped)
    for line in problems:
        print(f"run_named_tests: {line}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
