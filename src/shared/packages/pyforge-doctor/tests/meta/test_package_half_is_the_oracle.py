"""Story 57.3 (spec-pyforge-doctor:CAP-97; FR-28 <- spec-pyforge-doctor:CAP-97; decision D1 of the 2026-11-10
cutover readiness plan): the package-local half of Doctor's suite is the rebuild oracle.

The package-local half is every test module without the tree marker this package's ``pyproject.toml`` declares for a
module that reads the repository outside its own package. ``pyforge-doctor-test`` runs that half, and a rebuild root
can run it unchanged, because every tree it reads it builds itself. For that half to stand in for Doctor on a second
root, it has to cover Doctor. This module holds it to the oracle rule, read by AST over this package's ``src/`` and
``tests/`` (and the marker's name from its ``pyproject.toml``); it reads nothing outside the package, so it carries no
marker and runs in the half it judges:

* every module under ``src/pyforge/doctor/sources/`` is imported by an unmarked test module (``import``,
  ``from ... import``, or ``importlib.import_module`` with a literal name; importing a submodule imports its package);
* every gather ``DISPATCH`` names in ``sources/__main__.py`` is called by an unmarked module, through a name or an
  attribute the module's own imports bind to that function (a source reached only through the CLI, or only from a
  marked function, is not called);
* every check code defined under ``src/`` is named by an unmarked module (a string literal equal to it, or a reference
  to the module constant or enum member that holds it), or sits in ``_UNNAMED_CHECK_CODES`` with the reason it is not
  named yet. The codes are the ones ``tests/meta/test_public_contract.py`` reads for contract.md § Check codes
  (``_code_facts``: literal and constant ``check=`` codes, helper-bound codes, item-row ``"kind"`` values and the codes
  of enumerable computed sites), so the oracle and the contract count the same set. The gap list only shrinks: an
  entry that names no defined code, or a code an unmarked module now names, fails, and the list may not grow past
  ``_GAP_CEILING``;
* no unmarked module skips on A's tree: the only skips in the package half are the three environment skips pinned in
  ``_ENVIRONMENT_SKIPS``, each with its count.

Inside an unmarked module, a function or class that carries the marker itself is left out of every reading: it runs
in the live half, not here. This module is left out too: it is the judge, and its gap list spells every gap code. The ``fires`` tests feed each rule synthetic input (a gather no unmarked module calls, a
check code no unmarked module names, a source module no unmarked module imports, a new skip, a gap entry that is no
longer a gap, a call made only from a marked function) and prove it is reported.
"""

from __future__ import annotations

import ast
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

import test_public_contract as contract_reader

from pyforge.doctor.models import Source
from pyforge.doctor.sources import __main__ as dispatcher

_PACKAGE_DOTTED = "pyforge.doctor"
_DISPATCH_MODULE = "sources/__main__.py"
_SKIP_CALLS = frozenset({"skip", "importorskip"})
_SKIP_MARKS = frozenset({"skip", "skipif"})

