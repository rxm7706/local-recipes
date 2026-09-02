"""Stage 1: settings-import refusals (CAP-3).

Called in two places from ``config.settings.production``:

1. ``refuse_required_settings()`` — *before* ``env("DJANGO_SECRET_KEY")`` /
   ``env("DJANGO_ADMIN_URL")`` so a missing key raises ``ImproperlyConfigured``
   that names the setting and its remedy, rather than an opaque django-environ
   mid-import failure.
2. ``run_stage_one(sys.modules[__name__])`` — last statement of the leaf, after
   composition, so conditions that read composed values see the final state.

Conditions run in ``_STAGE_ONE`` order:

* ``refuse_required_settings`` — deployed env keys that must be supplied.
* ``refuse_unverified_broker_tls`` — Story 41.4 / CAP-12: a deployed broker is
  verified TLS or it does not boot.

Every condition is deployed-only (``is_deployed()`` early return).

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Final

from django.core.exceptions import ImproperlyConfigured

from config import broker_tls
from config.locality import LOCAL
from config.locality import RUNTIME_ENV_VAR
from config.locality import is_deployed

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

__all__ = [
    "REQUIRED_SETTINGS",
    "RequiredSetting",
    "refuse_required_settings",
    "refuse_unverified_broker_tls",
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
    RequiredSetting(
        name="COMPONENT_OIDC_ISSUER",
        remedy=(
            "Set COMPONENT_OIDC_ISSUER to the IdP issuer URL for this deployment "
            "(for example: https://idp.example/realms/platform)."
        ),
    ),
    RequiredSetting(
        name="COMPONENT_OIDC_JWKS_URL",
        remedy=(
            "Set COMPONENT_OIDC_JWKS_URL to the IdP JWKS URL for this deployment "
            "(https://... or a pinned file:// mirror)."
        ),
    ),
    RequiredSetting(
        name="COMPONENT_OIDC_AUDIENCE",
        remedy=(
            "Set COMPONENT_OIDC_AUDIENCE to the expected audience for platform "
            "tokens (often the OIDC client id)."
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


def refuse_unverified_broker_tls() -> None:
    """Refuse a deployed component whose broker TLS would not be verified.

    Story 41.4 / CAP-12 (red-team X-2 → R-14). Three forbidden states, each
    named in its message:

    1. an unrecognised ``COMPONENT_BROKER_SSL_CERT_REQS`` value;
    2. ``COMPONENT_BROKER_SSL_CERT_REQS=none`` while deployed — encrypted but
       unauthenticated is the exact posture this story removes;
    3. a ``rediss://`` broker with no CA bundle to verify it against.

    ``config.broker_tls`` already composes ``CERT_REQUIRED`` for every one of
    these, so the refusal is the operator-facing half of a posture that is
    already fail-closed, never the only thing standing between production and
    ``CERT_NONE``.

    Raises:
        ImproperlyConfigured: Message always names the env key and its remedy.
    """
    if not is_deployed():
        return

    requested = broker_tls.requested_cert_reqs_name()
    if requested not in broker_tls.CERT_REQS_BY_NAME:
        recognised = ", ".join(sorted(broker_tls.CERT_REQS_BY_NAME))
        message = (
            f"{broker_tls.CERT_REQS_ENV_VAR} is {requested!r}, which is not a "
            f"recognised broker certificate policy (expected one of: "
            f"{recognised}). Unset it to take the verified default "
            f"({broker_tls.VERIFIED!r})."
        )
        raise ImproperlyConfigured(message)

    if requested == broker_tls.UNVERIFIED:
        message = (
            f"{broker_tls.CERT_REQS_ENV_VAR}={broker_tls.UNVERIFIED} disables "
            "broker certificate verification in a deployed component: a "
            f"{broker_tls.TLS_SCHEME} link would be encrypted but not "
            f"authenticated. Unset it (the default is "
            f"{broker_tls.VERIFIED!r}), or set {RUNTIME_ENV_VAR}={LOCAL} if "
            "this is local development against a self-signed Redis."
        )
        raise ImproperlyConfigured(message)

    if (
        broker_tls.is_tls_broker(broker_tls.broker_url_from_env())
        and broker_tls.resolve_ca_bundle() is None
    ):
        message = (
            f"{broker_tls.BROKER_URL_ENV_VAR} is a {broker_tls.TLS_SCHEME} URL "
            "but no CA bundle resolved, so the broker's certificate cannot be "
            "verified. Install the corporate CA into the OS trust store (or "
            f"set SSL_CERT_FILE), or set {broker_tls.CA_BUNDLE_ENV_VAR} to a "
            "PEM bundle path that exists in this component."
        )
        raise ImproperlyConfigured(message)


_STAGE_ONE: Final[tuple[Callable[[], None], ...]] = (
    refuse_required_settings,
    refuse_unverified_broker_tls,
)


def run_stage_one(settings_module: ModuleType, /) -> None:
    """Evaluate every stage-1 condition against a settings module being composed.

    The ``settings_module`` argument is required for call-site uniformity with
    the django-15-factor-base pattern (conditions that read composed names use
    ``getattr`` on it). Every CAP-3 stage-1 condition reads ``os.environ`` — the
    same source ``config.settings.base`` composed from — so the module is
    accepted and reserved for later namespace-based conditions.

    Args:
        settings_module: The leaf settings module (``sys.modules[__name__]``).

    Raises:
        ImproperlyConfigured: When any condition finds a forbidden state.
    """
    if not is_deployed():
        return

    # Reserved for namespace-based conditions; silence unused-arg linters.
    _ = settings_module
    for condition in _STAGE_ONE:
        condition()
