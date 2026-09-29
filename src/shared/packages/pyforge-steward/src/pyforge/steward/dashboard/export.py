"""Story 9.4 — CAP-5's "declared, not implemented" half plus its server-side gate.

`middleware.py` (Story 9.1) resolves ``scope["dashboard_identity"]``/
``scope["dashboard_role"]`` at the ASGI boundary; this module is what an
adopter's export view calls to decide whether THAT resolved role may leave
with the data at all. Three pieces:

- `ExportPolicy` — the declaration schema: the closed set of roles an export
  is allowed for, an optional webhook URL to announce a refusal to, and an
  optional `age` recipient to encrypt the produced artifact for. Validated at
  construction, mirroring `AccessDeclaration`'s exact style (type + emptiness
  + no-padding checks naming the offending field) — a misconfigured adopter
  fails loudly at config time rather than silently exporting to everyone or
  never encrypting.
- `authorize_export()` — the ONLY place the decision is made (standing epic
  constraint: an adopter's UI hiding the export control is never sufficient
  on its own). Every refusal is logged as a security event and, if a webhook
  is configured, announced to it via one best-effort, HMAC-signed POST
  (`resolve_webhook_secret`, DW-9-4-3) that refuses to fire at all against a
  loopback/link-local/private/reserved target (DW-9-4-4) — a webhook failure
  or refusal is caught and logged but never suppresses or delays the raised
  refusal.
- `maybe_encrypt_export()` — wraps Story 1.3's `keys.encrypt_file` (the real
  `age` binary, no new crypto dependency) to optionally encrypt the produced
  export artifact when `policy.encryption_recipient` is declared.

This module does NOT build Story 9.3's durable audit-trail model — "recorded
as a security event" here is a `logging` call, the natural integration point
once 9.3 lands, not a substitute for it — and does NOT cross-validate
`ExportPolicy.allowed_roles` against `AccessDeclaration.roles` (9.1's reviews
rejected that same coupling for `TrustedIngress`; independent declarations by
design).

Deliberately import-free of `django`/`channels` — plain stdlib
(`dataclasses`, `logging`, `urllib.request`, `urllib.parse`, `json`,
`datetime`, `pathlib`, `hashlib`, `hmac`, `ipaddress`, `socket`, `os`) plus
the sibling `pyforge.steward.keys` import — so this module works with or
without the `[dashboard]` extra installed, same as
`middleware.py`/`declarations.py`.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import socket
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from pyforge.steward.keys import encrypt_file

_SECURITY_LOGGER_NAME = "pyforge.steward.dashboard.security"
_WEBHOOK_TIMEOUT_SECONDS = 5

SECRET_ENV_VAR = "STEWARD_EXPORT_WEBHOOK_SECRET"
"""DW-9-4-3: the shared HMAC secret, read fresh from this env var on every
refusal (never a literal or default fallback) -- mirroring
`pyforge.herald.webhook.resolve_webhook_secret`'s "never a default
fallback" contract, the precedent named in the deferred-work entry this
closes. Unlike Herald's webhook host (a long-lived ASGI process that
resolves its secret once at construction), `authorize_export` has no
construction point of its own -- it is called directly, per refusal -- so
the secret is resolved per call instead."""

_SIGNATURE_HEADER = "X-Steward-Signature-256"
_SIGNATURE_PREFIX = "sha256="
"""Our own convention for our own outbound POST, not a platform
requirement -- same framing `pyforge.herald.webhook` uses for its
(GitHub-shaped) header name."""


class WebhookSecretMissingError(RuntimeError):
    """`resolve_webhook_secret` found no usable secret. Caught by
    `_post_refusal_webhook`'s broad `except Exception` like any other
    webhook-delivery failure -- the fail-closed behavior this class exists
    for is refusing to emit an UNSIGNED event, not a distinct error surface
    for the caller."""


def resolve_webhook_secret(env: Mapping[str, str] | None = None) -> bytes:
    """The shared HMAC secret for signing export-refusal webhook POSTs,
    read from `STEWARD_EXPORT_WEBHOOK_SECRET` -- never a literal or default
    fallback. Raises `WebhookSecretMissingError` when unset or empty, so a
    caller can never sign with a blank secret (which would make the
    signature trivially forgeable by anyone).

    `env` defaults to `os.environ` and is injectable, mirroring
    `pyforge.herald.webhook.resolve_webhook_secret`'s same shape, so a test
    never needs to touch the real process environment.
    """
    source = os.environ if env is None else env
    value = source.get(SECRET_ENV_VAR)
    if not value:
        raise WebhookSecretMissingError(
            f"{SECRET_ENV_VAR} is not set -- an unsigned export-refusal "
            f"webhook POST would give a receiver no way to verify it "
            f"actually came from this service (DW-9-4-3)"
        )
    return value.encode("utf-8")


def _is_blocked_ip_address(value: str) -> bool:
    """Whether `value` -- an IP address literal -- names a loopback,
    link-local (including the 169.254.169.254 cloud-metadata address),
    private (RFC 1918 / RFC 4193), reserved, multicast, or unspecified
    address (DW-9-4-4). Raises `ValueError` when `value` is not a valid
    IPv4/IPv6 literal -- callers that need to tolerate a DNS name rather
    than an address catch that themselves."""
    ip_obj = ipaddress.ip_address(value)
    return (
        ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_private
        or ip_obj.is_reserved
        or ip_obj.is_multicast
        or ip_obj.is_unspecified
    )


def _resolve_hostname_ips(hostname: str) -> list[str]:
    """The distinct IP address literals `hostname` resolves to, via
    `socket.getaddrinfo` -- a thin, monkeypatchable seam so a test never
    performs a real DNS lookup, mirroring how this module's tests already
    monkeypatch `urllib.request.urlopen` rather than hitting the network.

    An unresolvable hostname is not a security concern this check can act
    on -- the POST attempt itself will fail with its own network error
    moments later -- so `socket.gaierror` is swallowed and an empty list
    returned rather than raised.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return []
    # `str(...)`, not a bare `info[4][0]` set comprehension: `sockaddr` is
    # typed as a union of the IPv4 (2-tuple) and IPv6 (4-tuple) shapes, and
    # mypy cannot narrow index `[0]` across that union to `str` alone --
    # both shapes' first element genuinely is a `str` address at runtime.
    return sorted({str(info[4][0]) for info in infos})


