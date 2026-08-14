"""Meta test -- Story 10.1 factory/platform import boundary.

Invokes the real ``lint-imports`` CLI (import-linter, provisioned via
``requirements/local.txt``) against this package's own ``pyproject.toml``
and asserts the ``forbidden`` contract barring ``pyforge`` imports is kept.
Mirrors pyforge-marshal's AD-3/AD-4 precedent (``src/shared/packages/
pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py``): makes the
factory/platform boundary a real CI gate, not just a convention.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _PACKAGE_ROOT / "pyproject.toml"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_lint_imports_passes_against_the_platform_host():
    if shutil.which("lint-imports") is None:
        pytest.fail(
            "lint-imports not on PATH -- install requirements/local.txt "
            "(provisions import-linter) before running this suite",
        )
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        ["lint-imports", "--config", str(_PYPROJECT), "--no-cache"],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=_PACKAGE_ROOT,
    )
    stdout = _strip_ansi(result.stdout)
    assert result.returncode == 0, (
        f"lint-imports failed (exit {result.returncode}):\n"
        f"stdout:\n{stdout}\nstderr:\n{_strip_ansi(result.stderr)}"
    )
    assert re.search(r"\b0\s+broken\b", stdout), (
        f"expected a '0 broken' summary in lint-imports output:\n{stdout}"
    )