#: The check codes no unmarked module names yet, each with the reason. The list only shrinks: a code an unmarked
#: module comes to name must leave it (``test_the_gap_list_only_shrinks``), and it may not grow past
#: ``_GAP_CEILING``. Measured 2026-11-12 (Story 57.3) over the package half: which of these its tests produce, and
#: where, was read from a run that recorded every ``Finding`` the half constructs.
_UNNAMED_CHECK_CODES: Mapping[str, str] = {
    "capability-effect-unevaluable": (
        "produced over the empty git tree of tests/unit/test_sources_unmeasured.py, which judges it through "
        "models.is_gather_failure and never by name"
    ),
    "chain-audit-checkpoint-coherence": (
        "named only in the live half (test_live_sources_board_chain_layers_audit.py): the chain-layers audit runs "
        "scripts/fleet_scan.py from the checkout, and no package-local test builds that script (Story 58.1)"
    ),
    "chain-audit-checkpoint-layers": (
        "named only in the live half (test_live_sources_board_chain_layers_audit.py), as for the coherence checkpoint"
    ),
    "chain-audit-checkpoint-orphans": (
        "named only in the live half (test_live_sources_board_chain_layers_audit.py), as for the coherence checkpoint"
    ),
    "chain-audit-checkpoint-staleness": (
        "named only in the live half (test_live_sources_board_chain_layers_audit.py), as for the coherence checkpoint"
    ),
    "chain-audit-verdict": (
        "named only in the live half (test_live_sources_board_chain_layers_audit.py), as for the coherence checkpoint"
    ),
    "console-bar-layout": (
        "check-layout's one code (board._LAYOUT_CHECK); test_sources_board_check_layout.py and "
        "test_sources_unmeasured.py produce it and assert the status and the message, never the code"
    ),
    "coverage-summary": (
        "bmad-drift's per-run summary row; test_sources_factory.py produces it on every gather and asserts the "
        "substantive findings beside it, never this code"
    ),
    "docs-currency-map-unreadable": (
        "produced by test_sources_docs_currency.py and test_sources_unmeasured.py, which assert the status and the "
        "unevaluable evidence, never the code (docs_currency._CHECK_MAP_UNREADABLE)"
    ),
    "docs-currency-ok": (
        "the clean run's one OK (docs_currency._CHECK_OK); test_sources_docs_currency.py produces it and asserts the "
        "status only"
    ),
    "docs-shelf-occupancy-unevaluable": (
        "produced by test_sources_docs_shelf.py and test_sources_unmeasured.py, judged by status and "
        "models.is_gather_failure, never by name"
    ),
    "dreams-hygiene-unevaluable": (
        "produced over the empty git tree of test_sources_unmeasured.py, judged through models.is_gather_failure"
    ),
    "frontmatter-duplicate-keys-unevaluable": (
        "produced over the empty git tree of test_sources_unmeasured.py, judged through models.is_gather_failure"
    ),
    "general-docs-consistency-unevaluable": (
        "produced over the empty git tree of test_sources_unmeasured.py, judged through models.is_gather_failure"
    ),
    "hollow-sprint-status": (
        "a HygieneFindingKind member; test_sources_hygiene.py produces the finding and test_hygiene_definitions.py "
        "tests its predicate (is_hollow_sprint_status), and neither names the kind"
    ),
    "ledger-direction-unevaluable": (
        "produced over the empty git tree of test_sources_unmeasured.py, judged through models.is_gather_failure"
    ),
    "ledger-untracked": (
        "story-status's finding for a ledger git does not track (sources/marshal.py); no package-local test reaches it"
    ),
    "platform-ci-test-env": (
        "produced by test_sources_platform_policy.py's absent-interpreter case, which asserts the status and the "
        "unevaluable evidence, never the code"
    ),
    "readme-placeholder": (
        "a HygieneFindingKind member; test_sources_hygiene.py produces the finding and test_hygiene_definitions.py "
        "tests its predicate (is_readme_placeholder), and neither names the kind"
    ),
    "stale-dream-status": (
        "a HygieneFindingKind member; test_sources_hygiene.py produces the finding and test_hygiene_definitions.py "
        "tests its predicate (is_stale_dream_status), and neither names the kind"
    ),
    "station-unevaluable": (
        "bmad-output-hygiene's WARN for a station folder it cannot read (sources/hygiene.py); no package-local test "
        "reaches it"
    ),
    "status-body-consistency-unevaluable": (
        "produced over the empty git tree of test_sources_unmeasured.py, judged through models.is_gather_failure"
    ),
    "tests-policy": (
        "platform-policy-suite's suite verdict; test_sources_platform_policy.py produces it and asserts the status "
        "and the exit code, never the code"
    ),
}

#: The gap list's size when this module landed (2026-11-12). Raising it is a reviewed edit, never a side effect.
_GAP_CEILING = 23

