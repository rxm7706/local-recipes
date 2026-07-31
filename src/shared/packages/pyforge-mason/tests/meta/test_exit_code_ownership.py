"""AD-7 — one exit-code owner: no module besides `exit_codes.py` may define a
module-level `EXIT_*` name.

Mirrors `test_dependency_direction.py`'s approach for AD-2: AST-based, not
string/regex matching, so a comment or docstring that merely *mentions* an
`EXIT_*` name is not flagged, and only a genuine module-level definition
counts -- a same-spelled local variable inside a function body is not the
drift AD-7 exists to prevent.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "mason"


def _owner_path(root: Path) -> Path:
    """The only module permitted to define a module-level `EXIT_*` name."""
    return (root / "exit_codes.py").resolve()


# Nodes that open a new (non-module) scope: names bound inside them are
# locals/attributes, not module-level names, so the scan must not descend.
_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def _module_level_exit_names(tree: ast.Module) -> list[str]:
    """`EXIT_*` names bound at module scope -- not inside a function, class,
    or lambda, so a same-spelled local variable or class attribute is not
    mistaken for a rogue owner.

    The scan recurses through nested *statements* (if/try/for/while/with) and
    recognizes every module-level binding form, not just a bare top-level
    `x = ...`: plain/unpacking/annotated/augmented assignment, walrus
    (`:=`), `for`/`with ... as` targets, `except ... as` names, `def`/`class`
    names, and `import ... as` aliases. A shallower check that only iterated
    `tree.body` for `ast.Assign` would let e.g. a platform-conditional
    `if sys.platform == "win32": EXIT_WIN = 75` -- the most realistic drift
    vector -- pass undetected.

    The one sanctioned binding is consumption of the contract itself:
    `from <...>.exit_codes import EXIT_X` with no rename. Renaming
    (`as EXIT_Y`) or importing an `EXIT_*` name from anywhere else creates a
    new module-level `EXIT_*` name and is flagged.
    """
    names: list[str] = []

    def record(name: str) -> None:
        if name.startswith("EXIT_"):
            names.append(name)

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPE_NODES):
                # def/class statements still BIND their own name at module
                # level, even though their bodies are a new scope.
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    record(child.name)
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                record(child.id)
            elif isinstance(child, ast.ExceptHandler) and child.name:
                record(child.name)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                from_owner = (
                    isinstance(child, ast.ImportFrom)
                    and child.module is not None
                    and child.module.rpartition(".")[2] == "exit_codes"
                )
                for alias in child.names:
                    if from_owner and alias.asname is None:
                        continue  # canonical, un-renamed consumption
                    record(alias.asname or alias.name.split(".")[0])
            visit(child)

    visit(tree)
    return names


def _find_rogue_exit_code_owners(root: Path, owner: Path) -> list[Path]:
    """Return every `.py` file under `root`, other than `owner`, that defines
    a module-level `EXIT_*` name."""
    violators = []
    for path in sorted(root.rglob("*.py")):
        if path.resolve() == owner:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            # A file the scanner cannot even read (broken symlink,
            # permissions) is a file it cannot prove clean -- same rationale
            # as test_dependency_direction.py's unreadable-file handling.
            raise AssertionError(
                f"{path}: unreadable ({exc}); the AD-7 exit-code-ownership "
                "guard cannot AST-scan this file"
            ) from exc
        except UnicodeDecodeError as exc:
            raise AssertionError(
                f"{path}: not valid UTF-8; the AD-7 exit-code-ownership "
                "guard cannot AST-scan this file"
            ) from exc

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise AssertionError(
                f"{path}: invalid Python syntax; the AD-7 exit-code-ownership "
                "guard cannot AST-scan this file"
            ) from exc

        if _module_level_exit_names(tree):
            violators.append(path)
    return violators


def test_no_rogue_exit_code_owner_outside_exit_codes_py():
    # Guard the guard: if the package layout ever moves, rglob over a stale
    # path would yield zero files and this test would pass vacuously forever.
    assert PKG_ROOT.is_dir(), (
        f"AD-7 guard is scanning nothing — package root moved? {PKG_ROOT}"
    )
    violators = _find_rogue_exit_code_owners(PKG_ROOT, _owner_path(PKG_ROOT))
    assert not violators, (
        "AD-7: only exit_codes.py may define a module-level EXIT_* name; "
        f"found one in: {violators}"
    )


def test_exit_codes_py_itself_defines_the_contract():
    # A guard that never actually fires on the owner file could be silently
    # vacuous (e.g. a typo in _owner_path). Prove the owner really does carry
    # EXIT_* names, so the exclusion above is excluding something real.
    tree = ast.parse((PKG_ROOT / "exit_codes.py").read_text(encoding="utf-8"))
    assert set(_module_level_exit_names(tree)) == {
        "EXIT_OK", "EXIT_FAILED", "EXIT_USAGE", "EXIT_CFE_UNAVAILABLE", "EXIT_INTERRUPTED",
    }


# --- Regression fixtures proving the detection logic itself, mirroring
# test_dependency_direction.py's rigor: synthetic trees, not the real
# package, so these assert the scanner's behavior independent of what
# src/pyforge/mason/ currently contains. -------------------------------------

def test_detection_fires_on_a_violation_and_permits_the_owner_file(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "exit_codes.py").write_text("EXIT_OK = 0\nEXIT_FAILED = 1\n", encoding="utf-8")
    (root / "cli.py").write_text("EXIT_ROGUE = 99\n", encoding="utf-8")
    (root / "other.py").write_text("EXIT_ANOTHER: int = 3\n", encoding="utf-8")
    # A same-spelled local inside a function body is not module-level and
    # must NOT be flagged.
    (root / "clean.py").write_text(
        "def f():\n    EXIT_LOCAL = 5\n    return EXIT_LOCAL\n", encoding="utf-8",
    )
    nested = root / "nested"
    nested.mkdir()
    # Same bare filename as the owner, different path — must NOT be exempted
    # by a filename-only allowlist (the same failure mode test_dependency_
    # direction.py's regression fixtures guard against for cli.py).
    (nested / "exit_codes.py").write_text("EXIT_NESTED = 7\n", encoding="utf-8")

    owner = _owner_path(root)
    violators = {p.resolve() for p in _find_rogue_exit_code_owners(root, owner)}

    assert (root / "cli.py").resolve() in violators
    assert (root / "other.py").resolve() in violators
    assert (nested / "exit_codes.py").resolve() in violators
    assert (root / "exit_codes.py").resolve() not in violators
    assert (root / "clean.py").resolve() not in violators


def test_tuple_unpacking_assignment_does_not_hide_a_rogue_exit_name(tmp_path):
    """`EXIT_ROGUE, _ = 99, None` is still a module-level binding of an
    `EXIT_*` name -- a target-type check that only recognized a bare
    `ast.Name` would miss it."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "exit_codes.py").write_text("EXIT_OK = 0\n", encoding="utf-8")
    (root / "sneaky.py").write_text("EXIT_ROGUE, _ignored = 99, None\n", encoding="utf-8")

    violators = {p.resolve() for p in _find_rogue_exit_code_owners(root, _owner_path(root))}

    assert (root / "sneaky.py").resolve() in violators


