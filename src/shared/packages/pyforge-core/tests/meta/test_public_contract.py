"""Meta test -- the leaf's public contract and its source agree, both ways (Story 117.4, spec-pyforge-core:CAP-12).

``contract.md`` beside ``spec-pyforge-core``'s ``SPEC.md`` names every module of ``pyforge.core`` with the
capability that governs it, every public name a station may import, every environment variable the leaf reads or
sets, every feature-flag key it reads, every exit code it defines, its entry points and its Python floor, so a second
root can rebuild the leaf from Dream, memlog and Spec. This module derives each inventory from the source (an AST
scan of ``src/pyforge/core/*.py`` and the package's ``pyproject.toml``) and compares it with the contract both ways:
an item the source has and the contract lacks is reported as unlisted, an item the contract names and the source
lacks as missing from the source. Every message names the item.

What counts, read from the source:

* a module: every ``*.py`` under ``src/pyforge/core/`` but ``__init__`` (its ``__version__`` is not contract);
* a public name: a name a module binds at top level (``def``, ``class``, an assignment, a ``type`` alias, also
  inside a top-level ``if``, ``try`` or ``with``) with no leading underscore; an imported name is not one, and no
  ``__all__`` is consulted;
* an environment variable: an upper-case string, literal or through a module-level constant, that a module reads
  (``os.environ.get``, ``os.getenv``, ``os.environ[...]``, ``in os.environ``, ``.get`` on an expression holding
  ``os.environ``) or sets (``os.environ[...] =``, ``os.environ.update``, ``setdefault`` or ``pop``, a key of a dict
  passed as ``env=``, passed to a function whose name holds ``env``, or spreading ``**os.environ``);
* a feature-flag key: a string constant shaped ``pyforge.<x>`` or ``pyforge.<x>.<y>`` outside the leaf's own
  ``pyforge.core`` namespace; a ``pyforge.core.<x>`` string (the entry-point group, the example hook spec) is not a
  flag key, and must appear somewhere in the contract;
* an exit code: a top-level ``EXIT_<NAME> = <int>``;
* a schema id: a string constant shaped ``urn:<...>``;
* an entry point: each ``[project.scripts]`` entry (group ``console_scripts``), ``[project.gui-scripts]`` entry
  (``gui_scripts``) and ``[project.entry-points.<group>]`` entry;
* the Python floor: ``[project] requires-python``.

What it reads from the contract: the ``### `pyforge.core.<module>``` headings under ``## Modules``, and in each the
backticked tokens of the paragraphs that open ``Public names:`` and ``Estate-bound constants:``; the backticked cells
of the table rows under ``## Environment variables`` (variable, role, modules), ``## Feature-flag keys`` (key,
modules), ``## Exit codes`` (name, value, modules) and ``## Entry points`` (group, name, target); the backticked
``>=`` token under ``## Python floor``. Every module section opens a ``Governed by:`` paragraph, and every
``spec-<x>:CAP-n`` or ``fnd:CAP-n`` the contract cites must be a capability its Spec defines. An estate-bound
constant must be a public name of its module. Other prose is not read.

The module reads the Spec folder (and, for the citations, other Specs), so it is ``live_tree``; both directions are
proven on synthetic input, kind by kind, so neither check is vacuous.
"""

from __future__ import annotations

import ast
import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.live_tree

# tests/meta/<file> -> parents[2] is the package. The repository root is derived in `_repo_root()`, never at import,
# so a copy of the package alone still collects this module (spec-pyforge-core:CAP-14).
PACKAGE_DIR = Path(__file__).resolve().parents[2]
SOURCE_DIR = PACKAGE_DIR / "src" / "pyforge" / "core"
PYPROJECT = PACKAGE_DIR / "pyproject.toml"
CONTRACT_RELATIVE = Path("_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/contract.md")

