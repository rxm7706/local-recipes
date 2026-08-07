"""Meta test -- AD-4 pure-function guard (Story 3.1).

``doctor.prescribe`` consumes Epic 1/2's already-gathered ``Finding``\\ s as
plain data -- it must add ZERO subprocess/MCP calls of its own. AST-scan
``prescribe.py`` and fail if it:

- imports ``subprocess`` or reaches os's own shell-out family (mirrors
  ``test_sources_warden_no_subprocess.py``'s own subprocess-violation
  detector, applied to this file instead of ``sources/warden.py``);
- imports ``mcp`` or any of its submodules (mirrors
  ``test_atlas_sole_mcp_import.py``'s own detector -- ``prescribe.py`` is
  NOT the sanctioned ``mcp`` import site, only ``sources/atlas.py`` is);
- imports anything outside the file's closed sanctioned surface
  (``__future__``, ``dataclasses``, ``collections.abc``, ``re``,
  ``..models``) -- a positive allowlist, same rationale as the warden
  guard's own: it ends the "one more shell-out mechanism" arms race at
  once rather than enumerating a growing denylist.

Positively proves the detector fires on synthetic violations -- the guard
is alive, not vacuous -- mirroring ``test_sources_warden_no_subprocess.py``'s
own style.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
PRESCRIBE_SOURCE_PATH = PACKAGE_DIR / "prescribe.py"

# prescribe.py's own containing package -- what its relative imports
# resolve against.
_SOURCE_PACKAGE_PARTS = ("pyforge", "doctor")

_SANCTIONED_IMPORTS = frozenset(
    {
        "__future__",
        "dataclasses",
        "collections.abc",
        "re",
        "pyforge.doctor.models",
    }
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _resolve_import_from(
    node: ast.ImportFrom, package_parts: tuple[str, ...]
) -> str | None:
    if not node.level:
        return node.module or ""
    if node.level - 1 >= len(package_parts):
        return None
    base = package_parts[: len(package_parts) - (node.level - 1)]
    if node.module:
        return ".".join((*base, node.module))
    return ".".join(base)


def _is_os_shell_out_name(name: str) -> bool:
    return name in ("system", "popen") or name.startswith(
        ("spawn", "exec", "posix_spawn")
    )


def _subprocess_or_mcp_violations(tree: ast.Module) -> list[int]:
    os_aliases = {"os"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os" and alias.asname:
                    os_aliases.add(alias.asname)
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess" or alias.name.startswith("subprocess."):
                    violations.append(node.lineno)
                if alias.name == "mcp" or alias.name.startswith("mcp."):
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "subprocess" or module.startswith("subprocess."):
                violations.append(node.lineno)
            elif module == "os" and any(
                _is_os_shell_out_name(alias.name) for alias in node.names
            ):
                violations.append(node.lineno)
            elif node.level == 0 and (module == "mcp" or module.startswith("mcp.")):
                violations.append(node.lineno)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "subprocess"
        ):
            violations.append(node.lineno)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in os_aliases
            and _is_os_shell_out_name(node.attr)
        ):
            violations.append(node.lineno)
    return sorted(set(violations))


def _imported_modules(tree: ast.Module) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_from(node, _SOURCE_PACKAGE_PARTS)
            if module is not None:
                imported.add(module)
    return imported


def test_prescribe_module_exists():
    assert PRESCRIBE_SOURCE_PATH.is_file(), (
        f"expected {PRESCRIBE_SOURCE_PATH} -- the Story 3.1 "
        "partition/rank/root-cause pipeline module is missing"
    )


def test_prescribe_has_no_subprocess_or_mcp_call_sites():
    violations = _subprocess_or_mcp_violations(_parse(PRESCRIBE_SOURCE_PATH))
    assert not violations, (
        f"prescribe.py reaches subprocess/mcp at line(s) {violations} -- "
        "AD-4 requires doctor.prescribe to add ZERO calls of its own, "
        "consuming only already-gathered Findings"
    )


def test_prescribe_import_surface_is_exactly_the_sanctioned_set():
    imported = _imported_modules(_parse(PRESCRIBE_SOURCE_PATH))
    unsanctioned = imported - _SANCTIONED_IMPORTS
    assert not unsanctioned, (
        f"prescribe.py imports outside the sanctioned surface: "
        f"{sorted(unsanctioned)} -- AD-4 confines this module to "
        "__future__, dataclasses, collections.abc, and its own models; "
        "extend _SANCTIONED_IMPORTS only for a consciously-reviewed need"
    )


# --- synthetic-violation positive proof (the guard is alive, not vacuous) --


def test_guard_fires_on_synthetic_subprocess_import():
    plain = "import subprocess\n"
    assert _subprocess_or_mcp_violations(ast.parse(plain)) == [1]
    from_import = "from subprocess import run\n"
    assert _subprocess_or_mcp_violations(ast.parse(from_import)) == [1]


def test_guard_fires_on_synthetic_subprocess_call():
    synthetic = "import subprocess\nsubprocess.run(['warden', 'scan'])\n"
    assert _subprocess_or_mcp_violations(ast.parse(synthetic)) == [1, 2]


def test_guard_fires_on_synthetic_os_shell_out():
    system_call = "import os\nos.system('warden scan')\n"
    assert _subprocess_or_mcp_violations(ast.parse(system_call)) == [2]
    aliased = "import os as _o\n_o.popen('warden scan')\n"
    assert _subprocess_or_mcp_violations(ast.parse(aliased)) == [2]
    from_system = "from os import system\n"
    assert _subprocess_or_mcp_violations(ast.parse(from_system)) == [1]


def test_guard_fires_on_synthetic_mcp_import():
    plain = "import mcp\n"
    assert _subprocess_or_mcp_violations(ast.parse(plain)) == [1]
    submodule = "import mcp.client.stdio\n"
    assert _subprocess_or_mcp_violations(ast.parse(submodule)) == [1]
    from_import = "from mcp import ClientSession\n"
    assert _subprocess_or_mcp_violations(ast.parse(from_import)) == [1]


def test_guard_does_not_fire_on_benign_use():
    benign = (
        "import os\n"
        "os.getcwd()\n"
        "from dataclasses import dataclass\n"
    )
    assert _subprocess_or_mcp_violations(ast.parse(benign)) == []


def test_import_surface_guard_fires_on_synthetic_unsanctioned_imports():
    for synthetic in (
        "import subprocess\n",
        "import mcp\n",
        "import json\n",
        "from pathlib import Path\n",
    ):
        unsanctioned = _imported_modules(ast.parse(synthetic))
        assert unsanctioned - _SANCTIONED_IMPORTS, (
            f"allowlist guard failed to flag: {synthetic!r}"
        )


def test_import_surface_guard_passes_the_sanctioned_surface():
    benign = (
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "from collections.abc import Iterable\n"
        "from .models import DoctorStatus, Finding, Partition\n"
    )
    assert _imported_modules(ast.parse(benign)) - _SANCTIONED_IMPORTS == set()


def test_import_surface_guard_resolves_relative_models_import():
    # prescribe.py lives directly under pyforge/doctor/ (unlike
    # sources/warden.py, one level deeper) -- one leading dot resolves to
    # pyforge.doctor.models, confirmed against the real file's own import.
    relative = "from .models import Finding\n"
    resolved = _imported_modules(ast.parse(relative))
    assert "pyforge.doctor.models" in resolved
