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


def _composed_for_environment(resolved: Path, payload: object) -> object:
    """The tree as ``PYFORGE_ENVIRONMENT`` renders it (Story 76.1): the sibling ``flag-overlays.json``
    composed in, so this reader agrees with the chart, the host provider and ``read_boolean``.
    A bad environment or overlay is a named :class:`CutoverRootError`."""
    from pyforge.core import flags as core_flags  # noqa: PLC0415 -- flags imports this module at load

    try:
        environment = core_flags.current_environment()
        overlays = core_flags.overlays_path_for(resolved)
        if overlays is None or not isinstance(payload, dict):
            return payload
        return core_flags.compose(payload, core_flags.load_overlays(overlays), environment)
    except core_flags.FlagConfigError as exc:
        raise CutoverRootError(str(exc)) from exc


def read_cutover_root(path: Path | str | None = None) -> str:
    """Return ``local-recipes`` or ``foundry`` from the flag's defaultVariant
    (as the current environment renders the tree)."""
    resolved = resolve_flags_path(path)
    if resolved is None:
        raise CutoverRootError("no flag tree: set PYFORGE_FLAGS_PATH or pass a flags.json path")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CutoverRootError(f"unreadable flag tree {resolved}: {exc}") from exc
    payload = _composed_for_environment(resolved, payload)
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
