"""Read ``pyforge.cutover_root`` from the flagd tree (Story 44.12 / fnd:CAP-8).

CLIs use this reader. The host may also call it; OpenFeature string
evaluation of the same key must agree with ``read_cutover_root``.

``root_of_record`` answers the root of record, that root's forge repository
slug and where the answer came from; ``forge_slug_for`` maps a root to its
slug with no I/O (Story 117.2, spec-pyforge-core CAP-13). ``FORGE_SLUGS`` is
the one home of the slug table: a constant, because the leaf reads no
repository file. Kept out of this seam: whether a caller is the writer (the
caller compares its own root name), the clone URL (the caller composes
``https://github.com/<slug>.git``) and the station-packages directory.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

CUTOVER_FLAG = "pyforge.cutover_root"
CUTOVER_VARIANTS = ("local-recipes", "foundry")
DEFAULT_CUTOVER_ROOT = "local-recipes"
ENV_FLAGS_PATH = "PYFORGE_FLAGS_PATH"
LOCAL_DEV_RELATIVE = Path("src/platform/config/flags.json")

FORGE_SLUGS: Mapping[str, str] = MappingProxyType(
    {
        "local-recipes": "rxm7706/local-recipes",
        "foundry": "rxm7706/python-foundry",
    }
)
"""Each root of record's forge repository slug (``owner/name``), read-only."""


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


@dataclass(frozen=True)
class RootOfRecord:
    """The root of record, its forge repository slug, and the answer's source
    (``flag-tree`` when a tree was read, ``default`` when none was in reach)."""

    root: str
    forge_slug: str
    source: str


def forge_slug_for(root: str) -> str:
    """The forge repository slug of ``root``; pure, no I/O."""
    if root not in CUTOVER_VARIANTS:
        raise CutoverRootError(f"unknown root {root!r}: expected one of {', '.join(CUTOVER_VARIANTS)}")
    return FORGE_SLUGS[root]


def root_of_record(path: Path | str | None = None) -> RootOfRecord:
    """The root of record as the current environment renders the flag tree.

    An explicit ``path`` is read with :func:`read_cutover_root`, so one that is
    not a file is a :class:`CutoverRootError`, never the default. With no path,
    :func:`resolve_flags_path` finds the tree (``PYFORGE_FLAGS_PATH``, then the
    walk-up) and the reader reads it, so every :class:`CutoverRootError` holds;
    only when no tree is in reach is the answer ``DEFAULT_CUTOVER_ROOT`` with
    source ``default``.
    """
    if path is None:
        resolved = resolve_flags_path()
        if resolved is None:
            return RootOfRecord(
                root=DEFAULT_CUTOVER_ROOT,
                forge_slug=forge_slug_for(DEFAULT_CUTOVER_ROOT),
                source="default",
            )
        path = resolved
    root = read_cutover_root(path)
    return RootOfRecord(root=root, forge_slug=forge_slug_for(root), source="flag-tree")
