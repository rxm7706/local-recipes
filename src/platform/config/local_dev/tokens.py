"""Mint signed development JWTs for declared personas.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Final

import jwt
import structlog
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config.local_dev.keys import SIGNING_ALGORITHM
from config.local_dev.keys import ensure_keypair
from config.local_dev.keys import load_private_key
from config.local_dev.personas import build_claims
from config.local_dev.personas import get_persona
from config.locality import RUNTIME_ENV_VAR
from config.locality import is_local

__all__ = ["DEFAULT_LIFETIME_SECONDS", "mint_token"]

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

DEFAULT_LIFETIME_SECONDS: Final[int] = 900


def mint_token(
    persona_key: str, *, lifetime_seconds: int = DEFAULT_LIFETIME_SECONDS
) -> str:
    if not is_local():
        raise ImproperlyConfigured(
            f"a development token is never minted in a deployed environment. "
            f"Set {RUNTIME_ENV_VAR}=local for local development.",
        )

    persona = get_persona(persona_key)
    keypair = ensure_keypair()

    issued_at = datetime.now(tz=UTC)
    claims: dict[str, Any] = {
        **build_claims(persona),
        "iss": settings.OIDC_ISSUER,
        "aud": settings.OIDC_AUDIENCE.strip(),
        "iat": issued_at,
        "exp": issued_at + timedelta(seconds=lifetime_seconds),
        "jti": uuid.uuid4().hex,
    }

    token = jwt.encode(
        claims,
        load_private_key(keypair),
        algorithm=SIGNING_ALGORITHM,
        headers={"kid": keypair.kid},
    )
    logger.info(
        "local_dev.token_minted",
        persona=persona.key,
        kid=keypair.kid,
        jti=claims["jti"],
    )
    return token