@pytest.mark.parametrize("source", [
    pytest.param('if True:\n    EXIT_WIN = 75\n', id="conditional"),
    pytest.param('(EXIT_W := 9)\n', id="walrus"),
    pytest.param('try:\n    EXIT_T = 1\nexcept Exception:\n    pass\n', id="try-block"),
    pytest.param('for EXIT_I in [1]:\n    pass\n', id="for-target"),
    pytest.param('with open("x") as EXIT_F:\n    pass\n', id="with-as"),
    pytest.param('while False:\n    EXIT_LOOP = 4\n', id="while-body"),
    pytest.param('try:\n    pass\nexcept OSError as EXIT_E:\n    pass\n', id="except-as"),
    pytest.param('EXIT_AUG = 0\nEXIT_AUG += 1\n', id="aug-assign"),
    pytest.param('import os as EXIT_OS\n', id="import-as"),
    pytest.param('from os.path import sep as EXIT_SEP\n', id="from-import-as"),
    pytest.param('from other_module import EXIT_FOREIGN\n', id="foreign-exit-import"),
    pytest.param('from exit_codes import EXIT_OK as EXIT_YES\n', id="renamed-canonical-import"),
    pytest.param('def EXIT_helper():\n    pass\n', id="def-name"),
])
def test_nested_and_indirect_module_level_bindings_are_not_hidden(tmp_path, source):
    """Every module-level binding form must be visible to the scanner — a
    shallow `tree.body`-only walk missed all the nested/indirect ones (the
    platform-conditional case being the realistic drift vector)."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "exit_codes.py").write_text("EXIT_OK = 0\n", encoding="utf-8")
    (root / "sneaky.py").write_text(source, encoding="utf-8")

    violators = {p.resolve() for p in _find_rogue_exit_code_owners(root, _owner_path(root))}

    assert (root / "sneaky.py").resolve() in violators


def test_canonical_unrenamed_exit_codes_import_is_not_flagged(tmp_path):
    """`from .exit_codes import EXIT_OK` is the sanctioned way for cli.py to
    consume the contract — it re-binds the canonical names, it doesn't define
    new ones. (The real cli.py depends on this exemption.)"""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "exit_codes.py").write_text("EXIT_OK = 0\nEXIT_FAILED = 1\n", encoding="utf-8")
    (root / "cli.py").write_text(
        "from .exit_codes import EXIT_FAILED, EXIT_OK\n", encoding="utf-8",
    )

    violators = _find_rogue_exit_code_owners(root, _owner_path(root))

    assert violators == []


def test_bindings_inside_functions_classes_and_lambdas_are_not_flagged(tmp_path):
    """Scope exclusion: locals, class attributes, and lambda parameters named
    EXIT_* are not module-level names and must not be flagged."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "exit_codes.py").write_text("EXIT_OK = 0\n", encoding="utf-8")
    (root / "scoped.py").write_text(
        "def f():\n"
        "    EXIT_LOCAL = 5\n"
        "    return EXIT_LOCAL\n"
        "class C:\n"
        "    EXIT_ATTR = 1\n"
        "g = lambda EXIT_ARG=1: EXIT_ARG\n",
        encoding="utf-8",
    )

    violators = _find_rogue_exit_code_owners(root, _owner_path(root))

    assert violators == []


def test_non_utf8_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")

    with pytest.raises(AssertionError, match="not valid UTF-8"):
        _find_rogue_exit_code_owners(root, _owner_path(root))


def test_invalid_syntax_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_text("def(:\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="invalid Python syntax"):
        _find_rogue_exit_code_owners(root, _owner_path(root))


def test_unreadable_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").symlink_to(root / "does-not-exist.py")

    with pytest.raises(AssertionError, match="unreadable"):
        _find_rogue_exit_code_owners(root, _owner_path(root))
