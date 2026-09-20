"""AD-6 -- capability tiers are structural, not conventional: `package.py`,
`environment.py`, and `doctor.py` must never carry a *module-level* `cfe`
import (Story 1.7's Design Notes; Story 1.8 adds `doctor.py` to the guard,
since AD-6's own text names it alongside the other two CFE-independent
modules and this story is what gives the file real content to scan).

"Module-level" here means "still eager at import time" -- not merely "a
direct child of `tree.body`". A `cfe` import nested inside a top-level
`try`/`if`/`with` block (e.g. the common optional-dependency idiom
`try: from . import cfe` / `except ImportError: cfe = None`) still runs
when the module is imported, so the detector recurses into those compound
statements' bodies (and `Try`'s handlers/orelse/finalbody). It never
descends into `FunctionDef`/`AsyncFunctionDef`/`ClassDef` bodies, though --
those are genuinely deferred until called/instantiated, and that is the
*lazy* `cfe` import AD-6 explicitly permits for `package.py`'s future
conda-forge ship target (Epic 3). This is the one deliberate divergence
from `test_dependency_direction.py`/`test_exit_code_ownership.py`, whose
blanket bans have no lazy-import exception to preserve.

The detector also recognizes dotted/absolute import forms, not just the
bare `cfe`/relative-dot forms: `import pyforge.mason.cfe` (an
`ast.alias.name` ending in `.cfe`) and `from pyforge.mason import cfe` (an
`ast.ImportFrom.module` ending in `mason`, importing an alias named `cfe`)
are both flagged.

Per the spec's Tasks & Acceptance, unreadable/non-UTF-8/invalid-syntax file
handling is not required here -- only the module-level-vs-nested distinction
is novel; the sibling meta-tests already cover that hardening rigor for
their own guards.
"""

from __future__ import annotations

import ast
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "mason"

_GUARDED_FILENAMES = ("package.py", "environment.py", "doctor.py")


def _import_matches_cfe(node: ast.Import) -> bool:
    """True if `node` (`import cfe` or `import pyforge.mason.cfe`) binds a
    `cfe` module -- the bare name or a dotted absolute form ending in
    `.cfe`."""
    return any(alias.name == "cfe" or alias.name.endswith(".cfe") for alias in node.names)


def _import_from_matches_cfe(node: ast.ImportFrom) -> bool:
    """True if `node` imports `cfe` via a `from ... import ...` form:
    `from .cfe import ...` / `from pyforge.mason.cfe import ...` (module is
    `cfe` or ends with `.cfe`), or `from . import cfe` / `from pyforge.mason
    import cfe` (module is `None` or ends with `mason`, and an alias named
    `cfe` is imported)."""
    module = node.module
    if module == "cfe" or (module is not None and module.endswith(".cfe")):
        return True
    if module is None or module.endswith("mason"):
        return any(alias.name == "cfe" for alias in node.names)
    return False


def _scan_for_module_level_cfe_import(body: list[ast.stmt]) -> bool:
    """Scan `body` (a list of statements at module level, or nested inside
    a top-level `Try`/`If`/`With`) for a `cfe` import that is still eager at
    import time.

    Recurses into `Try` (body/handlers/orelse/finalbody), `If`
    (body/orelse), and `With` (body) -- those compound statements all run
    at import time. Never recurses into `FunctionDef`/`AsyncFunctionDef`/
    `ClassDef` bodies: a `cfe` import nested there is deferred until
    called/instantiated, which is the lazy import AD-6 permits."""
    for node in body:
        if isinstance(node, ast.Import) and _import_matches_cfe(node):
            return True
        if isinstance(node, ast.ImportFrom) and _import_from_matches_cfe(node):
            return True
        if isinstance(node, ast.Try):
            if (
                _scan_for_module_level_cfe_import(node.body)
                or _scan_for_module_level_cfe_import(node.orelse)
                or _scan_for_module_level_cfe_import(node.finalbody)
                or any(_scan_for_module_level_cfe_import(handler.body) for handler in node.handlers)
            ):
                return True
        elif isinstance(node, ast.If):
            if _scan_for_module_level_cfe_import(node.body) or _scan_for_module_level_cfe_import(node.orelse):
                return True
        elif isinstance(node, ast.With):
            if _scan_for_module_level_cfe_import(node.body):
                return True
        # FunctionDef/AsyncFunctionDef/ClassDef: deliberately not descended
        # into -- see docstring.
    return False


