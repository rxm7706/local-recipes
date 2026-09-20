"""AD-2 — dependency direction: no use-case module reaches an external tool
directly.

Only `cli.py`, `cfe.py` (the sole CFE caller, AD-3/AD-4), and adapters under
`engines/` (AD-12) may spawn a process, so only they may `import subprocess`.
Everything else — the use-case nouns, shared shapes, the resolution chain —
must go through those seams.

AST-based, not string/regex matching (Story 1.1's retro finding: a naive
text scan fails on a comment that merely *mentions* the banned name — see
`test_namespace_is_implicit.py::test_no_cli_framework_dependency`'s
docstring for the concrete precedent). `cfe.py` and `engines/*.py` don't
exist yet this story, so this test is vacuous-but-real today: it pins the
invariant now and starts actually excluding files the moment Epic 2 adds
them, mirroring how `test_namespace_is_implicit.py` pins a structural
invariant ahead of full population.

Story 2.1 adds a second, unconditional guard: AD-4 forbids `import`,
`importlib.import_module`, or `exec` of CFE code anywhere in
`pyforge/mason/`, with no allowlist at all (unlike the `subprocess` guard
above, which permits exactly the three seam modules). The `import`/`from
... import` half of that ban is already covered by every other meta-test in
this suite naming CFE modules explicitly (there is no CFE *code* to import
in-process anywhere yet); what no existing guard covers is a dynamic
`importlib.import_module(...)` or `exec(...)` call, which sidesteps a
static `import` scan entirely. That gap is what this addition closes.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "mason"


def _allowed_paths(root: Path) -> set[Path]:
    """The only modules permitted to `import subprocess` under `root`.

    Full resolved paths, not bare filenames (review finding #3) — a
    same-named file elsewhere in the tree (e.g. some `nested/cli.py`) must
    NOT be wrongly exempted just because its filename matches.
    """
    allowed = {root / "cli.py", root / "cfe.py"}
    allowed.update((root / "engines").glob("*.py"))
    return {p.resolve() for p in allowed}


def _find_subprocess_importers(root: Path, allowed: set[Path]) -> list[Path]:
    """Return every `.py` file under `root`, outside `allowed`, that has an
    `import subprocess` or `from subprocess import ...` AST node."""
    violators = []
    for path in sorted(root.rglob("*.py")):
        if path.resolve() in allowed:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            # Same rationale as the decode/parse handlers below: a file the
            # scanner cannot even read (broken symlink, permissions) is a
            # file it cannot prove clean, and a raw traceback is not an
            # actionable test failure.
            raise AssertionError(
                f"{path}: unreadable ({exc}); the AD-2 subprocess-import guard cannot AST-scan this file"
            ) from exc
        except UnicodeDecodeError as exc:
            # Fail loudly rather than silently skip (review finding #5): a
            # guard that cannot read a file cannot prove that file is clean,
            # and a raw UnicodeDecodeError traceback is not an actionable
            # test failure. This is the simplest correct behavior — a
            # genuinely non-UTF-8 `.py` file under this tree is itself a
            # bug worth surfacing, not a case to special-case around.
            raise AssertionError(
                f"{path}: not valid UTF-8; the AD-2 subprocess-import guard cannot AST-scan this file"
            ) from exc

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            # Same rationale as the UnicodeDecodeError handling above: a file
            # the scanner cannot parse is a file it cannot prove clean, and a
            # raw SyntaxError traceback is not an actionable test failure.
            raise AssertionError(
                f"{path}: invalid Python syntax; the AD-2 subprocess-import guard cannot AST-scan this file"
            ) from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(alias.name == "subprocess" for alias in node.names):
                violators.append(path)
                break
            if isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                violators.append(path)
                break
    return violators


def test_no_subprocess_import_outside_the_allowlist():
    # Guard the guard: if the package layout ever moves, rglob over a stale
    # path would yield zero files and this test would pass vacuously forever.
    assert PKG_ROOT.is_dir(), f"AD-2 guard is scanning nothing — package root moved? {PKG_ROOT}"
    violators = _find_subprocess_importers(PKG_ROOT, _allowed_paths(PKG_ROOT))
    assert not violators, (
        f"AD-2: only cli.py, cfe.py, and engines/*.py may `import subprocess`; found it in: {violators}"
    )


# --- Regression fixtures proving the detection logic itself (review finding
# #4): synthetic trees, not the real package, so these assert the scanner's
# behavior independent of what src/pyforge/mason/ currently contains. ------


def test_detection_fires_on_a_violation_and_permits_allowed_files(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cli.py").write_text("import subprocess\n", encoding="utf-8")
    (root / "recipe.py").write_text("import subprocess\n", encoding="utf-8")
    (root / "other.py").write_text("from subprocess import run\n", encoding="utf-8")
    engines = root / "engines"
    engines.mkdir()
    (engines / "pixi.py").write_text("import subprocess\n", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir()
    # Same bare filename as the allowed cli.py, different path — must NOT be
    # exempted by a filename-only allowlist (review finding #3).
    (nested / "cli.py").write_text("import subprocess\n", encoding="utf-8")

    violators = {p.resolve() for p in _find_subprocess_importers(root, _allowed_paths(root))}

    assert (root / "recipe.py").resolve() in violators
    assert (root / "other.py").resolve() in violators
    assert (nested / "cli.py").resolve() in violators
    assert (root / "cli.py").resolve() not in violators
    assert (engines / "pixi.py").resolve() not in violators


def test_non_utf8_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")

    with pytest.raises(AssertionError, match="not valid UTF-8"):
        _find_subprocess_importers(root, _allowed_paths(root))


def test_invalid_syntax_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_text("def(:\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="invalid Python syntax"):
        _find_subprocess_importers(root, _allowed_paths(root))


def test_unreadable_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").symlink_to(root / "does-not-exist.py")

    with pytest.raises(AssertionError, match="unreadable"):
        _find_subprocess_importers(root, _allowed_paths(root))


# --- AD-4 — no importlib.import_module(...) or exec(...) call, anywhere,
# --- no allowlist (Story 2.1) ------------------------------------------------


def _collect_import_module_aliases(tree: ast.Module) -> tuple[set[str], set[str]]:
    """Collect every local name bound to the `importlib` module itself, and
    every local name bound to `importlib.import_module` directly (via `from
    importlib import import_module`), anywhere in `tree` — including
    `as`-aliased forms and names bound inside a nested function body (AD-4
    has no lazy-import carve-out, so aliasing must be resolved tree-wide,
    not just at module scope). The unaliased forms (`import importlib`,
    `from importlib import import_module`) fall out of this uniformly:
    `alias.asname or alias.name` yields the plain name when no `as` clause
    is present.

    Review pass (2026-08-11): the original version of this guard matched
    only the literal names `"importlib"`/`"import_module"`, so `import
    importlib as il; il.import_module(...)` (or the `from ... import
    import_module as im` equivalent) reached `importlib.import_module`
    without ever being recognized as such."""
    importlib_names: set[str] = set()
    import_module_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    importlib_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    import_module_names.add(alias.asname or alias.name)
    return importlib_names, import_module_names


def _is_import_module_call(func: ast.expr, importlib_names: set[str], import_module_names: set[str]) -> bool:
    """True for `func` shaped as `<importlib alias>.import_module` (an
    attribute access whose base name resolves to the `importlib` module, by
    however it was locally aliased) or a bare name resolving to
    `importlib.import_module` itself (the `from importlib import
    import_module [as ...]` idiom)."""
    if isinstance(func, ast.Attribute):
        return func.attr == "import_module" and isinstance(func.value, ast.Name) and func.value.id in importlib_names
    if isinstance(func, ast.Name):
        return func.id in import_module_names
    return False


def _is_exec_call(func: ast.expr) -> bool:
    """True for `func` shaped as the bare `exec` builtin name. `exec` is a
    builtin, never a legal attribute access (there is no `foo.exec(...)`
    form to also guard against), so a bare-name check is exhaustive."""
    return isinstance(func, ast.Name) and func.id == "exec"


def _is_dunder_import_call(func: ast.expr) -> bool:
    """True for a call to the `__import__` builtin — Python's own low-level
    import primitive, and what an `import` statement compiles down to.
    AD-4's rule text bans "no `import`... ever"; `__import__` is a way to
    perform that same operation as an ordinary function call, sidestepping
    every `import`-statement form entirely (review pass, 2026-08-11: found
    unguarded by the original version of this detector, which only matched
    `importlib.import_module`/`exec`). Like `exec`, it is always a bare
    builtin name, never a legal attribute access."""
    return isinstance(func, ast.Name) and func.id == "__import__"


def _find_importlib_or_exec_callers(root: Path) -> list[Path]:
    """Return every `.py` file under `root` containing a call shaped like
    `importlib.import_module(...)` (however aliased), a bare
    `import_module(...)` call (however aliased), an `exec(...)` call, or an
    `__import__(...)` call — anywhere in the file, unconditionally (AD-4 has
    no lazy-import carve-out like AD-6's `test_capability_tiers.py` guard; a
    dynamic import/exec of CFE code is banned even inside a function body,
    because AD-4's whole point is that CFE is *never* loaded in-process, not
    merely "not eagerly").

    Scope boundary (review pass, 2026-08-11): resolves direct aliasing of
    `importlib`/`import_module` via `import`/`from...import` statements
    only. It does not trace indirect rebinding (`dynamic_import =
    importlib.import_module; dynamic_import(...)`) or reflective lookups
    (`globals()["__import__"](...)`) — those are open-ended and belong to
    Story 2.2's dedicated, more thorough seam-guard methodology, not this
    incidental AD-4 check."""
    violators = []
    for path in sorted(root.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise AssertionError(
                f"{path}: unreadable ({exc}); the AD-4 import_module/exec guard cannot AST-scan this file"
            ) from exc
        except UnicodeDecodeError as exc:
            raise AssertionError(
                f"{path}: not valid UTF-8; the AD-4 import_module/exec guard cannot AST-scan this file"
            ) from exc

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise AssertionError(
                f"{path}: invalid Python syntax; the AD-4 import_module/exec guard cannot AST-scan this file"
            ) from exc

        importlib_names, import_module_names = _collect_import_module_aliases(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and (
                _is_import_module_call(node.func, importlib_names, import_module_names)
                or _is_exec_call(node.func)
                or _is_dunder_import_call(node.func)
            ):
                violators.append(path)
                break
    return violators


def test_no_importlib_import_module_or_exec_call_anywhere():
    # Guard the guard: same rationale as test_no_subprocess_import_outside_
    # the_allowlist above — a stale PKG_ROOT would make this pass vacuously.
    assert PKG_ROOT.is_dir(), f"AD-4 guard is scanning nothing — package root moved? {PKG_ROOT}"
    violators = _find_importlib_or_exec_callers(PKG_ROOT)
    assert not violators, (
        "AD-4: no importlib.import_module(...), exec(...), or __import__(...) "
        f"call is permitted anywhere in pyforge.mason, no allowlist — found "
        f"it in: {violators}"
    )


def test_importlib_detection_fires_on_the_attribute_form(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import importlib\nimportlib.import_module('conda_forge_expert')\n",
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_importlib_or_exec_callers(root)}

    assert (root / "sneaky.py").resolve() in violators


def test_importlib_detection_fires_on_the_bare_name_form(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "from importlib import import_module\nimport_module('conda_forge_expert')\n",
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_importlib_or_exec_callers(root)}

    assert (root / "sneaky.py").resolve() in violators


def test_exec_detection_fires_on_a_bare_call(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text("exec(open('cfe_script.py').read())\n", encoding="utf-8")

    violators = {p.resolve() for p in _find_importlib_or_exec_callers(root)}

    assert (root / "sneaky.py").resolve() in violators


def test_importlib_or_exec_detection_fires_even_nested_inside_a_function(tmp_path):
    """Unlike AD-6's `test_capability_tiers.py` lazy-import carve-out, AD-4
    has no "nested in a function body is fine" exception — this guard must
    fire regardless of nesting depth."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "def helper():\n    import importlib\n    return importlib.import_module('conda_forge_expert')\n",
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_importlib_or_exec_callers(root)}

    assert (root / "sneaky.py").resolve() in violators


