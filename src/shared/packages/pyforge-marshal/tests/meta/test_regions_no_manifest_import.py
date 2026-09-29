"""Meta test -- the Story 8.4 review-finding import-linter contract:
``pyforge.marshal.seed.regions`` never imports ``...seed.model.manifest``
(``seed/model/manifest.py`` already imports FROM ``regions/markers.py``, so
the reverse edge would be a package import cycle). Mirrors
``test_ad3_ad4_import_linter.py``'s own approach: parse ``pyproject.toml``
for the NEW contract's declared shape and invoke the real ``lint-imports``
CLI to prove it (and its three siblings) hold against the installed
package. A lower-stakes layering concern than AD-9's security-sensitive
control-channel isolation, so this file skips that file's own
dynamic-import evasion scan (``importlib.import_module``/``__import__``) --
import-linter's static check is sufficient here, matching AD-3/AD-4's own
(lighter) precedent rather than AD-9's.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _PACKAGE_ROOT / "pyproject.toml"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _contracts() -> list[dict]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    return data["tool"]["importlinter"]["contracts"]


def _contract_forbidding_manifest() -> dict:
    # .get: a contract of another import-linter type has no
    # forbidden_modules key -- skip it rather than KeyError-ing and masking
    # the real assertion (mirrors test_ad3_ad4_import_linter.py's own
    # `_contract_forbidding` helper).
    for contract in _contracts():
        if "pyforge.marshal.seed.model.manifest" in contract.get("forbidden_modules", []):
            return contract
    raise AssertionError("no contract forbids pyforge.marshal.seed.model.manifest")


def test_regions_no_manifest_import_contract_shape():
    contract = _contract_forbidding_manifest()
    assert contract["type"] == "forbidden"
    assert contract["source_modules"] == ["pyforge.marshal.seed.regions"]
    assert contract["forbidden_modules"] == ["pyforge.marshal.seed.model.manifest"]


def test_lint_imports_passes_against_the_installed_package():
    if shutil.which("lint-imports") is None:
        pytest.fail(
            "lint-imports not on PATH -- run this suite via the env that "
            "provisions import-linter: "
            "`pixi run -e pyforge-marshal pyforge-marshal-test`"
        )
    result = subprocess.run(
        ["lint-imports", "--config", str(_PYPROJECT), "--no-cache"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    stdout = _strip_ansi(result.stdout)
    assert result.returncode == 0, (
        f"lint-imports failed (exit {result.returncode}):\nstdout:\n{stdout}\nstderr:\n{_strip_ansi(result.stderr)}"
    )
    assert re.search(r"\b0\s+broken\b", stdout), f"expected a '0 broken' summary in lint-imports output:\n{stdout}"
