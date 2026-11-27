#!/usr/bin/env python3
"""Every lint/type target and ``requires-python`` floor matches the interpreter
``pixi.toml`` pins -- the registry shape of ``pixi-version-check`` applied to
ruff / mypy targets and project floors (steward Story 66.1 / 93.1 / 95.1 / 124.3 / 148.1 / 148.3,
``spec-pyforge-steward`` CAP-153).

Reads the one Python ``pixi.toml`` declares, ``[feature.interpreter.dependencies] python = "X.Y.Z.*"`` (steward
Story 148.1), then holds every copy of it:

- ``pixi.toml`` itself: no other feature and no ``[dependencies]`` names ``python``, and every environment lists the
  ``interpreter`` feature, so each one resolves the declared version (Story 148.1);
- ``pixi.lock``: every environment, on every platform, resolves exactly ``X.Y.Z`` (Story 148.1);
- ``.github/workflows`` and ``.github/actions``: Python is set up only through ``./.github/actions/setup-estate-python``,
  which reads the declaration, never by another ``actions/setup-python`` step; and no step starts a ``python``
  command before its job has an interpreter from that action, an activated pixi environment or a container
  (Story 148.3). The recipe lanes' ``setup-miniconda`` ``python-version`` is the Python a recipe is built for, a
  per-build choice, and is not the estate's;

- ten ``src/shared/packages/pyforge-*/pyproject.toml``: ``[tool.ruff]
  target-version``, ``[tool.mypy] python_version``, and ``[project]
  requires-python`` lower bound;
- nine ``src/shared/packages/django-*/pyproject.toml``: ``[tool.ruff]
  target-version`` and ``requires-python`` lower bound (no mypy required);
- ``src/platform/pyproject.toml``: ``[tool.ruff] target-version`` and
  ``[tool.mypy] python_version`` (no ``[project]`` table);
Then, against the declared ``X.Y`` (the minor version):

- every ``src/shared/packages/pyforge-*/pixi.toml``: the ``python`` lower bound
  of ``[package.host-dependencies]`` and of ``[package.run-dependencies]`` (the
  floor ``pixi-build-python`` builds and installs each package against; Story
  124.3, decision D6). A drift names the file.

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


INTERPRETER_FEATURE = "interpreter"
ESTATE_PYTHON_ACTION = "./.github/actions/setup-estate-python"
_DECLARED_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.\*$")
_LOCK_ENV_RE = re.compile(r"^  ([A-Za-z0-9_-]+):$")
_LOCK_PLATFORM_RE = re.compile(r"^      ([A-Za-z0-9_-]+):$")
_LOCK_PYTHON_RE = re.compile(r"/python-(\d+\.\d+\.\d+)-[^/]*\.(?:conda|tar\.bz2)$")
_JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
_RUNS_PYTHON_RE = re.compile(r"^(?:python3?)(?:\s|$)")


def declared_python(data: dict) -> str | None:
    """``X.Y.Z`` from ``[feature.interpreter.dependencies] python = "X.Y.Z.*"``, or ``None``."""
    feature = data.get("feature", {}).get(INTERPRETER_FEATURE, {})
    spec = _python_spec(feature.get("dependencies") if isinstance(feature, dict) else None)
    m = _DECLARED_RE.match(spec or "")
    return ".".join(m.groups()) if m else None


def interpreter_minor() -> tuple[int, int] | None:
    data = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
    version = declared_python(data)
    if version is None:
        return None
    major, minor, _ = version.split(".")
    return int(major), int(minor)


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


def _python_spec(table: object) -> str | None:
    """The ``python`` entry of a pixi dependency table, as a spec string (``None`` when absent)."""
    if not isinstance(table, dict) or "python" not in table:
        return None
    entry = table["python"]
    if isinstance(entry, dict):
        entry = entry.get("version")
    return None if entry is None else str(entry)


def findings_for_package_manifest(pixi_toml: Path, minor: tuple[int, int]) -> list[str]:
    """A package ``pixi.toml``'s host and run ``python`` floors against the interpreter (Story 124.3)."""
    data = tomllib.loads(pixi_toml.read_text(encoding="utf-8"))
    package = data.get("package", {})
    want_floor = f">={minor[0]}.{minor[1]}"
    out: list[str] = []
    for table in ("host-dependencies", "run-dependencies"):
        spec = _python_spec(package.get(table) if isinstance(package, dict) else None)
        if spec is None:
            out.append(f"[package.{table}] has no python")
            continue
        m = _REQ_RE.search(spec)
        if not m:
            out.append(f"[package.{table}] python = {spec!r} has no parseable lower bound")
        elif (int(m.group(1)), int(m.group(2))) != minor:
            out.append(f"[package.{table}] python = {spec!r}, interpreter floor is {want_floor}")
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


