"""Lexical skip-glob matching shared by ``detect``/``check`` and ``verbs/skips``.

``seed/verbs/check.py`` may not import ``verbs/skips`` (leaf import contract);
``apply_skips`` and ``managed_after_skips`` must stay identical to what
``check`` uses for recorded skips. This module is the one matcher both sides
import (Story 70.2).
"""

from __future__ import annotations

import fnmatch
from collections.abc import Sequence

from ..errors import UsageError


def _materialize_patterns(patterns: Sequence[str]) -> tuple[str, ...]:
    if isinstance(patterns, str):
        raise UsageError(
            f"skip patterns must be a sequence of glob strings, got a bare str {patterns!r}",
            remedy=(f"wrap a single pattern in a tuple or list -- ({patterns!r},) rather than {patterns!r}"),
        )
    materialized = tuple(patterns)
    for pattern in materialized:
        if not isinstance(pattern, str):
            raise UsageError(
                f"every skip pattern must be a str, got {pattern!r}",
                remedy="remove or quote the non-string entry in the skip pattern list",
            )
    return materialized


def _require_patterns(patterns: Sequence[str]) -> tuple[str, ...]:
    materialized = _materialize_patterns(patterns)
    stripped = tuple(pattern.strip() for pattern in materialized)
    for original, pattern in zip(materialized, stripped, strict=True):
        if not pattern:
            raise UsageError(
                f"every skip pattern must be non-blank once stripped, got {original!r}",
                remedy=(
                    "remove the blank entry from the skip pattern list, or replace it"
                    " with a glob naming the artifact path to skip"
                ),
            )
    return stripped


def _normalize_relative_posix(target_path: str) -> str:
    normalized = target_path
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def first_match(patterns: Sequence[str], relative_posix: str) -> str | None:
    for pattern in _require_patterns(patterns):
        if fnmatch.fnmatchcase(relative_posix, pattern):
            return pattern
    return None
