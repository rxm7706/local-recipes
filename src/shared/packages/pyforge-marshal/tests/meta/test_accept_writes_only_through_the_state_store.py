"""Meta test — ``accept.py`` writes state only through ``write_state`` (Story 97.1, AC4).

AST-scan ``pyforge.marshal.seed.verbs.accept`` and fail on any write primitive
other than a call to ``write_state`` (the one sanctioned path to
``.marshal/seed-state.yml``).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
_ACCEPT_MODULE = Path(_PACKAGE_FILE).resolve().parent / "seed" / "verbs" / "accept.py"

_WRITE_MODES = frozenset("wax+")
_FORBIDDEN_ATTR_WRITES = frozenset({"write_text", "write_bytes"})
_FORBIDDEN_YAML_DUMP = frozenset({"dump", "safe_dump", "dump_all"})


def _parse() -> ast.Module:
    return ast.parse(_ACCEPT_MODULE.read_text(encoding="utf-8"), filename=str(_ACCEPT_MODULE))


def _is_write_open_mode(mode: str | None) -> bool:
    if not mode:
        return False
    return any(ch in mode for ch in _WRITE_MODES)


def _violations(tree: ast.Module) -> list[str]:
    violations: list[str] = []
    yaml_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "yaml" or alias.name.startswith("yaml."):
                    yaml_aliases.add(alias.asname or "yaml")
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "yaml":
            bound = node.module.split(".")[0]
            for alias in node.names:
                yaml_aliases.add(alias.asname or alias.name)
                if alias.name in _FORBIDDEN_YAML_DUMP:
                    violations.append(f"yaml dump at line {node.lineno}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "open" and node.args:
                mode = None
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value if isinstance(node.args[1].value, str) else None
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        mode = kw.value.value
                if _is_write_open_mode(mode):
                    violations.append(f"open(..., write mode) at line {node.lineno}")
            elif isinstance(func, ast.Attribute):
                if func.attr in _FORBIDDEN_ATTR_WRITES:
                    violations.append(f".{func.attr} at line {node.lineno}")
                if func.attr in _FORBIDDEN_YAML_DUMP and (
                    (isinstance(func.value, ast.Name) and func.value.id in yaml_aliases)
                    or (isinstance(func.value, ast.Name) and func.value.id == "yaml")
                ):
                    violations.append(f"yaml.{func.attr} at line {node.lineno}")
                if func.attr == "write" and isinstance(func.value, ast.Name) and func.value.id == "fs":
                    violations.append(f"fs.write at line {node.lineno} (use write_state only)")
                if func.attr in {"replace_span", "atomic_write_bytes", "atomic_write_text"}:
                    violations.append(f"forbidden fs.{func.attr} at line {node.lineno}")
    return violations


def test_accept_module_uses_no_forbidden_write_primitives():
    tree = _parse()
    found = _violations(tree)
    assert not found, "accept.py must write only via write_state:\n" + "\n".join(found)


def test_accept_module_calls_write_state():
    tree = _parse()
    names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "write_state"
    }
    assert names == {"write_state"}, "accept.py must call write_state for persistence"
