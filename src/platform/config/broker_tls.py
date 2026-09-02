"""Verified broker TLS (CAP-12 / steward 41.4; red-team X-2 → directive R-14).

``rediss://`` used to mean *encrypted but unauthenticated*: base settings pinned
``ssl_cert_reqs`` to ``ssl.CERT_NONE`` for every TLS broker URL, so anything able
to answer on the broker's address was accepted. Under an enterprise TLS mandate
that is worse than plaintext -- it looks encrypted and is MITM-able.

This module is the single declaration site for the broker's TLS posture, for the
Celery broker and the Redis result backend alike:

* ``ssl_cert_reqs`` is ``ssl.CERT_REQUIRED`` unless the process is explicitly
  local (``COMPONENT_RUNTIME=local``) *and* asked for a weaker policy by name.
  Composition fails closed -- a deployed component that asks still composes
  ``CERT_REQUIRED`` and is refused by name at stage 1
  (``config.startup.stage_one.refuse_unverified_broker_tls``), so no code path
  can leave a deployed broker unverified.
* The trust source resolves the corporate CA: **OS trust store first**
  (``SSL_CERT_FILE`` / ``SSL_CERT_DIR``, else OpenSSL's compiled-in defaults --
  the pair ``ssl.get_default_verify_paths()`` consults, and where an enterprise
  CA is installed), **explicit ``COMPONENT_BROKER_CA_BUNDLE`` path second**.

Both halves of the OS tier count. A host whose ``update-ca-certificates``
equivalent populates a hashed directory and ships no single concatenated
``cert.pem`` resolves through ``capath``, which becomes redis-py's
``ssl_ca_path``; verified against the installed stack (redis-py 8.1.0 declares
``ssl_ca_path`` and feeds it to ``SSLContext.load_verify_locations(capath=...)``;
kombu 5.6.2 merges the whole ``broker_use_ssl`` mapping into the connection
kwargs with ``connparams.update(conninfo.ssl)``, and celery 5.6.3's Redis result
backend does the same with ``redis_backend_use_ssl``).

redis-py wants paths, not a Python trust object, so the ``truststore`` library
cannot stand in for this resolution; the OS trust store is consumed by path,
exactly as OpenSSL's own defaults expose it -- and nothing here egresses or
resolves anything at runtime, so an air-gapped deployment resolves identically
(pap:CAP-6).
"""

from __future__ import annotations

import os
import ssl
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING
from typing import Final

from django.core.exceptions import ImproperlyConfigured

from config.locality import LOCAL
from config.locality import RUNTIME_ENV_VAR
from config.locality import is_local

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import ModuleType

__all__ = [
    "CA_BUNDLE_ENV_VAR",
    "CERT_REQS_BY_NAME",
    "CERT_REQS_ENV_VAR",
    "DEFAULT_REDIS_URL",
    "TLS_SCHEME",
    "UNVERIFIED",
    "VERIFIED",
    "CaTrust",
    "broker_url_from_env",
    "broker_url_from_settings",
    "broker_use_ssl",
    "is_tls_broker",
    "no_ca_trust_message",
    "requested_cert_reqs_name",
    "resolve_ca_trust",
    "resolve_cert_reqs",
    "unrecognised_policy_message",
    "unverified_when_deployed_message",
]

#: URL scheme that makes the broker connection TLS. Compared case-insensitively:
#: ``REDISS://`` is legal URL syntax, and urlparse/kombu/celery all normalise it
#: to the ``rediss`` transport -- so it must compose SSL options here too, or
#: kombu connects it with none at all ("Secure redis scheme specified (rediss)
#: with no ssl options, defaulting to insecure SSL behaviour").
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

#: The verified policy -- the default everywhere, and the only deployed value.
VERIFIED: Final[str] = "required"

#: The unverified policy -- laptop-only (``COMPONENT_RUNTIME=local``).
UNVERIFIED: Final[str] = "none"

#: The whole recognised policy surface, name -> verify mode. Anything else is
#: refused by name. The *values* are what the code branches on: any entry that
#: is not ``CERT_REQUIRED`` is treated as laptop-only, so adding a weaker rung
#: here (``optional``, say) cannot silently become deployable.
CERT_REQS_BY_NAME: Final[Mapping[str, ssl.VerifyMode]] = MappingProxyType(
    {
        VERIFIED: ssl.CERT_REQUIRED,
        UNVERIFIED: ssl.CERT_NONE,
    },
)


