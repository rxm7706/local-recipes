"""Meta test -- AD-1 no-reimplementation guard (Story 1.2).

``sources/warden.py`` is the ONE sanctioned site in ``pyforge.doctor`` that
may import ``pyforge.warden`` (see ``test_no_warden_import.py``'s
exemption). This guard narrows that permission further, AST-scanning ONLY
``sources/warden.py`` and failing if it:

- imports ``subprocess`` (as a module import, or a ``from subprocess
  import ...``), calls anything through a ``subprocess.*`` attribute, or
  reaches os's own shell-out family (``system``/``popen``/``spawn*``/
  ``exec*``/``posix_spawn*`` -- via attribute access on ``os`` or an
  ``import os as ...`` alias, or via ``from os import ...``) -- it must
  call warden as a library, never shell out on its own (AD-1);
- imports any ``pyforge.warden`` submodule OTHER than ``engines``, or any
  NAME from ``engines`` other than ``run_doctor_checks`` -- the sole
  sanctioned surface is ``pyforge.warden.engines.run_doctor_checks``, and
  engines' own module namespace holds ``os``/``subprocess``/``ErrorKind``/
  ``Finding`` bindings that a symbol-level import would otherwise launder
  through the sanctioned module unflagged. Relative forms (``from
  ...warden import verdict``) are resolved against the module's own
  package and caught the same as absolute spellings;
- imports ANY module outside the file's closed sanctioned surface
  (``__future__``, ``pathlib``, ``..models``, ``pyforge.warden.engines``)
  -- a positive allowlist, so alternate spawn mechanisms (``pty``,
  ``asyncio`` subprocess helpers, ``os.startfile``) and dynamic importers
  (``importlib``) fail the guard without the shell-out denylist having to
  enumerate every next one.

Positively proves the detector fires on synthetic violations -- the guard
is alive, not vacuous -- mirroring ``test_read_only_guard.py``'s own style.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
WARDEN_SOURCE_PATH = PACKAGE_DIR / "sources" / "warden.py"

# sources/warden.py's own containing package -- what its relative imports
# resolve against.
_SOURCE_PACKAGE_PARTS = ("pyforge", "doctor", "sources")


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _resolve_import_from(
    node: ast.ImportFrom, package_parts: tuple[str, ...]
) -> str | None:
    """The absolute dotted module a ``from ... import`` targets, resolving
    relative forms against ``package_parts``. None when the relative level
    climbs beyond the top-level package (a runtime error anyway)."""
    if not node.level:
        return node.module or ""
    if node.level - 1 >= len(package_parts):
        return None
    base = package_parts[: len(package_parts) - (node.level - 1)]
    if node.module:
        return ".".join((*base, node.module))
    return ".".join(base)


def _is_os_shell_out_name(name: str) -> bool:
    # os.system/os.popen plus the spawn*/exec*/posix_spawn* families --
    # all alternate shell-out mechanisms AD-1 forbids just as much as
    # subprocess itself (review findings, 2026-07-30).
    return name in ("system", "popen") or name.startswith(
        ("spawn", "exec", "posix_spawn")
    )


def _subprocess_violations(tree: ast.Module) -> list[int]:
    # `import os as _o` would otherwise dodge the attribute check keyed to
    # the literal name "os" (review finding, 2026-07-30).
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
                if alias.name == "subprocess" or alias.name.startswith(
                    "subprocess."
                ):
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "subprocess" or module.startswith("subprocess."):
                violations.append(node.lineno)
            # `from os import system` binds the shell-out primitive
            # directly, no attribute access needed -- same gap class as
            # the aliased-os form (review finding, 2026-07-30).
            elif module == "os" and any(
                _is_os_shell_out_name(alias.name) for alias in node.names
            ):
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


def _non_engines_warden_submodule_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pyforge.warden":
                    # The bare package import carries no submodule -- not a
                    # violation by itself (nothing is usable from it without
                    # a further attribute-access, which the doctor code
                    # never does; the sanctioned code path is an explicit
                    # `from pyforge.warden.engines import ...`).
                    continue
                # Exact match only: a boundary-free startswith would admit
                # a hypothetical `pyforge.warden.engines_evil`, and
                # sub-paths of `engines` (a module, not a package) are not
                # sanctioned either (review finding, 2026-07-30).
                if (
                    alias.name.startswith("pyforge.warden.")
                    and alias.name != "pyforge.warden.engines"
                ):
                    violations.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            # Resolve relative forms (`from ...warden import verdict`)
            # against sources/warden.py's own package first -- they reach
            # pyforge.warden through the shared namespace package without
            # ever spelling it absolutely (review finding, 2026-07-30;
            # mirrors test_no_warden_import.py).
            module = _resolve_import_from(node, _SOURCE_PACKAGE_PARTS)
            if module is None:
                continue
            if module == "pyforge.warden.engines":
                # Symbol-level allowlist: the sanction covers exactly
                # ``run_doctor_checks``. engines' own module namespace
                # also holds ``os``, ``subprocess``, ``ErrorKind``, and a
                # name-identical ``Finding`` -- importing any of those
                # here would launder forbidden names through the
                # sanctioned module unflagged (review finding,
                # 2026-07-30). ``*`` is likewise rejected.
                if any(
                    alias.name != "run_doctor_checks"
                    for alias in node.names
                ):
                    violations.append(node.lineno)
                continue
            if module == "pyforge.warden" or module.startswith(
                "pyforge.warden."
            ):
                violations.append(node.lineno)
            # `from pyforge import warden` names the submodule as an alias
            # under the PARENT module ("pyforge") -- the checks above miss
            # this form entirely (review finding, 2026-07-30; mirrors the
            # identical fix in test_no_warden_import.py).
            elif module == "pyforge" and any(
                alias.name == "warden" for alias in node.names
            ):
                violations.append(node.lineno)
    return sorted(set(violations))


# The complete sanctioned import surface of sources/warden.py -- relative
# forms resolved to their absolute targets. Growing the shell-out denylist
# one bypass at a time (os.system, aliased os, from-os, spawn/exec, then
# pty/asyncio/...) is an arms race; this file's legitimate surface is tiny
# and closed, so a positive allowlist ends every STATIC import bypass class
# at once (review finding, 2026-07-30). A future legitimate import means
# consciously extending this set, which is the point.
_SANCTIONED_IMPORTS = frozenset(
    {
        "__future__",
        "pathlib",
        "pyforge.doctor.models",
        "pyforge.warden.engines",
    }
)


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


def test_sources_warden_module_exists():
    assert WARDEN_SOURCE_PATH.is_file(), (
        f"expected {WARDEN_SOURCE_PATH} -- the sanctioned warden import "
        "site (Story 1.2) is missing"
    )


def test_sources_warden_has_no_subprocess_call_sites():
    violations = _subprocess_violations(_parse(WARDEN_SOURCE_PATH))
    assert not violations, (
        f"sources/warden.py uses subprocess at line(s) {violations} -- "
        "AD-1 requires a library call into pyforge.warden.engines, never "
        "a reimplementation via subprocess"
    )


def test_sources_warden_imports_no_submodule_besides_engines():
    violations = _non_engines_warden_submodule_violations(
        _parse(WARDEN_SOURCE_PATH)
    )
    assert not violations, (
        f"sources/warden.py imports a non-engines pyforge.warden submodule "
        f"at line(s) {violations} -- only pyforge.warden.engines is "
        "sanctioned"
    )


def test_sources_warden_import_surface_is_exactly_the_sanctioned_set():
    imported = _imported_modules(_parse(WARDEN_SOURCE_PATH))
    unsanctioned = imported - _SANCTIONED_IMPORTS
    assert not unsanctioned, (
        f"sources/warden.py imports outside the sanctioned surface: "
        f"{sorted(unsanctioned)} -- AD-1 confines this module to "
        "__future__, pathlib, its own models, and pyforge.warden.engines; "
        "extend _SANCTIONED_IMPORTS only for a consciously-reviewed need"
    )


# --- synthetic-violation positive proof (the guard is alive, not vacuous) --


def test_guard_fires_on_synthetic_subprocess_import():
    plain = "import subprocess\n"
    assert _subprocess_violations(ast.parse(plain)) == [1]
    from_import = "from subprocess import run\n"
    assert _subprocess_violations(ast.parse(from_import)) == [1]


def test_guard_fires_on_synthetic_subprocess_call():
    synthetic = "import subprocess\nsubprocess.run(['warden', 'scan'])\n"
    assert _subprocess_violations(ast.parse(synthetic)) == [1, 2]


def test_guard_fires_on_synthetic_os_system_or_popen_shell_out():
    system_call = "import os\nos.system('warden scan')\n"
    assert _subprocess_violations(ast.parse(system_call)) == [2]
    popen_call = "import os\nos.popen('warden scan')\n"
    assert _subprocess_violations(ast.parse(popen_call)) == [2]


def test_guard_fires_on_synthetic_from_os_import_shell_out():
    from_system = "from os import system\n"
    assert _subprocess_violations(ast.parse(from_system)) == [1]
    from_popen_aliased = "from os import popen as p\n"
    assert _subprocess_violations(ast.parse(from_popen_aliased)) == [1]


def test_guard_fires_on_synthetic_aliased_os_and_spawn_exec_family():
    aliased = "import os as _o\n_o.system('warden scan')\n"
    assert _subprocess_violations(ast.parse(aliased)) == [2]
    execv = "import os\nos.execv('/usr/bin/warden', ['warden'])\n"
    assert _subprocess_violations(ast.parse(execv)) == [2]
    spawn = "import os\nos.posix_spawn('/usr/bin/warden', [], {})\n"
    assert _subprocess_violations(ast.parse(spawn)) == [2]


def test_guard_does_not_fire_on_benign_os_use():
    benign = "import os\nos.getcwd()\nfrom os import path\n"
    assert _subprocess_violations(ast.parse(benign)) == []


def test_guard_fires_on_synthetic_non_engines_submodule_import():
    plain = "import pyforge.warden.models\n"
    assert _non_engines_warden_submodule_violations(ast.parse(plain)) == [1]
    from_import = "from pyforge.warden import verdict\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(from_import)
    ) == [1]
    from_submodule = "from pyforge.warden.verdict import exit_code_for\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(from_submodule)
    ) == [1]
    parent_alias = "from pyforge import warden\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(parent_alias)
    ) == [1]


def test_guard_fires_on_synthetic_engines_prefixed_sibling_import():
    # No dot boundary: `engines_evil` must not ride on `engines`'s
    # sanction, and sub-paths of the `engines` module are not sanctioned
    # in either import branch (review finding, 2026-07-30).
    sibling = "import pyforge.warden.engines_evil\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(sibling)
    ) == [1]
    subpath = "import pyforge.warden.engines.sub\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(subpath)
    ) == [1]
    from_sibling = "from pyforge.warden.engines_evil import x\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(from_sibling)
    ) == [1]


def test_guard_fires_on_synthetic_relative_warden_import():
    # Resolved against sources/warden.py's own package
    # (pyforge.doctor.sources): three dots climb to `pyforge`.
    relative_submodule = "from ...warden import verdict\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(relative_submodule)
    ) == [1]
    relative_deep = "from ...warden.models import ErrorKind\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(relative_deep)
    ) == [1]
    relative_parent_alias = "from ... import warden\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(relative_parent_alias)
    ) == [1]


def test_guard_fires_on_synthetic_symbol_laundering_through_engines():
    # engines' own module namespace holds os/subprocess/ErrorKind/Finding
    # bindings -- a name-level import through the sanctioned module would
    # launder them in unflagged if the guard stayed module-granular
    # (review finding, 2026-07-30).
    vocab = "from pyforge.warden.engines import ErrorKind\n"
    assert _non_engines_warden_submodule_violations(ast.parse(vocab)) == [1]
    shadow = "from pyforge.warden.engines import Finding\n"
    assert _non_engines_warden_submodule_violations(ast.parse(shadow)) == [1]
    laundered = "from pyforge.warden.engines import subprocess as sp\n"
    assert _non_engines_warden_submodule_violations(
        ast.parse(laundered)
    ) == [1]
    star = "from pyforge.warden.engines import *\n"
    assert _non_engines_warden_submodule_violations(ast.parse(star)) == [1]
    mixed = "from pyforge.warden.engines import run_doctor_checks, os\n"
    assert _non_engines_warden_submodule_violations(ast.parse(mixed)) == [1]


def test_import_surface_guard_fires_on_synthetic_unsanctioned_imports():
    # Each of these evades the shell-out denylist (or is a dynamic-import
    # vehicle) yet fails the closed allowlist -- the arms race ends here
    # (review finding, 2026-07-30).
    for synthetic in (
        "import pty\n",
        "import asyncio\n",
        "import importlib\n",
        "import os\n",
        "from ctypes import CDLL\n",
    ):
        unsanctioned = _imported_modules(ast.parse(synthetic))
        assert unsanctioned - _SANCTIONED_IMPORTS, (
            f"allowlist guard failed to flag: {synthetic!r}"
        )


def test_import_surface_guard_passes_the_sanctioned_surface():
    benign = (
        "from __future__ import annotations\n"
        "from pathlib import Path\n"
        "from ..models import DoctorStatus, Finding, Source\n"
        "from pyforge.warden.engines import run_doctor_checks\n"
    )
    assert _imported_modules(ast.parse(benign)) - _SANCTIONED_IMPORTS == set()


def test_guard_does_not_fire_on_the_sanctioned_engines_import():
    benign = "from pyforge.warden.engines import run_doctor_checks\n"
    assert _subprocess_violations(ast.parse(benign)) == []
    assert _non_engines_warden_submodule_violations(ast.parse(benign)) == []
    # The relative spelling of the same sanctioned import resolves to the
    # identical module and is equally sanctioned.
    relative = "from ...warden.engines import run_doctor_checks\n"
    assert _non_engines_warden_submodule_violations(ast.parse(relative)) == []
