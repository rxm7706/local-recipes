#!/usr/bin/env python3
"""``pre-commit`` hook: no secret-shaped value enters a tracked NIC config (steward Story 118.9,
``spec-pyforge-steward`` CAP-178).

Scans each staged file under ``src/platform/deploy/nic/`` (the hook's ``files:`` pattern) with the
pattern table of ``steward keys audit --secrets`` -- ``_SECRET_PATTERNS`` in
``src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py``, read here from that module's
source with ``ast`` so the table is declared once. Standard library only: pre-commit stashes
unstaged changes while a hook runs, so a hook never starts pixi (see ``.pre-commit-config.yaml``).
An environment-variable name (``env: GITOPS_DEPLOY_KEY``) is not secret-shaped and passes.

A finding names the file, the line and the pattern, never the value.

    python scripts/nic_config_secret_scan.py src/platform/deploy/nic/my-nebari-hetzner.yaml

EXIT  0 clean · 1 a secret-shaped value (the commit is refused) · 2 could-not-run (the pattern
      table or a named file cannot be read)
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS_MODULE = ROOT / "src" / "shared" / "packages" / "pyforge-steward" / "src" / "pyforge" / "steward" / "keys.py"
TABLE_NAME = "_SECRET_PATTERNS"


def load_patterns(module: Path = KEYS_MODULE) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """``(name, compiled pattern)`` pairs from the ``_SECRET_PATTERNS = (("name", re.compile("...")), ...)``
    assignment in ``module``; raises ``ValueError`` when the table is absent or not that shape."""
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        if not (isinstance(target, ast.Name) and target.id == TABLE_NAME):
            continue
        value = node.value
        if not isinstance(value, ast.Tuple):
            break
        table: list[tuple[str, re.Pattern[str]]] = []
        for element in value.elts:
            if not (isinstance(element, ast.Tuple) and len(element.elts) == 2):
                raise ValueError(f"{TABLE_NAME} entry is not a (name, re.compile(...)) pair")
            name, call = element.elts
            if not (
                isinstance(name, ast.Constant)
                and isinstance(name.value, str)
                and isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "compile"
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "re"
            ):
                raise ValueError(f"{TABLE_NAME} entry is not a (name, re.compile(...)) pair")
            # Only the pattern is read here, so a flag or any other argument would be dropped
            # silently and this hook would scan with a different table than keys does.
            if call.keywords or len(call.args) != 1:
                raise ValueError(
                    f"{TABLE_NAME} entry {name.value!r}: re.compile takes the pattern alone here "
                    "(inline flags such as (?i), never a flags= or second argument)"
                )
            if not (isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)):
                raise ValueError(f"{TABLE_NAME} entry {name.value!r}: the pattern is not a string literal")
            table.append((name.value, re.compile(call.args[0].value)))
        if table:
            return tuple(table)
        break
    raise ValueError(f"{module}: no {TABLE_NAME} table")


def scan(path: Path, patterns: tuple[tuple[str, re.Pattern[str]], ...]) -> list[str]:
    text = path.read_bytes().decode("utf-8", errors="replace").replace("\x00", "")
    return [
        f"{path}:{lineno} matches the {name!r} plaintext-secret pattern"
        for lineno, line in enumerate(text.split("\n"), start=1)
        for name, pattern in patterns
        if pattern.search(line)
    ]


def main(argv: list[str] | None = None) -> int:
    paths = [Path(arg) for arg in (sys.argv[1:] if argv is None else argv)]
    try:
        patterns = load_patterns(KEYS_MODULE)
        findings = [finding for path in paths for finding in scan(path, patterns)]
    except (OSError, SyntaxError, ValueError, re.error) as exc:
        print(f"[nic-config-secret-scan] could not run -- {exc}")
        return 2
    for finding in findings:
        print(f"[nic-config-secret-scan] refused -- {finding}")
    if findings:
        print("[nic-config-secret-scan] a NIC config names env-var names only; secrets stay in .env through keys")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
