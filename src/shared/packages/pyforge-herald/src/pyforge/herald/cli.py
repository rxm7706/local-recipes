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
success (0), an int code passes through verbatim. There is no scan/report
region yet, so unlike warden's ``main`` this skeleton has no
last-resort exception net, no ``KeyboardInterrupt`` handling, and no
``exit_code_for`` projection -- those land once there is an actual bridge
operation whose exit code needs sole-ownership semantics.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__

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
