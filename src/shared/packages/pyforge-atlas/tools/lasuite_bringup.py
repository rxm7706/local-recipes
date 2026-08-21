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

**A bring-up that pushed nothing -- or that never reached the CMS -- is NEVER a success.** The
attended checklist closes DW-H3 on this script's word, so :func:`main` guards the report at BOTH
ends and then proves reachability:

* it refuses to run at all when the resolved wiki root has no ``outputs/`` stage (a typo'd
  ``ATLAS_WIKI_ROOT`` must fail loudly, not silently scaffold a fresh empty tree at the wrong
  path) -- exit ``3``;
* it refuses to report success when the sync touched zero pages -- exit ``3``;
* and, because :class:`~pyforge.atlas.factory.lasuite.SyncReport`'s ``skipped`` is defined as
  "unchanged -- NO remote call made", an ALL-SKIPPED run satisfies both of those while contacting
  the CMS exactly zero times. So :func:`main` additionally calls
  :meth:`~pyforge.atlas.factory.lasuite.LaSuiteClient.list_documents` once, after the sync and
  before returning ``0`` -- exit ``0`` is unreachable without genuine CMS contact. (Verified
  before this probe existed: pointed at a DEAD endpoint with a populated ``.lasuite_sync.json``
  the script printed ``created=0 updated=0 skipped=1`` and exited **0** with a success banner.)

An all-skipped run is otherwise a legitimate PASS -- it is exactly the idempotency the attended
checklist's steps 5 and 7 exist to observe -- so this script deliberately does NOT fail when
``created + updated == 0``. ``scaffold_wiki`` is kept for the surviving case (root exists,
``raw/``/``compiled/`` may not); it is a convenience, never a guard.

Usage (attended bring-up)::

    export LASUITE_BASE_URL=<real base url>
    export LASUITE_API_TOKEN=<minted token>
    pixi run -e pyforge-atlas python src/shared/packages/pyforge-atlas/tools/lasuite_bringup.py

The ``pixi run -e pyforge-atlas`` prefix is REQUIRED: ``tools/`` is not packaged into the wheel,
so outside that env both ``import httpx`` and ``from pyforge.atlas.factory.lasuite import ...``
fail, and no install makes the bare ``python <path>`` form work.

Exit codes:

* ``0`` -- success: at least one page was created/updated/skipped AND the CMS answered a live
  ``list_documents()`` probe; the resolved base URL and wiki root are echoed so the operator can
  see what the script actually talked to.
* ``1`` -- unconfigured: ``LASUITE_BASE_URL`` and/or ``LASUITE_API_TOKEN`` missing.
* ``2`` -- a :class:`~pyforge.atlas.factory.lasuite.LaSuiteError`: transport failure (connection
  refused, timeout, malformed base URL), a redirected write, a non-2xx CMS response, a corrupt
  sync mapping, or a failed reachability probe. Also covers a ``ValueError`` out of the
  ``httpx.Client`` constructor (an ambient ``HTTP_PROXY`` with an unsupported scheme).
* ``3`` -- nothing was synced: either the resolved wiki root has no ``outputs/`` directory (checked
  BEFORE anything is created) or the sync reported ``created+updated+skipped == 0``. NOT a pass.
