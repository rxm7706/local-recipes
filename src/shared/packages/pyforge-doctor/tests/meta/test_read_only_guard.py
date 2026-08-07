"""Meta test — NFR-1 read-only guard (Story 1.1; exemption added Story 4.2).

Nothing under the installed ``pyforge.doctor`` package may write outside a
``tempfile``-scoped path (architecture spine Consistency Conventions: "v1 is
read-only everywhere — no module under pyforge.doctor may write outside a
tempfile-scoped path or mutate scanned trees", mirroring warden's own
NFR-S4 discipline) -- EXCEPT ``fleet_surface.py`` (Story 4.2, FR-11, AD-8),
the ONE sanctioned write site this v1.x addition deliberately introduces
(mirrors ``sources/atlas.py``'s own sole-``mcp``-import-site exemption
pattern, applied to the filesystem-write surface instead): AD-8 bounds what
that write may do (strictly derived from already-gathered findings, no
independent gather, idempotent, schema-versioned) even though NFR-1's own
blanket rule predates it. This is a best-effort STATIC AST scan for
filesystem-write call sites: ``open(..., "w"/"a"/"x"/...)``, ``Path.write_text``/
``Path.write_bytes``, and the common ``os``/``shutil`` mutation calls
(``remove``/``unlink``/``rename``/``mkdir``/``makedirs``/``chmod``/
``copy*``/``move``/``rmtree``).

Positively proves the detector fires on synthetic violations — the guard is
alive, not vacuous — mirroring the sole-ownership meta-test's own style.

Bounds (stated, not aspirational): this is a best-effort STATIC check, same
class as the sole-ownership guard's own stated bounds — dynamic dispatch
(``getattr``) or an indirection through a helper function is out of scope.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.doctor

_PACKAGE_FILE = pyforge.doctor.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

# The one sanctioned filesystem-write site (Story 4.2) -- exempted from this
# scan, mirroring `test_atlas_sole_mcp_import.py`'s identical
# `_EXEMPT_RELATIVE_PATHS` pattern for the mcp-import surface.
_EXEMPT_RELATIVE_PATHS = frozenset({Path("fleet_surface.py")})

_WRITE_METHOD_NAMES = frozenset(
    {
        "write_text",
        "write_bytes",
        "copy",
        "copy2",
        "copytree",
        "move",
        "rmtree",
        "remove",
        "unlink",
        "rename",
        "mkdir",
        "makedirs",
        "chmod",
    }
)


def _package_modules() -> list[Path]:
    return sorted(
        path
        for path in PACKAGE_DIR.rglob("*.py")
        if path.relative_to(PACKAGE_DIR) not in _EXEMPT_RELATIVE_PATHS
    )


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _open_call_violations(tree: ast.Module) -> list[int]:
    """A bare ``open(path)`` (or explicit ``mode="r"``/``"rb"``) is
    read-only and not a violation; any mode containing ``w``/``a``/``x`` or
    a ``+`` (update mode) is a write call site. Catches both the builtin
    ``open(...)`` Name form and the attribute form (``Path(...).open(...)``,
    ``some_file.open(...)``)."""
    violations: list[int] = []
    for node in ast.walk(tree):
        is_builtin_open = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open"
        )
        is_attribute_open = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "open"
        )
        if not (isinstance(node, ast.Call) and (is_builtin_open or is_attribute_open)):
            continue
        # Builtin open(path, mode) carries mode as the 2nd positional arg;
        # the attribute form Path(...).open(mode) has no explicit `path`
        # (self is implicit), so mode is the 1st positional arg there.
        mode_index = 1 if is_builtin_open else 0
        mode_arg = None
        if len(node.args) > mode_index:
            mode_arg = node.args[mode_index]
        else:
            for keyword in node.keywords:
                if keyword.arg == "mode":
                    mode_arg = keyword.value
        if mode_arg is None:
            # bare open(path) defaults to "r" -- read-only.
            continue
        if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
            if any(flag in mode_arg.value for flag in ("w", "a", "x", "+")):
                violations.append(node.lineno)
    return violations


def _write_method_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _WRITE_METHOD_NAMES
        ):
            violations.append(node.lineno)
    return violations


def _read_only_violations(tree: ast.Module) -> list[int]:
    return sorted(_open_call_violations(tree) + _write_method_violations(tree))


def test_package_scan_surface_is_not_empty():
    modules = _package_modules()
    assert modules, "read-only guard found no modules to scan"


def test_fleet_surface_module_exists():
    fleet_surface_path = PACKAGE_DIR / "fleet_surface.py"
    assert fleet_surface_path.is_file(), (
        f"expected {fleet_surface_path} -- the Story 4.2 sanctioned write "
        "site is missing"
    )


def test_fleet_surface_is_exempted_from_this_scan():
    modules = {path.relative_to(PACKAGE_DIR) for path in _package_modules()}
    assert Path("fleet_surface.py") not in modules


def test_fleet_surface_itself_writes_somewhere():
    """Non-vacuous proof: the sanctioned site actually contains a
    filesystem-write call site -- so this exemption is narrowing a real
    permission, not an accidentally-unused one."""
    violations = _read_only_violations(_parse(PACKAGE_DIR / "fleet_surface.py"))
    assert violations, "fleet_surface.py does not write to the filesystem at all"


def test_no_filesystem_write_call_sites_in_package():
    for module_path in _package_modules():
        violations = _read_only_violations(_parse(module_path))
        assert not violations, (
            f"{module_path.name} contains a filesystem-write call site at "
            f"line(s) {violations} -- pyforge.doctor must stay read-only "
            "(NFR-1) outside a tempfile-scoped path"
        )


def test_guard_fires_on_synthetic_open_write_violation():
    synthetic = 'open("somefile", "w").write("x")\n'
    assert _open_call_violations(ast.parse(synthetic)) == [1]


def test_guard_fires_on_synthetic_path_open_attribute_form_violation():
    synthetic = "from pathlib import Path\nPath('x').open('w').write('y')\n"
    assert _open_call_violations(ast.parse(synthetic)) == [2]


def test_guard_fires_on_synthetic_path_write_text_violation():
    synthetic = "from pathlib import Path\nPath('x').write_text('y')\n"
    assert _write_method_violations(ast.parse(synthetic)) == [2]


def test_guard_fires_on_synthetic_shutil_copy_violation():
    synthetic = "import shutil\nshutil.copy('a', 'b')\n"
    assert _write_method_violations(ast.parse(synthetic)) == [2]


def test_guard_does_not_fire_on_benign_read_only_calls():
    benign = (
        "open('a.txt')\n"
        "open('a.txt', 'r')\n"
        "open('a.txt', mode='rb')\n"
        "from pathlib import Path\n"
        "Path('a.txt').read_text()\n"
        "Path('a.txt').open('r')\n"
        "Path('a.txt').open()\n"
    )
    assert _read_only_violations(ast.parse(benign)) == []
