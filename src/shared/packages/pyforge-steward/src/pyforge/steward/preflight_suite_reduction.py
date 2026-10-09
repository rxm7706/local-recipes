"""Shrink station suite lanes when the coverage gate already runs unit tests (Story 71.4)."""

from __future__ import annotations

import ast
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COVERAGE_PARITY_NOTE = (
    "Suite reduction skips tests the gate run covers under --cov; gate PYTHONPATH "
    "includes scripts/ and coverage tracing differs from CI's station job."
)

_STATION_TEST_RE = re.compile(r"^pyforge-([a-z]+)-test$")
_STATION_GATE_RE = re.compile(r"^pyforge-([a-z]+)-coverage-gate$")


PYTEST_EXIT_NO_TESTS_COLLECTED = 5


@dataclass(frozen=True)
class ReducedSuiteSegment:
    """One pytest invocation in a reduced suite lane (Story 71.9)."""

    label: str  # ``rest-of-task`` | ``gate-dirs-complement``
    argv: list[str]  # argv after ``pixi run --frozen -e <env> --``


@dataclass(frozen=True)
class SuiteLaneOverride:
    """How to run a suite lane instead of its pixi task verbatim."""

    segments: tuple[ReducedSuiteSegment, ...]
    journal: dict[str, Any]


@dataclass(frozen=True)
class _ParsedPytest:
    prefix: list[str]
    test_paths: list[str]
    marker_expr: str | None
    suffix: list[str]


def _find_task(pixi_data: dict[str, Any], task_name: str) -> dict[str, Any] | None:
    for feature in pixi_data.get("feature", {}).values():
        tasks = feature.get("tasks")
        if isinstance(tasks, dict) and task_name in tasks:
            return tasks[task_name]
    return None


def _task_cmd(pixi_data: dict[str, Any], task_name: str) -> str | None:
    task = _find_task(pixi_data, task_name)
    if task is None:
        return None
    cmd = task.get("cmd")
    return cmd if isinstance(cmd, str) else None


def _task_env(pixi_data: dict[str, Any], task_name: str) -> dict[str, str]:
    task = _find_task(pixi_data, task_name)
    if task is None:
        return {}
    raw = task.get("env")
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _parse_single_pytest(cmd: str) -> _ParsedPytest | None:
    if "&&" in cmd:
        return None
    parts = shlex.split(cmd)
    try:
        idx = parts.index("pytest")
    except ValueError:
        return None
    prefix = parts[:idx]
    rest = parts[idx + 1 :]
    test_paths: list[str] = []
    marker_expr: str | None = None
    suffix: list[str] = []
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in ("-m", "--markers") and i + 1 < len(rest):
            marker_expr = rest[i + 1]
            i += 2
            continue
        if tok.startswith("-"):
            if tok in ("-q", "-qq", "-v", "-vv", "-x", "--maxfail", "-n", "--dist"):
                suffix.append(tok)
                if tok in ("--maxfail", "-n", "--dist") and i + 1 < len(rest):
                    suffix.append(rest[i + 1])
                    i += 2
                    continue
                i += 1
                continue
            suffix.append(tok)
            i += 1
            continue
        test_paths.append(tok)
        i += 1
    if not test_paths:
        return None
    return _ParsedPytest(prefix=prefix, test_paths=test_paths, marker_expr=marker_expr, suffix=suffix)


def _scripts_top_level_modules(repo_root: Path) -> set[str]:
    scripts = repo_root / "scripts"
    if not scripts.is_dir():
        return set()
    return {p.stem for p in scripts.glob("*.py") if p.is_file() and p.name != "__init__.py"}


def _imports_scripts_module(path: Path, script_modules: set[str]) -> str | None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError, SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                if top in script_modules:
                    return f"{path}: import {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".", 1)[0]
                if top in script_modules:
                    return f"{path}: from {node.module} import ..."
            if node.level and any(isinstance(n, ast.alias) for n in node.names):
                return f"{path}: relative import from scripts"
    return None


def _scan_unit_meta_scripts_imports(repo_root: Path, station: str) -> str | None:
    pkg = repo_root / "src" / "shared" / "packages" / f"pyforge-{station}"
    script_modules = _scripts_top_level_modules(repo_root)
    if not script_modules:
        return None
    for sub in ("unit", "meta"):
        tests_dir = pkg / "tests" / sub
        if not tests_dir.is_dir():
            continue
        for py_file in tests_dir.rglob("*.py"):
            hit = _imports_scripts_module(py_file, script_modules)
            if hit:
                return hit
    return None