def test_importlib_or_exec_detection_permits_unrelated_calls_and_imports(tmp_path):
    """A bare `import importlib` with no `import_module`/`exec` call, and an
    unrelated attribute access ending in a different name, must not be
    flagged — the detector targets the specific call shapes, not the mere
    presence of the word `importlib`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "clean.py").write_text(
        "import importlib\nimportlib.metadata.version('pyforge-mason')\ndef execute():\n    return 1\nexecute()\n",
        encoding="utf-8",
    )

    violators = _find_importlib_or_exec_callers(root)

    assert violators == []


def test_dunder_import_detection_fires_on_a_bare_call(tmp_path):
    """Review pass (2026-08-11): `__import__` is Python's own low-level
    import primitive and was completely unguarded by the original detector,
    which only recognized `importlib.import_module`/`exec`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        '__import__("pyforge.mason.cfe", fromlist=["cfe"])\n',
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_importlib_or_exec_callers(root)}

    assert (root / "sneaky.py").resolve() in violators


def test_importlib_detection_fires_on_an_aliased_module_import(tmp_path):
    """Review pass (2026-08-11): `import importlib as il` then
    `il.import_module(...)` reaches the exact same function as the
    unaliased form and was undetected before `_collect_import_module_
    aliases` resolved local names back to `importlib`."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import importlib as il\nil.import_module('conda_forge_expert')\n",
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_importlib_or_exec_callers(root)}

    assert (root / "sneaky.py").resolve() in violators


def test_importlib_detection_fires_on_an_aliased_import_module_from_import(tmp_path):
    """Review pass (2026-08-11): `from importlib import import_module as im`
    then `im(...)` reaches `importlib.import_module` under a name the
    original bare-name check (`func.id == "import_module"`) never
    recognized."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "from importlib import import_module as im\nim('conda_forge_expert')\n",
        encoding="utf-8",
    )

    violators = {p.resolve() for p in _find_importlib_or_exec_callers(root)}

    assert (root / "sneaky.py").resolve() in violators