def _has_module_level_cfe_import(tree: ast.Module) -> bool:
    """True if `tree` carries a `cfe` import that is still eager at import
    time -- a direct child of `tree.body`, or nested inside a top-level
    `try`/`if`/`with` block -- covering both the bare/relative-dot forms
    (`import cfe`, `from . import cfe`, `from .cfe import ...`) and
    dotted/absolute forms (`import pyforge.mason.cfe`, `from pyforge.mason
    import cfe`).

    A `cfe` import nested inside a function/class body is never visited --
    see `_scan_for_module_level_cfe_import`'s docstring -- so the lazy
    import AD-6 permits is not flagged."""
    return _scan_for_module_level_cfe_import(tree.body)


def _find_violators(root: Path, filenames: tuple[str, ...]) -> list[Path]:
    """Return every guarded file under `root` that carries a module-level
    `cfe` import. A guarded file that does not exist under `root` is simply
    skipped, not an error."""
    violators = []
    for filename in filenames:
        path = root / filename
        if not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _has_module_level_cfe_import(tree):
            violators.append(path)
    return violators


def test_package_and_environment_carry_no_module_level_cfe_import():
    # Guard the guard: if the package layout ever moves, scanning a stale
    # path would yield zero files and this test would pass vacuously forever.
    assert PKG_ROOT.is_dir(), f"AD-6 guard is scanning nothing -- package root moved? {PKG_ROOT}"
    # Second vacuity mode (Phase 1 audit, 2026-08-10): `_find_violators`
    # SKIPS a guarded filename that no longer exists, so renaming or
    # splitting package.py/environment.py/doctor.py (e.g. into a package/
    # subpackage in Epic 3) would silently drop it from the guard while the
    # suite stays green. Every guarded name must resolve to a real file; a
    # rename must update _GUARDED_FILENAMES in the same change.
    missing = [f for f in _GUARDED_FILENAMES if not (PKG_ROOT / f).is_file()]
    assert not missing, (
        "AD-6 guard lost sight of a guarded module -- renamed or split "
        f"without updating _GUARDED_FILENAMES? missing: {missing}"
    )
    violators = _find_violators(PKG_ROOT, _GUARDED_FILENAMES)
    assert not violators, (
        "AD-6: package.py/environment.py/doctor.py must never carry a "
        f"module-level `cfe` import; found one in: {violators}"
    )


# --- Regression fixtures proving the detector itself (mirrors
# test_dependency_direction.py's rigor): synthetic files, not the real
# package, so these assert the detector's behavior independent of what
# src/pyforge/mason/ currently contains. ------------------------------------


def test_detector_fires_on_a_module_level_import_cfe(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "package.py").write_text("import cfe\n", encoding="utf-8")

    violators = {p.resolve() for p in _find_violators(root, _GUARDED_FILENAMES)}

    assert (root / "package.py").resolve() in violators


def test_detector_fires_on_a_module_level_from_dot_import_cfe(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "environment.py").write_text("from . import cfe\n", encoding="utf-8")

    violators = {p.resolve() for p in _find_violators(root, _GUARDED_FILENAMES)}

    assert (root / "environment.py").resolve() in violators


def test_detector_fires_on_a_module_level_from_dot_cfe_import(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "package.py").write_text(
        "from .cfe import ensure_cfe_root\n",
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_violators(root, _GUARDED_FILENAMES)}

    assert (root / "package.py").resolve() in violators


