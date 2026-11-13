"""Story 118.1 / spec-pyforge-testing-charter:CAP-6 (FR-253): the kit's public surface is written down, and this holds it.

The contract is the Spec companion ``spec-pyforge-testing-charter/contract.md``. This test derives the kit side from
the source with ``ast`` (nothing is imported) and from the kit's ``pyproject.toml``, reads the contract side from the
companion, and fails naming each item one side has and the other lacks:

* **module** and **public name**: one ``### `pyforge.testing_kit[.<module>]` `` heading per module under
  ``## Modules``; the package's public names are its ``__all__``, a submodule's are its module-level functions,
  classes and assignments whose names do not start with ``_``;
* **fixture**: every ``@pytest.fixture`` the source defines (its ``name=``, a literal or a module constant, else the
  function's name), under ``### Fixtures``;
* **marker**: every ``pytest.mark.<name>`` the source applies and every marker the suite's ``pyproject.toml``
  declares, under ``### Markers``;
* **run-dependency**: ``[project] dependencies``, under ``## Run-dependencies``;
* **Python floor**: ``requires-python``, under ``## Python floor``;
* **estate-bound member**: each module ``## Estate-bound members`` names must be a module of the kit.

The contract is read by its headings and the first backticked token of each ``- `` bullet line; prose is not read.
It reads outside the package (the Spec folder), so it is a live-tree test.
"""

from __future__ import annotations

import ast
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_tree

# tests/meta -> tests -> pyforge-testing-kit -> packages -> shared -> src -> repo root
_KIT = Path(__file__).resolve().parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[6]
CONTRACT = (
    _REPO_ROOT
    / "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/contract.md"
)

PACKAGE = "pyforge.testing_kit"
MODULES = "Modules"
FIXTURES = "Fixtures"
MARKERS = "Markers"
RUN_DEPENDENCIES = "Run-dependencies"
ESTATE_BOUND = "Estate-bound members"
PYTHON_FLOOR = "Python floor"

_H2 = re.compile(r"^## (.+?)\s*$")
_H3 = re.compile(r"^### (.+?)\s*$")
_BULLET = re.compile(r"^- `([^`]+)`")
_TICK = re.compile(r"`([^`]+)`")
_VERSION = re.compile(r"^\d+\.\d+$")
_FLOOR = re.compile(r">=\s*(\d+\.\d+)")
_DIST = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclass
class Surface:
    """One side of the contract: what the kit's source declares, or what ``contract.md`` records."""

    modules: dict[str, set[str]] = field(default_factory=dict)  # dotted module -> public names
    fixtures: set[str] = field(default_factory=set)
    markers: set[str] = field(default_factory=set)
    run_dependencies: set[str] = field(default_factory=set)
    python_floor: str | None = None
    estate_bound: set[str] = field(default_factory=set)  # contract side only


# --------------------------------------------------------------------------- the kit side


def _string_constants(tree: ast.Module) -> dict[str, str]:
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name) and isinstance(value, ast.Constant) and isinstance(value.value, str):
            constants[target.id] = value.value
    return constants


def _dunder_all(tree: ast.Module, where: str) -> set[str]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            if not isinstance(node.value, (ast.List, ast.Tuple)) or not all(
                isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.value.elts
            ):
                raise AssertionError(f"{where}: __all__ is not a literal list of strings, so it cannot be checked")
            return {e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    raise AssertionError(f"{where}: the package declares no __all__, so its public names cannot be checked")


def _assigned_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for elt in target.elts for name in _assigned_names(elt)]
    return []


def _public_names(tree: ast.Module) -> set[str]:
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            names.extend(name for target in node.targets for name in _assigned_names(target))
        elif isinstance(node, ast.AnnAssign):
            names.extend(_assigned_names(node.target))
    return {name for name in names if not name.startswith("_")}


def _is_pytest_attr(node: ast.expr, attr: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == attr
        and isinstance(node.value, ast.Name)
        and (node.value.id == "pytest")
    )


def _fixtures(tree: ast.Module) -> set[str]:
    constants = _string_constants(tree)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            call = decorator if isinstance(decorator, ast.Call) else None
            if not _is_pytest_attr(call.func if call else decorator, "fixture"):
                continue
            name = next((kw.value for kw in call.keywords if kw.arg == "name"), None) if call else None
            if isinstance(name, ast.Constant) and isinstance(name.value, str):
                found.add(name.value)
            elif isinstance(name, ast.Name) and name.id in constants:
                found.add(constants[name.id])
            elif name is None:
                found.add(node.name)
            else:
                raise AssertionError(f"fixture `{node.name}` takes a name that is no literal or module constant")
    return found


