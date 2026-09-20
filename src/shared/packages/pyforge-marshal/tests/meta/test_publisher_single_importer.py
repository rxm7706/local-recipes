"""Story 33.4 meta — exactly one publishing ``pyforge.core.client`` importer."""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
PUBLISHER_ADAPTER = PACKAGE_DIR / "adapters" / "publisher_host.py"
LOGIN_ADAPTER = PACKAGE_DIR / "adapters" / "oidc_pkce.py"


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
    publish_importers = [path for path in importers if path != LOGIN_ADAPTER]
    assert publish_importers == [PUBLISHER_ADAPTER]
    assert LOGIN_ADAPTER in importers


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
