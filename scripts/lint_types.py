#!/usr/bin/env python3
"""The ten ``pyforge-*`` and nine ``django-*`` portal packages' ruff gate, plus
``pyforge-*`` mypy (steward Story 66.1 / 93.1, ``spec-pyforge-steward`` CAP-153).

    python scripts/lint_types.py ruff            # ruff check   src + tests, per package
    python scripts/lint_types.py ruff-format     # ruff format --check
    python scripts/lint_types.py ruff-format --fix
    python scripts/lint_types.py mypy            # mypy -p pyforge.<station>, cwd = the package

Why a runner and not three shell lines: each package carries its OWN
``[tool.ruff]`` / ``[tool.mypy]`` in its ``pyproject.toml`` (py314 targets for
``pyforge-*``; ``py312`` for ``django-*``; mypy strict for ``pyforge-core``; the
2026-09-20 mypy baseline disabled per module, per error code -- never
``ignore_errors``), and ruff/mypy only read the config nearest the files they
are given when run from inside that package. The CI lane
(``.github/workflows/lint-types.yml``) and the ``pr-preflight`` leg call the
pixi tasks that call this script verbatim, so local and runner cannot diverge.

Django packages not yet clean for a verb are listed in ``NOT_YET_CLEAN``; that
map only shrinks as each station's fix story lands (Story 93.1).

``src/platform`` is NOT in scope: it has its own ``platform-ci`` lane and a
step-for-step local twin (``platform-ci-local -- --test``).

EXIT  0 clean · 1 findings (the tool's own non-zero) · 2 could-not-run
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = ROOT / "src" / "shared" / "packages"

# Seeded from measurement on Story 93.1's base (2026-10-11). Only shrinks — each
# station's fix story removes its own entry; never re-add a package or verb.
NOT_YET_CLEAN: dict[str, frozenset[str]] = {
    "django-atlas": frozenset({"ruff", "ruff-format"}),
    "django-doctor": frozenset({"ruff"}),
    "django-herald": frozenset({"ruff", "ruff-format"}),
    "django-marshal": frozenset({"ruff", "ruff-format"}),
    "django-mason": frozenset({"ruff"}),
    "django-pyforge": frozenset({"ruff", "ruff-format"}),
    "django-scribe": frozenset({"ruff"}),
    "django-steward": frozenset({"ruff", "ruff-format"}),
    "django-warden": frozenset({"ruff", "ruff-format"}),
}

NOT_YET_CLEAN_CEILING: dict[str, frozenset[str]] = NOT_YET_CLEAN

RUFF_VERBS = frozenset({"ruff", "ruff-format"})


def pyforge_packages(packages_dir: Path = PACKAGES_DIR) -> list[Path]:
    return sorted(p for p in packages_dir.glob("pyforge-*") if (p / "pyproject.toml").is_file())


def django_packages(packages_dir: Path = PACKAGES_DIR) -> list[Path]:
    return sorted(p for p in packages_dir.glob("django-*") if (p / "pyproject.toml").is_file())


def packages() -> list[Path]:
    """Backward-compatible alias: the ten ``pyforge-*`` packages only."""
    return pyforge_packages()


def has_ruff_table(pkg: Path) -> bool:
    data = tomllib.loads((pkg / "pyproject.toml").read_text(encoding="utf-8"))
    return "ruff" in data.get("tool", {})


def _validate_not_yet_clean(django: list[Path]) -> str | None:
    live = {p.name for p in django}
    for name, verbs in NOT_YET_CLEAN.items():
        if not name.startswith("django-"):
            return f"NOT_YET_CLEAN entry `{name}` is not a django-* package name"
        if name.startswith("pyforge-"):
            return f"NOT_YET_CLEAN entry `{name}` must not name a pyforge-* package"
        if name not in live:
            return f"NOT_YET_CLEAN entry `{name}` is not a live django-* package under {PACKAGES_DIR}"
        for verb in verbs:
            if verb not in RUFF_VERBS:
                return f"NOT_YET_CLEAN entry `{name}` names unknown verb `{verb}`"
    return None


def _run(argv: list[str], cwd: Path) -> int:
    proc = subprocess.run(argv, cwd=cwd)
    return proc.returncode


def _listed_for(pkg_name: str, verb: str) -> bool:
    return verb in NOT_YET_CLEAN.get(pkg_name, frozenset())


def _status_line(verb: str, pkg_name: str, rc: int, *, missing_table: bool = False) -> str:
    listed = _listed_for(pkg_name, verb)
    if missing_table:
        detail = "missing [tool.ruff] table"
    elif listed and rc == 0:
        detail = "clean — remove NOT_YET_CLEAN entry"
    elif listed and rc == 1:
        detail = "not yet clean (listed)"
    elif rc == 0:
        detail = "ok"
    else:
        detail = f"exit {rc}"
    return f"[lint-types] {verb:<11} {pkg_name:<20} {detail}"


def _record_worst(worst: int, pkg_name: str, verb: str, rc: int, *, missing_table: bool = False) -> int:
    listed = _listed_for(pkg_name, verb)
    if listed:
        if rc == 0:
            return max(worst, 1)
        if rc == 1 or missing_table:
            return worst
        return max(worst, 1)
    if rc != 0 or missing_table:
        return max(worst, 1)
    return worst


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("verb", choices=["ruff", "ruff-format", "mypy"])
    parser.add_argument("--fix", action="store_true", help="ruff-format only: rewrite in place")
    args = parser.parse_args(argv)

    tool = "ruff" if args.verb.startswith("ruff") else "mypy"
    if shutil.which(tool) is None:
        print(f"[lint-types] could-not-run -- `{tool}` is not on PATH (run from `-e pyforge-guild`)")
        return 2

    pyforge = pyforge_packages()
    if len(pyforge) < 10:
        print(f"[lint-types] could-not-run -- expected ten pyforge-* packages under {PACKAGES_DIR}, found {len(pyforge)}")
        return 2

    if args.verb in RUFF_VERBS:
        django = django_packages()
        if len(django) < 9:
            print(f"[lint-types] could-not-run -- expected nine django-* packages under {PACKAGES_DIR}, found {len(django)}")
            return 2
        err = _validate_not_yet_clean(django)
        if err:
            print(f"[lint-types] could-not-run -- {err}")
            return 2
        pkgs = sorted(pyforge + django, key=lambda p: p.name)
    else:
        pkgs = pyforge

    worst = 0
    for pkg in pkgs:
        pkg_name = pkg.name
        trees = [d for d in ("src", "tests") if (pkg / d).is_dir()]
        is_django = pkg_name.startswith("django-")

        if args.verb in RUFF_VERBS and is_django and not has_ruff_table(pkg):
            print(_status_line(args.verb, pkg_name, 1, missing_table=True))
            worst = _record_worst(worst, pkg_name, args.verb, 1, missing_table=True)
            continue

        if args.verb == "ruff-format" and args.fix and _listed_for(pkg_name, "ruff-format"):
            print(f"[lint-types] ruff-format {pkg_name:<20} skipped (listed for ruff-format)")
            continue

        if args.verb == "ruff":
            rc = _run(["ruff", "check", *trees], cwd=pkg)
        elif args.verb == "ruff-format":
            rc = _run(["ruff", "format", *([] if args.fix else ["--check"]), *trees], cwd=pkg)
        else:
            import_name = next(
                d.name for d in (pkg / "src" / "pyforge").iterdir() if d.is_dir() and not d.name.startswith("_")
            )
            rc = _run(["mypy", "-p", f"pyforge.{import_name}"], cwd=pkg)

        print(_status_line(args.verb, pkg_name, rc))
        worst = _record_worst(worst, pkg_name, args.verb, rc)
    return worst


if __name__ == "__main__":
    sys.exit(main())