LEAF = "pyforge.core"
FOUNDRY_SPEC = "spec-python-foundry-cutover"  # the `fnd:` prefix (AGENTS.md, CHAIN-STANDARD section 0)

ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]*")
FLAG_KEY = re.compile(r"pyforge\.[a-z0-9_]+(?:\.[a-z0-9_]+)?")
SCHEMA_ID = re.compile(r"urn:\S+")
EXIT_NAME = re.compile(r"EXIT_[A-Z0-9_]+")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
FLOOR = re.compile(r">=\s*\d+(?:\.\d+)*")
TOKEN = re.compile(r"`([^`]+)`")
CITATION = re.compile(r"\b(spec-[a-z0-9-]+|fnd):CAP-(\d+)\b")
MODULE_HEADING = re.compile(r"### `pyforge\.core\.(\w+)`")
TABLE_SEPARATOR = re.compile(r"\|[\s:|-]+\|")

Item = tuple[str, str]


@dataclass(frozen=True)
class Source:
    """What the source has: ``(kind, item)`` pairs, plus the leaf-namespace strings the contract must mention."""

    items: frozenset[Item]
    leaf_strings: frozenset[str]


@dataclass(frozen=True)
class Contract:
    """What ``contract.md`` names."""

    items: frozenset[Item]
    estate: frozenset[tuple[str, str]]
    citations: tuple[str, ...]
    tokens: frozenset[str]
    problems: tuple[str, ...]


# -- the source ---------------------------------------------------------------------------------------------------


def _target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for element in target.elts for name in _target_names(element)]
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return []


def _top_level_names(body: list[ast.stmt]) -> list[str]:
    names: list[str] = []
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            names.extend(name for target in node.targets for name in _target_names(target))
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            names.extend(_target_names(node.target))
        elif isinstance(node, ast.TypeAlias):
            names.extend(_target_names(node.name))
        elif isinstance(node, ast.If):
            names.extend(_top_level_names(node.body) + _top_level_names(node.orelse))
        elif isinstance(node, (ast.Try, ast.TryStar)):
            nested = [*node.body, *node.orelse, *node.finalbody]
            nested.extend(statement for handler in node.handlers for statement in handler.body)
            names.extend(_top_level_names(nested))
        elif isinstance(node, ast.With):
            names.extend(_top_level_names(node.body))
    return names


def _constants(tree: ast.Module) -> dict[str, object]:
    """Module-level ``NAME = <literal>`` bindings, private ones included (an env read often goes through one)."""
    found: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node.value.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, ast.Constant)
        ):
            found[node.target.id] = node.value.value
    return found


