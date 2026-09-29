"""``trending-candidates`` task entrypoint — CAP-3 operator surface (Story 13.3, FR-66).

Read-side, offline-safe CLI over the already-materialized ``trending_candidates_classified``
dataset (Story 13.2, CAP-2): delegates to the SAME ``query.query_trending_candidates``
function the MCP tool (``mcp/tools.py::query_trending_candidates``) delegates to, so
identical filters yield identical output by construction (Design Notes).

Run: ``pixi run -e pyforge-atlas trending-candidates [-- --json]``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
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


def _print_table(envelope: dict) -> None:
    # Provenance header (review finding, Story 13.3): the table used to print the rows
    # ALONE, which made "this table was never ingested" and "your filters matched
    # nothing" byte-identical output — both just `(no candidates)`, exit 0. It also
    # left the staleness that catalog.yml (this same story) promises the surface always
    # shows — "an operator or agent can always see how stale this table is" — visible
    # only under `--json`, i.e. false for the DEFAULT human path the claim describes.
    print(
        f"# {envelope['dataset']}  provenance={envelope['provenance_kind']}"
        f"  build_stamp={envelope['build_stamp'] or 'none'}"
    )
    if envelope.get("reason"):
        # Per LINE (follow-up review finding, Story 13.3): a kedro `DatasetError`
        # reason is multi-line, and the continuation lines printed WITHOUT the `#`
        # prefix — visible in the ordinary fresh-worktree run, where an un-prefixed
        # `[Errno 2] ...` line sat between the header and the rows.
        for line in str(envelope["reason"]).splitlines():
            print(f"# {line}")
    # rows -> matched -> shown (second follow-up review finding, Story 13.3). `shown`
    # alone (the post-cap count) left the two states an operator most needs to tell
    # apart byte-identical: a table whose rows are ALL tagged period="all" — what CAP-1
    # writes when the HTML scrape breaks and it falls back to the Search API — answers
    # the DEFAULT `--period weekly` with the same `shown=0  (no candidates)` as a
    # healthy table nothing qualified in, under a fresh build_stamp that says all is
    # well. `rows=N  matched=0` says "the data is here, your filters excluded all of
    # it"; `matched=400  shown=25` is also the only place truncation is visible.
    print(
        f"# filters={envelope['filters']}  rows={envelope['rows']}"
        f"  matched={envelope['matched']}  shown={envelope['count']}"
    )

    candidates = envelope["candidates"]
    if not candidates:
        print("(no candidates)")
        return
    widths = {c: max(len(c), *(len(str(row.get(c, ""))) for row in candidates)) for c in _TABLE_COLUMNS}
    print("  ".join(c.ljust(widths[c]) for c in _TABLE_COLUMNS))
    print("  ".join("-" * widths[c] for c in _TABLE_COLUMNS))
    for row in candidates:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in _TABLE_COLUMNS))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Saved, not assumed to be NOTSET (review finding, Story 13.3): `logging.disable`
    # is PROCESS-global, so resetting to NOTSET in the `finally` would CLEAR a floor
    # the calling process had deliberately set — verified live: a host at
    # `logging.disable(logging.WARNING)` came back from one `main(["--json"])` call
    # with its own suppression silently lifted. Restore what was there.
    previous_disable = logging.root.manager.disable
    if args.json:
        # `--json` promises a byte-for-byte-parseable envelope on stdout (SPEC.md's
        # CAP-3 success signal: "JSON output validates against a documented schema").
        # `query_trending_candidates` bootstraps a real Kedro session, which installs
        # its own rich console handler AS PART OF that bootstrap
        # (kedro/framework/project/rich_logging.yml) -- setting a logger's level ahead
        # of time gets overwritten the moment bootstrap applies its own dictConfig.
        # `logging.disable` is the one mechanism dictConfig does not reset: a global
        # floor no per-logger reconfiguration can undo.
        #
        # CRITICAL, not INFO (review finding, Story 13.3): that handler sits on the
        # ROOT logger and writes to STDOUT (verified live), and the root logger's own
        # level is WARNING -- so an INFO-only floor still let every WARNING record
        # (e.g. kedro's own "Credentials not found in your Kedro project config.")
        # print INTO the envelope, and `json.loads(stdout)` then failed. Under `--json`
        # stdout carries the envelope and NOTHING else.
        #
        # This SUPPRESSES those records; it does not redirect them (follow-up review
        # finding, Story 13.3 — this comment used to claim "diagnostics still reach the
        # operator, on stderr, via the handler below", and there is no such handler).
        # Re-pointing them at stderr instead is not available from here: kedro installs
        # its stdout handler via its own `dictConfig` DURING the bootstrap inside
        # `query_trending_candidates`, i.e. after this point and before any code here
        # runs again. The `--json` operator is not left blind: a load failure is
        # reported IN-BAND in the envelope itself (`provenance_kind: "unavailable"` +
        # `reason`), and any failure that reaches the guard below is printed to stderr.
        # Table mode is human-read, so library log noise there stays un-suppressed.
        logging.disable(logging.CRITICAL)

    try:
        try:
            # Deferred (not a module-level import): importing `query` transitively
            # imports `kedro.framework.project`, whose `_ProjectLogging` singleton
            # fires its own "Using '...' as logging configuration" INFO log AT IMPORT
            # TIME -- before any code below could suppress it. Must import AFTER the
            # disable() call above. It is INSIDE this try (review finding, Story
            # 13.3): an ImportError raised here used to escape as a raw traceback,
            # since the outer try carried only a `finally`.
            from . import query

            envelope = query.query_trending_candidates(
                period=args.period,
                tier=args.tier,
                top=args.top,
                not_on_cf=args.not_on_cf,
                min_stars=args.min_stars,
            )
            # Serialized INSIDE the guard too (review finding, Story 13.3): a cell
            # `json.dumps` cannot encode (e.g. a Timestamp column) used to escape as a
            # raw traceback from outside it.
            #
            # EMITTED inside it as well (follow-up review finding, Story 13.3): the two
            # print paths used to sit outside this `except`, in an outer `try` carrying
            # only a `finally`, so a write failure escaped as a raw traceback — and the
            # ordinary `trending-candidates -- --json | head` produced exactly that
            # (`BrokenPipeError`, verified live), for the one class of failure a CLI is
            # most likely to meet.
            if args.json:
                print(json.dumps(envelope))
            else:
                _print_table(envelope)
            # FLUSHED HERE, inside the guard (second follow-up review finding, Story
            # 13.3): stdout is BLOCK-buffered whenever it is a pipe, and no realistic
            # envelope fills that buffer — so `print` returned cleanly and the
            # BrokenPipeError surfaced only in the interpreter's SHUTDOWN flush, i.e.
            # outside this `try`, as "Exception ignored while flushing sys.stdout" +
            # exit 120. The previous pass verified its fix in a shell exporting
            # PYTHONUNBUFFERED=1 (ambient here, set by neither pixi.toml nor the
            # Containerfile) — which is precisely the setting that hid it: with
            # `env -u PYTHONUNBUFFERED … --json | head`, the guard never ran.
            sys.stdout.flush()
        except BrokenPipeError:
            # The reader (`| head`, `| less` quit early) is gone: nothing can be
            # reported to it, and leaving the interpreter to flush stdout at shutdown
            # prints "Exception ignored in: <_io.TextIOWrapper name='<stdout>'>" to
            # stderr. Detach stdout first, then exit quietly on the standard 1.
            #
            # ONLY when this process owns the real stdout (second follow-up review
            # finding, Story 13.3): `dup2` retargets the descriptor for the WHOLE
            # process and nothing ever undoes it, so an in-process `main()` caller —
            # the same callable API `test_json_restores_the_callers_own_logging_floor`
            # exists for — came back with its own stdout permanently pointed at
            # /dev/null. A host that redirected `sys.stdout` has no shutdown flush of
            # the real stdout to silence anyway, so the detach is unnecessary there as
            # well as destructive. The devnull fd is closed rather than leaked.
            if sys.stdout is sys.__stdout__:
                with contextlib.suppress(OSError):
                    devnull = os.open(os.devnull, os.O_WRONLY)
                    try:
                        os.dup2(devnull, sys.stdout.fileno())
                    finally:
                        os.close(devnull)
            return 1
        except Exception as exc:
            # Broad on purpose: a bad filter value is `ValueError` (the documented
            # contract), but ANY other failure -- a Kedro session/credential bootstrap
            # error, an ImportError, an unencodable cell -- must still degrade to a
            # clean stderr message + exit 1 for a CLI's end user, never a raw
            # traceback. The type is prefixed because several of these carry a message
            # that is meaningless alone (review finding, Story 13.3: a bootstrap
            # `KeyError` printed the bare line `'atlas'`, and a zero-message exception
            # printed an empty one).
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        return 0
    finally:
        if args.json:
            logging.disable(previous_disable)


if __name__ == "__main__":
    raise SystemExit(main())
