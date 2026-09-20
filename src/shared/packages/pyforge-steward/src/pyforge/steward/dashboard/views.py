"""Story 9.2 — CAP-3's "absent from the served response" proof surface.

`build_navigation_view` is a Django view *factory*: it closes over a fixed
set of declared `Page`s and returns a plain view callable an adopter wires
into their own `urlpatterns` (AD-1 — the library provides the pipeline, not
the routing; no `urls.py` or template ships here). The returned view reads
the role Story 9.1's `DashboardIdentityMiddleware` already placed on
`request.scope`, builds the role-filtered navigation via `navigation.py`,
and renders it as JSON — so CAP-3's claim that a restricted page is *absent*,
not merely unrendered, is checkable against an actual `HttpResponse` body
rather than trusted from reading `build_navigation`'s source.

Requires `django`, like `apps.py`/`cache.py` — this module is not imported
by anything outside the `pyforge-steward[dashboard]` extra.
"""

from __future__ import annotations

from typing import Callable, Sequence

from django.http import JsonResponse

from .navigation import Page, build_navigation


def build_navigation_view(pages: Sequence[Page]) -> Callable:
    """Return a Django view function rendering `role`'s navigation as JSON.

    `role` is read from `request.scope.get("dashboard_role")` — the key
    `DashboardIdentityMiddleware` (Story 9.1) sets, or leaves absent/`None`
    when no identity was established. The response body contains only the
    path/label of pages that role may see; a restricted page leaves no trace
    in it at all.

    `pages` is validated once here, at wiring time, not per-request: two
    declared pages sharing one `path` would otherwise let a role that
    matches both surface a navigation payload with an ambiguous duplicate
    entry, silently, on every request that role makes.
    """
    if not isinstance(pages, Sequence):
        raise TypeError(f"build_navigation_view requires pages to be a Sequence[Page], got {type(pages).__name__}")
    # Materialized once, before validation: the closure below reuses `pages`
    # on every request it serves, so a one-shot iterator passed in here must
    # not be exhausted by this wiring-time loop alone -- that would silently
    # starve every future request of navigation, for every role, forever.
    pages = tuple(pages)
    seen_paths: dict[str, Page] = {}
    for index, page in enumerate(pages):
        if not isinstance(page, Page):
            raise TypeError(f"pages[{index}] must be a Page, got {type(page).__name__}")
        if page.path in seen_paths:
            raise ValueError(
                f"pages declares {page.path!r} more than once "
                f"({seen_paths[page.path].label!r} and {page.label!r}) — "
                f"each declared page's path must be unique"
            )
        seen_paths[page.path] = page

    def navigation_view(request) -> JsonResponse:
        role = getattr(request, "scope", {}).get("dashboard_role")
        visible = build_navigation(role, pages)
        response = JsonResponse({"pages": [{"path": page.path, "label": page.label} for page in visible]})
        # This payload is role-scoped -- the entire point of CAP-3 is that a
        # restricted page must not reach an unauthorized caller. A shared
        # HTTP cache or reverse proxy caching one role's response and
        # serving it to a different role's request would reopen exactly
        # that leak one layer up, so caching is refused explicitly rather
        # than left to whatever the deployment's defaults happen to be.
        # `no-store` alone already forbids storage by any cache, private or
        # shared -- `private` adds nothing once `no-store` is present.
        response["Cache-Control"] = "no-store"
        return response

    return navigation_view
