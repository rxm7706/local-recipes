"""The argparse CLI skeleton (Story 1.1), now wiring ``deck seed`` (Story 1.6).

``pull``/``status``/``watch`` are still unwired (Epics 2-4). The ``deck``
group's ``deck_command`` subparsers collection stays ``required=True``, so
``herald deck`` alone is still a usage error (exit 2) -- the same "no bare
group" contract ``herald``'s own top-level ``command`` subparsers enforce
(FR-26: every subcommand's ``--help`` is 100% argparse-generated, never
hand-written).

Exit-code shape mirrors ``pyforge.warden.cli.main``: argparse's own exits
(``--version``/``--help`` -> 0, usage errors -> 2, never 0) pass through as
the process exit code via the caught ``SystemExit``'s code -- ``None`` means
success (0), an int code passes through verbatim. ``main`` itself still has
no last-resort exception net and no ``KeyboardInterrupt`` handling -- out of
this story's AC scope, same as Story 1.1.

``dispatch`` (Story 1.4) is AD-6's sole ``HeraldError`` catch point: the CLI
boundary catches what bridge-core raises, writes one structured stderr line,
and projects it to an exit code via ``errors.exit_code_for``. ``deck seed``
is the first subcommand wired through it -- ``main`` builds the V1-default
``McpTransport`` (Story 1.2's spike outcome: the primary path, not the
fallback), composes ``bridge.run`` with ``deck_pipeline.seed``, and hands the
whole operation to ``dispatch``. This module is the one place allowed to name
a concrete adapter (``McpTransport``) -- it is the composition root AD-2/AD-3
carve out of the determinism boundary, never bridge-core itself."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from . import __version__, bridge, deck_pipeline, errors
from .transport import McpTransport

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
    deck_subparsers = deck.add_subparsers(dest="deck_command", required=True)
    seed = deck_subparsers.add_parser(
        "seed", help="seed a deck slug into Claude Design (CAP-1)"
    )
    seed.add_argument("slug", help="deck slug, e.g. pyforge-warden")
    seed.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repo root containing presentations/<slug>/ (default: cwd)",
    )
    seed.add_argument(
        "--support-source-project",
        default=deck_pipeline.PILOT_SUPPORT_SOURCE_PROJECT_ID,
        help=(
            "Design project id to copy deck-stage.js from (default: the "
            "already-seeded pyforge-marshal pilot project)"
        ),
    )
    pull = deck_subparsers.add_parser(
        "pull", help="pull a deck's prototype from Claude Design into the repo (CAP-2)"
    )
    pull.add_argument("slug", help="deck slug, e.g. pyforge-warden")
    pull.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repo root containing presentations/<slug>/ (default: cwd)",
    )
    # status/watch land in Epics 3-4, under this same deck_subparsers group.
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
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
    if args.command == "deck" and args.deck_command == "seed":
        return _run_deck_seed(args)
    if args.command == "deck" and args.deck_command == "pull":
        return _run_deck_pull(args)
    return 0


def _run_deck_seed(args: argparse.Namespace) -> int:
    """Compose ``bridge.run`` + ``deck_pipeline.seed`` over the V1-default
    ``McpTransport`` and hand the whole operation to ``dispatch`` (AD-6).

    ``McpTransport()`` is constructed *inside* ``operation`` -- never before
    ``dispatch`` is called -- so a construction failure (today: none;
    ``McpTransport.__init__`` only ever raises on a non-https override,
    never on its no-argument default) is caught by the same AD-6 boundary
    as everything else in this call, rather than crashing ``main`` raw."""
    repo_root = args.repo_root if args.repo_root is not None else Path.cwd()

    def operation() -> None:
        transport = McpTransport()
        result = bridge.run(
            transport,
            lambda t: deck_pipeline.seed(
                t,
                slug=args.slug,
                repo_root=repo_root,
                support_source_project_id=args.support_source_project,
            ),
        )
        print(f"seeded {args.slug}: {result.project.url}")

    return dispatch(operation)


def _run_deck_pull(args: argparse.Namespace) -> int:
    """Compose ``bridge.run`` + ``deck_pipeline.pull_prototype`` over the
    V1-default ``McpTransport`` and hand the whole operation to ``dispatch``
    (AD-6), mirroring ``_run_deck_seed``'s composition shape exactly:
    ``McpTransport()`` is constructed inside ``operation``, never before
    ``dispatch`` is called."""
    repo_root = args.repo_root if args.repo_root is not None else Path.cwd()

    def operation() -> None:
        transport = McpTransport()
        result = bridge.run(
            transport,
            lambda t: deck_pipeline.pull_prototype(
                t, slug=args.slug, repo_root=repo_root
            ),
        )
        if result.unchanged:
            print(f"pull {args.slug} ({result.artifact}): unchanged")
        else:
            print(f"pulled {args.slug} ({result.artifact}) -> {result.local_path}")

    return dispatch(operation)


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
    ``operation`` completes without raising. Wired to ``deck seed`` (Story
    1.6, via ``_run_deck_seed``); also exercised directly in tests."""
    try:
        operation()
    except errors.HeraldError as exc:
        flat = " ".join(str(exc).splitlines())
        message = "".join(ch if ch.isprintable() else " " for ch in flat)
        print(f"{TOOL_NAME}: {type(exc).__name__}: {message}", file=sys.stderr)
        return errors.exit_code_for(exc)
    return 0
