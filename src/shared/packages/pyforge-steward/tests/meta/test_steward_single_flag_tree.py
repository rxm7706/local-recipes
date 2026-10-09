"""Story 76.3 — steward reads flags only from the one flagd tree (canopy:AD-11)."""

from __future__ import annotations

import ast
from pathlib import Path

STEWARD_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "steward"


def _steward_modules() -> list[Path]:
    return sorted(STEWARD_SRC.rglob("*.py"))


def test_no_steward_module_reads_steward_flags_json_or_flags_env() -> None:
    """A second tree (.steward/flags.json or FLAGS_* env vars) is review-blocking."""
    offenders: list[str] = []
    for path in _steward_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if ".steward/flags.json" in node.value:
                    offenders.append(f"{path.relative_to(STEWARD_SRC.parents[1])}:{node.lineno} string")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "get" and isinstance(node.func.value, ast.Attribute):
                    if (
                        isinstance(node.func.value.value, ast.Name)
                        and node.func.value.value.id == "os"
                        and node.func.value.attr == "environ"
                    ):
                        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                            if node.args[0].value.startswith("FLAGS_"):
                                offenders.append(
                                    f"{path.relative_to(STEWARD_SRC.parents[1])}:{node.lineno} os.environ.get"
                                )
    assert not offenders, "steward must not read a second flag tree:\n" + "\n".join(offenders)