def test_detector_permits_a_lazy_function_body_cfe_import(tmp_path):
    """AD-6 explicitly permits `package.py`'s future conda-forge ship target
    to import `cfe` lazily -- nested inside a function body, never at
    module scope -- and this detector must not flag it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "package.py").write_text(
        "def ship_conda_forge():\n    from . import cfe\n    return cfe\n",
        encoding="utf-8",
    )

    violators = _find_violators(root, _GUARDED_FILENAMES)

    assert violators == []


def test_detector_fires_on_a_module_level_dotted_absolute_import_cfe(tmp_path):
    """Review pass (2026-08-09): `import pyforge.mason.cfe`'s `ast.alias.name`
    is the full dotted string, not the bare `"cfe"` -- the detector must
    still recognize it as a `cfe` import."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "package.py").write_text("import pyforge.mason.cfe\n", encoding="utf-8")

    violators = {p.resolve() for p in _find_violators(root, _GUARDED_FILENAMES)}

    assert (root / "package.py").resolve() in violators


def test_detector_fires_on_a_module_level_dotted_absolute_from_import_cfe(tmp_path):
    """Review pass (2026-08-09): `from pyforge.mason import cfe`'s
    `node.module` is `"pyforge.mason"`, not `"cfe"` or `None` -- the
    detector must still recognize it as a `cfe` import."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "environment.py").write_text(
        "from pyforge.mason import cfe\n",
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_violators(root, _GUARDED_FILENAMES)}

    assert (root / "environment.py").resolve() in violators


def test_detector_fires_on_a_module_level_cfe_import_nested_in_a_try_block(tmp_path):
    """Review pass (2026-08-09): the common optional-dependency idiom
    (`try: from . import cfe` / `except ImportError: cfe = None`) still
    executes eagerly at import time -- its `ImportFrom` node lives inside
    `ast.Try.body`, not as a direct child of `tree.body`, so the detector
    must recurse into it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "package.py").write_text(
        "try:\n    from . import cfe\nexcept ImportError:\n    cfe = None\n",
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_violators(root, _GUARDED_FILENAMES)}

    assert (root / "package.py").resolve() in violators


def test_detector_ignores_files_outside_the_guarded_filenames(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "recipe.py").write_text("import cfe\n", encoding="utf-8")

    violators = _find_violators(root, _GUARDED_FILENAMES)

    assert violators == []


def test_detector_permits_a_module_with_no_cfe_import_at_all(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "package.py").write_text('"""Docstring only."""\n', encoding="utf-8")
    (root / "environment.py").write_text('"""Docstring only."""\n', encoding="utf-8")

    violators = _find_violators(root, _GUARDED_FILENAMES)

    assert violators == []


# --- Story 1.8: doctor.py joins the guard --------------------------------


def test_detector_fires_on_a_module_level_cfe_import_in_doctor(tmp_path):
    """Story 1.8 adds `doctor.py` to `_GUARDED_FILENAMES` -- a module-level
    `cfe` import there must be flagged exactly like `package.py`/
    `environment.py`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "doctor.py").write_text("from . import cfe\n", encoding="utf-8")

    violators = {p.resolve() for p in _find_violators(root, _GUARDED_FILENAMES)}

    assert (root / "doctor.py").resolve() in violators


def test_detector_permits_a_lazy_function_body_cfe_import_in_doctor(tmp_path):
    """`doctor.py`'s real `build_report` imports `cfe` lazily, inside its own
    function body (see the module's docstring) -- the detector must permit
    that shape for `doctor.py` exactly as it already does for `package.py`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "doctor.py").write_text(
        "def build_report():\n    from . import cfe\n    return cfe\n",
        encoding="utf-8",
    )

    violators = _find_violators(root, _GUARDED_FILENAMES)

    assert violators == []
