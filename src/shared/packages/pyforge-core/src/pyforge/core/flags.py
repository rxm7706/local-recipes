"""The fleet-wide CLI flag contract (steward Story 75.1 / spec-feature-flag-governance).

Every station CLI reads a boolean feature flag through this module and no other:
``pyforge.core`` held only the ``cutover_root`` string reader
(:mod:`pyforge.core.cutover_root`) before this, and ``django_pyforge.flags`` is
reachable only inside the host. This file is in ``cutover_root``'s shape (Story
44.12's precedent: a steward-authored CLI reader in ``pyforge-core``), co-governed
by ``spec-pyforge-core``.

**The names here are a fleet contract.** Every other station's flagged CLI story
reuses ``read_boolean``, ``FlagOff``, ``require`` and ``disabled_help`` and never
re-implements them. After Story 75.1 landed, the signature, the tree-resolution
order and the OFF/absent semantics change only additively (Story 76.1 makes
``read_boolean`` read the per-environment rendered tree and Story 76.3 routes its
evaluation through OpenFeature; neither changes what is stated here).

* **Tree resolution** is exactly :func:`pyforge.core.cutover_root.resolve_flags_path`
  -- reused, never copied: the explicit ``flags_path``, else ``PYFORGE_FLAGS_PATH``,
  else the nearest ``src/platform/config/flags.json`` walking up from the working
  directory.
* **OFF and absent semantics.** ``state: DISABLED`` reads False whatever else is set
  (the kill switch wins). A present key reads its ``defaultVariant``'s value when
  that value is a bool. A missing tree, an unreadable tree, a missing key or a
  non-bool value reads ``default``, with one named WARN on stderr naming the key
  and the reason. A new capability passes ``default=False`` so it never reads ON by
  accident; only a retrofit kill switch (``spec-feature-flag-governance`` CAP-7) may
  pass ``default=True``.
* **The Q3 helpers** (a flag-off verb stays listed in ``--help`` and refuses with its
  station's usage code): :class:`FlagOff`, :func:`require` and :func:`disabled_help`.
  They never choose an exit code -- each station's ``main()`` catches ``FlagOff`` and
  returns its own usage code (2 for steward), so no station's frozen exit-code
  domain changes and this module defines no exit code.

Stdlib-only apart from its sibling ``cutover_root``; no OpenFeature dependency, no
environment-variable provider and no station-specific logic belong here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pyforge.core import cutover_root

_DISABLED_STATE = "DISABLED"


class FlagOff(Exception):
    """A flag-gated capability was invoked while its flag reads OFF.

    Carries the flag ``key``; the message is ``flag <key> is off``. It is a plain
    ``Exception`` (never a ``SystemExit``): the station's ``main()`` decides the
    exit code.
    """

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"flag {key} is off")


def _warn(key: str, reason: str, default: bool) -> bool:
    """One named WARN on stderr for an absent/unreadable/malformed read; return ``default``."""
    print(
        f"pyforge.core.flags: WARN flag {key}: {reason}; reading default {default}",
        file=sys.stderr,
    )
    return default


def read_boolean(key: str, default: bool = False, *, flags_path: Path | str | None = None) -> bool:
    """Return the boolean value of flag ``key`` from the flagd tree.

    ``state: DISABLED`` reads False whatever else is set. Otherwise the key's
    ``defaultVariant`` value is returned when it is a bool; a missing tree, an
    unreadable or malformed tree, a missing key or a non-bool value returns
    ``default`` after one named WARN on stderr (never an exception).
    """
    resolved = cutover_root.resolve_flags_path(flags_path)
    if resolved is None:
        return _warn(key, "no flag tree (set PYFORGE_FLAGS_PATH or pass flags_path)", default)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # json.JSONDecodeError and UnicodeDecodeError are ValueErrors
        return _warn(key, f"unreadable flag tree {resolved}: {exc}", default)
    flags = payload.get("flags") if isinstance(payload, dict) else None
    if not isinstance(flags, dict):
        return _warn(key, f"malformed flag tree {resolved}: no 'flags' object", default)
    if key not in flags:
        return _warn(key, f"key missing from {resolved}", default)
    entry = flags[key]
    if not isinstance(entry, dict):
        return _warn(key, f"entry in {resolved} is not an object", default)
    state = entry.get("state")
    if isinstance(state, str) and state.upper() == _DISABLED_STATE:
        return False  # the kill switch wins over any variant and over ``default``
    variants = entry.get("variants")
    variant = entry.get("defaultVariant")
    if not isinstance(variants, dict) or not isinstance(variant, str) or variant not in variants:
        return _warn(key, f"entry in {resolved} lacks variants/defaultVariant", default)
    value = variants[variant]
    if not isinstance(value, bool):
        return _warn(key, f"variant {variant!r} in {resolved} is not a boolean", default)
    return value


def require(key: str, default: bool = False, *, flags_path: Path | str | None = None) -> None:
    """Raise :class:`FlagOff` when ``read_boolean`` reads ``key`` as False; else return."""
    if not read_boolean(key, default, flags_path=flags_path):
        raise FlagOff(key)


def disabled_help(help_text: str, key: str, default: bool = False, *, flags_path: Path | str | None = None) -> str:
    """Return ``help_text`` marked disabled when the flag is off, unchanged when on.

    The marker is `` [disabled: flag <key> is off]``, so a flag-off verb stays
    listed in ``--help`` (``spec-feature-flag-governance`` Q3).
    """
    if read_boolean(key, default, flags_path=flags_path):
        return help_text
    return f"{help_text} [disabled: flag {key} is off]"
