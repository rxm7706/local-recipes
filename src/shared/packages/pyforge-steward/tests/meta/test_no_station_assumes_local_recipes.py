"""Steward Story 63.6 (spec-pyforge-steward CAP-152): no station code assumes
the `local-recipes` environment at runtime.

Operator ruling 2026-09-20: `local-recipes` is the recipe factory -- 10 GB,
"much larger and too big to be used as the default runtime environment" --
and only `pyforge-guild`, the bare-minimum default, exists where station
code runs. A shell-out to `pixi run -e local-recipes ...` or a path under
`.pixi/envs/local-recipes/...` therefore works only on a machine that
happens to carry the factory env beside the checkout (the primary checkout
did; every fresh worktree and every dispatch clone did not -- the
2026-09-20 audit found marshal `cli/watch.py`, `core/gate.py`,
`adapters/scribe_cli.py`, herald `deck_pipeline.py`, `sync_all.py` and
steward `provision.py`, `upgrade.py`, `suite.py` all doing it).

The guard reads every station package's `src/` with `ast` and inspects
STRING CONSTANTS only: an argv element, a path literal or a message that
names the factory env is a finding; a docstring is prose about the past and
is exempt (`ast.get_docstring` on module / class / function bodies). Comments
never reach the AST. `urn:local-recipes:...` schema ids and the GitHub
`rxm7706/local-recipes` repo slug are the repository's NAME, not the env,
and are excluded by pattern.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
ROOT = next(p for p in _HERE.parents if (p / "pixi.toml").is_file() and (p / "AGENTS.md").is_file())
PACKAGES = ROOT / "src" / "shared" / "packages"

#: A string constant that reaches the factory env at runtime.
_RUNTIME_REF = re.compile(
    r"(\.pixi/envs/local-recipes|(^|\s|\")-e[\s\",]+local-recipes\b|pixi\s+install\s+-e\s+local-recipes\b)"
)
#: The repository's own name in a schema id or a GitHub slug -- not the env.
_NAME_NOT_ENV = re.compile(r"(urn:local-recipes:|rxm7706/local-recipes|github\.com/[^/]+/local-recipes)")


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Line numbers of every docstring constant in ``tree``."""
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                lines.add(body[0].value.lineno)
    return lines


def _runtime_offenders(py_file: Path) -> list[tuple[int, str]]:
    text = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:  # pragma: no cover - a broken file is another test's finding
        return []
    exempt = _docstring_nodes(tree)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        # An argv list holds `"-e"` and `"local-recipes"` as two constants: flag the
        # pair. A bare `"local-recipes"` elsewhere is usually the REPO or cutover-root
        # NAME (`CUTOVER_VARIANTS = ("local-recipes", "foundry")`), not the env.
        if isinstance(node, (ast.List, ast.Tuple)):
            elts = node.elts
            for a, b in zip(elts, elts[1:]):
                if (isinstance(a, ast.Constant) and a.value == "-e" and isinstance(b, ast.Constant)
                        and b.value == "local-recipes" and b.lineno not in exempt):
                    found.append((b.lineno, "-e local-recipes (argv)"))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.lineno not in exempt:
            value = node.value
            if "local-recipes" in value and _RUNTIME_REF.search(value) and not _NAME_NOT_ENV.search(value):
                found.append((node.lineno, value.strip()[:100]))
    return sorted(set(found))


def _station_src_dirs() -> list[Path]:
    return sorted(p / "src" for p in PACKAGES.glob("pyforge-*") if (p / "src").is_dir())


def test_every_station_has_a_src_tree_to_scan() -> None:
    assert len(_station_src_dirs()) >= 10, _station_src_dirs()


@pytest.mark.parametrize("src_dir", _station_src_dirs(), ids=lambda p: p.parent.name)
def test_no_station_src_reaches_the_local_recipes_env_at_runtime(src_dir: Path) -> None:
    offenders: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        for lineno, value in _runtime_offenders(py_file):
            offenders.append(f"{py_file.relative_to(ROOT)}:{lineno}: {value!r}")
    assert not offenders, (
        "station code reaches the `local-recipes` env, which does not exist at runtime "
        "(only `pyforge-guild` does -- operator ruling 2026-09-20, spec-pyforge-steward CAP-152); "
        "shell to `-e pyforge-guild` (register the task in `guild-tasks` with its deps in the Guild feature) "
        "or read `.pixi/envs/pyforge-guild/...`:\n  " + "\n  ".join(offenders)
    )


def test_guard_sees_an_argv_and_a_path_but_not_a_docstring(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        '"""Run: pixi run -e local-recipes publish -- prose about the past."""\n'
        'ARGV = ["pixi", "run", "-e", "local-recipes", "bmad-loop", "list"]\n'
        'BIN = ".pixi/envs/local-recipes/bin"\n'
        'SCHEMA_ID = "urn:local-recipes:pyforge-doctor:report-schema"\n'
        'REPO = "rxm7706/local-recipes"\n'
        'def f():\n    """pixi install -e local-recipes -- also prose."""\n    return "-e local-recipes"\n',
        encoding="utf-8",
    )
    hits = sorted(line for line, _ in _runtime_offenders(sample))
    assert hits == [2, 3, 8], hits
