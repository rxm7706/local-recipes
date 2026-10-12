#!/usr/bin/env python3
"""Every lint/type target and ``requires-python`` floor matches the interpreter
``pixi.toml`` pins -- the registry shape of ``pixi-version-check`` applied to
ruff / mypy targets and project floors (steward Story 66.1 / 93.1 / 95.1,
``spec-pyforge-steward`` CAP-153).

Reads ``pixi.toml``'s ``[feature.python.dependencies] python`` floor once, then:

- ten ``src/shared/packages/pyforge-*/pyproject.toml``: ``[tool.ruff]
  target-version``, ``[tool.mypy] python_version``, and ``[project]
  requires-python`` lower bound;
- nine ``src/shared/packages/django-*/pyproject.toml``: ``[tool.ruff]
  target-version`` and ``requires-python`` lower bound (no mypy required);
- ``src/platform/pyproject.toml``: ``[tool.ruff] target-version`` and
  ``[tool.mypy] python_version`` (no ``[project]`` table).

Expected values are derived from the pin, never hard-coded here.

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
PLATFORM_PYPROJECT = ROOT / "src" / "platform" / "pyproject.toml"
_PY_RE = re.compile(r"(\d+)\.(\d+)")
_REQ_RE = re.compile(r">=?(\d+)\.(\d+)")


def interpreter_minor() -> tuple[int, int] | None:
    data = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
    pin = str(data.get("feature", {}).get("python", {}).get("dependencies", {}).get("python", ""))
    m = _PY_RE.search(pin)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _want_targets(minor: tuple[int, int]) -> tuple[str, str]:
    return f"py{minor[0]}{minor[1]}", f"{minor[0]}.{minor[1]}"


def _requires_python_floor(data: dict, minor: tuple[int, int]) -> list[str]:
    project = data.get("project")
    if not isinstance(project, dict):
        return []
    req = project.get("requires-python")
    want_floor = f">={minor[0]}.{minor[1]}"
    if req is None:
        return ["missing [project] requires-python"]
    req_s = str(req)
    m = _REQ_RE.search(req_s)
    if not m:
        return [f"[project] requires-python = {req_s!r} has no parseable lower bound"]
    got = (int(m.group(1)), int(m.group(2)))
    if got != minor:
        return [f"[project] requires-python = {req_s!r}, interpreter floor is {want_floor}"]
    return []


def findings_for_pyforge(pyproject: Path, minor: tuple[int, int]) -> list[str]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    tool = data.get("tool", {})
    out: list[str] = []
    want_ruff, want_mypy = _want_targets(minor)
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
    out.extend(_requires_python_floor(data, minor))
    return out


def findings_for_django(pyproject: Path, minor: tuple[int, int]) -> list[str]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    tool = data.get("tool", {})
    out: list[str] = []
    want_ruff, _ = _want_targets(minor)
    ruff = tool.get("ruff")
    if not isinstance(ruff, dict):
        out.append("no [tool.ruff] section")
    elif ruff.get("target-version") != want_ruff:
        out.append(f"[tool.ruff] target-version = {ruff.get('target-version')!r}, interpreter is {want_ruff}")
    out.extend(_requires_python_floor(data, minor))
    return out


def findings_for_platform(pyproject: Path, minor: tuple[int, int]) -> list[str]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    tool = data.get("tool", {})
    out: list[str] = []
    want_ruff, want_mypy = _want_targets(minor)
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


# Backward-compatible alias for tests/scripts/test_lint_types_gate.py
findings_for = findings_for_pyforge


def main() -> int:
    minor = interpreter_minor()
    if minor is None:
        print("[target-version] could-not-run -- pixi.toml has no parseable python pin")
        return 2
    pyforge_pkgs = sorted(p for p in PACKAGES_DIR.glob("pyforge-*") if (p / "pyproject.toml").is_file())
    django_pkgs = sorted(p for p in PACKAGES_DIR.glob("django-*") if (p / "pyproject.toml").is_file())
    if len(pyforge_pkgs) < 10:
        print(f"[target-version] could-not-run -- expected ten pyforge-* packages, found {len(pyforge_pkgs)}")
        return 2
    if len(django_pkgs) < 9:
        print(f"[target-version] could-not-run -- expected nine django-* packages, found {len(django_pkgs)}")
        return 2
    if not PLATFORM_PYPROJECT.is_file():
        print("[target-version] could-not-run -- src/platform/pyproject.toml is missing")
        return 2

    total = 0
    for pkg in pyforge_pkgs:
        for f in findings_for_pyforge(pkg / "pyproject.toml", minor):
            print(f"[target-version] drift -- {pkg.name}: {f}")
            total += 1
    for pkg in django_pkgs:
        for f in findings_for_django(pkg / "pyproject.toml", minor):
            print(f"[target-version] drift -- {pkg.name}: {f}")
            total += 1
    for f in findings_for_platform(PLATFORM_PYPROJECT, minor):
        print(f"[target-version] drift -- src/platform: {f}")
        total += 1

    if total:
        print(
            f"[target-version] {total} finding(s) across "
            f"{len(pyforge_pkgs)} pyforge-*, {len(django_pkgs)} django-*, and src/platform; "
            f"interpreter {minor[0]}.{minor[1]}"
        )
        return 1
    print(
        f"[target-version] ok -- {len(pyforge_pkgs)} pyforge-*, {len(django_pkgs)} django-*, "
        f"and src/platform target py{minor[0]}{minor[1]} / {minor[0]}.{minor[1]}, matching pixi.toml"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