def _normalize_path_str(repo_root: Path, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _discover_test_subdirs(repo_root: Path, task_paths: list[str]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for raw in task_paths:
        base = _normalize_path_str(repo_root, raw)
        if not base.is_dir():
            continue
        if list(base.glob("test_*.py")) or list(base.glob("*_test.py")):
            if base not in seen:
                seen.add(base)
                found.append(base)
        roots = [base]
        nested = base / "tests"
        if nested.is_dir() and nested not in roots:
            roots.append(nested)
        for root in roots:
            if root.name != "tests":
                continue
            for child in sorted(root.iterdir()):
                if not child.is_dir() or child in seen:
                    continue
                if list(child.glob("test_*.py")) or list(child.glob("*_test.py")):
                    seen.add(child)
                    found.append(child)
    return found


def _gate_paths_resolved(repo_root: Path, gate_run: dict[str, Any]) -> list[Path]:
    out: list[Path] = []
    for raw in gate_run.get("test_paths", []):
        if not isinstance(raw, str):
            continue
        path = _normalize_path_str(repo_root, raw)
        if path.is_dir():
            out.append(path)
    return out


def _complement_marker(task_marker: str | None, gate_marker: str) -> str | None:
    if task_marker == gate_marker:
        return None
    if task_marker:
        return f"({task_marker}) and not ({gate_marker})"
    return "slow"


def _pytest_argv_from_parsed(
    parsed: _ParsedPytest,
    repo_root: Path,
    *,
    test_dirs: list[Path],
    marker_expr: str | None,
) -> list[str]:
    rel = [str(p.relative_to(repo_root)) if p.is_relative_to(repo_root) else str(p) for p in test_dirs]
    argv = [*parsed.prefix, "pytest", *rel, *parsed.suffix]
    if marker_expr:
        argv.extend(["-m", marker_expr])
    return argv


def _build_reduced_segments(
    parsed: _ParsedPytest, repo_root: Path, gate_run: dict[str, Any]
) -> list[ReducedSuiteSegment] | None:
    gate_dirs = _gate_paths_resolved(repo_root, gate_run)
    if not gate_dirs:
        return None
    gate_marker = str(gate_run.get("marker_expr", "not slow"))
    all_dirs = _discover_test_subdirs(repo_root, parsed.test_paths)
    if not all_dirs:
        all_dirs = [_normalize_path_str(repo_root, p) for p in parsed.test_paths]
    gate_set = {p.resolve() for p in gate_dirs}
    other_dirs = [d for d in all_dirs if d.resolve() not in gate_set]
    segments: list[ReducedSuiteSegment] = []
    if other_dirs:
        other_argv = _pytest_argv_from_parsed(
            parsed, repo_root, test_dirs=other_dirs, marker_expr=parsed.marker_expr
        )
        segments.append(ReducedSuiteSegment("rest-of-task", other_argv))
    complement = _complement_marker(parsed.marker_expr, gate_marker)
    if complement is not None:
        gate_argv = _pytest_argv_from_parsed(
            parsed, repo_root, test_dirs=gate_dirs, marker_expr=complement
        )
        segments.append(ReducedSuiteSegment("gate-dirs-complement", gate_argv))
    if not segments:
        return None
    return segments


def _build_reduced_shell_cmd(parsed: _ParsedPytest, repo_root: Path, gate_run: dict[str, Any]) -> str | None:
    """Join reduced segments for collect-only helpers (tests and partition checks)."""
    built = _build_reduced_segments(parsed, repo_root, gate_run)
    if not built:
        return None
    return " && ".join(shlex.join(seg.argv) for seg in built)


def _gate_driver_argv(gate_cmd: str) -> list[str] | None:
    parts = shlex.split(gate_cmd)
    try:
        idx = parts.index("scripts/coverage_gates_ci.py")
    except ValueError:
        try:
            idx = next(i for i, p in enumerate(parts) if p.endswith("coverage_gates_ci.py"))
        except StopIteration:
            return None
    driver = parts[: idx + 1]
    rest = parts[idx + 1 :]
    out = [*driver, "--plan", *rest]
    return out


def _read_gate_plan(repo_root: Path, gate_task: str, pixi_data: dict[str, Any]) -> dict[str, Any] | None:
    gate_cmd = _task_cmd(pixi_data, gate_task)
    if not gate_cmd:
        return None
    argv = _gate_driver_argv(gate_cmd)
    if argv is None:
        return None
    env = {**os.environ, **_task_env(pixi_data, gate_task)}
    if argv and argv[0] == "python":
        run_argv = [sys.executable, *argv[1:]]
    else:
        run_argv = argv
    proc = subprocess.run(
        run_argv,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _unit_run_for_station(plan: dict[str, Any], station: str) -> dict[str, Any] | None:
    runs = plan.get("runs")
    if not isinstance(runs, list):
        return None
    for run in runs:
        if isinstance(run, dict) and run.get("station") == station and run.get("suite") == "unit":
            return run
    return None


def derive_suite_lane_override(
    repo_root: Path,
    *,
    station: str,
    pixi_data: dict[str, Any],
    gate_plan: dict[str, Any] | None,
) -> SuiteLaneOverride | None:
    """Return a reduced suite command, or ``None`` to run the pixi task whole."""
    test_task = f"pyforge-{station}-test"
    cmd = _task_cmd(pixi_data, test_task)
    if not cmd:
        return None
    if gate_plan is None:
        return None
    gate_run = _unit_run_for_station(gate_plan, station)
    if gate_run is None:
        return None
    scripts_hit = _scan_unit_meta_scripts_imports(repo_root, station)
    if scripts_hit:
        return None
    parsed = _parse_single_pytest(cmd)
    if parsed is None:
        return None
    reduced = _build_reduced_segments(parsed, repo_root, gate_run)
    if not reduced:
        return None
    return SuiteLaneOverride(
        segments=tuple(reduced),
        journal={
            "suite_reduction": True,
            "suite_reduction_reason": "coverage gate unit run overlaps station suite",
            "coverage_parity_note": COVERAGE_PARITY_NOTE,
            "gate_station": station,
            "gate_suite": "unit",
        },
    )


def reduction_skip_journal(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "suite_reduction": False,
        "suite_reduction_reason": reason,
        **extra,
    }


def build_suite_lane_overrides(
    repo_root: Path,
    *,
    selected_task_names: set[str],
    pixi_data: dict[str, Any],
) -> dict[str, SuiteLaneOverride | dict[str, Any]]:
    """Map ``pyforge-<s>-test`` task names to overrides or skip journals."""
    overrides: dict[str, SuiteLaneOverride | dict[str, Any]] = {}
    gate_tasks_selected = {t for t in selected_task_names if _STATION_GATE_RE.match(t)}
    if not gate_tasks_selected:
        return overrides

    for task in selected_task_names:
        match = _STATION_TEST_RE.match(task)
        if not match:
            continue
        station = match.group(1)
        gate_task = f"pyforge-{station}-coverage-gate"
        if gate_task not in selected_task_names:
            overrides[task] = reduction_skip_journal("coverage gate lane not selected")
            continue
        gate_cmd = _task_cmd(pixi_data, gate_task)
        if not gate_cmd:
            overrides[task] = reduction_skip_journal("missing coverage gate task cmd")
            continue
        if "&&" in (_task_cmd(pixi_data, task) or ""):
            overrides[task] = reduction_skip_journal("station test task is not a single pytest invocation")
            continue
        gate_plan = _read_gate_plan(repo_root, gate_task, pixi_data)
        if gate_plan is None:
            overrides[task] = reduction_skip_journal("coverage gate --plan failed or returned unparsable JSON")
            continue
        scripts_hit = _scan_unit_meta_scripts_imports(repo_root, station)
        if scripts_hit:
            overrides[task] = reduction_skip_journal(f"tests import scripts/ module ({scripts_hit})")
            continue
        override = derive_suite_lane_override(repo_root, station=station, pixi_data=pixi_data, gate_plan=gate_plan)
        if override is None:
            parsed = _parse_single_pytest(_task_cmd(pixi_data, task) or "")
            if parsed is None:
                overrides[task] = reduction_skip_journal("station test task is not a single pytest invocation")
            else:
                overrides[task] = reduction_skip_journal("no reducible overlap with gate unit plan")
        else:
            overrides[task] = override
    return overrides


def _segment_without_quiet_flags(segment: str) -> str:
    parts = shlex.split(segment)
    filtered = [p for p in parts if p not in ("-q", "-qq")]
    return shlex.join(filtered)


def collect_pytest_node_ids(repo_root: Path, shell_cmd: str, *, env: dict[str, str] | None = None) -> set[str]:
    """``pytest --collect-only -q`` node ids for a shell pytest command."""
    ids: set[str] = set()
    segments = [part.strip() for part in shell_cmd.split("&&")]
    run_env = {**os.environ, **(env or {})}
    for segment in segments:
        if not segment:
            continue
        stripped = _segment_without_quiet_flags(segment)
        collect_cmd = re.sub(r"\bpytest\b", "pytest --collect-only -q", stripped, count=1)
        proc = subprocess.run(
            ["bash", "-lc", collect_cmd],
            cwd=repo_root,
            env=run_env,
            capture_output=True,
            text=True,
        )
        if proc.returncode == PYTEST_EXIT_NO_TESTS_COLLECTED:
            continue
        if proc.returncode != 0:
            raise RuntimeError(proc.stdout + proc.stderr)
        for line in proc.stdout.splitlines():
            line = line.strip()
            if "::" in line and not line.startswith("="):
                ids.add(line.split()[0] if line.split() else line)
    return ids


def gate_collect_shell(repo_root: Path, gate_run: dict[str, Any]) -> str:
    paths = gate_run.get("test_paths", [])
    marker = str(gate_run.get("marker_expr", "not slow"))
    rel = [str(p) for p in paths if isinstance(p, str)]
    return shlex.join(["pytest", *rel, "-q", "-m", marker])
