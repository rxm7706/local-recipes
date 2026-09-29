"""Meta test -- the atomic-write sole-ownership guard (Story 14.2, CAP-7).

AST-scan every ``*.py`` file under every SIBLING station's ``src/pyforge``
tree (``src/shared/packages/pyforge-<station>/src/pyforge/...`` for every
station directory except ``pyforge-core`` itself, where the one canonical
implementation legitimately lives) and fail the build if any function
contains BOTH:

(a) a temp-file WRITE-OPEN call -- ``tempfile.mkstemp``/
    ``tempfile.NamedTemporaryFile``, a low-level ``os.open(...)``/
    ``os.fdopen(...)``, or a ``<name>.write_text(...)``/``.write_bytes(...)``/
    a write-mode ``.open("w"...)`` method call (the write-open idioms this
    session's own census found across all 20 pre-refactor copies), OR a
    BARE-NAME-bound equivalent -- ``from tempfile import mkstemp
    [as x]``/``NamedTemporaryFile [as x]``, ``from os import fdopen [as
    x]``/``open [as x]`` (review pass 2: the same bare-name evasion class
    already closed on the replace side below, now closed symmetrically
    here); AND
(b) an ``os.replace(...)``-EQUIVALENT call -- ``os.replace(...)`` bound via
    ``import os``/``import os as x``; a bare name bound via
    ``from os import replace [as x]``; OR a ``<name>.replace(...)`` call
    whose receiver LOOKS like a temp-path local (contains "tmp"/"temp",
    case-insensitive) -- ``Path.replace`` is a real stdlib rename-in-place
    method, so ``tmp_path.replace(path)`` is functionally identical to
    ``os.replace(tmp_path, path)`` and must not evade this guard just
    because it is spelled as a method call on a non-``os``-bound name
    (review finding: the original detector only recognized the ``os.``-
    bound spelling).

Scans SOURCE trees (reads files from disk), not installed packages -- mirrors
``test_leaf_constraint.py``'s identical convention, so results never depend
on whether an environment happens to be freshly rebuilt.

Station roster is DERIVED by listing ``pyforge-*`` directories under
``src/shared/packages/`` (minus ``pyforge-core``), never hardcoded -- a ninth
station added later is covered automatically with no edit here.

Non-vacuous proof, both directions (mirrors ``test_leaf_constraint.py``'s
same-shape proof): a synthetic ``tempfile.mkstemp`` + ``os.replace`` pair in
one function IS flagged, as are the ``from os import replace`` and
``tmp_path.replace(...)`` variants; ``fs_local.py::repoint_symlink_atomic``'s
REAL body (read from the actual installed source, not a stand-in) is NOT
flagged -- it calls ``os.replace`` but never opens a file for writing (only
``os.symlink``), and CAP-2's Boundaries name this function as explicitly out
of scope for the atomic-write extraction (a different primitive: atomic
symlink repoint, not content write).

Bounds (stated, not aspirational): a best-effort STATIC check, AST ``Call``
nodes only -- dynamic dispatch (``getattr(os, "replace")(...)``) is out of
scope, matching every sibling meta-test's stated limitation. Indirection
through a callback PARAMETER (a function that takes a ``write_fn`` argument
and calls it, with the real write-open call living in the CALLER's lambda,
not in the scanned function's own body) is also out of scope -- measured
against ``datasets/refresh.py``'s pre-retirement ``_atomic_write(target,
write_fn)``, which this detector does not flag for exactly this reason. That
shape is retired by this same story regardless; the detector's job is to
catch a FUTURE second implementation, most of which (per this session's own
census) open the temp file directly rather than through a passed-in callback.
The ``<name>.replace(...)`` receiver heuristic is deliberately narrow (name
must look temp-path-shaped) rather than firing on EVERY ``.replace(...)``
call -- a broader match would flag ordinary ``str.replace(old, new)`` calls
fleet-wide, which is not this guard's job.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from conftest import (
    PACKAGES_ROOT,
    parse_module,
    sibling_station_dirs,
    station_source_files,
)

_sibling_station_dirs = sibling_station_dirs
_station_source_files = station_source_files
_parse = parse_module

_WRITE_OPEN_TEMPFILE_ATTRS = frozenset({"mkstemp", "NamedTemporaryFile"})
_WRITE_OPEN_OS_ATTRS = frozenset({"open", "fdopen"})
_WRITE_OPEN_METHOD_ATTRS = frozenset({"write_text", "write_bytes"})
_TEMP_PATH_NAME_HINTS = ("tmp", "temp")


def _module_aliases(tree: ast.AST, module_name: str) -> frozenset[str]:
    """Local names bound to ``module_name`` itself: ``import os`` ->
    ``{"os"}``, ``import os as o`` -> adds ``"o"``."""
    names = {module_name}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module_name and alias.asname is not None:
                    names.add(alias.asname)
    return frozenset(names)


def _os_replace_bare_names(tree: ast.AST) -> frozenset[str]:
    """Local names bound to ``os.replace`` itself via ``from os import
    replace [as x]`` -- a bare-name call site (``replace(tmp, path)`` or
    ``x(tmp, path)``) that never spells ``os.`` at the call at all."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                if alias.name == "replace":
                    names.add(alias.asname or alias.name)
    return frozenset(names)


