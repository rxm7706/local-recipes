"""Story 47.1 (spec-pyforge-atlas:CAP-73, FR-78): atlas's public contract is written beside the Spec, and this
meta-test holds the code to it.

``contract.md`` (a companion of ``spec-pyforge-atlas``) names every CLI verb and option, every MCP tool, every
feature-flag key, every environment variable and every exit code the package has. Each family below is DERIVED
from the code, never declared here, and every derived name must appear as a code token in its own section of
``contract.md``:

- verbs: Kedro's project command group (``__main__.discover_cli_verbs``) plus the first-token flags ``main``
  answers before Kedro loads (``--version``);
- options: each Click command's params for the Kedro group, and the literal ``add_argument`` names of every
  ``python -m`` entry point under ``src/`` and every ``tools/`` script;
- MCP tools: ``mcp.tools.TOOL_SPECS``;
- flag keys: string constants passed to a ``pyforge.core.flags`` reader or bound to a ``*FLAG_KEY`` name; the
  derived set must also equal the ``pyforge.atlas.*`` keys of the flag tree (a logger or hook name that shares
  the prefix is not a key);
- environment variables: ``os.environ.get`` / ``os.environ[...]`` / ``os.getenv`` in ``src/`` and ``tools/``
  (a Name resolved to its module-level string constant; a read through a variable resolved from the call sites,
  the table or the config interpolations that feed it), plus every ``${env_or:NAME,…}`` in ``conf/base/*.yml``;
- exit codes: the integer returns of each entry point's ``main`` (and of the same-module function it returns),
  and every literal ``SystemExit`` / ``sys.exit`` code, under ``## Exit codes``.

Each family has one negative case (``-k absent``) that adds a synthetic name to the derived set and expects the
comparison to fail. The module reads the Spec folder and the flag tree, so it runs in the live-tree half.
"""

from __future__ import annotations

import ast
import functools
import inspect
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_tree

_CONTRACT_RELATIVE = Path("_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md")
_FLAGS_RELATIVE = Path("src/platform/config/flags.json")
_FLAG_PREFIX = "pyforge.atlas."
_CODE_TOKEN = re.compile(r"`([^`\n]+)`")
_ENVIRON_GETTERS = frozenset({"os.environ.get", "os.getenv"})
_EXIT_CALLS = frozenset({"SystemExit", "sys.exit"})
_MAX_DEPTH = 8


# --------------------------------------------------------------------------- paths (computed, never at import)


def _member_root() -> Path:
    """The atlas member (``src/shared/packages/pyforge-atlas``): tests/meta/<this file> -> parents[2]."""
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    for candidate in _member_root().parents:
        if (candidate / _FLAGS_RELATIVE).is_file() and (candidate / _CONTRACT_RELATIVE).parent.is_dir():
            return candidate
    raise AssertionError(f"no repository root above {_member_root()} holds {_FLAGS_RELATIVE} and the atlas Spec")


def _package_dir() -> Path:
    return _member_root() / "src" / "pyforge" / "atlas"


def _src_files() -> list[Path]:
    return sorted((_member_root() / "src").rglob("*.py"))


def _tool_scripts() -> list[Path]:
    return sorted((_member_root() / "tools").glob("*.py"))


# --------------------------------------------------------------------------- parsed modules


