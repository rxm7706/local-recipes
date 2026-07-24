"""Fetches per-product cycle data from the endoflife.date API and writes it
into the on-disk cache layout ``feeds.py`` defines (Story 6.3).

Dev/ops-only maintenance script -- not part of the installed
``pyforge.warden`` package, and NEVER imported or invoked by ``scan``/
``CurrencyEngine``/anything in the installed package (NFR-S2: the ``scan``
runtime path opens no socket at any point). This script is the ENTIRE
"opt-in online" surface for currency-axis endoflife.date enrichment -- a
human runs it, on whatever cadence they choose, to (re)provision the cache
``currency.py`` later reads fully offline. Mirrors ``scripts/refresh_kev_
feed.py`` exactly, widened for endoflife.date's per-product (rather than
one-shot) API shape: there is no single "everything" endpoint, so this
script fetches one JSON document per product slug and aggregates them into
ONE cache document (``{product_slug: [cycle-record, ...]}``).

Uses stdlib ``urllib.request`` only -- no new dependency, mirrors
``scripts/refresh_kev_feed.py``'s/``scripts/generate_conda_pypi_map.py``'s
dev-only-script convention.

Usage::

    python scripts/refresh_endoflife_feed.py [--cache-dir <dir>] [--product SLUG ...]

Defaults ``--cache-dir`` to ``$PYFORGE_WARDEN_FEED_CACHE_DIR`` (the same env
var ``feeds.resolve_cache_dir`` reads at scan time) -- pass ``--cache-dir``
explicitly to provision a cache before that env var is even set. Defaults
``--product`` to every ``source: endoflife``/``source: heuristic-seed``
product slug in the bundled ``data/lts-registry.yaml`` (the ``source:
manual`` entries carry their own ``lts_lines`` and need no endoflife.date
fetch at all) -- pass one or more ``--product`` flags to fetch a narrower
(or a not-yet-registry-listed) set instead.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPTS_DIR.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

import yaml  # noqa: E402

from pyforge.warden.feeds import (  # noqa: E402
    FEED_CACHE_DIR_ENV_VAR,
    write_endoflife_cache,
)

# The real, stable, public endoflife.date "legacy" per-product JSON API: an
# array of per-cycle objects (cycle/releaseDate/eol/latest/
# latestReleaseDate/lts/support/discontinued/link -- verified against
# publicly documented endoflife.date API usage). One request per product
# slug; there is no single one-shot "everything" endpoint.
ENDOFLIFE_URL_TEMPLATE = "https://endoflife.date/api/{slug}.json"

_USER_AGENT = "pyforge-warden-refresh-endoflife-feed/1.0"

_REGISTRY_PATH = _SRC_DIR / "pyforge" / "warden" / "data" / "lts-registry.yaml"


def default_product_slugs() -> list[str]:
    """The bundled registry's own ``source: endoflife``/``source:
    heuristic-seed`` product slugs, sorted -- ``source: manual`` entries
    carry their own ``lts_lines`` and need no endoflife.date fetch at all
    (``currency.py`` never consults the cache for them). Returns an empty
    list (never raises) if the registry is unreadable/malformed -- the
    caller's own ``--product`` flag is the fallback for that case."""
    try:
        document = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    if not isinstance(document, dict):
        return []
    products = document.get("products")
    if not isinstance(products, dict):
        return []
    slugs: list[str] = []
    for entry in products.values():
        if not isinstance(entry, dict):
            continue
        slug = entry.get("slug")
        if isinstance(slug, str) and slug and entry.get("source") != "manual":
            slugs.append(slug)
    return sorted(set(slugs))


def fetch_product_cycles(slug: str, *, timeout: int = 60) -> list[dict[str, object]]:
    """Fetch + parse one product's endoflife.date cycle-array JSON. Raises
    ``urllib.error.URLError`` on a network failure or ``ValueError`` on a
    response that is not a JSON array -- a parse-sanity check so a
    provisioning run never silently caches a malformed/truncated document
    (mirrors ``refresh_kev_feed.fetch_kev_document``'s own guard). ``slug``
    is URL-escaped (``urllib.parse.quote(slug, safe="")``) before
    interpolation into the request URL -- even a ``/`` in a malformed/
    operator-typo'd slug is encoded rather than treated as a path
    separator -- so it can never produce a malformed or unintended request
    URL, whether it came from the bundled registry's own default list or an
    operator-supplied ``--product`` value."""
    url = ENDOFLIFE_URL_TEMPLATE.format(slug=urllib.parse.quote(slug, safe=""))
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    document = json.loads(raw)
    if not isinstance(document, list):
        raise ValueError(
            f"endoflife.date response for {slug!r} is not the expected shape "
            "(a JSON array of cycle records)"
        )
    return document


def refresh(
    cache_dir: str, *, product_slugs: list[str] | None = None, timeout: int = 60
) -> dict[str, object]:
    """End-to-end refresh: fetch every product's cycle array, aggregate into
    ONE ``{product_slug: [cycle-record, ...]}`` document, atomically write it
    via ``feeds.write_endoflife_cache``. Returns a small stats dict for the
    CLI's own human report -- never partially written (the write is atomic).
    A single product's fetch failure aborts the WHOLE refresh (fail loud,
    never silently cache a partial snapshot that looks complete)."""
    slugs = product_slugs if product_slugs is not None else default_product_slugs()
    document: dict[str, object] = {
        slug: fetch_product_cycles(slug, timeout=timeout) for slug in slugs
    }
    path = write_endoflife_cache(cache_dir, document)
    return {
        "cache_path": str(path),
        "product_count": len(document),
        "products": sorted(document),
    }


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir",
        default=os.environ.get(FEED_CACHE_DIR_ENV_VAR),
        help=(
            "feed cache root to write into (default: "
            f"${FEED_CACHE_DIR_ENV_VAR})"
        ),
    )
    parser.add_argument(
        "--product",
        action="append",
        dest="products",
        metavar="SLUG",
        default=None,
        help=(
            "an endoflife.date product slug to fetch; repeatable "
            "(default: every source:endoflife/source:heuristic-seed slug "
            "in the bundled data/lts-registry.yaml)"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="per-product HTTP timeout in seconds (default: 60)",
    )
    return parser


def main() -> None:
    args = _build_argparser().parse_args()
    if not args.cache_dir:
        print(
            f"error: no cache dir given and ${FEED_CACHE_DIR_ENV_VAR} is "
            "unset -- pass --cache-dir explicitly",
            file=sys.stderr,
        )
        raise SystemExit(2)
    try:
        result = refresh(args.cache_dir, product_slugs=args.products, timeout=args.timeout)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print(
            f"refresh-endoflife-feed FAILED: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    if args.products is None and result["product_count"] == 0:
        # No --product was given AND the bundled registry resolved to zero
        # default slugs -- indistinguishable, on stdout alone, from a
        # deliberate narrow run. The registry is likely missing/malformed
        # (default_product_slugs() degrades to [] rather than raising);
        # still a successful no-op (exit code unchanged), but it must not
        # be silent.
        print(
            "warning: 0 default products resolved from the bundled "
            "registry -- it may be missing or malformed; pass --product "
            "explicitly to override",
            file=sys.stderr,
        )
    print(f"fetched {result['product_count']} product(s): {', '.join(result['products'])}")
    print(f"  wrote: {result['cache_path']}")


if __name__ == "__main__":
    main()
