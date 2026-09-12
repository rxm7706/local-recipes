"""Declared local personas for OIDC mapper exercises.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Final

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from config.authorization.mapper import EMAIL_CLAIM
from config.authorization.mapper import NAME_CLAIM
from config.authorization.mapper import USERNAME_CLAIM

__all__ = [
    "DESIGNATED_STAFF",
    "DESIGNATED_SUPERUSER",
    "DESIGNATED_WAGTAIL_ADMIN",
    "PERSONAS",
    "Persona",
    "UnknownPersonaError",
    "build_claims",
    "get_persona",
    "persona_keys",
    "resolve_groups",
]

DESIGNATED_STAFF: Final[str] = "<designated-staff-group>"
DESIGNATED_SUPERUSER: Final[str] = "<designated-superuser-group>"
DESIGNATED_WAGTAIL_ADMIN: Final[str] = "<designated-wagtail-admin-group>"


class UnknownPersonaError(LookupError):
    """Raised when a key names no declared persona."""


@dataclass(frozen=True, slots=True)
class Persona:
    key: str
    subject: str
    username: str
    email: str
    name: str
    groups: tuple[str, ...] = ()


PERSONAS: Final[tuple[Persona, ...]] = (
    Persona(
        key="staff",
        subject="local-dev:persona:staff",
        username="staff-persona",
        email="staff-persona@localhost.invalid",
        name="Staff Persona",
        groups=(DESIGNATED_STAFF,),
    ),
    Persona(
        key="reader",
        subject="local-dev:persona:reader",
        username="reader-persona",
        email="reader-persona@localhost.invalid",
        name="Reader Persona",
        groups=(),
    ),
    Persona(
        key="editor",
        subject="local-dev:persona:editor",
        username="editor-persona",
        email="editor-persona@localhost.invalid",
        name="Editor Persona",
        groups=(DESIGNATED_WAGTAIL_ADMIN,),
    ),
    Persona(
        key="marshal-operator",
        subject="local-dev:persona:marshal-operator",
        username="marshal-operator",
        email="marshal-operator@localhost.invalid",
        name="Marshal Operator",
        groups=("pyforge:station:marshal",),
    ),
)

_BY_KEY: Final[dict[str, Persona]] = {persona.key: persona for persona in PERSONAS}


def persona_keys() -> tuple[str, ...]:
    return tuple(_BY_KEY)


def get_persona(key: str) -> Persona:
    persona = _BY_KEY.get(key)
    if persona is None:
        raise UnknownPersonaError(key)
    return persona


def resolve_groups(persona: Persona) -> tuple[str, ...]:
    contract = settings.CLAIMS_CONTRACT
    designated = {
        DESIGNATED_STAFF: contract.staff_group,
        DESIGNATED_SUPERUSER: contract.superuser_group,
        DESIGNATED_WAGTAIL_ADMIN: settings.WAGTAIL_ADMIN_IDP_GROUP,
    }
    return tuple(dict.fromkeys(designated.get(name, name) for name in persona.groups))


def build_claims(persona: Persona) -> dict[str, Any]:
    contract = settings.CLAIMS_CONTRACT
    claims: dict[str, Any] = {
        USERNAME_CLAIM: persona.username,
        EMAIL_CLAIM: persona.email,
        NAME_CLAIM: persona.name,
    }
    _set_dotted(claims, contract.identity_key_claim, persona.subject)
    _set_dotted(claims, contract.group_claim, list(resolve_groups(persona)))
    return claims


def _set_dotted(payload: dict[str, Any], path: str, value: Any) -> None:
    if not path:
        return
    head, separator, tail = path.partition(".")
    if not separator:
        payload[path] = value
        return
    nested = payload.setdefault(head, {})
    if not isinstance(nested, dict):
        raise ImproperlyConfigured(
            "the configured claim names overlap: one is a dotted path through another's value",
        )
    _set_dotted(nested, tail, value)
