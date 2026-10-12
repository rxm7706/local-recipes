"""Story 91.1 AC7: module-scope import boundaries for the stations index gate."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
ROOT = next(p for p in _HERE.parents if (p / "pixi.toml").is_file() and (p / "AGENTS.md").is_file())
PLATFORM = ROOT / "src" / "platform"
GUARDED_FILES = (
    PLATFORM / "config" / "stations_index.py",
    PLATFORM / "config" / "urls.py",
)
_SETTINGS_BASE = PLATFORM / "config" / "settings" / "base.py"
_STATION_API = "config.station_api"
# Calls that import a module named by their first argument.
_DYNAMIC_IMPORT_CALLS = frozenset({"importlib.import_module", "import_module", "__import__", "importlib.__import__"})


def _portal_module_names() -> frozenset[str]:
    tree = ast.parse(_SETTINGS_BASE.read_text(encoding="utf-8"), filename=str(_SETTINGS_BASE))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_STATION_PORTAL_PACKAGES":
                    value = ast.literal_eval(node.value)
                    return frozenset(module for _, module in value)
    msg = "_STATION_PORTAL_PACKAGES not found in settings base"
    raise AssertionError(msg)


def _is_or_under(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


def _forbidden_module(module: str, portal_modules: frozenset[str]) -> bool:
    """`pyforge` or under it, a portal package or any of its submodules, or `config.station_api`."""
    forbidden = ("pyforge", _STATION_API, *portal_modules)
    return any(_is_or_under(module, package) for package in forbidden)


def _resolve_from(package: str, level: int, module: str | None) -> str | None:
    """The absolute module an `ImportFrom` names, relative imports resolved against `package`."""
    if level == 0:
        return module
    parts = package.split(".")
    if level - 1 >= len(parts):
        return None
    base = ".".join(parts[: len(parts) - (level - 1)])
    return f"{base}.{module}" if module else base


def _dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _dotted_name(node.value)
        return f"{owner}.{node.attr}" if owner else None
    return None


class _ModuleScopeImports(ast.NodeVisitor):
    """Every module a file imports while it is itself being imported.

    Statement imports count anywhere their statement runs at import time: at top level, inside a
    module-level `if`, `try` or `with`, and in a class body. So does a dynamic import call with a
    literal module name (`importlib.import_module("config.station_api")`). A function or lambda
    body runs only when called, so it is skipped; its decorators and default values are not.
    """

    def __init__(self, package: str) -> None:
        self.package = package
        self.found: list[tuple[int, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.visit(node.args)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self.visit(node.args)

    def visit_Import(self, node: ast.Import) -> None:
        self.found.extend((node.lineno, alias.name) for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = _resolve_from(self.package, node.level, node.module)
        if module is None:
            return
        self.found.append((node.lineno, module))
        # `from config import station_api` imports the submodule `config.station_api`.
        self.found.extend((node.lineno, f"{module}.{alias.name}") for alias in node.names if alias.name != "*")

    def visit_Call(self, node: ast.Call) -> None:
        if _dotted_name(node.func) in _DYNAMIC_IMPORT_CALLS and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                self.found.append((node.lineno, first.value))
        self.generic_visit(node)


def _module_scope_imports(source: str, package: str) -> list[tuple[int, str]]:
    visitor = _ModuleScopeImports(package)
    visitor.visit(ast.parse(source))
    return visitor.found


def _findings(source: str, package: str, portal_modules: frozenset[str]) -> list[str]:
    return [
        f"{line}: {module}"
        for line, module in _module_scope_imports(source, package)
        if _forbidden_module(module, portal_modules)
    ]


def test_stations_index_files_import_nothing_forbidden_at_module_scope() -> None:
    portal_modules = _portal_module_names()
    findings: list[str] = []
    for path in GUARDED_FILES:
        rel = path.relative_to(ROOT).as_posix()
        package = ".".join(path.relative_to(PLATFORM).parent.parts)
        findings.extend(
            f"{rel}:{finding} (forbidden module-scope import)"
            for finding in _findings(path.read_text(encoding="utf-8"), package, portal_modules)
        )
    assert not findings, "\n".join(findings)


def test_portal_module_names_are_read_from_settings() -> None:
    assert {"django_herald_portal", "django_warden_fabric"} <= _portal_module_names()


_MUST_FLAG = {
    "import-pyforge": "import pyforge",
    "import-pyforge-submodule": "import pyforge.core",
    "from-pyforge": "from pyforge import core",
    "from-pyforge-submodule": "from pyforge.herald.deck import x",
    "import-station-api": "import config.station_api",
    "import-station-api-as": "import config.station_api as api",
    "from-config-import-station-api": "from config import station_api",
    "from-config-import-station-api-among-others": "from config import urls, station_api as api",
    "from-station-api": "from config.station_api import iter_station_apps",
    "relative-from-package": "from . import station_api",
    "relative-from-module": "from .station_api import iter_station_apps",
    "import-portal": "import django_herald_portal",
    "import-portal-submodule": "import django_herald_portal.views",
    "from-portal-submodule": "from django_warden_fabric.views import chrome_home",
    "from-portal-import-submodule": "from django_warden_fabric import views",
    "importlib-import-module": 'importlib.import_module("config.station_api")',
    "import-module-assigned": '_api = importlib.import_module("config.station_api")',
    "bare-import-module": 'import_module("config.station_api")',
    "dunder-import": '__import__("config.station_api")',
    "import-module-pyforge": 'importlib.import_module("pyforge.herald")',
    "import-module-portal-submodule": 'importlib.import_module("django_herald_portal.views")',
    "inside-if": "if True:\n    import config.station_api",
    "inside-else": "if False:\n    pass\nelse:\n    from config import station_api",
    "inside-try": "try:\n    import config.station_api\nexcept ImportError:\n    pass",
    "inside-except": "try:\n    pass\nexcept ImportError:\n    import config.station_api",
    "inside-finally": "try:\n    pass\nfinally:\n    from config import station_api",
    "inside-with": "with ctx():\n    from config import station_api",
    "import-module-inside-with": 'with ctx():\n    importlib.import_module("config.station_api")',
    "class-body": "class C:\n    import config.station_api",
    "decorator": 'def deco(f):\n    return f\n@deco(importlib.import_module("config.station_api"))\ndef f():\n    pass',
    "default-argument": 'def f(api=importlib.import_module("config.station_api")):\n    pass',
}

_MUST_NOT_FLAG = {
    "function-body-import-module": 'def f():\n    importlib.import_module("config.station_api")',
    "function-body-import": "def f():\n    import config.station_api",
    "async-function-body-from": "async def f():\n    from config import station_api",
    "method-body": "class C:\n    def m(self):\n        from config import station_api",
    "lambda-body": '_load = lambda: importlib.import_module("config.station_api")',
    "sibling-host-module": "from config import optional_components",
    "own-module": "from config.stations_index import stations_index",
    "relative-sibling": "from . import optional_components",
    "name-prefix-not-a-submodule": "import config.station_api_helpers",
    "portal-name-prefix-not-a-submodule": "import django_herald_portal_extra",
    "pyforge-name-prefix-not-a-submodule": "import pyforgery",
    "chrome-package": "from django_pyforge.roles import roles_from_request",
    "import-module-non-literal": "importlib.import_module(name)",
    "import-module-host-module": 'importlib.import_module("config.optional_components")',
}

_DETECTOR_PORTALS = frozenset({"django_herald_portal", "django_warden_fabric"})


@pytest.mark.parametrize("source", list(_MUST_FLAG.values()), ids=list(_MUST_FLAG))
def test_detector_flags_module_scope_import(source: str) -> None:
    assert _findings(textwrap.dedent(source), "config", _DETECTOR_PORTALS)


@pytest.mark.parametrize("source", list(_MUST_NOT_FLAG.values()), ids=list(_MUST_NOT_FLAG))
def test_detector_ignores_call_time_and_unrelated_imports(source: str) -> None:
    assert _findings(textwrap.dedent(source), "config", _DETECTOR_PORTALS) == []
