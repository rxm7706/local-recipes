"""Story 9.2 — CAP-3: an unauthorized page is absent, not hidden.

`Page` is the declaration an adopter fills in instead of hand-wiring
conditional navigation: the path/label a caller sees, and the closed set of
roles allowed to see it. `build_navigation` is the builder — it never
renders anything, it only decides which pages a given role may see, in the
declared order. A page whose `roles` does not include the caller's role is
not marked hidden, it is simply absent from the returned tuple, which is
what `views.py`'s JSON-rendered response then reflects verbatim.

Deliberately import-free of `django`/`channels`, mirroring `declarations.py`
and `middleware.py` — plain `dataclasses`, so this module (and its tests)
work with or without the `[dashboard]` extra installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Page:
    """CAP-3: one navigable page, and the closed set of roles that may see it.

    ``path``/``label`` are what a caller sees; ``roles`` is the closed
    vocabulary of role names allowed to see this page. This class does not
    render or filter anything — it is the statement an adopter makes instead
    of hand-writing conditional navigation.
    """

    path: str
    label: str
    roles: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, value in (("path", self.path), ("label", self.label)):
            if not isinstance(value, str):
                raise TypeError(f"Page.{field_name} must be a string, got {type(value).__name__}")
            if not value.strip():
                raise ValueError(
                    f"Page.{field_name} must not be empty or whitespace-only — "
                    f"a page cannot be navigated to or labeled without one"
                )
            if value != value.strip():
                raise ValueError(
                    f"Page.{field_name} {value!r} carries leading/trailing "
                    f"whitespace — a padded value is not what a caller sees "
                    f"or where the route is actually mounted"
                )
        if not isinstance(self.roles, tuple):
            raise TypeError(
                f"Page.roles must be a tuple of role names, got "
                f"{type(self.roles).__name__} — a bare string would silently "
                f"be iterated character-by-character instead of treated as "
                f"one role"
            )
        if not self.roles:
            raise ValueError(
                "Page.roles must not be empty — a page with no permitted "
                "roles can never be reached and should not be declared"
            )
        for index, role in enumerate(self.roles):
            if not isinstance(role, str):
                raise TypeError(
                    f"Page.roles[{index}] must be a string, got "
                    f"{type(role).__name__} — a non-string role can never "
                    f"match an extracted role header"
                )
            if not role.strip():
                raise ValueError(
                    f"Page.roles[{index}] must not be empty or whitespace-only — an unnamed role can never match"
                )
            if role != role.strip():
                raise ValueError(
                    f"Page.roles[{index}] {role!r} carries leading/trailing "
                    f"whitespace — the role value extracted from a header "
                    f"never does, so it can never match"
                )


def build_navigation(role: str | None, pages: Sequence[Page]) -> tuple[Page, ...]:
    """CAP-3: the pages `role` may see, in the declared order.

    ``role=None`` (no identity established) returns an empty tuple — CAP-1's
    "degrades to a known-unprivileged identity, never an elevated one", the
    same fail-closed default `middleware.py` and `filtering.py` share. A page
    whose ``roles`` does not include ``role`` is simply omitted, not marked
    hidden — the caller receiving this tuple has no way to know it existed.

    Every element of ``pages`` is checked by type before the membership test
    runs (review pass 1). Without this, a duck-typed object whose ``roles``
    happens to be a bare *string* rather than a tuple turns ``role in
    page.roles`` into Python substring matching instead of exact-tuple
    membership -- reopening, at this boundary, precisely the hole Story
    9.1's `DashboardIdentityMiddleware.__init__` already hardened against for
    `TrustedIngress` (a `role="east"` could then match a duck-typed page
    whose `.roles` string merely *contains* "east", silently exposing it to
    a role that was never declared for it).
    """
    if role is None:
        return ()
    if not isinstance(pages, Sequence):
        raise TypeError(f"build_navigation requires pages to be a Sequence[Page], got {type(pages).__name__}")
    # Materialized once: `pages` is typed `Sequence[Page]`, but a caller
    # passing a one-shot iterator would pass the type-check loop below and
    # then find it already exhausted by the time the membership pass runs,
    # silently returning an empty tuple regardless of role.
    pages = tuple(pages)
    for index, page in enumerate(pages):
        if not isinstance(page, Page):
            raise TypeError(
                f"pages[{index}] must be a Page, got {type(page).__name__} — "
                f"a duck-typed look-alike could turn the role membership "
                f"check below into a substring match instead of exact "
                f"membership"
            )
    return tuple(page for page in pages if role in page.roles)
