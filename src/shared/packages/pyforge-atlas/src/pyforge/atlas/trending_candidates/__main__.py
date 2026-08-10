"""``trending-candidates`` task entrypoint — CAP-3 operator surface (Story 13.3, FR-66).

Read-side, offline-safe CLI over the already-materialized ``trending_candidates_classified``
dataset (Story 13.2, CAP-2): delegates to the SAME ``query.query_trending_candidates``
function the MCP tool (``mcp/tools.py::query_trending_candidates``) delegates to, so
identical filters yield identical output by construction (Design Notes).

Run: ``pixi run -e pyforge-atlas trending-candidates [-- --json]``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

_TABLE_COLUMNS = ("repo_full_name", "tier", "reason", "stars_total", "period")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trending-candidates",
        description=(
            "Query the CAP-2 tiered/classified GitHub-trending candidate list "
            "(CAP-3, tier-taxonomy.md) — read-side only, offline-safe."
        ),
    )
    parser.add_argument(
        "--period",
        default="weekly",
        help="daily|weekly|monthly|all ingestion window (default: weekly)",
    )
    parser.add_argument(
        "--tier",
        default="1,2",
        help="comma-list of 1/2/skip, or the literal 'all' (default: 1,2)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="display cap over the already-ingested set (default: 25)",
    )
    cf_group = parser.add_mutually_exclusive_group()
    cf_group.add_argument(
        "--not-on-cf",
        dest="not_on_cf",
        action="store_true",
        default=True,
        help="filter to not-yet-on-conda-forge candidates (default)",
    )
    cf_group.add_argument(
        "--all",
        dest="not_on_cf",
        action="store_false",
        help="include already-on-conda-forge candidates too",
    )
    parser.add_argument(
        "--min-stars",
        type=int,
        default=500,
        help="floor to drop micro-repos (default: 500)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="machine-readable JSON output (default: a formatted table)",
    )
    return parser


def _print_table(candidates: list[dict]) -> None:
    if not candidates:
        print("(no candidates)")
        return
    widths = {
        c: max(len(c), *(len(str(row.get(c, ""))) for row in candidates))
        for c in _TABLE_COLUMNS
    }
    print("  ".join(c.ljust(widths[c]) for c in _TABLE_COLUMNS))
    print("  ".join("-" * widths[c] for c in _TABLE_COLUMNS))
    for row in candidates:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in _TABLE_COLUMNS))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.json:
        # `--json` promises a byte-for-byte-parseable envelope on stdout (SPEC.md's
        # CAP-3 success signal: "JSON output validates against a documented schema").
        # `query_trending_candidates` bootstraps a real Kedro session, which configures
        # a console (rich) handler at INFO for the `kedro` logger tree AS PART OF that
        # bootstrap (kedro/framework/project/rich_logging.yml) -- setting a logger's
        # level ahead of time gets overwritten the moment bootstrap applies its own
        # dictConfig. `logging.disable` is the one mechanism dictConfig does not
        # reset: a global floor no per-logger reconfiguration can undo. Raised only
        # for the JSON path -- table mode is human-read, so library log noise there
        # is harmless. Reset in `finally` below (review finding, Story 13.3): this is
        # PROCESS-global state, and `main()` is also callable in-process (tests, or any
        # future long-lived caller) -- leaving it disabled would silently suppress
        # INFO logging for the rest of that process after a single `--json` call.
        logging.disable(logging.INFO)

    try:
        # Deferred (not a module-level import): importing `query` transitively imports
        # `kedro.framework.project`, whose `_ProjectLogging` singleton fires its own
        # "Using '...' as logging configuration" INFO log AT IMPORT TIME -- before any
        # code below could suppress it. Must import AFTER the disable() call above.
        from . import query

        try:
            envelope = query.query_trending_candidates(
                period=args.period,
                tier=args.tier,
                top=args.top,
                not_on_cf=args.not_on_cf,
                min_stars=args.min_stars,
            )
        except Exception as exc:
            # Broad on purpose (review finding, Story 13.3): a bad filter value is
            # `ValueError` (the documented contract), but ANY other failure -- e.g. a
            # Kedro session/credential bootstrap error -- must still degrade to a clean
            # stderr message + exit 1 for a CLI's end user, never a raw traceback.
            print(str(exc), file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(envelope))
        else:
            _print_table(envelope["candidates"])
        return 0
    finally:
        if args.json:
            logging.disable(logging.NOTSET)


if __name__ == "__main__":
    raise SystemExit(main())
