"""The ``doctor`` console-script entry point.

Story 1.5 wires the ``check`` subcommand (FR-9/NFR-4): ``--engines``/
``--env`` compose Story 1.2/1.4's gather functions (``sources.warden.gather``,
``checks.env_hygiene.gather``) and Story 1.3's ``checks.registry``
(catalog + single-check filter) into one human-readable-or-``--json``
``DoctorReport``, exiting via ``verdict.exit_code_for``. Story 2.3 wires
``monitor --fleet`` the same way, composing Story 2.1/2.2's
``sources.atlas.gather`` per requested ``--watch`` axis. Story 3.4 wires
``diagnose --target ... [--prescribe]``, composing the same two gather
filters for one target and, with ``--prescribe``, Epic 3's
``prescribe.partition``/``prescribe.rank``/``prescribe.name_root_cause``
pipeline into ``Prescription``\\ s. Epic 4 extends this wiring three ways:
Story 4.1's ``score.grade`` runs alongside ``diagnose``'s own gather,
adding ``grade``/``axis_scores`` to the report; Story 4.2's
``monitor --surface PATH`` (opt-in) writes a persistent fleet-health
surface from the SAME already-gathered findings via ``fleet_surface``;
Story 4.3 adds ``adoption`` as a fourth, opt-in-only ``--watch`` axis
(``sources.atlas`` itself, not this module, does the real work); Story
4.4's ``prescribe.recommend_safe_upgrade`` populates each Prescription's
``safe_upgrade_target``/``safe_upgrade_reason``. Story 13.1 wires a fifth
subcommand, ``backlog-intake <identifier> [path]``, composing
``sources.backlog_intake.gather`` the same gather-then-emit way -- the
``identifier`` is pre-validated via ``backlog_intake.parse_identifier`` at
the argparse boundary before ``gather`` ever runs (mirrors
``_validate_check_names``'s own "validate at the call boundary" discipline).

``main`` always RETURNS an int; it never calls an exit primitive itself
(``verdict.py`` is the sole module permitted to do that -- the
sole-ownership meta-test enforces it), so any ``if __name__ == "__main__":``
guard must wrap the call in ``raise SystemExit(main())`` rather than embed a
literal exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import traceback
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import jsonschema
from pyforge.core.report import BASE_ENVELOPE_SCHEMA, compose

from . import fleet_surface, score, sources
from .checks import env_hygiene, registry
from .hooks import build_prescriptions, gather_for_diagnose
from .models import DoctorReport, DoctorStatus, Finding, Prescription, Source
from .sources import atlas, backlog_intake, bmad_method, sibling_dreams
from .sources import marshal as marshal_source
from .sources import warden as warden_source
from .verdict import EXIT_SIGINT, exit_code_for

# Story 2.3 AC1: omitting `--watch` runs this documented default axis set
# (the two highest-signal defaults per Story 2.1/2.2's own Sources), not
# every axis unconditionally.
_DEFAULT_MONITOR_AXES: tuple[str, ...] = ("staleness", "cve")

# Story 3.4: `diagnose --target` reuses the SAME default axis set for its
# own fleet-signal gather -- no AC asks for a different default, and
# introducing one would be an unjustified divergence from `monitor`'s own
# documented default (Simplicity First).
_DEFAULT_DIAGNOSE_AXES: tuple[str, ...] = _DEFAULT_MONITOR_AXES

# Scaffold stage (Story 1.1): __init__.py stays empty (no __version__
# constant -- see models.py's module docstring for the taxonomy rationale),
# so the version string duplicates pyproject.toml's version literal here
# instead. Acceptable at scaffold stage; keep the two in sync by hand.
__version__ = "0.1.0"

# --engines/--env's nargs="?" sentinel: present with NO value ("--engines"
# alone) means "run the whole category"; present WITH a value means "run
# just that named check". Distinct object identity -- never confusable with
# a real check name (a plain string) or with the flag's absent-default
# (None).
_WHOLE_CATEGORY = object()

# Story 6.3: `check`'s three categories, mapped to the `Source` each one's
# whole-category gather reports under -- `_category_in_scope`'s only way to
# ask `sources.scope_for` "is this category in scope?" without a second,
# hand-rolled category->scope table living beside `sources.REGISTRY`.
_CATEGORY_SOURCE: dict[str, Source] = {
    "engines": Source.WARDEN_DOCTOR,
    "env": Source.ENV_HYGIENE,
    "durability": Source.MARSHAL_DURABILITY,
    "bmad-core": Source.BMAD_METHOD_VERSION_DRIFT,
    "sibling-dreams": Source.SIBLING_DREAMS_DRIFT,
}


def _build_parser() -> tuple[
    argparse.ArgumentParser,
    argparse.ArgumentParser,
    argparse.ArgumentParser,
    argparse.ArgumentParser,
    argparse.ArgumentParser,
    argparse.ArgumentParser,
]:
    parser = argparse.ArgumentParser(
        prog="doctor",
        description=("Pre-flight + fleet-watch diagnostics for the pyforge factory."),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser(
        "check",
        help="run pre-flight diagnostics (engine availability + env hygiene)",
    )
    check.add_argument(
        "path",
        nargs="?",
        default=".",
        help="target directory to check (default: current directory)",
    )
    check.add_argument(
        "--engines",
        nargs="?",
        const=_WHOLE_CATEGORY,
        default=None,
        metavar="NAME",
        help=(
            "run the 'engines' category (pyforge-warden's self-check); an "
            "optional NAME runs just that named check (see --list)"
        ),
    )
    check.add_argument(
        "--env",
        nargs="?",
        const=_WHOLE_CATEGORY,
        default=None,
        metavar="NAME",
        help=(
            "run the 'env' category (credential-hygiene scan); an optional NAME runs just that named check (see --list)"
        ),
    )
    check.add_argument(
        "--durability",
        action="store_true",
        help=(
            "run the 'durability' category (Marshal's tracked sprint ledgers "
            "still hold every completion they once held) -- whole category "
            "only, no NAME (see _gather_durability)"
        ),
    )
    check.add_argument(
        "--bmad-core",
        action="store_true",
        help=(
            "run the 'bmad-core' category (installed bmad-method framework "
            "version vs. pixi.toml's declared floor, and vs. the latest "
            "release actually published upstream) -- whole category only, "
            "no NAME (see _gather_bmad_core); OPT-IN ONLY, NEVER part of "
            "the zero-flag default run -- this source's upstream half makes "
            "a real, un-mockable npm-registry HTTP call (up to 5.0s), which "
            "would risk the default run's speed budget; registered "
            "scope='repo' despite that live call -- unlike every other "
            "'repo'-scoped category, --scope repo does not guarantee no "
            "network I/O for this one"
        ),
    )
    check.add_argument(
        "--sibling-dreams",
        action="store_true",
        help=(
            "run the 'sibling-dreams' category (shared Dream titles vs the "
            "named sibling PyForge tree on status/owner/content-hash) -- "
            "whole category only; OPT-IN ONLY, NEVER part of the zero-flag "
            "default run (live GitHub Contents API call when a token is "
            "present); fail-open without GH_TOKEN/GITHUB_TOKEN"
        ),
    )
    check.add_argument(
        "--scope",
        choices=("repo", "runtime", "all"),
        default="all",
        help=(
            "restrict which categories run to those whose "
            "sources.REGISTRY-declared scope matches ('repo': reads only "
            "tracked files/git history, runs anywhere; 'runtime': reads "
            "host state, cannot run in CI -- no check is registered "
            "runtime-scope yet, so this always yields zero findings today); "
            "default 'all' matches every category (today's behavior, "
            "unchanged); combining with an explicit --engines/--env/"
            "--durability/--bmad-core/--sibling-dreams whose own scope "
            "doesn't match is a usage error, not a silent empty result -- "
            "ignored by --list"
        ),
    )
    check.add_argument(
        "--list",
        action="store_true",
        help=(
            "list the full check catalog as text and exit -- never "
            "gathers/runs anything (ignores "
            "--engines/--env/--durability/--bmad-core/--json/path/--scope)"
        ),
    )
    check.add_argument(
        "--json",
        action="store_true",
        help="emit one schema-valid DoctorReport document on stdout",
    )
    # Deliberately NO --version on this subparser: verified live against
    # `pyforge.warden.cli.main(["scan", "--version"])` (an argparse usage
    # error, exit 2) -- --version stays top-level only, mirroring warden's
    # own convention exactly (see the story spec's Design Notes).

    monitor = subparsers.add_parser(
        "monitor",
        help="fleet-pulse watch over cf_atlas's staleness/cve/abandonment signals",
    )
    monitor.add_argument(
        "--fleet",
        action="store_true",
        required=True,
        help=(
            "required -- names the scope this verb watches (the whole "
            "fleet); mirrors the Dream's own `doctor monitor --fleet` "
            "surface literally"
        ),
    )
    monitor.add_argument(
        "--watch",
        default=None,
        metavar="AXIS[,AXIS...]",
        help=(
            "comma-separated Watch axes to run (staleness, cve, "
            "abandonment, adoption); default when omitted: staleness,cve"
        ),
    )
    monitor.add_argument(
        "--target",
        default=None,
        metavar="MAINTAINER",
        help="scope every requested axis to one maintainer/feedstock",
    )
    monitor.add_argument(
        "--source",
        default=None,
        metavar="SOURCE",
        help="filter the rendered output to one Finding.source tag",
    )
    monitor.add_argument(
        "--json",
        action="store_true",
        help="emit one schema-valid DoctorReport document on stdout",
    )
    monitor.add_argument(
        "--surface",
        default=None,
        metavar="PATH",
        help=(
            "also write a persistent, schema-versioned fleet-health surface "
            "to PATH, derived strictly from this run's own findings "
            "(idempotent regeneration; no independent second gather)"
        ),
    )

    diagnose = subparsers.add_parser(
        "diagnose",
        help="gather + (optionally) partition/rank/root-cause one target",
    )
    diagnose.add_argument(
        "--target",
        required=True,
        metavar="TARGET",
        help=(
            "the feedstock/maintainer to scope the fleet-signal gather to; "
            "when TARGET is also an existing local directory, the "
            "engines+env checks (Story 1.5's own default combined run) are "
            "gathered against it too"
        ),
    )
    diagnose.add_argument(
        "--prescribe",
        action="store_true",
        help=(
            "run the partition/rank/root-cause pipeline and populate "
            "prescriptions; without this flag, findings are gathered and "
            "reported but never partitioned/ranked"
        ),
    )
    diagnose.add_argument(
        "--json",
        action="store_true",
        help="emit one schema-valid DoctorReport document on stdout",
    )

    backlog_intake_parser = subparsers.add_parser(
        "backlog-intake",
        help=("scan every station's tracked deferred-work-ledger.md for entries naming an epic/story, fleet wide"),
    )
    backlog_intake_parser.add_argument(
        "identifier",
        help=("an epic ('13') or story ('13.1'/'13-1') id, optionally prefixed 'Epic '/'Story ' (case-insensitive)"),
    )
    backlog_intake_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="target directory to scan (default: current directory)",
    )
    backlog_intake_parser.add_argument(
        "--json",
        action="store_true",
        help="emit one schema-valid DoctorReport document on stdout",
    )

    flags_parser = subparsers.add_parser(
        "flags",
        help="feature-flag actuators (Story 48.5 / R-21)",
    )
    flags_sub = flags_parser.add_subparsers(dest="flags_command", required=True)
    kill_switch_parser = flags_sub.add_parser(
        "kill-switch",
        help="disable one FILE-resolver flag and record the kill-switch metric",
    )
    kill_switch_parser.add_argument(
        "--flag",
        required=True,
        help="OpenFeature flag key to disable (e.g. pyforge.three_surfaces)",
    )
    kill_switch_parser.add_argument(
        "--reason",
        required=True,
        help="short operator reason recorded on the kill-switch metric label",
    )
    kill_switch_parser.add_argument(
        "--flags-path",
        default=None,
        help="path to flags.json (default: resolve via django_pyforge.flags)",
    )

    return parser, check, monitor, diagnose, backlog_intake_parser, flags_parser


def _validate_check_names(args: argparse.Namespace, check_parser: argparse.ArgumentParser) -> None:
    """A NAME given to ``--engines``/``--env`` must be a cataloged check for
    that category -- an unknown name is an argparse usage error (``.error()``,
    exit 2) raised HERE, before ``gather_one`` is ever called (resolves both
    prior stories' "validate vs pass through" deferral).

    Skipped entirely when ``--list`` is given: ``--list``'s own contract is
    to ignore ``--engines``/``--env``/``--durability``/``--scope``/``--json``/
    ``path`` and never gather anything (review finding) -- validating a name
    it will never act on would make ``doctor check --list --engines
    <bad-name>`` a usage error instead of the promised catalog listing.

    A NAME rejected here that also happens to be an existing path is very
    likely a path-argument-ordering mistake, not a typo'd check name: the
    ``--engines``/``--env`` flags use ``nargs="?"`` so they can optionally
    take a value, which makes them structurally ambiguous with an adjacent
    bare positional ``path`` in argparse's own token matching (confirmed
    empirically during review -- e.g. ``doctor check --engines /some/dir``
    parses ``/some/dir`` as the check NAME, not the scan target). The error
    message names this specific, discoverable cause rather than leaving an
    operator to guess why a real path was rejected as an "unknown check
    name" (review finding)."""
    if args.list:
        return
    for category, value in (("engines", args.engines), ("env", args.env)):
        if value is None or value is _WHOLE_CATEGORY:
            continue
        known_names = sorted(spec.name for spec in registry.list_checks(category=category))
        if value not in known_names:
            hint = ""
            # `value and`: an empty NAME (`--engines=`) must not hint --
            # Path("") normalizes to Path(".") which exists, so the bare
            # truthiness guard is load-bearing, not cosmetic (review
            # finding). shlex.quote: the suggested command must survive a
            # copy-paste even when the path embeds whitespace/newlines
            # (review finding).
            if value and Path(value).exists():
                hint = (
                    f" -- {value!r} looks like a path: if you meant to set "
                    "the scan target, place it BEFORE --engines/--env, e.g. "
                    f"`doctor check {shlex.quote(value)} --{category}`"
                )
            check_parser.error(
                f"argument --{category}: unknown check name {value!r} (known: {', '.join(known_names)}){hint}"
            )


