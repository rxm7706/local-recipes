#!/usr/bin/env python3
"""The ten ``pyforge-*`` packages' lint / type gate, one runner for three verbs
(steward Story 66.1, ``spec-pyforge-steward`` CAP-153).

    python scripts/lint_types.py ruff            # ruff check   src + tests, per package
    python scripts/lint_types.py ruff-format     # ruff format --check
    python scripts/lint_types.py ruff-format --fix
    python scripts/lint_types.py mypy            # mypy -p pyforge.<station>, cwd = the package

Why a runner and not three shell lines: each package carries its OWN
``[tool.ruff]`` / ``[tool.mypy]`` in its ``pyproject.toml`` (py314 targets;
mypy strict for ``pyforge-core``; the 2026-09-20 mypy baseline disabled per
module, per error code -- never ``ignore_errors``), and ruff/mypy only read
the config nearest the files they are given when run from inside that
package. The CI lane (``.github/workflows/lint-types.yml``) and the
``pr-preflight`` leg call the pixi tasks that call this script verbatim, so
local and runner cannot diverge -- the whole reason the story exists.

``src/platform`` is NOT in scope: it has its own ``platform-ci`` lane and a
step-for-step local twin (``platform-ci-local -- --test``).

EXIT  0 clean · 1 findings (the tool's own non-zero) · 2 could-not-run
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = ROOT / "src" / "shared" / "packages"


def packages() -> list[Path]:
    return sorted(p for p in PACKAGES_DIR.glob("pyforge-*") if (p / "pyproject.toml").is_file())


def _run(argv: list[str], cwd: Path) -> int:
    proc = subprocess.run(argv, cwd=cwd)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("verb", choices=["ruff", "ruff-format", "mypy"])
    parser.add_argument("--fix", action="store_true", help="ruff-format only: rewrite in place")
    args = parser.parse_args(argv)

    tool = "ruff" if args.verb.startswith("ruff") else "mypy"
    if shutil.which(tool) is None:
        print(f"[lint-types] could-not-run -- `{tool}` is not on PATH (run from `-e pyforge-guild`)")
        return 2
    pkgs = packages()
    if len(pkgs) < 10:
        print(f"[lint-types] could-not-run -- expected ten pyforge-* packages under {PACKAGES_DIR}, found {len(pkgs)}")
        return 2

    worst = 0
    for pkg in pkgs:
        trees = [d for d in ("src", "tests") if (pkg / d).is_dir()]
        if args.verb == "ruff":
            rc = _run(["ruff", "check", *trees], cwd=pkg)
        elif args.verb == "ruff-format":
            rc = _run(["ruff", "format", *([] if args.fix else ["--check"]), *trees], cwd=pkg)
        else:
            # By package NAME over mypy_path=src, never `mypy src`: each station is also an
            # editable install on sys.path, and crawling the directory made mypy see every
            # module twice ("found twice under different module names").
            import_name = next(d.name for d in (pkg / "src" / "pyforge").iterdir() if d.is_dir() and not d.name.startswith("_"))
            rc = _run(["mypy", "-p", f"pyforge.{import_name}"], cwd=pkg)
        status = "ok" if rc == 0 else f"exit {rc}"
        print(f"[lint-types] {args.verb:<11} {pkg.name:<20} {status}")
        worst = max(worst, 1 if rc else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main())
