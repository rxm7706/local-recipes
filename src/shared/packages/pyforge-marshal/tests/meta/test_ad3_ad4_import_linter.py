"""Meta test -- AD-3/AD-4 import-linter contracts (Story 1.1).

Invokes the real ``lint-imports`` CLI (import-linter, provisioned in the
root ``pixi.toml``'s ``[feature.pyforge-marshal.dependencies]``) against
this package's own ``pyproject.toml`` and asserts both contracts are KEPT
against the installed package. Separately parses the same
``pyproject.toml`` to assert the two contracts' declared
``source_modules``/``forbidden_modules`` are exactly what AD-3/AD-4
require -- so a future edit that silently narrows or widens either
contract's scope is caught even if the tree at the time still happens to
pass the live check.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover -- this package requires-python >=3.12
    import tomli as tomllib

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _PACKAGE_ROOT / "pyproject.toml"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _contracts() -> list[dict]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    return data["tool"]["importlinter"]["contracts"]


def _contract_forbidding(forbidden_module: str) -> dict:
    for contract in _contracts():
        if forbidden_module in contract["forbidden_modules"]:
            return contract
    raise AssertionError(f"no contract forbids {forbidden_module!r}")


def test_pyproject_declares_exactly_two_contracts():
    assert len(_contracts()) == 2


def test_ad4_core_purity_contract_shape():
    contract = _contract_forbidding("subprocess")
    assert contract["type"] == "forbidden"
    assert contract["source_modules"] == ["pyforge.marshal.core"]
    assert set(contract["forbidden_modules"]) == {
        "subprocess",
        "os",
        "time",
        "pyforge.marshal.adapters",
    }


def test_ad3_harness_seam_contract_shape():
    contract = _contract_forbidding("bmad_loop")
    assert contract["type"] == "forbidden"
    assert set(contract["source_modules"]) == {
        "pyforge.marshal.cli",
        "pyforge.marshal.core",
        "pyforge.marshal.ports",
        "pyforge.marshal.supervisor",
    }
    assert contract["forbidden_modules"] == ["bmad_loop"]
    # AD-3's own documented scope gap (architecture.md Design Notes): the
    # whole `adapters` package is deliberately excluded from source_modules
    # -- including it would also forbid harness_bmadloop.py, the one module
    # this contract must allow to import bmad_loop.
    assert "pyforge.marshal.adapters" not in contract["source_modules"]


def test_lint_imports_passes_against_the_installed_package():
    result = subprocess.run(
        ["lint-imports", "--config", str(_PYPROJECT), "--no-cache"],
        capture_output=True,
        text=True,
    )
    stdout = _strip_ansi(result.stdout)
    assert result.returncode == 0, (
        f"lint-imports failed (exit {result.returncode}):\n"
        f"stdout:\n{stdout}\nstderr:\n{_strip_ansi(result.stderr)}"
    )
    # A loose regex, not an exact-substring match on the whole summary line:
    # a future import-linter release reformatting its report (spacing,
    # wording) should not break this test over something unrelated to the
    # contracts themselves. The "2 kept" contract COUNT is separately
    # enforced by test_pyproject_declares_exactly_two_contracts (which reads
    # the config, not lint-imports' stdout) -- this only needs to confirm
    # nothing broke.
    assert re.search(r"\b0\s+broken\b", stdout), (
        f"expected a '0 broken' summary in lint-imports output:\n{stdout}"
    )
