"""``marshal seed`` (Story 7.1, AD-70) -- the seed-installer noun group's CLI
scaffold. Registers ``seed`` on the SAME ``subparsers`` object every other
noun group uses, with six nested verb actions (``init``/``adopt``/``check``/
``update``/``explain``/``version`` -- the same six verb names architecture
§ 4 assigns one file each under ``seed/verbs/`` in a later story; here they
are stub functions in THIS module, not yet split into that package),
mirroring ``cli/gate.py``'s ``add_gate_subparser`` nested-``evaluate``-action
shape: ``seed_subparsers = parser.add_subparsers(dest="seed_command",
required=True)``, one ``add_parser`` per verb. ``required=True`` means a
bare ``marshal seed`` with no verb is a clean argparse usage error, not a
silent no-op -- same convention as ``gate``'s own ``gate_command``.

Five of the six verbs here are still STUBs (Story 7.1's own scope -- naming
was contested until the 2026-08-10 correct-course settled it: the installer
lives *inside* ``pyforge-marshal``, no new package, no second binary, no
binding revival of the retired ``genesis`` name): each prints a one-line
message naming itself as not yet implemented and returns ``EXIT_OK``,
imported from ``core/verdict.py`` (AD-7's sole-ownership rule -- never a new
exit-code literal here; used ONLY for the literal ``0`` success value, per
this story's own Boundaries bullet -- ``core/verdict.py``'s MRS lattice
itself is never reused for anything else). ``run_check`` (Story 10.5,
FR-88..93) is the first real one: it loads the packaged model manifest,
resolves ``--repo-root`` (a plain ``argparse`` validation, not a
``seed/verbs/preconditions.py`` rung -- ``check`` never calls that
mutating-verb gate), and delegates every real decision to
``seed.verbs.check.run_check``, which is pure and read-only (see that
module's own docstring). This module's own job is thin CLI plumbing: parse
args, load the manifest, call the verb, render its ``CheckReport`` as text
or ``--json``, and map ``seed/errors.py``'s six-leaf taxonomy to a process
exit code -- it contains no detect/plan/hash/region logic of its own. No
Copier import, no state/apply/engine/derive/migrate logic lands here --
those belong to Epics 8, 10.6, 10.7, 11, 12.
"""

from __future__ import annotations

import argparse
import json
from importlib import resources
from pathlib import Path

from ..core.verdict import EXIT_OK
from ..seed.detect.findings import Severity
from ..seed.errors import ConformanceFailure, InternalError, SeedError, UsageError
from ..seed.model.manifest import Manifest, ManifestError, load_manifest
from ..seed.verbs.check import CheckReport
from ..seed.verbs.check import run_check as _run_check_verb

# The severity groups a text report renders, in the fixed order the spec's
# own "matching bmad_drift_check.py's report shape" bullet requires:
# HARD before DRIFT before INFO, the same worst-first ordering the origin
# script and `Severity`'s own member declaration order both use.
_TEXT_REPORT_SEVERITY_ORDER: tuple[Severity, ...] = (Severity.HARD, Severity.DRIFT, Severity.INFO)


def run_init(args: argparse.Namespace) -> int:
    print("marshal seed init: not yet implemented")
    return EXIT_OK


def run_adopt(args: argparse.Namespace) -> int:
    print("marshal seed adopt: not yet implemented")
    return EXIT_OK


def _load_packaged_manifest() -> Manifest:
    """The bundled model manifest (``seed/templates/manifest.yaml``),
    loaded through ``importlib.resources`` so it keeps working from a
    zipped or relocated install -- mirrors ``engine/copier.py::
    _load_packaged_manifest``'s identical shape, duplicated rather than
    imported: that function is private to a sibling module, and this
    package's established stance (``verbs/skips.py``'s module docstring) is
    that a small duplicated helper beats reaching into a neighbour's
    private namespace. A ``ManifestError`` here names a broken
    INSTALLATION, never a problem with the target repo being checked --
    the caller wraps it as ``InternalError`` (exit 10), matching
    ``state/store.py``'s identical "broken install, not invalid state"
    distinction for its own packaged ``schema.json``."""
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        return load_manifest(manifest_path)


