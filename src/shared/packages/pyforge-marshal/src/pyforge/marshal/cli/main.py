"""The ``marshal`` console-script entry point (Story 1.1 scaffold stub).

Only ``--version``/``--help`` are wired -- no real command exists yet (that
lands story-by-story against the Structural Seed's ``cli/`` package). Not
wired through the envelope/finding machinery: mirrors
``pyforge-doctor``'s ``__main__.py`` exit-relay pattern (structure: return
an int, never raise, relay argparse's own code, clamp anything foreign).
``main`` always RETURNS an int and embeds NO guarded exit-code literal
itself: ``EXIT_OK``/``EXIT_USAGE``/``EXIT_SIGINT``/``GUARDED_EXIT_CODES``
are imported from ``core/verdict.py``, the sole module permitted to spell
those integers (AD-7 -- the sole-ownership meta-test's AST scan enforces
the exit-call cases; the import discipline here keeps even non-call
literals out, one step stricter than the doctor file this mirrors). The
``if __name__ == "__main__": raise SystemExit(main())`` guard below calls
``SystemExit`` with the RESULT of ``main()`` -- a call expression, never a
literal -- which is why the meta-test does not flag it; it relays an
already-computed exit code rather than constructing a new one.
"""

from __future__ import annotations

import argparse
import sys

from ..core.verdict import EXIT_OK, EXIT_SIGINT, EXIT_USAGE, GUARDED_EXIT_CODES

# Scaffold stage (Story 1.1): __init__.py stays empty (no __version__
# constant), so the version string duplicates pyproject.toml's version
# literal here instead. Acceptable at scaffold stage; keep the two in sync
# by hand.
__version__ = "0.1.0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="marshal",
        description=(
            "Deterministic BMAD-loop supervisor (scaffold stage: no real "
            "command wired yet)."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and return an exit code -- never raises ``SystemExit``
    itself. Exit codes stay inside Marshal's frozen ``{0, 1, 2, 3, 4, 130}``
    domain (AD-7): argparse's own ``--version``/``--help`` exits (``0``)
    and usage errors (``2``) are relayed as plain ints, and a
    ``KeyboardInterrupt`` during parsing returns the SIGINT constant.
    """
    if argv is None:
        argv = sys.argv[1:]
    parser = _build_parser()
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits itself: --version/--help -> 0, a usage error -> 2
        # (never 0). Surface its code as a return value, never re-raised --
        # a non-int code (argparse never produces one under this parser
        # config) falls back to 2, still inside the guarded domain.
        if exc.code is None:
            return EXIT_OK
        if isinstance(exc.code, int) and exc.code in GUARDED_EXIT_CODES:
            return exc.code
        # Any other int (or non-int, e.g. a message string) is clamped to
        # EXIT_USAGE -- defense in depth for a future argparse action that
        # might exit with something outside Marshal's frozen domain (AD-7).
        return EXIT_USAGE
    except KeyboardInterrupt:
        return EXIT_SIGINT
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