def _category_in_scope(category: str, requested_scope: str) -> bool:
    """Whether ``category`` (one of ``_CATEGORY_SOURCE``'s keys) should run
    under ``--scope``'s already-validated ``requested_scope`` value ("repo",
    "runtime", or "all").

    ``"all"`` (the default) matches every category unconditionally --
    preserving today's behavior exactly, per the story's own "omitting
    --scope behaves exactly as today" constraint. ``"repo"``/``"runtime"``
    match only a category whose OWN registered scope (read live from
    ``sources.scope_for``, never a second hardcoded scope list -- the
    story's own Always constraint) equals the request.
    """
    if requested_scope == "all":
        return True
    return sources.scope_for(_CATEGORY_SOURCE[category]) == requested_scope


def _validate_scope_against_explicit_categories(
    args: argparse.Namespace, check_parser: argparse.ArgumentParser
) -> None:
    """An EXPLICITLY-requested category (``--engines``/``--env`` given, or
    ``--durability``/``--bmad-core``) whose registered scope doesn't match a
    non-``"all"`` ``--scope`` is a usage error (``.error()``, exit 2) raised
    HERE, before dispatch -- mirrors ``_validate_check_names``'s own
    "validate at the call boundary, not inside gather" discipline.

    Review finding: without this check, ``doctor check --engines --scope
    runtime`` silently narrowed ``run_engines`` to ``False`` in
    ``_run_check`` and reported ``0 finding(s)``, exit ``0`` -- byte-for-byte
    indistinguishable from "ran the requested check and it passed clean" for
    an automated ``--json`` consumer. An operator who names a category
    explicitly is asking for its result, not silence; the contradiction is
    surfaced loudly instead.

    Skipped when ``--list`` is given (mirrors ``_validate_check_names``'s own
    ``--list`` bypass) or when ``--scope`` is ``"all"`` (nothing to
    contradict). The DEFAULT run (no category flag given at all) is
    untouched -- ``--scope runtime`` narrowing an implicit "run everything"
    down to zero categories is the documented, intentional CI-selection
    behavior (story spec's I/O matrix), not a contradiction to flag.
    """
    if args.list or args.scope == "all":
        return
    explicit = [
        (flag, category)
        for flag, category, given in (
            ("--engines", "engines", args.engines is not None),
            ("--env", "env", args.env is not None),
            ("--durability", "durability", args.durability),
            ("--bmad-core", "bmad-core", args.bmad_core),
            ("--sibling-dreams", "sibling-dreams", args.sibling_dreams),
        )
        if given
    ]
    for flag, category in explicit:
        category_scope = sources.scope_for(_CATEGORY_SOURCE[category])
        if category_scope != args.scope:
            check_parser.error(
                f"argument {flag}: {category!r} is scope={category_scope!r}, "
                f"excluded by --scope {args.scope!r} -- remove --scope or "
                f"drop {flag}"
            )