def _resolve_repo_root(raw: str | None) -> Path:
    """``--repo-root``, or the current working directory when omitted --
    validated as a real, existing directory before anything downstream
    trusts it. Raises ``UsageError`` (exit 2), never
    ``verbs.preconditions.PreconditionFailure`` (exit 3): that ladder is a
    MUTATING verb's gate (this story's own Never bullets forbid ``check``
    from calling it), and a misspelled ``--repo-root`` is an ordinary
    invalid-CLI-argument, the exact case ``UsageError``'s own docstring
    names."""
    candidate = Path(raw) if raw is not None else Path.cwd()
    if not candidate.is_dir():
        raise UsageError(
            f"--repo-root {str(candidate)!r} does not resolve to an existing directory",
            remedy=(
                "pass an existing directory to --repo-root, or omit it to check the"
                " current working directory"
            ),
        )
    return candidate


def _render_check_report_text(report: CheckReport) -> str:
    """The human-readable ``marshal seed check`` report: a model-version
    status line, then one severity-grouped section per non-empty group with
    a per-group count, each finding rendered as ``path: message`` -- the
    spec's own "matching ``bmad_drift_check.py``'s report shape" bullet.
    Reads only ``report.by_severity``/public fields, never re-derives
    ``failing`` (that rule lives in exactly one place, ``CheckReport.failing``,
    so this renderer and ``--json`` can never disagree about it)."""
    lines = [
        (
            "marshal seed check"
            f" -- model_version: manifest={report.manifest_model_version}"
            f" state={report.state_model_version or '(never adopted)'}"
            f" status={report.model_version_status.value}"
        )
    ]
    if not report.findings:
        lines.append("no findings -- the repo conforms to the installed seed model")
    for severity in _TEXT_REPORT_SEVERITY_ORDER:
        group = report.by_severity(severity)
        if not group:
            continue
        lines.append(f"{severity.value} ({len(group)}):")
        for finding in group:
            lines.append(f"  {finding.path}: {finding.message}")
    lines.append(f"result: {'FAIL' if report.failing else 'OK'}")
    return "\n".join(lines)


def _print_seed_error(exc: SeedError, *, as_json: bool) -> None:
    """Render a caught ``SeedError`` the same way a clean/failing run is
    rendered: honoring ``--json`` on the error path exactly as it is
    honored on the success path (review finding -- a CI harness that
    unconditionally parses stdout as JSON whenever ``--json`` was passed
    must get JSON on every exit code, not text on some and JSON on
    others)."""
    if as_json:
        print(
            json.dumps(
                {"error": {"type": type(exc).__name__, "message": exc.message, "remedy": exc.remedy}},
                indent=2,
            )
        )
    else:
        print(str(exc))


def run_check(args: argparse.Namespace, *, manifest: Manifest | None = None) -> int:
    """``marshal seed check`` (Story 10.5): thin CLI plumbing over
    ``seed.verbs.check.run_check``, the pure read-only detector -- this
    function performs no detect/plan/hash/region logic of its own.

    ``manifest`` is keyword-only and defaults to the packaged one -- a
    caller (``main.py``'s dispatch) never supplies it, so production
    behavior is unchanged; it exists purely as the same test-injection seam
    ``cli/adapters.py::run_adapters_sync(args, fs=..., harness=...)`` already
    establishes for this package's CLI functions, so a test can exercise
    every exit-code path against a small synthetic manifest instead of the
    real 43-entry packaged one.

    The verb call is INSIDE the ``try`` (review finding -- it was
    previously outside, so a ``SeedError`` raised deep in the call chain,
    or an unguarded OS-level failure such as a missing ``git`` executable
    reached via ``plan.build.build_plan``'s subprocess calls, escaped
    ``main.py``'s dispatcher uncaught as a raw traceback: ``main.py`` only
    catches ``SystemExit``/``KeyboardInterrupt``, never a bare
    ``Exception``). Catches ``SeedError`` and returns ``exc.exit_code``,
    giving every ``SeedError`` leaf one uniform rendering path. A bare
    ``Exception`` (a genuinely unanticipated failure this module did not
    predict -- ``seed.verbs.check.run_check``'s own docstring says the verb
    call never raises, but that is an assumption, not an enforced
    guarantee, per the same review finding) is wrapped as ``InternalError``
    (exit 10) rather than allowed to reach the user as a traceback -- the
    ONE deliberate catch-``Exception`` boundary in this package, matching
    ``core/verdict.py``'s own top-level-dispatcher precedent; it is a CLI
    entry-point backstop, not a pattern any other ``seed/`` module may
    copy (``tests/meta/test_seed_no_bare_exception.py`` only bans RAISING a
    bare ``Exception``, never catching one, so this is within that guard's
    own stated bounds). A clean or failing conformance run is NOT an
    exception: ``ConformanceFailure.exit_code`` is read as a plain class
    attribute for the failing case, matching the epics AC's framing of a
    non-zero exit as this command's ORDINARY designed output, not an
    exceptional one."""
    try:
        repo_root = _resolve_repo_root(args.repo_root)
        if manifest is None:
            manifest = _load_packaged_manifest()
        report = _run_check_verb(repo_root, manifest, strict=args.strict)
    except ManifestError as exc:
        wrapped = InternalError(
            f"the packaged seed manifest could not be loaded: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the packaged manifest.yaml ships inside"
                " the distribution and its absence or corruption is a broken"
                " installation, not a problem with the repository being checked"
            ),
        )
        _print_seed_error(wrapped, as_json=args.json)
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, as_json=args.json)
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, as_json=args.json)
        return wrapped.exit_code

    if args.json:
        print(json.dumps(report.to_json_dict(), indent=2))
    else:
        print(_render_check_report_text(report))

    return ConformanceFailure.exit_code if report.failing else EXIT_OK