def _webhook_target_is_blocked(hostname: str) -> bool:
    """Whether `hostname` -- resolved fresh, right now -- names or resolves
    to a blocked address (DW-9-4-4). Checked again here, not only at
    `ExportPolicy` construction: construction-time validation
    (`__post_init__`) can only catch an IP-literal `webhook_url` cheaply
    and without a network call; a DNS name is resolved fresh on every
    delivery, which also catches a name that resolves differently now than
    it did at declaration time (a rebind onto the cloud-metadata address,
    for instance).
    """
    return any(_is_blocked_ip_address(ip) for ip in _resolve_hostname_ips(hostname))


@dataclass(frozen=True)
class ExportPolicy:
    """CAP-5: the role vocabulary an export is gated on, plus its two opt-ins.

    ``allowed_roles`` is the closed set of role names `authorize_export`
    checks a resolved role against — independent of, and never
    cross-validated against, `AccessDeclaration.roles` (see this module's
    docstring). ``webhook_url``, if declared, is where a refusal is
    announced — signed with an HMAC secret (`resolve_webhook_secret`,
    DW-9-4-3) and refused, unsent, if it (or a name it resolves to at
    delivery time) is loopback/link-local/private/reserved, unless
    ``allow_private_webhook_targets=True`` opts in (DW-9-4-4's explicit
    escape hatch, e.g. for an intentional internal SIEM sink — the default
    is closed, matching this repo's "fail-closed, not fail-open" convention
    for security-sensitive tooling). ``encryption_recipient``, if declared,
    is the `age` public key `maybe_encrypt_export` encrypts the produced
    artifact to. This class does not perform authorization or encryption
    itself — it is the statement an adopter makes instead of hand-wiring
    either.
    """

    allowed_roles: tuple[str, ...]
    webhook_url: str | None = None
    encryption_recipient: str | None = None
    allow_private_webhook_targets: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_roles, tuple):
            raise TypeError(
                f"ExportPolicy.allowed_roles must be a tuple of role names, "
                f"got {type(self.allowed_roles).__name__} — a bare string "
                f"would silently be iterated character-by-character instead "
                f"of treated as one role"
            )
        if not self.allowed_roles:
            raise ValueError(
                "ExportPolicy.allowed_roles must not be empty — an export "
                "policy with no allowed roles can never authorize an export, "
                "which is never what a caller declaring one intends"
            )
        for index, role in enumerate(self.allowed_roles):
            if not isinstance(role, str):
                raise TypeError(
                    f"ExportPolicy.allowed_roles[{index}] must be a string, "
                    f"got {type(role).__name__} — a non-string role can "
                    f"never match an extracted role"
                )
            if not role.strip():
                raise ValueError(
                    f"ExportPolicy.allowed_roles[{index}] must not be empty "
                    f"or whitespace-only — an unnamed role can never be "
                    f"authorized against"
                )
            if role != role.strip():
                raise ValueError(
                    f"ExportPolicy.allowed_roles[{index}] {role!r} carries "
                    f"leading/trailing whitespace — the role value extracted "
                    f"from a header never does, so it can never match"
                )

        if not isinstance(self.allow_private_webhook_targets, bool):
            raise TypeError(
                f"ExportPolicy.allow_private_webhook_targets must be a bool, "
                f"got {type(self.allow_private_webhook_targets).__name__}"
            )

        if self.webhook_url is not None:
            if not isinstance(self.webhook_url, str):
                raise TypeError(
                    f"ExportPolicy.webhook_url must be a string or None, got {type(self.webhook_url).__name__}"
                )
            parsed = urlparse(self.webhook_url)
            # `.hostname`, not `.netloc` (Edge Case Hunter): a URL like
            # `https://@` or `https://:1` has a non-empty `netloc` (an empty
            # userinfo/port marker) but no real host, so it passed this check
            # and only failed at request time -- every refusal's webhook POST
            # would then silently fail, caught by `_post_refusal_webhook`'s
            # broad `except Exception` and logged as a generic failure with no
            # hint the DECLARATION itself is malformed.
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise ValueError(
                    f"ExportPolicy.webhook_url {self.webhook_url!r} is not a "
                    f"valid http(s) URL — it must have an http or https "
                    f"scheme and a real host, or the refusal webhook POST has "
                    f"nowhere to go"
                )
            # DW-9-4-4: reject an IP-LITERAL host that is loopback/
            # link-local (incl. the 169.254.169.254 cloud-metadata
            # address)/private/reserved at declaration time, cheaply and
            # without a network call. `localhost` (case-insensitive) is
            # special-cased alongside it -- an RFC 6761 reserved name that
            # is loopback by convention, not merely by whatever a resolver
            # happens to answer. Any OTHER DNS name cannot be judged here --
            # resolving it would make constructing a policy perform a real
            # lookup, and a name that is safe today can still resolve
            # somewhere unsafe at delivery time -- so a name is instead
            # re-checked fresh on every delivery by `_post_refusal_webhook`
            # (`_webhook_target_is_blocked`).
            if not self.allow_private_webhook_targets:
                if parsed.hostname.lower() == "localhost":
                    literal_blocked = True
                else:
                    try:
                        literal_blocked = _is_blocked_ip_address(parsed.hostname)
                    except ValueError:
                        literal_blocked = False
                if literal_blocked:
                    raise ValueError(
                        f"ExportPolicy.webhook_url {self.webhook_url!r} "
                        f"targets {parsed.hostname!r}, a loopback/link-local/"
                        f"private/reserved address — a security-event "
                        f"webhook must not target the machine's own network "
                        f"unless allow_private_webhook_targets=True is set "
                        f"explicitly"
                    )

        if self.encryption_recipient is not None:
            if not isinstance(self.encryption_recipient, str):
                raise TypeError(
                    f"ExportPolicy.encryption_recipient must be a string or "
                    f"None, got {type(self.encryption_recipient).__name__}"
                )
            if not self.encryption_recipient.strip():
                raise ValueError(
                    "ExportPolicy.encryption_recipient must not be empty or "
                    "whitespace-only — an unnamed recipient can never be "
                    "encrypted to"
                )
            if self.encryption_recipient != self.encryption_recipient.strip():
                raise ValueError(
                    f"ExportPolicy.encryption_recipient "
                    f"{self.encryption_recipient!r} carries leading/trailing "
                    f"whitespace — a padded recipient is not the `age` "
                    f"public key `age --encrypt` expects"
                )


