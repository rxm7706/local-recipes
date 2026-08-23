"""Provision designated Django Group rows from the claims contract.

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import Final

import structlog
from django.apps import apps as global_apps
from django.conf import settings

if TYPE_CHECKING:
    from django.apps.registry import Apps
    from django.db.migrations.state import StateApps

__all__ = ["ProvisionResult", "provision_designated_groups"]

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

STAFF_ROLE: Final = "staff"
SUPERUSER_ROLE: Final = "superuser"

DESIGNATED_GROUP_PERMISSIONS: Final[dict[str, tuple[str, ...]]] = {
    STAFF_ROLE: ("users.view_user", "users.change_user"),
    SUPERUSER_ROLE: (),
}


@dataclass(frozen=True, slots=True)
class ProvisionResult:
    created: tuple[str, ...] = ()
    existing: tuple[str, ...] = ()
    permissions_attached: int = 0


@dataclass(frozen=True, slots=True)
class _DesignatedGroup:
    name: str
    roles: tuple[str, ...] = ()
    codenames: tuple[str, ...] = ()


def provision_designated_groups(apps: StateApps | Apps | None = None) -> ProvisionResult:
    contract = settings.CLAIMS_CONTRACT
    if not contract.is_configured:
        logger.warning(
            "authorization.provisioning_skipped",
            reason="claims_contract_unconfigured",
        )
        return ProvisionResult()

    registry: Apps = global_apps if apps is None else apps
    group_model: Any = registry.get_model("auth", "Group")
    permission_model: Any = registry.get_model("auth", "Permission")

    created: list[str] = []
    existing: list[str] = []
    attached = 0

    for designated in _designated_groups(contract.staff_group, contract.superuser_group):
        group, was_created = group_model.objects.get_or_create(name=designated.name)
        (created if was_created else existing).append(designated.name)

        permissions = _resolve_permissions(permission_model, designated)
        group.permissions.set(permissions)
        attached += len(permissions)

    result = ProvisionResult(
        created=tuple(created),
        existing=tuple(existing),
        permissions_attached=attached,
    )
    logger.info(
        "authorization.groups_provisioned",
        created=result.created,
        existing=result.existing,
        permissions_attached=result.permissions_attached,
    )
    return result


def _designated_groups(staff_group: str, superuser_group: str) -> tuple[_DesignatedGroup, ...]:
    by_name: dict[str, _DesignatedGroup] = {}
    for role, name in ((STAFF_ROLE, staff_group), (SUPERUSER_ROLE, superuser_group)):
        entry = by_name.get(name, _DesignatedGroup(name=name))
        added = tuple(code for code in DESIGNATED_GROUP_PERMISSIONS[role] if code not in entry.codenames)
        by_name[name] = _DesignatedGroup(
            name=name,
            roles=(*entry.roles, role),
            codenames=(*entry.codenames, *added),
        )
    return tuple(by_name.values())


def _resolve_permissions(permission_model: Any, designated: _DesignatedGroup) -> list[Any]:
    resolved: list[Any] = []
    for label in designated.codenames:
        app_label, _, codename = label.partition(".")
        permission = permission_model.objects.filter(
            content_type__app_label=app_label,
            codename=codename,
        ).first()
        if permission is None:
            logger.warning(
                "authorization.permission_unresolved",
                permission=label,
                group=designated.name,
                roles=designated.roles,
            )
            continue
        resolved.append(permission)
    return resolved
