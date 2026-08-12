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
  is configured, announced to it via one best-effort POST — a webhook failure
  is caught and logged but never suppresses or delays the raised refusal.
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
`datetime`, `pathlib`) plus the sibling `pyforge.steward.keys` import — so
this module works with or without the `[dashboard]` extra installed, same as
`middleware.py`/`declarations.py`.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from pyforge.steward.keys import encrypt_file

_SECURITY_LOGGER_NAME = "pyforge.steward.dashboard.security"
_WEBHOOK_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class ExportPolicy:
    """CAP-5: the role vocabulary an export is gated on, plus its two opt-ins.

    ``allowed_roles`` is the closed set of role names `authorize_export`
    checks a resolved role against — independent of, and never
    cross-validated against, `AccessDeclaration.roles` (see this module's
    docstring). ``webhook_url``, if declared, is where a refusal is
    announced. ``encryption_recipient``, if declared, is the `age` public key
    `maybe_encrypt_export` encrypts the produced artifact to. This class does
    not perform authorization or encryption itself — it is the statement an
    adopter makes instead of hand-wiring either.
    """

    allowed_roles: tuple[str, ...]
    webhook_url: str | None = None
    encryption_recipient: str | None = None

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

        if self.webhook_url is not None:
            if not isinstance(self.webhook_url, str):
                raise TypeError(
                    f"ExportPolicy.webhook_url must be a string or None, got "
                    f"{type(self.webhook_url).__name__}"
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
    one best-effort webhook POST if `policy.webhook_url` is set (any failure
    caught and logged, never suppressing or delaying the raise), and raises
    `ExportUnauthorizedError`.

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
        "export refused: identity=%r role=%r is not authorized by this "
        "export policy",
        identity,
        role,
    )

    if policy.webhook_url is not None:
        _post_refusal_webhook(policy.webhook_url, identity=identity, role=role, log=log)

    if role is None:
        raise ExportUnauthorizedError("export refused: no role was resolved for this request")
    raise ExportUnauthorizedError(f"export refused: role {role!r} is not authorized")


def _post_refusal_webhook(
    webhook_url: str, *, identity: str | None, role: str | None, log: logging.Logger
) -> None:
    """Best-effort POST of a minimal refusal event — never raises.

    The payload is deliberately minimal: no `allowed_roles` or other policy
    internals, for the same reason `UntrustedIngressError` never echoes the
    declared ingress list — an event payload should carry what a receiver
    needs to act on, not a dump of the declaration. Any failure (network
    error, timeout, an unexpected error building the request) is caught and
    logged as a secondary warning; it must never suppress or delay the
    refusal `authorize_export` raises after calling this.
    """
    try:
        payload = json.dumps(
            {
                "event": "export_refused",
                "identity": identity,
                "role": role,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(request, timeout=_WEBHOOK_TIMEOUT_SECONDS)
    except Exception:
        log.warning(
            "export-refusal webhook POST to %r failed", webhook_url, exc_info=True
        )


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
