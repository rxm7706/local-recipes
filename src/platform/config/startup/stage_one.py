"""Stage 1: settings-import refusals (CAP-3).

Called in two places from ``config.settings.production``:

1. ``refuse_required_settings()`` — *before* ``env("DJANGO_SECRET_KEY")`` /
   ``env("DJANGO_ADMIN_URL")`` so a missing key raises ``ImproperlyConfigured``
   that names the setting and its remedy, rather than an opaque django-environ
   mid-import failure.
2. ``run_stage_one(sys.modules[__name__])`` — last statement of the leaf, after
   composition, so conditions that read composed values see the final state.

Conditions, in the order ``run_stage_one`` evaluates them:

* ``refuse_required_settings`` — deployed env keys that must be supplied.
* ``refuse_unverified_broker_tls`` — Story 41.4 / CAP-12: a deployed broker is
  verified TLS or it does not boot. Reads the composed ``CELERY_BROKER_URL``.

Every condition is deployed-only (``is_deployed()`` early return).

Portions adapted from millsks/django-15-factor-base (MIT License).
"""

from __future__ import annotations

import os
import ssl
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Final

from django.core.exceptions import ImproperlyConfigured

from config import broker_tls
from config.locality import is_deployed

if TYPE_CHECKING:
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
                f"{setting.name} is {kind} in a deployed component. {setting.remedy}"
            )
            raise ImproperlyConfigured(message)


def refuse_unverified_broker_tls(settings_module: ModuleType | None = None) -> None:
    """Refuse a deployed component whose broker TLS would not be verified.

    Story 41.4 / CAP-12 (red-team X-2 → R-14). Three forbidden states, each
    named in its message:

    1. an unrecognised ``COMPONENT_BROKER_SSL_CERT_REQS`` value;
    2. a policy weaker than ``CERT_REQUIRED`` while deployed — encrypted but
       unauthenticated is the exact posture this story removes;
    3. a ``rediss://`` broker with no CA trust source to verify it against.

    Case 2 branches on the *verify mode* rather than the policy name, so a
    weaker rung added to ``CERT_REQS_BY_NAME`` later cannot become deployable
    by omission.

    The broker URL comes from the composed ``CELERY_BROKER_URL`` on
    *settings_module* when there is one — the URL Celery will actually connect
    with — rather than a re-derivation that django-environ's
    ``REDIS_BROKER_URL_FILE`` handling could disagree with.

    ``config.broker_tls`` already composes ``CERT_REQUIRED`` for every one of
    these, so the refusal is the operator-facing half of a posture that is
    already fail-closed, never the only thing standing between production and
    ``CERT_NONE``.

    Args:
        settings_module: The leaf settings module being validated, if any.

    Raises:
        ImproperlyConfigured: Message always names the env key and its remedy.
    """
    if not is_deployed():
        return

    requested = broker_tls.requested_cert_reqs_name()
    mode = broker_tls.CERT_REQS_BY_NAME.get(requested)
    if mode is None:
        raise ImproperlyConfigured(broker_tls.unrecognised_policy_message(requested))

    if mode != ssl.CERT_REQUIRED:
        raise ImproperlyConfigured(
            broker_tls.unverified_when_deployed_message(requested),
        )

    broker_url = broker_tls.broker_url_from_settings(settings_module)
    if broker_tls.is_tls_broker(broker_url) and not broker_tls.resolve_ca_trust():
        raise ImproperlyConfigured(broker_tls.no_ca_trust_message())


def run_stage_one(settings_module: ModuleType, /) -> None:
    """Evaluate every stage-1 condition against a settings module being composed.

    Conditions run in this order:

    1. :func:`refuse_required_settings` — deployed env keys that must be
       supplied. Reads ``os.environ``; it runs before django-environ would.
    2. :func:`refuse_unverified_broker_tls` — Story 41.4 / CAP-12. Reads the
       *composed* ``CELERY_BROKER_URL`` off ``settings_module``, which is why
       this entry point takes one and why leaves call it last.

    Args:
        settings_module: The leaf settings module (``sys.modules[__name__]``).

    Raises:
        ImproperlyConfigured: When any condition finds a forbidden state.
    """
    if not is_deployed():
        return

    refuse_required_settings()
    refuse_unverified_broker_tls(settings_module)
