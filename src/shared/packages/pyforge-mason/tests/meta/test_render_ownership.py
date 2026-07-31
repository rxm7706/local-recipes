"""AD-8 — core returns data; only the driving adapter formats.

Only `cli.py` (the CLI shell -- argparse's own `--help`/`--version`/usage
output, and the sole call site of `render.write`) and `render.py` (the one
formatter) may write to stdout. Every use-case module that lands in a later
epic must call `render.write(...)` instead of formatting its own output --
this test's allowlist (`cli.py`, `render.py` only) already covers them
without needing a future edit (see the story spec's Design Notes).

AST-based, not string/regex matching -- mirrors
`test_dependency_direction.py`'s precedent exactly (a naive text scan fails
on a comment that merely *mentions* the banned pattern), including its
error-handling rigor (unreadable/non-UTF-8/invalid-syntax files fail the
test loudly, never silently, never with a raw traceback) and its
full-resolved-path allowlist (a same-named file elsewhere in the tree must
not be wrongly exempted just because its filename matches).

A stdout-writing call is either:
* `print(...)` with no `file=` keyword (the stdlib default is stdout), or
  with a `file=` keyword whose target is not literally `sys.stderr`/
  `stderr`;
* a `.write(...)`/`.writelines(...)` call whose target is literally
  `sys.stdout`, `sys.stdout.buffer`, or a bare `stdout` name (e.g.
  `from sys import stdout`) -- symmetric with the stderr-target check just
  below it, which already recognizes a bare `stderr` name.

`parser.print_help()` (argparse's own output surface, explicitly out of
scope for AD-8 per the story spec's Never clause) is a method call named
`print_help`, not `print`/`.write`, so it is never flagged by this scan.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "mason"


def _allowed_paths(root: Path) -> set[Path]:
    """The only modules permitted to write to stdout under `root`."""
    allowed = {root / "cli.py", root / "render.py"}
    return {p.resolve() for p in allowed}


def _is_stderr_target(node: ast.expr) -> bool:
    """True iff `node` is literally `sys.stderr` or a bare `stderr` name
    (e.g. `from sys import stderr`)."""
    try:
        source = ast.unparse(node)
    except Exception:
        return False
    return source in {"sys.stderr", "stderr"}


def _is_stdout_write_target(node: ast.expr) -> bool:
    """True iff `node` is literally `sys.stdout`, `sys.stdout.buffer`, or a
    bare `stdout` name (e.g. `from sys import stdout`) -- symmetric with
    `_is_stderr_target`'s bare `stderr` recognition."""
    try:
        source = ast.unparse(node)
    except Exception:
        return False
    return source in {"sys.stdout", "sys.stdout.buffer", "stdout"}


def _is_stdout_write_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id == "print":
        for keyword in node.keywords:
            if keyword.arg == "file":
                return not _is_stderr_target(keyword.value)
        return True  # bare print() defaults to stdout
    if isinstance(func, ast.Attribute) and func.attr in {"write", "writelines"}:
        return _is_stdout_write_target(func.value)
    return False


def _find_stdout_writers(root: Path, allowed: set[Path]) -> list[Path]:
    """Return every `.py` file under `root`, outside `allowed`, containing
    an AST `Call` node that writes to stdout (see module docstring)."""
    violators = []
    for path in sorted(root.rglob("*.py")):
        if path.resolve() in allowed:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise AssertionError(
                f"{path}: unreadable ({exc}); the AD-8 stdout-write guard "
                "cannot AST-scan this file"
            ) from exc
        except UnicodeDecodeError as exc:
            raise AssertionError(
                f"{path}: not valid UTF-8; the AD-8 stdout-write guard "
                "cannot AST-scan this file"
            ) from exc

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            raise AssertionError(
                f"{path}: invalid Python syntax; the AD-8 stdout-write "
                "guard cannot AST-scan this file"
            ) from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_stdout_write_call(node):
                violators.append(path)
                break
    return violators