def _applied_markers(tree: ast.Module) -> set[str]:
    return {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute) and _is_pytest_attr(node.value, "mark")
    }


def derive_kit(kit: Path) -> Surface:
    """Everything the kit at ``kit`` declares, read from its source and ``pyproject.toml``."""
    surface = Surface()
    source = kit / "src" / "pyforge" / "testing_kit"
    for path in sorted(source.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if path.stem == "__init__":
            surface.modules[PACKAGE] = _dunder_all(tree, f"{PACKAGE}/__init__.py")
        else:
            surface.modules[f"{PACKAGE}.{path.stem}"] = _public_names(tree)
        surface.fixtures |= _fixtures(tree)
        surface.markers |= _applied_markers(tree)
    with (kit / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    project = pyproject["project"]
    for requirement in project.get("dependencies", []):
        match = _DIST.match(requirement.strip())
        assert match, f"unparseable requirement {requirement!r} in pyproject.toml"
        surface.run_dependencies.add(match.group(0).lower())
    floor = _FLOOR.search(project.get("requires-python", ""))
    surface.python_floor = floor.group(1) if floor else None
    ini = pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {})
    surface.markers |= {marker.split(":", 1)[0].strip() for marker in ini.get("markers", [])}
    return surface


# --------------------------------------------------------------------------- the contract side


def _sections(lines: list[str], heading: re.Pattern[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lines:
        match = heading.match(line)
        if match is not None:
            current = sections.setdefault(match.group(1), [])
        elif current is not None:
            current.append(line)
    return sections


def _bullets(lines: list[str]) -> set[str]:
    return {match.group(1) for line in lines if (match := _BULLET.match(line)) is not None}


def read_contract(text: str) -> Surface:
    """What ``contract.md`` records."""
    recorded = Surface()
    top = _sections(text.splitlines(), _H2)
    for title, body in _sections(top.get(MODULES, []), _H3).items():
        module = _TICK.fullmatch(title)
        if module is not None:
            recorded.modules[module.group(1)] = _bullets(body)
    fixtures_and_markers = _sections(top.get("Fixtures and markers", []), _H3)
    recorded.fixtures = _bullets(fixtures_and_markers.get(FIXTURES, []))
    recorded.markers = _bullets(fixtures_and_markers.get(MARKERS, []))
    recorded.run_dependencies = {name.lower() for name in _bullets(top.get(RUN_DEPENDENCIES, []))}
    recorded.estate_bound = _bullets(top.get(ESTATE_BOUND, []))
    versions = [token for token in _TICK.findall("\n".join(top.get(PYTHON_FLOOR, []))) if _VERSION.match(token)]
    recorded.python_floor = versions[0] if versions else None
    return recorded


# --------------------------------------------------------------------------- the comparison


def _both_ways(kind: str, section: str, kit: set[str], recorded: set[str]) -> list[str]:
    return [
        f"{kind} `{item}` is in the kit and absent from contract.md § {section}" for item in sorted(kit - recorded)
    ] + [f"contract.md § {section} names {kind} `{item}`, which the kit lacks" for item in sorted(recorded - kit)]


def compare(kit: Surface, recorded: Surface) -> list[str]:
    """One finding per item one side has and the other lacks, naming the item."""
    findings = _both_ways("module", MODULES, set(kit.modules), set(recorded.modules))
    for module in sorted(set(kit.modules) & set(recorded.modules)):
        findings += _both_ways("public name", f"{MODULES} `{module}`", kit.modules[module], recorded.modules[module])
    findings += _both_ways("fixture", FIXTURES, kit.fixtures, recorded.fixtures)
    findings += _both_ways("marker", MARKERS, kit.markers, recorded.markers)
    findings += _both_ways("run-dependency", RUN_DEPENDENCIES, kit.run_dependencies, recorded.run_dependencies)
    if kit.python_floor != recorded.python_floor:
        findings.append(
            f"Python floor: the kit requires `{kit.python_floor}` and contract.md § {PYTHON_FLOOR} records "
            f"`{recorded.python_floor}`"
        )
    findings += [
        f"contract.md § {ESTATE_BOUND} names module `{module}`, which the kit lacks"
        for module in sorted(recorded.estate_bound - set(kit.modules))
    ]
    return findings


# --------------------------------------------------------------------------- the real kit and contract


@pytest.fixture(scope="module")
def kit_side() -> Surface:
    return derive_kit(_KIT)


@pytest.fixture(scope="module")
def contract_text() -> str:
    assert CONTRACT.is_file(), f"the contract companion is missing: {CONTRACT}"
    return CONTRACT.read_text(encoding="utf-8")


def test_the_kit_side_is_derived_not_empty(kit_side: Surface) -> None:
    """A scan that finds nothing would pass vacuously: every family reads something real."""
    assert kit_side.modules.get(PACKAGE), "the package's __all__ was not read"
    assert len(kit_side.modules) > 1, "no submodule was read"
    assert "make_flag_provider_fixture" in kit_side.modules[f"{PACKAGE}.flags"]
    assert "flag_provider" in kit_side.fixtures  # the name= is a module constant: proves constant resolution
    assert {"parametrize", "live_tree"} <= kit_side.markers
    assert "pyforge-core" in kit_side.run_dependencies
    assert kit_side.python_floor is not None


def test_the_contract_side_is_read_not_empty(contract_text: str) -> None:
    recorded = read_contract(contract_text)
    assert recorded.modules.get(PACKAGE), "contract.md § Modules records no name for the package"
    assert recorded.fixtures and recorded.markers and recorded.run_dependencies and recorded.estate_bound
    assert recorded.python_floor is not None


def test_contract_and_kit_agree(kit_side: Surface, contract_text: str) -> None:
    findings = compare(kit_side, read_contract(contract_text))
    assert not findings, "contract.md and the kit differ:\n" + "\n".join(findings)


# --------------------------------------------------------------------------- synthetic proof

_SYNTHETIC_INIT = '"""A kit."""\n\nfrom pyforge.testing_kit.alpha import Thing\n\n__all__ = ["Thing"]\n'
_SYNTHETIC_ALPHA = '''"""One module."""

import pytest

LIMIT = 3
FIXTURE_NAME = "probe"
_PRIVATE = 1


class Thing:
    pass


def helper() -> None:
    pytest.mark.usefixtures(FIXTURE_NAME)


def _hidden() -> None:
    pass


def make() -> object:
    @pytest.fixture(name=FIXTURE_NAME)
    def probe() -> None:
        pass

    return probe
'''
_SYNTHETIC_PYPROJECT = """[project]
name = "kit"
requires-python = ">=3.14"
dependencies = ["dep-a>=1.0", "Dep_B"]

[tool.pytest.ini_options]
markers = ["live_tree: reads outside"]
"""
_SYNTHETIC_CONTRACT = """# Contract

Prose naming `Ghost` is not read.

## Modules

### `pyforge.testing_kit`

- `Thing` — re-exported.

### `pyforge.testing_kit.alpha`

- `LIMIT` — a constant.
- `FIXTURE_NAME` — the fixture's name.
- `Thing` — a class.
- `helper` — a function.
- `make` — builds the fixture.

## Fixtures and markers

### Fixtures

- `probe` — built by `make()`.

### Markers

- `usefixtures` — applied by `helper`.
- `live_tree` — declared by the suite.

## Run-dependencies

- `dep-a` — one.
- `dep_b` — two.

## Estate-bound members

- `pyforge.testing_kit.alpha` — bound here.

## Python floor

`3.14` — the floor.
"""


def _synthetic_kit(root: Path, **extra: str) -> Path:
    source = root / "src" / "pyforge" / "testing_kit"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text(_SYNTHETIC_INIT, encoding="utf-8")
    (source / "alpha.py").write_text(_SYNTHETIC_ALPHA, encoding="utf-8")
    for name, text in extra.items():
        (source / f"{name}.py").write_text(text, encoding="utf-8")
    (root / "pyproject.toml").write_text(_SYNTHETIC_PYPROJECT, encoding="utf-8")
    return root


def _swap(old: str, new: str) -> str:
    assert old in _SYNTHETIC_CONTRACT, f"mutation premise: {old!r} is in the synthetic contract"
    return _SYNTHETIC_CONTRACT.replace(old, new, 1)


def test_the_synthetic_kit_and_contract_agree(tmp_path: Path) -> None:
    assert compare(derive_kit(_synthetic_kit(tmp_path)), read_contract(_SYNTHETIC_CONTRACT)) == []


@pytest.mark.parametrize(
    ("contract", "finding"),
    [
        pytest.param(
            _swap("### `pyforge.testing_kit.alpha`\n", "### Alpha\n"),
            "module `pyforge.testing_kit.alpha` is in the kit and absent from contract.md § Modules",
            id="kit-module-missing",
        ),
        pytest.param(
            _swap("- `helper` — a function.\n", ""),
            "public name `helper` is in the kit and absent from contract.md § Modules `pyforge.testing_kit.alpha`",
            id="kit-name-missing",
        ),
        pytest.param(
            _swap("- `Thing` — re-exported.\n", ""),
            "public name `Thing` is in the kit and absent from contract.md § Modules `pyforge.testing_kit`",
            id="all-name-missing",
        ),
        pytest.param(
            _swap(
                "## Fixtures and markers", "### `pyforge.testing_kit.beta`\n\n- `gone` — x.\n\n## Fixtures and markers"
            ),
            "contract.md § Modules names module `pyforge.testing_kit.beta`, which the kit lacks",
            id="contract-module-extra",
        ),
        pytest.param(
            _swap("- `make` — builds the fixture.\n", "- `make` — builds the fixture.\n- `ghost` — gone.\n"),
            "contract.md § Modules `pyforge.testing_kit.alpha` names public name `ghost`, which the kit lacks",
            id="contract-name-extra",
        ),
        pytest.param(
            _swap("- `probe` — built by `make()`.\n", ""),
            "fixture `probe` is in the kit and absent from contract.md § Fixtures",
            id="fixture-missing",
        ),
        pytest.param(
            _swap("- `live_tree` — declared by the suite.\n", ""),
            "marker `live_tree` is in the kit and absent from contract.md § Markers",
            id="marker-missing",
        ),
        pytest.param(
            _swap("- `dep_b` — two.\n", "- `dep_b` — two.\n- `dep-c` — three.\n"),
            "contract.md § Run-dependencies names run-dependency `dep-c`, which the kit lacks",
            id="run-dependency-extra",
        ),
        pytest.param(
            _swap("`3.14` — the floor.", "`3.12` — the floor."),
            "Python floor: the kit requires `3.14` and contract.md § Python floor records `3.12`",
            id="floor-differs",
        ),
        pytest.param(
            _swap("- `pyforge.testing_kit.alpha` — bound here.\n", "- `pyforge.testing_kit.gamma` — bound here.\n"),
            "contract.md § Estate-bound members names module `pyforge.testing_kit.gamma`, which the kit lacks",
            id="estate-bound-module-unknown",
        ),
    ],
)
def test_a_planted_gap_in_the_contract_is_named(tmp_path: Path, contract: str, finding: str) -> None:
    assert compare(derive_kit(_synthetic_kit(tmp_path)), read_contract(contract)) == [finding]


def test_a_new_kit_module_is_named(tmp_path: Path) -> None:
    kit = _synthetic_kit(tmp_path, beta='"""Another module."""\n\nVALUE = 1\n')
    assert compare(derive_kit(kit), read_contract(_SYNTHETIC_CONTRACT)) == [
        "module `pyforge.testing_kit.beta` is in the kit and absent from contract.md § Modules"
    ]


def test_a_new_public_name_is_named_and_a_private_one_is_not(tmp_path: Path) -> None:
    kit = _synthetic_kit(tmp_path)
    alpha = kit / "src" / "pyforge" / "testing_kit" / "alpha.py"
    alpha.write_text(alpha.read_text(encoding="utf-8") + "\nNEW, _ALSO_PRIVATE = 1, 2\n", encoding="utf-8")
    assert compare(derive_kit(kit), read_contract(_SYNTHETIC_CONTRACT)) == [
        "public name `NEW` is in the kit and absent from contract.md § Modules `pyforge.testing_kit.alpha`"
    ]


def test_a_package_without_a_literal_all_is_refused(tmp_path: Path) -> None:
    kit = _synthetic_kit(tmp_path)
    (kit / "src" / "pyforge" / "testing_kit" / "__init__.py").write_text("__all__ = sorted(['Thing'])\n")
    with pytest.raises(AssertionError, match="not a literal list of strings"):
        derive_kit(kit)
