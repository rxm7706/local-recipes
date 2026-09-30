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

* **The environment** (Story 76.1, ``canopy:AD-11`` amended 2026-09-28). ``PYFORGE_ENVIRONMENT``
  names one of ``dev`` / ``staging`` / ``production`` (``dev`` when unset, for local
  development); anything else is a named :class:`UnknownEnvironmentError`, never a read that
  falls back to ``default``. A ``flag-overlays.json`` document beside the resolved tree is
  value-only -- per environment, a key the tree defines mapped to one of that flag's variant
  names -- and :func:`compose` returns the tree with each overlaid ``defaultVariant`` replaced
  for the environment (a ``DISABLED`` flag stays off in every environment). :func:`render`
  returns that composed tree as bytes: the chart's ConfigMap and the host's FILE provider mount
  or read the same rendering ``read_boolean`` reads here. No sibling document (the in-cluster
  mount already holds the rendered tree) reads the tree as it is. An invalid environment or
  overlay raises a :class:`FlagConfigError` subclass out of ``read_boolean`` (a WARN plus
  ``default`` could read ON for a retrofit ``default=True``).

* **The clock** (Story 76.2, ``spec-feature-flag-governance`` CAP-5 and Q4). Every flag in the
  tree carries flagd flag-level ``metadata`` of five string fields (:data:`METADATA_FIELDS`):
  ``owner`` (the station token), ``story`` (the ledger key that introduced the flag), ``created``
  (``YYYY-MM-DD``), ``on_everywhere`` (``YYYY-MM-DD``, the day the flag first read ON in every
  environment's rendering, else ``""``) and ``cleanup_by`` (``on_everywhere`` plus
  :data:`CLEANUP_DAYS` days, else ``""``). A flag with no boolean ON variant never runs a clock.
  :func:`check_metadata` refuses each failure with a named :class:`FlagMetadataError` subclass
  naming the flag and the field, and :func:`compose` runs it, so every path that composes the
  tree (``read_boolean``, :func:`render`, ``read_cutover_root``) refuses a tree that breaks it.
  A tree with no ``flag-overlays.json`` beside it is not composed and is read as it is.

Stdlib-only apart from its sibling ``cutover_root``; no OpenFeature dependency, no
environment-variable provider and no station-specific logic belong here.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
from collections.abc import Mapping
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from pyforge.core import cutover_root

_DISABLED_STATE = "DISABLED"

ENV_ENVIRONMENT = "PYFORGE_ENVIRONMENT"
ENVIRONMENTS = ("dev", "staging", "production")
DEFAULT_ENVIRONMENT = "dev"
OVERLAYS_FILE_NAME = "flag-overlays.json"

METADATA_FIELDS = ("owner", "story", "created", "on_everywhere", "cleanup_by")
CLEANUP_DAYS = 90  # spec-feature-flag-governance Q4: a flag may live 90 days after it is ON everywhere
_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class FlagConfigError(ValueError):
    """The environment, the overlay document or the tree cannot be composed.

    Raised, never downgraded to a WARN plus ``default``: a fallback could read ON. Each
    subclass below names one refusal and its message names the offending entry.
    """


class UnknownEnvironmentError(FlagConfigError):
    """An environment outside ``dev`` / ``staging`` / ``production``."""


class OverlayDocumentError(FlagConfigError):
    """The overlay document is unreadable or not shaped ``{environment: {key: variant}}``."""


class OverlayUnknownKeyError(FlagConfigError):
    """An overlay key the tree does not define."""


class OverlayUnknownVariantError(FlagConfigError):
    """An overlay variant the flag does not define."""


class OverlayNotAVariantError(FlagConfigError):
    """An overlay entry that is not a variant name (an object would define a second tree)."""


class FlagTreeError(FlagConfigError):
    """``render`` found no tree, or one it cannot read."""


class FlagMetadataError(FlagConfigError):
    """A flag's ``metadata`` breaks the clock contract (Story 76.2); each subclass names one refusal."""


