"""Story 104.1: cfe-regression-net runs when a repo-root script its tests load changes.

The conda-forge-expert meta suite (`.claude/skills/conda-forge-expert/tests/`, run by
`.github/workflows/cfe-regression-net.yml` as `test-ci`) loads several repo-root scripts by path,
e.g. ``REPO_ROOT / "scripts" / "fleet_picture.py"``. The workflow fired only on the skill tree and the
pixi files, so doctor Story 45.1's change to ``scripts/fleet_picture.py`` broke three of those tests
on 2026-10-14 and nothing ran them until an unrelated PR touched ``pixi.toml`` (mason Story 31.1
fixed the tests). This test derives, from the tests' own source, every ``scripts/`` file they join
onto the repository root, and asserts both of the workflow's path filters cover each one. Steward
owns the lane (``docs/governance/ci-surfaces.yaml`` row ``cfe-regression-net``) and its selection
(``spec-pyforge-steward`` CAP-159, Story 71.2: pr-preflight reads the same filters).

Data the tests read (``recipes/**``, ``conda_build_config.yaml``) is deliberately out of scope: a
filter on it would run the lane on every recipe PR. Station packages the tests import are installed
into the lane's environment and are judged by their own suites.
"""

from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath

import yaml

REPO_ROOT = Path(__file__).resolve().parents[6]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "cfe-regression-net.yml"
CFE_TESTS = REPO_ROOT / ".claude" / "skills" / "conda-forge-expert" / "tests"


def _parents_index(node: ast.AST) -> int | None:
    """N for an expression ``Path(__file__).resolve().parents[N]`` (or without ``.resolve()``)."""
    if not (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)):
        return None
    value = node.value
    if not (isinstance(value, ast.Attribute) and value.attr == "parents"):
        return None
    inner = value.value
    if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr == "resolve":
        inner = inner.func.value
    if not (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "Path"):
        return None
    arg = inner.args[0] if inner.args else None
    if not (isinstance(arg, ast.Name) and arg.id == "__file__"):
        return None
    index = node.slice.value
    return index if isinstance(index, int) else None


def _root_names(tree: ast.Module, test_file: Path) -> set[str]:
    """Module-level names bound to this repository's root."""
    names = set()
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            index = _parents_index(stmt.value)
            if index is not None and test_file.resolve().parents[index] == REPO_ROOT:
                names.add(stmt.targets[0].id)
    return names


def _joined_segments(node: ast.AST) -> tuple[str | None, list[str]]:
    """For ``NAME / "a" / "b"``: ("NAME", ["a", "b"]); otherwise (None, [])."""
    segments: list[str] = []
    while isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        if not (isinstance(node.right, ast.Constant) and isinstance(node.right.value, str)):
            return None, []
        segments.insert(0, node.right.value)
        node = node.left
    if isinstance(node, ast.Name):
        return node.id, segments
    return None, []


def loaded_root_scripts() -> set[str]:
    """Every ``scripts/...`` file under the repository root that a CFE test joins onto the root."""
    found = set()
    for test_file in sorted(CFE_TESTS.rglob("*.py")):
        tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
        roots = _root_names(tree, test_file)
        if not roots:
            continue
        for node in ast.walk(tree):
            name, segments = _joined_segments(node)
            if name not in roots or not segments:
                continue
            relative = "/".join(part for segment in segments for part in segment.split("/") if part)
            if relative.startswith("scripts/") and (REPO_ROOT / relative).is_file():
                found.add(relative)
    return found


def _filter_paths(trigger: str) -> list[str]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    on = document.get("on", document.get(True))  # PyYAML reads a bare `on:` key as True
    return list(on[trigger]["paths"])


def _covered(path: str, globs: list[str]) -> bool:
    return any(PurePosixPath(path).full_match(glob) for glob in globs)


def test_the_derivation_finds_the_scripts_the_tests_load() -> None:
    scripts = loaded_root_scripts()
    # Blindness guard: on 2026-10-14 the CFE tests loaded these five by path.
    assert {
        "scripts/fleet_picture.py",
        "scripts/fleet_scan.py",
        "scripts/loop_stall_check.py",
        "scripts/spec_surface_check.py",
        "scripts/unpushed_work_check.py",
    } <= scripts, sorted(scripts)


def test_both_filters_cover_every_loaded_script() -> None:
    scripts = sorted(loaded_root_scripts())
    for trigger in ("pull_request", "push"):
        globs = _filter_paths(trigger)
        missing = [path for path in scripts if not _covered(path, globs)]
        assert not missing, f"{trigger}: cfe-regression-net does not fire on {missing}; add them to its paths"


def test_a_filter_missing_a_script_is_reported() -> None:
    globs = [glob for glob in _filter_paths("push") if glob != "scripts/fleet_picture.py"]
    assert not _covered("scripts/fleet_picture.py", globs)
