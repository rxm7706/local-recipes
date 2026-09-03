"""Django-free RS256 assertion verification (canopy AD-7).

The claim rules live here, not in ``crypto``, so that exactly one code path
decides whether an assertion is good: ``crypto.verify_assertion`` (the
Django-settings wrapper the supervisor and the portals use) and
``mcp_auth.authorize_station_scope`` (the transport gate in front of both the
in-process station app and the sidecar proxy) both call this function. Story
42.1 requires the laptop path and the deployed path to verify identically --
one verifier, transport-agnostic -- and a second copy of these rules is how
that guarantee rots.

Importable with no Django installed at all: this module reaches for ``jwt``
and the Django-free claim schema only. The caller supplies the public key.
"""

from __future__ import annotations

import jwt
from jwt.exceptions import ExpiredSignatureError
from jwt.exceptions import InvalidAudienceError
from jwt.exceptions import InvalidSignatureError
from jwt.exceptions import PyJWTError

from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.exceptions import BadSignatureError
from django_pyforge.assertion.exceptions import ExpiredAssertionError
from django_pyforge.assertion.exceptions import WrongAudienceError
from django_pyforge.assertion.schema import ALG
from django_pyforge.assertion.schema import AUDIENCE_PREFIX
from django_pyforge.assertion.schema import CLAIM_AUD
from django_pyforge.assertion.schema import CLAIM_DELEGATED_BY
from django_pyforge.assertion.schema import CLAIM_EXP
from django_pyforge.assertion.schema import CLAIM_IAT
from django_pyforge.assertion.schema import CLAIM_ROLES
from django_pyforge.assertion.schema import CLAIM_SUB
from django_pyforge.assertion.schema import DELEGATED_BY
from django_pyforge.assertion.schema import MAX_TTL_SECONDS

REQUIRED_CLAIMS = (
    CLAIM_SUB,
    CLAIM_ROLES,
    CLAIM_AUD,
    CLAIM_EXP,
    CLAIM_IAT,
    CLAIM_DELEGATED_BY,
)


def verify_assertion_claims(
    token: str,
    *,
    audience: str,
    public_pem: str,
) -> dict[str, object]:
    """Verify one RS256 service assertion and return its claims.

    Raises ``WrongAudienceError`` when the token is well-formed and correctly
    signed but issued for another station -- the transport gate turns that into
    403 while every other refusal is 401, so keep the distinction.
    """
    if not isinstance(public_pem, str) or not public_pem.strip():
        msg = "assertion public key is not configured"
        raise AssertionRefusedError(msg)
    try:
        claims = jwt.decode(
            token,
            public_pem,
            algorithms=[ALG],
            audience=audience,
            options={"require": list(REQUIRED_CLAIMS)},
        )
    except ExpiredSignatureError as exc:
        raise ExpiredAssertionError from exc
    except InvalidAudienceError as exc:
        raise WrongAudienceError from exc
    except InvalidSignatureError as exc:
        raise BadSignatureError from exc
    except PyJWTError as exc:
        raise AssertionRefusedError from exc
    if claims.get(CLAIM_DELEGATED_BY) != DELEGATED_BY:
        msg = "delegated_by is not pyforge-host"
        raise AssertionRefusedError(msg)
    iat = int(claims[CLAIM_IAT])
    exp = int(claims[CLAIM_EXP])
    if exp - iat > MAX_TTL_SECONDS:
        msg = "exp exceeds five minutes from iat"
        raise AssertionRefusedError(msg)
    aud = claims.get(CLAIM_AUD)
    if not isinstance(aud, str) or not aud.startswith(AUDIENCE_PREFIX):
        raise WrongAudienceError
    if not isinstance(claims.get(CLAIM_ROLES), list):
        msg = "roles must be a list"
        raise AssertionRefusedError(msg)
    return claims