def _string(node: ast.AST | None, constants: dict[str, object]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        value = constants.get(node.id)
        if isinstance(value, str):
            return value
    return None


def _is_os_environ(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _holds_os_environ(node: ast.AST) -> bool:
    return any(_is_os_environ(sub) for sub in ast.walk(node))


def _call_name(func: ast.expr) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _environment(tree: ast.Module, constants: dict[str, object]) -> set[tuple[str, str]]:
    """``(variable, role)`` pairs, the role ``read`` or ``set``."""
    found: set[tuple[str, str]] = set()

    def add(node: ast.AST | None, role: str) -> None:
        name = _string(node, constants)
        if name is not None and ENV_NAME.fullmatch(name):
            found.add((name, role))

    def add_keys(node: ast.AST) -> None:
        if isinstance(node, ast.Dict):
            for key in node.keys:
                add(key, "set")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "get" and _holds_os_environ(func.value) and node.args:
                add(node.args[0], "read")
            elif (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
                and node.args
            ):
                add(node.args[0], "read")
            elif (
                isinstance(func, ast.Attribute)
                and func.attr in {"update", "setdefault", "pop"}
                and _is_os_environ(func.value)
            ):
                if func.attr != "update" and node.args:
                    add(node.args[0], "set")
                for argument in node.args:
                    add_keys(argument)
            if "env" in _call_name(func).lower():
                for argument in node.args:
                    add_keys(argument)
            for keyword in node.keywords:
                if keyword.arg == "env":
                    add_keys(keyword.value)
        elif isinstance(node, ast.Subscript) and _is_os_environ(node.value):
            add(node.slice, "read" if isinstance(node.ctx, ast.Load) else "set")
        elif isinstance(node, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
            if any(_is_os_environ(comparator) for comparator in node.comparators):
                add(node.left, "read")
        elif isinstance(node, ast.Dict) and any(
            key is None and _is_os_environ(value) for key, value in zip(node.keys, node.values, strict=True)
        ):
            add_keys(node)
    return found


def derive_source(source_dir: Path, pyproject: Path) -> Source:
    """Every contract item the leaf's source and ``pyproject.toml`` have."""
    items: set[Item] = set()
    leaf_strings: set[str] = set()
    for path in sorted(source_dir.glob("*.py")):
        if path.stem == "__init__":
            continue
        module = f"{LEAF}.{path.stem}"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constants = _constants(tree)
        items.add(("module", module))
        items.update(("public name", f"{module}.{name}") for name in _top_level_names(tree.body) if name[:1] != "_")
        items.update(
            ("environment variable", f"{name} ({role}) in {module}") for name, role in _environment(tree, constants)
        )
        for name, value in constants.items():
            if EXIT_NAME.fullmatch(name) and isinstance(value, int) and not isinstance(value, bool):
                items.add(("exit code", f"{name} = {value} in {module}"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if FLAG_KEY.fullmatch(node.value):
                if node.value == LEAF or node.value.startswith(f"{LEAF}."):
                    leaf_strings.add(node.value)
                else:
                    items.add(("feature-flag key", f"{node.value} in {module}"))
            elif SCHEMA_ID.fullmatch(node.value):
                items.add(("schema id", f"{node.value} in {module}"))
    project: dict[str, Any] = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
    groups: dict[str, dict[str, str]] = {
        "console_scripts": project.get("scripts", {}),
        "gui_scripts": project.get("gui-scripts", {}),
        **project.get("entry-points", {}),
    }
    for group, entries in groups.items():
        items.update(("entry point", f"{group}: {name} = {target}") for name, target in entries.items())
    floor = project.get("requires-python")
    if isinstance(floor, str):
        items.add(("python floor", floor.replace(" ", "")))
    return Source(frozenset(items), frozenset(leaf_strings))


# -- the contract -------------------------------------------------------------------------------------------------


def _paragraphs(text: str) -> list[tuple[str, str | None, list[str]]]:
    """``(section, module, lines)`` per paragraph; ``module`` is set under a ``### `pyforge.core.<m>``` heading."""
    paragraphs: list[tuple[str, str | None, list[str]]] = []
    section = ""
    module: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            paragraphs.append((section, module, list(buffer)))
            buffer.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if line.startswith("## "):
            flush()
            section, module = line[3:].strip(), None
        elif line.startswith("### "):
            flush()
            match = MODULE_HEADING.fullmatch(stripped)
            module = f"{LEAF}.{match.group(1)}" if section == "Modules" and match else None
            paragraphs.append((section, module, []))  # the heading itself, so an empty section still counts
        elif not stripped:
            flush()
        else:
            buffer.append(line)
    flush()
    return paragraphs


def _rows(lines: list[str]) -> list[list[str]]:
    """The data rows of a table paragraph: a row whose first cell holds no backtick is a header."""
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or TABLE_SEPARATOR.fullmatch(stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if TOKEN.search(cells[0]):
            rows.append(cells)
    return rows


def _table_items(section: str, cells: list[str]) -> tuple[set[Item], list[str]]:
    tokens = [TOKEN.findall(cell) for cell in cells]
    width = {"Environment variables": 3, "Feature-flag keys": 2, "Exit codes": 3, "Entry points": 3}[section]
    if len(tokens) < width or not all(tokens[:width]):
        return set(), [f"malformed row under '## {section}' in contract.md: {' | '.join(cells)}"]
    first = tokens[0][0]
    if section == "Environment variables":
        role = tokens[1][0]
        return {("environment variable", f"{first} ({role}) in {module}") for module in tokens[2]}, []
    if section == "Feature-flag keys":
        return {("feature-flag key", f"{first} in {module}") for module in tokens[1]}, []
    if section == "Exit codes":
        return {("exit code", f"{first} = {tokens[1][0]} in {module}") for module in tokens[2]}, []
    return {("entry point", f"{first}: {tokens[1][0]} = {tokens[2][0]}")}, []


def parse_contract(text: str) -> Contract:
    """Every item ``contract.md`` names, read from the places the module docstring lists."""
    items: set[Item] = set()
    estate: set[tuple[str, str]] = set()
    problems: list[str] = []
    governed: set[str] = set()
    seen: list[str] = []
    for section, module, lines in _paragraphs(text):
        body = " ".join(line.strip() for line in lines)
        if section == "Modules" and module is not None:
            if not lines:
                if module in seen:
                    problems.append(f"duplicate section in contract.md: {module}")
                seen.append(module)
                items.add(("module", module))
            elif body.startswith("Governed by:"):
                governed.add(module)
            elif body.startswith("Public names:"):
                for token in TOKEN.findall(body):
                    if IDENTIFIER.fullmatch(token):
                        items.add(("public name", f"{module}.{token}"))
                    else:
                        problems.append(f"not a name under {module} 'Public names:' in contract.md: {token}")
            elif body.startswith("Estate-bound constants:"):
                for token in TOKEN.findall(body):
                    if IDENTIFIER.fullmatch(token):
                        estate.add((module, token))
                    elif SCHEMA_ID.fullmatch(token):
                        items.add(("schema id", f"{token} in {module}"))
        elif section in {"Environment variables", "Feature-flag keys", "Exit codes", "Entry points"}:
            for cells in _rows(lines):
                found, malformed = _table_items(section, cells)
                items.update(found)
                problems.extend(malformed)
        elif section == "Python floor":
            items.update(
                ("python floor", token.replace(" ", "")) for token in TOKEN.findall(body) if FLOOR.fullmatch(token)
            )
    problems.extend(
        f"no 'Governed by:' paragraph under {module} in contract.md" for module in seen if module not in governed
    )
    citations = tuple(dict.fromkeys(f"{spec}:CAP-{number}" for spec, number in CITATION.findall(text)))
    return Contract(frozenset(items), frozenset(estate), citations, frozenset(TOKEN.findall(text)), tuple(problems))


# -- the comparison -----------------------------------------------------------------------------------------------


def drift(source: Source, contract: Contract) -> list[str]:
    """One message per disagreement, each naming the item; empty when the two agree."""
    messages = [f"unlisted in contract.md: {kind} {item}" for kind, item in sorted(source.items - contract.items)]
    messages += [f"missing from the source: {kind} {item}" for kind, item in sorted(contract.items - source.items)]
    messages += [
        f"missing from the source: estate-bound constant {module}.{name}"
        for module, name in sorted(contract.estate)
        if ("public name", f"{module}.{name}") not in source.items
    ]
    messages += [
        f"unlisted in contract.md: leaf-namespace string {value}"
        for value in sorted(source.leaf_strings - contract.tokens)
    ]
    messages += list(contract.problems)
    return messages


def unresolved_citations(contract: Contract, spec_files: Iterable[Path]) -> list[str]:
    """Each cited ``spec-<x>:CAP-n`` / ``fnd:CAP-n`` whose Spec defines no such capability heading.

    ``spec_files`` are ``SPEC.md`` paths; a Spec's slug is the name of the folder that holds its ``SPEC.md``."""
    by_slug: dict[str, list[Path]] = {}
    for path in spec_files:
        by_slug.setdefault(path.parent.name, []).append(path)
    unresolved: list[str] = []
    for citation in contract.citations:
        spec, number = citation.split(":CAP-")
        slug = FOUNDRY_SPEC if spec == "fnd" else spec
        heading = re.compile(rf"^- \*\*CAP-{number} ", re.MULTILINE)
        if not any(heading.search(path.read_text(encoding="utf-8")) for path in by_slug.get(slug, [])):
            unresolved.append(f"citation {citation} names no capability its Spec defines")
    return unresolved


# -- the live contract --------------------------------------------------------------------------------------------


def _repo_root() -> Path:
    """The repository root: the package -> packages -> shared -> src -> the root."""
    return PACKAGE_DIR.parents[3]


def _live_contract() -> str:
    return (_repo_root() / CONTRACT_RELATIVE).read_text(encoding="utf-8")


def _live_spec_files() -> list[Path]:
    """Every Spec's ``SPEC.md``: the planning Specs of each BMAD project and the governance Specs."""
    root = _repo_root()
    planning = sorted((root / "_bmad-output" / "projects").glob("*/planning-artifacts/specs/*/SPEC.md"))
    governance = sorted((root / "docs" / "governance").glob("*/SPEC.md"))
    return [*planning, *governance]


def test_contract_and_source_agree() -> None:
    messages = drift(derive_source(SOURCE_DIR, PYPROJECT), parse_contract(_live_contract()))
    assert not messages, f"{CONTRACT_RELATIVE} and pyforge.core disagree:\n" + "\n".join(messages)


def test_every_capability_the_contract_cites_is_defined() -> None:
    contract = parse_contract(_live_contract())
    assert contract.citations, "contract.md cites no capability"
    unresolved = unresolved_citations(contract, _live_spec_files())
    assert not unresolved, "\n".join(unresolved)


# -- both directions on synthetic input ---------------------------------------------------------------------------

SYNTHETIC_MODULE = '''\
"""A synthetic leaf module."""

import os

EXIT_USAGE = 2
SWITCH = "pyforge.alpha.switch"
GROUP = "pyforge.core.hooks"
SCHEMA = {"$id": "urn:local-recipes:alpha:schema"}
_HOME = "ALPHA_HOME"


def home() -> str:
    return os.environ.get(_HOME, "")


def launch(runner, argv):
    return runner(argv, env={**os.environ, "ALPHA_CHILD": "1"})
'''

SYNTHETIC_PYPROJECT = """\
[project]
name = "synthetic"
requires-python = ">=3.14"

[project.scripts]
alpha = "pyforge.core.alpha:home"

[project.entry-points."pyforge.core.hooks"]
dummy = "pyforge.core.alpha:launch"
"""

SYNTHETIC_CONTRACT = """\
# Contract

## Modules

### `pyforge.core.alpha`

Governed by: spec-demo:CAP-1.

Public names: `EXIT_USAGE`, `SWITCH`, `GROUP`, `SCHEMA`, `home`,
`launch`.

Estate-bound constants: `SCHEMA` (`urn:local-recipes:alpha:schema`).

## Environment variables

| Variable | Role | Modules | Meaning |
|---|---|---|---|
| `ALPHA_HOME` | `read` | `pyforge.core.alpha` | Where alpha lives. |
| `ALPHA_CHILD` | `set` | `pyforge.core.alpha` | Handed to the child. |

## Feature-flag keys

| Key | Modules | Meaning |
|---|---|---|
| `pyforge.alpha.switch` | `pyforge.core.alpha` | Turns alpha on. |

## Exit codes

| Name | Value | Modules | Means |
|---|---|---|---|
| `EXIT_USAGE` | `2` | `pyforge.core.alpha` | A usage error. |

## Entry points

| Group | Name | Target |
|---|---|---|
| `console_scripts` | `alpha` | `pyforge.core.alpha:home` |
| `pyforge.core.hooks` | `dummy` | `pyforge.core.alpha:launch` |

## Python floor

`>=3.14`.
"""


def _synthetic(
    tmp_path: Path,
    *,
    module: str = SYNTHETIC_MODULE,
    extra_files: dict[str, str] | None = None,
    pyproject: str = SYNTHETIC_PYPROJECT,
    contract: str = SYNTHETIC_CONTRACT,
) -> list[str]:
    source_dir = tmp_path / "core"
    source_dir.mkdir()
    (source_dir / "__init__.py").write_text('__version__ = "0"\n', encoding="utf-8")
    (source_dir / "alpha.py").write_text(module, encoding="utf-8")
    for name, text in (extra_files or {}).items():
        (source_dir / name).write_text(text, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return drift(derive_source(source_dir, tmp_path / "pyproject.toml"), parse_contract(contract))


def _contract(old: str, new: str) -> str:
    assert SYNTHETIC_CONTRACT.count(old) == 1, old
    return SYNTHETIC_CONTRACT.replace(old, new)


def test_the_synthetic_source_and_contract_agree(tmp_path: Path) -> None:
    assert _synthetic(tmp_path) == []


def test_a_public_name_unlisted_in_the_contract_is_reported(tmp_path: Path) -> None:
    messages = _synthetic(tmp_path, module=SYNTHETIC_MODULE + "\n\ndef extra() -> None:\n    pass\n")
    assert messages == ["unlisted in contract.md: public name pyforge.core.alpha.extra"]


def test_a_contract_name_missing_from_the_source_is_reported(tmp_path: Path) -> None:
    messages = _synthetic(tmp_path, contract=_contract("`launch`.", "`launch`, `ghost`."))
    assert messages == ["missing from the source: public name pyforge.core.alpha.ghost"]


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        pytest.param(
            {"extra_files": {"beta.py": '"""Beta."""\n'}},
            "unlisted in contract.md: module pyforge.core.beta",
            id="module",
        ),
        pytest.param(
            {"module": SYNTHETIC_MODULE + '\n\ndef depth() -> str:\n    return os.getenv("ALPHA_DEPTH", "")\n'},
            "unlisted in contract.md: environment variable ALPHA_DEPTH (read) in pyforge.core.alpha",
            id="environment-variable-read",
        ),
        pytest.param(
            {"module": SYNTHETIC_MODULE + '\n\ndef mark() -> None:\n    os.environ["ALPHA_MARK"] = "1"\n'},
            "unlisted in contract.md: environment variable ALPHA_MARK (set) in pyforge.core.alpha",
            id="environment-variable-set",
        ),
        pytest.param(
            {"module": SYNTHETIC_MODULE + '\nOTHER = "pyforge.alpha.other"\n'},
            "unlisted in contract.md: feature-flag key pyforge.alpha.other in pyforge.core.alpha",
            id="feature-flag-key",
        ),
        pytest.param(
            {"module": SYNTHETIC_MODULE + "\nEXIT_DATA = 65\n"},
            "unlisted in contract.md: exit code EXIT_DATA = 65 in pyforge.core.alpha",
            id="exit-code",
        ),
        pytest.param(
            {"module": SYNTHETIC_MODULE + '\nOTHER_SCHEMA = "urn:local-recipes:alpha:other"\n'},
            "unlisted in contract.md: schema id urn:local-recipes:alpha:other in pyforge.core.alpha",
            id="schema-id",
        ),
        pytest.param(
            {
                "pyproject": SYNTHETIC_PYPROJECT.replace(
                    "[project.entry-points", 'beta = "pyforge.core.alpha:launch"\n\n[project.entry-points'
                )
            },
            "unlisted in contract.md: entry point console_scripts: beta = pyforge.core.alpha:launch",
            id="entry-point",
        ),
        pytest.param(
            {"pyproject": SYNTHETIC_PYPROJECT.replace(">=3.14", ">=3.15")},
            "unlisted in contract.md: python floor >=3.15",
            id="python-floor",
        ),
        pytest.param(
            {"module": SYNTHETIC_MODULE + '\nSPEC = "pyforge.core.example"\n'},
            "unlisted in contract.md: leaf-namespace string pyforge.core.example",
            id="leaf-namespace-string",
        ),
    ],
)
def test_each_kind_unlisted_in_the_contract_is_reported(tmp_path: Path, change: dict[str, Any], expected: str) -> None:
    assert expected in _synthetic(tmp_path, **change)


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        pytest.param(
            "## Environment variables",
            "### `pyforge.core.ghost`\n\nGoverned by: spec-demo:CAP-1.\n\nPublic names: none.\n\n## Environment variables",
            "missing from the source: module pyforge.core.ghost",
            id="module",
        ),
        pytest.param(
            "| `ALPHA_HOME` |",
            "| `ALPHA_GHOST` | `read` | `pyforge.core.alpha` | Gone. |\n| `ALPHA_HOME` |",
            "missing from the source: environment variable ALPHA_GHOST (read) in pyforge.core.alpha",
            id="environment-variable",
        ),
        pytest.param(
            "| `ALPHA_HOME` | `read`",
            "| `ALPHA_HOME` | `set`",
            "missing from the source: environment variable ALPHA_HOME (set) in pyforge.core.alpha",
            id="environment-variable-role",
        ),
        pytest.param(
            "| `pyforge.alpha.switch` |",
            "| `pyforge.alpha.ghost` | `pyforge.core.alpha` | Gone. |\n| `pyforge.alpha.switch` |",
            "missing from the source: feature-flag key pyforge.alpha.ghost in pyforge.core.alpha",
            id="feature-flag-key",
        ),
        pytest.param(
            "| `EXIT_USAGE` | `2`",
            "| `EXIT_GHOST` | `9` | `pyforge.core.alpha` | Gone. |\n| `EXIT_USAGE` | `2`",
            "missing from the source: exit code EXIT_GHOST = 9 in pyforge.core.alpha",
            id="exit-code",
        ),
        pytest.param(
            "| `console_scripts` |",
            "| `console_scripts` | `ghost` | `pyforge.core.alpha:ghost` |\n| `console_scripts` |",
            "missing from the source: entry point console_scripts: ghost = pyforge.core.alpha:ghost",
            id="entry-point",
        ),
        pytest.param(
            "(`urn:local-recipes:alpha:schema`)",
            "(`urn:local-recipes:alpha:schema`, `urn:local-recipes:alpha:ghost`)",
            "missing from the source: schema id urn:local-recipes:alpha:ghost in pyforge.core.alpha",
            id="schema-id",
        ),
        pytest.param(
            "Estate-bound constants: `SCHEMA`",
            "Estate-bound constants: `SCHEMA`, `GHOST`",
            "missing from the source: estate-bound constant pyforge.core.alpha.GHOST",
            id="estate-bound-constant",
        ),
        pytest.param(
            "`>=3.14`.",
            "`>=3.13`.",
            "missing from the source: python floor >=3.13",
            id="python-floor",
        ),
    ],
)
def test_each_kind_missing_from_the_source_is_reported(tmp_path: Path, old: str, new: str, expected: str) -> None:
    assert expected in _synthetic(tmp_path, contract=_contract(old, new))


def test_a_module_section_without_a_governor_is_reported(tmp_path: Path) -> None:
    messages = _synthetic(tmp_path, contract=_contract("Governed by: spec-demo:CAP-1.\n\n", ""))
    assert messages == ["no 'Governed by:' paragraph under pyforge.core.alpha in contract.md"]


def test_a_duplicate_module_section_is_reported(tmp_path: Path) -> None:
    duplicate = "### `pyforge.core.alpha`\n\nGoverned by: spec-demo:CAP-1.\n\n## Environment variables"
    messages = _synthetic(tmp_path, contract=_contract("## Environment variables", duplicate))
    assert messages == ["duplicate section in contract.md: pyforge.core.alpha"]


def test_a_citation_naming_no_defined_capability_is_reported(tmp_path: Path) -> None:
    spec = tmp_path / "docs" / "governance" / "spec-demo"
    spec.mkdir(parents=True)
    (spec / "SPEC.md").write_text("- **CAP-1 — a demo capability.**\n", encoding="utf-8")
    assert unresolved_citations(parse_contract(SYNTHETIC_CONTRACT), [spec / "SPEC.md"]) == []
    contract = parse_contract(_contract("spec-demo:CAP-1", "spec-demo:CAP-2"))
    assert unresolved_citations(contract, [spec / "SPEC.md"]) == [
        "citation spec-demo:CAP-2 names no capability its Spec defines"
    ]