#: The only skips the package half holds, by module under ``tests/``: (count, why it never fires on A's tree).
_ENVIRONMENT_SKIPS: Mapping[str, tuple[int, str]] = {
    "unit/test_checks_env_hygiene.py": (
        1,
        "a filesystem that refuses a non-UTF-8 file name; A's Linux and macOS checkouts accept one",
    ),
    "unit/test_sources_factory.py": (
        1,
        "_needs_unprivileged: chmod-based unreadable-directory cases mean nothing to root; CI and laptops run "
        "unprivileged",
    ),
    "unit/test_sources_registry.py": (
        1,
        "_needs_checkout: locate_checkout_script's two cases need scripts/fleet_scan.py above the package, which "
        "A's tree always has (the baseline's one)",
    ),
}


# --------------------------------------------------------------------------------------------------
# Reading the package.
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Package:
    """What the oracle reads: the package's sources and test modules, keyed by path, and its tree marker."""

    src: Mapping[str, str]  # path under src/pyforge/doctor (posix) -> text
    tests: Mapping[str, str]  # path under tests/ (posix) -> text, test modules only
    marker: str


def _package_root() -> Path:
    # tests/meta -> tests -> the package
    return Path(__file__).resolve().parents[2]


def _tree_marker(pyproject_text: str) -> str:
    """The marker the package declares for a module that reads the repository outside its own package."""
    markers = tomllib.loads(pyproject_text)["tool"]["pytest"]["ini_options"]["markers"]
    found = [
        entry.split(":", 1)[0].split("(", 1)[0].strip()
        for entry in markers
        if "outside its own package" in entry.split(":", 1)[-1]
    ]
    assert len(found) == 1, f"expected one declared tree marker in pyproject.toml, found {found}"
    return found[0]


