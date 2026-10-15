"""Pages deploy duty: tree hash, build.json, and deploy-when-changed (Story 102.2 / CAP-168)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

PAGES_DUTY_FLAG = "pyforge.steward.pages_duty"

# Relative paths excluded from tree_hash (never hashed silently — each entry documents why).
# Herald M3 footer paths join this list when that footer ships (design-thinking P-A).
HASH_EXCLUDE_RELATIVE: frozenset[str] = frozenset(
    {
        "build.json",  # written after hash; must not feed back into itself
    }
)


def tree_hash(root: Path, *, exclude: Iterable[str] | None = None) -> str:
    """SHA-256 over sorted relative paths and file bytes under ``root``."""
    if not root.is_dir():
        msg = f"tree_hash root is not a directory: {root}"
        raise ValueError(msg)
    excluded = HASH_EXCLUDE_RELATIVE if exclude is None else frozenset(exclude)
    digest = hashlib.sha256()
    paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excluded or any(rel == e or rel.startswith(f"{e}/") for e in excluded):
            continue
        paths.append(rel)
    for rel in paths:
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / rel).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_json(
    tree_hash_value: str,
    built_from: str,
    run_id: str,
    built_at: str,
) -> dict[str, Any]:
    """The live ``build.json`` document shape."""
    return {
        "tree_hash": tree_hash_value,
        "built_from": built_from,
        "run_id": run_id,
        "built_at": built_at,
    }


def parse_live_tree_hash(live_text: str | None) -> str | None:
    """Return ``tree_hash`` from live JSON text, or ``None`` when absent/unusable."""
    if live_text is None or not live_text.strip():
        return None
    try:
        payload = json.loads(live_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("tree_hash")
    if not isinstance(value, str) or not value:
        return None
    return value


def decide_deploy(local_hash: str, live_text: str | None, *, flag_on: bool) -> bool:
    """Whether the built tree changed enough to deploy (``True`` = deploy)."""
    if not flag_on:
        return True
    live_hash = parse_live_tree_hash(live_text)
    if live_hash is None:
        return True
    return local_hash != live_hash
