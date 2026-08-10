"""``trending-handoff`` task entrypoint — CAP-5 downstream handoff to Mason (Story
13.5, FR-68).

Read-side, offline-safe CLI over the already-classified ``trending_candidates_classified``
dataset (Story 13.2, CAP-2): looks up ONE candidate, requires a caller-supplied
PASSING health-screen verdict, and on a tier-1/2 candidate prints ONE structured JSON
record to stdout — never a recipe, never a staged-recipes PR (SPEC.md's CAP-5 success
signal). Unlike ``trending-candidates`` (Story 13.3) there is no table mode: output is
unconditionally JSON, and NFR-6 governs the exit code — 0 pass, 1 policy-fail
(``hand_off_candidate``'s own documented ``ValueError`` contract: an ineligible
candidate, a missing/failing health screen, or a not-yet-ingested dataset), 2 error
(anything else — an unexpected bootstrap failure must NOT be swallowed as a
policy-fail), 130 interrupted.

Run: ``pixi run -e pyforge-atlas trending-handoff -- --repo owner/repo --verdict pass
--abandonment-signal "..." --license-clarity "..."``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trending-handoff",
        description=(
            "Hand off ONE tier-1/2 trending candidate to the packaging factory "
            "(CAP-5, FR-68) — requires a recorded, PASSING health-screen verdict on "
            "every call. Never auto-submits a recipe or opens a staged-recipes PR."
        ),
    )
    parser.add_argument("--repo", required=True, help="owner/repo (case-insensitive)")
    parser.add_argument(
        "--verdict",
        required=True,
        choices=("pass", "fail"),
        help="the recorded health-screen verdict — must be 'pass' to hand off",
    )
    parser.add_argument(
        "--abandonment-signal",
        required=True,
        dest="abandonment_signal",
        help="recorded abandonment-signal evidence (non-empty)",
    )
    parser.add_argument(
        "--license-clarity",
        required=True,
        dest="license_clarity",
        help="recorded license-clarity evidence (non-empty)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Mirrors `trending_candidates/__main__.py`'s process-global logging floor, for
    # the identical reason: `hand_off_candidate` bootstraps a real Kedro session,
    # which installs its own rich console handler ON THE ROOT LOGGER, writing to
    # STDOUT, as PART of that bootstrap — overwriting any per-logger level set ahead
    # of time. `logging.disable` is the one mechanism that survives it. This CLI is
    # unconditionally JSON (no table mode), so the floor applies to every call, not
    # just a `--json`-gated branch — and is unconditionally restored in `finally`,
    # preserving whatever floor the calling process had already set (the identical
    # `__main__.py` follow-up review finding: resetting to NOTSET unconditionally
    # would CLEAR a floor the caller deliberately set).
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)

    try:
        # Deferred (not a module-level import): importing `handoff` transitively
        # imports `kedro.framework.project`, whose `_ProjectLogging` singleton fires
        # its own INFO log AT IMPORT TIME — before the `disable()` call above could
        # suppress it (identical reasoning to `__main__.py`).
        from . import handoff

        record = handoff.hand_off_candidate(
            repo_full_name=args.repo,
            verdict=args.verdict,
            abandonment_signal=args.abandonment_signal,
            license_clarity=args.license_clarity,
        )
        print(json.dumps(record))
        # Flushed here, inside the guard (mirrors `__main__.py`'s own follow-up
        # review finding): stdout is block-buffered whenever it is a pipe, so a
        # write failure only surfaces on this explicit flush, not on `print` itself.
        sys.stdout.flush()
        return 0
    except ValueError as exc:
        # NFR-6: 1 = policy-fail — an ineligible candidate, a failing/missing
        # health screen, or a not-yet-ingested dataset. Not type-prefixed (unlike
        # the generic handler below): every `hand_off_candidate` `ValueError`
        # message already names its own specific reason (I/O & Edge-Case Matrix),
        # so a `ValueError: ` prefix would be redundant, not clarifying.
        # Suppressed (review finding): a broken STDERR pipe would otherwise raise
        # `BrokenPipeError` from INSIDE this handler, escaping as a raw traceback —
        # the sibling `except BrokenPipeError:` clause below only catches one raised
        # from the `try` body, never one raised from another `except` block.
        with contextlib.suppress(BrokenPipeError):
            print(str(exc), file=sys.stderr)
        return 1
    except BrokenPipeError:
        # Mirrors `__main__.py`'s detach-then-quiet-exit pattern (identical
        # rationale): the reader is gone, nothing can be reported to it, and
        # leaving the interpreter to flush stdout at shutdown prints "Exception
        # ignored in: ..." to stderr. NFR-6 maps this to exit 2 (an unexpected
        # error, not a policy-fail) rather than `__main__.py`'s 1 — this CLI's 1 is
        # reserved for `hand_off_candidate`'s own documented `ValueError` contract.
        if sys.stdout is sys.__stdout__:
            with contextlib.suppress(OSError):
                devnull = os.open(os.devnull, os.O_WRONLY)
                try:
                    os.dup2(devnull, sys.stdout.fileno())
                finally:
                    os.close(devnull)
        return 2
    except KeyboardInterrupt:
        # NFR-6: 130 = interrupted (128 + SIGINT's signal number 2) — the standard
        # shell convention for a Ctrl-C'd process.
        return 130
    except Exception as exc:
        # NFR-6: 2 = unexpected error — must NOT be swallowed as a policy-fail
        # (Boundaries & Constraints: "Unexpected bootstrap failure ... Not
        # swallowed as policy-fail"). Broad on purpose: a Kedro session/credential
        # bootstrap error, an ImportError, an unencodable cell — anything that
        # isn't `hand_off_candidate`'s own documented `ValueError` contract must
        # still degrade to a clean stderr message, never a raw traceback. Prefixed
        # with the exception TYPE (mirrors `__main__.py`): several of these carry a
        # message that is meaningless alone (e.g. a bootstrap `KeyError` prints the
        # bare line `'atlas'`). Suppressed for the identical broken-stderr-pipe
        # reason as the `ValueError` handler above.
        with contextlib.suppress(BrokenPipeError):
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    finally:
        logging.disable(previous_disable)


if __name__ == "__main__":
    raise SystemExit(main())