@dataclass(frozen=True, slots=True)
class CaTrust:
    """Where the broker's certificate chain gets verified from.

    ``cafile`` is a concatenated PEM bundle, ``capath`` a hashed directory of
    them. OpenSSL accepts either or both; so does redis-py, as ``ssl_ca_certs``
    and ``ssl_ca_path``.
    """

    cafile: str | None = None
    capath: str | None = None

    def __bool__(self) -> bool:
        """True when at least one trust source resolved."""
        return self.cafile is not None or self.capath is not None

    def as_ssl_options(self) -> dict[str, object]:
        """Render the resolved sources as redis-py connection kwargs."""
        options: dict[str, object] = {}
        if self.cafile is not None:
            options["ssl_ca_certs"] = self.cafile
        if self.capath is not None:
            options["ssl_ca_path"] = self.capath
        return options


def is_tls_broker(url: str) -> bool:
    """Return True when *url* is a TLS (``rediss://``) broker URL.

    The scheme is compared case-insensitively; only the prefix is lower-cased,
    so a credential-bearing URL is never wholesale transformed.
    """
    return url[: len(TLS_SCHEME)].lower() == TLS_SCHEME


def broker_url_from_env() -> str:
    """Resolve the broker URL from ``os.environ`` alone.

    The fallback for a caller with no composed settings to consult. Mirrors
    ``config.settings.base``'s ``REDIS_BROKER_URL`` -> ``REDIS_URL`` ->
    :data:`DEFAULT_REDIS_URL` order; prefer :func:`broker_url_from_settings`,
    which reads what Celery will actually connect with.
    """
    broker = os.environ.get(BROKER_URL_ENV_VAR, "").strip()
    if broker:
        return broker
    return os.environ.get(REDIS_URL_ENV_VAR, "").strip() or DEFAULT_REDIS_URL


def broker_url_from_settings(settings_module: ModuleType | None = None) -> str:
    """Return the broker URL Celery will actually connect with.

    Prefers the composed ``CELERY_BROKER_URL`` on the settings module being
    validated over re-deriving it from the environment. django-environ reads
    through a ``FileAwareMapping``, which gives ``REDIS_BROKER_URL_FILE`` (the
    Kubernetes/Docker secret-mount pattern) precedence over the plain variable,
    and it neither strips surrounding whitespace nor treats ``""`` as unset --
    so a re-derived URL can disagree with the composed one in both directions.

    Args:
        settings_module: The leaf settings module being validated, if any.

    Returns:
        The composed ``CELERY_BROKER_URL``, else the environment-derived URL.
    """
    composed = getattr(settings_module, "CELERY_BROKER_URL", None)
    if isinstance(composed, str) and composed.strip():
        return composed
    return broker_url_from_env()


def requested_cert_reqs_name() -> str:
    """Return the certificate policy the operator asked for.

    Unset/blank means :data:`VERIFIED`. The value is returned verbatim (lower-
    cased) even when unrecognised, so it can be named back to the operator.
    """
    return os.environ.get(CERT_REQS_ENV_VAR, "").strip().lower() or VERIFIED


def _readable_file(candidate: str | None) -> str | None:
    """Return *candidate* when it is a file this process can actually read."""
    if candidate and Path(candidate).is_file() and os.access(candidate, os.R_OK):
        return candidate
    return None


def _readable_dir(candidate: str | None) -> str | None:
    """Return *candidate* when it is a directory this process can search."""
    if (
        candidate
        and Path(candidate).is_dir()
        and os.access(candidate, os.R_OK | os.X_OK)
    ):
        return candidate
    return None


def resolve_ca_trust() -> CaTrust:
    """Return the CA sources to verify the broker against.

    OS trust store first -- ``SSL_CERT_FILE`` / ``SSL_CERT_DIR`` when set to
    real paths, otherwise OpenSSL's compiled-in defaults, which is where an
    enterprise CA install lands. Both halves count: a host with a hashed CA
    directory and no concatenated bundle is correctly configured and must not
    be refused. The explicit :data:`CA_BUNDLE_ENV_VAR` path is the second tier,
    consulted only when the OS store yields nothing.

    A configured path that is missing or unreadable is skipped rather than
    trusted, so a typo or a permission mistake degrades to "no trust source" --
    which stage 1 refuses at boot instead of failing at first connect.
    """
    defaults = ssl.get_default_verify_paths()
    os_trust = CaTrust(
        cafile=_readable_file(defaults.cafile),
        capath=_readable_dir(defaults.capath),
    )
    if os_trust:
        return os_trust
    return CaTrust(cafile=_readable_file(os.environ.get(CA_BUNDLE_ENV_VAR)))