def _write_open_bare_names(tree: ast.AST) -> frozenset[str]:
    """Local names bound to a write-open callable itself via ``from
    tempfile import mkstemp [as x]``/``NamedTemporaryFile [as x]`` or ``from
    os import fdopen [as x]``/``open [as x]`` -- a bare-name call site that
    never spells the owning module at the call at all (review pass 2: the
    same evasion class already closed on the ``os.replace`` side, above)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module == "tempfile":
            for alias in node.names:
                if alias.name in _WRITE_OPEN_TEMPFILE_ATTRS:
                    names.add(alias.asname or alias.name)
        elif node.module == "os":
            for alias in node.names:
                if alias.name in _WRITE_OPEN_OS_ATTRS:
                    names.add(alias.asname or alias.name)
    return frozenset(names)


def _looks_like_temp_path_name(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _TEMP_PATH_NAME_HINTS)


def _calls_os_replace(func: ast.AST, os_names: frozenset[str], replace_bare_names: frozenset[str]) -> bool:
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        if isinstance(callee, ast.Attribute) and callee.attr == "replace":
            if isinstance(callee.value, ast.Name) and (
                callee.value.id in os_names or _looks_like_temp_path_name(callee.value.id)
            ):
                return True
        elif isinstance(callee, ast.Name) and callee.id in replace_bare_names:
            return True
    return False


def _is_write_mode_arg(node: ast.Call) -> bool:
    """True if a ``.open(...)`` call's mode -- positional or ``mode=``
    keyword -- is a string literal starting with ``"w"`` (``"w"``, ``"wb"``,
    ``"w+"``, ...). A bare ``.open()``/``.open("r")`` read is not a
    write-open signal."""
    mode_arg: ast.expr | None = node.args[0] if node.args else None
    for keyword in node.keywords:
        if keyword.arg == "mode":
            mode_arg = keyword.value
    return isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str) and mode_arg.value.startswith("w")


def _calls_temp_write_open(
    func: ast.AST,
    os_names: frozenset[str],
    tempfile_names: frozenset[str],
    write_open_bare_names: frozenset[str] = frozenset(),
) -> bool:
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in write_open_bare_names:
            # A bare-name call bound via `from tempfile import mkstemp` or
            # `from os import fdopen`/`open` (review pass 2) -- the same
            # evasion class already closed on the os.replace side.
            return True
        if not isinstance(node.func, ast.Attribute):
            continue
        attr = node.func.attr
        owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
        if owner is not None and owner in tempfile_names and attr in _WRITE_OPEN_TEMPFILE_ATTRS:
            return True
        if owner is not None and owner in os_names and attr in _WRITE_OPEN_OS_ATTRS:
            return True
        if attr in _WRITE_OPEN_METHOD_ATTRS:
            # A `<anything>.write_text(...)`/`.write_bytes(...)` call --
            # deliberately owner-agnostic: the object is almost always a
            # local `tmp`/`tmp_path` variable, not a module-bound name.
            return True
        if attr == "open" and owner not in os_names and _is_write_mode_arg(node):
            # `<anything>.open("w", ...)` -- e.g. `tmp_path.open("w",
            # encoding="utf-8")` (steward's budget.py/keys.py idiom).
            # os-bound `.open` is already handled above regardless of mode
            # (os.open has no string-mode argument at all).
            return True
    return False


def _functions_with_both_signals(tree: ast.Module) -> list[tuple[str, int]]:
    """Every ``(function_name, lineno)`` in ``tree`` whose function body
    contains BOTH a temp-file write-open call and an os.replace-equivalent
    call."""
    os_names = _module_aliases(tree, "os")
    tempfile_names = _module_aliases(tree, "tempfile")
    replace_bare_names = _os_replace_bare_names(tree)
    write_open_bare_names = _write_open_bare_names(tree)
    violations: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _calls_temp_write_open(node, os_names, tempfile_names, write_open_bare_names) and _calls_os_replace(
            node, os_names, replace_bare_names
        ):
            violations.append((node.name, node.lineno))
    return violations


def test_scan_surface_is_not_empty():
    files = _station_source_files()
    assert files, "sole-ownership guard found no sibling station source files to scan"
    stations = _sibling_station_dirs()
    assert len(stations) >= 5, f"expected several sibling stations, found {stations}"


@pytest.mark.parametrize("module_path", _station_source_files(), ids=lambda p: str(p.relative_to(PACKAGES_ROOT)))
def test_no_second_atomic_write_implementation(module_path: Path):
    violations = _functions_with_both_signals(_parse(module_path))
    assert not violations, (
        f"{module_path} defines function(s) {violations} with BOTH a temp-file "
        f"write-open and an os.replace-equivalent call -- a second atomic-write "
        f"implementation outside pyforge-core (CAP-7: the floor stays a floor; "
        f"delegate to pyforge.core.atomic_write* instead)"
    )


def test_guard_fires_on_a_synthetic_second_implementation():
    """Non-vacuous proof (positive): a plain mkstemp + os.replace pair in one
    function IS flagged."""
    synthetic = (
        "import os\n"
        "import tempfile\n"
        "def _write(target):\n"
        "    handle, tmp = tempfile.mkstemp(dir=target.parent)\n"
        "    os.close(handle)\n"
        "    os.replace(tmp, target)\n"
    )
    violations = _functions_with_both_signals(ast.parse(synthetic))
    assert violations == [("_write", 3)]


def test_guard_fires_on_a_synthetic_os_open_write_variant():
    """Non-vacuous proof: the low-level ``os.open`` write-open idiom (this
    codebase's pre-Story-14.2 pid+thread-id shape) is ALSO detected, not just
    ``tempfile.mkstemp``."""
    synthetic = (
        "import os\n"
        "def _write(target, tmp):\n"
        "    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)\n"
        "    os.close(fd)\n"
        "    os.replace(tmp, target)\n"
    )
    violations = _functions_with_both_signals(ast.parse(synthetic))
    assert violations == [("_write", 2)]


def test_guard_fires_on_a_synthetic_from_os_import_replace_variant():
    """Non-vacuous proof (review finding): ``from os import replace as x;
    x(tmp, target)`` -- a bare-name call bound via ``from os import
    replace`` -- is ALSO detected, not only the ``os.replace(...)``
    spelling."""
    synthetic = (
        "import tempfile\n"
        "from os import replace as _do_replace\n"
        "def _write(target):\n"
        "    handle, tmp = tempfile.mkstemp(dir=target.parent)\n"
        "    _do_replace(tmp, target)\n"
    )
    violations = _functions_with_both_signals(ast.parse(synthetic))
    assert violations == [("_write", 3)]


def test_guard_fires_on_a_synthetic_from_tempfile_import_mkstemp_variant():
    """Non-vacuous proof (review pass 2): ``from tempfile import mkstemp;
    mkstemp(...)`` -- a bare-name write-open call bound via ``from tempfile
    import`` -- is ALSO detected, not only the ``tempfile.mkstemp(...)``
    spelling."""
    synthetic = (
        "import os\n"
        "from tempfile import mkstemp\n"
        "def _write(target):\n"
        "    handle, tmp = mkstemp(dir=target.parent)\n"
        "    os.close(handle)\n"
        "    os.replace(tmp, target)\n"
    )
    violations = _functions_with_both_signals(ast.parse(synthetic))
    assert violations == [("_write", 3)]


def test_guard_fires_on_a_synthetic_from_os_import_fdopen_variant():
    """Non-vacuous proof (review pass 2): ``from os import fdopen;
    fdopen(...)`` -- a bare-name write-open call bound via ``from os
    import`` -- is ALSO detected, the same evasion class already closed on
    the ``os.replace`` side."""
    synthetic = (
        "import os\n"
        "import tempfile\n"
        "from os import fdopen\n"
        "def _write(target):\n"
        "    handle, tmp = tempfile.mkstemp(dir=target.parent)\n"
        "    with fdopen(handle, 'w') as fh:\n"
        "        fh.write('x')\n"
        "    os.replace(tmp, target)\n"
    )
    violations = _functions_with_both_signals(ast.parse(synthetic))
    assert violations == [("_write", 4)]


def test_guard_fires_on_a_synthetic_name_dot_replace_variant():
    """Non-vacuous proof (review finding): ``tmp_path.replace(path)`` -- a
    ``Path.replace`` call on a temp-path-shaped local, not an ``os``-bound
    name -- is functionally identical to ``os.replace`` and must ALSO be
    detected."""
    synthetic = (
        "import tempfile\n"
        "def _write(target):\n"
        "    handle, tmp = tempfile.mkstemp(dir=target.parent)\n"
        "    tmp_path = tmp\n"
        "    tmp_path.replace(target)\n"
    )
    violations = _functions_with_both_signals(ast.parse(synthetic))
    assert violations == [("_write", 2)]


def test_guard_does_not_fire_on_a_synthetic_replace_only_function():
    """A function that calls ``os.replace`` with no write-open call at all
    (the ``repoint_symlink_atomic`` shape: a symlink repoint, not a content
    write) must not be flagged -- proves the guard requires BOTH signals,
    not either alone."""
    synthetic = "import os\ndef repoint(path, target, tmp):\n    os.symlink(target, tmp)\n    os.replace(tmp, path)\n"
    assert _functions_with_both_signals(ast.parse(synthetic)) == []


def test_guard_does_not_fire_on_an_unrelated_dot_replace_call():
    """A ``.replace(...)`` call on a NON-temp-shaped name (ordinary
    ``str.replace``) must not be treated as an os.replace-equivalent, even
    alongside a write-open call in the same function -- the heuristic is
    scoped to temp-path-shaped receivers, not every ``.replace(...)`` call
    fleet-wide."""
    synthetic = (
        "import tempfile\n"
        "def _write(target, text):\n"
        "    handle, tmp = tempfile.mkstemp(dir=target.parent)\n"
        "    cleaned = text.replace('a', 'b')\n"
        "    return cleaned\n"
    )
    assert _functions_with_both_signals(ast.parse(synthetic)) == []


def test_guard_does_not_fire_on_repoint_symlink_atomics_real_body():
    """Non-vacuous proof (negative), against the REAL source: reads the
    actual ``fs_local.py`` from disk and confirms the whole file -- including
    ``repoint_symlink_atomic``, which does call ``os.replace`` -- carries no
    violation, because that function never opens a file for writing (only
    ``os.symlink``). CAP-2's Boundaries name this function explicitly out of
    scope for the atomic-write extraction."""
    fs_local_path = PACKAGES_ROOT / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "adapters" / "fs_local.py"
    assert fs_local_path.is_file(), f"expected {fs_local_path} to exist"
    tree = _parse(fs_local_path)
    function_names = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "repoint_symlink_atomic" in function_names
    violations = _functions_with_both_signals(tree)
    assert violations == [], f"fs_local.py has unexpected sole-ownership violation(s): {violations}"
