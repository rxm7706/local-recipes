"""Story 33.4 meta — exactly one publishing ``pyforge.core.client`` importer."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
PUBLISHER_ADAPTER = PACKAGE_DIR / "adapters" / "publisher_host.py"
LOGIN_ADAPTER = PACKAGE_DIR / "adapters" / "oidc_pkce.py"
MODEL_LIST_LIVE_ADAPTER = PACKAGE_DIR / "adapters" / "model_list_live.py"
CLI_ADAPTERS = PACKAGE_DIR / "cli" / "adapters.py"


def _module_paths() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _imports_client_for_publishing(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "pyforge.core.client":
            return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pyforge.core.client":
                    return True
    return False


def test_exactly_one_pyforge_core_client_importer_for_publishing() -> None:
    importers = [path for path in _module_paths() if _imports_client_for_publishing(path)]
    exempt = {LOGIN_ADAPTER}
    publish_importers = [path for path in importers if path not in exempt]
    assert publish_importers == [PUBLISHER_ADAPTER]
    assert LOGIN_ADAPTER in importers


#: The live model-list seam (Story 84.1): the adapter and the HTTP transport
#: it wraps. Dispatch, drain, spin and policy load never read a live list,
#: so outside the seam itself only ``cli/adapters.py`` may import either.
LIVE_LIST_MODULE = "pyforge.marshal.adapters.model_list_live"
LIVE_LIST_HTTP_MODULE = "pyforge.marshal.adapters.model_list_http"


def _module_name(path: Path, package_dir: Path) -> str:
    parts = ["pyforge", "marshal", *path.relative_to(package_dir).with_suffix("").parts]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _is_import_module_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr == "import_module"
    return isinstance(func, ast.Name) and func.id in {"import_module", "__import__"}


def imported_modules(source: str, module_name: str, *, is_package: bool = False) -> frozenset[str]:
    """Every dotted name ``source`` imports: ``import a.b``, ``from a import b``
    (both ``a`` and ``a.b``), relative forms resolved against ``module_name``
    (``from ..adapters import model_list_live``), and a literal
    ``importlib.import_module("a.b")`` (Story 84.2)."""
    package = module_name if is_package else module_name.rpartition(".")[0]
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = package.split(".")
                base = ".".join(base_parts[: len(base_parts) - (node.level - 1)])
                module = f"{base}.{node.module}" if node.module else base
            else:
                module = node.module or ""
            names.add(module)
            names.update(f"{module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call) and _is_import_module_call(node) and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                names.add(first.value)
    return frozenset(names)


def live_list_boundary_violations(package_dir: Path) -> list[str]:
    """Modules outside the seam that import it, other than ``cli/adapters.py``."""
    allowed = {
        LIVE_LIST_MODULE: {package_dir / "cli" / "adapters.py"},
        LIVE_LIST_HTTP_MODULE: {package_dir / "cli" / "adapters.py", package_dir / "adapters" / "model_list_live.py"},
    }
    violations: list[str] = []
    for path in sorted(package_dir.rglob("*.py")):
        imported = imported_modules(
            path.read_text(encoding="utf-8"),
            _module_name(path, package_dir),
            is_package=path.name == "__init__.py",
        )
        for target, importers in allowed.items():
            if target in imported and path not in importers:
                violations.append(f"{path.relative_to(package_dir)} imports {target}")
    return violations


def test_only_cli_adapters_imports_model_list_live() -> None:
    assert live_list_boundary_violations(PACKAGE_DIR) == []
    cli_imports = imported_modules(CLI_ADAPTERS.read_text(encoding="utf-8"), _module_name(CLI_ADAPTERS, PACKAGE_DIR))
    assert LIVE_LIST_MODULE in cli_imports


def _seam_tree(tmp_path: Path, offender: str) -> Path:
    """A minimal ``pyforge/marshal`` tree: the seam, its one sanctioned
    importer, and ``core/dispatch.py`` carrying ``offender``."""
    package_dir = tmp_path / "pyforge" / "marshal"
    for rel, text in {
        "__init__.py": "",
        "adapters/__init__.py": "",
        "adapters/model_list_http.py": "",
        "adapters/model_list_live.py": "from ..adapters.model_list_http import http_get_for_model_list\n",
        "cli/__init__.py": "",
        "cli/adapters.py": "from ..adapters.model_list_live import LiveModelListFetch\n",
        "core/__init__.py": "",
        "core/dispatch.py": offender,
    }.items():
        target = package_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return package_dir


def test_seam_tree_without_offender_is_clean(tmp_path: Path) -> None:
    assert live_list_boundary_violations(_seam_tree(tmp_path, "import json\n")) == []


@pytest.mark.parametrize(
    "offender",
    [
        "import pyforge.marshal.adapters.model_list_live\n",
        "import pyforge.marshal.adapters.model_list_live as live\n",
        "from pyforge.marshal.adapters import model_list_live\n",
        "from pyforge.marshal.adapters.model_list_live import fetch_live_ids_for_profile\n",
        "from ..adapters import model_list_live\n",
        "from ..adapters.model_list_live import LiveModelListFetch\n",
        "from ..adapters import model_list_http\n",
        "from ..adapters.model_list_http import http_get_for_model_list\n",
        "import pyforge.marshal.adapters.model_list_http\n",
        "def f():\n    from ..adapters import model_list_live\n",
        "import importlib\nimportlib.import_module('pyforge.marshal.adapters.model_list_live')\n",
    ],
)
def test_any_import_form_outside_cli_adapters_is_a_violation(tmp_path: Path, offender: str) -> None:
    """Each form the Story 84.1 check missed reds the boundary (Story 84.2)."""
    violations = live_list_boundary_violations(_seam_tree(tmp_path, offender))
    assert violations, offender
    assert all(v.startswith("core/dispatch.py imports ") for v in violations)


def test_no_django_pyforge_imports_under_marshal_src() -> None:
    offenders: list[str] = []
    for path in _module_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "django_pyforge" in node.module:
                offenders.append(str(path.relative_to(PACKAGE_DIR)))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "django_pyforge" in alias.name:
                        offenders.append(str(path.relative_to(PACKAGE_DIR)))
    assert offenders == []


def test_core_publish_has_no_io_imports() -> None:
    path = PACKAGE_DIR / "core" / "publish.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = {"os", "socket", "urllib", "urllib.request", "httpx", "requests", "subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                assert alias.name not in forbidden and root not in forbidden
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            assert node.module not in forbidden and root not in forbidden