class FlagMetadataMissingError(FlagMetadataError):
    """A flag with no ``metadata`` object, a missing field, or an empty ``owner`` / ``story``."""


class FlagMetadataNotAStringError(FlagMetadataError):
    """A metadata field that is not a string (flagd accepts primitives; the contract is strings)."""


class FlagMetadataDateError(FlagMetadataError):
    """A date field that is not a real ``YYYY-MM-DD`` date (``created`` must be one; the others may be ``""``)."""


class FlagClockMismatchError(FlagMetadataError):
    """``on_everywhere`` disagrees with what the environments render: set where one is not ON, or empty where all are."""


class FlagCleanupDateError(FlagMetadataError):
    """``cleanup_by`` is not ``on_everywhere`` plus :data:`CLEANUP_DAYS` days (or not empty where ``on_everywhere`` is)."""


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


def check_environment(name: str, *, source: str = "environment") -> str:
    """Return ``name`` when it is one of :data:`ENVIRONMENTS`, else raise :class:`UnknownEnvironmentError`."""
    if name not in ENVIRONMENTS:
        raise UnknownEnvironmentError(f"{source} {name!r} is not one of {', '.join(ENVIRONMENTS)}")
    return name


def current_environment(environ: Mapping[str, str] | None = None) -> str:
    """The environment from ``PYFORGE_ENVIRONMENT`` (``dev`` when unset); an unknown value raises."""
    raw = (os.environ if environ is None else environ).get(ENV_ENVIRONMENT)
    if raw is None:
        return DEFAULT_ENVIRONMENT
    return check_environment(raw, source=ENV_ENVIRONMENT)


def overlays_path_for(tree_path: Path | str) -> Path | None:
    """The ``flag-overlays.json`` beside ``tree_path``, or None when there is no such file."""
    candidate = Path(tree_path).with_name(OVERLAYS_FILE_NAME)
    return candidate if candidate.is_file() else None