class ExportUnauthorizedError(Exception):
    """CAP-5: `authorize_export` refused a role that is not in the policy.

    The message names only the refused role (or "no role" when none was
    resolved) — deliberately NOT `policy.allowed_roles` or
    `policy.webhook_url` — mirroring `UntrustedIngressError`'s precedent
    (Story 9.1): an ASGI server that renders a propagated exception as a
    DEBUG 500 would otherwise disclose the policy's internal shape to the
    very caller that was just refused.
    """


def authorize_export(
    *,
    identity: str | None,
    role: str | None,
    policy: ExportPolicy,
    logger: logging.Logger | None = None,
) -> None:
    """CAP-5: the ONLY place the export-authorization decision is made.

    Returns `None` with no logging and no webhook call when `role` is in
    `policy.allowed_roles`. Otherwise — including `role is None`, CAP-1's
    degrade-to-unprivileged case — logs a security-event WARNING, attempts
    one best-effort, HMAC-signed webhook POST if `policy.webhook_url` is set
    (any failure or SSRF-shaped refusal caught and logged, never suppressing
    or delaying the raise), and raises `ExportUnauthorizedError`.

    `identity` is included in the WARNING log line and the webhook payload —
    unlike `UntrustedIngressError`'s exception message (which an untrusted
    caller can potentially observe via a DEBUG 500), neither of those
    surfaces is caller-facing: the log is operator-facing and the webhook
    only ever reaches the adopter's own configured receiver, and a security
    event with no actor is not actionable.
    """
    if role is not None and role in policy.allowed_roles:
        return None

    log = logger or logging.getLogger(_SECURITY_LOGGER_NAME)
    log.warning(
        "export refused: identity=%r role=%r is not authorized by this export policy",
        identity,
        role,
    )

    if policy.webhook_url is not None:
        _post_refusal_webhook(policy, identity=identity, role=role, log=log)

    if role is None:
        raise ExportUnauthorizedError("export refused: no role was resolved for this request")
    raise ExportUnauthorizedError(f"export refused: role {role!r} is not authorized")


