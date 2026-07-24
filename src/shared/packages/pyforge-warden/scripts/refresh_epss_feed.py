"""Fetches the FIRST.org EPSS (Exploit Prediction Scoring System) feed and
writes it into the on-disk cache layout ``feeds.py`` defines (Story 6.7).

Dev/ops-only maintenance script -- not part of the installed
``pyforge.warden`` package, and NEVER imported or invoked by ``scan``/
``OsvEngine``/anything in the installed package (NFR-S2: the ``scan``
runtime path opens no socket at any point). This script is the ENTIRE
"opt-in online" surface for EPSS enrichment -- a human runs it, on whatever
cadence they choose, to (re)provision the cache ``OsvEngine`` later reads
fully offline.

Uses stdlib ``urllib.request`` + ``gzip`` + ``csv`` only -- no new
dependency, mirrors ``scripts/refresh_kev_feed.py``'s dev-only-script
convention. Unlike CISA's KEV feed (JSON), FIRST.org publishes EPSS as a
gzip-compressed CSV (``cve,epss,percentile``, with a leading ``#``-prefixed
metadata comment line) -- this script decompresses and parses it, then
normalizes into the SAME cached-JSON-document convention every other feed in
this project uses (``{"scores": [{"cve": ..., "epss": ..., "percentile":
...}, ...]}``) before ever calling ``write_epss_cache`` -- ``feeds.py``
itself stays feed-shape-agnostic and never sees raw CSV.

Usage::

    python scripts/refresh_epss_feed.py [--cache-dir <dir>]

Defaults ``--cache-dir`` to ``$PYFORGE_WARDEN_FEED_CACHE_DIR`` (the same env
var ``feeds.resolve_cache_dir`` reads at scan time) -- pass ``--cache-dir``
explicitly to provision a cache before that env var is even set.
"""

from __future__ import annotations

import argparse
import csv
import gzip
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
    write_epss_cache,
)

EPSS_FEED_URL = "https://epss.cyentia.com/epss_scores-current.csv.gz"

_USER_AGENT = "pyforge-warden-refresh-epss-feed/1.0"

_EXPECTED_FIELDNAMES = {"cve", "epss", "percentile"}


def fetch_epss_scores(*, timeout: int = 60) -> list[dict[str, object]]:
    """Fetch, gzip-decompress, and CSV-parse the FIRST.org EPSS feed into a
    list of ``{"cve": str, "epss": float, "percentile": float}`` records.

    Raises ``urllib.error.URLError`` on a network failure or ``ValueError``
    on a response that does not decompress/parse into the expected shape --
    a parse-sanity check so a provisioning run never silently caches a
    malformed/truncated document. A single malformed CSV row (an empty
    ``cve``, or an unparsable ``epss``/``percentile``) is skipped, never
    aborting the parse of the rest -- this codebase's established
    tolerant-per-entry convention (mirrors ``feeds.load_epss_scores``'s own
    per-entry tolerance on the read side)."""
    request = urllib.request.Request(
        EPSS_FEED_URL, headers={"User-Agent": _USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw_gzip = response.read()
    try:
        raw_csv = gzip.decompress(raw_gzip).decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(
            "FIRST.org EPSS response is not a valid gzip-compressed UTF-8 "
            "CSV document"
        ) from exc
    # The real feed's first line is a `#model_version:...,score_date:...`
    # metadata comment, not the CSV header -- skip any leading `#` lines
    # before csv.DictReader ever sees the real `cve,epss,percentile` header.
    lines = [line for line in raw_csv.splitlines() if not line.startswith("#")]
    reader = csv.DictReader(lines)
    # A subset check, not an exact-match: tolerates FIRST.org adding a new
    # column to the public feed without a code change (forward-compat --
    # review finding), while still failing loud if any of the three columns
    # this script actually reads is missing.
    if reader.fieldnames is None or not _EXPECTED_FIELDNAMES.issubset(
        reader.fieldnames
    ):
        raise ValueError(
            "FIRST.org EPSS response is not the expected shape (a CSV "
            "header including 'cve,epss,percentile')"
        )
    scores: list[dict[str, object]] = []
    for row in reader:
        cve = row.get("cve")
        if not isinstance(cve, str) or not cve:
            continue
        try:
            scores.append(
                {
                    "cve": cve,
                    "epss": float(row["epss"]),
                    "percentile": float(row["percentile"]),
                }
            )
        except (TypeError, ValueError):
            continue
    if not scores:
        raise ValueError("FIRST.org EPSS response parsed to zero usable score rows")
    return scores


def refresh(cache_dir: str, *, timeout: int = 60) -> dict[str, object]:
    """End-to-end refresh: fetch the feed, atomically write it via
    ``feeds.write_epss_cache``. Returns a small stats dict for the CLI's own
    human/JSON report -- never partially written (the write is atomic)."""
    scores = fetch_epss_scores(timeout=timeout)
    document = {"scores": scores}
    path = write_epss_cache(cache_dir, document)
    return {
        "url": EPSS_FEED_URL,
        "cache_path": str(path),
        "score_count": len(scores),
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
        print(f"refresh-epss-feed FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"fetched {result['url']}")
    print(f"  score_count: {result['score_count']}")
    print(f"  wrote      : {result['cache_path']}")


if __name__ == "__main__":
    main()
