#!/usr/bin/env python3
"""Every ``pyforge-*`` package's ruff ``target-version`` and mypy
``python_version`` match the interpreter ``pixi.toml`` pins -- the registry
shape of ``pixi-version-check`` applied to the lint / type targets (steward
Story 66.1, ``spec-pyforge-steward`` CAP-153; decided 2026-09-04, landed
2026-09-20).

Reads ``pixi.toml``'s ``[feature.python.dependencies] python`` floor
(``>=3.14.7,3.14.*`` -> ``3.14``) once, then each of the ten
``src/shared/packages/pyforge-*/pyproject.toml``: ``[tool.ruff]
target-version`` must be ``py314`` and ``[tool.mypy] python_version`` must be
``3.14`` (both derived from the pin, never hard-coded here). A package with
no ``[tool.ruff]`` / ``[tool.mypy]`` at all is a finding too -- that is the
un-gated state this story retired.

EXIT  0 clean · 1 drift · 2 could-not-run
"""
from __future__ import annotations

# Registry declaration -- see scripts/detectors.py. Tracked files only.
DETECTOR = {"scope": "repo"}

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES_DIR = ROOT / "src" / "shared" / "packages"
_PY_RE = re.compile(r"(\d+)\.(\d+)")


def interpreter_minor() -> tuple[int, int] | None:
    data = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
    pin = str(data.get("feature", {}).get("python", {}).get("dependencies", {}).get("python", ""))
    m = _PY_RE.search(pin)
    return (int(m.group(1)), int(m.group(2))) if m else None


def findings_for(pyproject: Path, minor: tuple[int, int]) -> list[str]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    tool = data.get("tool", {})
    out: list[str] = []
    want_ruff = f"py{minor[0]}{minor[1]}"
    want_mypy = f"{minor[0]}.{minor[1]}"
    ruff = tool.get("ruff")
    if not isinstance(ruff, dict):
        out.append("no [tool.ruff] section")
    elif ruff.get("target-version") != want_ruff:
        out.append(f"[tool.ruff] target-version = {ruff.get('target-version')!r}, interpreter is {want_ruff}")
    mypy = tool.get("mypy")
    if not isinstance(mypy, dict):
        out.append("no [tool.mypy] section")
    elif str(mypy.get("python_version")) != want_mypy:
        out.append(f"[tool.mypy] python_version = {mypy.get('python_version')!r}, interpreter is {want_mypy}")
    return out


def main() -> int:
    minor = interpreter_minor()
    if minor is None:
        print("[target-version] could-not-run -- pixi.toml has no parseable python pin")
        return 2
    pkgs = sorted(p for p in PACKAGES_DIR.glob("pyforge-*") if (p / "pyproject.toml").is_file())
    if not pkgs:
        print(f"[target-version] could-not-run -- no pyforge-* packages under {PACKAGES_DIR}")
        return 2
    total = 0
    for pkg in pkgs:
        for f in findings_for(pkg / "pyproject.toml", minor):
            print(f"[target-version] drift -- {pkg.name}: {f}")
            total += 1
    if total:
        print(f"[target-version] {total} finding(s) across {len(pkgs)} package(s); interpreter {minor[0]}.{minor[1]}")
        return 1
    print(f"[target-version] ok -- {len(pkgs)} packages target py{minor[0]}{minor[1]} / {minor[0]}.{minor[1]}, matching pixi.toml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