def load_overlays(path: Path | str) -> dict[str, Any]:
    """Read the overlay document at ``path``; raises :class:`OverlayDocumentError` when it is unusable."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # json.JSONDecodeError and UnicodeDecodeError are ValueErrors
        raise OverlayDocumentError(f"unreadable overlay document {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise OverlayDocumentError(f"overlay document {path} is not an object keyed by environment")
    return payload


def _is_disabled(entry: object) -> bool:
    state = entry.get("state") if isinstance(entry, dict) else None
    return isinstance(state, str) and state.upper() == _DISABLED_STATE


def _validate_overlays(flags: Mapping[str, Any], overlays: Mapping[str, Any]) -> None:
    """Every entry of every environment, whichever one is being rendered: a typo never waits for its turn."""
    for name, entries in overlays.items():
        if name not in ENVIRONMENTS:
            raise UnknownEnvironmentError(f"overlay environment {name!r} is not one of {', '.join(ENVIRONMENTS)}")
        if not isinstance(entries, dict):
            raise OverlayDocumentError(f"overlay {name} is not an object mapping keys to variant names")
        for key, variant in entries.items():
            where = f"overlay {name}.{key}"
            if key not in flags:
                raise OverlayUnknownKeyError(f"{where} names a key the tree lacks")
            if not isinstance(variant, str):
                what = "an object" if isinstance(variant, dict) else type(variant).__name__
                raise OverlayNotAVariantError(
                    f"{where} is {what}, not a variant name (an overlay holds values only; "
                    "a definition would be a second tree)"
                )
            entry = flags[key]
            variants = entry.get("variants") if isinstance(entry, dict) else None
            if not isinstance(variants, dict) or variant not in variants:
                raise OverlayUnknownVariantError(f"{where} names variant {variant!r}, which the flag lacks")


def _rendered_variant(key: str, entry: Mapping[str, Any], overlays: Mapping[str, Any], environment: str) -> object:
    """The variant ``environment`` reads for ``key``: the overlay's, else the tree's ``defaultVariant``."""
    named = overlays.get(environment)
    if isinstance(named, dict) and key in named:
        return named[key]
    return entry.get("defaultVariant")


def _renders_on(key: str, entry: object, overlays: Mapping[str, Any], environment: str) -> bool:
    """True when ``environment`` reads ``key`` as boolean ON (a ``DISABLED`` flag and a non-boolean one never do)."""
    if not isinstance(entry, dict) or _is_disabled(entry):
        return False
    variant = _rendered_variant(key, entry, overlays, environment)
    variants = entry.get("variants")
    return isinstance(variant, str) and isinstance(variants, dict) and variants.get(variant) is True


def _metadata_date(key: str, field: str, value: str, *, allow_empty: bool) -> date | None:
    """``value`` as a date; None for an allowed ``""``; a :class:`FlagMetadataDateError` for anything else."""
    if value == "" and allow_empty:
        return None
    if _DATE_PATTERN.fullmatch(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    empty = ' (or "")' if allow_empty else ""
    raise FlagMetadataDateError(f"flag {key} metadata.{field} {value!r} is not a YYYY-MM-DD date{empty}")


def check_metadata(flags: Mapping[str, Any], overlays: Mapping[str, Any] | None = None) -> None:
    """Refuse the first flag whose ``metadata`` breaks the clock contract (Story 76.2); return None when all hold.

    Each flag needs the five :data:`METADATA_FIELDS` as strings: ``owner`` and ``story`` non-empty,
    ``created`` a real ``YYYY-MM-DD`` date, ``on_everywhere`` and ``cleanup_by`` a date or ``""``.
    ``on_everywhere`` is set exactly when every environment of :data:`ENVIRONMENTS` renders the flag
    ON (the tree's ``defaultVariant`` with ``overlays`` applied; a ``DISABLED`` or non-boolean flag
    never does, so its clock stays ``""``), and ``cleanup_by`` is ``on_everywhere`` plus
    :data:`CLEANUP_DAYS` days, else ``""``. A flag killed with ``state: DISABLED`` reads OFF in every
    environment, so a kill switch clears its clock in the same edit. Each refusal is a
    :class:`FlagMetadataError` subclass whose message names the flag and the field; ``flags`` is
    not modified.
    """
    overlays = overlays or {}
    for key, entry in flags.items():
        metadata = entry.get("metadata") if isinstance(entry, dict) else None
        if not isinstance(metadata, dict):
            raise FlagMetadataMissingError(f"flag {key} has no metadata object (needs {', '.join(METADATA_FIELDS)})")
        values: dict[str, str] = {}
        for field in METADATA_FIELDS:
            if field not in metadata:
                raise FlagMetadataMissingError(f"flag {key} metadata.{field} is missing")
            value = metadata[field]
            if not isinstance(value, str):
                raise FlagMetadataNotAStringError(
                    f"flag {key} metadata.{field} is {type(value).__name__}, not a string"
                )
            values[field] = value
        for field in ("owner", "story"):
            if not values[field].strip():
                raise FlagMetadataMissingError(f"flag {key} metadata.{field} is empty")
        _metadata_date(key, "created", values["created"], allow_empty=False)
        on_everywhere = _metadata_date(key, "on_everywhere", values["on_everywhere"], allow_empty=True)
        cleanup_by = _metadata_date(key, "cleanup_by", values["cleanup_by"], allow_empty=True)

        not_on = [name for name in ENVIRONMENTS if not _renders_on(key, entry, overlays, name)]
        if on_everywhere is not None and not_on:
            raise FlagClockMismatchError(
                f"flag {key} metadata.on_everywhere is {values['on_everywhere']!r} but it does not "
                f"render ON in {', '.join(not_on)} (it stays '' until every environment does)"
            )
        if on_everywhere is None and not not_on:
            raise FlagClockMismatchError(
                f"flag {key} metadata.on_everywhere is '' but every environment renders it ON "
                "(record the day it first did)"
            )
        try:
            expected = on_everywhere + timedelta(days=CLEANUP_DAYS) if on_everywhere is not None else None
        except OverflowError as exc:  # 9999-12-31 + 90 days
            raise FlagMetadataDateError(
                f"flag {key} metadata.on_everywhere {values['on_everywhere']!r} + {CLEANUP_DAYS} days is not a date"
            ) from exc
        if cleanup_by != expected:
            expected_text = expected.isoformat() if expected is not None else ""
            raise FlagCleanupDateError(
                f"flag {key} metadata.cleanup_by is {values['cleanup_by']!r} but on_everywhere "
                f"{values['on_everywhere']!r} + {CLEANUP_DAYS} days is {expected_text!r}"
            )


def compose(tree: Mapping[str, Any], overlays: Mapping[str, Any], environment: str) -> dict[str, Any]:
    """The tree with each ``defaultVariant`` the overlay names for ``environment`` replaced.

    Every entry of the whole overlay document is validated first (any environment), each a named
    :class:`FlagConfigError`; then :func:`check_metadata` runs over every flag (Story 76.2), so no
    path that composes the tree accepts one whose clock is wrong. A flag whose tree ``state`` is
    ``DISABLED`` keeps it and its variant: the kill switch wins in every environment. ``tree`` is
    not modified.
    """
    check_environment(environment)
    flags = tree.get("flags")
    if not isinstance(flags, dict):
        raise FlagTreeError("flag tree has no 'flags' object")
    _validate_overlays(flags, overlays)
    check_metadata(flags, overlays)
    composed = copy.deepcopy(dict(tree))
    for key, variant in (overlays.get(environment) or {}).items():
        entry = composed["flags"][key]
        if not _is_disabled(entry):
            entry["defaultVariant"] = variant
    return composed


def render(environment: str, *, flags_path: Path | str | None = None) -> bytes:
    """The tree as ``environment`` reads it, as JSON bytes: the chart's ConfigMap and the host's FILE provider.

    Resolves the tree exactly as ``read_boolean`` does and composes the ``flag-overlays.json``
    beside it when there is one (else the tree as it is). Raises :class:`FlagConfigError`
    subclasses; unlike ``read_boolean`` it has no ``default`` to fall back to.
    """
    check_environment(environment)
    resolved = cutover_root.resolve_flags_path(flags_path)
    if resolved is None:
        raise FlagTreeError("no flag tree: set PYFORGE_FLAGS_PATH or pass flags_path")
    try:
        tree = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FlagTreeError(f"unreadable flag tree {resolved}: {exc}") from exc
    if not isinstance(tree, dict):
        raise FlagTreeError(f"malformed flag tree {resolved}: not an object")
    overlays = overlays_path_for(resolved)
    if overlays is not None:
        tree = compose(tree, load_overlays(overlays), environment)
    return (json.dumps(tree, indent=2) + "\n").encode("utf-8")


def read_boolean(key: str, default: bool = False, *, flags_path: Path | str | None = None) -> bool:
    """Return the boolean value of flag ``key`` from the flagd tree.

    ``state: DISABLED`` reads False whatever else is set. Otherwise the key's
    ``defaultVariant`` value is returned when it is a bool; a missing tree, an
    unreadable or malformed tree, a missing key or a non-bool value returns
    ``default`` after one named WARN on stderr (never an exception).

    The tree is read as ``PYFORGE_ENVIRONMENT`` renders it (Story 76.1): a
    ``flag-overlays.json`` beside the resolved tree is composed for that
    environment (see :func:`compose`). An unknown environment, or an overlay that
    cannot be composed, raises a :class:`FlagConfigError` subclass -- never a
    WARN plus ``default``, which could read ON.
    """
    environment = current_environment()  # before any read: a bad environment never reads ON
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
    overlays = overlays_path_for(resolved)
    if overlays is not None:
        flags = compose(payload, load_overlays(overlays), environment)["flags"]
    if key not in flags:
        return _warn(key, f"key missing from {resolved}", default)
    entry = flags[key]
    if not isinstance(entry, dict):
        return _warn(key, f"entry in {resolved} is not an object", default)
    if _is_disabled(entry):
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
