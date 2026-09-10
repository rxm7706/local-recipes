"""Live Artifactory HTTP transport for the attended, credentialed run Story
25.2 needs (Story 25.4).

Deliberately NOT inside ``src/pyforge/atlas/``: that whole package tree is
scanned by ``tests/unit/catalog/test_no_inline_io.py``'s ``IO_DENYLIST``,
which bans ``requests``/``urllib3``/``httpx``/etc. anywhere in package code
(``ArtifactoryConfig``'s own docstring: "the concrete HTTP client is
constructed OUTSIDE package code"). ``tools/`` is the established sibling
location for attended-operator scripts (mirrors ``tools/bootstrap.py``).

Auth resolution mirrors ``.claude/skills/conda-forge-expert/scripts/_http.py``'s
existing JFrog convention exactly: an API key takes ``X-JFrog-Art-Api``;
username+password falls back to HTTP Basic. Credentials are never read from
``os.environ`` here -- the factory takes them as explicit arguments, so the
attended operator's own run site decides where they come from (typically
``os.environ`` at the call site, kept out of this module so importing it
never touches an env var).
"""

from __future__ import annotations

from base64 import b64encode

import requests
from pyforge.atlas.artifactory.aql_adapter import (
    AqlRequest,
    AqlResponse,
    AqlTransport,
    ArtifactoryAqlError,
)

_TIMEOUT_S = 30


def live_transport(
    base_url: str,
    *,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> AqlTransport:
    """Build a live :data:`AqlTransport` against a real Artifactory instance
    at ``base_url``. Exactly one of API-key or username+password auth must
    be supplied; neither raises :class:`ArtifactoryAqlError` naming which
    credential is missing, rather than silently attempting an unauthenticated
    call."""
    headers: dict[str, str] = {}
    if api_key:
        headers["X-JFrog-Art-Api"] = api_key
    elif username and password:
        creds = f"{username}:{password}"
        headers["Authorization"] = "Basic " + b64encode(creds.encode()).decode()
    else:
        raise ArtifactoryAqlError(
            "no Artifactory credentials supplied to live_transport(): pass "
            "either api_key= (JFROG_API_KEY), or both username= and "
            "password= (JFROG_USERNAME / JFROG_PASSWORD)"
        )

    def _transport(request: AqlRequest) -> AqlResponse:
        response = requests.request(
            request.method,
            f"{base_url.rstrip('/')}{request.url}",
            json=request.body,
            headers=headers,
            timeout=_TIMEOUT_S,
        )
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return AqlResponse(status_code=response.status_code, body=body)

    return _transport
