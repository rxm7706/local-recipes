"""Story 9.2 — CAP-2's filtering half, and AD-6's filter-then-search shape.

`filter_by_role` is the only entry point from Story 9.1's `get_master_dataset()`
return value into a role-scoped view: it consumes the master (unfiltered)
dataset and produces a `RoleFilteredRows`, never mutating the master and
never writing its output back into the shared cache — closing the CAP-2
misuse `cache.py`'s own docstring demonstrates (an east-role closure warming
a shared key, served to a west-role caller).

`search` is the *only* way to query a `RoleFilteredRows`, and its sole
row-shaped parameter is runtime-checked against that type before any row is
touched. This is AD-6's "enforced by signature, not by discipline": there is
no function in this module — or anywhere in this package — that can search
`get_master_dataset()`'s raw return value, so the filter-then-search order is
a property of the API shape rather than of caller care.

Deliberately import-free of `django`/`channels`, mirroring `declarations.py`
and `navigation.py` — plain `dataclasses`, so this module (and its tests)
work with or without the `[dashboard]` extra installed.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .declarations import AccessDeclaration


@dataclass(frozen=True)
class RoleFilteredRows:
    """AD-6: the ONLY row-shaped type `search()` accepts.

    A distinct type rather than a plain tuple or list, so a caller cannot
    pass `get_master_dataset()`'s raw return value — or any other row-shaped
    object — to `search()` and have it work: the type itself is what AD-6
    means by "enforced by signature".
    """

    rows: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.rows, tuple):
            raise TypeError(
                f"RoleFilteredRows.rows must be a tuple of row mappings, got "
                f"{type(self.rows).__name__} — a bare list would let its "
                f"contents keep changing out from under a caller holding "
                f"this value"
            )
        for index, row in enumerate(self.rows):
            if not isinstance(row, Mapping):
                raise TypeError(
                    f"RoleFilteredRows.rows[{index}] must be a Mapping, got "
                    f"{type(row).__name__} — a non-mapping row cannot be "
                    f"searched by column"
                )


def filter_by_role(
    master: Sequence[Mapping[str, Any]],
    declaration: AccessDeclaration,
    role: str | None,
) -> RoleFilteredRows:
    """CAP-2: the rows of `master` that `role` may see, per `declaration`.

    ``role=None`` (no identity established) fails closed to zero rows, never
    an error — CAP-1's "degrades to a known-unprivileged identity, never an
    elevated one", the same default `navigation.py`'s `build_navigation`
    shares. A ``role`` outside ``declaration.roles`` is a configuration
    defect, not a no-identity degrade, and raises loudly naming the role.

    ``role`` is compared against ``row[declaration.access_column]`` by exact
    equality only — no normalization or stripping. Story 9.1 review pass 3
    explicitly deferred role/identity normalization to Story 9.3's audit
    rows; this inherits that deferral rather than re-deciding it here.

    Never mutates ``master`` and never writes its result back into any
    cache — the master dataset's only sanctioned entry point remains
    `cache.py`'s `get_master_dataset()`, and a role-filtered frame is never
    given a cache key of its own.
    """
    if not isinstance(declaration, AccessDeclaration):
        raise TypeError(
            f"filter_by_role requires an AccessDeclaration, got "
            f"{type(declaration).__name__} — a duck-typed look-alike could "
            f"turn the role-vocabulary check below into a substring match "
            f"instead of exact membership, the same hole "
            f"`DashboardIdentityMiddleware.__init__` already guards against "
            f"for `TrustedIngress`"
        )

    if role is None:
        return RoleFilteredRows(rows=())

    if role not in declaration.roles:
        raise ValueError(
            f"role {role!r} is not in the declared role vocabulary "
            f"{declaration.roles!r} — an unrecognized role is a "
            f"configuration defect, never treated the same as no identity"
        )

    if not isinstance(master, Sequence):
        raise TypeError(
            f"filter_by_role requires master to be a Sequence of row "
            f"mappings, got {type(master).__name__} — likely a caller that "
            f"never actually called `get_master_dataset()`, or that dropped "
            f"a cache-miss `None` straight through"
        )

    column = declaration.access_column
    matched: list[Mapping[str, Any]] = []
    for index, row in enumerate(master):
        if not isinstance(row, Mapping):
            raise TypeError(
                f"row {index} must be a Mapping, got {type(row).__name__} — "
                f"filter_by_role cannot look up the declared access column "
                f"{column!r} on a non-mapping row"
            )
        try:
            value = row[column]
        except KeyError as exc:
            raise KeyError(
                f"row {index} is missing the declared access column "
                f"{column!r} — filter_by_role cannot determine whether this "
                f"row belongs to role {role!r}"
            ) from exc
        if value == role:
            # A deep copy, not the original reference: `master`'s rows must
            # stay untouched by whatever a caller does with the returned
            # frame -- mutating a row (including a nested value inside it)
            # reached through `RoleFilteredRows` must never reach back into
            # the master dataset this was filtered from. A shallow `dict(row)`
            # is not enough: a nested mutable value would still be the same
            # object shared with `master`.
            matched.append(copy.deepcopy(row))
    return RoleFilteredRows(rows=tuple(matched))


def search(frame: RoleFilteredRows, predicate: Callable[[Mapping[str, Any]], bool]) -> tuple[Mapping[str, Any], ...]:
    """AD-6: search a `RoleFilteredRows` — and nothing else — by `predicate`.

    The `isinstance` check runs before any row is inspected, so a caller
    passing the raw master dataset (or any other type) is refused by the
    signature rather than by convention.
    """
    if not isinstance(frame, RoleFilteredRows):
        raise TypeError(
            f"search() requires a RoleFilteredRows, got "
            f"{type(frame).__name__} — AD-6: the library exposes no entry "
            f"point that can search the unfiltered master set, so this is "
            f"refused before any row is inspected"
        )
    if not callable(predicate):
        raise TypeError(
            f"search() requires a callable predicate, got "
            f"{type(predicate).__name__} — validated at the boundary rather "
            f"than left to raise from inside the row loop"
        )
    return tuple(row for row in frame.rows if predicate(row))