def test_no_stdout_write_outside_the_allowlist():
    # Guard the guard: if the package layout ever moves, rglob over a stale
    # path would yield zero files and this test would pass vacuously forever.
    assert PKG_ROOT.is_dir(), (
        f"AD-8 guard is scanning nothing — package root moved? {PKG_ROOT}"
    )
    violators = _find_stdout_writers(PKG_ROOT, _allowed_paths(PKG_ROOT))
    assert not violators, (
        "AD-8: only cli.py and render.py may format/write a command result "
        f"to stdout; found a stdout-writing call in: {violators}"
    )


# --- Regression fixtures proving the detection logic itself, synthetic
# trees rather than the real package -- these assert the scanner's own
# behavior independent of what src/pyforge/mason/ currently contains. ------

def test_detection_fires_on_a_violation_and_permits_allowed_files(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "cli.py").write_text("print('hi')\n", encoding="utf-8")
    (root / "render.py").write_text("import sys\nsys.stdout.write('hi')\n", encoding="utf-8")
    (root / "recipe.py").write_text("print('uh oh')\n", encoding="utf-8")
    (root / "other.py").write_text(
        "import sys\nprint('also bad', file=sys.stdout)\n", encoding="utf-8",
    )
    (root / "buffered.py").write_text(
        "import sys\nsys.stdout.buffer.write(b'bytes')\n", encoding="utf-8",
    )
    (root / "fine.py").write_text(
        "import sys\nprint('fine', file=sys.stderr)\nsys.stderr.write('also fine')\n",
        encoding="utf-8",
    )
    nested = root / "nested"
    nested.mkdir()
    # Same bare filename as the allowed cli.py, different path -- must NOT
    # be wrongly exempted by a filename-only allowlist.
    (nested / "cli.py").write_text("print('shadow')\n", encoding="utf-8")

    violators = {p.resolve() for p in _find_stdout_writers(root, _allowed_paths(root))}

    assert (root / "recipe.py").resolve() in violators
    assert (root / "other.py").resolve() in violators
    assert (root / "buffered.py").resolve() in violators
    assert (nested / "cli.py").resolve() in violators
    assert (root / "cli.py").resolve() not in violators
    assert (root / "render.py").resolve() not in violators
    assert (root / "fine.py").resolve() not in violators


def test_detection_fires_on_a_bare_stdout_name_import(tmp_path):
    """`from sys import stdout` then a bare `stdout.write(...)` must be
    caught -- symmetric with the bare-`stderr`-name case already exempted
    for the fine-file above."""
    root = tmp_path / "mason"
    root.mkdir()
    (root / "shadowed.py").write_text(
        "from sys import stdout\nstdout.write('sneaky')\n", encoding="utf-8",
    )
    violators = {p.resolve() for p in _find_stdout_writers(root, _allowed_paths(root))}
    assert (root / "shadowed.py").resolve() in violators


def test_detection_fires_on_writelines(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "sneaky.py").write_text(
        "import sys\nsys.stdout.writelines(['a', 'b'])\n", encoding="utf-8",
    )
    violators = {p.resolve() for p in _find_stdout_writers(root, _allowed_paths(root))}
    assert (root / "sneaky.py").resolve() in violators


def test_non_utf8_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_bytes(b"\xff\xfe not valid utf-8 \x80\x81")

    with pytest.raises(AssertionError, match="not valid UTF-8"):
        _find_stdout_writers(root, _allowed_paths(root))


def test_invalid_syntax_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").write_text("def(:\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="invalid Python syntax"):
        _find_stdout_writers(root, _allowed_paths(root))


def test_unreadable_file_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    root = tmp_path / "mason"
    root.mkdir()
    (root / "broken.py").symlink_to(root / "does-not-exist.py")

    with pytest.raises(AssertionError, match="unreadable"):
        _find_stdout_writers(root, _allowed_paths(root))
