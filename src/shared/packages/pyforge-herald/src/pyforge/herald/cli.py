"""The argparse CLI dispatcher (Story 1.1's skeleton; ``deck seed`` wired by
Story 1.6; Epic 6 -- Stories 6.1/6.2/6.3/6.5 -- extends it with the
``progress``/``success``/``notice`` Moment subcommands, shared global flags,
the operator-role write gate, and inline help).

``deck``'s own subparsers gained ``pull`` in Epic 2 (``status``/``watch``
still land in Epics 3-4). ``progress``/``success``/``notice`` are
placeholder handlers only -- their real Moment logic is
Epics 8/9/10's scope (Story 6.1's own AC says so explicitly: "handler
returns 'not yet implemented' or placeholder").

**Dispatcher (Story 6.1, AD-11).** One ``herald`` entry point; every
subcommand routes through ``_route``. Exit-code shape, reconciled with
``errors.py``'s existing map rather than inventing a parallel one:

* ``0`` -- success, or ``--help``/``--version`` (argparse's own exit).
* ``1`` -- a usage problem short of "which subcommand" (no command given at
  all), or any ``HeraldError`` ``dispatch`` catches whose type
  ``errors.exit_code_for`` has not mapped to a more specific code (that
  covers Story 6.2's ``InvalidDateRangeError`` and Story 6.3's
  ``OperatorAuthorizationError`` -- both fall through the existing map's
  default, unchanged).
* ``2`` -- an ``argparse``-detected usage error: unknown subcommand,
  unknown flag, missing required positional. 100% ``argparse``'s own exit
  (never rewritten here) -- only ``_HeraldArgumentParser.error``'s human-
  readable *text* is customized, per Story 6.5's "names the problem,
  suggests --help" AC.
* ``130`` -- ``KeyboardInterrupt`` during a subcommand's own operation (the
  implementation notes' interrupt convention; ``errors.py`` has no entry
  for it because a ``KeyboardInterrupt`` is never a ``HeraldError``).

``dispatch`` (Story 1.4) remains AD-6's sole ``HeraldError`` catch point;
every write subcommand's ``operation`` closure below still routes through
it exactly like ``deck seed`` always has, so a write-gate refusal
(``OperatorAuthorizationError``) or a bad ``--date-range``
(``InvalidDateRangeError``) gets the identical one-stderr-line/exit-code
treatment as any other ``HeraldError`` -- no parallel error-reporting path
was added for Epic 6.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from . import __version__, auth, bridge, deck_pipeline, errors
from .transport import McpTransport

TOOL_NAME = "herald"

TOP_LEVEL_COMMANDS = ("deck", "progress", "success", "notice")
"""Every top-level subcommand this dispatcher knows, in help/error-message
order. Extending this tuple is the whole of what Story 6.1's "Moment 5"
extensibility promise (AD-20) asks of a future subcommand's wiring here."""

_UNRECOGNIZED_RE = re.compile(r"unrecognized arguments: (\S+)")
_INVALID_CHOICE_RE = re.compile(r"invalid choice: '([^']*)' \(choose from (.+)\)")


