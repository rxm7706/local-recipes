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
                f"{path}: unreadable ({exc}); the AD-2 subprocess-import "
                "guard cannot AST-scan this file"
            ) from exc
        except UnicodeDecodeError as exc:
            # Fail loudly rather than silently skip (review finding #5): a
            # guard that cannot read a file cannot prove that file is clean,
            # and a raw UnicodeDecodeError traceback is not an actionable
            # test failure. This is the simplest correct behavior — a
            # genuinely non-UTF-8 `.py` file under this tree is itself a
            # bug worth surfacing, not a case to special-case around.
            raise AssertionError(
                f"{path}: not valid UTF-8; the AD-2 subprocess-import guard "
                "cannot AST-scan this file"
            ) from exc

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            # Same rationale as the UnicodeDecodeError handling above: a file
            # the scanner cannot parse is a file it cannot prove clean, and a
            # raw SyntaxError traceback is not an actionable test failure.
            raise AssertionError(
                f"{path}: invalid Python syntax; the AD-2 subprocess-import "
                "guard cannot AST-scan this file"
            ) from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name == "subprocess" for alias in node.names
            ):
                violators.append(path)
                break
            if isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                violators.append(path)
                break
    return violators


def test_no_subprocess_import_outside_the_allowlist():
    # Guard the guard: if the package layout ever moves, rglob over a stale
    # path would yield zero files and this test would pass vacuously forever.
    assert PKG_ROOT.is_dir(), (
        f"AD-2 guard is scanning nothing — package root moved? {PKG_ROOT}"
    )
    violators = _find_subprocess_importers(PKG_ROOT, _allowed_paths(PKG_ROOT))
    assert not violators, (
        "AD-2: only cli.py, cfe.py, and engines/*.py may `import subprocess`; "
        f"found it in: {violators}"
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