* ``4`` -- the wiki tree is unreadable/unwritable, or a page is not valid UTF-8.
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
    re-opened (a fresh TCP/TLS handshake) per call. ``follow_redirects=True`` because
    :class:`~pyforge.atlas.factory.lasuite.Response` carries only ``status_code`` + ``body`` and
    DROPS headers: an unfollowed 3xx (an http->https upgrade in front of a real La Suite) would
    reach the operator as a bare, undebuggable ``HTTP 301: ''`` with the ``Location`` already
    discarded. Following is necessary but NOT sufficient for writes -- httpx rewrites POST/PATCH
    to GET on 301/302/303 and drops the body, which would silently turn a create into a list and
    surface as a *different* misleading error -- so a redirected non-GET raises a clear
    :class:`LaSuiteError` naming the chain instead.

    Transport failures are wrapped into :class:`LaSuiteError` naming the method/URL, so they
    surface through the same error-clarity contract as every other ``LaSuiteError``, never a raw
    ``httpx`` traceback. ``httpx.InvalidURL`` is listed explicitly because it is NOT an
    ``httpx.HTTPError`` subclass (httpx 0.28.1 MRO: ``InvalidURL -> Exception``) -- without it a
    typo'd ``LASUITE_BASE_URL`` escapes both this handler and :func:`main`'s and produces exactly
    the traceback this wrapper exists to prevent.

    ``trust_env`` is deliberately left at its ``True`` default: the attended enterprise bring-up
    legitimately needs the proxy / ``SSL_CERT_FILE`` env chain. Keeping the OFFLINE gate
    env-independent is the rehearsal FIXTURE's job, never the opener's.
    """
    client = httpx.Client(timeout=timeout, follow_redirects=True)

    def _opener(request: Request) -> Response:
        try:
            resp = client.request(
                request.method, request.url, headers=request.headers, json=request.json
            )
        except (httpx.HTTPError, httpx.InvalidURL, UnicodeError) as exc:
            raise LaSuiteError(
                f"{request.method} {request.url} -> transport error: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if resp.history and request.method.upper() != "GET":
            # httpx rewrites POST/PATCH to GET on 301/302/303 and drops the body, so the write
            # never happened even though the final response is a 2xx. The operator must see this
            # verbatim -- Response carries no headers, so nothing downstream can express it.
            chain = " -> ".join(str(r.url) for r in resp.history)
            raise LaSuiteError(
                f"{request.method} {request.url} was REDIRECTED to {resp.url} "
                f"(chain: {chain} -> {resp.url}); httpx rewrites a redirected POST/PATCH to GET "
                "and drops the body, so this WRITE did not happen. Point "
                f"{LASUITE_BASE_URL_ENV} at the final URL (usually the https:// form) instead."
            )
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

    root = _resolve_wiki_root()
    outputs = root / "outputs"
    if not outputs.is_dir():
        # BEFORE anything is created: a typo'd ATLAS_WIKI_ROOT must fail loudly here rather than
        # scaffold a fresh empty tree at the wrong path and then "succeed" having pushed nothing.
        print(
            f"lasuite_bringup: NOTHING TO PUSH -- no outputs/ stage at {outputs} "
            f"(wiki root resolved to {root}; set {_WIKI_ROOT_ENV} to point at the real wiki). "
            "Nothing was created and no request was made -- this is NOT a pass.",
            file=sys.stderr,
        )
        return 3

    try:
        # build_httpx_opener() is INSIDE the block: an ambient HTTP_PROXY with an unsupported
        # scheme makes the httpx.Client CONSTRUCTOR raise ValueError, which would otherwise
        # escape main() and exit 1 -- colliding with the documented "unconfigured" code.
        client = LaSuiteClient(config, opener=build_httpx_opener())
        # WikiSyncer construction AND sync_all() share this block: a corrupt
        # .lasuite_sync.json raises LaSuiteError from __init__, not just sync_all().
        syncer = WikiSyncer(client, scaffold_wiki(root))
        report = syncer.sync_all()
        if report.total == 0:
            # AFTER the sync: zero pages proved nothing, and the attended checklist's step 8
            # closes DW-H3 on this script's word -- never report that as a success.
            print(
                f"lasuite_bringup: SYNCED ZERO PAGES -- wiki root {root}, base URL "
                f"{config.base_url}. A bring-up that pushed nothing proves nothing -- "
                "this is NOT a pass.",
                file=sys.stderr,
            )
            return 3
        # Reachability probe -- the guard neither of the two above can be: `skipped` means
        # "unchanged, NO remote call made", so an all-skipped run satisfies both while never
        # touching the CMS. One live GET makes exit 0 unreachable without genuine CMS contact
        # (and is list_documents()'s only real-HTTP exercise). Deliberately NOT a
        # `created+updated == 0` check: the checklist's steps 5 and 7 expect all-skipped PASSES.
        client.list_documents()
    except LaSuiteError as exc:
        print(f"lasuite_bringup: FAILED -- {exc}", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as exc:
        # Ordered BEFORE the ValueError handler: UnicodeDecodeError IS a ValueError subclass.
        print(
            f"lasuite_bringup: FAILED -- the wiki tree at {root} is unreadable/unwritable or "
            f"holds a non-UTF-8 page ({type(exc).__name__}: {exc}).",
            file=sys.stderr,
        )
        return 4
    except ValueError as exc:
        print(
            f"lasuite_bringup: FAILED -- could not build the HTTP client "
            f"({type(exc).__name__}: {exc}); check the proxy env "
            "(HTTP_PROXY/HTTPS_PROXY/ALL_PROXY) this shell exports.",
            file=sys.stderr,
        )
        return 2

    print(f"lasuite_bringup: base_url={config.base_url} wiki_root={root}")
    print(
        f"created={len(report.created)} updated={len(report.updated)} "
        f"skipped={len(report.skipped)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