def _read_package(root: Path) -> Package:
    src_root = root / "src" / "pyforge" / "doctor"
    src = {
        path.relative_to(src_root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(src_root.rglob("*.py"))
        if "__pycache__" not in path.parts
    }
    tests_root = root / "tests"
    tests = {
        path.relative_to(tests_root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(tests_root.rglob("test_*.py"))
        # The judge is not part of the half it judges: its gap list spells every gap code.
        if "__pycache__" not in path.parts and path.resolve() != Path(__file__).resolve()
    }
    return Package(src, tests, _tree_marker((root / "pyproject.toml").read_text(encoding="utf-8")))


def _carries(node: ast.expr, marker: str) -> bool:
    """True when the expression names the marker (``pytest.mark.<marker>``, alone, called or in a list)."""
    return any(isinstance(each, ast.Attribute) and each.attr == marker for each in ast.walk(node))


def _module_is_marked(tree: ast.Module, marker: str) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in targets) and _carries(node.value, marker):
            return True
    return False


class _DropMarked(ast.NodeTransformer):
    """Leave out every function and class that carries the marker: it runs in the live half."""

    def __init__(self, marker: str) -> None:
        self.marker = marker

    def _keep(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> ast.AST | None:
        if any(_carries(decorator, self.marker) for decorator in node.decorator_list):
            return None
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST | None:
        return self._keep(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST | None:
        return self._keep(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST | None:
        return self._keep(node)


def _unmarked(package: Package) -> dict[str, ast.Module]:
    """The package half: each test module without the marker, with its marked functions and classes left out."""
    out: dict[str, ast.Module] = {}
    for path, text in package.tests.items():
        tree = ast.parse(text)
        if not _module_is_marked(tree, package.marker):
            out[path] = _DropMarked(package.marker).visit(tree)
    return out


def _dotted(path: str) -> str:
    """``sources/chain.py`` -> ``pyforge.doctor.sources.chain``; a package's ``__init__.py`` is the package."""
    parts = [*_PACKAGE_DOTTED.split("."), *path.removesuffix(".py").split("/")]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _prefixes(dotted: str) -> Iterator[str]:
    parts = dotted.split(".")
    for end in range(1, len(parts) + 1):
        yield ".".join(parts[:end])


@dataclass(frozen=True)
class Bindings:
    """What one test module's imports bind: names to modules, names to objects, and every module imported."""

    modules: Mapping[str, str]  # local name -> dotted module
    objects: Mapping[str, tuple[str, str]]  # local name -> (dotted module, attribute)
    imported: frozenset[str]  # dotted modules the module imports (submodules import their packages)
    known: frozenset[str]  # the package's own modules, by dotted name

    def is_module(self, dotted: str) -> bool:
        """A module of the package, or a package on the way to one (``pyforge``, ``pyforge.doctor``)."""
        return dotted in self.known or any(each.startswith(f"{dotted}.") for each in self.known)


def _bindings(tree: ast.Module, known: frozenset[str]) -> Bindings:
    modules: dict[str, str] = {}
    objects: dict[str, tuple[str, str]] = {}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.update(_prefixes(alias.name))
                if alias.asname:
                    modules[alias.asname] = alias.name
                else:
                    head = alias.name.split(".", 1)[0]
                    modules[head] = head
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.update(_prefixes(node.module))
            for alias in node.names:
                local = alias.asname or alias.name
                sub = f"{node.module}.{alias.name}"
                if sub in known:
                    imported.add(sub)
                    modules[local] = sub
                else:
                    objects[local] = (node.module, alias.name)
        elif isinstance(node, ast.Call) and _call_names(node) == ("importlib", "import_module"):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                imported.update(_prefixes(node.args[0].value))
    return Bindings(modules, objects, frozenset(imported), known)


def _call_names(call: ast.Call) -> tuple[str, ...]:
    """``importlib.import_module(...)`` -> ``("importlib", "import_module")``; anything else -> its dotted parts."""
    parts: list[str] = []
    node: ast.expr = call.func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return tuple(reversed(parts))
    return ()


def _module_of(node: ast.expr, bindings: Bindings) -> str | None:
    """The dotted module an expression names: a name bound to a module, or a submodule reached from one."""
    if isinstance(node, ast.Name):
        return bindings.modules.get(node.id)
    if isinstance(node, ast.Attribute):
        base = _module_of(node.value, bindings)
        if base is not None and bindings.is_module(f"{base}.{node.attr}"):
            return f"{base}.{node.attr}"
    return None


def _reference(node: ast.expr, bindings: Bindings) -> tuple[str, str] | None:
    """``(dotted module, qualified name)`` a name or attribute refers to through the module's imports."""
    if isinstance(node, ast.Name):
        return bindings.objects.get(node.id)
    if isinstance(node, ast.Attribute):
        module = _module_of(node.value, bindings)
        if module is not None:
            return module, node.attr
        owner = _reference(node.value, bindings)
        if owner is not None:
            return owner[0], f"{owner[1]}.{node.attr}"
    return None


# --------------------------------------------------------------------------------------------------
# The four readings.
# --------------------------------------------------------------------------------------------------


def _source_modules(package: Package) -> dict[str, str]:
    """``sources/<name>.py`` -> its dotted name, for every module directly under ``sources/``."""
    return {
        path: _dotted(path)
        for path in package.src
        if path.startswith("sources/") and path.count("/") == 1 and path.endswith(".py")
    }


def _known_modules(package: Package) -> frozenset[str]:
    return frozenset(_dotted(path) for path in package.src)


def unimported_sources(package: Package) -> list[str]:
    known = _known_modules(package)
    imported: set[str] = set()
    for tree in _unmarked(package).values():
        imported |= _bindings(tree, known).imported
    return sorted(path for path, dotted in _source_modules(package).items() if dotted not in imported)


def dispatch_gathers(package: Package) -> dict[str, tuple[str, str]]:
    """``DISPATCH`` read from ``sources/__main__.py``: each key as written -> (dotted module, function)."""
    tree = ast.parse(package.src[_DISPATCH_MODULE])
    package_dotted = _dotted(_DISPATCH_MODULE).rsplit(".", 1)[0]
    modules: dict[str, str] = {}
    functions: dict[str, tuple[str, str]] = {}
    known = _known_modules(package)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package_dotted.split(".")
                base = ".".join([*parts[: len(parts) - (node.level - 1)], *([node.module] if node.module else [])])
            else:
                base = node.module or ""
            for alias in node.names:
                local = alias.asname or alias.name
                if f"{base}.{alias.name}" in known:
                    modules[local] = f"{base}.{alias.name}"
                else:
                    functions[local] = (base, alias.name)
    table: dict[str, tuple[str, str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == "DISPATCH" for t in targets) or not isinstance(value, ast.Dict):
            continue
        for key, entry in zip(value.keys, value.values, strict=True):
            label = _label(key)
            if isinstance(entry, ast.Attribute) and isinstance(entry.value, ast.Name) and entry.value.id in modules:
                table[label] = (modules[entry.value.id], entry.attr)
            elif isinstance(entry, ast.Name) and entry.id in functions:
                table[label] = functions[entry.id]
            else:
                table[label] = ("<unreadable>", ast.unparse(entry))
    return table


def _label(key: ast.expr | None) -> str:
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return key.value
    if (
        isinstance(key, ast.Attribute)
        and key.attr == "value"
        and isinstance(key.value, ast.Attribute)
        and isinstance(key.value.value, ast.Name)
        and key.value.value.id == "Source"
        and key.value.attr in Source.__members__
    ):
        return Source[key.value.attr].value
    return "<unreadable>" if key is None else ast.unparse(key)


def uncalled_gathers(package: Package) -> list[str]:
    known = _known_modules(package)
    called: set[tuple[str, str]] = set()
    for tree in _unmarked(package).values():
        bindings = _bindings(tree, known)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                target = _reference(node.func, bindings)
                if target is not None:
                    called.add(target)
    return sorted(
        f"{label}: {module}.{function}"
        for label, (module, function) in dispatch_gathers(package).items()
        if (module, function) not in called
    )


def _source_constants(package: Package) -> dict[str, dict[str, str]]:
    """Each source module's string constants: module level (as the contract reader evaluates them) and the string
    members of its classes (``HygieneFindingKind.DEAD_TEST_SCAFFOLDING``), keyed ``<Class>.<member>``."""
    out: dict[str, dict[str, str]] = {}
    for path, text in package.src.items():
        tree = ast.parse(text)
        consts = dict(contract_reader._module_constants(tree))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for member in node.body:
                if (
                    isinstance(member, ast.Assign)
                    and isinstance(member.value, ast.Constant)
                    and isinstance(member.value.value, str)
                ):
                    for target in member.targets:
                        if isinstance(target, ast.Name):
                            consts[f"{node.name}.{target.id}"] = member.value.value
        out[_dotted(path)] = consts
    return out


def check_codes(package: Package) -> set[str]:
    """Every check code defined under ``src/``, read the way contract.md § Check codes is."""
    return {code for _module, code in contract_reader._code_facts(dict(package.src)).check_codes}


def named_codes(package: Package) -> set[str]:
    """The strings the unmarked modules name: literals, and the source constants their references resolve to."""
    known = _known_modules(package)
    consts = _source_constants(package)
    named: set[str] = set()
    for tree in _unmarked(package).values():
        bindings = _bindings(tree, known)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                named.add(node.value)
            elif isinstance(node, (ast.Name, ast.Attribute)):
                target = _reference(node, bindings)
                if target is not None and target[1] in consts.get(target[0], {}):
                    named.add(consts[target[0]][target[1]])
    return named


def unnamed_codes(package: Package, gaps: Mapping[str, str]) -> list[str]:
    return sorted(code for code in check_codes(package) - named_codes(package) if code not in gaps)


def stale_gaps(package: Package, gaps: Mapping[str, str]) -> list[str]:
    defined, named = check_codes(package), named_codes(package)
    out = []
    for code, reason in sorted(gaps.items()):
        if code not in defined:
            out.append(f"{code}: no such check code under src/ -- remove it from the gap list")
        elif code in named:
            out.append(f"{code}: an unmarked module names it now -- remove it from the gap list (it only shrinks)")
        elif not reason.strip():
            out.append(f"{code}: the gap entry gives no reason")
    return out


def skips(package: Package) -> dict[str, int]:
    """Skip sites per unmarked module: each call of pytest's ``skip`` or ``importorskip`` and each use of its
    ``mark.skip`` or ``mark.skipif`` (a decorator, or a mark bound to a name), under any name the module binds to
    pytest, to those functions or to ``mark``."""
    out: dict[str, int] = {}
    for path, tree in _unmarked(package).items():
        pytest_names = {"pytest"}
        mark_names: set[str] = set()
        direct: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                pytest_names |= {a.asname for a in node.names if a.name == "pytest" and a.asname}
            elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
                direct |= {a.asname or a.name for a in node.names if a.name in _SKIP_CALLS}
                mark_names |= {a.asname or a.name for a in node.names if a.name == "mark"}
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                names = _call_names(node)
                if (len(names) == 2 and names[0] in pytest_names and names[1] in _SKIP_CALLS) or (
                    len(names) == 1 and names[0] in direct
                ):
                    count += 1
            elif isinstance(node, ast.Attribute) and node.attr in _SKIP_MARKS:
                owner = node.value
                if (isinstance(owner, ast.Name) and owner.id in mark_names) or (
                    isinstance(owner, ast.Attribute)
                    and owner.attr == "mark"
                    and isinstance(owner.value, ast.Name)
                    and owner.value.id in pytest_names
                ):
                    count += 1
        if count:
            out[path] = count
    return out


def skip_problems(package: Package, pinned: Mapping[str, tuple[int, str]]) -> list[str]:
    found = skips(package)
    problems = [
        f"{path}: {count} skip(s) in the package half, {pinned.get(path, (0, ''))[0]} pinned"
        for path, count in sorted(found.items())
        if count != pinned.get(path, (0, ""))[0]
    ]
    problems += [
        f"{path}: pinned {count} skip(s), the module holds none -- shrink the pin"
        for path, (count, _why) in sorted(pinned.items())
        if path not in found
    ]
    return problems


# --------------------------------------------------------------------------------------------------
# This package.
# --------------------------------------------------------------------------------------------------


def _this_package() -> Package:
    return _read_package(_package_root())


def test_the_reader_sees_both_halves() -> None:
    package = _this_package()
    unmarked = _unmarked(package)
    assert len(unmarked) >= 50, f"the reader found only {len(unmarked)} unmarked modules"
    assert len(package.tests) - len(unmarked) >= 10, "the reader found almost no marked modules"
    assert "meta/test_package_half_is_the_oracle.py" not in package.tests


def test_every_source_module_is_imported_by_an_unmarked_module() -> None:
    package = _this_package()
    assert len(_source_modules(package)) >= 30
    assert unimported_sources(package) == []


def test_the_dispatch_reader_sees_every_runtime_entry() -> None:
    read = dispatch_gathers(_this_package())
    runtime = {name: (fn.__module__, fn.__name__) for name, fn in dispatcher.DISPATCH.items()}
    assert read == runtime


def test_every_dispatch_gather_is_called_by_an_unmarked_module() -> None:
    assert uncalled_gathers(_this_package()) == []


def test_every_check_code_is_named_by_an_unmarked_module_or_pinned_as_a_gap() -> None:
    package = _this_package()
    assert len(check_codes(package)) >= 200
    assert unnamed_codes(package, _UNNAMED_CHECK_CODES) == []


def test_the_gap_list_only_shrinks() -> None:
    assert len(_UNNAMED_CHECK_CODES) <= _GAP_CEILING
    assert stale_gaps(_this_package(), _UNNAMED_CHECK_CODES) == []


def test_the_package_half_holds_only_the_environment_skips() -> None:
    assert skip_problems(_this_package(), _ENVIRONMENT_SKIPS) == []


# --------------------------------------------------------------------------------------------------
# Each rule fires on synthetic input.
# --------------------------------------------------------------------------------------------------

_SYN_MARKER = "syn_tree"
_SYN_MAIN = (
    "from . import alpha, beta\n"
    "DISPATCH = {\n"
    '    "alpha-source": alpha.gather,\n'
    '    "beta-source": beta.gather_beta,\n'
    "}\n"
)
_SYN_ALPHA = (
    "from ..models import Finding\n"
    "_SILENT = 'syn-code-silent'\n"
    "def gather(target):\n"
    "    return (Finding(source='alpha', check='syn-code-named', status='ok', message=''),\n"
    "            Finding(source='alpha', check=_SILENT, status='warn', message=''))\n"
)
_SYN_BETA = (
    "from ..models import Finding\n"
    "def gather_beta(target):\n"
    "    return (Finding(source='beta', check='syn-code-by-constant', status='ok', message=''),)\n"
    "BETA_CODE = 'syn-code-by-constant'\n"
)


def _syn(tests: Mapping[str, str], src: Mapping[str, str] | None = None) -> Package:
    base = {
        "__init__.py": "",
        "models.py": "class Finding: ...\n",
        "sources/__init__.py": "",
        "sources/__main__.py": _SYN_MAIN,
        "sources/alpha.py": _SYN_ALPHA,
        "sources/beta.py": _SYN_BETA,
    }
    return Package({**base, **(src or {})}, dict(tests), _SYN_MARKER)


_SYN_FULL = (
    "from pyforge.doctor.sources import alpha, beta\n"
    "from pyforge.doctor.sources import __main__\n"
    "def test_a():\n"
    "    assert alpha.gather(None)[0].check == 'syn-code-named'\n"
    "    assert alpha.gather(None)[1].check == alpha._SILENT\n"
    "    assert beta.gather_beta(None)[0].check == beta.BETA_CODE\n"
)


def test_the_oracle_fires_on_nothing_when_the_half_covers_the_package() -> None:
    package = _syn({"unit/test_syn.py": _SYN_FULL})
    assert unimported_sources(package) == []
    assert uncalled_gathers(package) == []
    assert unnamed_codes(package, {}) == []
    assert skip_problems(package, {}) == []


def test_the_oracle_fires_on_a_gather_no_unmarked_module_calls() -> None:
    package = _syn(
        {
            "unit/test_syn.py": _SYN_FULL.replace("    assert beta.gather_beta(None)[0].check == beta.BETA_CODE\n", ""),
            "unit/test_live_syn.py": (
                f"import pytest\nfrom pyforge.doctor.sources import beta\npytestmark = pytest.mark.{_SYN_MARKER}\n"
                "def test_b():\n    beta.gather_beta(None)\n"
            ),
        }
    )
    assert uncalled_gathers(package) == ["beta-source: pyforge.doctor.sources.beta.gather_beta"]


def test_the_oracle_fires_on_a_call_made_only_from_a_marked_function() -> None:
    package = _syn(
        {
            "unit/test_syn.py": _SYN_FULL.replace("    assert beta.gather_beta(None)[0].check == beta.BETA_CODE\n", "")
            + f"import pytest\n@pytest.mark.{_SYN_MARKER}\ndef test_b():\n    beta.gather_beta(None)\n",
        }
    )
    assert uncalled_gathers(package) == ["beta-source: pyforge.doctor.sources.beta.gather_beta"]


def test_the_oracle_fires_on_a_check_code_no_unmarked_module_names() -> None:
    package = _syn(
        {
            "unit/test_syn.py": _SYN_FULL.replace(" == alpha._SILENT", ""),
            "unit/test_live_syn.py": (
                f"import pytest\npytestmark = [pytest.mark.{_SYN_MARKER}]\n"
                "def test_b():\n    assert 'syn-code-silent'\n"
            ),
        }
    )
    assert unnamed_codes(package, {}) == ["syn-code-silent"]
    assert unnamed_codes(package, {"syn-code-silent": "a reason"}) == []


def test_the_oracle_fires_on_a_source_module_no_unmarked_module_imports() -> None:
    package = _syn(
        {"unit/test_syn.py": _SYN_FULL},
        {"sources/gamma.py": "def helper():\n    return 1\n"},
    )
    assert unimported_sources(package) == ["sources/gamma.py"]
    covered = _syn(
        {"unit/test_syn.py": _SYN_FULL + "import importlib\nimportlib.import_module('pyforge.doctor.sources.gamma')\n"},
        {"sources/gamma.py": "def helper():\n    return 1\n"},
    )
    assert unimported_sources(covered) == []


def test_the_oracle_fires_on_a_skip_in_an_unmarked_module() -> None:
    package = _syn(
        {
            "unit/test_syn.py": _SYN_FULL + "import pytest as pt\ndef test_c():\n    pt.skip('not on this tree')\n",
            "unit/test_other.py": (
                "from pytest import importorskip, mark as m\n_needs = m.skipif(True, reason='x')\nimportorskip('yaml')\n"
            ),
            "unit/test_live_syn.py": (
                f"import pytest as pt\npytestmark = pt.mark.{_SYN_MARKER}\ndef test_d():\n    pt.skip('live only')\n"
            ),
        }
    )
    assert skips(package) == {"unit/test_other.py": 2, "unit/test_syn.py": 1}
    assert skip_problems(package, {"unit/test_other.py": (2, "two environment skips")}) == [
        "unit/test_syn.py: 1 skip(s) in the package half, 0 pinned"
    ]
    assert skip_problems(package, {"unit/test_other.py": (2, "x"), "unit/test_syn.py": (1, "x")}) == []
    assert skip_problems(package, {"unit/test_gone.py": (1, "x"), "unit/test_other.py": (2, "x")}) == [
        "unit/test_syn.py: 1 skip(s) in the package half, 0 pinned",
        "unit/test_gone.py: pinned 1 skip(s), the module holds none -- shrink the pin",
    ]


def test_the_oracle_fires_on_a_gap_entry_that_is_no_longer_a_gap() -> None:
    package = _syn({"unit/test_syn.py": _SYN_FULL})
    assert stale_gaps(package, {"syn-code-named": "x", "syn-code-unknown": "y"}) == [
        "syn-code-named: an unmarked module names it now -- remove it from the gap list (it only shrinks)",
        "syn-code-unknown: no such check code under src/ -- remove it from the gap list",
    ]
    narrowed = _syn({"unit/test_syn.py": _SYN_FULL.replace(" == alpha._SILENT", "")})
    assert stale_gaps(narrowed, {"syn-code-silent": "   "}) == ["syn-code-silent: the gap entry gives no reason"]


def test_the_oracle_fires_when_the_dispatch_reader_cannot_read_an_entry() -> None:
    package = _syn(
        {"unit/test_syn.py": _SYN_FULL}, {"sources/__main__.py": _SYN_MAIN.replace("}\n", '    "x": f(),\n}\n')}
    )
    assert uncalled_gathers(package) == ["x: <unreadable>.f()"]


def test_the_tree_marker_is_the_one_the_package_declares() -> None:
    declared = (
        '[tool.pytest.ini_options]\nmarkers = ["slow: takes long", '
        '"syn_tree: the module reads the repository outside its own package"]\n'
    )
    assert _tree_marker(declared) == _SYN_MARKER
    assert _tree_marker((_package_root() / "pyproject.toml").read_text(encoding="utf-8")) == _this_package().marker
