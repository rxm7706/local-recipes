"""Story 9.6 — CAP-7's proof suite: isolation guarantees demonstrated, not claimed.

Four guard-pairs, one per surface (`filtering.py`, `views.py`/`navigation.py`,
`export.py`, `cache.py` + `filtering.py`). Each pair's first test calls the
REAL production function twice, impersonating two distinct roles in one test
body, and asserts both directions of isolation together ("privileged sees
more, unprivileged sees less" — never split across separate tests for the
same guard). Each pair's second test proves the identical assertion logic
fails when that surface's guard is deliberately removed — the guard-removed
variant is always a small function defined locally in this file, reproducing
what the guard's absence would do, never a monkeypatch of the real production
module (`filtering.py`'s equality guard, `navigation.py`'s/`views.py`'s role-
membership guard, and `export.py`'s role-membership check are all inline
comparisons, not named patchable seams — see this story's spec, Design Notes).

The cache pair is different in shape: `cache.py` has no runtime guard for
CAP-2 at all — its own docstring states the invariant is a caller contract it
cannot enforce. So instead of a "guard removed" variant, the second test
reproduces the exact misuse `cache.py`'s docstring already narrates in prose
(a role-pre-filtering `fetch` closure warming a shared key), converting that
claim into an executable, pinned regression.

This file additionally proves each surface's CAP-1 fail-closed default
(`role=None`, "no identity established" -- degrades to zero access, never an
error or elevated grant) with the real production function, since that
branch is as much an isolation guarantee as the two-role comparisons above.

This file covers the cache invariant (9.1/AD-5/CAP-2) half of the AC below by
name. The retention refusal (9.3/AD-7) half is ALREADY a mutation-proof case
-- `test_purge_expired_entries_rechecks_days_a_subclass_could_have_skipped`
in `test_dashboard_audit.py` bypasses one guard via a subclass and proves a
second, independent guard still catches it -- so this file adds no
duplicate coverage for it; see this story's spec for the full rationale.
"""

from __future__ import annotations

import io
import json

import pytest

# Navigation and cache tests below need django (views.py/cache.py both
# require it, per their own module docstrings); filtering.py/export.py are
# deliberately import-free of django. This file exercises all four, so it
# follows the same importorskip guard the django-requiring sibling files use
# (test_dashboard_cache.py, test_dashboard_views.py), so the package suite
# still collects (not errors) when the `[dashboard]` extra is absent.
pytest.importorskip("django", reason="this file exercises views.py/cache.py, which require pyforge-steward[dashboard]")

from django.conf import settings  # noqa: E402

# Settings may already be configured if this file collects alongside another
# test module that configured them first -- guard so a second `configure()`
# call (which Django refuses) never crashes the run. This file needs only
# CACHES (no INSTALLED_APPS/DATABASES -- it never touches audit.py's
# DB-backed surface), mirroring test_dashboard_views.py's minimal block.
#
# Alphabetically, "test_dashboard_isolation_proof.py" sorts after "audit"/
# "cache" and before "middleware"/"navigation"/"views", so in a full-suite
# run audit.py's fuller INSTALLED_APPS/DATABASES/CACHES declaration (a
# mutual superset with cache.py's) will already be in force by the time this
# guard runs -- but the assertion in `_fresh_backend()` below still applies
# defensively in case this file is ever run in isolation or collected first.
if not settings.configured:
    settings.configure(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyforge-steward-dashboard-test",
            },
        },
    )

from django.core.cache import caches  # noqa: E402 -- must follow settings.configure()
from django.core.cache.backends.locmem import LocMemCache  # noqa: E402
from django.core.handlers.asgi import ASGIRequest  # noqa: E402
from django.http import JsonResponse  # noqa: E402

