"""allauth adapter routing interactive OIDC sign-in through the mapper.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import structlog
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpResponseForbidden

from config.authorization.exceptions import ClaimsRejected
from config.authorization.mapper import resolve_user
from config.authorization.mapper import sync_for_interactive

if TYPE_CHECKING:
    from collections.abc import Mapping

    from allauth.socialaccount.models import SocialLogin
    from django.http import HttpRequest
    from django.http import HttpResponse

__all__ = ["OIDCSocialAccountAdapter", "claims_from"]

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_ID_TOKEN_ENVELOPE = "id_token"  # noqa: S105
_USERINFO_ENVELOPE = "userinfo"
_REFUSAL_BODY = "Sign-in was refused."


def claims_from(sociallogin: SocialLogin) -> Mapping[str, Any]:
    extra_data: Mapping[str, Any] = getattr(sociallogin.account, "extra_data", None) or {}
    envelopes = [extra_data.get(name) for name in (_ID_TOKEN_ENVELOPE, _USERINFO_ENVELOPE)]
    present = [envelope for envelope in envelopes if isinstance(envelope, dict)]
    if not present:
        return extra_data
    flattened: dict[str, Any] = {}
    for envelope in present:
        flattened.update(envelope)
    return flattened


class OIDCSocialAccountAdapter(DefaultSocialAccountAdapter):  # type: ignore[misc]
    """Route every interactive sign-in through the one mapper (CAP-1)."""

    def is_open_for_signup(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> bool:
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def pre_social_login(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
    ) -> None:
        claims = claims_from(sociallogin)
        try:
            user = resolve_user(claims)
            sync_for_interactive(user, claims)
        except ClaimsRejected as refusal:
            logger.warning("authorization.interactive_login_refused", reason=refusal.reason)
            raise ImmediateHttpResponse(self.refusal_response(request)) from refusal
        sociallogin.connect(request, user)

    def refusal_response(self, request: HttpRequest) -> HttpResponse:
        return HttpResponseForbidden(_REFUSAL_BODY)
