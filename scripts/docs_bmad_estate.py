#!/usr/bin/env python3
"""Generator door: ``docs/reference/bmad-estate-llms-full.md`` (doctor Story 30.4,
spec-pyforge-doctor CAP-84; the catalog itself is scribe Story 24.1/24.2, spec-pyforge-scribe CAP-32).

The page's generator is scribe's own CLI, ``scribe catalog bmad-estate``. ``docs-currency``
runs only a ``scripts/docs_*.py`` generator (doctor Story 40.2), so ``docs/map.yaml`` could not
name one for this page and reported it as a registry gap. This script is that door and nothing
more: both modes hand the work to the scribe CLI entry (never ``pyforge.scribe`` internals),
run through this interpreter, so the verdict is scribe's and ``bmad-estate-check`` stays the
detector of record.

Usage::

    python scripts/docs_bmad_estate.py                    # regenerate (scribe catalog bmad-estate --write)
    python scripts/docs_bmad_estate.py --check            # exit 0 current, 1 stale, 2 could not run
    python scripts/docs_bmad_estate.py --check --root R   # judge another checkout's tree
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "[docs-bmad-estate]"


def scribe_command(root: Path, *, check: bool) -> list[str]:
    """The scribe CLI call for one mode, run by this interpreter."""
    mode = "--check" if check else "--write"
    return [sys.executable, "-m", "pyforge.scribe.cli", "catalog", "bmad-estate", mode, "--root", str(root)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Report staleness without writing.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (default: this checkout).")
    args = parser.parse_args(argv)
    if importlib.util.find_spec("pyforge.scribe") is None:
        print(f"{PREFIX} could-not-run: `pyforge.scribe` is not importable here ({sys.executable})")
        return 2
    try:
        proc = subprocess.run(scribe_command(args.root, check=args.check), capture_output=True, text=True, check=False)
    except OSError as exc:
        print(f"{PREFIX} could-not-run: {exc}")
        return 2
    output = (proc.stdout + proc.stderr).strip()
    if output:
        print(output)
    if proc.returncode in (0, 1):
        return proc.returncode
    return 2


if __name__ == "__main__":
    sys.exit(main())