from pyforge.steward.dashboard.cache import get_master_dataset  # noqa: E402
from pyforge.steward.dashboard.declarations import AccessDeclaration  # noqa: E402
from pyforge.steward.dashboard.export import (  # noqa: E402
    ExportPolicy,
    ExportUnauthorizedError,
    authorize_export,
)
from pyforge.steward.dashboard.filtering import filter_by_role  # noqa: E402
from pyforge.steward.dashboard.navigation import Page  # noqa: E402
from pyforge.steward.dashboard.views import build_navigation_view  # noqa: E402


def _fresh_backend():
    """Mirrors test_dashboard_cache.py's helper of the same name: fails
    loudly, rather than silently asserting against the wrong store, if
    another test module won the `settings.configure()` race with an
    incompatible CACHES declaration.
    """
    backend = caches["default"]
    assert isinstance(backend, LocMemCache), (
        f"the cache-invariant tests below require the LocMemCache declared "
        f"in this file, got {type(backend).__name__} -- another test module "
        f"configured Django settings first"
    )
    assert settings.CACHES["default"].get("LOCATION") == "pyforge-steward-dashboard-test", (
        f"another test module configured Django settings first: "
        f"CACHES[default] is {settings.CACHES['default']!r}, not the backend "
        f"declared in this file"
    )
    backend.clear()
    return backend


# ── Filtering: filter_by_role (CAP-2/CAP-7) ──────────────────────────────

_FILTER_DECLARATION = AccessDeclaration(access_column="region", roles=("east", "west"))
_FILTER_MASTER = [
    {"region": "east", "id": 1},
    {"region": "east", "id": 2},
    {"region": "east", "id": 3},
    {"region": "west", "id": 4},
]


def _assert_filter_isolation(east_rows, west_rows):
    """The isolation assertion shared by both filtering tests below: east
    (the role skewed to have more master rows) sees strictly more than
    west, and the two role views are disjoint by id.
    """
    east_ids = {row["id"] for row in east_rows}
    west_ids = {row["id"] for row in west_rows}
    assert east_ids == {1, 2, 3}, f"east's view is wrong: {east_ids!r}"
    assert west_ids == {4}, f"west's view is wrong: {west_ids!r}"
    assert east_ids.isdisjoint(west_ids), "east and west views must be disjoint"


def test_filter_by_role_isolation_is_not_vacuous():
    east_view = filter_by_role(_FILTER_MASTER, _FILTER_DECLARATION, "east")
    west_view = filter_by_role(_FILTER_MASTER, _FILTER_DECLARATION, "west")

    _assert_filter_isolation(east_view.rows, west_view.rows)


def _filter_without_role_guard(master, role):
    """Reproduces `filter_by_role` with its `row[access_column] == role`
    equality guard removed: every row is returned regardless of role --
    exactly what filter_by_role would do if that one comparison were
    deleted. Never a monkeypatch of filtering.py itself.
    """
    return tuple(master)


def test_filter_by_role_isolation_check_fails_if_the_equality_guard_is_removed():
    east_view = _filter_without_role_guard(_FILTER_MASTER, "east")
    west_view = _filter_without_role_guard(_FILTER_MASTER, "west")

    with pytest.raises(AssertionError):
        _assert_filter_isolation(east_view, west_view)


def test_filter_by_role_degrades_to_zero_rows_with_no_identity():
    """CAP-1's fail-closed default: `role=None` (no identity established)
    returns zero rows, never an error and never every row.
    """
    view = filter_by_role(_FILTER_MASTER, _FILTER_DECLARATION, None)

    assert view.rows == ()


# ── Navigation: build_navigation_view + Page (CAP-3/CAP-7) ───────────────

VIEWER_ONLY_PAGE = Page(path="/reports", label="Reports", roles=("viewer",))
ADMIN_ONLY_PAGE = Page(path="/admin-console", label="Admin Console", roles=("admin",))
SHARED_PAGE = Page(path="/home", label="Home", roles=("viewer", "admin"))
NAV_PAGES = (VIEWER_ONLY_PAGE, ADMIN_ONLY_PAGE, SHARED_PAGE)