class _Module:
    """One parsed source file: its tree, parent links, module-level constants and module-level functions."""

    def __init__(self, source: str, name: str) -> None:
        self.name = name
        self.tree = ast.parse(source, filename=name)
        self.parents: dict[ast.AST, ast.AST] = {
            child: node for node in ast.walk(self.tree) for child in ast.iter_child_nodes(node)
        }
        self.constants = _module_constants(self.tree)
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {
            node.name: node for node in self.tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def enclosing_function(self, node: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        current = self.parents.get(node)
        while current is not None and not isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            current = self.parents.get(current)
        return current

    def literal(self, name: str) -> object | None:
        """The literal value of a module-level assignment to ``name`` (a table), or None."""
        for node in self.tree.body:
            target, value = _assignment(node)
            if isinstance(target, ast.Name) and target.id == name and value is not None:
                try:
                    return ast.literal_eval(value)
                except ValueError, TypeError, SyntaxError:
                    return None
        return None


def _assignment(node: ast.AST) -> tuple[ast.expr | None, ast.expr | None]:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        return node.targets[0], node.value
    if isinstance(node, ast.AnnAssign):
        return node.target, node.value
    return None, None


def _module_constants(tree: ast.Module) -> dict[str, str | int]:
    constants: dict[str, str | int] = {}
    for node in tree.body:
        target, value = _assignment(node)
        if not isinstance(target, ast.Name) or value is None:
            continue
        if isinstance(value, ast.Constant) and type(value.value) in (str, int):
            constants[target.id] = value.value
        elif isinstance(value, ast.Name) and value.id in constants:
            constants[target.id] = constants[value.id]
    return constants


@functools.cache
def _module(path: Path) -> _Module:
    return _Module(path.read_text(encoding="utf-8"), path.relative_to(_member_root()).as_posix())


def _has_main_guard(module: _Module) -> bool:
    for node in module.tree.body:
        if (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            and any(isinstance(c, ast.Constant) and c.value == "__main__" for c in node.test.comparators)
        ):
            return True
    return False


def _entry_name(path: Path) -> str:
    """How a reader invokes the file: ``pyforge atlas``, ``python -m pyforge.atlas.<mod>`` or ``tools/<x>.py``."""
    relative = path.relative_to(_member_root())
    if relative.parts[0] == "tools":
        return relative.as_posix()
    parts = path.relative_to(_member_root() / "src").with_suffix("").parts
    if parts[-1] == "__main__":
        parts = parts[:-1]
    dotted = ".".join(parts)
    return "pyforge atlas" if dotted == "pyforge.atlas" else f"python -m {dotted}"


def _python_m_entry_points() -> list[Path]:
    root_main = _package_dir() / "__main__.py"
    return [path for path in _src_files() if path != root_main and _has_main_guard(_module(path))]


def _entry_points() -> list[Path]:
    """Every file a reader runs: the Kedro dispatch, the ``python -m`` modules and the guarded tools scripts."""
    return [path for path in _src_files() + _tool_scripts() if _has_main_guard(_module(path))]


def _own_nodes(function: ast.AST) -> Iterable[ast.AST]:
    """The nodes of ``function``'s own body, never descending into a nested function, lambda or class."""
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))


# --------------------------------------------------------------------------- the contract file


@functools.cache
def _contract_text() -> str:
    return (_repo_root() / _CONTRACT_RELATIVE).read_text(encoding="utf-8")


def _tokens(text: str) -> set[str]:
    return set(_CODE_TOKEN.findall(text))


