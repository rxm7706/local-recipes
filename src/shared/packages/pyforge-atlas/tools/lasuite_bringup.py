#!/usr/bin/env python3
"""The real httpx-backed La Suite / Wagtail bring-up script (Story 16.2, CAP-2/CAP-3).

``factory/lasuite.py``'s sole network seam (``Opener``) has, until now, only ever been driven
by an in-memory ``MockWagtail`` (``tests/factory/test_lasuite.py``). This script supplies the
LIVE half: :func:`build_httpx_opener` constructs a real ``httpx``-backed opener, and :func:`main`
wires it into a :class:`~pyforge.atlas.factory.lasuite.LaSuiteClient` and runs a
:class:`~pyforge.atlas.factory.lasuite.WikiSyncer` over it -- the exact same create/update/
idempotent-skip/resume contract ``test_lasuite.py`` proves against the mock, now over real HTTP.

This is the ONE code path both this story's offline loopback rehearsal
(``tests/factory/test_lasuite_live_rehearsal.py``, which imports :func:`build_httpx_opener`
directly via ``importlib``) and the later ATTENDED DW-H3 bring-up run -- only
``LASUITE_BASE_URL``/``LASUITE_API_TOKEN`` differ between the two. No separate "real"
implementation may be written later (spec Boundaries & Constraints).

Lives under ``tools/`` -- OUTSIDE ``src/pyforge/atlas/**`` -- deliberately: the no-inline-IO scan
(``tests/catalog/test_no_inline_io.py``) denylists ``httpx`` in package code with no exemption
route (AC-2: package code holds no HTTP client), and ``factory/lasuite.py`` stays frozen. Mirrors
the existing ``tools/normalize_viz_build.py`` precedent (invoked directly via
``python tools/<script>.py``, never packaged/importable).

**Why the wiki root is resolved here, not via ``orchestration/definitions.py::resolve_wiki_root``.**
That module executes ``defs = build_definitions()`` -- a full Dagster/Kedro
``KedroProjectTranslator`` build -- as its own last top-level statement, so importing ANYTHING
from it (even the 3-line env lookup) pulls in that ~2.6s build as a side effect. This script
inlines the identical env-lookup logic instead (:func:`_resolve_wiki_root`), so both this story's
rehearsal and the attended bring-up stay fast and decoupled from an unrelated subsystem.

Usage (attended bring-up)::

    export LASUITE_BASE_URL=<real base url>
    export LASUITE_API_TOKEN=<minted token>
    python src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py

Exit codes: ``0`` success, ``1`` unconfigured (missing base URL / token), ``2`` a ``LaSuiteError``
(transport failure, non-2xx response, or a corrupt sync mapping).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

from pyforge.atlas.factory.lasuite import (
    LASUITE_BASE_URL_ENV,
    LASUITE_TOKEN_ENV,
    LaSuiteClient,
    LaSuiteError,
    Opener,
    Request,
    Response,
    WikiSyncer,
    resolve_lasuite_config,
)
from pyforge.atlas.factory.wiki import scaffold_wiki


def build_httpx_opener(*, timeout: float = 30.0) -> Opener:
    """Build a real httpx-backed :data:`~pyforge.atlas.factory.lasuite.Opener`.

    ONE ``httpx.Client`` is constructed and reused for every request this opener makes -- not
    re-opened (a fresh TCP/TLS handshake) per call. Transport failures (connection refused,
    timeout -- the single most likely failure mode of the ATTENDED live bring-up) are wrapped
    into :class:`LaSuiteError` naming the method/URL, so they surface through the same
    error-clarity contract as every other ``LaSuiteError``, never a raw ``httpx`` traceback.
    """
    client = httpx.Client(timeout=timeout)

    def _opener(request: Request) -> Response:
        try:
            resp = client.request(
                request.method, request.url, headers=request.headers, json=request.json
            )
        except httpx.HTTPError as exc:
            raise LaSuiteError(
                f"{request.method} {request.url} -> transport error: {exc}"
            ) from exc
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        return Response(status_code=resp.status_code, body=body)

    return _opener


# --- wiki root resolution (inlined -- see module docstring for why) --------------------------

_WIKI_ROOT_ENV = "ATLAS_WIKI_ROOT"
# tools/../ == the pyforge-atlas project root -- identical to what
# orchestration/definitions.py's PROJECT_PATH resolves to (parents[4] from that deeper file).
_PROJECT_PATH = Path(__file__).resolve().parents[1]


def _resolve_wiki_root() -> Path:
    override = (os.environ.get(_WIKI_ROOT_ENV) or "").strip()
    return Path(override) if override else (_PROJECT_PATH / "wiki")


def main() -> int:
    config = resolve_lasuite_config()
    if config is None:
        print(
            f"lasuite_bringup: not configured -- export {LASUITE_BASE_URL_ENV} and "
            f"{LASUITE_TOKEN_ENV} first.",
            file=sys.stderr,
        )
        return 1

    client = LaSuiteClient(config, opener=build_httpx_opener())
    try:
        # WikiSyncer construction AND sync_all() share this block: a corrupt
        # .lasuite_sync.json raises LaSuiteError from __init__, not just sync_all().
        syncer = WikiSyncer(client, scaffold_wiki(_resolve_wiki_root()))
        report = syncer.sync_all()
    except LaSuiteError as exc:
        print(f"lasuite_bringup: FAILED -- {exc}", file=sys.stderr)
        return 2

    print(
        f"created={len(report.created)} updated={len(report.updated)} "
        f"skipped={len(report.skipped)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
