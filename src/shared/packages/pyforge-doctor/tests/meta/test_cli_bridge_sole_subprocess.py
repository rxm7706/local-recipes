"""Meta test -- AD-5 sole-subprocess-site guard (Story 2.1).

``cli_bridge.py`` is the ONE module in ``pyforge.doctor`` permitted to call
``subprocess``/``os.system``/``os.spawn*``/``os.popen`` (AD-5) -- extends
``test_sources_warden_no_subprocess.py``'s existing subprocess-scan
machinery (there scoped to prove ``sources/warden.py`` alone has ZERO
subprocess call sites) to instead assert ``cli_bridge.py`` is the sole site
where a real subprocess call is permitted ANYWHERE ELSE in the package --
mirrors ``test_no_warden_import.py``'s "scan every other module, one
exemption" shape, but keyed to the subprocess/os-shell-out surface instead
of a ``pyforge.warden`` import.

The detector itself is the identical hardened one proven necessary across
``test_sources_warden_no_subprocess.py``'s three review passes (2026-07-30):
catches a plain ``import subprocess`` / ``from subprocess import ...``, any
``subprocess.*`` attribute call, ``os.system``/``os.popen`` plus the
``spawn*``/``exec*``/``posix_spawn*`` family via attribute access OR
``from os import <name>``, and an aliased ``import os as _o`` module
reference -- built in from the start here rather than re-discovered.

Positively proves the detector fires on a synthetic violation -- the guard
is alive, not vacuous.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

# The one sanctioned subprocess site (AD-5) -- exempted from this scan.
_EXEMPT_RELATIVE_PATHS = frozenset({Path("cli_bridge.py")})


def _package_modules() -> list[Path]:
    return sorted(
        path
        for path in PACKAGE_DIR.rglob("*.py")
        if path.relative_to(PACKAGE_DIR) not in _EXEMPT_RELATIVE_PATHS
    )


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _is_os_shell_out_name(name: str) -> bool:
    return name in ("system", "popen") or name.startswith(
        ("spawn", "exec", "posix_spawn")
    )


def _subprocess_violations(tree: ast.Module) -> list[int]:
    # `import os as _o` would otherwise dodge the attribute check keyed to
    # the literal name "os" -- same hardening as
    # test_sources_warden_no_subprocess.py's own detector.
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


def test_package_scan_surface_is_not_empty():
    modules = _package_modules()
    assert modules, "cli_bridge sole-subprocess guard found no modules to scan"


def test_cli_bridge_module_exists():
    assert (PACKAGE_DIR / "cli_bridge.py").is_file(), (
        "expected pyforge/doctor/cli_bridge.py -- the sanctioned subprocess "
        "site (Story 2.1, AD-5) is missing"
    )


def test_cli_bridge_is_exempted_from_this_scan():
    modules = {path.relative_to(PACKAGE_DIR) for path in _package_modules()}
    assert Path("cli_bridge.py") not in modules


def test_no_module_outside_cli_bridge_calls_subprocess():
    for module_path in _package_modules():
        violations = _subprocess_violations(_parse(module_path))
        assert not violations, (
            f"{module_path.relative_to(PACKAGE_DIR)} uses subprocess/os "
            f"shell-out at line(s) {violations} -- AD-5 confines all "
            "subprocess calls to cli_bridge.py"
        )


def test_cli_bridge_itself_calls_subprocess():
    """Non-vacuous proof: the sanctioned site actually uses subprocess (so
    this guard is testing a real narrowing, not an accidentally-unused
    permission)."""
    violations = _subprocess_violations(
        _parse(PACKAGE_DIR / "cli_bridge.py")
    )
    assert violations, "cli_bridge.py does not call subprocess at all"


# --- synthetic-violation positive proof (the guard is alive, not vacuous) --


def test_guard_fires_on_synthetic_subprocess_import():
    plain = "import subprocess\n"
    assert _subprocess_violations(ast.parse(plain)) == [1]
    from_import = "from subprocess import run\n"
    assert _subprocess_violations(ast.parse(from_import)) == [1]


def test_guard_fires_on_synthetic_subprocess_call():
    synthetic = "import subprocess\nsubprocess.run(['doctor', 'scan'])\n"
    assert _subprocess_violations(ast.parse(synthetic)) == [1, 2]


def test_guard_fires_on_synthetic_os_system_or_popen_shell_out():
    system_call = "import os\nos.system('doctor scan')\n"
    assert _subprocess_violations(ast.parse(system_call)) == [2]
    popen_call = "import os\nos.popen('doctor scan')\n"
    assert _subprocess_violations(ast.parse(popen_call)) == [2]


def test_guard_fires_on_synthetic_from_os_import_shell_out():
    from_system = "from os import system\n"
    assert _subprocess_violations(ast.parse(from_system)) == [1]
    from_popen_aliased = "from os import popen as p\n"
    assert _subprocess_violations(ast.parse(from_popen_aliased)) == [1]


def test_guard_fires_on_synthetic_aliased_os_and_spawn_exec_family():
    aliased = "import os as _o\n_o.system('doctor scan')\n"
    assert _subprocess_violations(ast.parse(aliased)) == [2]
    execv = "import os\nos.execv('/usr/bin/doctor', ['doctor'])\n"
    assert _subprocess_violations(ast.parse(execv)) == [2]
    spawn = "import os\nos.posix_spawn('/usr/bin/doctor', [], {})\n"
    assert _subprocess_violations(ast.parse(spawn)) == [2]


def test_guard_does_not_fire_on_benign_os_use():
    benign = "import os\nos.getcwd()\nfrom os import path\n"
    assert _subprocess_violations(ast.parse(benign)) == []
