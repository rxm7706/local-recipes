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
product slug in the bundled ``data/lts-registry.yaml`` (a ``source: manual``
entry carries its own ``lts_lines`` and a ``null`` slug per the registry's
own header -- there is nothing to fetch for it) -- pass one or more
``--product`` flags to fetch a narrower (or a not-yet-registry-listed) set
instead. A run that resolves ZERO slugs (registry missing/malformed and no
``--product`` given) refuses to write and exits non-zero -- an empty
snapshot is the most complete-looking partial snapshot possible, and it
must never clobber a previously provisioned cache.
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

# The reader's own normalizer -- imported (not duplicated) so writer and
# reader can never drift apart on what "the same product key" means. This
# direction of import is sanctioned: the SCRIPT imports the package; the
# package never imports the script (NFR-S2).
from pyforge.warden.currency import _normalize_name  # noqa: E402
from pyforge.warden.feeds import (  # noqa: E402
    FEED_CACHE_DIR_ENV_VAR,
    endoflife_cache_path,
    load_endoflife_snapshot,
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
    heuristic-seed`` product slugs, sorted -- a ``source: manual`` entry
    carries its own ``lts_lines`` and a ``null`` slug (per the registry's
    own header), so there is nothing to fetch for it; the ``!= "manual"``
    filter below is belt-and-braces against a future manual entry that
    grew a slug, not a claim ``currency.py`` would ignore one (its slug
    routing is unconditional). Returns an empty list (never raises) if the
    registry is unreadable/malformed -- the caller's own ``--product`` flag
    is the fallback for that case."""
    try:
        document = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        # UnicodeDecodeError is a ValueError, not an OSError -- a corrupted
        # registry's invalid UTF-8 must hit the documented degrade-to-[]
        # path (and thence the zero-slug refusal), never escape as a
        # decode traceback.
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
    ``ValueError`` on an empty slug (a usage error, not a request worth
    making -- an empty slug would otherwise fetch the API root's
    ``.json`` and surface as a baffling HTTP error), ``urllib.error.
    URLError`` on a network failure, or ``ValueError`` on a response that
    is not a JSON array -- a parse-sanity check so a provisioning run never
    silently caches a malformed/truncated document (mirrors
    ``refresh_kev_feed.fetch_kev_document``'s own guard). ``slug`` is
    URL-escaped (``urllib.parse.quote(slug, safe="")``) before
    interpolation into the request URL -- even a ``/`` in a malformed/
    operator-typo'd slug is encoded rather than treated as a path
    separator -- so it can never produce a malformed or unintended request
    URL, whether it came from the bundled registry's own default list or an
    operator-supplied ``--product`` value.

    JSON numbers are parsed with ``parse_float=str``/``parse_int=str`` so a
    bare-number ``cycle`` value keeps its LEXICAL form (``3.10`` stays
    ``"3.10"``, never float-truncated to ``"3.1"``) -- the reader
    (``currency._resolve_from_cycles``) treats cycle identifiers as
    strings, and a ``"3.1"``/``"3.10"`` collapse would misroute a real
    interpreter line (review finding, 2026-07-23). Only our reader's four
    fields (``cycle``/``releaseDate``/``eol``/``latest``) matter and none
    is legitimately numeric, so stringifying every numeral is lossless
    where it counts."""
    if not slug:
        raise ValueError("empty product slug -- pass a real endoflife.date slug")
    url = ENDOFLIFE_URL_TEMPLATE.format(slug=urllib.parse.quote(slug, safe=""))
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    document = json.loads(raw, parse_float=str, parse_int=str)
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
    never silently cache a partial snapshot that looks complete). ZERO slugs
    to fetch (registry missing/malformed with no ``--product`` given, or an
    explicitly empty ``product_slugs`` list) raises ``ValueError`` BEFORE
    any write -- an empty snapshot is the most complete-looking partial
    snapshot possible, and writing it would clobber a previously
    provisioned, still-good cache with a document that floods every later
    scan with ``currency:unknown`` findings (review finding, 2026-07-23).

    The write REPLACES the whole cache document, never merges into it:
    merging would re-stamp every unfetched (possibly-stale) product as
    fresh under the new file's mtime — a false-green vector for a
    compliance gate. A narrower ``--product`` run that drops previously
    provisioned products therefore reports them in the returned stats'
    ``dropped_products`` (and ``main()`` warns on stderr) so the shrink is
    loud, not silent (review finding, 2026-07-23)."""
    slugs = product_slugs if product_slugs is not None else default_product_slugs()
    if not slugs:
        raise ValueError(
            "no product slugs to fetch (the bundled registry is missing/"
            "malformed and no --product was given) -- refusing to write an "
            "empty snapshot over a possibly-good cache"
        )
    # The scan-time reader (currency.py) normalizes snapshot keys and drops
    # BOTH members of any normalized collision -- so two case/separator
    # variants of one slug ("Django"/"django") would produce a "successful"
    # refresh whose product no scan can ever resolve. Fail loud BEFORE any
    # request instead (review finding, 2026-07-23); exact duplicates are
    # merely deduped.
    deduped_slugs = sorted(set(slugs))
    by_normalized: dict[str, str] = {}
    for slug in deduped_slugs:
        normalized = _normalize_name(slug)
        other = by_normalized.get(normalized)
        if other is not None:
            raise ValueError(
                f"product slugs {other!r} and {slug!r} normalize to the "
                f"same cache key {normalized!r} -- the scan-time reader "
                "would treat them as ambiguous and drop BOTH; de-duplicate "
                "the slug list"
            )
        by_normalized[normalized] = slug
    existing = load_endoflife_snapshot(endoflife_cache_path(cache_dir))
    previous_products = set(existing) if existing is not None else set()
    document: dict[str, object] = {
        slug: fetch_product_cycles(slug, timeout=timeout) for slug in deduped_slugs
    }
    path = write_endoflife_cache(cache_dir, document)
    return {
        "cache_path": str(path),
        "product_count": len(document),
        "products": sorted(document),
        "dropped_products": sorted(previous_products - set(document)),
    }


def _timeout_type(value: str) -> int:
    """Argparse type for ``--timeout``: a POSITIVE integer. Zero would set a
    non-blocking socket and a negative value would only surface later as a
    baffling fetch-time failure -- both are usage errors, rejected at parse
    time with a usage exit (2), never a FAILED-banner exit (1) (review
    finding, 2026-07-23)."""
    try:
        timeout = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid int value: {value!r}") from exc
    if timeout <= 0:
        raise argparse.ArgumentTypeError(
            f"--timeout must be a positive integer (seconds), got {value!r}"
        )
    return timeout


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
        type=_timeout_type,
        default=60,
        help="per-product HTTP timeout in seconds, a positive integer (default: 60)",
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
    dropped = result["dropped_products"]
    if dropped:
        print(
            f"warning: {len(dropped)} previously provisioned product(s) "
            f"dropped by this narrower fetch set: {', '.join(dropped)} -- "
            "the cache is a whole-document snapshot (replace, not merge: "
            "merging would re-stamp unfetched, possibly-stale products as "
            "fresh); rerun without --product to re-provision the full "
            "registry set",
            file=sys.stderr,
        )
    print(f"fetched {result['product_count']} product(s): {', '.join(result['products'])}")
    print(f"  wrote: {result['cache_path']}")


if __name__ == "__main__":
    main()