def _dependency_tables(name: str, table: dict) -> list[tuple[str, object]]:
    """A feature's (or the default feature's) dependency tables, its per-target ones included."""
    out: list[tuple[str, object]] = [(f"[{name}dependencies]", table.get("dependencies"))]
    targets = table.get("target")
    if isinstance(targets, dict):
        for target, body in targets.items():
            if isinstance(body, dict):
                out.append((f"[{name}target.{target}.dependencies]", body.get("dependencies")))
    return out


def findings_for_workspace(data: dict) -> list[str]:
    """``python`` is declared once, in the interpreter feature, and every environment takes it (Story 148.1)."""
    out: list[str] = []
    tables = _dependency_tables("", data)
    for feature, body in data.get("feature", {}).items():
        if feature != INTERPRETER_FEATURE and isinstance(body, dict):
            tables.extend(_dependency_tables(f"feature.{feature}.", body))
    for label, table in tables:
        if _python_spec(table) is not None:
            out.append(f"{label} declares python; only [feature.{INTERPRETER_FEATURE}.dependencies] may")
    for env, body in data.get("environments", {}).items():
        features = body if isinstance(body, list) else body.get("features", []) if isinstance(body, dict) else []
        if INTERPRETER_FEATURE not in features:
            out.append(f"environment {env!r} does not list the {INTERPRETER_FEATURE!r} feature")
    return out


def lock_pythons(lock_text: str) -> dict[tuple[str, str], str]:
    """``(environment, platform) -> python version`` from ``pixi.lock``'s environments section."""
    out: dict[tuple[str, str], str] = {}
    env = platform = None
    inside = False
    for line in lock_text.splitlines():
        if line.startswith("environments:"):
            inside = True
            continue
        if line.startswith("packages:"):
            break
        if not inside:
            continue
        if m := _LOCK_ENV_RE.match(line):
            env, platform = m.group(1), None
        elif m := _LOCK_PLATFORM_RE.match(line):
            platform = m.group(1)
        elif env and platform and (m := _LOCK_PYTHON_RE.search(line.strip())):
            out[(env, platform)] = m.group(1)
    return out


def findings_for_lock(lock_text: str, version: str, environments: list[str]) -> list[str]:
    """Every environment resolves the declared python on every platform it locks (Story 148.1)."""
    resolved = lock_pythons(lock_text)
    out = [
        f"{env} on {platform} resolves python {got}, pixi.toml declares {version}"
        for (env, platform), got in sorted(resolved.items())
        if got != version
    ]
    locked = {env for env, _ in resolved}
    out.extend(f"environment {env!r} has no python in pixi.lock" for env in environments if env not in locked)
    return out


