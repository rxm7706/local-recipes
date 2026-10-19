"""The one opt-in switch every credentialed fetch reads, and the auth built from a credential
for its own host only (Story 35.1, spec-pyforge-atlas CAP-65; AD-2, AD-11).

A request that carries a credential runs only when the operator sets
``PYFORGE_ATLAS_CREDENTIALED=1`` for the run. The switch is read at the moment a dataset would
fetch, never at import: Dagster builds every dataset when it imports the definitions, long
before a run decides whether it is credentialed. ``pyforge.atlas.live_vcs_universe`` gates the
new behaviour; OFF, a dataset keeps the path it had before this story.

No ``requests`` import (the no-inline-IO scan): requests calls any callable ``auth`` with the
prepared request, so :class:`BearerAuth` is a plain class.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlsplit

from pyforge.core.flags import read_boolean

SWITCH = "PYFORGE_ATLAS_CREDENTIALED"
FLAG_KEY = "pyforge.atlas.live_vcs_universe"
GITHUB_API_HOST = "api.github.com"


def credentialed() -> bool:
    """Whether the operator set ``PYFORGE_ATLAS_CREDENTIALED=1`` for this run (exactly ``1``)."""
    return os.environ.get(SWITCH, "") == "1"


def live_vcs_universe() -> bool:
    """Whether Epic 35's behaviour is on. ``False`` when the flag tree is missing or unreadable."""
    return read_boolean(FLAG_KEY, default=False)


def token_of(credentials: Any) -> str | None:
    """The token a catalog credential carries: ``{token: ...}`` (``github_token``) or a bare
    string. Anything else (a ``[user, password]`` pair, an empty value) is no token."""
    value = credentials.get("token") if isinstance(credentials, dict) else credentials
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


class BearerAuth:
    """A requests ``auth`` callable: ``Authorization: Bearer <token>``, set only on a request to
    ``host``. A redirect to another host drops it (requests' ``rebuild_auth`` never re-applies a
    callable auth). The token never appears in ``repr``."""

    def __init__(self, token: str, host: str) -> None:
        self._token = token
        self.host = host

    def __call__(self, request: Any) -> Any:
        if urlsplit(request.url).hostname == self.host:
            request.headers["Authorization"] = f"Bearer {self._token}"
        return request

    def __repr__(self) -> str:
        return f"BearerAuth(host={self.host!r})"


def github_auth(credentials: Any, url: str) -> BearerAuth | None:
    """Bearer auth for a GitHub API ``url``, or ``None``: the switch is off, there is no token, or
    ``url`` is not on ``api.github.com`` (an override to another host never receives the token)."""
    if not credentialed():
        return None
    token = token_of(credentials)
    if token is None or urlsplit(url).hostname != GITHUB_API_HOST:
        return None
    return BearerAuth(token, GITHUB_API_HOST)


def skip_reason(url: str) -> str:
    """The staleness reason a credentialed store records when it sends nothing (no secret)."""
    if not credentialed():
        return f"credentialed fetch not run: {SWITCH} is not 1 -- keeping last-good"
    host = urlsplit(url).hostname
    if host != GITHUB_API_HOST:
        return f"credentialed fetch not run: {host!r} is not {GITHUB_API_HOST} -- keeping last-good"
    return "credentialed fetch not run: no github_token -- keeping last-good"
