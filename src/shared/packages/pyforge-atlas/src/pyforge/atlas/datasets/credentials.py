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
import re
from typing import Any
from urllib.parse import urlsplit

from pyforge.core.flags import read_boolean

SWITCH = "PYFORGE_ATLAS_CREDENTIALED"
FLAG_KEY = "pyforge.atlas.live_vcs_universe"
GITHUB_API_HOST = "api.github.com"
# a token is printable ASCII with no space or control character: a newline inside one would make
# http.client refuse the header with an error that quotes the header, token included
_TOKEN = re.compile(r"[\x21-\x7e]+")


def credentialed() -> bool:
    """Whether the operator set ``PYFORGE_ATLAS_CREDENTIALED=1`` for this run (exactly ``1``)."""
    return os.environ.get(SWITCH, "") == "1"


def live_vcs_universe() -> bool:
    """Whether Epic 35's behaviour is on. ``False`` when the flag tree is missing or unreadable."""
    return read_boolean(FLAG_KEY, default=False)


def token_of(credentials: Any) -> str | None:
    """The token a catalog credential carries: ``{token: ...}`` (``github_token``) or a bare
    string, without surrounding whitespace. Anything else (a ``[user, password]`` pair, an empty
    value, a value with a space or control character inside) is no token."""
    value = credentials.get("token") if isinstance(credentials, dict) else credentials
    if isinstance(value, str) and _TOKEN.fullmatch(value.strip()):
        return value.strip()
    return None


def _https_on(url: str, host: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == "https" and parts.hostname == host


class BearerAuth:
    """A requests ``auth`` callable: ``Authorization: Bearer <token>``, set only on an https request
    to ``host``. A redirect to another host drops it (requests' ``rebuild_auth`` never re-applies a
    callable auth). The token never appears in ``repr``."""

    def __init__(self, token: str, host: str) -> None:
        self._token = token
        self.host = host

    def __call__(self, request: Any) -> Any:
        if _https_on(request.url, self.host):
            request.headers["Authorization"] = f"Bearer {self._token}"
        return request

    def __repr__(self) -> str:
        return f"BearerAuth(host={self.host!r})"


def github_auth(credentials: Any, url: str) -> BearerAuth | None:
    """Bearer auth for a GitHub API ``url``, or ``None``: the switch is off, there is no token, or
    ``url`` is not https on ``api.github.com`` (an override to another host never receives the
    token, and neither does plain http)."""
    if not credentialed():
        return None
    token = token_of(credentials)
    if token is None or not _https_on(url, GITHUB_API_HOST):
        return None
    return BearerAuth(token, GITHUB_API_HOST)


def skip_reason(url: str) -> str:
    """The staleness reason a credentialed store records when it sends nothing (no secret)."""
    if not credentialed():
        return f"credentialed fetch not run: {SWITCH} is not 1 -- keeping last-good"
    if not _https_on(url, GITHUB_API_HOST):
        parts = urlsplit(url)
        return (
            f"credentialed fetch not run: {parts.scheme}://{parts.hostname} is not https://{GITHUB_API_HOST}"
            " -- keeping last-good"
        )
    return "credentialed fetch not run: no github_token -- keeping last-good"
