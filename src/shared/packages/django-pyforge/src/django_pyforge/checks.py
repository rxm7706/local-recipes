"""System checks for portal registration (prefix + no SLA body on chrome)."""

from __future__ import annotations

from django.core.checks import CheckMessage
from django.core.checks import Error
from django.core.checks import register

from django_pyforge.portals import PortalConfig
from django_pyforge.discovery import iter_portal_configs

CHROME_FIELDS = (
    "station_name",
    "mount_token",
    "mcp_token",
    "chrome_hooks",
    "owner_slug",
    "backup",
    "work_class",
    "promotion_date",
    "urlconf",
)


def expected_mount_token(station_name: str) -> str:
    return f"/stations/{station_name}/"


def validate_portal_config(config: PortalConfig) -> list[CheckMessage]:
    errors: list[CheckMessage] = []
    hint = f"portal {getattr(config, 'name', type(config).__name__)}"
    if hasattr(config, "sla_body"):
        errors.append(
            Error(
                "SLA body is not a django-pyforge chrome field",
                hint=hint,
                id="django_pyforge.E003",
            ),
        )
    missing = [field for field in CHROME_FIELDS if not hasattr(config, field)]
    if missing:
        errors.append(
            Error(
                f"portal AppConfig missing chrome fields: {missing}",
                hint=hint,
                id="django_pyforge.E004",
            ),
        )
        return errors
    required_text = (
        "station_name",
        "mount_token",
        "mcp_token",
        "owner_slug",
        "backup",
        "work_class",
        "urlconf",
    )
    blank = [field for field in required_text if not getattr(config, field)]
    if blank:
        errors.append(
            Error(
                f"portal AppConfig empty chrome fields: {blank}",
                hint=hint,
                id="django_pyforge.E004",
            ),
        )
    expected = expected_mount_token(config.station_name)
    if config.mount_token != expected:
        errors.append(
            Error(
                "portal must register at "
                f"{expected}; got {config.mount_token!r}",
                hint=hint,
                id="django_pyforge.E001",
            ),
        )
    return errors


@register()
def check_portal_registration(app_configs, **kwargs) -> list[CheckMessage]:
    _ = kwargs
    if app_configs:
        configs = [c for c in app_configs if isinstance(c, PortalConfig)]
    else:
        configs = list(iter_portal_configs())
    errors: list[CheckMessage] = []
    seen: set[str] = set()
    for config in configs:
        errors.extend(validate_portal_config(config))
        name = getattr(config, "station_name", None)
        if name in seen:
            errors.append(
                Error(
                    f"duplicate station_name {name!r}",
                    id="django_pyforge.E005",
                ),
            )
        if name:
            seen.add(name)
    return errors
