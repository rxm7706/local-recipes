"""The argparse CLI skeleton (Story 1.1).

This story wires only the top-level parser and the empty ``deck`` subcommand
group -- no ``seed``/``pull``/``status``/``watch`` parsers yet (those are
Stories 1.2-1.5+ against
``_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md``). The
``deck`` group's own ``deck_command`` subparsers collection is registered as
``required=True`` with zero parsers added, so ``herald deck`` alone is
already a usage error (exit 2) -- the same "no bare group" contract
``herald``'s own top-level ``command`` subparsers enforce (FR-26: every
subcommand's ``--help`` is 100% argparse-generated, never hand-written).

Exit-code shape mirrors ``pyforge.warden.cli.main``: argparse's own exits
(``--version``/``--help`` -> 0, usage errors -> 2, never 0) pass through as
the process exit code via the caught ``SystemExit``'s code -- ``None`` means
success (0), an int code passes through verbatim. ``main`` itself still has
no last-resort exception net and no ``KeyboardInterrupt`` handling -- out of
this story's AC scope, same as Story 1.1.

Story 1.4 adds ``dispatch``, AD-6's sole ``HeraldError`` catch point: the CLI
boundary catches what bridge-core raises, writes one structured stderr line,
and projects it to an exit code via ``errors.exit_code_for``. It is not yet
wired into ``main``'s subparsers -- no subcommand exists to call it (that
lands with Story 1.6's ``seed``) -- so it is exercised directly in tests
until then.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from . import __version__, errors

TOOL_NAME = "herald"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Dream-to-deck bridge CLI -- seeds, pulls, and syncs Claude "
            "Design decks against this repo's docs/dreams/ and "
            "presentations/ trees."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    deck = subparsers.add_parser(
        "deck", help="manage Claude Design decks (seed/pull/status/watch)"
    )
    # Empty subparser group by design (Story 1.1 scope): later stories add
    # seed/pull/status/watch here, one at a time, under this same group.
    deck.add_subparsers(dest="deck_command", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = _build_parser()
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits itself: --version/--help -> 0, usage error -> 2
        # (never 0). Surface its code as a return value -- a caught
        # variable, never an exit literal. A non-int code (argparse never
        # produces one under this parser config) falls back to 1 rather
        # than an int() crash.
        if exc.code is None:
            return 0
        if isinstance(exc.code, int):
            return exc.code
        return 1
    return 0


def dispatch(operation: Callable[[], None]) -> int:
    """Run ``operation``, catching ``HeraldError`` at the CLI boundary
    (AD-6): bridge-core raises, this is the sole place that catches.

    Writes one structured line to stderr (tool name, error type name,
    message -- embedded newlines and every other non-printable character
    flattened to spaces, so a multi-line message can never break the
    one-line contract for line-oriented consumers, and a server-relayed
    message carrying ANSI escapes or backspaces can never erase or spoof
    the structured prefix on a terminal) and returns
    ``errors.exit_code_for``'s mapped exit code; returns 0 when
    ``operation`` completes without raising. Not wired to any subcommand
    yet -- exercised directly in tests."""
    try:
        operation()
    except errors.HeraldError as exc:
        flat = " ".join(str(exc).splitlines())
        message = "".join(ch if ch.isprintable() else " " for ch in flat)
        print(f"{TOOL_NAME}: {type(exc).__name__}: {message}", file=sys.stderr)
        return errors.exit_code_for(exc)
    return 0
