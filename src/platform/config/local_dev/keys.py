"""Development signing keypair for local JWT minting.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Final

import structlog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.exceptions import ImproperlyConfigured
from jwt.algorithms import RSAAlgorithm

from config.locality import RUNTIME_ENV_VAR
from config.locality import is_local

__all__ = [
    "DEV_KEY_DIR",
    "JWKS_FILENAME",
    "PRIVATE_KEY_FILENAME",
    "SIGNING_ALGORITHM",
    "DevKeypair",
    "ensure_keypair",
    "load_private_key",
]

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

BASE_DIR: Final[Path] = Path(__file__).resolve().parents[2]
DEV_KEY_DIR: Final[Path] = BASE_DIR / ".dev-keys"
JWKS_FILENAME: Final[str] = "jwks.json"
PRIVATE_KEY_FILENAME: Final[str] = "private.pem"
SIGNING_ALGORITHM: Final[str] = "RS256"

_KEY_DIR_MODE: Final[int] = 0o700
_PRIVATE_KEY_MODE: Final[int] = 0o600


@dataclass(frozen=True, slots=True)
class DevKeypair:
    kid: str
    private_path: Path
    jwks_path: Path


def ensure_keypair() -> DevKeypair:
    if not is_local():
        raise ImproperlyConfigured(
            f"a development keypair is never generated in a deployed environment. "
            f"Set {RUNTIME_ENV_VAR}=local for local development.",
        )

    DEV_KEY_DIR.mkdir(mode=_KEY_DIR_MODE, parents=True, exist_ok=True)
    private_path = DEV_KEY_DIR / PRIVATE_KEY_FILENAME
    jwks_path = DEV_KEY_DIR / JWKS_FILENAME

    if private_path.exists() and jwks_path.exists():
        kid = _kid_from_jwks(jwks_path)
        return DevKeypair(kid=kid, private_path=private_path, jwks_path=jwks_path)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    kid = _compute_kid(public_key)

    private_path.write_bytes(private_pem)
    private_path.chmod(_PRIVATE_KEY_MODE)

    jwks = {"keys": [RSAAlgorithm.to_jwk(public_key, as_dict=True) | {"kid": kid, "use": "sig", "alg": SIGNING_ALGORITHM}]}
    jwks_path.write_text(json.dumps(jwks, indent=2))
    jwks_path.chmod(_PRIVATE_KEY_MODE)

    logger.info("local_dev.keypair_generated", kid=kid, directory=str(DEV_KEY_DIR))
    return DevKeypair(kid=kid, private_path=private_path, jwks_path=jwks_path)


def load_private_key(keypair: DevKeypair) -> bytes:
    return keypair.private_path.read_bytes()


def _compute_kid(public_key: Any) -> str:
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.sha256(public_pem).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _kid_from_jwks(jwks_path: Path) -> str:
    document = json.loads(jwks_path.read_text())
    keys = document.get("keys", [])
    if not keys:
        raise ImproperlyConfigured(f"JWKS document at {jwks_path} has no keys")
    kid = keys[0].get("kid")
    if not isinstance(kid, str) or not kid:
        raise ImproperlyConfigured(f"JWKS document at {jwks_path} has no kid")
    return kid