def _section(contract: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", contract)
    return match.group(1) if match else ""


def _subsection_tokens(section: str) -> dict[str, set[str]]:
    """``### `<entry>` `` subsections: the heading's first code token -> the code tokens of its body."""
    blocks: dict[str, set[str]] = {}
    for match in re.finditer(r"(?ms)^### ([^\n]*)\n(.*?)(?=^### |\Z)", section):
        heading = _CODE_TOKEN.findall(match.group(1))
        if heading:
            blocks[heading[0]] = _tokens(match.group(2))
    return blocks


def _row_tokens(section: str) -> dict[str, set[str]]:
    """Table rows whose first cell is one code token: that token -> the code tokens of the rest of the row."""
    rows: dict[str, set[str]] = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = line.strip().strip("|").split("|")
        first = _CODE_TOKEN.findall(cells[0])
        if len(first) == 1:
            rows[first[0]] = _tokens("|".join(cells[1:]))
    return rows


def missing_names(derived: Iterable[str], section: str) -> list[str]:
    """The derived names that are not a code token of ``section``."""
    present = _tokens(section)
    return sorted(name for name in derived if name not in present)


def missing_by_entry(derived: Mapping[str, set[str]], blocks: Mapping[str, set[str]]) -> list[str]:
    """Per entry point: an entry the contract lacks, or a derived name its block lacks."""
    missing: list[str] = []
    for entry, names in sorted(derived.items()):
        if entry not in blocks:
            missing.append(f"{entry}: not in the contract")
            continue
        missing.extend(f"{entry}: {name}" for name in sorted(names - blocks[entry]))
    return missing


# --------------------------------------------------------------------------- family 1: verbs


def derive_verbs() -> set[str]:
    from pyforge.atlas.__main__ import discover_cli_verbs

    verbs = {f"pyforge atlas {name}" for name in discover_cli_verbs()}
    main = _module(_package_dir() / "__main__.py").functions["main"]
    for node in _own_nodes(main):
        if isinstance(node, ast.Compare):
            for comparator in node.comparators:
                if isinstance(comparator, ast.Constant) and str(comparator.value).startswith("--"):
                    verbs.add(f"pyforge atlas {comparator.value}")
    return verbs


# --------------------------------------------------------------------------- family 2: options


def _argparse_names(module: _Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            names.update(arg.value for arg in node.args if isinstance(arg, ast.Constant) and isinstance(arg.value, str))
    return names


def derive_options() -> dict[str, set[str]]:
    import click
    from kedro.framework.cli.project import project_group

    from pyforge.atlas.__main__ import discover_cli_verbs

    options: dict[str, set[str]] = {}
    for verb in sorted(discover_cli_verbs()):
        names: set[str] = set()
        for param in project_group.commands[verb].params:
            if isinstance(param, click.Option):
                names.update(param.opts)
                names.update(param.secondary_opts)
            elif param.name:
                names.add(param.name)
        options[f"pyforge atlas {verb}"] = names
    for path in _python_m_entry_points() + _tool_scripts():
        options[_entry_name(path)] = _argparse_names(_module(path))
    return options


# --------------------------------------------------------------------------- family 3: MCP tools


def derive_tools() -> set[str]:
    from pyforge.atlas.mcp.tools import TOOL_SPECS

    return set(TOOL_SPECS)


# --------------------------------------------------------------------------- family 4: flag keys


def _flag_readers() -> dict[str, int]:
    """The public ``pyforge.core.flags`` functions that take a ``key``, with its positional index."""
    from pyforge.core import flags

    readers: dict[str, int] = {}
    for name, function in inspect.getmembers(flags, inspect.isfunction):
        if name.startswith("_") or function.__module__ != flags.__name__:
            continue
        parameters = list(inspect.signature(function).parameters)
        if "key" in parameters:
            readers[name] = parameters.index("key")
    return readers


def _str_value(expr: ast.expr | None, module: _Module) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.Name):
        value = module.constants.get(expr.id)
        return value if isinstance(value, str) else None
    return None


def _flag_keys_in(module: _Module, readers: Mapping[str, int]) -> set[str]:
    local: dict[str, int] = {}
    aliases: set[str] = set()
    for node in ast.walk(module.tree):
        if isinstance(node, ast.ImportFrom) and node.module == "pyforge.core.flags":
            local.update({(a.asname or a.name): readers[a.name] for a in node.names if a.name in readers})
        elif isinstance(node, ast.ImportFrom) and node.module == "pyforge.core":
            aliases.update(a.asname or a.name for a in node.names if a.name == "flags")
    keys: set[str] = set()
    for node in ast.walk(module.tree):
        target, value = _assignment(node)
        if isinstance(target, ast.Name) and target.id.endswith("FLAG_KEY"):
            bound = _str_value(value, module)
            if bound is not None:
                keys.add(bound)
        if not isinstance(node, ast.Call):
            continue
        index: int | None = None
        if isinstance(node.func, ast.Name) and node.func.id in local:
            index = local[node.func.id]
        elif (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in aliases
            and node.func.attr in readers
        ):
            index = readers[node.func.attr]
        if index is None:
            continue
        arg = (
            node.args[index]
            if index < len(node.args)
            else next((k.value for k in node.keywords if k.arg == "key"), None)
        )
        key = _str_value(arg, module)
        if key is not None:
            keys.add(key)
    return keys


def derive_flag_keys() -> set[str]:
    readers = _flag_readers()
    keys: set[str] = set()
    for path in _src_files() + _tool_scripts():
        keys |= _flag_keys_in(_module(path), readers)
    return keys


def _tree_flag_keys() -> set[str]:
    tree = json.loads((_repo_root() / _FLAGS_RELATIVE).read_text(encoding="utf-8"))
    return {key for key in tree["flags"] if key.startswith(_FLAG_PREFIX)}


def flag_drift(derived: set[str], tree_keys: set[str]) -> list[str]:
    return sorted(
        [f"{key}: read by the code, absent from the flag tree" for key in derived - tree_keys]
        + [f"{key}: in the flag tree, absent from the code" for key in tree_keys - derived]
    )


# --------------------------------------------------------------------------- family 5: environment variables


def _environ_read(node: ast.AST) -> ast.expr | None:
    """The name argument of ``os.environ.get(X)``, ``os.getenv(X)`` or ``os.environ[X]``; else None."""
    if isinstance(node, ast.Call) and node.args and ast.unparse(node.func) in _ENVIRON_GETTERS:
        return node.args[0]
    if isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ":
        return node.slice
    return None


def _parameters(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    arguments = function.args
    return [a.arg for a in arguments.posonlyargs + arguments.args + arguments.kwonlyargs]


def _custom_resolvers(module: _Module) -> dict[str, str]:
    """``{"<resolver key>": <function>}`` dict entries: the config resolver key -> the function it names."""
    resolvers: dict[str, str] = {}
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(key.value, str) and isinstance(value, ast.Name):
                    resolvers[key.value] = value.id
    return resolvers


def _config_interpolations(resolver: str) -> set[str]:
    """Every ``${<resolver>:NAME,…}`` in ``conf/base/*.yml``."""
    pattern = re.compile(r"\$\{" + re.escape(resolver) + r":([A-Za-z_][A-Za-z0-9_]*)\s*,")
    names: set[str] = set()
    for path in sorted((_member_root() / "conf" / "base").glob("*.yml")):
        names.update(pattern.findall(path.read_text(encoding="utf-8")))
    return names


def _resolver_feed(function: ast.FunctionDef | ast.AsyncFunctionDef, module: _Module) -> set[str] | None:
    """A function no code calls but a config resolver table names is fed by that resolver's interpolations."""
    names: set[str] = set()
    for key, target in _custom_resolvers(module).items():
        if target == function.name:
            names |= _config_interpolations(key)
    return names or None


def _parameter_values(
    function: ast.FunctionDef | ast.AsyncFunctionDef, parameter: str, module: _Module, depth: int
) -> set[str] | None:
    """The values ``parameter`` takes, from every call of ``function`` in its module."""
    positional = [a.arg for a in function.args.posonlyargs + function.args.args]
    index = positional.index(parameter) if parameter in positional else None
    calls = [
        node
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == function.name
    ]
    if not calls:
        return _resolver_feed(function, module)
    values: set[str] = set()
    for call in calls:
        arg = call.args[index] if index is not None and index < len(call.args) else None
        if arg is None:
            arg = next((k.value for k in call.keywords if k.arg == parameter), None)
        if arg is None:
            continue
        fed = _values(arg, module.enclosing_function(call), module, depth + 1)
        if fed is None:
            return None
        values |= fed
    return values or None


def _loop_values(function: ast.FunctionDef | ast.AsyncFunctionDef, name: str, module: _Module) -> set[str] | None:
    """The values ``name`` takes as a ``for`` target over a module-level table."""
    for node in _own_nodes(function):
        if not isinstance(node, (ast.For, ast.comprehension)) or not isinstance(node.iter, ast.Name):
            continue
        table = module.literal(node.iter.id)
        if not isinstance(table, (tuple, list)):
            continue
        if isinstance(node.target, ast.Name) and node.target.id == name:
            rows = list(table)
        elif isinstance(node.target, ast.Tuple):
            slots = [i for i, e in enumerate(node.target.elts) if isinstance(e, ast.Name) and e.id == name]
            if not slots:
                continue
            rows = [row[slots[0]] for row in table]
        else:
            continue
        if rows and all(isinstance(row, str) for row in rows):
            return set(rows)
    return None


def _single_assignment(function: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> ast.expr | None:
    values = [
        node.value
        for node in _own_nodes(function)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == name
    ]
    return values[0] if len(values) == 1 else None


def _values(
    expr: ast.expr, function: ast.FunctionDef | ast.AsyncFunctionDef | None, module: _Module, depth: int = 0
) -> set[str] | None:
    """The string values ``expr`` takes, resolved from the code that feeds it; None when it cannot be resolved."""
    if depth > _MAX_DEPTH:
        return None
    constant = _str_value(expr, module)
    if constant is not None:
        return {constant}
    if isinstance(expr, ast.Name):
        if function is None:
            return None
        if expr.id in _parameters(function):
            return _parameter_values(function, expr.id, module, depth)
        looped = _loop_values(function, expr.id, module)
        if looped is not None:
            return looped
        assigned = _single_assignment(function, expr.id)
        return None if assigned is None else _values(assigned, function, module, depth + 1)
    # an expression over one name (an f-string over a parameter): evaluated for each value that name takes
    free = {n.id for n in ast.walk(expr) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    if len(free) != 1:
        return None
    (name,) = free
    inputs = _values(ast.Name(id=name, ctx=ast.Load()), function, module, depth + 1)
    if not inputs:
        return None
    code = compile(ast.Expression(body=expr), module.name, "eval")
    results = {eval(code, {"__builtins__": {}}, {name: value}) for value in inputs}
    return results if all(isinstance(result, str) for result in results) else None


def environment_reads(module: _Module) -> tuple[set[str], list[str]]:
    """The environment variable names ``module`` reads, and every read site it cannot resolve."""
    names: set[str] = set()
    unresolved: list[str] = []
    for node in ast.walk(module.tree):
        arg = _environ_read(node)
        if arg is None:
            continue
        values = _values(arg, module.enclosing_function(node), module)
        if values:
            names |= values
        else:
            unresolved.append(f"{module.name}:{getattr(node, 'lineno', '?')}")
    return names, unresolved


def derive_environment_variables() -> tuple[set[str], list[str]]:
    names: set[str] = set()
    unresolved: list[str] = []
    for path in _src_files() + _tool_scripts():
        found, open_sites = environment_reads(_module(path))
        names |= found
        unresolved.extend(open_sites)
    for resolver in _custom_resolvers(_module(_package_dir() / "settings.py")):
        names |= _config_interpolations(resolver)
    return names, unresolved


# --------------------------------------------------------------------------- family 6: exit codes


def _int_value(expr: ast.expr | None, module: _Module) -> int | None:
    if isinstance(expr, ast.Constant) and type(expr.value) is int:
        return expr.value
    if isinstance(expr, ast.Name):
        value = module.constants.get(expr.id)
        return value if type(value) is int else None
    return None


def _returned_codes(function: ast.FunctionDef | ast.AsyncFunctionDef, module: _Module, seen: set[str]) -> set[int]:
    if function.name in seen:
        return set()
    seen.add(function.name)
    codes: set[int] = set()
    for node in _own_nodes(function):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        code = _int_value(node.value, module)
        if code is not None:
            codes.add(code)
        elif (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in module.functions
        ):
            codes |= _returned_codes(module.functions[node.value.func.id], module, seen)
    return codes


def exit_codes_of(module: _Module) -> set[str]:
    codes: set[int] = set()
    main = module.functions.get("main")
    if main is not None:
        codes |= _returned_codes(main, module, set())
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call) and node.args and ast.unparse(node.func) in _EXIT_CALLS:
            code = _int_value(node.args[0], module)
            if code is not None:
                codes.add(code)
    return {str(code) for code in codes}


def derive_exit_codes() -> dict[str, set[str]]:
    return {_entry_name(path): exit_codes_of(_module(path)) for path in _entry_points()}


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def contract() -> str:
    return _contract_text()


@pytest.fixture(scope="module")
def verbs() -> set[str]:
    return derive_verbs()


@pytest.fixture(scope="module")
def options() -> dict[str, set[str]]:
    return derive_options()


@pytest.fixture(scope="module")
def environment() -> tuple[set[str], list[str]]:
    return derive_environment_variables()


@pytest.fixture(scope="module")
def exit_codes() -> dict[str, set[str]]:
    return derive_exit_codes()


# --------------------------------------------------------------------------- the code matches the contract


def test_every_verb_is_in_the_contract(contract: str, verbs: set[str]) -> None:
    assert verbs, "no verb derived from the Kedro project group"
    assert missing_names(verbs, _section(contract, "CLI verbs")) == []


def test_every_option_of_every_entry_point_is_in_the_contract(contract: str, options: dict[str, set[str]]) -> None:
    assert any(options.values()), "no option derived"
    assert missing_by_entry(options, _subsection_tokens(_section(contract, "CLI options"))) == []


def test_every_mcp_tool_is_in_the_contract(contract: str) -> None:
    tools = derive_tools()
    assert tools, "TOOL_SPECS is empty"
    assert missing_names(tools, _section(contract, "MCP tools")) == []


def test_every_flag_key_is_in_the_contract_and_the_flag_tree(contract: str) -> None:
    keys = derive_flag_keys()
    assert keys, "no flag key derived"
    assert flag_drift(keys, _tree_flag_keys()) == []
    assert missing_names(keys, _section(contract, "Feature flags")) == []


def test_every_environment_read_resolves(environment: tuple[set[str], list[str]]) -> None:
    names, unresolved = environment
    assert names, "no environment variable derived"
    assert unresolved == [], "an environment read the derivation cannot resolve: extend the resolver, never a list"


def test_every_environment_variable_is_in_the_contract(contract: str, environment: tuple[set[str], list[str]]) -> None:
    names, _ = environment
    assert missing_names(names, _section(contract, "Environment variables")) == []


def test_every_exit_code_is_in_the_contract(contract: str, exit_codes: dict[str, set[str]]) -> None:
    assert any(exit_codes.values()), "no exit code derived"
    assert missing_by_entry(exit_codes, _row_tokens(_section(contract, "Exit codes"))) == []


# --------------------------------------------------------------------------- one negative case per family


def test_a_verb_absent_from_the_contract_fails(contract: str, verbs: set[str]) -> None:
    synthetic = "pyforge atlas no-such-verb"
    assert missing_names(verbs | {synthetic}, _section(contract, "CLI verbs")) == [synthetic]


def test_an_option_absent_from_the_contract_fails(contract: str, options: dict[str, set[str]]) -> None:
    entry = "pyforge atlas run"
    broken = {**options, entry: options[entry] | {"--no-such-option"}}
    blocks = _subsection_tokens(_section(contract, "CLI options"))
    assert missing_by_entry(broken, blocks) == [f"{entry}: --no-such-option"]


def test_an_entry_point_absent_from_the_contract_fails(contract: str, options: dict[str, set[str]]) -> None:
    broken = {**options, "tools/no_such_tool.py": {"--flag"}}
    blocks = _subsection_tokens(_section(contract, "CLI options"))
    assert missing_by_entry(broken, blocks) == ["tools/no_such_tool.py: not in the contract"]


def test_a_tool_absent_from_the_contract_fails(contract: str) -> None:
    synthetic = "run_no_such_pipeline"
    assert missing_names(derive_tools() | {synthetic}, _section(contract, "MCP tools")) == [synthetic]


def test_a_flag_key_absent_from_the_contract_fails(contract: str) -> None:
    synthetic = "pyforge.atlas.no_such_switch"
    assert missing_names(derive_flag_keys() | {synthetic}, _section(contract, "Feature flags")) == [synthetic]


def test_a_flag_key_absent_from_the_code_or_the_tree_fails() -> None:
    keys = derive_flag_keys()
    tree = _tree_flag_keys()
    dropped = sorted(keys)[0]
    assert flag_drift(keys - {dropped}, tree) == [f"{dropped}: in the flag tree, absent from the code"]
    synthetic = "pyforge.atlas.no_such_switch"
    assert flag_drift(keys | {synthetic}, tree) == [f"{synthetic}: read by the code, absent from the flag tree"]


def test_an_environment_variable_absent_from_the_contract_fails(
    contract: str, environment: tuple[set[str], list[str]]
) -> None:
    names, _ = environment
    synthetic = "PYFORGE_ATLAS_NO_SUCH_VARIABLE"
    assert missing_names(names | {synthetic}, _section(contract, "Environment variables")) == [synthetic]


def test_an_environment_read_absent_from_any_resolution_fails() -> None:
    module = _Module("import os\n\ndef read(source):\n    return os.environ.get(source())\n", "synthetic.py")
    assert environment_reads(module) == (set(), ["synthetic.py:4"])


def test_an_exit_code_absent_from_the_contract_fails(contract: str, exit_codes: dict[str, set[str]]) -> None:
    entry = "tools/lasuite_bringup.py"
    broken = {**exit_codes, entry: exit_codes[entry] | {"77"}}
    rows = _row_tokens(_section(contract, "Exit codes"))
    assert missing_by_entry(broken, rows) == [f"{entry}: 77"]
