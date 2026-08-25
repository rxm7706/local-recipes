"""Refuse Wagtail admin when the session has no Wagtail-admin IdP group."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest
    from django.http import HttpResponse

ADMIN_PREFIX = "/cms/"
LOGIN_PREFIX = "/cms/login"
FORBIDDEN_TEMPLATE = "front_door/cms_forbidden.html"


def _path(request: HttpRequest) -> str:
    return request.path_info or request.path


def is_wagtail_admin_path(path: str) -> bool:
    return path == "/cms" or path.startswith(ADMIN_PREFIX)


def is_cms_login_path(path: str) -> bool:
    return path == LOGIN_PREFIX or path.startswith(f"{LOGIN_PREFIX}/")


def holds_wagtail_admin_group(user: object) -> bool:
    groups = getattr(user, "groups", None)
    if groups is None:
        return False
    name = settings.WAGTAIL_ADMIN_IDP_GROUP
    if not name:
        return False
    return groups.filter(name=name).exists()


def must_refuse_admin(request: HttpRequest) -> bool:
    if not is_wagtail_admin_path(_path(request)):
        return False
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return not holds_wagtail_admin_group(user)


def _oidc_login_redirect(request: HttpRequest) -> HttpResponse:
    login_url = str(settings.WAGTAILADMIN_LOGIN_URL)
    query = urlencode({"next": request.get_full_path()})
    separator = "&" if "?" in login_url else "?"
    return redirect(f"{login_url}{separator}{query}")


class WagtailAdminGroupRequiredMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if must_refuse_admin(request):
            return render(
                request,
                FORBIDDEN_TEMPLATE,
                {"idp_group": settings.WAGTAIL_ADMIN_IDP_GROUP},
                status=403,
            )
        if is_cms_login_path(_path(request)):
            user = getattr(request, "user", None)
            if user is None or not getattr(user, "is_authenticated", False):
                return _oidc_login_redirect(request)
            if holds_wagtail_admin_group(user):
                return redirect(reverse("wagtailadmin_home"))
        return self.get_response(request)