def _split_watch_axes(raw: str | None) -> tuple[str, ...]:
    """Pure parse of ``--watch``'s comma-separated axis list -- no
    validation, no side effects. ``raw is None`` (the flag omitted
    entirely) returns Story 2.3's documented default axis set.
    De-duplication preserves first-occurrence order (``dict.fromkeys``) so
    a redundant ``--watch staleness,staleness`` doesn't double-gather;
    empty tokens (``",,"``, a leading/trailing comma) are dropped."""
    if raw is None:
        return _DEFAULT_MONITOR_AXES
    tokens = (token.strip() for token in raw.split(","))
    return tuple(dict.fromkeys(token for token in tokens if token))


def _validate_monitor_args(args: argparse.Namespace, monitor_parser: argparse.ArgumentParser) -> None:
    """An unknown axis or an unrecognized ``--source`` is a usage error
    (``.error()``, exit 2) raised HERE, before any ``atlas.gather`` call --
    mirrors ``_validate_check_names``'s own "validate at the call boundary,
    not inside the gather" discipline."""
    axes = _split_watch_axes(args.watch)
    if not axes:
        monitor_parser.error(f"argument --watch: expected at least one axis, got an empty value ({args.watch!r})")
    unknown_axes = [axis for axis in axes if axis not in atlas.VALID_WATCH_AXES]
    if unknown_axes:
        monitor_parser.error(
            f"argument --watch: unknown axis(es) {unknown_axes!r} (known: {', '.join(sorted(atlas.VALID_WATCH_AXES))})"
        )
    if args.source is not None:
        known_sources = sorted(source.value for source in Source)
        if args.source not in known_sources:
            monitor_parser.error(
                f"argument --source: unknown source {args.source!r} (known: {', '.join(known_sources)})"
            )


