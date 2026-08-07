"""The ``marshal`` console-script entry point (Story 1.1 scaffold; Story
1.3 converts the flat parser to a subparser tree).

``--version``/``--help`` keep working with no subcommand given -- a bare
``marshal`` invocation still returns ``EXIT_OK`` (Story 1.1's exit-code
behavior, preserved) but prints the usage line rather than silence, so a
caller that lost its arguments cannot read as success. ``config`` (Story
1.3, FR-54) is the first real
subcommand, dispatched to ``cli/config.py``. ``init`` (Story 1.4,
FR-1/FR-2) is the second, dispatched to ``cli/init.py``. ``homes`` (Story
1.6, FR-4/FR-8) is the third, ``preflight`` (Story 1.7, FR-7/FR-47/FR-52)
is the fourth, and ``teardown`` (Story 1.8, NFR-6/AD-29) is the fifth, all
three dispatched to the SAME ``cli/init.py`` module (see that
module's own docstring for why). ``gate`` (Story 2.1, FR-20) dispatches to
``cli/gate.py``, and ``factory`` (Story 3.3, FR-9/FR-17, AD-3/AD-22/AD-25)
-- Marshal's first launch verb, with nested ``spin``/``attach`` actions --
dispatches to ``cli/spin.py``. ``deploy`` (Story 4.1, FR-30/FR-31,
AD-13/AD-29), with a nested ``promote`` action, dispatches to
``cli/deploy.py``. ``land`` (Story 4.8, FR-60/AD-40) is a NEW top-level
sibling -- not nested under ``deploy`` -- that takes a wave from "gates
passed" to "merged, branch retired, feed resynced" in one command,
dispatching to ``cli/land.py``. ``retire`` (Story 4.10, FR-63/AD-47) is a
NEW top-level sibling too, dispatching to ``cli/retire.py``: a fleet-wide
sweep across every project's loop home for bmad-loop-minted, worktree-
isolated per-story branches provably safe to delete (dry-run by default,
``--execute`` to actually delete). ``status`` (Story 5.1, FR-36/AD-5) is
another NEW top-level sibling, dispatching to ``cli/status.py``: one row per
loop home across the whole fleet -- runtime state, current story, elapsed
time, budget consumed -- derived entirely from journals/run state, never a
hand-maintained file. ``check`` (Story 5.6, FR-65/AD-50) is the LAST Epic 5
top-level sibling, dispatching to ``cli/check.py``: routes to the repo's
existing detector registry (``scripts/detectors.py``, repo root) through
the front door, never a reimplementation. Not wired through the
envelope/finding machinery ITSELF: mirrors ``pyforge-doctor``'s
``__main__.py`` exit-relay pattern (structure: return an int, never raise,
relay argparse's own code, clamp anything foreign) -- individual
subcommand handlers (e.g. ``config.run_config``) are the ones that build
and print an envelope; this module only dispatches to them and relays
their returned int.

Story 5.6 also adds a context-resolution step ahead of dispatch:
``_resolve_context`` gathers a ``core.context.MarshalContext`` (project
slug, composed policy, conventional loop-home path, story key) whenever
``--project`` is present on the invocation, via the SAME
``policy.compose``/``cli/init.py::_home_path`` primitives every existing
command already calls individually -- never a second resolution
mechanism. The resolved context (``None`` when no ``--project`` is
present) is threaded to the dispatched handler via an additive
``context=`` keyword, but ONLY when that handler's own signature already
accepts one (``inspect.signature``-checked here, per-handler) -- of the
handlers wired below, only ``cli/check.py::run_check`` (this story's own
brand-new command) actually consumes it; ``cli/spin.py::run_spin``,
``cli/status.py::run_status``, and ``cli/land.py::run_land`` (the three
already-shipped commands this story's AC also names) accept it as an
additive, currently-UNUSED parameter, proving the "resolved once at the
front door" plumbing works end to end without retrofitting those three
large, already-hardened commands' own internal policy/home-path
re-derivation in this pass (see the spec's own Design Notes). Every other
handler's signature is untouched, so ``inspect.signature`` simply never
finds a ``context`` parameter to fill for them.

Story 1.9 (packaging, FR-52/FR-57) extends ``--version`` (still bypassing
the envelope, still exiting ``EXIT_OK`` unconditionally -- it is
informational, never a gate) to ALSO resolve and print the harness's
version via ``adapters.harness_bmadloop.BmadLoopHarness`` (a module-level
reference here, exactly like ``cli/init.py``'s own DI seam, so tests can
monkeypatch ``pyforge.marshal.cli.main.BmadLoopHarness``), plus a
prominent warning line when the harness is undeterminable or outside its
declared range (either tier -- see that adapter module's
``harness_version_in_range``). ``--version`` stays a CUSTOM ``argparse.Action``
(``_VersionAction``, ``nargs=0``) rather than becoming a plain
``store_true`` flag checked after parsing completes: an Action fires the
instant its option string is consumed, DURING ``parse_args``, before
argparse ever validates a subcommand's required arguments or rejects
unrecognized trailing tokens -- the same "always wins" property the
built-in ``action="version"`` this replaces had. (Scope, unchanged from
that built-in: the flag is registered on the ROOT parser only, so it wins
anywhere before a subcommand name hands parsing to a subparser --
``marshal init --version`` remains that subparser's usage error, unlike
``--help``, which argparse auto-registers per subparser.) A first-pass
``store_true`` version of
this change lost that property (``marshal --version init`` and
``marshal --version --bogus`` both started exiting ``2`` instead of
printing the version, review-caught and reverted) -- ``_VersionAction``
restores it while still computing its text dynamically, which the built-in
action's static ``%(prog)s`` template cannot do. ``__version__`` itself
(the hand-synced literal below) and its own safety-net test are untouched.

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
import inspect
import sys

from ..adapters.harness_bmadloop import (
    HARNESS_VERSION_RANGE_TEXT,
    BmadLoopHarness,
    harness_version_in_range,
    harness_version_tuple,
)
from ..core import policy as policy_core
from ..core.context import MarshalContext
from ..core.verdict import EXIT_OK, EXIT_SIGINT, EXIT_USAGE, GUARDED_EXIT_CODES
from . import check as check_cli
from . import config as config_cli
from . import deploy as deploy_cli
from . import gate as gate_cli
from . import init as init_cli
from . import land as land_cli
from . import retire as retire_cli
from . import spin as spin_cli
from . import status as status_cli

# Scaffold stage (Story 1.1): __init__.py stays empty (no __version__
# constant), so the version string duplicates pyproject.toml's version
# literal here instead. Acceptable at scaffold stage; keep the two in sync
# by hand.
__version__ = "0.1.0"


def _drain_stdout() -> None:
    """Flush stdout inside a guard before returning an exit code. With
    stdout piped or redirected it is block-buffered: the usage line and
    argparse's ``--help``/``--version`` output never touch the fd during
    ``main()``, and a broken destination (closed pipe, full disk) surfaces
    only at the interpreter's shutdown flush -- which CPython converts to
    exit status 120, outside the frozen domain, after ``main()`` has
    already returned its careful in-domain code. Flushing HERE surfaces the
    ``OSError`` while it can still be suppressed (``config``'s devnull
    redirect neutralizes the dirty buffer so the shutdown re-flush cannot
    raise) and the in-domain return value survives."""
    try:
        sys.stdout.flush()
    except OSError:
        config_cli._suppress_downstream_pipe_close()


def _version_text() -> str:
    """Story 1.9 (FR-52/FR-57): the text ``--version`` prints -- Marshal's
    own hand-synced ``__version__`` plus the resolved harness version (or a
    "not determined" line), plus a prominent warning line whenever the
    harness is undeterminable, unparseable, or numerically outside its
    declared range -- each names the specific problem rather than
    collapsing all three into one "outside the supported range" wording.
    ``BmadLoopHarness()`` is instantiated via the module-level name so tests
    can monkeypatch ``pyforge.marshal.cli.main.BmadLoopHarness`` -- the same
    DI idiom ``cli/init.py``'s ``run_init``/``run_preflight`` use for their
    own default-port construction, just with no subcommand-handler frame to
    thread an explicit parameter through here."""
    lines = [f"marshal {__version__}"]
    harness_version = BmadLoopHarness().harness_version()
    if harness_version is None:
        lines.append("bmad-loop: not determined")
        lines.append(
            "WARNING: harness version could not be determined -- expected "
            f"a bmad-loop version in {HARNESS_VERSION_RANGE_TEXT}"
        )
    else:
        lines.append(f"bmad-loop {harness_version}")
        if harness_version_tuple(harness_version) is None:
            # Distinct from the numerically-out-of-range case below: this
            # string isn't a version at all (review finding: the original
            # wording said "is outside the supported range" even for an
            # unparseable string like "dev", conflating the two).
            lines.append(
                f"WARNING: bmad-loop version {harness_version!r} could not "
                f"be parsed -- expected a version in {HARNESS_VERSION_RANGE_TEXT}"
            )
        elif not harness_version_in_range(harness_version):
            lines.append(
                f"WARNING: bmad-loop {harness_version} is outside the "
                f"supported range {HARNESS_VERSION_RANGE_TEXT}"
            )
    return "\n".join(lines)


class _VersionAction(argparse.Action):
    """Story 1.9: a custom, zero-argument ``Action`` (mirrors argparse's own
    built-in ``_VersionAction``) so ``--version`` fires THE INSTANT its
    option string is consumed during ``parse_args`` -- before argparse
    checks a subcommand's required arguments or rejects unrecognized
    trailing tokens -- rather than only after a full, successful parse. This
    is what gives ``--version`` its "always wins" property for any tokens
    AFTER it on the root-parser line; once a subcommand name is consumed,
    the subparser owns the rest and no per-subcommand ``--version`` is
    registered (same as the built-in action this mirrors -- ``--help``
    differs only because argparse auto-registers it per subparser). A plain
    ``store_true`` flag checked inside ``main()`` after ``parse_args``
    returns does NOT have this property (review-caught: ``marshal --version
    init`` and ``marshal --version --bogus`` exited ``2`` instead of
    printing the version under that approach)."""

    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
        super().__init__(
            option_strings=option_strings, dest=dest, default=default, nargs=0, help=help
        )

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            print(_version_text())
        except OSError:
            # With WRITE-THROUGH stdout (a tty, `python -u`) a broken
            # destination surfaces at this print itself, before
            # ``parser.exit()`` ever runs -- and an OSError raised here
            # would escape ``main()``'s SystemExit/KeyboardInterrupt-only
            # catch, violating its never-raises contract. The
            # block-buffered case is already covered by ``_drain_stdout()``
            # at the SystemExit catch; this guard covers the unbuffered
            # path the same way, with the same suppression.
            config_cli._suppress_downstream_pipe_close()
        parser.exit()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="marshal",
        description="Deterministic BMAD-loop supervisor.",
    )
    parser.add_argument(
        "--version",
        action=_VersionAction,
        help="Show marshal's version and the resolved harness version, then exit.",
    )
    subparsers = parser.add_subparsers(dest="command")
    config_cli.add_config_subparser(subparsers)
    init_cli.add_init_subparser(subparsers)
    init_cli.add_homes_subparser(subparsers)
    init_cli.add_preflight_subparser(subparsers)
    init_cli.add_teardown_subparser(subparsers)
    gate_cli.add_gate_subparser(subparsers)
    spin_cli.add_factory_subparser(subparsers)
    deploy_cli.add_deploy_subparser(subparsers)
    land_cli.add_land_subparser(subparsers)
    retire_cli.add_retire_subparser(subparsers)
    status_cli.add_status_subparser(subparsers)
    check_cli.add_check_subparser(subparsers)
    return parser


def _resolve_context(args: argparse.Namespace) -> MarshalContext | None:
    """Story 5.6 (FR-65/AD-50): resolves a ``MarshalContext`` once, before
    dispatch, whenever ``--project`` is present on the invocation --
    gathered via the SAME primitives every existing command already calls
    individually (``cli/config.py``'s conventional project-policy lookup +
    ``core.policy.compose``, ``cli/init.py::_home_path``), never a second
    resolution mechanism. Returns ``None`` when the invocation carries no
    ``--project`` value at all -- several subcommands (``factory spin``,
    ``land``) identify their project via a positional ``slug`` instead;
    resolving THAT is a future story's own scope, not this one's (see the
    module docstring and the spec's own Design Notes)."""
    slug = getattr(args, "project", None)
    if slug is None:
        return None

    # Code review (2026-08-07, Edge Case Hunter, the single most severe
    # finding against this story): the policy-file lookup is now gated on
    # `_is_valid_project_slug` BEFORE any filesystem touch, and the
    # presence probe is wrapped in `try/except OSError` -- the SAME
    # established pattern `cli/status.py`/`cli/land.py`/`cli/retire.py`
    # already use for this exact operation. The original version had
    # neither guard: an unvalidated slug let `conventional_project_policy_
    # path` build a path via naive string interpolation (a real, previously
    # documented path-traversal risk `cli/gate.py`'s own comments name for
    # the identical lookup), and a bare `candidate.is_file()` propagates
    # `PermissionError` on Python 3.12 for an unsearchable ancestor
    # directory -- uncaught here, that would have crashed `main()`'s own
    # "never raises" contract for any `marshal check --project ...`/
    # `marshal status --project ...` invocation hitting either condition.
    project_data: dict[str, object] = {}
    if policy_core._is_valid_project_slug(slug):
        candidate = config_cli.conventional_project_policy_path(slug)
        try:
            present = candidate.is_file()
        except OSError:
            present = True
        if present:
            try:
                project_data = dict(config_cli._read_project_policy(candidate))
            except config_cli.PolicyIOError:
                project_data = {}

    effective, _findings = policy_core.compose(
        project_slug=slug, project=project_data, flags={}
    )
    loop_home = init_cli._home_path(slug) if policy_core._is_valid_project_slug(slug) else None
    story = getattr(args, "story", None)
    return MarshalContext(slug=slug, loop_home=loop_home, policy=effective, story=story)


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and return an exit code -- never raises ``SystemExit``
    itself. Exit codes stay inside Marshal's frozen ``{0, 1, 2, 3, 4, 130}``
    domain (AD-7): argparse's own ``--help``/``--version`` exits (``0``) and
    usage errors (``2``) are relayed as plain ints via the ``SystemExit``
    catch below -- ``--version`` (Story 1.9) is ``_VersionAction``, a custom
    Action that calls ``parser.exit()`` itself, so it raises ``SystemExit``
    exactly like the built-in version/help actions it mirrors and is
    relayed through the SAME path, never a separate branch. A subcommand
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
            _drain_stdout()
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
        # Story 5.6 (FR-65/AD-50): resolve MarshalContext once, ahead of
        # dispatch, and thread it through ONLY when the handler's own
        # signature already accepts one -- inspect.signature-checked here
        # so every handler that hasn't been extended with a `context=`
        # parameter yet keeps working completely unchanged (see the module
        # docstring for exactly which ones have been, this pass).
        if "context" in inspect.signature(handler).parameters:
            result = handler(args, context=_resolve_context(args))
        else:
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
        # argparse printed help/version to stdout before exiting (its own
        # write is even swallowed on error since 3.12) -- drain the buffer
        # NOW or a piped `marshal --help` exits 120 at shutdown flush.
        _drain_stdout()
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
