"""Resolve IdP claims to users and sync staff/superuser from group claims.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Final

import structlog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.db import transaction

from config.authorization.claims import read_group_claim
from config.authorization.claims import read_identity_key
from config.authorization.exceptions import ClaimsRejected

if TYPE_CHECKING:
    from collections.abc import Mapping

    from platformapp.users.models import User

__all__ = [
    "EMAIL_CLAIM",
    "NAME_CLAIM",
    "SyncOutcome",
    "USERNAME_CLAIM",
    "resolve_user",
    "sync_authorization",
    "sync_for_interactive",
]

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

USERNAME_CLAIM: Final = "preferred_username"
EMAIL_CLAIM: Final = "email"
NAME_CLAIM: Final = "name"

_IDENTITY_FIELD: Final = "idp_subject"
_USERNAME_FIELD: Final = "username"
_EMAIL_FIELD: Final = "email"
_NAME_FIELD: Final = "name"

_UNSAFE_USERNAME_CHARACTERS: Final = re.compile(r"[^\w.@+-]", re.ASCII)
_DERIVED_DIGEST_LENGTH: Final = 32
_DERIVED_USERNAME_PREFIX: Final = "idp-"

_IDENTITY_KEY_ABSENT: Final = "identity key claim absent"
_IDENTITY_KEY_TOO_LONG: Final = "identity key longer than the identity field"
_USERNAME_UNAVAILABLE: Final = "no username available for the identity key"
_GROUP_CLAIM_ABSENT: Final = "group claim absent"
_USER_DEACTIVATED: Final = "resolved user is deactivated"


@dataclass(frozen=True, slots=True)
class SyncOutcome:
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    ignored: tuple[str, ...] = ()
    is_staff: bool = False
    is_superuser: bool = False


def resolve_user(claims: Mapping[str, Any]) -> User:
    subject = read_identity_key(claims, settings.CLAIMS_CONTRACT.identity_key_claim)
    if subject is None:
        raise ClaimsRejected(_IDENTITY_KEY_ABSENT)
    _reject_an_unstorable_identity_key(subject)

    user_model = get_user_model()
    user = user_model.objects.filter(idp_subject=subject).first()
    if user is not None:
        _reject_a_deactivated_user(user)
        return user

    return _create_user(subject, claims)


def _reject_a_deactivated_user(user: User) -> None:
    if user.is_active:
        return
    logger.warning(
        "authorization.claims_rejected",
        reason=_USER_DEACTIVATED,
        idp_subject=user.idp_subject,
    )
    raise ClaimsRejected(_USER_DEACTIVATED)


def _reject_an_unstorable_identity_key(subject: str) -> None:
    limit = _field_max_length(_IDENTITY_FIELD)
    if limit is None or len(subject) <= limit:
        return
    logger.warning(
        "authorization.identity_key_rejected",
        reason=_IDENTITY_KEY_TOO_LONG,
        identity_key_length=len(subject),
        identity_field_length=limit,
    )
    raise ClaimsRejected(_IDENTITY_KEY_TOO_LONG)


def _create_user(subject: str, claims: Mapping[str, Any]) -> User:
    user_model = get_user_model()
    attributes = _attributes_from_claims(claims, subject)

    with transaction.atomic():
        user = user_model(idp_subject=subject)
        user.username = _available_username(user, attributes["username"], subject)
        user.email = attributes["email"]
        user.name = attributes["name"]
        user.set_unusable_password()
        try:
            with transaction.atomic():
                user.save()
        except IntegrityError as conflict:
            return _resolve_a_lost_insert(subject, user.username, conflict)

    logger.info(
        "authorization.user_created",
        idp_subject=subject,
        username=user.username,
    )
    return user


def _resolve_a_lost_insert(subject: str, username: str, conflict: IntegrityError) -> User:
    winner = get_user_model().objects.filter(idp_subject=subject).first()
    if winner is None:
        logger.warning(
            "authorization.username_unavailable",
            idp_subject=subject,
            desired_username=username,
        )
        raise ClaimsRejected(_USERNAME_UNAVAILABLE) from conflict

    logger.info(
        "authorization.user_created_concurrently",
        idp_subject=subject,
        username=winner.username,
    )
    return winner


def _attributes_from_claims(claims: Mapping[str, Any], subject: str) -> dict[str, str]:
    return {
        "username": _sanitized_username(_read_text(claims, USERNAME_CLAIM))
        or _username_from_identity_key(subject),
        "email": _bounded(_read_text(claims, EMAIL_CLAIM), _EMAIL_FIELD),
        "name": _bounded(_read_text(claims, NAME_CLAIM), _NAME_FIELD),
    }


def _field_max_length(field_name: str) -> int | None:
    field = get_user_model()._meta.get_field(field_name)  # noqa: SLF001
    max_length = getattr(field, "max_length", None)
    return max_length if isinstance(max_length, int) else None


def _bounded(value: str, field_name: str) -> str:
    limit = _field_max_length(field_name)
    return value if limit is None else value[:limit]


def _sanitized_username(value: str) -> str:
    rendered = _UNSAFE_USERNAME_CHARACTERS.sub("-", value).strip("-")
    limit = _field_max_length(_USERNAME_FIELD)
    if limit is not None:
        rendered = rendered[:limit]
    return rendered.strip("-")


def _read_text(claims: Mapping[str, Any], name: str) -> str:
    value = claims.get(name)
    return value.strip() if isinstance(value, str) else ""


def _available_username(user: User, desired: str, subject: str) -> str:
    user_model = get_user_model()
    candidates = _username_candidates(desired, subject)
    holders: dict[str, str | None] = dict(
        user_model.objects.filter(username__in=candidates)
        .exclude(pk=user.pk)
        .values_list("username", "idp_subject"),
    )
    for candidate in candidates:
        if candidate not in holders:
            if candidate != desired:
                logger.warning(
                    "authorization.username_collision",
                    idp_subject=subject,
                    desired_username=desired,
                    held_by_idp_subject=holders[desired],
                    username=candidate,
                )
            return candidate

    logger.warning(
        "authorization.username_unavailable",
        idp_subject=subject,
        desired_username=desired,
    )
    raise ClaimsRejected(_USERNAME_UNAVAILABLE)


def _username_candidates(desired: str, subject: str) -> list[str]:
    ordered = [desired, _derived_username(subject), _username_from_identity_key(subject)]
    return list(dict.fromkeys(ordered))


def _username_from_identity_key(subject: str) -> str:
    return _sanitized_username(subject) or _derived_username(subject)


def _derived_username(subject: str) -> str:
    digest = hashlib.sha256(subject.encode()).hexdigest()[:_DERIVED_DIGEST_LENGTH]
    return f"{_DERIVED_USERNAME_PREFIX}{digest}"


def sync_authorization(user: User, claims: Mapping[str, Any]) -> SyncOutcome:
    contract = settings.CLAIMS_CONTRACT
    asserted = read_group_claim(claims, contract.group_claim)
    if asserted is None:
        logger.warning(
            "authorization.claims_rejected",
            reason=_GROUP_CLAIM_ABSENT,
            idp_subject=user.idp_subject,
            group_claim=contract.group_claim,
        )
        raise ClaimsRejected(_GROUP_CLAIM_ABSENT)

    with transaction.atomic():
        resolved: dict[str, int] = dict(
            Group.objects.filter(name__in=asserted).values_list("name", "pk"),
        )
        held: dict[str, int] = dict(user.groups.values_list("name", "pk"))

        ordered = tuple(dict.fromkeys(asserted))
        ignored = tuple(name for name in ordered if name not in resolved)
        added = tuple(name for name in ordered if name in resolved and name not in held)
        removed = tuple(sorted(name for name in held if name not in resolved))

        if added:
            user.groups.add(*(resolved[name] for name in added))
        if removed:
            user.groups.remove(*(held[name] for name in removed))

        user.is_staff = contract.staff_group in resolved
        user.is_superuser = contract.superuser_group in resolved
        user.save(update_fields=["is_staff", "is_superuser"])

        for name in ignored:
            logger.warning(
                "authorization.unknown_group_claim",
                idp_subject=user.idp_subject,
                group=name,
            )

        outcome = SyncOutcome(
            added=added,
            removed=removed,
            ignored=ignored,
            is_staff=user.is_staff,
            is_superuser=user.is_superuser,
        )
        logger.info(
            "authorization.synced",
            idp_subject=user.idp_subject,
            groups_added=outcome.added,
            groups_removed=outcome.removed,
            groups_ignored=outcome.ignored,
            is_staff=outcome.is_staff,
            is_superuser=outcome.is_superuser,
        )
    return outcome


def sync_for_interactive(user: User, claims: Mapping[str, Any]) -> SyncOutcome:
    return sync_authorization(user, claims)