def _validate_backlog_intake_args(args: argparse.Namespace, backlog_intake_parser: argparse.ArgumentParser) -> None:
    """An ``identifier`` that ``backlog_intake.parse_identifier`` cannot
    parse is a usage error (``.error()``, exit 2) raised HERE, before
    ``backlog_intake.gather`` is ever called -- mirrors
    ``_validate_check_names``'s own "validate at the call boundary, not
    inside gather" discipline."""
    if backlog_intake.parse_identifier(args.identifier) is None:
        backlog_intake_parser.error(
            f"argument identifier: {args.identifier!r} is not a parseable "
            "epic/story id (expected e.g. '13', '13.1', '13-1', 'Epic 13', "
            "'Story 13.1')"
        )


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and return an exit code -- never raises ``SystemExit``
    itself. Exit codes stay inside Doctor's frozen ``{0, 2, 130}`` domain
    (AD-2): argparse's own ``--version``/``--help`` exits (``0``) and usage
    errors (``2``) are caught and returned as plain ints, and a
    ``KeyboardInterrupt`` during parsing returns the SIGINT constant.
    """
    if argv is None:
        argv = sys.argv[1:]
    (
        parser,
        check_parser,
        monitor_parser,
        _diagnose_parser,
        backlog_intake_parser,
        _flags_parser,
    ) = _build_parser()
    try:
        try:
            args = parser.parse_args(argv)
            if args.command == "check":
                _validate_check_names(args, check_parser)
                _validate_scope_against_explicit_categories(args, check_parser)
            elif args.command == "monitor":
                _validate_monitor_args(args, monitor_parser)
            elif args.command == "backlog-intake":
                _validate_backlog_intake_args(args, backlog_intake_parser)
            # "diagnose" has no name/axis catalog to validate against --
            # --target is a free-form string and argparse's own
            # required=True already enforces its presence.
        except SystemExit as exc:
            # argparse exits itself: --version/--help -> 0, a usage error
            # -> 2 (never 0). Surface its code as a return value, never
            # re-raised -- a non-int code (argparse never produces one
            # under this parser config) falls back to 2, still inside the
            # guarded domain. This mapping is ONLY for the parse/validate
            # phase: a SystemExit raised during dispatch is NOT argparse's
            # and lands in the outer handler below instead (review
            # finding: `SystemExit(None)` from a component calling bare
            # `sys.exit()` inside a gather would otherwise map to 0 here
            # -- a crashed run reporting success).
            if exc.code is None:
                return 0
            if isinstance(exc.code, int) and exc.code in {0, 2, 130}:
                return exc.code
            # Any other int (or non-int, e.g. a message string) is clamped
            # to 2 -- defense in depth for a future argparse action that
            # might exit with something outside Doctor's frozen {0, 2, 130}
            # domain (AD-2).
            return 2
        # Dispatch stays INSIDE the outer try: a gather call is real
        # multi-second work (the whole point of this story), so a Ctrl-C
        # during dispatch -- not just during parsing -- must also return
        # EXIT_SIGINT rather than escape as a raw KeyboardInterrupt (main()
        # never raises -- see its own docstring). `args.command` is one of
        # `{"check", "monitor", "diagnose", "backlog-intake"}` past this
        # point (subparsers is required=True).
        if args.command == "monitor":
            return _run_monitor(args)
        if args.command == "diagnose":
            return _run_diagnose(args)
        if args.command == "backlog-intake":
            return _run_backlog_intake(args)
        if args.command == "flags":
            return _run_flags(args)
        return _run_check(args)
    except KeyboardInterrupt:
        return EXIT_SIGINT
    except SystemExit:
        # Exit-code sole ownership (mirrors warden's cli.py): argparse's
        # own exits were already handled at the parse phase above, so a
        # SystemExit reaching here was raised INSIDE dispatch -- a
        # component calling sys.exit (even sys.exit(0)) must never dictate
        # the verb's verdict. Its carried code is not trusted; projected as
        # an internal error (review finding).
        _stderr(
            "doctor: internal error: SystemExit raised inside dispatch "
            "(exit-code sole-ownership violation); any partial stdout "
            "must not be consumed"
        )
        return 2
    except Exception as exc:  # noqa: BLE001 -- last-resort net, mirrors
        # pyforge-warden's cli.py: an internal defect (e.g. a future
        # schema/model drift tripping _emit_json's jsonschema.validate
        # self-check) must never surface as the interpreter's default exit
        # 1 or an UNCAUGHT traceback -- it would violate this module's own
        # documented {0, 2, 130} exit-code domain (AD-2) (review finding).
        # The formatted traceback IS deliberately emitted to stderr first,
        # exactly as warden's net does -- Doctor's consumers are unattended
        # loop agents whose only diagnostic surface is stderr, and a bare
        # one-line repr (e.g. `ValidationError(...)`) is undiagnosable
        # without the failing frame (review finding).
        _stderr("".join(traceback.format_exception(exc)).rstrip("\n"))
        _stderr(f"doctor: internal error: {exc!r}")
        return 2


def _gather_engines(name: object, target: Path) -> tuple[Finding, ...]:
    """Findings for the "engines" category: the whole suite, or one named
    check filtered from it. ``gather_one`` returning ``None`` for a
    (already-validated) name can ONLY mean the category degraded to
    warden's all-or-nothing sentinel -- ``sources.warden.gather`` never
    partially succeeds -- so render one synthetic FAIL ``Finding`` naming
    the degradation, never a bare "not found" (story spec Design Notes)."""
    if name is _WHOLE_CATEGORY:
        return warden_source.gather(target)
    finding = registry.gather_one("engines", name, target)
    if finding is not None:
        return (finding,)
    return (
        Finding(
            source=Source.WARDEN_DOCTOR,
            check=name,
            status=DoctorStatus.FAIL,
            message=(
                f"check {name!r} did not run -- the 'engines' category "
                "degraded (pyforge-warden absent, unimportable, or its "
                "self-check crashed); re-run `doctor check --engines` "
                "(no name) to see the full degradation reason"
            ),
            evidence={},
        ),
    )


def _gather_env(name: object, target: Path) -> tuple[Finding, ...]:
    """Findings for the "env" category: the whole suite, or one named check
    filtered from it. ``env_hygiene.gather`` is ADDITIVE, never
    sentinel-replacing -- ``gather_one`` returning ``None`` here is the
    ordinary "clean, no match" outcome, not a degradation, so it yields zero
    Findings, never a synthetic one (the asymmetric complement of
    ``_gather_engines`` above; see the story spec's Design Notes for why the
    two categories are NOT handled uniformly)."""
    if name is _WHOLE_CATEGORY:
        return env_hygiene.gather(target)
    finding = registry.gather_one("env", name, target)
    return (finding,) if finding is not None else ()


def _gather_durability(target: Path) -> tuple[Finding, ...]:
    """Findings for the "durability" category (Story 5.2, FR-14/AD-11).

    WHOLE-CATEGORY ONLY -- deliberately no per-check NAME, unlike
    ``--engines``/``--env``. Per-check addressability is a
    ``checks.registry`` concern (a ``_CATALOG`` entry plus a ``gather_one``
    dispatch branch), and this story's surface is ``__main__.py``; a NAME
    argument here would have to hand-roll a second filter path beside
    ``gather_one``, which is exactly the drift ``registry.gather_one``'s
    "filter, not a second code path" rule exists to prevent. So the flag is
    a plain switch, and ``--list`` does not advertise durability checks.

    ``sources.marshal.gather`` is all-or-nothing like warden's and never
    raises (its own contract: git missing, target not a repo, or no ledger
    all degrade to WARN), so there is no synthetic-degradation branch to
    mirror ``_gather_engines``'.
    """
    return marshal_source.gather(target)


def _gather_bmad_core(target: Path) -> tuple[Finding, ...]:
    """Findings for the "bmad-core" category (Story 10.3, Epic 10/CAP-3).

    WHOLE-CATEGORY ONLY -- mirrors ``_gather_durability``'s own shape and
    rationale exactly: no per-check NAME, since per-check addressability is
    a ``checks.registry`` concern this flag deliberately doesn't reach for.

    OPT-IN ONLY -- unlike ``--durability``, this category is deliberately
    NEVER part of ``_run_check``'s "no flags -> all on" default branch (see
    that function's own comment): ``bmad_method.gather``'s CAP-2 half makes
    a real, un-mockable live npm-registry HTTP call (up to 5.0s), which
    would put NFR-4's hard 5-second pre-flight budget at direct risk if run
    on every invocation.

    ``bmad_method.gather`` already degrades via its own
    ``sources.degrade_on_exception`` wrapper (never raises, never FAILs --
    see that module's own docstring), so there is no synthetic-degradation
    branch to mirror ``_gather_engines``' either.
    """
    return bmad_method.gather(target)


def _gather_sibling_dreams(target: Path) -> tuple[Finding, ...]:
    """Findings for the "sibling-dreams" category (Story 16.1 / CAP-1).

    OPT-IN ONLY -- live GitHub Contents API when a token is present; same
    NFR-4 rationale as ``--bmad-core``. Fail-open without a token.
    """
    return sibling_dreams.gather(target)


def _run_check(args: argparse.Namespace) -> int:
    if args.list:
        return _render_list()

    target = Path(args.path)
    run_engines = args.engines is not None
    run_env = args.env is not None
    run_durability = args.durability
    # Story 10.3: `--bmad-core` is opt-in ONLY and must never be auto-
    # enabled by the "no flags -> all on" branch below (see
    # `_gather_bmad_core`'s own docstring for the NFR-4 rationale), unlike
    # `--durability`, which is. It must ALSO count as an "explicit flag
    # given" for that branch's own trigger condition -- mirrors the
    # existing "explicit flags narrow" semantics `--engines`/`--env`/
    # `--durability` already have amongst each other (proven by
    # `test_default_run_includes_durability_but_a_narrowing_flag_excludes_it`):
    # `doctor check --bmad-core` alone must run ONLY bmad-core, not also
    # silently pull in engines+env+durability just because none of THOSE
    # three flags happened to be named.
    run_bmad_core = args.bmad_core
    # Story 16.1: same opt-in / narrowing discipline as `--bmad-core`.
    run_sibling_dreams = args.sibling_dreams
    if not run_engines and not run_env and not run_durability and not run_bmad_core and not run_sibling_dreams:
        # Neither flag given -> both categories run (FR-2), each as the
        # WHOLE category -- args.engines/args.env are still None here (the
        # "flag absent" default, distinct from _WHOLE_CATEGORY, the "flag
        # given with no value" const), so the sentinel must be substituted
        # explicitly rather than forwarded as-is. `run_bmad_core` /
        # `run_sibling_dreams` are deliberately NOT set True here.
        run_engines = run_env = run_durability = True
        engines_name: object = _WHOLE_CATEGORY
        env_name: object = _WHOLE_CATEGORY
    else:
        engines_name = args.engines
        env_name = args.env

    # Story 6.3: narrow the already-resolved run_* booleans by --scope
    # (default "all" leaves every category untouched, matching today's
    # behavior exactly). Applied AFTER the default/explicit-flag resolution
    # above -- --scope filters WHAT was already selected to run, it never
    # itself selects a category.
    run_engines = run_engines and _category_in_scope("engines", args.scope)
    run_env = run_env and _category_in_scope("env", args.scope)
    run_durability = run_durability and _category_in_scope("durability", args.scope)
    run_bmad_core = run_bmad_core and _category_in_scope("bmad-core", args.scope)
    run_sibling_dreams = run_sibling_dreams and _category_in_scope("sibling-dreams", args.scope)

    findings: tuple[Finding, ...] = ()
    if run_engines:
        findings += _gather_engines(engines_name, target)
    if run_env:
        findings += _gather_env(env_name, target)
    if run_durability:
        findings += _gather_durability(target)
    if run_bmad_core:
        findings += _gather_bmad_core(target)
    if run_sibling_dreams:
        findings += _gather_sibling_dreams(target)

    # Computed BEFORE emission: a stdout write failure must never replace
    # the already-computed exit code (mirrors warden's cli.py discipline).
    exit_code = exit_code_for(findings)
    if args.json:
        _emit_json(findings, verb="check")
    else:
        _emit_text(findings, verb="check")
    return exit_code


def _run_monitor(args: argparse.Namespace) -> int:
    """Story 2.3: compose Story 2.1/2.2's ``sources.atlas.gather`` per
    requested ``--watch`` axis (already validated by ``_validate_monitor_args``
    before this ever runs) into one ``DoctorReport``. Multi-axis composition
    (Story 2.2 AC3) is exactly this loop-and-concatenate -- see
    ``sources/atlas.py``'s own module docstring for why that composition
    deliberately lives here, not inside ``gather()`` itself.

    ``--source`` filters the ALREADY-GATHERED findings before either
    render (never a second, narrower gather) -- this keeps the FR-9 parity
    guarantee automatic: whatever the human-readable output shows is
    exactly what ``--json`` shows, because both render from the same
    filtered tuple.

    Story 4.2: ``--surface PATH`` (optional) writes a persistent
    fleet-health surface derived from this SAME (already ``--source``-
    filtered) findings tuple -- never a second, independent gather (AD-8).
    Omitting ``--surface`` changes nothing about ``monitor``'s existing
    behavior (backward compatible, mirrors Story 4.3's own "opt-in only"
    discipline for a new addition)."""
    axes = _split_watch_axes(args.watch)

    findings: tuple[Finding, ...] = ()
    for axis in axes:
        findings += atlas.gather(axis, target=args.target)

    if args.source is not None:
        findings = tuple(f for f in findings if f.source.value == args.source)
        # Review finding: `axes` was recorded verbatim from `--watch`,
        # requested BEFORE this filter -- narrowing to the axes still
        # actually represented in the filtered findings keeps the
        # surface's own "exactly which axes the triggering run covered"
        # claim honest even when `--source` drops an entire axis.
        remaining_sources = {f.source for f in findings}
        axes = tuple(axis for axis in axes if atlas.AXIS_SOURCES.get(axis, frozenset()) & remaining_sources)

    if args.surface:
        fleet_surface.write_surface(Path(args.surface), findings, axes=axes)

    exit_code = exit_code_for(findings)
    if args.json:
        _emit_json(findings, verb="monitor")
    else:
        _emit_text(findings, verb="monitor")
    return exit_code


def _run_diagnose(args: argparse.Namespace) -> int:
    """Story 3.4: gather Findings for ``--target``, composing Epic 1's
    `checks` gather (when ``--target`` is ALSO an existing local directory
    -- "when the target implies an environment check", the AC's own
    wording) with Epic 2's `sources.atlas` gather (always, scoped to
    ``--target`` as the maintainer/feedstock filter). Without
    ``--prescribe``, reports the gathered Findings with ``prescriptions``
    present but empty (Story 1.1's frozen envelope requires the KEY for
    ``verb == "diagnose"`` even when there's nothing to populate it with
    yet). With ``--prescribe``, runs Story 3.1/3.2/3.3's full pipeline --
    every gathered Finding becomes exactly one ``Prescription``, so a
    target with only ``blocked``/``accepted-risk`` Findings still reports
    them (Story 3.1's "never a silent drop" rule, extended here)."""
    # `Path("").is_dir()` resolves to the CWD and returns True (review
    # finding) -- `--target ""` would otherwise silently scope the local
    # engine/env checks to wherever `doctor` happens to be invoked from,
    # rather than the AC's own "when TARGET is ALSO an existing local
    # directory" intent for a genuinely-given target.
    target_path = Path(args.target) if args.target.strip() else None
    directory_checks = target_path is not None and target_path.is_dir()
    findings = gather_for_diagnose(
        args.target,
        directory_checks=directory_checks,
        axes=_DEFAULT_DIAGNOSE_AXES,
    )

    prescriptions: tuple[Prescription, ...] = ()
    if args.prescribe:
        prescriptions = build_prescriptions(findings)

    # Story 4.1: `diagnose` is the one verb that grades a single target's
    # OWN findings (the "composite health grade per dependency" framing) --
    # always computed (score.grade is pure/cheap, mirrors `--prescribe`'s
    # own AD-4 discipline of never gating a pure aggregation behind more
    # flags than necessary), never gated behind an extra flag.
    grade_result = score.grade(findings)

    exit_code = exit_code_for(findings)
    if args.json:
        # verb="diagnose" ALWAYS carries the `prescriptions` key in the
        # JSON envelope, empty or not (Story 1.1's frozen contract) --
        # unlike the text render below, this is never conditioned on
        # `--prescribe`.
        _emit_json(
            findings,
            verb="diagnose",
            prescriptions=prescriptions,
            grade_result=grade_result,
        )
    else:
        # The human-readable render only shows a "prescription(s)" section
        # when `--prescribe` was actually requested -- an UNREQUESTED empty
        # pipeline result would misleadingly read as "ran and found zero"
        # rather than "didn't run" (AC1's own "reports them without
        # partitioning/ranking" framing). The grade line, unlike
        # prescriptions, is unconditional -- it costs nothing to show.
        _emit_text(
            findings,
            verb="diagnose",
            prescriptions=prescriptions if args.prescribe else None,
            grade_result=grade_result,
        )
    return exit_code


def _run_flags(args: argparse.Namespace) -> int:
    """Story 48.5: opt-in flag actuators (never part of check/monitor)."""
    if args.flags_command != "kill-switch":
        return 2
    from pyforge.doctor.actuators.flag_kill_switch import kill_switch

    if args.flags_path:
        flags_path = Path(args.flags_path)
    else:
        try:
            from django_pyforge.flags import resolve_flags_path
        except ImportError:
            _stderr("doctor flags kill-switch: --flags-path is required when django_pyforge is not importable")
            return 2
        resolved = resolve_flags_path()
        if resolved is None:
            _stderr("doctor flags kill-switch: could not resolve flags.json")
            return 2
        flags_path = resolved
    if not flags_path.is_file():
        _stderr(f"doctor flags kill-switch: flags file not found: {flags_path}")
        return 2
    try:
        result = kill_switch(flags_path, args.flag, args.reason)
    except KeyError as exc:
        _stderr(f"doctor flags kill-switch: {exc}")
        return 2
    _write_stdout(f"disabled {result.flag} in {result.path} ({result.previous_state} -> {result.new_state})\n")
    return 0


def _run_backlog_intake(args: argparse.Namespace) -> int:
    """Story 13.1: composes ``backlog_intake.gather`` into one
    ``DoctorReport`` -- mirrors ``_run_check``'s own gather-then-emit shape.
    ``args.identifier`` was already validated by
    ``_validate_backlog_intake_args`` before this ever runs, so
    ``gather`` cannot hit its own unparseable-identifier WARN branch here.
    """
    findings = backlog_intake.gather(Path(args.path), identifier=args.identifier)

    exit_code = exit_code_for(findings)
    if args.json:
        _emit_json(findings, verb="backlog-intake")
    else:
        _emit_text(findings, verb="backlog-intake")
    return exit_code


def _render_list() -> int:
    lines = [f"{spec.category}\t{spec.name}" for spec in registry.list_checks()]
    _write_stdout("\n".join(lines) + "\n")
    return 0


def _report_schema() -> dict:
    schema_text = resources.files("pyforge.doctor").joinpath("data", "report-schema.json").read_text(encoding="utf-8")
    return json.loads(schema_text)


def _emit_json(
    findings: tuple[Finding, ...],
    *,
    verb: str,
    prescriptions: tuple[Prescription, ...] | None = None,
    grade_result: score.GradeResult | None = None,
) -> None:
    report = DoctorReport(
        schema_version=1,
        verb=verb,
        generated_at=datetime.now(UTC).isoformat(),
        findings=findings,
        prescriptions=prescriptions,
        grade=grade_result.grade.value if grade_result is not None else None,
        axis_scores=(
            tuple(axis.to_json_dict() for axis in grade_result.axis_scores) if grade_result is not None else None
        ),
    )
    document = report.to_json_dict()
    # Self-validated BEFORE it ever reaches stdout -- a schema-invalid
    # document must never be the one thing an automated caller (Marshal)
    # consumes as the contract. Story 14.3, SPEC-pyforge-core CAP-4:
    # validates against the packaged schema COMPOSED with the shared base
    # envelope schema (an `allOf` merge -- the packaged schema is embedded
    # verbatim, unmodified); every payload that validated before still
    # validates, since the base only adds already-satisfied presence checks.
    # Draft202012Validator is pinned explicitly (review-pass patch, matches
    # warden's identical call site) -- the composed dict's own top-level
    # has no `$schema` key (only the nested base branch does), so a bare
    # `jsonschema.validate` would rely on the library's default-draft
    # auto-detection instead of the pin every station's own schema declares.
    jsonschema.Draft202012Validator(compose(BASE_ENVELOPE_SCHEMA, _report_schema())).validate(document)
    _write_stdout(json.dumps(document, sort_keys=True, indent=2) + "\n")


def _single_line(text: str) -> str:
    """Neutralize embedded line breaks so one finding's ``message`` can
    never fabricate extra ``_emit_text`` lines (mirrors warden's
    ``report.py::_single_line`` -- its own Story 1.8 review finding, and a
    review finding here too). ``Finding.message`` is free text with no
    no-newline guarantee -- env-hygiene messages embed scanned file paths
    verbatim, and a path may legally contain ``\\n``, which would otherwise
    render as a second, indistinguishable-from-real finding line and desync
    the header's ``N finding(s)`` count."""
    return text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


def _emit_text(
    findings: tuple[Finding, ...],
    *,
    verb: str,
    prescriptions: tuple[Prescription, ...] | None = None,
    grade_result: score.GradeResult | None = None,
) -> None:
    ok = sum(1 for f in findings if f.status is DoctorStatus.OK)
    warn = sum(1 for f in findings if f.status is DoctorStatus.WARN)
    fail = sum(1 for f in findings if f.status is DoctorStatus.FAIL)
    lines = [f"doctor {verb}: {len(findings)} finding(s) -- {ok} ok, {warn} warn, {fail} fail"]
    if grade_result is not None:
        # Story 4.1 FR-9 parity: whatever --json's `grade`/`axis_scores`
        # show must also be visible in the human-readable render.
        lines.append(f"  grade: {grade_result.grade.value} -- {_single_line(grade_result.reason)}")
        for axis in grade_result.axis_scores:
            lines.append(f"    [{axis.axis}] {axis.grade.value} ({axis.ok} ok, {axis.warn} warn, {axis.fail} fail)")
    for finding in findings:
        lines.append(
            f"  [{finding.source.value}] {finding.check}: {finding.status.value} -- {_single_line(finding.message)}"
        )
    # Story 3.4 FR-9 parity: whatever --json shows under "prescriptions"
    # must also be visible in the human-readable render -- otherwise
    # `doctor diagnose --prescribe` (no --json) would silently omit the
    # entire point of --prescribe from its own default output.
    if prescriptions is not None:
        lines.append(f"  {len(prescriptions)} prescription(s):")
        for prescription in prescriptions:
            rank_text = f"rank {prescription.rank}" if prescription.rank is not None else "unranked"
            lines.append(
                f"    [{prescription.partition.value}, {rank_text}] "
                f"{prescription.finding_ref}: {_single_line(prescription.action)}"
            )
            lines.append(f"      root cause: {_single_line(prescription.root_cause)}")
            # Story 4.4 FR-9 parity: whatever --json's safe_upgrade_target/
            # safe_upgrade_reason show must also be visible here.
            if prescription.safe_upgrade_target is not None:
                lines.append(
                    f"      safe upgrade: {prescription.safe_upgrade_target} "
                    f"({_single_line(prescription.safe_upgrade_reason or '')})"
                )
            else:
                lines.append(f"      safe upgrade: none -- {_single_line(prescription.safe_upgrade_reason or '')}")
    _write_stdout("\n".join(lines) + "\n")


def _stderr(message: str) -> None:
    """Print one stderr diagnostic, absorbing any stream failure (mirrors
    warden's ``cli.py``'s own ``_stderr`` idiom)."""
    try:
        if sys.stderr is not None:
            print(message, file=sys.stderr)
    except Exception:  # noqa: BLE001 -- absorb everything, see docstring
        pass


def _write_stdout(text: str) -> None:
    """Write ``text`` to stdout, absorbing a ``BrokenPipeError`` (the
    consumer vanished, e.g. ``| head``) and any other stdout ``OSError``/
    ``ValueError`` -- the caller's exit code is already computed and must
    never be replaced by a stdout emission failure (mirrors warden's
    ``cli.py``, specifically its ``_run_doctor``'s rendering block).
    ``sys.stdout`` can legitimately be ``None`` (e.g. a detached/frozen
    process) -- guarded the same way the sibling ``_stderr`` already guards
    ``sys.stderr`` (review finding: this guard was missing here)."""
    if sys.stdout is None:
        return
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        _absorb_broken_pipe()
    except (OSError, ValueError) as exc:
        _stderr(f"doctor: stdout emission failed ({exc.__class__.__name__}); any partial stdout must not be consumed")


def _absorb_broken_pipe() -> None:
    """The stdout consumer vanished mid-emission (e.g. ``| head``): the
    exit code is already computed, so the pipe error is absorbed -- never a
    traceback. Mirrors warden's ``cli.py::_absorb_broken_pipe`` exactly:
    process-stream path (``sys.stdout`` IS ``sys.__stdout__``) re-points fd 1
    at ``os.devnull``; swapped-stream path (test captures, embedders) closes
    the stream object instead."""
    stream = sys.stdout
    if stream is sys.__stdout__:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(devnull, stream.fileno())
            finally:
                os.close(devnull)
        except OSError, ValueError, AttributeError:
            pass
        return
    try:
        stream.close()
    except Exception:  # noqa: BLE001 -- best effort, see docstring above
        pass


if __name__ == "__main__":
    raise SystemExit(main())
