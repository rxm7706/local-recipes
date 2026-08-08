"""Operator role verification for write subcommands (Story 6.3, AD-16).

AD-16's rule: write operations (``herald success publish``, ``herald notice
author``, and a future ``herald progress --update``) require the
``operator`` role; read operations (``herald progress`` with no write flag)
are public and never call this module at all. This module is the one gate
every write-subcommand handler in ``cli.py`` calls *before* running its own
logic (a middleware pattern, not a per-command ad-hoc check) -- so adding a
Moment 5 write subcommand later reuses this gate rather than reinventing it.

**Scope boundary (explicit, per this story's own AC):** this module answers
"is there a verified operator role for this call?" and nothing else. It does
not verify a Herald web session, does not mint or refresh a credential, and
does not implement any Moment's actual write logic (publishing a claim is
Epic 9's scope; authoring a notice is Epic 10's). A caller past this gate
gets only "authorized, would proceed" today.

**Auth sources, checked in this order** (mirrors the story's own AC
wording: "``HERALD_TOKEN`` env var or ``~/.herald/config``"):

1. ``HERALD_TOKEN`` env var -- format ``<role>:<opaque-token>`` (a single
   ``:`` splits the two). This is deliberately not "any non-empty value
   grants the operator role": a stub that treated *presence* of the env var
   as sufficient would be a trivial bypass (``export HERALD_TOKEN=x``) and
   could never represent a caller with a *different* role either, which the
   AC's "user without operator role" scenario requires being distinguishable
   from "no auth context at all". A value with no ``:`` is malformed --
   treated the same as no auth context (never guessed at as a role).
2. ``~/.herald/config`` (overridable via ``config_path=`` for tests) -- a
   JSON object with a ``role`` field, e.g. ``{"role": "operator"}``. A
   missing file, an unreadable/malformed file, or a file with no string
   ``role`` field all resolve to "no auth context" (``None``) -- never
   raised, since "no auth context" is itself a normal, AC-covered outcome,
   not a Herald-internal failure.

Real credential verification (signature checks, session validation against
a live Herald backend) is out of scope for this stub, same as the write
logic it gates -- ``[ASSUMPTION]`` in AD-16 notes the backend integration is
still to be confirmed with the ops team.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .errors import OperatorAuthorizationError

logger = logging.getLogger(__name__)

OPERATOR_ROLE = "operator"
"""The one role AD-16 gates write operations on."""

TOKEN_ENV_VAR = "HERALD_TOKEN"

DEFAULT_CONFIG_PATH = Path.home() / ".herald" / "config"


@dataclass(frozen=True)
class AuthContext:
    """A resolved auth source: the role it claims, and where it came from
    (for the audit log -- never the token itself, which is not retained
    past parsing)."""

    role: str
    source: str


def resolve_auth_context(*, config_path: Path | None = None) -> AuthContext | None:
    """The caller's ``AuthContext``, or ``None`` when neither auth source
    resolves to one -- "no auth context found" per the AC, not an error.

    Checked in order: ``HERALD_TOKEN`` env var, then ``config_path`` (or
    ``DEFAULT_CONFIG_PATH`` when omitted, e.g. in production; tests always
    pass an explicit ``config_path`` under ``tmp_path`` so this call can
    never read a developer's real ``~/.herald/config``)."""
    raw_token = os.environ.get(TOKEN_ENV_VAR)
    if raw_token:
        role, sep, _opaque = raw_token.partition(":")
        if sep and role:
            return AuthContext(role=role, source=f"env:{TOKEN_ENV_VAR}")
        logger.info(
            "%s is set but not in '<role>:<token>' form; ignoring", TOKEN_ENV_VAR
        )

    path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.info("%s is not valid JSON; ignoring", path)
        return None
    role = data.get("role") if isinstance(data, dict) else None
    if not isinstance(role, str) or not role:
        return None
    return AuthContext(role=role, source=f"file:{path}")


def require_operator_role(context: AuthContext | None, *, action: str) -> AuthContext:
    """The write-gate middleware: raises ``OperatorAuthorizationError`` (AD-
    16) unless ``context`` is a verified ``operator``; returns ``context``
    unchanged otherwise, so a caller can chain it inline
    (``ctx = require_operator_role(resolve_auth_context(), action=...)``).

    Every check -- pass or refuse -- is logged at INFO for the audit trail
    the story's implementation notes ask for; the token itself is never
    logged (``AuthContext`` never carries it past ``resolve_auth_context``)."""
    if context is None:
        logger.info("auth check for %s: no auth context found", action)
        raise OperatorAuthorizationError(
            "auth context missing. Configure with `herald auth login` or "
            "set HERALD_TOKEN env var"
        )
    if context.role != OPERATOR_ROLE:
        logger.info(
            "auth check for %s: role %r (source %s) is not %r",
            action,
            context.role,
            context.source,
            OPERATOR_ROLE,
        )
        raise OperatorAuthorizationError(
            f"unauthorized: operator role required (found role {context.role!r})"
        )
    logger.info("auth check for %s: authorized (source %s)", action, context.source)
    return context


def confirm(prompt: str, *, reader: Callable[[str], str] = input) -> bool:
    """A ``"Continue? [Y/n]"``-shaped confirmation prompt for a write
    subcommand. Defaults to blank/'y'/'yes' (case-insensitive) as
    confirmed; anything else declines. ``reader`` is injectable so a test
    never has to block on real stdin (mirrors this package's existing
    injectable-seam convention, e.g. ``deck_pipeline.LocalProver``)."""
    try:
        answer = reader(prompt)
    except EOFError:
        return False
    return answer.strip().lower() in ("", "y", "yes")
