"""Shared Tier-3 sprint feed ``development_status:`` parsing (Story 41.2).

One parser for ``sources/ledger.py`` and ``sources/marshal.py`` so terminal
status membership and story-key sets stay identical across both guards.
"""

from __future__ import annotations

import re

__all__ = (
    "TERMINAL",
    "is_epic_aggregate_key",
    "normalize_status_value",
    "parse_development_statuses",
)

TERMINAL = frozenset({"done"})

_EPIC_AGGREGATE_KEY_RE = re.compile(r"^epic-\d+(?:-retrospective)?$")


def is_epic_aggregate_key(key: str) -> bool:
    """``epic-N`` and ``epic-N-retrospective`` rows are roll-ups, not stories."""
    return _EPIC_AGGREGATE_KEY_RE.fullmatch(key) is not None


def normalize_status_value(raw: str) -> str:
    """Strip YAML quoting and a trailing inline ``#`` comment from a status value."""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    quote: str | None = None
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].strip()
    return value.strip()


def parse_development_statuses(text: str) -> dict[str, str]:
    """``key: value`` pairs under ``development_status:``."""
    out: dict[str, str] = {}
    in_block = False
    for raw in text.splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw and not raw.startswith((" ", "\t")):
            break
        line = stripped
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = normalize_status_value(value)
    return out
