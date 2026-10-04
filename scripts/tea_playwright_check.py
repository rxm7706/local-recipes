#!/usr/bin/env python3
"""tea-playwright-check — CAP-5 story-id drift against on-disk Story Coverage Matrices.

Story 86.6 registers this as a repo-scope detector (`detectors-ci`). The verdict is
`_bmad/scripts/bmad_tea_playwright.py --all --check` (the generator owns the matrix
contract; this file is the registry-facing wrapper only).

EXIT
    0  all eight stations covered
    1  at least one station drifted (stderr lines name the station)
    2  could not run (missing generator or unexpected failure)
"""

from __future__ import annotations

DETECTOR = {"scope": "repo"}

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATOR = ROOT / "_bmad" / "scripts" / "bmad_tea_playwright.py"
PREFIX = "[tea-playwright]"


def run_check(root: Path) -> tuple[int, list[str]]:
    if not GENERATOR.is_file():
        rel = GENERATOR.relative_to(root).as_posix()
        return 2, [f"{PREFIX} could-not-run: missing generator at {rel}"]
    command = [sys.executable, str(GENERATOR), "--all", "--check", "--repo-root", str(root)]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        return 2, [f"{PREFIX} could-not-run: {exc}"]
    lines = [line for line in (proc.stdout + proc.stderr).splitlines() if line.strip()]
    if proc.returncode not in (0, 1):
        return 2, [f"{PREFIX} could-not-run: generator exited {proc.returncode}", *lines]
    return proc.returncode, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (default: this checkout).")
    parser.add_argument("--json", action="store_true", help="Emit {status, findings} as JSON.")
    args = parser.parse_args(argv)
    code, lines = run_check(args.root)
    status = {0: "ok", 1: "findings", 2: "could-not-run"}[code]
    if args.json:
        print(json.dumps({"detector": "tea-playwright-check", "status": status, "exit": code, "findings": lines}))
    else:
        for line in lines:
            print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
