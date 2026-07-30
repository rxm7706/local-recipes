"""The ``marshal`` console-script entry point (Story 1.1 scaffold; Story
1.3 converts the flat parser to a subparser tree).

``--version``/``--help`` keep working with no subcommand given -- a bare
``marshal`` invocation still returns ``EXIT_OK`` (Story 1.1's exit-code
behavior, preserved) but prints the usage line rather than silence, so a
caller that lost its arguments cannot read as success. ``config`` (Story
1.3, FR-54) is the first real
subcommand, dispatched to ``cli/config.py``. Not wired through the
envelope/finding machinery ITSELF: mirrors ``pyforge-doctor``'s
``__main__.py`` exit-relay pattern (structure: return an int, never raise,
relay argparse's own code, clamp anything foreign) -- individual
subcommand handlers (e.g. ``config.run_config``) are the ones that build
and print an envelope; this module only dispatches to them and relays
their returned int.

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
from . import config as config_cli

# Scaffold stage (Story 1.1): __init__.py stays empty (no __version__
# constant), so the version string duplicates pyproject.toml's version
# literal here instead. Acceptable at scaffold stage; keep the two in sync
# by hand.
__version__ = "0.1.0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="marshal",
        description="Deterministic BMAD-loop supervisor.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")
    config_cli.add_config_subparser(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and return an exit code -- never raises ``SystemExit``
    itself. Exit codes stay inside Marshal's frozen ``{0, 1, 2, 3, 4, 130}``
    domain (AD-7): argparse's own ``--version``/``--help`` exits (``0``)
    and usage errors (``2``) are relayed as plain ints, a subcommand
    handler's returned value is relayed only after the SAME domain clamp the
    ``SystemExit`` path applies (see ``core/verdict.exit_code_for``),
    and a ``KeyboardInterrupt`` anywhere in parser construction, parsing, or
    handler dispatch returns the SIGINT constant.
    """
    if argv is None:
        argv = sys.argv[1:]
    try:
        # _build_parser() sits INSIDE the try: a KeyboardInterrupt landing
        # during parser construction must return EXIT_SIGINT like one during
        # parsing, or main() would raise in violation of its own contract.
        parser = _build_parser()
        args = parser.parse_args(argv)
        if getattr(args, "command", None) is None:
            # Story 1.1's bare-invocation EXIT CODE is preserved (0), but
            # now that real subcommands exist, exiting in silence would let
            # a caller that LOST its arguments read as success -- print the
            # usage line so the invocation is visibly incomplete.
            parser.print_usage()
            return EXIT_OK
        handler = getattr(args, "handler", None)
        if handler is None:
            # Unreachable today -- every registered subparser calls
            # `set_defaults(handler=...)` -- but a future subparser that
            # forgets to must not silently report EXIT_OK: that would mask
            # an internal wiring bug as success. EXIT_USAGE (never a raise,
            # keeping this function's own "never raise" contract) makes the
            # failure visible instead.
            return EXIT_USAGE
        result = handler(args)
        if (
            isinstance(result, int)
            and not isinstance(result, bool)
            and result in GUARDED_EXIT_CODES
        ):
            return result
        # Same clamp as the SystemExit branch below, for the same reason: a
        # handler that returns None (fell off the end) or any value outside
        # the frozen domain is an internal wiring bug, and the console
        # script's sys.exit(None) would exit 0 -- masking the bug as
        # success. The docstring's frozen-domain claim is enforced, not
        # merely expected.
        return EXIT_USAGE
    except SystemExit as exc:
        # argparse exits itself: --version/--help -> 0, a usage error -> 2
        # (never 0). Surface its code as a return value, never re-raised --
        # a non-int code (argparse never produces one under this parser
        # config) falls back to 2, still inside the guarded domain. bool is
        # excluded like everywhere else in this package: SystemExit(True)
        # numerically equals 1 but is not an exit code -- clamp it.
        if exc.code is None:
            return EXIT_OK
        if (
            isinstance(exc.code, int)
            and not isinstance(exc.code, bool)
            and exc.code in GUARDED_EXIT_CODES
        ):
            return exc.code
        # Any other int (or non-int, e.g. a message string) is clamped to
        # EXIT_USAGE -- defense in depth for a future argparse action that
        # might exit with something outside Marshal's frozen domain (AD-7).
        return EXIT_USAGE
    except KeyboardInterrupt:
        return EXIT_SIGINT


if __name__ == "__main__":
    raise SystemExit(main())