def _request(role, *, include_role_key: bool = True):
    """Duplicated locally from test_dashboard_views.py's helper of the same
    name -- this package's established per-file convention, no shared
    conftest.py.
    """
    scope = {"method": "GET", "path": "/", "headers": []}
    if include_role_key:
        scope["dashboard_role"] = role
    return ASGIRequest(scope, io.BytesIO())


def _assert_navigation_isolation(admin_body, viewer_body):
    """The isolation assertion shared by both navigation tests below:
    admin's response bytes contain admin+shared paths and omit the
    viewer-only path; viewer's contain only shared and omit the admin-only
    path.
    """
    assert b"/admin-console" in admin_body
    assert b"/home" in admin_body
    assert b"/reports" not in admin_body, "admin's response must not leak the viewer-only page"

    assert b"/home" in viewer_body
    assert b"/reports" in viewer_body
    assert b"/admin-console" not in viewer_body, "viewer's response must not leak the admin-only page"


def test_navigation_isolation_is_not_vacuous_in_either_direction():
    view = build_navigation_view(NAV_PAGES)

    admin_response = view(_request("admin"))
    viewer_response = view(_request("viewer"))

    _assert_navigation_isolation(admin_response.content, viewer_response.content)


def _navigation_view_without_role_guard(pages):
    """Reproduces `build_navigation_view` with its role-membership guard
    removed: the returned view renders every declared page regardless of
    `request.scope['dashboard_role']`. Never a monkeypatch of views.py or
    navigation.py themselves.
    """

    def navigation_view(request):
        return JsonResponse({"pages": [{"path": page.path, "label": page.label} for page in pages]})

    return navigation_view


def test_navigation_isolation_check_fails_if_the_role_membership_guard_is_removed():
    view = _navigation_view_without_role_guard(NAV_PAGES)

    admin_response = view(_request("admin"))
    viewer_response = view(_request("viewer"))

    with pytest.raises(AssertionError):
        _assert_navigation_isolation(admin_response.content, viewer_response.content)


def test_navigation_degrades_to_no_pages_with_no_identity():
    """CAP-1's fail-closed default: a scope with no `dashboard_role` key at
    all (`include_role_key=False` -- the shape a request untouched by
    `DashboardIdentityMiddleware` would have) sees no pages whatsoever, not
    every page.
    """
    view = build_navigation_view(NAV_PAGES)

    response = view(_request(role=None, include_role_key=False))

    assert json.loads(response.content) == {"pages": []}


# ── Export: authorize_export + ExportPolicy (CAP-5/CAP-7) ────────────────

_EXPORT_POLICY = ExportPolicy(allowed_roles=("admin",))


def _assert_export_isolation(export_fn, policy, authorized_role, unauthorized_role):
    """The isolation assertion shared by both export tests below:
    `authorized_role` returns `None` silently; `unauthorized_role` raises
    `ExportUnauthorizedError`.

    Deliberately not a nested `pytest.raises` -- when the expected raise
    does not happen (the guard-removed case), `pytest.raises` itself would
    raise `Failed`, not `AssertionError`, which the guard-removed test's own
    `pytest.raises(AssertionError)` could not catch. A plain try/except that
    raises `AssertionError` explicitly on a missing raise keeps this
    reusable for both tests.
    """
    assert export_fn(identity="alice", role=authorized_role, policy=policy) is None

    try:
        export_fn(identity="eve", role=unauthorized_role, policy=policy)
    except ExportUnauthorizedError:
        pass
    else:
        raise AssertionError(
            f"expected ExportUnauthorizedError for role {unauthorized_role!r}, but export_fn returned instead"
        )


def test_export_authorization_isolation_is_not_vacuous():
    _assert_export_isolation(authorize_export, _EXPORT_POLICY, "admin", "viewer")


def _authorize_export_without_role_guard(**kwargs):
    """Reproduces `authorize_export` with its role-membership check removed:
    always returns `None` (authorized), regardless of role or policy. Never
    a monkeypatch of export.py itself.
    """
    return None