def _post_refusal_webhook(policy: ExportPolicy, *, identity: str | None, role: str | None, log: logging.Logger) -> None:
    """Best-effort, HMAC-signed POST of a minimal refusal event — never raises.

    The payload is deliberately minimal: no `allowed_roles` or other policy
    internals, for the same reason `UntrustedIngressError` never echoes the
    declared ingress list — an event payload should carry what a receiver
    needs to act on, not a dump of the declaration.

    Two fail-closed guards run before anything is sent (DW-9-4-3/DW-9-4-4):
    the resolved target must not be blocked (checked fresh here, not only
    at `ExportPolicy` construction — see `_webhook_target_is_blocked`), and
    a shared HMAC secret must be configured. Either guard failing, a
    network error, a timeout, or any other unexpected error building the
    request is caught and logged as a secondary warning; none of them may
    suppress or delay the refusal `authorize_export` raises after calling
    this.
    """
    webhook_url = policy.webhook_url
    assert webhook_url is not None  # only called when a webhook is configured
    try:
        hostname = urlparse(webhook_url).hostname
        assert hostname is not None  # already required by __post_init__
        if not policy.allow_private_webhook_targets and _webhook_target_is_blocked(hostname):
            log.warning(
                "export-refusal webhook POST to %r refused: %r resolves to "
                "a loopback/link-local/private/reserved address",
                webhook_url,
                hostname,
            )
            return
        secret = resolve_webhook_secret()
        payload = json.dumps(
            {
                "event": "export_refused",
                "identity": identity,
                "role": role,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        ).encode("utf-8")
        signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        request = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                _SIGNATURE_HEADER: f"{_SIGNATURE_PREFIX}{signature}",
            },
            method="POST",
        )
        urllib.request.urlopen(request, timeout=_WEBHOOK_TIMEOUT_SECONDS)
    except Exception:
        log.warning("export-refusal webhook POST to %r failed", webhook_url, exc_info=True)


def maybe_encrypt_export(path: str | Path, policy: ExportPolicy, *, output: str | Path) -> Path:
    """CAP-5's optional-encryption half — wraps Story 1.3's `keys.encrypt_file`.

    Returns `Path(path)` unchanged, performing no encryption, when
    `policy.encryption_recipient is None`. Otherwise encrypts `path` to
    `output` via `keys.encrypt_file` and returns `Path(output)`; a
    `subprocess.CalledProcessError` from a malformed recipient or a missing
    `age` binary propagates unmodified, matching `encrypt_file`'s own
    contract.

    `output` must differ from `path` (Edge Case Hunter): `encrypt_file` shells
    to `age --output <out> -- <in>`, and nothing guarantees `age` fully reads
    the input before it opens the output for writing -- with `output == path`
    that write could truncate the plaintext export while `age` is still
    reading it, corrupting the only copy rather than producing a second
    encrypted one.
    """
    if policy.encryption_recipient is None:
        return Path(path)
    if Path(path) == Path(output):
        raise ValueError(
            f"maybe_encrypt_export: output {output!r} must differ from path "
            f"{path!r} — encrypting a file onto itself risks truncating the "
            f"plaintext while `age` is still reading it"
        )
    encrypt_file(path, recipient=policy.encryption_recipient, output=output)
    return Path(output)
