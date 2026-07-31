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


def _module_level_exit_names(tree: ast.Module) -> list[str]:
    """`EXIT_*` names assigned directly in the module body -- not inside a
    function or class, so a same-spelled local variable elsewhere is not
    mistaken for a rogue owner.

    Each target is AST-walked, not just checked for a bare `ast.Name`, so a
    tuple/list-unpacking assignment (e.g. `EXIT_ROGUE, _ = 99, None`) can't
    hide an `EXIT_*` name from a shallower check that only recognized a
    direct `ast.Name` target.
    """
    names = []
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            for sub in ast.walk(target):
                if isinstance(sub, ast.Name) and sub.id.startswith("EXIT_"):
                    names.append(sub.id)
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
