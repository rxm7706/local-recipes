"""Claims contract: identity-key and group claim names from the environment.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Final

if TYPE_CHECKING:
    import environ

__all__ = [
    "CLAIMS_ENVIRONMENT_VARIABLES",
    "ClaimsContract",
    "load_claims_contract",
    "read_group_claim",
    "read_identity_key",
]

CLAIMS_ENVIRONMENT_VARIABLES: Final[tuple[str, ...]] = (
    "COMPONENT_IDENTITY_CLAIM",
    "COMPONENT_GROUP_CLAIM",
    "COMPONENT_STAFF_GROUP",
    "COMPONENT_SUPERUSER_GROUP",
)


@dataclass(frozen=True, slots=True)
class ClaimsContract:
    """Four names mapping IdP claims onto Django authorization."""

    identity_key_claim: str
    group_claim: str
    staff_group: str
    superuser_group: str

    @property
    def is_configured(self) -> bool:
        return all(
            (
                self.identity_key_claim,
                self.group_claim,
                self.staff_group,
                self.superuser_group,
            ),
        )


def load_claims_contract(env: environ.Env) -> ClaimsContract:
    identity_key_claim, group_claim, staff_group, superuser_group = (
        env.str(name, default="").strip() for name in CLAIMS_ENVIRONMENT_VARIABLES
    )
    return ClaimsContract(
        identity_key_claim=identity_key_claim,
        group_claim=group_claim,
        staff_group=staff_group,
        superuser_group=superuser_group,
    )


def _resolve(claims: Mapping[str, Any], path: str) -> Any:
    if not path:
        return None
    if path in claims:
        return claims[path]
    current: Any = claims
    for segment in path.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return None
        current = current[segment]
    return current


def _read_name(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, int):
        return str(value)
    return None


def read_group_claim(claims: Mapping[str, Any], path: str) -> list[str] | None:
    value = _resolve(claims, path)
    if isinstance(value, str | int) and not isinstance(value, bool):
        name = _read_name(value)
        return None if name is None else [name]
    if isinstance(value, list | tuple):
        names = [_read_name(item) for item in value]
        return None if any(name is None for name in names) else [name for name in names if name is not None]
    return None


def read_identity_key(claims: Mapping[str, Any], path: str) -> str | None:
    return _read_name(_resolve(claims, path))