def unrecognised_policy_message(requested: str) -> str:
    """Message naming an unrecognised :data:`CERT_REQS_ENV_VAR` value."""
    recognised = ", ".join(sorted(CERT_REQS_BY_NAME))
    return (
        f"{CERT_REQS_ENV_VAR} is {requested!r}, which is not a recognised "
        f"broker certificate policy (expected one of: {recognised}). "
        f"Unset it to take the verified default ({VERIFIED!r})."
    )


def unverified_when_deployed_message(requested: str) -> str:
    """Message naming a verification-disabling policy in a deployed component."""
    return (
        f"{CERT_REQS_ENV_VAR}={requested} disables broker certificate "
        "verification in a deployed component: a "
        f"{TLS_SCHEME} link would be encrypted but not authenticated. "
        f"Unset it (the default is {VERIFIED!r}), or set "
        f"{RUNTIME_ENV_VAR}={LOCAL} if this is local development against a "
        "self-signed Redis."
    )


def no_ca_trust_message() -> str:
    """Message for a TLS broker with nothing to verify its certificate against."""
    return (
        f"The Celery broker URL is a {TLS_SCHEME} URL "
        f"({BROKER_URL_ENV_VAR} / {REDIS_URL_ENV_VAR}) but no CA trust source "
        "resolved, so the broker's certificate cannot be verified. Install the "
        "corporate CA into the OS trust store (or set SSL_CERT_FILE / "
        f"SSL_CERT_DIR), or set {CA_BUNDLE_ENV_VAR} to a PEM bundle path this "
        "component can read."
    )


def resolve_cert_reqs() -> ssl.VerifyMode:
    """Return the verify mode to compose into settings -- fail closed.

    A policy weaker than ``CERT_REQUIRED`` is honoured only for an explicitly
    local process that asked for it by name. Deployed processes always compose
    ``CERT_REQUIRED``; stage 1 turns those into a named refusal, so the
    misconfiguration is loud rather than silently corrected.

    An unrecognised value composes ``CERT_REQUIRED`` too, but a *local* process
    is told immediately: there is no stage 1 locally, so ``…=nonee`` would
    otherwise be silently upgraded and the self-signed-Redis workflow this
    story preserves would fail with an opaque TLS error instead. Deployed
    processes are deliberately left to stage 1, which keeps its "unrecognised
    policy" refusal reachable rather than pre-empted at settings import.

    The two are not symmetric, on purpose. Stage 1 refuses an unrecognised
    value in a deployed component whatever the broker scheme — declaring an
    intent to weaken verification is itself the finding. This function is
    reached only for a ``rediss://`` broker, so on a laptop the typo is named
    exactly where it changes behaviour; the far commoner
    ``redis://localhost`` laptop, where the value is inert, is not blocked from
    booting over it.

    Raises:
        ImproperlyConfigured: Local process, TLS broker, unrecognised policy.
    """
    requested = requested_cert_reqs_name()
    mode = CERT_REQS_BY_NAME.get(requested)
    if mode is None:
        if is_local():
            raise ImproperlyConfigured(unrecognised_policy_message(requested))
        return ssl.CERT_REQUIRED
    if mode != ssl.CERT_REQUIRED and not is_local():
        return ssl.CERT_REQUIRED
    return mode


def broker_use_ssl(url: str) -> dict[str, object] | None:
    """Return ``CELERY_BROKER_USE_SSL`` / ``CELERY_REDIS_BACKEND_USE_SSL``.

    ``None`` for a non-TLS broker -- Celery's own "this transport is not TLS"
    value. The CA sources are omitted when verification is off (nothing to
    verify against) or when none resolve; the latter is a deployed refusal at
    stage 1, and locally leaves OpenSSL's own defaults in charge.

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
        options.update(resolve_ca_trust().as_ssl_options())
    return options