class _HeraldArgumentParser(argparse.ArgumentParser):
    """``argparse.ArgumentParser`` with one hook: every usage-error message
    is reworded to this CLI's own wording (Story 6.1's "unknown command
    'x'"/Story 6.2's "unknown flag '--x'"/Story 6.5's "suggests --help"
    ACs) before the same ``exit(2)`` ``argparse`` already performs.

    Exit codes are never touched here -- only the text. Because
    ``add_subparsers`` sets ``parser_class=type(self)`` (stdlib behavior),
    building the top-level parser as this class makes every subparser --
    ``deck``, ``deck seed``, ``progress``, ``success``, ``success
    publish``, ``notice``, ``notice author`` -- inherit the same wording
    with no per-parser wiring."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {_reword_usage_error(message)}", file=sys.stderr)
        print("See --help for available options.", file=sys.stderr)
        self.exit(2)


def _reword_usage_error(message: str) -> str:
    """``argparse``'s own usage-error text, reworded to this CLI's
    conventions. Falls back to the original message unchanged for any
    shape this function does not specifically recognize -- a message this
    function cannot improve is still a real usage error, not a bug to hide.

    The invalid-choice branch reads its "valid subcommands" list straight
    out of argparse's own ``(choose from ...)`` clause rather than
    hardcoding ``TOP_LEVEL_COMMANDS`` -- this hook fires for *every*
    subparsers level this CLI has (``herald <bogus>`` at the top, but also
    ``herald deck <bogus>``, ``herald success <bogus>``, ...), and only
    argparse itself knows which choices applied at whichever level raised.
    A hardcoded top-level list would have been silently wrong for every
    nested level."""
    match = _UNRECOGNIZED_RE.search(message)
    if match is not None:
        return f"unknown flag {match.group(1)!r}"
    match = _INVALID_CHOICE_RE.search(message)
    if match is not None:
        value, choices = match.groups()
        return f"unknown command {value!r}; valid subcommands: {choices}"
    return message


def _global_flags_parent() -> argparse.ArgumentParser:
    """Story 6.2's shared ``--json``/``--date-range``/``--station`` flags,
    as a ``parents=[...]`` template -- defined once, attached to every
    Moment subcommand (``progress``/``success``/``notice``) below, so a
    future Moment 5 subcommand reuses it rather than redeclaring the three
    flags by hand."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="machine-readable JSON output (no colorization)",
    )
    parent.add_argument(
        "--date-range",
        metavar="<start>..<end>",
        default=None,
        help="filter to a date range, e.g. 2026-08-01..2026-08-31 (YYYY-MM-DD)",
    )
    parent.add_argument(
        "--station",
        "-s",
        default=None,
        help="filter to one station, e.g. warden",
    )
    return parent


