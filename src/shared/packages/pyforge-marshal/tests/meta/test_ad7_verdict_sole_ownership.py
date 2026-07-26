"""Meta test -- the ``pyforge.marshal`` ``core/verdict.py`` sole-ownership
guard (Story 1.1). Mirrors ``pyforge-warden``'s sibling
``tests/meta/test_verdict_sole_ownership.py`` AST-scan technique exactly,
adapted to Marshal's own 6-member lattice and exit-code domain.

AST-scan every module in the installed package EXCEPT ``verdict.py`` and
fail if any of them:

(a) calls an exit primitive (``sys.exit`` / ``os._exit`` / ``SystemExit``,
    including ``from sys import exit as <alias>`` / ``from os import _exit
    as <alias>`` aliases, an aliased ``import sys as s`` / ``import os as
    o`` module reference, positional or keyword args, or a bare string arg
    -- ``sys.exit("msg")`` exits 1) with an int literal in Marshal's frozen
    exit-code domain ``{0, 1, 2, 3, 4, 130}`` (AD-7) or with a simple
    module-level ``NAME = <int literal>`` constant resolving to one;
(b) imports (or dereferences) a ``_``-private name from ``verdict`` --
    through ANY local name bound to the verdict module, not just the
    literal name ``verdict`` (``LATTICE_ORDER`` is deliberately PUBLIC --
    referencing it is legal; only ``_``-prefixed names like ``_RANK``/
    ``_EXIT_BY_VERDICT``/``_CLASSIFY_TABLE`` are guarded);
(c) contains a List/Tuple literal (or Dict literal keys) whose Verdict-token
    sequence spells out the full 6-member lattice in exactly the lattice
    order or its exact reverse. An UNORDERED enumeration of all 6 tokens
    does NOT fire -- enumerating the vocabulary is legal; encoding the
    ORDER is not.

Positively asserts ``verdict.py`` itself defines ``LATTICE_ORDER`` +
``exit_code_for`` and that the lattice-order detector fires on it -- the
guard is alive, not vacuous.

Bounds (stated, not aspirational): this is a best-effort STATIC check.
Indirection through helper functions (``exit(code())``), values built via
f-strings/arithmetic, dynamic attribute access (``getattr``), and
argparse's ``parser.error()`` (which exits 2 internally) are out of scope;
the runtime contract tests in ``tests/unit`` are the behavioral backstop.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.core.model import Verdict

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
VERDICT_TOKENS = frozenset(member.value for member in Verdict)
VERDICT_VALUE_BY_MEMBER = {member.name: member.value for member in Verdict}
GUARDED_EXIT_LITERALS = frozenset({0, 1, 2, 3, 4, 130})

# The lattice order, strongest first (the sequence the guard forbids outside
# verdict.py). Test-local knowledge: package modules never spell this out.
LATTICE_ORDER = (
    "error",
    "gate-failed",
    "scope-violation",
    "unevaluable",
    "warn",
    "clean",
)
LATTICE_REVERSED = tuple(reversed(LATTICE_ORDER))


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _non_verdict_modules() -> list[Path]:
    return [path for path in _package_modules() if path.name != "verdict.py"]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _exit_call_aliases(tree: ast.Module) -> frozenset[str]:
    """Bare names that invoke an exit primitive: the builtins plus any
    ``from sys import exit as X`` / ``from os import _exit as Y`` alias."""
    aliases = {"exit", "SystemExit"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module == "sys":
            for alias in node.names:
                if alias.name == "exit":
                    aliases.add(alias.asname or alias.name)
        elif node.module == "os":
            for alias in node.names:
                if alias.name == "_exit":
                    aliases.add(alias.asname or alias.name)
    return frozenset(aliases)


def _exit_module_aliases(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    """Names bound to the sys / os MODULES themselves -- ``import sys as s``
    makes ``s.exit(2)`` an exit call the attribute check must see."""
    sys_names = {"sys"}
    os_names = {"os"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name == "sys":
                sys_names.add(alias.asname or alias.name)
            elif alias.name == "os":
                os_names.add(alias.asname or alias.name)
    return (frozenset(sys_names), frozenset(os_names))


def _module_int_constants(tree: ast.Module) -> dict[str, int]:
    """Simple module-level ``NAME = <int literal>`` bindings (top level only
    -- a best-effort constant table, not a dataflow analysis)."""
    constants: dict[str, int] = {}
    for stmt in tree.body:
        value: ast.expr | None
        targets: list[ast.expr]
        if isinstance(stmt, ast.Assign):
            value, targets = stmt.value, stmt.targets
        elif isinstance(stmt, ast.AnnAssign):
            value, targets = stmt.value, [stmt.target]
        else:
            continue
        if (
            isinstance(value, ast.Constant)
            and isinstance(value.value, int)
            and not isinstance(value.value, bool)
        ):
            for target in targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = value.value
    return constants


def _is_exit_callable(
    func: ast.expr,
    exit_aliases: frozenset[str],
    sys_names: frozenset[str],
    os_names: frozenset[str],
) -> bool:
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            if (func.value.id in sys_names and func.attr == "exit") or (
                func.value.id in os_names and func.attr == "_exit"
            ):
                return True
        return func.attr == "SystemExit"
    return isinstance(func, ast.Name) and func.id in exit_aliases


def _exit_literal_violations(tree: ast.Module) -> list[int]:
    exit_aliases = _exit_call_aliases(tree)
    sys_names, os_names = _exit_module_aliases(tree)
    constants = _module_int_constants(tree)
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_exit_callable(
            node.func, exit_aliases, sys_names, os_names
        ):
            continue
        arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
        for arg in arguments:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, int)
                and not isinstance(arg.value, bool)
                and arg.value in GUARDED_EXIT_LITERALS
            ):
                violations.append(node.lineno)
            elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                # sys.exit("message") exits with code 1 -- a guarded value
                # smuggled through a string arg. Only verdict.py projects.
                violations.append(node.lineno)
            elif (
                isinstance(arg, ast.Name)
                and constants.get(arg.id) in GUARDED_EXIT_LITERALS
            ):
                violations.append(node.lineno)
    return violations


def _verdict_bound_names(tree: ast.Module) -> frozenset[str]:
    """Every local name bound to the verdict module: ``import ...verdict as
    v``, ``from . import verdict [as w]``, ``from pkg import verdict [as
    w]``."""
    names = {"verdict"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "verdict" or alias.name.endswith(".verdict"):
                    if alias.asname is not None:
                        names.add(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "verdict":
                    names.add(alias.asname or alias.name)
    return frozenset(names)


def _private_verdict_references(tree: ast.Module) -> list[str]:
    verdict_names = _verdict_bound_names(tree)
    references: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_tail = (node.module or "").split(".")[-1]
            if module_tail == "verdict":
                references.extend(
                    alias.name for alias in node.names if alias.name.startswith("_")
                )
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            # x._priv where x is any name bound to the verdict module ...
            if isinstance(node.value, ast.Name) and node.value.id in verdict_names:
                references.append(node.attr)
            # ... or pkg.verdict._priv via a plain `import pkg...verdict`.
            elif (
                isinstance(node.value, ast.Attribute)
                and node.value.attr == "verdict"
            ):
                references.append(node.attr)
    return references


def _sequence_element_token(element: ast.expr) -> str | None:
    if isinstance(element, ast.Constant) and isinstance(element.value, str):
        return element.value if element.value in VERDICT_TOKENS else None
    if (
        isinstance(element, ast.Attribute)
        and isinstance(element.value, ast.Name)
        and element.value.id == "Verdict"
    ):
        return VERDICT_VALUE_BY_MEMBER.get(element.attr)
    return None


def _ordered_verdict_tokens(node: ast.expr) -> list[str | None] | None:
    """The in-order element tokens of a List/Tuple literal or a Dict
    literal's keys -- non-Verdict elements map to ``None`` sentinels (NOT
    dropped: an interleaved literal must never spell the consecutive
    lattice); ``None`` for any other node."""
    if isinstance(node, (ast.List, ast.Tuple)):
        elements: list[ast.expr] = list(node.elts)
    elif isinstance(node, ast.Dict):
        elements = [key for key in node.keys if key is not None]
    else:
        return None
    return [_sequence_element_token(element) for element in elements]


def _contains_run(sequence: list[str | None], run: tuple[str, ...]) -> bool:
    if len(sequence) < len(run):
        return False
    return any(
        tuple(sequence[i : i + len(run)]) == run
        for i in range(len(sequence) - len(run) + 1)
    )


def _lattice_ordering_literals(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Dict)):
            continue
        tokens = _ordered_verdict_tokens(node)
        if tokens is None:
            continue
        if _contains_run(tokens, LATTICE_ORDER) or _contains_run(
            tokens, LATTICE_REVERSED
        ):
            violations.append(node.lineno)
    return violations


def test_package_scan_surface_is_not_empty():
    modules = _non_verdict_modules()
    assert modules, "sole-ownership guard found no modules to scan"
    names = {path.name for path in _package_modules()}
    assert "verdict.py" in names, "verdict.py missing from the installed package"


@pytest.mark.parametrize(
    "module_path", _non_verdict_modules(), ids=lambda p: p.name
)
def test_no_exit_literal_projection_outside_verdict(module_path: Path):
    violations = _exit_literal_violations(_parse(module_path))
    assert not violations, (
        f"{module_path.name} calls an exit primitive with a value from "
        f"{sorted(GUARDED_EXIT_LITERALS)} at line(s) {violations} -- only "
        "verdict.py projects"
    )


@pytest.mark.parametrize(
    "module_path", _non_verdict_modules(), ids=lambda p: p.name
)
def test_no_private_verdict_import_outside_verdict(module_path: Path):
    references = _private_verdict_references(_parse(module_path))
    assert not references, (
        f"{module_path.name} references private verdict name(s) {references}"
    )


@pytest.mark.parametrize(
    "module_path", _non_verdict_modules(), ids=lambda p: p.name
)
def test_no_lattice_ordering_outside_verdict(module_path: Path):
    violations = _lattice_ordering_literals(_parse(module_path))
    assert not violations, (
        f"{module_path.name} spells out the 6-member lattice ORDER (or its "
        f"exact reverse) at line(s) {violations} -- only verdict.py owns "
        "the lattice"
    )


def test_unordered_enumeration_of_all_tokens_does_not_fire():
    """Regression for the guard's own false positive: enumerating all 6
    tokens WITHOUT the lattice order is legal and must not fire."""
    shuffled = (
        'ALL = ["warn", "clean", "error", "unevaluable", "scope-violation", '
        '"gate-failed"]\n'
    )
    assert _lattice_ordering_literals(ast.parse(shuffled)) == []
    ordered = (
        'ORDER = ["error", "gate-failed", "scope-violation", "unevaluable", '
        '"warn", "clean"]\n'
    )
    assert _lattice_ordering_literals(ast.parse(ordered)) == [1]
    reverse = (
        'ORDER = ["clean", "warn", "unevaluable", "scope-violation", '
        '"gate-failed", "error"]\n'
    )
    assert _lattice_ordering_literals(ast.parse(reverse)) == [1]
    as_dict_keys = (
        'TABLE = {"error": 4, "gate-failed": 3, "scope-violation": 2, '
        '"unevaluable": 1, "warn": 0, "clean": 0}\n'
    )
    assert _lattice_ordering_literals(ast.parse(as_dict_keys)) == [1]


def test_interleaved_verdict_tokens_do_not_fire():
    """Tokens interleaved with non-Verdict elements never spell the
    consecutive lattice order and must not fire."""
    interleaved = (
        'X = ["error", "critical failure", "gate-failed", "blocked", '
        '"scope-violation", "out of bounds", "unevaluable", "unknown", '
        '"warn", "advisory", "clean", "ok"]\n'
    )
    assert _lattice_ordering_literals(ast.parse(interleaved)) == []


def test_exit_detector_sees_aliases_keywords_and_constants():
    """The detector's own coverage: aliased imports, keyword args, and
    module-level int constants all fire; benign (non-guarded) values do
    not."""
    aliased = "from sys import exit as bail\nbail(2)\n"
    assert _exit_literal_violations(ast.parse(aliased)) == [2]
    os_alias = "from os import _exit as die\ndie(130)\n"
    assert _exit_literal_violations(ast.parse(os_alias)) == [2]
    keyword = "import sys\nsys.exit(code=3)\n"
    assert _exit_literal_violations(ast.parse(keyword)) == [2]
    module_alias = "import sys as s\ns.exit(4)\n"
    assert _exit_literal_violations(ast.parse(module_alias)) == [2]
    constant = "import sys\nFAIL = 1\nsys.exit(FAIL)\n"
    assert _exit_literal_violations(ast.parse(constant)) == [3]
    # 5 is NOT in Marshal's guarded domain {0, 1, 2, 3, 4, 130} -- a bare
    # sys.exit(5) elsewhere is out of this guard's scope by design.
    benign = "import sys\nOK = 5\nsys.exit(OK)\nsys.exit(5)\n"
    assert _exit_literal_violations(ast.parse(benign)) == []


def test_exit_detector_sees_module_aliases_and_string_args():
    module_alias = "import sys as s\ns.exit(2)\n"
    assert _exit_literal_violations(ast.parse(module_alias)) == [2]
    os_module_alias = "import os as o\no._exit(130)\n"
    assert _exit_literal_violations(ast.parse(os_module_alias)) == [2]
    string_arg = 'import sys\nsys.exit("fatal")\n'
    assert _exit_literal_violations(ast.parse(string_arg)) == [2]
    none_arg = "import sys\nsys.exit(None)\nsys.exit()\n"
    assert _exit_literal_violations(ast.parse(none_arg)) == []


def test_private_detector_sees_verdict_module_aliases():
    aliased = "from pyforge.marshal.core import verdict as v\nx = v._RANK\n"
    assert _private_verdict_references(ast.parse(aliased)) == ["_RANK"]
    plain_import = (
        "import pyforge.marshal.core.verdict\n"
        "x = pyforge.marshal.core.verdict._RANK\n"
    )
    assert _private_verdict_references(ast.parse(plain_import)) == ["_RANK"]
    public_only = (
        "from pyforge.marshal.core import verdict\n"
        "order = verdict.LATTICE_ORDER\n"
        "code = verdict.exit_code_for\n"
    )
    assert _private_verdict_references(ast.parse(public_only)) == []


def test_guard_is_alive_synthetic_violation_fires_and_verdict_defines_projection():
    """Non-vacuous proof: (1) the exit-literal detector demonstrably fires
    on a synthetic violation, and (2) verdict.py itself structurally
    defines LATTICE_ORDER + exit_code_for, and the lattice-order detector
    fires ON verdict.py's own body (it literally spells the order it
    owns)."""
    synthetic_violation = "import sys\nsys.exit(3)\n"
    assert _exit_literal_violations(ast.parse(synthetic_violation)) == [2]

    verdict_path = PACKAGE_DIR / "core" / "verdict.py"
    tree = _parse(verdict_path)
    assigned: set[str] = set()
    functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            assigned.update(
                target.id for target in node.targets if isinstance(target, ast.Name)
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)
        elif isinstance(node, ast.FunctionDef):
            functions.add(node.name)
    assert "LATTICE_ORDER" in assigned
    assert "exit_code_for" in functions
    assert _lattice_ordering_literals(tree), (
        "the lattice-order detector failed to fire on verdict.py itself -- "
        "the guard would be vacuous"
    )
