"""Verified broker TLS (CAP-12 / steward 41.4; red-team X-2 → directive R-14).

``rediss://`` used to mean *encrypted but unauthenticated*: base settings pinned
``ssl_cert_reqs`` to ``ssl.CERT_NONE`` for every TLS broker URL, so anything able
to answer on the broker's address was accepted. Under an enterprise TLS mandate
that is worse than plaintext — it looks encrypted and is MITM-able.

This module is the single declaration site for the broker's TLS posture, for the
Celery broker and the Redis result backend alike:

* ``ssl_cert_reqs`` is ``ssl.CERT_REQUIRED`` unless the process is explicitly
  local (``COMPONENT_RUNTIME=local``) *and* the operator asked for ``none``.
  Composition fails closed — a deployed component that asks for ``none`` still
  composes ``CERT_REQUIRED`` and is refused by name at stage 1
  (``config.startup.stage_one.refuse_unverified_broker_tls``), so no code path
  can leave a deployed broker unverified.
* ``ssl_ca_certs`` resolves the corporate bundle: **OS trust store first**
  (``SSL_CERT_FILE``, else OpenSSL's compiled-in default CA file — the pair
  ``ssl.get_default_verify_paths()`` consults, and where an enterprise CA is
  installed), **explicit ``COMPONENT_BROKER_CA_BUNDLE`` path second**.

redis-py wants a bundle *path* (``ssl_ca_certs``), not a Python trust object, so
the ``truststore`` library cannot stand in for this resolution; the OS trust
store is consumed by path, exactly as OpenSSL's own defaults expose it — and
nothing here egresses or resolves anything at runtime, so an air-gapped
deployment resolves identically (pap:CAP-6).
"""

from __future__ import annotations

import os
import ssl
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING
from typing import Final

from config.locality import is_local

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "CA_BUNDLE_ENV_VAR",
    "CERT_REQS_BY_NAME",
    "CERT_REQS_ENV_VAR",
    "DEFAULT_REDIS_URL",
    "TLS_SCHEME",
    "UNVERIFIED",
    "VERIFIED",
    "broker_url_from_env",
    "broker_use_ssl",
    "is_tls_broker",
    "requested_cert_reqs_name",
    "resolve_ca_bundle",
    "resolve_cert_reqs",
]

#: URL scheme that makes the broker connection TLS.
TLS_SCHEME: Final[str] = "rediss://"

#: Env keys ``config.settings.base`` reads for the broker URL, in order.
BROKER_URL_ENV_VAR: Final[str] = "REDIS_BROKER_URL"
REDIS_URL_ENV_VAR: Final[str] = "REDIS_URL"

#: Default when neither URL key is set. Declared once; base settings imports it.
DEFAULT_REDIS_URL: Final[str] = "redis://localhost:6379/0"

#: Env key selecting the broker certificate policy (default: ``required``).
CERT_REQS_ENV_VAR: Final[str] = "COMPONENT_BROKER_SSL_CERT_REQS"

#: Env key holding an explicit PEM bundle path (second tier, after the OS store).
CA_BUNDLE_ENV_VAR: Final[str] = "COMPONENT_BROKER_CA_BUNDLE"

#: The verified policy — the default everywhere, and the only deployed value.
VERIFIED: Final[str] = "required"

#: The unverified policy — laptop-only (``COMPONENT_RUNTIME=local``).
UNVERIFIED: Final[str] = "none"

#: The whole recognised policy surface. Anything else is refused by name.
CERT_REQS_BY_NAME: Final[Mapping[str, ssl.VerifyMode]] = MappingProxyType(
    {
        VERIFIED: ssl.CERT_REQUIRED,
        UNVERIFIED: ssl.CERT_NONE,
    },
)


def is_tls_broker(url: str) -> bool:
    """Return True when *url* is a TLS (``rediss://``) broker URL."""
    return url.startswith(TLS_SCHEME)


def broker_url_from_env() -> str:
    """Resolve the broker URL the way ``config.settings.base`` does.

    Reads ``os.environ`` directly so stage 1 can evaluate the same URL without
    importing Django settings. Stage 1 runs after composition, so any ``.env``
    values django-environ read are already on ``os.environ``.
    """
    broker = os.environ.get(BROKER_URL_ENV_VAR, "").strip()
    if broker:
        return broker
    return os.environ.get(REDIS_URL_ENV_VAR, "").strip() or DEFAULT_REDIS_URL


def requested_cert_reqs_name() -> str:
    """Return the certificate policy the operator asked for.

    Unset/blank means :data:`VERIFIED`. The value is returned verbatim (lower-
    cased) even when unrecognised, so stage 1 can name it in its refusal.
    """
    return os.environ.get(CERT_REQS_ENV_VAR, "").strip().lower() or VERIFIED


def resolve_ca_bundle() -> str | None:
    """Return the CA bundle path to verify the broker against, or None.

    OS trust store first (``SSL_CERT_FILE`` / OpenSSL's default CA file — where
    a corporate bundle is installed), explicit :data:`CA_BUNDLE_ENV_VAR`
    second. A configured path that is not a readable file is skipped rather
    than trusted, so a typo degrades to "no bundle" and stage 1 refuses.
    """
    candidates = (
        ssl.get_default_verify_paths().cafile,
        os.environ.get(CA_BUNDLE_ENV_VAR),
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def resolve_cert_reqs() -> ssl.VerifyMode:
    """Return the verify mode to compose into settings — fail closed.

    ``ssl.CERT_NONE`` is honoured only for an explicitly local process asking
    for it by name. Every other case — deployed, or a value nobody recognises —
    composes ``ssl.CERT_REQUIRED``; stage 1 turns the deployed cases into a
    named refusal so the misconfiguration is loud rather than silent.
    """
    if requested_cert_reqs_name() == UNVERIFIED and is_local():
        return ssl.CERT_NONE
    return ssl.CERT_REQUIRED


def broker_use_ssl(url: str) -> dict[str, object] | None:
    """Return ``CELERY_BROKER_USE_SSL`` / ``CELERY_REDIS_BACKEND_USE_SSL``.

    ``None`` for a non-TLS broker — Celery's own "this transport is not TLS"
    value. ``ssl_ca_certs`` is omitted when verification is off (nothing to
    verify against) or when no bundle resolves; the latter is a deployed
    refusal at stage 1, and locally leaves OpenSSL's own defaults in charge.

    Args:
        url: The broker URL (``CELERY_BROKER_URL`` / result backend).

    Returns:
        The Celery SSL options mapping, or None when *url* is not TLS.
    """
    if not is_tls_broker(url):
        return None
    cert_reqs = resolve_cert_reqs()
    options: dict[str, object] = {"ssl_cert_reqs": cert_reqs}
    if cert_reqs != ssl.CERT_NONE:
        bundle = resolve_ca_bundle()
        if bundle is not None:
            options["ssl_ca_certs"] = bundle
    return options
