"""RS256 sign and verify for the service-assertion claim schema."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

import jwt
from django.conf import settings
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
from django_pyforge.assertion.schema import audience_for


def _setting_pem(name: str, override: str | None) -> str:
    raw = override if override is not None else getattr(settings, name, "")
    pem = raw.strip() if isinstance(raw, str) else ""
    if not pem:
        msg = f"{name} is not configured"
        raise AssertionRefusedError(msg)
    return pem


def sign_assertion(
    *,
    sub: str,
    roles: list[str],
    station: str,
    private_pem: str | None = None,
    iat: int | None = None,
) -> str:
    if not isinstance(sub, str) or not sub.strip():
        msg = "sub is empty"
        raise AssertionRefusedError(msg)
    if not isinstance(roles, list) or not all(isinstance(item, str) for item in roles):
        msg = "roles must be a list of strings"
        raise AssertionRefusedError(msg)
    issued = iat if iat is not None else int(datetime.now(tz=UTC).timestamp())
    claims = {
        CLAIM_SUB: sub,
        CLAIM_ROLES: list(roles),
        CLAIM_AUD: audience_for(station),
        CLAIM_IAT: issued,
        CLAIM_EXP: issued + MAX_TTL_SECONDS,
        CLAIM_DELEGATED_BY: DELEGATED_BY,
    }
    pem = _setting_pem("PYFORGE_ASSERTION_PRIVATE_KEY", private_pem)
    return jwt.encode(claims, pem, algorithm=ALG)


def mint_assertion(
    *,
    sub: str,
    roles: list[str],
    station: str,
    private_pem: str | None = None,
    iat: int | None = None,
) -> str:
    """Host-side signer used by the mint view and in-process test transport."""
    return sign_assertion(
        sub=sub,
        roles=roles,
        station=station,
        private_pem=private_pem,
        iat=iat,
    )


def verify_assertion(
    token: str,
    *,
    audience: str,
    public_pem: str | None = None,
) -> dict[str, object]:
    pem = _setting_pem("PYFORGE_ASSERTION_PUBLIC_KEY", public_pem)
    try:
        claims = jwt.decode(
            token,
            pem,
            algorithms=[ALG],
            audience=audience,
            options={
                "require": [
                    CLAIM_SUB,
                    CLAIM_ROLES,
                    CLAIM_AUD,
                    CLAIM_EXP,
                    CLAIM_IAT,
                    CLAIM_DELEGATED_BY,
                ],
            },
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
