"""RS256 service assertion: claim schema, sign/verify, portal client, mint."""

from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.exceptions import (
    AssertionRefusedError,
    BadSignatureError,
    ExpiredAssertionError,
    WrongAudienceError,
)
from django_pyforge.assertion.schema import ALG, AUDIENCE_PREFIX, DELEGATED_BY, MAX_TTL_SECONDS

__all__ = [
    "ALG",
    "AUDIENCE_PREFIX",
    "DELEGATED_BY",
    "MAX_TTL_SECONDS",
    "AssertionRefusedError",
    "BadSignatureError",
    "ExpiredAssertionError",
    "PortalClient",
    "WrongAudienceError",
    "mint_assertion",
    "sign_assertion",
    "verify_assertion",
]


def __getattr__(name: str):
    if name in {"mint_assertion", "sign_assertion", "verify_assertion"}:
        from django_pyforge.assertion import crypto

        return getattr(crypto, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
