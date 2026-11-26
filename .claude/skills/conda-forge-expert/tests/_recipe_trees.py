"""One parse per recipe.yaml for the meta audits that read every recipe (mason Story 48.1).

Four audits each parsed all of ``recipes/**/recipe.yaml`` with PyYAML's pure-Python loader,
about 13 s a pass. ``recipe_tree`` parses a file once per process with the C safe loader
(the pure-Python one where libyaml is not built in) and keeps the result while the file's
size and modification time stand. ``test_recipe_yaml_parse_audit.py::test_all_recipe_yaml_parse``
still reads every recipe with ``yaml.safe_load`` and checks this parse against it, so the two
cannot drift apart unseen.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SAFE_LOADER: Any = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

_TREES: dict[str, tuple[int, int, Any, Exception | None]] = {}


def recipe_tree(path: Path) -> tuple[Any, Exception | None]:
    """``(tree, None)`` for a file that parses, ``(None, error)`` for one that does not."""
    stat = path.stat()
    key = str(path)
    held = _TREES.get(key)
    if held is not None and held[0] == stat.st_size and held[1] == stat.st_mtime_ns:
        return held[2], held[3]
    tree: Any = None
    error: Exception | None = None
    try:
        tree = yaml.load(path.read_text(encoding="utf-8"), Loader=SAFE_LOADER)  # noqa: S506 -- a safe loader
    except Exception as exc:  # noqa: BLE001 -- the caller decides what an unparseable file means
        error = exc
    _TREES[key] = (stat.st_size, stat.st_mtime_ns, tree, error)
    return tree, error