def _build_parser() -> _HeraldArgumentParser:
    parser = _HeraldArgumentParser(
        prog=TOOL_NAME,
        description=(
            "Dream-to-deck bridge CLI -- seeds, pulls, and syncs Claude "
            "Design decks against this repo's docs/dreams/ and "
            "presentations/ trees; also the Herald Moments 2-4 CLI "
            "(progress/success/notice)."
        ),
        epilog=(
            "examples:\n"
            "  herald deck seed pyforge-warden\n"
            "  herald progress --json\n"
            "  herald progress --station warden "
            "--date-range 2026-08-01..2026-08-31\n"
            "  herald success publish claim-123\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(
        dest="command", required=False, metavar="command"
    )
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
    pull.add_argument(
        "--commit",
        action="store_true",
        help=(
            "commit the pulled + re-derived files to git (default: leave "
            "them uncommitted; never commits when the pull was unchanged)"
        ),
    )
    pull.add_argument(
        "--target",
        choices=[
            "prototype",
            "marp-deck",
            "marp-executive-summary",
            "marp-infographic",
            "standalone",
        ],
        default="prototype",
        help="which Design-side artifact to pull (default: prototype)",
    )
    # status/watch land in Epics 3-4, under this same deck_subparsers group.

    global_flags = _global_flags_parent()

    subparsers.add_parser(
        "progress",
        parents=[global_flags],
        help="show progress records (Moment 2; not yet implemented)",
        description="Show progress records. Read-only -- no operator role required.",
        epilog=(
            "examples:\n  herald progress\n  herald progress --json\n"
            "  herald progress --station warden "
            "--date-range 2026-08-01..2026-08-31\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    success = subparsers.add_parser(
        "success",
        parents=[global_flags],
        help="manage success claims (Moment 3; publish requires operator role)",
        description=(
            "List or publish success claims. Listing is read-only; "
            "publishing requires the operator role (AD-16)."
        ),
        epilog="examples:\n  herald success\n  herald success publish claim-123\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    success_subparsers = success.add_subparsers(
        dest="success_command", required=False, metavar="success_command"
    )
    publish = success_subparsers.add_parser(
        "publish", help="publish a success claim (requires operator role)"
    )
    publish.add_argument("claim_id", help="the claim id to publish")

    notice = subparsers.add_parser(
        "notice",
        parents=[global_flags],
        help="manage operational notices (Moment 4; author requires operator role)",
        description=(
            "List or author operational notices. Listing is read-only; "
            "authoring requires the operator role (AD-16)."
        ),
        epilog="examples:\n  herald notice\n  herald notice author weekly-update\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    notice_subparsers = notice.add_subparsers(
        dest="notice_command", required=False, metavar="notice_command"
    )
    author = notice_subparsers.add_parser(
        "author", help="author a notice (requires operator role)"
    )
    author.add_argument("name", help="the notice name/slug")

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
    if args.command is None:
        # Not an argparse usage error (the top-level subparsers group is
        # deliberately not `required=True`, unlike `deck`'s own nested
        # group) -- Story 6.1's AC calls for exit 1 here, not argparse's 2.
        parser.print_usage(sys.stderr)
        print(
            f"{TOOL_NAME}: error: no command given; valid subcommands: "
            f"{', '.join(TOP_LEVEL_COMMANDS)}",
            file=sys.stderr,
        )
        return 1
    try:
        return _route(args)
    except KeyboardInterrupt:
        return 130


def _route(args: argparse.Namespace) -> int:
    if args.command == "deck" and args.deck_command == "seed":
        return _run_deck_seed(args)
    if args.command == "deck" and args.deck_command == "pull":
        return _run_deck_pull(args)
    if args.command == "progress":
        return _run_progress(args)
    if args.command == "success":
        if getattr(args, "success_command", None) == "publish":
            return _run_success_publish(args)
        return _run_success_list(args)
    if args.command == "notice":
        if getattr(args, "notice_command", None) == "author":
            return _run_notice_author(args)
        return _run_notice_list(args)
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


def _pull_operation(
    args: argparse.Namespace, repo_root: Path, transport: McpTransport
) -> deck_pipeline.PullResult:
    """Compose the right ``deck_pipeline.pull_*`` call for ``args.target``.
    ``prototype`` (the default) dispatches to ``pull_prototype`` (Story 2.1);
    every ``marp-*`` choice dispatches to ``pull_marp_source`` with the
    ``marp-`` prefix stripped back to its ``kind`` (Story 2.3)."""
    if args.target == "prototype":
        return deck_pipeline.pull_prototype(
            transport, slug=args.slug, repo_root=repo_root, commit=args.commit
        )
    if args.target == "standalone":
        return deck_pipeline.pull_standalone_bundle(
            transport, slug=args.slug, repo_root=repo_root, commit=args.commit
        )
    kind = args.target.removeprefix("marp-")
    return deck_pipeline.pull_marp_source(
        transport,
        slug=args.slug,
        repo_root=repo_root,
        kind=kind,
        commit=args.commit,
    )


def _run_deck_pull(args: argparse.Namespace) -> int:
    """Compose ``bridge.run`` + the right ``deck_pipeline.pull_*`` call over
    the V1-default ``McpTransport`` and hand the whole operation to
    ``dispatch`` (AD-6), mirroring ``_run_deck_seed``'s composition shape
    exactly: ``McpTransport()`` is constructed inside ``operation``, never
    before ``dispatch`` is called."""
    repo_root = args.repo_root if args.repo_root is not None else Path.cwd()

    def operation() -> None:
        transport = McpTransport()
        result = bridge.run(transport, lambda t: _pull_operation(args, repo_root, t))
        if result.unchanged:
            print(f"pull {args.slug} ({result.artifact}): unchanged")
        else:
            suffix = " (committed)" if result.committed else ""
            print(
                f"pulled {args.slug} ({result.artifact}) -> {result.local_path}{suffix}"
            )

    return dispatch(operation)


def _parse_date_range(raw: str) -> tuple[date, date]:
    """``<start>..<end>`` (``YYYY-MM-DD`` each) -> a ``(start, end)`` pair.

    Raises ``errors.InvalidDateRangeError`` (Story 6.2) on any shape that
    does not parse -- deliberately *not* an ``argparse`` ``type=``
    validator, which would exit ``2``; the AC calls for exit ``1`` here, so
    parsing happens post-parse, inside a ``dispatch``-wrapped ``operation``.
    Uses ``date.fromisoformat`` (a ``date``, never a ``datetime``) rather
    than ``datetime.strptime`` -- there is no time component or timezone to
    a date range, so there is no naive-datetime footgun to construct
    around."""
    parts = raw.split("..")
    problem = (
        f"Invalid date format: {raw!r}; expected <start>..<end> as "
        f"YYYY-MM-DD..YYYY-MM-DD"
    )
    if len(parts) != 2:
        raise errors.InvalidDateRangeError(problem)
    start_raw, end_raw = parts
    try:
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
    except ValueError as exc:
        raise errors.InvalidDateRangeError(f"{problem} ({exc})") from exc
    return start, end


def _run_progress(args: argparse.Namespace) -> int:
    """``herald progress`` (Moment 2 placeholder, Story 6.1's AC: "handler
    returns 'not yet implemented'"). Read-only -- AD-16 requires no
    operator-role check for this path, and none is made."""

    def operation() -> None:
        date_range = _parse_date_range(args.date_range) if args.date_range else None
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "not yet implemented",
                        "station": args.station,
                        "date_range": (
                            [d.isoformat() for d in date_range]
                            if date_range is not None
                            else None
                        ),
                    }
                )
            )
        else:
            print("progress: not yet implemented")

    return dispatch(operation)


