#!/usr/bin/env python3
"""
run_skill_suite.py — Master test runner for conda-forge-expert.

Runs the entire test surface in one command:
  - unit tests (parsers, validators, license checker, vuln scanner, etc.)
  - meta tests (script imports, SKILL.md consistency)
  - integration tests (workflow end-to-end, MCP atlas tools)

Defaults to pytest discovery under tests/, with sensible markers and
output. Tests that need cf_atlas.db / vdb / network gracefully self-skip
when their preconditions aren't met, so this runner works on any machine
where Python + pytest + pyyaml are available.

CLI:
  run_skill_suite.py [--unit | --integration | --meta | --all]
                     [--keyword K] [--verbose] [--coverage]

Defaults:
  --all           : run everything (default if no scope flag given).
  --keyword K     : pytest -k filter.
  --verbose       : pytest -vv.
  --coverage      : run under coverage.py if installed.

Pixi:
  pixi run -e local-recipes test-skill                # all tests, summary view
  pixi run -e local-recipes test-skill -- --unit -vv  # unit only, verbose
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Master runner for the conda-forge-expert test suite."
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--unit", action="store_const", const="unit", dest="scope")
    scope.add_argument("--integration", action="store_const", const="integration", dest="scope")
    scope.add_argument("--meta", action="store_const", const="meta", dest="scope")
    scope.add_argument("--all", action="store_const", const="all", dest="scope")
    parser.add_argument("-k", "--keyword", default=None,
                        help="pytest -k filter")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--coverage", action="store_true",
                        help="Run under coverage.py if installed")
    args = parser.parse_args()
    scope = args.scope or "all"

    if scope == "all":
        target = str(TESTS_DIR)
    else:
        target = str(TESTS_DIR / scope)

    cmd: list[str] = []
    if args.coverage and shutil.which("coverage"):
        cmd = ["coverage", "run", "--source", str(SKILL_DIR / "scripts"),
               "-m", "pytest"]
    else:
        cmd = [sys.executable, "-m", "pytest"]
    cmd.append(target)
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-q")
    cmd.extend(["-rs", "--color=yes"])

    print("═" * 70)
    print(f"  conda-forge-expert · run_skill_suite ({scope})")
    print(f"  $ {' '.join(cmd)}")
    print("═" * 70)
    rc = subprocess.run(cmd).returncode
    if args.coverage and shutil.which("coverage") and rc == 0:
        print("\n→ Coverage summary")
        subprocess.run(["coverage", "report", "-m", "--skip-empty"])
    return rc


if __name__ == "__main__":
    sys.exit(main())
