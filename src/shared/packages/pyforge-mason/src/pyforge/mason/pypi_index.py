"""`pypi_index.py` -- PyPI JSON-index interrogation for idempotent shipping
(Story 3.7, FR-18, AD-10).

`ship_pypi` (Story 3.4) always attempted a `twine upload`; a retry of a ship
that had already succeeded either crashed on PyPI's own duplicate-file
rejection or silently re-uploaded (spec Intent). This module answers the
question `ship_pypi` needs answered BEFORE it decides whether to upload at
all: "does PyPI already have this exact name/version?" -- by querying PyPI's
own public JSON index directly, `GET https://pypi.org/pypi/<name>/
<version>/json`, rather than guessing from a local cache (AD-10 forbids any
local persistence of an interrogation result; every ship pays its own query
round-trip, D-11's accepted tradeoff).

The ONE module under `pyforge/mason/` permitted to import `urllib.request`
(`tests/meta/test_credential_isolation.py`'s Guard 2, own docstring: "Epic 3
is expected to add scoped, non-CFE HTTP capability later and must loosen
this guard explicitly when that story lands" -- this story is the one doing
so, via a narrow per-(file, module-name) allowlist keyed on this exact
filename, not a blanket widening of the guard). `requests`/`httpx`/
`http.client` stay BANNED here too (spec Always boundary) -- PyPI's own
public JSON index needs nothing beyond a bare, unauthenticated GET, which
`urllib.request.urlopen` already does with zero extra dependencies; there is
no legitimate reason for a third-party HTTP client to appear in this module
either.

No credential of any kind is ever read, sent, or even considered here: PyPI's
own JSON index is a fully public, unauthenticated endpoint (unlike the
`twine upload` this module exists to make idempotent), so this module carries
none of `engines.twine`/`engines.pixi`'s own AD-14 credential-inheritance
machinery -- there is simply no credential to inherit.

`version_exists(name, version, *, timeout=None) -> bool | None`'s three-way
outcome (AD-10: "never an assumption in either direction"): a `200` response
means the exact `name`/`version` combination already exists on PyPI ->
`True`; a `404` (`HTTPError.code == 404`) means it conclusively does not ->
`False`; anything else -- a non-404 `HTTPError`, a `URLError` (DNS failure,
connection refused), a bare `OSError`, or a `TimeoutError` (the `timeout=`
kwarg on `urlopen` itself expiring) -- means the question could not be
answered at all -> `None`. `package.py::ship_pypi` never attempts the
mutating `twine upload` call when this returns `None` -- an undeterminable
interrogation is never silently treated as "not shipped yet" (nor as
"already shipped").
"""

from __future__ import annotations

import urllib.error
import urllib.request

_PYPI_JSON_INDEX_URL_TEMPLATE = "https://pypi.org/pypi/{name}/{version}/json"
"""PyPI's own public, unauthenticated per-release JSON endpoint -- returns
`200` with a JSON body when `name`/`version` exists, `404` when it does not.
Never parsed here: only the HTTP status code this module's own `urlopen`
call raises or does not raise is consulted (module docstring); the response
BODY is discarded, unread."""

_VERSION_EXISTS_TIMEOUT_SECONDS = 30.0
"""A single small JSON metadata GET, not an upload or a from-source build --
mirrors `engines.gh._GH_PR_LIST_TIMEOUT_SECONDS`'s own identical rationale
and value (both are the "index/metadata interrogation" tier this story
adds, distinct from `engines.twine.upload`/`engines.pixi.upload`'s own 300s
allowance for a real file transfer)."""


def version_exists(name: str, version: str, *, timeout: float | None = None) -> bool | None:
    """Query PyPI's own public JSON index for `name`==`version` (Story 3.7,
    FR-18, AD-10) -- see module docstring for the full three-way outcome and
    why this module alone is permitted to import `urllib.request`.

    `timeout` defaults to `_VERSION_EXISTS_TIMEOUT_SECONDS` when `None`,
    mirroring every engine adapter's own per-operation-default convention
    (`engines.pixi.search`, `engines.gh.find_open_pr`, both added by this
    same story). Never raises: a timeout, a DNS failure, a connection
    refusal, or any HTTP status other than `200`/`404` all fold into `None`
    (module docstring) -- this function reports what it could determine,
    and the caller decides what an undeterminable answer means for its own
    ship attempt.
    """
    resolved_timeout = timeout if timeout is not None else _VERSION_EXISTS_TIMEOUT_SECONDS
    url = _PYPI_JSON_INDEX_URL_TEMPLATE.format(name=name, version=version)
    try:
        with urllib.request.urlopen(url, timeout=resolved_timeout):
            return True
    except urllib.error.HTTPError as exc:
        return False if exc.code == 404 else None
    except urllib.error.URLError, OSError, TimeoutError:
        return None