def _run_success_list(args: argparse.Namespace) -> int:
    """``herald success`` with no ``publish`` subcommand -- read-only
    listing placeholder, same shape as ``_run_progress``."""

    def operation() -> None:
        date_range = _parse_date_range(args.date_range) if args.date_range else None
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "not yet implemented",
                        "station": args.station,
                        "date_range": (
                            [d.isoformat() for d in date_range]
                            if date_range is not None
                            else None
                        ),
                    }
                )
            )
        else:
            print("success: not yet implemented")

    return dispatch(operation)


def _run_success_publish(args: argparse.Namespace) -> int:
    """``herald success publish <claim-id>`` -- Story 6.3's write-gated
    stub. ``auth.require_operator_role`` runs *before* anything else in
    ``operation``: a bypass would have to skip this call itself, not merely
    fail a check reachable after the "real" work already ran.

    The actual publish (validating evidence links via ``evidence.py``,
    persisting the claim) is Epic 9's scope -- this story's own AC says a
    stub that reaches "authorized, would proceed" is sufficient once past
    the gate."""

    def operation() -> None:
        auth.require_operator_role(
            auth.resolve_auth_context(), action="herald success publish"
        )
        if not auth.confirm("Continue? [Y/n] "):
            print("aborted: publish not confirmed")
            return
        print(
            f"authorized: would publish claim {args.claim_id!r} "
            f"(Epic 9 implements the actual publish)"
        )

    return dispatch(operation)


def _run_notice_list(args: argparse.Namespace) -> int:
    """``herald notice`` with no ``author`` subcommand -- read-only listing
    placeholder, same shape as ``_run_progress``."""

    def operation() -> None:
        date_range = _parse_date_range(args.date_range) if args.date_range else None
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "not yet implemented",
                        "station": args.station,
                        "date_range": (
                            [d.isoformat() for d in date_range]
                            if date_range is not None
                            else None
                        ),
                    }
                )
            )
        else:
            print("notice: not yet implemented")

    return dispatch(operation)


def _run_notice_author(args: argparse.Namespace) -> int:
    """``herald notice author <name>`` -- Story 6.3's write-gated stub,
    identical shape to ``_run_success_publish`` (same middleware, second
    caller -- proof it is a genuine reusable gate, not a one-off check
    wired to a single command)."""

    def operation() -> None:
        auth.require_operator_role(
            auth.resolve_auth_context(), action="herald notice author"
        )
        if not auth.confirm("Continue? [Y/n] "):
            print("aborted: notice not confirmed")
            return
        print(
            f"authorized: would author notice {args.name!r} "
            f"(Epic 10 implements the actual authoring)"
        )

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
    1.6), ``progress``/``success``/``notice`` (Epic 6); also exercised
    directly in tests."""
    try:
        operation()
    except errors.HeraldError as exc:
        flat = " ".join(str(exc).splitlines())
        message = "".join(ch if ch.isprintable() else " " for ch in flat)
        print(f"{TOOL_NAME}: {type(exc).__name__}: {message}", file=sys.stderr)
        return errors.exit_code_for(exc)
    return 0