def test_export_authorization_isolation_check_fails_if_the_role_check_is_removed():
    with pytest.raises(AssertionError):
        _assert_export_isolation(_authorize_export_without_role_guard, _EXPORT_POLICY, "admin", "viewer")


def test_export_authorization_degrades_to_refusal_with_no_identity():
    """CAP-1's fail-closed default: `role=None` (no identity established) is
    refused exactly like any other unauthorized role, never granted export.
    """
    with pytest.raises(ExportUnauthorizedError):
        authorize_export(identity=None, role=None, policy=_EXPORT_POLICY)


# ── Cache invariant: get_master_dataset + filter_by_role (AD-5/CAP-2/CAP-7) ─


def test_cache_invariant_holds_under_correct_two_role_wiring():
    backend = _fresh_backend()
    key = "isolation-proof-correct-wiring"
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [
        {"region": "east", "id": 1},
        {"region": "east", "id": 2},
        {"region": "west", "id": 3},
    ]

    # Two independently-defined callers, each with its OWN correct
    # (unfiltered) fetch closure, share one cache key -- distinct closures
    # (not one closure called twice) so this mirrors the misuse test's own
    # two-caller shape and the second caller's fetch is genuinely never
    # called (proven by `west_calls` below), not merely redundant with the
    # first.
    def east_caller_fetch():
        return master

    west_calls = []

    def west_caller_fetch():
        west_calls.append(1)
        return master

    # Role-filtering happens only after get_master_dataset returns, applied
    # by the caller, never inside the cache layer or the fetch closure
    # itself.
    east_master = get_master_dataset(key, east_caller_fetch, cache=backend)
    west_master = get_master_dataset(key, west_caller_fetch, cache=backend)
    assert west_calls == [], "the second caller's fetch must never run -- served from the first caller's cache write"

    east_view = filter_by_role(east_master, declaration, "east")
    west_view = filter_by_role(west_master, declaration, "west")

    east_ids = {row["id"] for row in east_view.rows}
    west_ids = {row["id"] for row in west_view.rows}
    assert east_ids == {1, 2}
    assert west_ids == {3}
    assert east_ids.isdisjoint(west_ids)

    # The raw cached value equals the COMPLETE unfiltered master, not a
    # subset -- the AC-named mutation-proof case for AD-5/CAP-2.
    assert backend.get(key) == master


def test_cache_invariant_is_violated_when_a_caller_pre_filters_before_caching():
    """Reproduces `cache.py`'s own documented misuse end-to-end: an
    east-role closure warms `key`, and a west-role caller sharing that key
    is served east's rows. Pins the module docstring's "Demonstrated" claim
    as an executable regression -- not a defect fixed by this story (`AD-5`'s
    other half is a caller contract `cache.py` cannot enforce; see its
    module docstring).
    """
    backend = _fresh_backend()
    key = "isolation-proof-misuse-wiring"
    declaration = AccessDeclaration(access_column="region", roles=("east", "west"))
    master = [
        {"region": "east", "id": 1},
        {"region": "west", "id": 2},
    ]

    # The FIRST caller's fetch closure pre-filters by role BEFORE caching --
    # what gets written under `key` is already role-scoped, not the master
    # frame `get_master_dataset` is contracted to receive.
    def east_prefiltering_fetch():
        return filter_by_role(master, declaration, "east").rows

    first_caller_result = get_master_dataset(key, east_prefiltering_fetch, cache=backend)

    # A SECOND, different-role caller shares the same key. Because a value
    # is already cached (east-filtered), get_master_dataset returns the
    # cache hit and never calls this caller's own fetch at all.
    calls = []

    def west_fetch():
        calls.append(1)
        return master

    second_caller_result = get_master_dataset(key, west_fetch, cache=backend)

    # west's caller is served east's filtered rows, not its own -- the exact
    # leak cache.py's docstring narrates in prose.
    assert second_caller_result == first_caller_result
    assert second_caller_result == ({"region": "east", "id": 1},)
    assert calls == [], "the second caller's fetch must never run -- the leaked value was already cached"
