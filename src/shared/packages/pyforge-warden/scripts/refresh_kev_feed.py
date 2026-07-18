"""Fetches the CISA Known Exploited Vulnerabilities (KEV) catalog and writes
it into the on-disk cache layout ``feeds.py`` defines (Story 6.4).

Dev/ops-only maintenance script -- not part of the installed
``pyforge.warden`` package, and NEVER imported or invoked by ``scan``/
``OsvEngine``/anything in the installed package (NFR-S2: the ``scan``
runtime path opens no socket at any point). This script is the ENTIRE
"opt-in online" surface for KEV enrichment -- a human runs it, on whatever
cadence they choose, to (re)provision the cache ``OsvEngine`` later reads
fully offline.

Uses stdlib ``urllib.request`` only -- no new dependency, mirrors
``scripts/generate_conda_pypi_map.py``'s dev-only-script convention.

Usage::

    python scripts/refresh_kev_feed.py [--cache-dir <dir>]

Defaults ``--cache-dir`` to ``$PYFORGE_WARDEN_FEED_CACHE_DIR`` (the same env
var ``feeds.resolve_cache_dir`` reads at scan time) -- pass ``--cache-dir``
explicitly to provision a cache before that env var is even set.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPTS_DIR.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from pyforge.warden.feeds import (  # noqa: E402
    FEED_CACHE_DIR_ENV_VAR,
    write_kev_cache,
)

KEV_FEED_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
)

_USER_AGENT = "pyforge-warden-refresh-kev-feed/1.0"


def fetch_kev_document(*, timeout: int = 60) -> dict[str, object]:
    """Fetch + parse the CISA KEV JSON feed. Raises ``urllib.error.URLError``
    on a network failure or ``ValueError`` on a response that is not a JSON
    object with a ``vulnerabilities`` list -- a parse-sanity check so a
    provisioning run never silently caches a malformed/truncated document."""
    request = urllib.request.Request(
        KEV_FEED_URL, headers={"User-Agent": _USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    document = json.loads(raw)
    if not isinstance(document, dict) or not isinstance(
        document.get("vulnerabilities"), list
    ):
        raise ValueError(
            "CISA KEV response is not the expected shape (a JSON object "
            "with a 'vulnerabilities' list)"
        )
    return document


def refresh(cache_dir: str, *, timeout: int = 60) -> dict[str, object]:
    """End-to-end refresh: fetch the feed, atomically write it via
    ``feeds.write_kev_cache``. Returns a small stats dict for the CLI's own
    human/JSON report -- never partially written (the write is atomic)."""
    document = fetch_kev_document(timeout=timeout)
    path = write_kev_cache(cache_dir, document)
    vulnerabilities = document.get("vulnerabilities")
    return {
        "url": KEV_FEED_URL,
        "cache_path": str(path),
        "catalog_version": document.get("catalogVersion"),
        "date_released": document.get("dateReleased"),
        "vulnerability_count": len(vulnerabilities) if isinstance(vulnerabilities, list) else 0,
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
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds (default: 60)",
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
        result = refresh(args.cache_dir, timeout=args.timeout)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print(f"refresh-kev-feed FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"fetched {result['url']}")
    print(f"  catalog_version    : {result['catalog_version']}")
    print(f"  date_released      : {result['date_released']}")
    print(f"  vulnerability_count: {result['vulnerability_count']}")
    print(f"  wrote              : {result['cache_path']}")


if __name__ == "__main__":
    main()
