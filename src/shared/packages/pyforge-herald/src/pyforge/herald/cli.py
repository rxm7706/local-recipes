"""The argparse CLI dispatcher (Story 1.1's skeleton; ``deck seed`` wired by
Story 1.6; Epic 6 -- Stories 6.1/6.2/6.3/6.5 -- extends it with the
``progress``/``success``/``notice`` Moment subcommands, shared global flags,
the operator-role write gate, and inline help).

``deck``'s own subparsers gained ``pull`` in Epic 2, ``status`` in Epic 3,
``watch`` in Epic 4, and ``push`` in Epic 5 (Story 5.1 -- CAP-5 export
push-back). ``progress``/``success``/``notice`` are all real as of Epics
8/9/10: each is local-storage-backed (``progress.py``/``claims.py``/
``notices.py``, all scaled down from the epics doc's live-database/
webhook/cron design per the 2026-08-08 scope decision -- see
``docs/dreams/herald-moments-2-4-live-backend.md``), with an explicit CLI
command as the sole record-creation path (an operator runs it by hand;
there is no webhook anywhere in this module).

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
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

from . import (
    __version__,
    auth,
    bridge,
    claims,
    deck_pipeline,
    errors,
    notices,
    progress,
)
from . import watch as watch_module
from .claims import CLAIM_STATUSES
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


def _global_flags_parent_for_nested_subparser() -> argparse.ArgumentParser:
    """The same three flags as ``_global_flags_parent``, but with
    ``default=argparse.SUPPRESS`` -- for a SECOND-level subparser nested
    under a first-level one that already carries ``parents=[_global_flags_parent()]``
    (``notice list`` under ``notice``, both wanting ``--json`` et al).

    Regression: attaching a plain (non-suppressed) copy of these flags to
    ``notice list`` made ``herald notice list --json`` work, but broke
    ``herald notice --json list`` -- argparse's nested-subparsers action
    parses each level into its OWN fresh sub-namespace before merging it
    into the outer one, so ``list``'s own unset ``--json`` (default
    ``False``) silently overwrote the value `notice`'s own parser had
    already set to ``True``. With ``SUPPRESS``, an unset flag at the
    ``list`` level is simply absent from that merge instead of clobbering
    the outer value with a stale default -- verified against all three
    orderings (flag before the subcommand, after it, and absent)."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--json",
        "-j",
        action="store_true",
        default=argparse.SUPPRESS,
        help="machine-readable JSON output (no colorization)",
    )
    parent.add_argument(
        "--date-range",
        metavar="<start>..<end>",
        default=argparse.SUPPRESS,
        help="filter to a date range, e.g. 2026-08-01..2026-08-31 (YYYY-MM-DD)",
    )
    parent.add_argument(
        "--station",
        "-s",
        default=argparse.SUPPRESS,
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
    status = deck_subparsers.add_parser(
        "status",
        help="show one or all decks' bridge state, JSON (CAP-3)",
    )
    status.add_argument(
        "slug",
        nargs="?",
        default=None,
        help="deck slug, e.g. pyforge-warden (default: every known deck)",
    )
    status.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repo root containing presentations/<slug>/ (default: cwd)",
    )
    watch = deck_subparsers.add_parser(
        "watch",
        help=(
            "poll one or more decks for Design-side edits and pull "
            "automatically once settled (CAP-4)"
        ),
    )
    watch.add_argument(
        "slugs", nargs="+", metavar="slug", help="deck slug(s), e.g. pyforge-warden"
    )
    watch.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repo root containing presentations/<slug>/ (default: cwd)",
    )
    watch.add_argument(
        "--interval",
        type=float,
        default=watch_module.DEFAULT_POLL_INTERVAL,
        help=(
            f"poll interval in seconds (default: "
            f"{watch_module.DEFAULT_POLL_INTERVAL:g}; floor: "
            f"{watch_module.MIN_POLL_INTERVAL:g})"
        ),
    )
    push = deck_subparsers.add_parser(
        "push",
        help="push regenerated derived exports back into Claude Design (CAP-5)",
    )
    push.add_argument("slug", help="deck slug, e.g. pyforge-warden")
    push.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repo root containing presentations/<slug>/ (default: cwd)",
    )

    global_flags = _global_flags_parent()

    progress_parser = subparsers.add_parser(
        "progress",
        parents=[global_flags],
        help="show or record progress (Moment 2)",
        description=(
            "Show progress records, or record one after a ship. Listing "
            "(no <station>, or --list) is read-only; --update writes and "
            "requires the operator role (AD-16)."
        ),
        epilog=(
            "examples:\n"
            "  herald progress\n"
            "  herald progress warden\n"
            "  herald progress warden --update --shipped 'Harness Policy' "
            "--compute-hours 3.5 --token-spend 42000 --wall-clock-hours 6\n"
            "  herald progress --list --station warden "
            "--date-range 2026-08-01..2026-08-31\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    progress_parser.add_argument(
        "station_arg",
        nargs="?",
        default=None,
        metavar="station",
        help="station to show (or, with --update, record progress for)",
    )
    progress_parser.add_argument(
        "--update",
        action="store_true",
        help="record today's progress for <station> (requires operator role)",
    )
    progress_parser.add_argument(
        "--list",
        action="store_true",
        help="list progress records (default when no <station> is given)",
    )
    progress_parser.add_argument(
        "--shipped",
        action="append",
        dest="shipped",
        metavar="<capability>",
        default=None,
        help="a shipped capability (repeatable; --update only)",
    )
    progress_parser.add_argument(
        "--compute-hours",
        type=float,
        default=None,
        help="compute hours (--update only)",
    )
    progress_parser.add_argument(
        "--token-spend", type=int, default=None, help="token spend (--update only)"
    )
    progress_parser.add_argument(
        "--wall-clock-hours",
        type=float,
        default=None,
        help="wall-clock hours (--update only)",
    )
    progress_parser.add_argument(
        "--unblock-narrative",
        default=None,
        help="unblock narrative (--update only; prompted interactively if omitted)",
    )

    success = subparsers.add_parser(
        "success",
        parents=[global_flags],
        help="manage success claims (Moment 3; publish requires operator role)",
        description=(
            "List, review, or publish success claims. Listing/review is "
            "read-only; create/publish/validate write local storage, and "
            "publish requires the operator role (AD-16)."
        ),
        epilog=(
            "examples:\n"
            "  herald success create warden --evidence-test-results "
            "https://example/tests\n"
            "  herald success review claim-123\n"
            "  herald success publish claim-123 --thesis 'Shipped X'\n"
            "  herald success list --status draft\n"
            "  herald success get claim-123\n"
            "  herald success validate claim-123\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    success.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repo root containing .herald/claims.json (default: cwd)",
    )
    success_subparsers = success.add_subparsers(
        dest="success_command", required=False, metavar="success_command"
    )
    success_create = success_subparsers.add_parser(
        "create",
        help=(
            "create a draft success claim from CLI flags (Story 9.2 -- "
            "scaled down from a CI webhook to an operator-run command)"
        ),
    )
    success_create.add_argument(
        "project_name", help="the project name, e.g. 'Marshal S-1.10'"
    )
    success_create.add_argument(
        "--shipped-date",
        metavar="YYYY-MM-DD",
        default=None,
        help="shipped date (default: today)",
    )
    success_create.add_argument(
        "--evidence-test-results",
        metavar="<url>",
        default=None,
        help="evidence link: test results",
    )
    success_create.add_argument(
        "--evidence-metrics",
        metavar="<url>",
        default=None,
        help="evidence link: metrics",
    )
    success_create.add_argument(
        "--evidence-adoption",
        metavar="<url>",
        default=None,
        help="evidence link: adoption signal",
    )
    success_create.add_argument(
        "--evidence-notice",
        metavar="<component>",
        default=None,
        help=(
            "evidence link: an operations notice's component name "
            "(Story 11.3 cross-Moment backlink; must already exist)"
        ),
    )
    success_review = success_subparsers.add_parser(
        "review", help="show a draft claim's evidence before publishing"
    )
    success_review.add_argument("claim_id", help="the claim id to review")
    publish = success_subparsers.add_parser(
        "publish", help="publish a success claim (requires operator role)"
    )
    publish.add_argument("claim_id", help="the claim id to publish")
    publish.add_argument(
        "--thesis",
        default=None,
        help="the published thesis text (required if the claim has none yet)",
    )
    success_list = success_subparsers.add_parser(
        "list", help="list success claims (same as `herald success` with no subcommand)"
    )
    success_list.add_argument(
        "--status",
        choices=CLAIM_STATUSES,
        default=None,
        help="filter to one status (default: every status)",
    )
    success_get = success_subparsers.add_parser(
        "get", help="show full detail for one claim"
    )
    success_get.add_argument("claim_id", help="the claim id")
    success_validate = success_subparsers.add_parser(
        "validate",
        help=(
            "re-check evidence links for one claim or every claim (Story "
            "9.5 -- scaled down from a weekly cron to an operator-run check)"
        ),
    )
    success_validate.add_argument(
        "claim_id", nargs="?", default=None, help="the claim id (omit with --all)"
    )
    success_validate.add_argument(
        "--all", action="store_true", help="re-validate every claim's evidence links"
    )

    notice = subparsers.add_parser(
        "notice",
        parents=[global_flags],
        help="manage operational notices (Moment 4; author/publish/close/archive require operator role)",
        description=(
            "List, author, publish, close, or archive operational notices. "
            "Listing and `get` are read-only; author/publish/close/archive "
            "require the operator role (AD-16)."
        ),
        epilog=(
            "examples:\n"
            "  herald notice\n"
            "  herald notice list --category deprecation\n"
            "  herald notice author --type deprecation --component auth-api-v1 "
            '--what "..." --why "..." --migration "..." --deadline 2026-09-01\n'
            "  herald notice publish auth-api-v1\n"
            "  herald notice get auth-api-v1\n"
            '  herald notice close auth-api-v1 --reason "migration complete"\n'
            "  herald notice archive --rename old-name new-name\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    notice_subparsers = notice.add_subparsers(
        dest="notice_command", required=False, metavar="notice_command"
    )

    notice_list = notice_subparsers.add_parser(
        "list",
        parents=[_global_flags_parent_for_nested_subparser()],
        help="list operational notices (read-only)",
    )
    notice_list.add_argument(
        "--category",
        choices=notices.NOTICE_TYPES,
        default=None,
        help="filter to one notice type",
    )
    notice_list.add_argument(
        "--status",
        choices=(*notices.NOTICE_STATUSES, "all"),
        default=None,
        help="filter to one lifecycle status (default: published + closed, no drafts)",
    )

    author = notice_subparsers.add_parser(
        "author", help="author (or re-author a draft) notice (requires operator role)"
    )
    author.add_argument(
        "--type", dest="notice_type", choices=notices.NOTICE_TYPES, default=None
    )
    author.add_argument("--component", default=None, help="the notice's component name")
    author.add_argument("--what", default=None)
    author.add_argument("--why", default=None)
    author.add_argument("--migration", default=None)
    author.add_argument("--deadline", default=None, help="YYYY-MM-DD (optional)")
    author.add_argument(
        "--reason-link",
        dest="reason_link",
        default=None,
        help="evidence URL (optional)",
    )
    author.add_argument(
        "--publish",
        action="store_true",
        help="publish immediately instead of leaving it a draft",
    )

    notice_publish = notice_subparsers.add_parser(
        "publish", help="publish a draft notice (requires operator role)"
    )
    notice_publish.add_argument("component", help="the notice's component name")

    notice_get = notice_subparsers.add_parser(
        "get", help="show one notice's full detail, following any rename redirect"
    )
    notice_get.add_argument("component", help="the notice's component name")

    notice_close = notice_subparsers.add_parser(
        "close", help="close a published notice (requires operator role)"
    )
    notice_close.add_argument("component", help="the notice's component name")
    notice_close.add_argument(
        "--reason", default=None, help="why it was closed (optional)"
    )

    notice_archive = notice_subparsers.add_parser(
        "archive",
        help="archive bookkeeping: record a rename redirect (requires operator role)",
    )
    notice_archive.add_argument(
        "--rename",
        nargs=2,
        metavar=("OLD", "NEW"),
        required=True,
        help="redirect OLD component's lookups to NEW (NEW must already have a notice)",
    )

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
    if args.command == "deck" and args.deck_command == "status":
        return _run_deck_status(args)
    if args.command == "deck" and args.deck_command == "watch":
        return _run_deck_watch(args)
    if args.command == "deck" and args.deck_command == "push":
        return _run_deck_push(args)
    if args.command == "progress":
        return _run_progress(args)
    if args.command == "success":
        success_command = getattr(args, "success_command", None)
        if success_command == "create":
            return _run_success_create(args)
        if success_command == "review":
            return _run_success_review(args)
        if success_command == "publish":
            return _run_success_publish(args)
        if success_command == "get":
            return _run_success_get(args)
        if success_command == "validate":
            return _run_success_validate(args)
        return _run_success_list(args)
    if args.command == "notice":
        notice_command = getattr(args, "notice_command", None)
        if notice_command == "author":
            return _run_notice_author(args)
        if notice_command == "publish":
            return _run_notice_publish(args)
        if notice_command == "get":
            return _run_notice_get(args)
        if notice_command == "close":
            return _run_notice_close(args)
        if notice_command == "archive":
            return _run_notice_archive(args)
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


def _run_deck_status(args: argparse.Namespace) -> int:
    """Compose ``bridge.run`` + ``deck_pipeline.status`` over the
    V1-default ``McpTransport`` and hand the whole operation to
    ``dispatch`` (AD-6), mirroring ``_run_deck_seed``/``_run_deck_pull``'s
    composition shape exactly: ``McpTransport()`` is constructed inside
    ``operation``, never before ``dispatch`` is called.

    Always prints one JSON array to stdout (FR-11's "machine-readable" AC)
    -- unlike ``seed``/``pull``, there is no separate human-prose success
    line: the report itself is the whole output, for one deck or every
    known one alike."""
    repo_root = args.repo_root if args.repo_root is not None else Path.cwd()

    def operation() -> None:
        transport = McpTransport()
        results = bridge.run(
            transport,
            lambda t: deck_pipeline.status(t, slug=args.slug, repo_root=repo_root),
        )
        print(
            json.dumps(
                [
                    {
                        "slug": result.slug,
                        "linked": result.linked,
                        "project_id": result.project_id,
                        "sync": result.sync,
                        "last_pull": result.last_pull,
                        "stale_mirror": result.stale_mirror,
                    }
                    for result in results
                ]
            )
        )

    return dispatch(operation)


def _run_deck_watch(args: argparse.Namespace) -> int:
    """Compose ``bridge.run`` + ``watch.watch`` over the V1-default
    ``McpTransport`` and hand the whole (long-running) operation to
    ``dispatch`` (AD-6), mirroring ``_run_deck_seed``/``_run_deck_pull``'s
    composition shape exactly: ``McpTransport()`` is constructed inside
    ``operation``, never before ``dispatch`` is called.

    An ``AuthError`` raised mid-loop (Story 4.3) is caught by ``dispatch``
    exactly like every other ``HeraldError`` -- that is what halts every
    watched deck at once, with ``dispatch``'s usual one-stderr-line/exit-code
    reporting and no parallel error path."""
    repo_root = args.repo_root if args.repo_root is not None else Path.cwd()

    def operation() -> None:
        transport = McpTransport()
        bridge.run(
            transport,
            lambda t: watch_module.watch(
                t,
                slugs=args.slugs,
                repo_root=repo_root,
                interval=args.interval,
            ),
        )

    return dispatch(operation)


def _run_deck_push(args: argparse.Namespace) -> int:
    """Compose ``bridge.run`` + ``deck_pipeline.push_exports`` over the
    V1-default ``McpTransport`` and hand the whole operation to
    ``dispatch`` (AD-6), mirroring ``_run_deck_seed``/``_run_deck_pull``'s
    composition shape exactly: ``McpTransport()`` is constructed inside
    ``operation``, never before ``dispatch`` is called.

    ``herald deck push`` is a standalone subcommand rather than an
    auto-trigger tacked onto ``deck pull``'s completion (Story 5.1's own
    design choice, recorded in its spec's Dev Notes): a pull's own
    re-derivation already runs ``deck-export`` for every artifact kind
    (prototype, each Marp source, the standalone bundle) and each can
    fail or be re-run independently of any other, so folding a Design
    write into that same call would make ``deck pull``'s success/failure
    story conditional on ``deck push``'s too. Keeping them as separate
    subcommands mirrors ``deck seed``/``deck pull``'s own separation and
    lets an operator re-run just the push after fixing a conflict without
    re-pulling anything."""
    repo_root = args.repo_root if args.repo_root is not None else Path.cwd()

    def operation() -> None:
        transport = McpTransport()
        result = bridge.run(
            transport,
            lambda t: deck_pipeline.push_exports(
                t, slug=args.slug, repo_root=repo_root
            ),
        )
        if not result.pushed and not result.skipped:
            print(f"push {args.slug}: nothing to push")
        else:
            print(
                f"pushed {args.slug}: {len(result.pushed)} file(s) pushed, "
                f"{len(result.skipped)} unchanged"
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
    if start > end:
        raise errors.InvalidDateRangeError(
            f"Invalid date range: {raw!r}; start ({start}) is after end ({end})"
        )
    return start, end


def _progress_path() -> Path:
    """The local progress store, resolved against the cwd -- mirrors
    ``progress.py``'s own explicit-``Path``-argument convention (this is the
    one place that resolves it against a real repo root; ``progress.py``
    itself never assumes a cwd)."""
    return Path.cwd() / progress.DEFAULT_PROGRESS_PATH


def _validate_station(station: str) -> None:
    """Raises ``errors.HeraldError`` naming the unrecognized station and
    every known one, per Story 8.3's AC ("Station 'unknown' not found.
    Available: warden, atlas, marshal, ...")."""
    if station not in progress.STATIONS:
        raise errors.HeraldError(
            f"Station {station!r} not found. Available: "
            f"{', '.join(progress.STATIONS)}. Use --list to see recorded "
            f"stations."
        )


def _prompt_unblock_narrative(
    station: str, on_date: str, *, reader: Callable[[str], str] = input
) -> str:
    """Story 8.2's scaled-down "operator prompted for the unblock
    narrative" AC: a plain text prompt (rather than the original webhook
    flow's draft-then-fill-in-later shape), reusing ``auth.confirm``'s
    injectable-``reader`` seam so a test never blocks on real stdin. A
    blank answer or ``EOFError`` records an empty narrative rather than
    aborting the whole update -- an operator without a narrative yet should
    still be able to record the rest of the ship."""
    try:
        answer = reader(
            f"Unblock narrative for {station} on {on_date} (blank for none): "
        )
    except EOFError:
        return ""
    return answer.strip()


def _format_progress_record(record: progress.Progress) -> str:
    capabilities = ", ".join(record.shipped_capabilities) or "(none)"
    return (
        f"station: {record.station}\n"
        f"date: {record.date}\n"
        f"shipped_capabilities: {capabilities}\n"
        f"compute_hours: {record.compute_hours}\n"
        f"token_spend: {record.token_spend}\n"
        f"wall_clock_hours: {record.wall_clock_hours}\n"
        f"unblock_narrative: {record.unblock_narrative or '(none)'}"
    )


def _run_progress_update(args: argparse.Namespace, station: str) -> None:
    """``herald progress <station> --update`` -- Story 8.2/8.3's write path
    (AD-16 names ``herald progress --update`` explicitly as a future
    operator-gated write in ``auth.py``'s own docstring). Records today's
    progress from explicit flags -- the scoped-down interpretation of the
    original AC's "extracted from bmad-loop journal / CI webhook payload"
    (see ``docs/dreams/herald-moments-2-4-live-backend.md``)."""
    auth.require_operator_role(
        auth.resolve_auth_context(), action="herald progress --update"
    )
    _validate_station(station)
    on_date = datetime.now(UTC).date().isoformat()
    narrative = (
        args.unblock_narrative
        if args.unblock_narrative is not None
        else _prompt_unblock_narrative(station, on_date)
    )
    record = progress.upsert(
        _progress_path(),
        station=station,
        date=on_date,
        shipped_capabilities=list(args.shipped) if args.shipped else [],
        compute_hours=args.compute_hours if args.compute_hours is not None else 0.0,
        token_spend=args.token_spend if args.token_spend is not None else 0,
        wall_clock_hours=(
            args.wall_clock_hours if args.wall_clock_hours is not None else 0.0
        ),
        unblock_narrative=narrative,
    )
    if args.json:
        print(json.dumps(asdict(record)))
    else:
        print(f"Progress updated for {station}")


def _run_progress_show(args: argparse.Namespace, station: str) -> None:
    """``herald progress <station>`` -- the latest record for one station."""
    _validate_station(station)
    record = progress.latest_for_station(_progress_path(), station)
    if record is None:
        if args.json:
            print(json.dumps({"station": station, "record": None}))
        else:
            print(f"No progress recorded for {station}.")
        return
    if args.json:
        print(json.dumps(asdict(record)))
    else:
        print(_format_progress_record(record))


def _run_progress_list(args: argparse.Namespace) -> None:
    """``herald progress`` (bare) or ``herald progress --list`` -- every
    record matching the shared ``--station``/``--date-range`` filters,
    newest first. NDJSON with ``--json`` (Story 8.3's AC), a one-line
    summary per record otherwise."""
    if args.station is not None:
        _validate_station(args.station)
    date_range = (
        _parse_date_range(args.date_range) if args.date_range is not None else None
    )
    records = progress.list_records(
        _progress_path(), station=args.station, date_range=date_range
    )
    if args.json:
        for record in records:
            print(json.dumps(asdict(record)))
        return
    if not records:
        print("No progress records found.")
        return
    for record in records:
        print(
            f"{record.date}  {record.station}  "
            f"{len(record.shipped_capabilities)} capabilities  "
            f"compute={record.compute_hours}h  token_spend={record.token_spend}  "
            f"wall_clock={record.wall_clock_hours}h"
        )


def _run_progress(args: argparse.Namespace) -> int:
    """``herald progress`` (Moment 2, Stories 8.1-8.3). Three shapes:
    ``<station>`` (latest record), ``<station> --update`` (write, operator
    role required), and no station / ``--list`` (filtered listing,
    read-only). Listing never checks auth (AD-16); only ``--update`` does."""

    def operation() -> None:
        if args.station_arg is not None:
            if args.update:
                _run_progress_update(args, args.station_arg)
            else:
                _run_progress_show(args, args.station_arg)
        else:
            _run_progress_list(args)

    return dispatch(operation, json_output=args.json)


def _success_claims_path(args: argparse.Namespace) -> Path:
    """Resolve ``.herald/claims.json`` under ``args.repo_root`` (default:
    cwd) -- shared by every ``success`` subcommand handler below."""
    repo_root = args.repo_root if args.repo_root is not None else Path.cwd()
    return repo_root / claims.DEFAULT_CLAIMS_PATH


def _run_success_create(args: argparse.Namespace) -> int:
    """``herald success create <project>`` (Story 9.2, scaled down): the
    CLI-triggered replacement for the original spec's PR-close webhook --
    an operator supplies the fields the webhook payload would have carried
    (project name, shipped date, evidence links) directly as flags. No
    operator-role gate: creating a *draft* is the scaled-down equivalent of
    the webhook firing automatically, which the original spec never gated
    on a role either -- only *publishing* is gated (AD-16)."""
    claims_path = _success_claims_path(args)

    def operation() -> None:
        evidence = []
        if args.evidence_test_results:
            evidence.append(
                claims.Evidence(
                    type="test_results",
                    url=args.evidence_test_results,
                    label="test results",
                )
            )
        if args.evidence_metrics:
            evidence.append(
                claims.Evidence(
                    type="metrics", url=args.evidence_metrics, label="metrics"
                )
            )
        if args.evidence_adoption:
            evidence.append(
                claims.Evidence(
                    type="adoption", url=args.evidence_adoption, label="adoption"
                )
            )
        if args.evidence_notice:
            # Verify the referenced notice actually exists before citing it
            # -- `notices.get_notice` raises `errors.HeraldError` (caught by
            # `dispatch` like any other) naming the unresolved component,
            # rather than letting a claim silently cite a notice that was
            # never authored (or was mistyped).
            repo_root = args.repo_root if args.repo_root is not None else Path.cwd()
            notices.get_notice(repo_root, args.evidence_notice)
            evidence.append(
                claims.Evidence(
                    type="notice",
                    url=args.evidence_notice,
                    label=f"notice: {args.evidence_notice}",
                )
            )
        claim = claims.create(
            claims_path,
            project_name=args.project_name,
            shipped_date=args.shipped_date,
            evidence=evidence,
        )
        print(f"created draft claim {claim.id} for {claim.project_name!r}")
        print(f"review with: herald success review {claim.id}")

    return dispatch(operation)


def _run_success_review(args: argparse.Namespace) -> int:
    """``herald success review <claim-id>`` (Story 9.2/9.3's review gate):
    read-only display of a claim's evidence, ahead of the operator-gated
    ``herald success publish``. Deliberately does not itself prompt to
    publish inline -- keeping ``publish`` as the sole path through
    ``auth.require_operator_role`` (Story 6.3's existing gate boundary)
    means there is exactly one place a bypass would have to defeat."""
    claims_path = _success_claims_path(args)

    def operation() -> None:
        claim = claims.read_one(claims_path, args.claim_id)
        print(f"claim {claim.id}: {claim.project_name} (status={claim.status})")
        print(f"shipped: {claim.shipped_date or '(unset)'}")
        print(f"thesis: {claim.thesis or '(none yet)'}")
        if claim.evidence:
            print("evidence:")
            for item in claim.evidence:
                mark = "validated" if item.validated else "unvalidated"
                print(f"  - [{item.type}] {item.label}: {item.url} ({mark})")
        else:
            print("evidence: (none)")
        if claim.status == "draft":
            print(f'to publish: herald success publish {claim.id} --thesis "..."')

    return dispatch(operation)


def _run_success_publish(args: argparse.Namespace) -> int:
    """``herald success publish <claim-id> [--thesis ...]`` -- Story 6.3's
    write-gated stub, now doing the real work (Story 9.3 + 9.5).
    ``auth.require_operator_role`` runs *before* anything else in
    ``operation``: a bypass would have to skip this call itself, not merely
    fail a check reachable after the "real" work already ran. Evidence
    links are validated via ``evidence.validate_for_publish`` (Story 6.4's
    shared protocol) inside ``claims.publish`` -- a broken link raises
    ``EvidenceLinkError`` before anything is persisted."""
    claims_path = _success_claims_path(args)

    def operation() -> None:
        auth.require_operator_role(
            auth.resolve_auth_context(), action="herald success publish"
        )
        if not auth.confirm("Continue? [Y/n] "):
            print("aborted: publish not confirmed")
            return
        claim = claims.publish(claims_path, args.claim_id, thesis=args.thesis)
        print(
            f"published claim {claim.id} for {claim.project_name} "
            f"on {claim.shipped_date}"
        )

    return dispatch(operation)


def _run_success_list(args: argparse.Namespace) -> int:
    """``herald success`` with no subcommand, or ``herald success list``
    (Story 9.3): read-only listing over ``claims.json``, optionally
    filtered by ``--status`` and/or the shared ``--date-range`` (matched
    against each claim's ``shipped_date``)."""
    claims_path = _success_claims_path(args)

    def operation() -> None:
        date_range = (
            _parse_date_range(args.date_range) if args.date_range is not None else None
        )
        status = getattr(args, "status", None)
        results = claims.list_claims(claims_path, status=status, date_range=date_range)
        if args.json:
            for claim in results:
                print(json.dumps(claims.to_dict(claim)))
        elif not results:
            print("success: no claims found")
        else:
            for claim in results:
                print(
                    f"{claim.id}  {claim.status:<9}  {claim.project_name}  "
                    f"{claim.shipped_date or '-'}  evidence={len(claim.evidence)}"
                )

    return dispatch(operation, json_output=args.json)


def _run_success_get(args: argparse.Namespace) -> int:
    """``herald success get <claim-id>`` (Story 9.3): full claim detail,
    read-only."""
    claims_path = _success_claims_path(args)

    def operation() -> None:
        claim = claims.read_one(claims_path, args.claim_id)
        if args.json:
            print(json.dumps(claims.to_dict(claim)))
            return
        print(f"id: {claim.id}")
        print(f"project_name: {claim.project_name}")
        print(f"status: {claim.status}")
        print(f"thesis: {claim.thesis or '(none)'}")
        print(f"shipped_date: {claim.shipped_date or '(unset)'}")
        print(f"created_at: {claim.created_at}")
        print(f"published_at: {claim.published_at or '(unset)'}")
        print(f"closed_at: {claim.closed_at or '(unset)'}")
        print(f"updated_at: {claim.updated_at}")
        print("evidence:")
        for item in claim.evidence:
            mark = "validated" if item.validated else "unvalidated"
            print(f"  - [{item.type}] {item.label}: {item.url} ({mark})")
        print("edit_history:")
        for version in claim.edit_history:
            print(f"  - {version.edited_at}: {version.thesis}")

    return dispatch(operation, json_output=args.json)


def _run_success_validate(args: argparse.Namespace) -> int:
    """``herald success validate <claim-id> | --all`` (Story 9.5, scaled
    down): the operator-run replacement for the original spec's weekly
    async re-validation cron -- re-checks evidence links via
    ``evidence.validate_link`` (never raises; this command's whole point is
    to surface breakage, not reject it) and updates
    ``validated``/``validated_at``."""
    claims_path = _success_claims_path(args)

    def operation() -> None:
        if bool(args.claim_id) == bool(args.all):
            raise errors.HeraldError(
                "herald success validate: supply exactly one of <claim-id> or --all"
            )
        if args.all:
            updated = claims.revalidate_all(claims_path)
            print(f"revalidated evidence for {len(updated)} claim(s)")
        else:
            claim = claims.revalidate(claims_path, args.claim_id)
            broken = sum(1 for item in claim.evidence if not item.validated)
            total = len(claim.evidence)
            print(
                f"revalidated claim {claim.id}: {total - broken}/{total} "
                f"evidence link(s) valid"
            )

    return dispatch(operation)


def _notice_summary_line(notice: notices.Notice) -> str:
    deadline = f" (deadline {notice.deadline})" if notice.deadline else ""
    return f"[{notice.status}] {notice.type}/{notice.component}{deadline}"


def _notice_to_json(
    notice: notices.Notice, *, referenced_by: list[claims.Claim] = ()
) -> dict:
    return {
        "type": notice.type,
        "component": notice.component,
        "what": notice.what,
        "why": notice.why,
        "migration": notice.migration,
        "deadline": notice.deadline,
        "reason_link": notice.reason_link,
        "status": notice.status,
        "path": notice.path,
        "created_at": notice.created_at,
        "published_at": notice.published_at,
        "closed_at": notice.closed_at,
        "closed_by": notice.closed_by,
        "close_reason": notice.close_reason,
        "revisions": list(notice.revisions),
        "referenced_by_claims": [
            {"id": c.id, "project_name": c.project_name, "status": c.status}
            for c in referenced_by
        ],
    }


def _run_notice_list(args: argparse.Namespace) -> int:
    """``herald notice`` (bare) or ``herald notice list`` -- read-only
    listing (Story 10.3/10.4/10.6). Draft notices are excluded unless
    ``--status draft``/``--status all`` was explicitly requested (Story
    10.6's AC: drafts are invisible by default, same as Success's
    draft/published distinction)."""
    category = getattr(args, "category", None)
    status = getattr(args, "status", None)

    def operation() -> None:
        date_range = (
            _parse_date_range(args.date_range) if args.date_range is not None else None
        )
        str_date_range = (
            (date_range[0].isoformat(), date_range[1].isoformat())
            if date_range is not None
            else None
        )
        results = notices.list_notices(
            Path.cwd(), category=category, date_range=str_date_range, status=status
        )
        if args.json:
            print(json.dumps([_notice_to_json(n) for n in results]))
        elif not results:
            print("notice: no notices found")
        else:
            for notice in results:
                print(_notice_summary_line(notice))

    return dispatch(operation, json_output=args.json)


def _run_notice_author(args: argparse.Namespace) -> int:
    """``herald notice author`` (Story 10.2/10.4) -- Story 6.3's write gate,
    still the first thing this handler does, followed by an interactive
    prompt for any required field not given on the command line, then the
    usual ``Continue? [Y/n]`` confirmation before anything is written."""

    def operation() -> None:
        auth.require_operator_role(
            auth.resolve_auth_context(), action="herald notice author"
        )
        notice_type = args.notice_type or _prompt(
            f"type ({'/'.join(notices.NOTICE_TYPES)})",
            validate=lambda v: v in notices.NOTICE_TYPES,
        )
        component = args.component or _prompt("component")
        what = args.what or _prompt("what")
        why = args.why or _prompt("why")
        migration = args.migration or _prompt("migration")
        deadline = (
            args.deadline
            if args.deadline
            else _prompt("deadline (YYYY-MM-DD, optional)", required=False)
        )
        reason_link = args.reason_link

        if not auth.confirm("Continue? [Y/n] "):
            print("aborted: notice not authored")
            return
        notice = notices.author_notice(
            Path.cwd(),
            notice_type=notice_type,
            component=component,
            what=what,
            why=why,
            migration=migration,
            deadline=deadline or None,
            reason_link=reason_link,
            publish=args.publish,
        )
        print(
            f"authored notice {notice.component!r} ({notice.status}) -> {notice.path}"
        )

    return dispatch(operation)


def _run_notice_publish(args: argparse.Namespace) -> int:
    """``herald notice publish <component>`` (Story 10.2/10.6) -- draft ->
    published, gated the same as ``notice author``."""

    def operation() -> None:
        auth.require_operator_role(
            auth.resolve_auth_context(), action="herald notice publish"
        )
        if not auth.confirm("Continue? [Y/n] "):
            print("aborted: notice not published")
            return
        notice = notices.publish_notice(Path.cwd(), args.component)
        print(f"published notice {notice.component!r}")

    return dispatch(operation)


def _run_notice_get(args: argparse.Namespace) -> int:
    """``herald notice get <component>`` -- read-only full detail,
    following a rename redirect (Story 10.3). Also shows Story 11.3's
    cross-Moment backlink: every claim citing this notice as evidence
    (``claims.referenced_by_claims``, computed fresh from ``claims.json`` --
    not stored on the notice itself, see ``claims.py``'s module docstring)."""

    def operation() -> None:
        notice = notices.get_notice(Path.cwd(), args.component)
        referenced_by = claims.referenced_by_claims(
            Path.cwd() / claims.DEFAULT_CLAIMS_PATH, notice.component
        )
        if args.json:
            print(json.dumps(_notice_to_json(notice, referenced_by=referenced_by)))
        else:
            print(_notice_summary_line(notice))
            print(f"what: {notice.what}")
            print(f"why: {notice.why}")
            print(f"migration: {notice.migration}")
            print(f"path: {notice.path}")
            if referenced_by:
                print("referenced by claims:")
                for c in referenced_by:
                    print(f"  - {c.id}  {c.project_name}  ({c.status})")

    return dispatch(operation, json_output=args.json)


def _run_notice_close(args: argparse.Namespace) -> int:
    """``herald notice close <component> [--reason ...]`` (Story 10.6) --
    published -> closed, gated the same as ``notice author``. ``closed_by``
    is best-effort (see ``notices.py``'s module docstring on the operator-
    identity gap): the resolved auth context's role/source string when one
    is available, else ``notices.UNKNOWN_OPERATOR``."""

    def operation() -> None:
        context = auth.require_operator_role(
            auth.resolve_auth_context(), action="herald notice close"
        )
        if not auth.confirm("Continue? [Y/n] "):
            print("aborted: notice not closed")
            return
        notice = notices.close_notice(
            Path.cwd(),
            args.component,
            reason=args.reason,
            closed_by=f"{context.role}:{context.source}",
        )
        print(f"closed notice {notice.component!r}")

    return dispatch(operation)


def _run_notice_archive(args: argparse.Namespace) -> int:
    """``herald notice archive --rename OLD NEW`` (Story 10.3) -- file-based
    redirect bookkeeping only (no HTTP redirect; no server exists to serve
    one), gated the same as ``notice author``."""

    def operation() -> None:
        auth.require_operator_role(
            auth.resolve_auth_context(), action="herald notice archive"
        )
        old_component, new_component = args.rename
        if not auth.confirm(f"Redirect {old_component!r} -> {new_component!r}? [Y/n] "):
            print("aborted: redirect not recorded")
            return
        notices.archive_rename(Path.cwd(), old_component, new_component)
        print(f"redirect recorded: {old_component!r} -> {new_component!r}")

    return dispatch(operation)


def _prompt(
    field: str,
    *,
    reader: Callable[[str], str] = input,
    required: bool = True,
    validate: Callable[[str], bool] | None = None,
) -> str:
    """A ``"<field>: "``-shaped prompt for any required notice field not
    given on the command line (Story 10.2's AC), mirroring ``auth.confirm``'s
    injectable-``reader`` convention so a test never blocks on real stdin.
    Re-prompts on an empty answer when ``required`` (default), or on an
    answer ``validate`` rejects; returns the first blank answer unchanged
    when ``required=False``."""
    while True:
        try:
            answer = reader(f"{field}: ").strip()
        except EOFError:
            answer = ""
        if not answer:
            if not required:
                return answer
            print(f"{field} is required.")
            continue
        if validate is not None and not validate(answer):
            print(f"invalid value for {field}.")
            continue
        return answer


def dispatch(operation: Callable[[], None], *, json_output: bool = False) -> int:
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
    directly in tests.

    ``json_output`` (Epic 6 review fix): callers that parsed ``--json``
    pass ``args.json`` through so a ``HeraldError`` on those paths renders
    as one JSON object on stderr instead of the plain-text line -- a
    ``--json`` caller parsing stderr as JSON on failure would otherwise get
    a parse error instead of the real one. Subcommands with no ``--json``
    flag (``deck seed``, ``success publish``, ``notice author``) never
    pass it, so their error rendering is unchanged."""
    try:
        operation()
    except errors.HeraldError as exc:
        flat = " ".join(str(exc).splitlines())
        message = "".join(ch if ch.isprintable() else " " for ch in flat)
        if json_output:
            print(
                json.dumps(
                    {"tool": TOOL_NAME, "error": type(exc).__name__, "message": message}
                ),
                file=sys.stderr,
            )
        else:
            print(f"{TOOL_NAME}: {type(exc).__name__}: {message}", file=sys.stderr)
        return errors.exit_code_for(exc)
    return 0
