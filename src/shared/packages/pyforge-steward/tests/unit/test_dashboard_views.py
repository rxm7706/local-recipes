"""Story 9.2 — `build_navigation_view` renders CAP-3's absent-not-hidden claim
as an actual served response, not a bare Python return value.

Builds a real Django `ASGIRequest` from a hand-built ASGI scope (no mocking,
no test client, no live server) and asserts on `response.content` -- the raw
serialized JSON bytes -- that a restricted page's path/label leave no trace
in the response a caller actually receives.
"""

from __future__ import annotations

import io
import json

import pytest

# `views.py` is the one new module besides `apps.py`/`cache.py` that
# genuinely needs django, so without the `[dashboard]` extra this file must
# SKIP, not raise a collection error (mirrors `test_dashboard_cache.py`).
pytest.importorskip("django", reason="views.py requires pyforge-steward[dashboard]")

from django.conf import settings  # noqa: E402

# Settings may already be configured if this file collects alongside another
# test module that configured them first -- guard so a second `configure()`
# call (which Django refuses) never crashes the run. This file needs no
# CACHES itself, but a bare `settings.configure()` would win the race with
# `test_dashboard_cache.py` under some collection orders (e.g. this file
# named first on the command line) and leave the process globally configured
# with Django's default LocMemCache -- no `LOCATION` -- which then fails
# `test_dashboard_cache.py`'s own `_fresh_backend()` assertion that the
# in-force CACHES declaration is the one IT expects. Configuring with the
# identical CACHES dict here means whichever module wins the race, the
# result is compatible with both.
if not settings.configured:
    settings.configure(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyforge-steward-dashboard-test",
            },
        },
    )

from django.core.handlers.asgi import ASGIRequest  # noqa: E402

from pyforge.steward.dashboard.navigation import Page  # noqa: E402
from pyforge.steward.dashboard.views import build_navigation_view  # noqa: E402

VIEWER_PAGE = Page(path="/reports", label="Reports", roles=("viewer",))
ADMIN_PAGE = Page(path="/admin-console", label="Admin Console", roles=("admin",))
SHARED_PAGE = Page(path="/home", label="Home", roles=("viewer", "admin"))
PAGES = (VIEWER_PAGE, ADMIN_PAGE, SHARED_PAGE)


def _request(role, *, include_role_key: bool = True):
    scope = {"method": "GET", "path": "/", "headers": []}
    if include_role_key:
        scope["dashboard_role"] = role
    # Only `scope["method"]` and `scope["path"]` are required by the
    # installed Django 5.2's `ASGIRequest.__init__` -- everything else
    # defaults, verified against the installed django source.
    return ASGIRequest(scope, io.BytesIO())


def test_low_privilege_role_sees_only_its_pages_in_the_served_response_bytes():
    view = build_navigation_view(PAGES)
    request = _request("viewer")

    response = view(request)

    assert response.status_code == 200
    body = response.content  # raw serialized JSON bytes, not a Python object

    assert b"/reports" in body
    assert b"Reports" in body
    assert b"/home" in body
    assert b"Home" in body

    # The restricted page must leave NO trace in the served bytes -- checked
    # on the wire format, not on a pre-serialization Python list.
    assert b"/admin-console" not in body
    assert b"Admin Console" not in body

    payload = json.loads(body)
    assert payload == {
        "pages": [
            {"path": "/reports", "label": "Reports"},
            {"path": "/home", "label": "Home"},
        ]
    }


def test_a_different_privileged_role_is_missing_the_first_roles_page_instead():
    """Proves the guard is not vacuous in only one direction: an admin sees
    admin+shared, and it is the viewer-only page that goes missing instead.
    """
    view = build_navigation_view(PAGES)
    request = _request("admin")

    response = view(request)
    body = response.content

    assert b"/admin-console" in body
    assert b"/home" in body
    assert b"/reports" not in body
    assert b"Reports" not in body


def test_no_identity_sees_no_pages_at_all():
    view = build_navigation_view(PAGES)
    request = _request(None)

    response = view(request)
    body = response.content

    assert json.loads(body) == {"pages": []}
    for page in PAGES:
        assert page.path.encode() not in body


def test_a_scope_missing_the_dashboard_role_key_entirely_degrades_to_no_pages():
    """`dashboard_role` absent from scope entirely (rather than explicitly
    `None`) is the shape a request never touched by
    `DashboardIdentityMiddleware` would have -- must degrade the same way.
    """
    view = build_navigation_view(PAGES)
    request = _request(role=None, include_role_key=False)

    response = view(request)

    assert json.loads(response.content) == {"pages": []}


def test_build_navigation_view_rejects_a_non_page_element_at_wiring_time():
    with pytest.raises(TypeError, match=r"pages\[1\] must be a Page"):
        build_navigation_view((VIEWER_PAGE, "not-a-page"))


def test_build_navigation_view_rejects_two_pages_declaring_the_same_path():
    duplicate = Page(path="/reports", label="Reports Again", roles=("admin",))

    with pytest.raises(ValueError, match=r"/reports.*more than once"):
        build_navigation_view((VIEWER_PAGE, duplicate))