# --- models.py is a dependency-direction LEAF (Consistency Conventions,
# --- Story 2.1, review pass 2026-08-11) --------------------------------

_MODELS_PATH = PKG_ROOT / "models.py"

_MODELS_ALLOWED_RELATIVE_IMPORTS = frozenset({"engines"})
"""The only sibling `pyforge.mason` module `models.py` may import from
(Consistency Conventions: "models.py is a LEAF the presentation layer
imports safely" — re-affirmed 2026-08-10, spec-pyforge-mason memlog). `
.engines` is itself a leaf with zero internal-package imports, so this one
exception cannot introduce a cycle back through `models.py`. Nothing
enforced this before Story 2.1's review pass — a future story importing,
say, `.doctor` into `models.py` would silently reintroduce the exact import
cycle the 2026-08-10 re-decision was written to prevent."""


def _find_models_leaf_violations(path: Path) -> list[str]:
    """Return a description of every relative import in `path` that does
    not resolve to `.engines` — `models.py`'s only sanctioned sibling
    import. A relative import naming anything else (`.cli`, `.doctor`,
    `.cfe`, `.resolve`, `.errors`, ...) risks the exact cycle the "leaf"
    guarantee exists to rule out, since those modules may themselves come
    to depend on `models.py`'s own shapes."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            if node.module is None:
                # `from . import X` — each imported name must itself be
                # an allowed sibling.
                for alias in node.names:
                    if alias.name not in _MODELS_ALLOWED_RELATIVE_IMPORTS:
                        violations.append(f"from . import {alias.name}")
            elif node.module not in _MODELS_ALLOWED_RELATIVE_IMPORTS:
                violations.append(f"from .{node.module} import ...")
    return violations


def test_models_module_imports_only_the_sanctioned_engines_sibling():
    # Guard the guard: same rationale as PKG_ROOT.is_dir() above — a stale
    # path would make this pass vacuously.
    assert _MODELS_PATH.is_file(), f"models.py leaf guard is scanning nothing — has it moved? {_MODELS_PATH}"
    violations = _find_models_leaf_violations(_MODELS_PATH)
    assert not violations, (
        "models.py must stay a dependency-direction leaf — its only "
        f"sanctioned sibling import is `.engines`; found: {violations}"
    )


def test_models_leaf_detector_fires_on_an_unsanctioned_relative_import(tmp_path):
    models = tmp_path / "models.py"
    models.write_text("from .doctor import DoctorReport\n", encoding="utf-8")

    assert _find_models_leaf_violations(models)


def test_models_leaf_detector_fires_on_an_unsanctioned_bare_relative_import(tmp_path):
    models = tmp_path / "models.py"
    models.write_text("from . import doctor\n", encoding="utf-8")

    assert _find_models_leaf_violations(models)


def test_models_leaf_detector_permits_the_engines_import(tmp_path):
    models = tmp_path / "models.py"
    models.write_text("from .engines import EngineStatus\n", encoding="utf-8")

    assert _find_models_leaf_violations(models) == []
