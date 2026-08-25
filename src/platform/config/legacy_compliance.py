"""Permanent /compliance/ → /stations/warden/ redirect (steward 19.1)."""

from __future__ import annotations

from django.http.response import HttpResponseRedirectBase

_TARGET_PREFIX = "/stations/warden/"


class HttpResponseMethodPreservingPermanentRedirect(HttpResponseRedirectBase):
    """RFC 7538 308 — permanent and method-preserving (unlike 301)."""

    status_code = 308


def redirect_to_warden(request, rest: str = ""):
    target = f"{_TARGET_PREFIX}{rest}"
    qs = request.META.get("QUERY_STRING")
    if qs:
        target = f"{target}?{qs}"
    return HttpResponseMethodPreservingPermanentRedirect(target)
