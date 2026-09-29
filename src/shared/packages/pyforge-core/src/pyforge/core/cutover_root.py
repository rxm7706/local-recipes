"""Read ``pyforge.cutover_root`` from the flagd tree (Story 44.12 / fnd:CAP-8).

CLIs use this reader. The host may also call it; OpenFeature string
evaluation of the same key must agree with ``read_cutover_root``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CUTOVER_FLAG = "pyforge.cutover_root"
CUTOVER_VARIANTS = ("local-recipes", "foundry")
DEFAULT_CUTOVER_ROOT = "local-recipes"
ENV_FLAGS_PATH = "PYFORGE_FLAGS_PATH"
LOCAL_DEV_RELATIVE = Path("src/platform/config/flags.json")


class CutoverRootError(ValueError):
    """Named fail: missing tree, unknown variant, or malformed flag."""


def resolve_flags_path(explicit: Path | str | None = None) -> Path | None:
    if explicit is not None:
        path = Path(explicit)
        return path if path.is_file() else None
    raw = os.environ.get(ENV_FLAGS_PATH)
    if raw:
        path = Path(raw)
        if path.is_file():
            return path
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        path = candidate / LOCAL_DEV_RELATIVE
        if path.is_file():
            return path
    return None


def read_cutover_root(path: Path | str | None = None) -> str:
    """Return ``local-recipes`` or ``foundry`` from the flag's defaultVariant."""
    resolved = resolve_flags_path(path)
    if resolved is None:
        raise CutoverRootError("no flag tree: set PYFORGE_FLAGS_PATH or pass a flags.json path")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CutoverRootError(f"unreadable flag tree {resolved}: {exc}") from exc
    flags = payload.get("flags") if isinstance(payload, dict) else None
    if not isinstance(flags, dict) or CUTOVER_FLAG not in flags:
        raise CutoverRootError(f"{CUTOVER_FLAG} missing from {resolved}")
    entry = flags[CUTOVER_FLAG]
    if not isinstance(entry, dict):
        raise CutoverRootError(f"{CUTOVER_FLAG} is not an object")
    variants = entry.get("variants")
    default = entry.get("defaultVariant")
    if not isinstance(variants, dict) or not isinstance(default, str):
        raise CutoverRootError(f"{CUTOVER_FLAG} lacks variants/defaultVariant")
    if default not in CUTOVER_VARIANTS or default not in variants:
        raise CutoverRootError(f"unknown cutover_root variant {default!r}")
    value = variants[default]
    if value not in CUTOVER_VARIANTS:
        raise CutoverRootError(f"cutover_root value {value!r} is not a known root")
    return str(value)