def run_update(args: argparse.Namespace) -> int:
    print("marshal seed update: not yet implemented")
    return EXIT_OK


def run_explain(args: argparse.Namespace) -> int:
    print("marshal seed explain: not yet implemented")
    return EXIT_OK


def run_version(args: argparse.Namespace) -> int:
    print("marshal seed version: not yet implemented")
    return EXIT_OK


def add_seed_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``seed`` subcommand on ``main.py``'s subparser tree, with
    six nested verb actions -- mirrors ``cli/gate.py::add_gate_subparser``'s
    identical nested-subparsers shape, one level down (six verbs instead of
    one ``evaluate`` action)."""
    parser = subparsers.add_parser(
        "seed",
        help="Scaffold/adopt/check/update a project from Marshal's seed templates (AD-70).",
        description=(
            "The seed-installer noun group. `check` (Story 10.5) is real; the "
            "other five verbs are still stubs from Story 7.1 -- their real "
            "detect/plan/apply/Copier logic lands in Epics 8, 10.6, 10.7, 11, 12."
        ),
    )
    seed_subparsers = parser.add_subparsers(dest="seed_command", required=True)

    init_parser = seed_subparsers.add_parser(
        "init",
        help="Scaffold a brand-new project from Marshal's seed templates.",
        description="Stub (Story 7.1) -- greenfield materialization lands in a later story.",
    )
    init_parser.set_defaults(handler=run_init)

    adopt_parser = seed_subparsers.add_parser(
        "adopt",
        help="Adopt an existing project onto Marshal's seed templates.",
        description="Stub (Story 7.1) -- brownfield adoption lands in a later story.",
    )
    adopt_parser.set_defaults(handler=run_adopt)

    check_parser = seed_subparsers.add_parser(
        "check",
        help="Report whether a project's seed state matches its templates.",
        description=(
            "Story 10.5: a read-only conformance report -- detect + plan, writes"
            " unreachable. Exits non-zero on any HARD finding; --strict also fails"
            " on DRIFT."
        ),
    )
    check_parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=None,
        metavar="PATH",
        help="The target repo to check (default: the current working directory).",
    )
    check_parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Also fail (non-zero exit) on DRIFT findings, not only HARD ones.",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit the full findings report as JSON instead of the text report.",
    )
    check_parser.set_defaults(handler=run_check)

    update_parser = seed_subparsers.add_parser(
        "update",
        help="Apply pending seed-template updates to a project.",
        description="Stub (Story 7.1) -- migration/update logic lands in a later story.",
    )
    update_parser.set_defaults(handler=run_update)

    explain_parser = seed_subparsers.add_parser(
        "explain",
        help="Explain what a seed operation would do without applying it.",
        description="Stub (Story 7.1) -- plan rationale rendering lands in a later story.",
    )
    explain_parser.set_defaults(handler=run_explain)

    version_parser = seed_subparsers.add_parser(
        "version",
        help="Report the seed templates' own version.",
        description="Stub (Story 7.1) -- model-version reporting lands in a later story.",
    )
    version_parser.set_defaults(handler=run_version)
