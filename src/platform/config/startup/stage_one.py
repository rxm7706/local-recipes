"""Stage 1: required-settings refusals at settings import (CAP-3).

Called in two places from ``config.settings.production``:

1. ``refuse_required_settings()`` — *before* ``env("DJANGO_SECRET_KEY")`` /
   ``env("DJANGO_ADMIN_URL")`` so a missing key raises ``ImproperlyConfigured``
   that names the setting and its remedy, rather than an opaque django-environ
   mid-import failure.
2. ``run_stage_one(sys.modules[__name__])`` — last statement of the leaf, after
   composition, for any namespace checks that belong at import time.

Every condition is deployed-only (``is_deployed()`` early return).

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Final

from django.core.exceptions import ImproperlyConfigured

from config.locality import is_deployed

if TYPE_CHECKING:
    from types import ModuleType

__all__ = [
    "REQUIRED_SETTINGS",
    "RequiredSetting",
    "refuse_required_settings",
    "run_stage_one",
]


@dataclass(frozen=True, slots=True)
class RequiredSetting:
    """One env key a deployed boot must supply, with an operator remedy."""

    name: str
    remedy: str


#: Deployed/production required env keys. Fixture-tested one case per name.
REQUIRED_SETTINGS: Final[tuple[RequiredSetting, ...]] = (
    RequiredSetting(
        name="DJANGO_SECRET_KEY",
        remedy=(
            "Set DJANGO_SECRET_KEY to a long random secret "
            "(for example: `python -c 'import secrets; "
            "print(secrets.token_urlsafe(50))'`)."
        ),
    ),
    RequiredSetting(
        name="DJANGO_ADMIN_URL",
        remedy=(
            "Set DJANGO_ADMIN_URL to the Django admin URL path for this "
            "deployment (for example: 'secret-admin/'), not the development "
            "default."
        ),
    ),
    RequiredSetting(
        name="MCP_HOST_SIDECAR_BASE_URL",
        remedy=(
            "Set MCP_HOST_SIDECAR_BASE_URL to the in-cluster mcp-host Service "
            "(the chart wires http://<release>-mcp-host:8090). Laptop and "
            "platform-ci-test leave it unset (COMPONENT_RUNTIME=local)."
        ),
    ),
)

_INVALID_ADMIN_URLS: Final[frozenset[str]] = frozenset(
    {
        "/",
        "admin",
        "admin/",
        "/admin",
        "/admin/",
    },
)


def _setting_value_is_missing_or_invalid(name: str, raw: str | None) -> bool:
    """True when the env value is absent, blank, or known-invalid for *name*."""
    if raw is None:
        return True
    value = raw.strip()
    if not value:
        return True
    # Placeholder admin paths are not usable production ADMIN_URL values.
    # Compare case-insensitively so Admin/ /Admin/ etc. cannot bypass.
    return name == "DJANGO_ADMIN_URL" and value.casefold() in {
        item.casefold() for item in _INVALID_ADMIN_URLS
    }


def refuse_required_settings() -> None:
    """Refuse missing/invalid required env keys when deployed.

    Reads ``os.environ`` directly so it can run *before* django-environ
    ``env(...)`` calls that would otherwise raise an opaque error.

    Raises:
        ImproperlyConfigured: Message always includes the setting name and remedy.
    """
    if not is_deployed():
        return

    for setting in REQUIRED_SETTINGS:
        raw = os.environ.get(setting.name)
        if _setting_value_is_missing_or_invalid(setting.name, raw):
            if raw is None or not str(raw).strip():
                kind = "missing or empty"
            else:
                kind = "invalid"
            message = (
                f"{setting.name} is {kind} in a deployed component. "
                f"{setting.remedy}"
            )
            raise ImproperlyConfigured(message)


def run_stage_one(settings_module: ModuleType, /) -> None:
    """Evaluate every stage-1 condition against a settings module being composed.

    The ``settings_module`` argument is required for call-site uniformity with
    the django-15-factor-base pattern (conditions that read composed names use
    ``getattr`` on it). CAP-3 stage 1 currently validates required env keys via
    ``os.environ``; the module is accepted and reserved for later conditions.

    Args:
        settings_module: The leaf settings module (``sys.modules[__name__]``).

    Raises:
        ImproperlyConfigured: When any condition finds a forbidden state.
    """
    if not is_deployed():
        return

    # Reserved for namespace-based conditions; silence unused-arg linters.
    _ = settings_module
    refuse_required_settings()
