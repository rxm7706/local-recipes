"""One parse per recipe.yaml for the meta audits that read every recipe (mason Story 48.1).

Four audits each parsed all of ``recipes/**/recipe.yaml`` with PyYAML's pure-Python loader,
about 13 s a pass. ``recipe_tree`` parses a file once per process with the C safe loader
(the pure-Python one where libyaml is not built in) and keeps the result while the file's
bytes stand (a hash of them, read on every call). ``test_recipe_yaml_parse_audit.py::test_all_recipe_yaml_parse``
still reads every recipe with ``yaml.safe_load`` and checks this parse against it, so the two
cannot drift apart unseen.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

SAFE_LOADER: Any = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

_TREES: dict[str, tuple[bytes, Any, Exception | None]] = {}


def recipe_tree(path: Path) -> tuple[Any, Exception | None]:
    """``(tree, None)`` for a file that parses, ``(None, error)`` for one that does not."""
    raw = path.read_bytes()
    digest = hashlib.blake2b(raw, digest_size=16).digest()
    key = str(path)
    held = _TREES.get(key)
    if held is not None and held[0] == digest:
        return held[1], held[2]
    tree: Any = None
    error: Exception | None = None
    try:
        tree = yaml.load(raw.decode("utf-8"), Loader=SAFE_LOADER)  # noqa: S506 -- a safe loader
    except Exception as exc:  # noqa: BLE001 -- the caller decides what an unparseable file means
        error = exc
    _TREES[key] = (digest, tree, error)
    return tree, error