def _steps(lines: list[str], start: int) -> list[list[str]]:
    """The step items of the ``steps:`` list that begins after ``lines[start]``."""
    steps: list[list[str]] = []
    item_indent = None
    for line in lines[start + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            if steps:
                steps[-1].append(line)
            continue
        indent = len(line) - len(line.lstrip())
        if item_indent is None and line.lstrip().startswith("- "):
            item_indent = indent
        if item_indent is None or indent < item_indent:
            break
        if indent == item_indent and line.lstrip().startswith("- "):
            steps.append([line])
        elif steps:
            steps[-1].append(line)
    return steps


def _run_lines(step: list[str]) -> list[str]:
    """The commands of a step's ``run:``, one per line, comments and blanks dropped."""
    text = [line.strip() for line in step]
    for i, line in enumerate(text):
        key = line.removeprefix("- ")
        if key.startswith("run:"):
            body = key[4:].strip()
            lines = text[i + 1 :] if body in ("|", ">", "|-", ">-", "") else [body]
            commands: list[str] = []
            continued = False
            for line in lines:
                if line and not line.startswith("#") and not continued:
                    commands.append(line)
                continued = line.endswith("\\")
            return commands
    return []


def _activating_actions(actions_dir: Path) -> set[str]:
    """Local composite actions that leave an interpreter on PATH for the steps after them."""
    out: set[str] = set()
    for action in sorted(actions_dir.glob("*/action.yml")):
        text = action.read_text(encoding="utf-8")
        if "activate-environment:" in text or "actions/setup-python@" in text:
            out.add(f"./.github/actions/{action.parent.name}")
    return out


def findings_for_workflow(path: Path, rel: str, activating: set[str]) -> list[str]:
    """Python in a workflow or action comes from the declaration (Story 148.3)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for number, line in enumerate(lines, 1):
        stripped = line.strip().removeprefix("- ")
        if stripped.startswith("uses: actions/setup-python@"):
            out.append(f"{rel}:{number} sets Python up with actions/setup-python; use {ESTATE_PYTHON_ACTION}")
    if path.name == "action.yml":
        return out
    job = None
    container = False
    for index, line in enumerate(lines):
        if m := _JOB_RE.match(line):
            job, container = m.group(1), False
        elif job and line.startswith("    container:"):
            container = True
        elif job and line.strip() == "steps:":
            ready = container
            for step in _steps(lines, index):
                text = "\n".join(step)
                uses = [s.strip().removeprefix("- ").removeprefix("uses:").strip() for s in step
                        if s.strip().removeprefix("- ").startswith("uses:")]
                if any(u in activating or u == ESTATE_PYTHON_ACTION for u in uses) or (
                    any(u.startswith("prefix-dev/setup-pixi@") for u in uses) and "activate-environment:" in text
                ):
                    ready = True
                if ready or "docker " in text:
                    continue
                if any(_RUNS_PYTHON_RE.match(c) for c in _run_lines(step)):
                    out.append(f"{rel}: job {job!r} runs python before it sets up the estate's Python")
    return out


def main() -> int:
    workspace = tomllib.loads((ROOT / "pixi.toml").read_text(encoding="utf-8"))
    version = declared_python(workspace)
    minor = interpreter_minor()
    if version is None or minor is None:
        print(
            f"[target-version] could-not-run -- pixi.toml has no python = \"X.Y.Z.*\" under "
            f"[feature.{INTERPRETER_FEATURE}.dependencies]"
        )
        return 2
    environments = list(workspace.get("environments", {}))
    if not environments:
        print("[target-version] could-not-run -- pixi.toml has no [environments]")
        return 2
    lock = ROOT / "pixi.lock"
    if not lock.is_file():
        print("[target-version] could-not-run -- pixi.lock is missing")
        return 2
    github = ROOT / ".github"
    workflow_files = sorted((github / "workflows").glob("*.yml")) + sorted((github / "actions").glob("*/action.yml"))
    estate_action = github / "actions" / "setup-estate-python" / "action.yml"
    if not estate_action.is_file():
        print(f"[target-version] could-not-run -- {ESTATE_PYTHON_ACTION}/action.yml is missing")
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
    pyforge_manifests = sorted(PACKAGES_DIR.glob("pyforge-*/pixi.toml"))
    if len(pyforge_manifests) < 10:
        print(
            f"[target-version] could-not-run -- expected ten pyforge-* package pixi.toml files, "
            f"found {len(pyforge_manifests)}"
        )
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
    for manifest in pyforge_manifests:
        for f in findings_for_package_manifest(manifest, minor):
            print(f"[target-version] drift -- {manifest.relative_to(ROOT).as_posix()}: {f}")
            total += 1
    for f in findings_for_workspace(workspace):
        print(f"[target-version] drift -- pixi.toml: {f}")
        total += 1
    for f in findings_for_lock(lock.read_text(encoding="utf-8"), version, environments):
        print(f"[target-version] drift -- pixi.lock: {f}")
        total += 1
    activating = _activating_actions(github / "actions")
    for path in workflow_files:
        if path == estate_action:
            continue
        for f in findings_for_workflow(path, activating=activating, rel=path.relative_to(ROOT).as_posix()):
            print(f"[target-version] drift -- {f}")
            total += 1

    if total:
        print(
            f"[target-version] {total} finding(s) across "
            f"{len(pyforge_pkgs)} pyforge-*, {len(django_pkgs)} django-*, src/platform and "
            f"{len(pyforge_manifests)} package pixi.toml files, pixi.toml, pixi.lock and the workflows; "
            f"python {version}"
        )
        return 1
    print(
        f"[target-version] ok -- python {version} is declared once and every one of {len(environments)} "
        f"environments locks it; {len(workflow_files)} workflow and action files set Python up only through "
        f"{ESTATE_PYTHON_ACTION}; {len(pyforge_pkgs)} pyforge-*, {len(django_pkgs)} django-*, "
        f"and src/platform target py{minor[0]}{minor[1]} / {minor[0]}.{minor[1]}, and "
        f"{len(pyforge_manifests)} package pixi.toml files hold python >={minor[0]}.{minor[1]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
