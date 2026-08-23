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

Two of the six verbs here are still STUBs (Story 7.1's own scope -- naming
was contested until the 2026-08-10 correct-course settled it: the installer
lives *inside* ``pyforge-marshal``, no new package, no second binary, no
binding revival of the retired ``genesis`` name): ``run_explain``/
``run_version`` each print a one-line message naming themselves as not yet
implemented and return ``EXIT_OK``, imported from ``core/verdict.py`` (AD-7's
sole-ownership rule -- never a new exit-code literal here; used ONLY for the
literal ``0`` success value, per this story's own Boundaries bullet --
``core/verdict.py``'s MRS lattice itself is never reused for anything else).
``run_check`` (Story 10.5, FR-88..93), ``run_adopt`` (Story 10.6, FR-79..87),
``run_init`` (Story 10.7, FR-72..78), and ``run_update`` (Story 11.4,
FR-94/FR-97..101) are the four real ones. ``run_check`` loads the packaged
model manifest, resolves ``--repo-root`` (a plain ``argparse`` validation,
not a ``seed/verbs/preconditions.py`` rung -- ``check`` never calls that
mutating-verb gate), and delegates every real decision to ``seed.verbs.
check.run_check``, which is pure and read-only (see that module's own
docstring). ``run_adopt`` does the same for ``seed.verbs.adopt.run_adopt``,
the first MUTATING verb this module wires: it additionally resolves
``--agents``/``--skip`` into typed sequences and supplies the confirmation
seam (a real ``input()``-based prompt by default, overridable for tests)
that verb's own ``confirm`` parameter requires (see ``seed/verbs/adopt.py``'s
module docstring). ``run_init`` resolves ``<path>``/``--slug``/``--agents``/
``--force`` and delegates to ``seed.verbs.init.run_init`` -- unlike
``run_adopt``, it supplies no confirmation seam at all (``init`` never
confirms; see that module's own docstring). ``run_update`` resolves
``--repo-root``/``--run``/``--force``/``--include-seeded``/``--yes`` and
delegates to ``seed.verbs.update.run_update``, the SAME confirmation seam
``run_adopt`` supplies -- and gains its own plan renderer
(``_render_update_plan_text``), fixing ``DW-FU-11-3`` (a migration-offered
``copied-seeded`` skip renders as an explicit offer, never a false
``matched --skip`` claim) rather than reusing ``_render_plan_text``
(``adopt``-specific per its own docstring). This module's own job is thin
CLI plumbing: parse args, load the manifest, call the verb, render its
result as text, and map ``seed/errors.py``'s six-leaf taxonomy to a process
exit code -- it contains no detect/plan/hash/region/apply/materialize logic
of its own. No Copier import here (``seed.verbs.adopt``/``seed.verbs.init``/
``seed.verbs.update``/``seed.engine`` own that, per P-02) -- state/derive
logic beyond what ``adopt``/``init``/``update`` already wire belongs to
Epic 12.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from importlib import resources
from pathlib import Path

from ..core.verdict import EXIT_OK
from ..seed.detect.findings import Severity
from ..seed.errors import ConformanceFailure, InternalError, SeedError, UsageError
from ..seed.migrate import registry as migrate_registry
from ..seed.model.manifest import Manifest, ManifestError, load_manifest
from ..seed.plan.types import Plan
from ..seed.verbs.adopt import FIRST_CLAIM_MARKER, AdoptResult
from ..seed.verbs.adopt import run_adopt as _run_adopt_verb
from ..seed.verbs.check import CheckReport
from ..seed.verbs.check import run_check as _run_check_verb
from ..seed.verbs.init import InitResult
from ..seed.verbs.init import run_init as _run_init_verb
from ..seed.verbs.update import UpdateResult
from ..seed.verbs.update import run_update as _run_update_verb

# The severity groups a text report renders, in the fixed order the spec's
# own "matching bmad_drift_check.py's report shape" bullet requires:
# HARD before DRIFT before INFO, the same worst-first ordering the origin
# script and `Severity`'s own member declaration order both use.
_TEXT_REPORT_SEVERITY_ORDER: tuple[Severity, ...] = (Severity.HARD, Severity.DRIFT, Severity.INFO)


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


def _real_confirm() -> bool:
    """``run_adopt``'s (verb-layer) required ``confirm`` seam, defaulted
    HERE rather than inside ``seed.verbs.adopt`` (that module's own
    docstring: "the REAL ``input()``-based implementation is ``cli/seed.py``'s
    to construct and supply") -- this is this package's first interactive
    prompt, so there is no prior precedent to mirror beyond the seam shape
    itself. A closed/EOF stdin (``EOFError``) OR an operator-issued
    interrupt (``KeyboardInterrupt``, review finding -- Ctrl-C during the
    prompt previously propagated as a raw ``BaseException`` instead of the
    documented graceful decline) is treated as "no", never a hang or a
    crash -- the epics AC's own explicit requirement, since a ``--apply``
    invoked from a non-interactive context (a CI job with stdin redirected
    from ``/dev/null``) must refuse to apply rather than block forever
    waiting for input nobody can supply."""
    try:
        response = input("Apply this plan? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        return False
    return response.strip().lower() in {"y", "yes"}


def _parse_agents(raw: str | None) -> tuple[str, ...]:
    """``--agents``'s one comma-separated value (``--agents claude,cursor``,
    matching the epics AC's own singular-flag syntax) split into a tuple of
    non-blank, stripped names -- ``()`` when the flag was not given at all."""
    if raw is None:
        return ()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _render_plan_text(plan: Plan) -> str:
    """The human-reviewable rendering of a ``marshal seed adopt`` plan --
    one line per ``Action`` (its id, target path, and rationale) and one per
    skipped artifact, or an explicit "nothing to do" line for an empty plan
    (FR-84/AD-60's own idempotence case). ``adopt`` carries no ``--json``
    flag (this story's own Never bullet: "a written plan.json already IS
    the machine-readable artifact FR-82 asks for"), so this is the ONLY
    rendering this command ever prints.

    A first-claim (FR-83) action is prefixed ``[OVERWRITES EXISTING FILE]``
    (review finding): this feature's whole safety model is "a human reviews
    the plan before anything destructive happens," and burying "this
    overwrites a pre-existing, unrelated file" in prose indistinguishable
    at a glance from an ordinary "create" action undercuts that model.
    Detected via ``seed.verbs.adopt.FIRST_CLAIM_MARKER``, the same shared
    constant that module's own rationale text embeds -- never a
    independently-typed duplicate of that string here."""
    if not plan.actions:
        lines = ["marshal seed adopt -- plan is empty; nothing to do"]
    else:
        lines = [f"marshal seed adopt -- plan ({len(plan.actions)} action(s)):"]
        for action in plan.actions:
            marker = "[OVERWRITES EXISTING FILE] " if FIRST_CLAIM_MARKER in action.rationale else ""
            lines.append(f"  {marker}{action.artifact_id} ({action.target_path}): {action.rationale}")
    if plan.skipped:
        lines.append(f"skipped ({len(plan.skipped)}):")
        for skipped in plan.skipped:
            lines.append(
                f"  {skipped.artifact_id} ({skipped.target_path}):"
                f" matched --skip {skipped.pattern!r}"
            )
    return "\n".join(lines)


def run_adopt(
    args: argparse.Namespace,
    *,
    manifest: Manifest | None = None,
    confirm: Callable[[], bool] | None = None,
) -> int:
    """``marshal seed adopt`` (Story 10.6): thin CLI plumbing over
    ``seed.verbs.adopt.run_adopt`` -- this function performs no detect/
    plan/apply/materialize logic of its own; every real decision is that
    module's (see its own docstring for the full orchestration and the
    FR-83/FR-84 resolution it implements).

    ``manifest``/``confirm`` are both keyword-only test-injection seams,
    mirroring ``run_check``'s own ``manifest=`` convention one level
    further: a production caller (``main.py``'s dispatch) never supplies
    either, so ``manifest`` defaults to the packaged one and ``confirm`` to
    ``_real_confirm`` (this module's real, ``input()``-based prompt) --
    production behavior is unchanged either way.

    The verb call is INSIDE the ``try``, and a bare ``Exception`` is wrapped
    as ``InternalError`` rather than left to escape as a traceback -- the
    identical widened try/except shape ``run_check`` above already
    establishes (10.5's own review finding), extended to this command."""
    try:
        repo_root = _resolve_repo_root(args.repo_root)
        if manifest is None:
            manifest = _load_packaged_manifest()
        result: AdoptResult = _run_adopt_verb(
            repo_root,
            manifest,
            apply=args.apply,
            yes=args.yes,
            agents=_parse_agents(args.agents),
            skip=tuple(args.skip) if args.skip else (),
            force=args.force,
            confirm=confirm if confirm is not None else _real_confirm,
        )
    except ManifestError as exc:
        wrapped = InternalError(
            f"the packaged seed manifest could not be loaded: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the packaged manifest.yaml ships inside"
                " the distribution and its absence or corruption is a broken"
                " installation, not a problem with the repository being adopted"
            ),
        )
        _print_seed_error(wrapped, as_json=False)
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, as_json=False)
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, as_json=False)
        return wrapped.exit_code

    print(_render_plan_text(result.plan))
    if result.declined:
        print("adopt: apply declined; nothing was applied.")
    elif result.applied is not None:
        if result.applied:
            print(f"adopt: applied {len(result.applied)} artifact(s): {', '.join(result.applied)}")
        else:
            print("adopt: plan was empty; nothing to apply.")
    else:
        print("adopt: dry-run; re-run with --apply to execute this plan.")

    return EXIT_OK


def _render_init_result_text(result: InitResult) -> str:
    """The human-readable ``marshal seed init`` report -- mirrors ``_render_
    plan_text``'s per-action listing (id, target path, rationale), but with
    no "dry-run"/"declined" branches at all: ``init`` never dry-runs and
    never confirms (that module's own docstring), so there is exactly one
    outcome to render -- what was actually applied, or, for a ``--force``'d
    target whose every filtered entry was already conformant, that nothing
    needed to happen."""
    lines = [f"marshal seed init -- slug {result.slug!r}:"]
    if not result.plan.actions:
        lines.append("  plan is empty; nothing to do")
    else:
        lines.append(f"  plan ({len(result.plan.actions)} action(s)):")
        for action in result.plan.actions:
            lines.append(f"    {action.artifact_id} ({action.target_path}): {action.rationale}")
        lines.append(f"applied {len(result.applied)} artifact(s): {', '.join(result.applied)}")
    return "\n".join(lines)


def run_init(
    args: argparse.Namespace,
    *,
    manifest: Manifest | None = None,
) -> int:
    """``marshal seed init`` (Story 10.7): thin CLI plumbing over ``seed.
    verbs.init.run_init`` -- this function performs no bootstrap/detect/
    plan/apply/materialize logic of its own; every real decision is that
    module's (see its own docstring for the full orchestration).

    ``manifest`` is the same keyword-only test-injection seam ``run_check``/
    ``run_adopt`` already establish; a production caller (``main.py``'s
    dispatch) never supplies it. Unlike ``run_adopt``, there is no
    ``confirm=`` seam here at all -- ``init`` never confirms (``seed.verbs.
    init``'s own docstring).

    The verb call is INSIDE the ``try``, and a bare ``Exception`` is wrapped
    as ``InternalError`` rather than left to escape as a traceback -- the
    identical widened try/except shape ``run_check``/``run_adopt`` already
    establish."""
    try:
        path = Path(args.path)
        if manifest is None:
            manifest = _load_packaged_manifest()
        result: InitResult = _run_init_verb(
            path,
            manifest,
            slug=args.slug,
            agents=_parse_agents(args.agents),
            force=args.force,
        )
    except ManifestError as exc:
        wrapped = InternalError(
            f"the packaged seed manifest could not be loaded: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the packaged manifest.yaml ships inside"
                " the distribution and its absence or corruption is a broken"
                " installation, not a problem with the directory being initialized"
            ),
        )
        _print_seed_error(wrapped, as_json=False)
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, as_json=False)
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, as_json=False)
        return wrapped.exit_code

    print(_render_init_result_text(result))
    return EXIT_OK


def _render_update_plan_text(plan: Plan) -> str:
    """The human-reviewable rendering of a ``marshal seed update`` plan --
    mirrors ``_render_plan_text``'s own shape (one line per ``Action``, one
    per skipped artifact, an explicit "nothing to do" line for an empty
    plan), but ``update`` gets its OWN renderer rather than reusing
    ``_render_plan_text`` unmodified (that one is ``adopt``-specific per its
    own docstring) so it can fix ``DW-FU-11-3``: a migration-offered
    ``copied-seeded`` skip (``SkippedArtifact.pattern ==
    migrate_registry._SEEDED_OFFER_PATTERN``) renders as an explicit
    migration offer, never the generic ``matched --skip {pattern!r}``
    sentence that would falsely imply a ``--skip`` glob was given."""
    if not plan.actions:
        lines = ["marshal seed update -- plan is empty; nothing to do"]
    else:
        lines = [f"marshal seed update -- plan ({len(plan.actions)} action(s)):"]
        for action in plan.actions:
            lines.append(f"  {action.artifact_id} ({action.target_path}): {action.rationale}")
    if plan.skipped:
        lines.append(f"skipped ({len(plan.skipped)}):")
        for skipped in plan.skipped:
            if skipped.pattern == migrate_registry._SEEDED_OFFER_PATTERN:
                lines.append(
                    f"  {skipped.artifact_id} ({skipped.target_path}):"
                    " offered by a migration; not applied without --include-seeded"
                )
            else:
                lines.append(
                    f"  {skipped.artifact_id} ({skipped.target_path}):"
                    f" matched --skip {skipped.pattern!r}"
                )
    return "\n".join(lines)


def _render_referenced_dep_findings_text(findings: tuple) -> str:
    """DRIFT-only referenced-dependency findings for ``marshal seed update``."""
    lines = [f"referenced dependencies ({len(findings)} DRIFT finding(s)):"]
    for finding in findings:
        lines.append(f"  {finding.path}: {finding.message}")
    return "\n".join(lines)


def run_update(
    args: argparse.Namespace,
    *,
    manifest: Manifest | None = None,
    confirm: Callable[[], bool] | None = None,
) -> int:
    """``marshal seed update`` (Story 11.4): thin CLI plumbing over
    ``seed.verbs.update.run_update`` -- this function performs no detect/
    plan/migrate/apply/materialize logic of its own; every real decision is
    that module's (see its own docstring for the full orchestration and the
    three-source merge it implements).

    ``manifest``/``confirm`` are the identical keyword-only test-injection
    seams ``run_adopt`` already establishes, extended here unchanged.

    The verb call is INSIDE the ``try``, and a bare ``Exception`` is wrapped
    as ``InternalError`` rather than left to escape as a traceback -- the
    identical widened try/except shape ``run_check``/``run_adopt``/
    ``run_init`` already establish."""
    try:
        repo_root = _resolve_repo_root(args.repo_root)
        if manifest is None:
            manifest = _load_packaged_manifest()
        result: UpdateResult = _run_update_verb(
            repo_root,
            manifest,
            run=args.run,
            force=args.force,
            include_seeded=args.include_seeded,
            yes=args.yes,
            confirm=confirm if confirm is not None else _real_confirm,
        )
    except ManifestError as exc:
        wrapped = InternalError(
            f"the packaged seed manifest could not be loaded: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the packaged manifest.yaml ships inside"
                " the distribution and its absence or corruption is a broken"
                " installation, not a problem with the repository being updated"
            ),
        )
        _print_seed_error(wrapped, as_json=False)
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, as_json=False)
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, as_json=False)
        return wrapped.exit_code

    print(_render_update_plan_text(result.plan))
    if result.referenced_dep_findings:
        print(_render_referenced_dep_findings_text(result.referenced_dep_findings))
    if result.declined:
        print("update: apply declined; nothing was applied.")
    elif result.applied is not None:
        if result.applied:
            print(f"update: applied {len(result.applied)} artifact(s): {', '.join(result.applied)}")
        else:
            print("update: plan was empty; nothing to apply.")
    else:
        print("update: dry-run; re-run with --run to execute this plan.")

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
            "The seed-installer noun group. `check` (Story 10.5), `adopt` "
            "(Story 10.6), and `init` (Story 10.7) are real; `update`/`explain`/"
            "`version` are still stubs from Story 7.1 -- their real logic lands "
            "in Epics 11, 12."
        ),
    )
    seed_subparsers = parser.add_subparsers(dest="seed_command", required=True)

    init_parser = seed_subparsers.add_parser(
        "init",
        help="Scaffold a brand-new project from Marshal's seed templates.",
        description=(
            "Story 10.7: bootstrap (mkdir + git init if needed) -> detect -> plan ->"
            " preconditions -> apply DIRECTLY -- no dry-run, no confirm prompt"
            " (FR-78's non-empty-directory refusal is this verb's own safety gate)."
        ),
    )
    init_parser.add_argument(
        "path",
        metavar="PATH",
        help="The target directory to scaffold (created, and git-initialized, if needed).",
    )
    init_parser.add_argument(
        "--slug",
        dest="slug",
        default=None,
        metavar="SLUG",
        help="The project slug substituted into every {{ slug }}-templated path/answer"
        " (default: PATH's resolved directory name).",
    )
    init_parser.add_argument(
        "--agents",
        dest="agents",
        default=None,
        metavar="LIST",
        help="Comma-separated agent adapters to record, e.g. claude,cursor.",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Proceed even though PATH already exists and is non-empty (FR-78).",
    )
    init_parser.set_defaults(handler=run_init)

    adopt_parser = seed_subparsers.add_parser(
        "adopt",
        help="Adopt an existing project onto Marshal's seed templates.",
        description=(
            "Story 10.6: detect -> plan -> confirm -> apply -> state-write. Dry-run"
            " by default -- writes only .marshal/plan.json and prints it; --apply"
            " executes the plan (prompting for confirmation unless --yes is given)."
        ),
    )
    adopt_parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=None,
        metavar="PATH",
        help="The target repo to adopt (default: the current working directory).",
    )
    adopt_parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute the plan (default: dry-run -- compute and print the plan only).",
    )
    adopt_parser.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help="Skip the confirmation prompt when applying (unattended/CI use).",
    )
    adopt_parser.add_argument(
        "--agents",
        dest="agents",
        default=None,
        metavar="LIST",
        help="Comma-separated agent adapters to record, e.g. claude,cursor.",
    )
    adopt_parser.add_argument(
        "--skip",
        dest="skip",
        action="append",
        default=None,
        metavar="GLOB",
        help="Glob naming an artifact path to leave untouched (repeatable).",
    )
    adopt_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Bypass the hand-edited-managed-content precondition (rung 6 only).",
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
        description=(
            "Story 11.4: detect -> plan (migrations + absent entries + wholesale"
            " regenerate, merged) -> confirm -> apply -> state-write. Dry-run by"
            " default -- writes only .marshal/plan.json and prints it; --run executes"
            " the plan (prompting for confirmation unless --yes is given)."
        ),
    )
    update_parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=None,
        metavar="PATH",
        help="The target repo to update (default: the current working directory).",
    )
    update_parser.add_argument(
        "--run",
        action="store_true",
        default=False,
        help="Execute the plan (default: dry-run -- compute and print the plan only).",
    )
    update_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help=(
            "Bypass the hand-edited-managed-content precondition (rung 6 only) and"
            " materialize whole-file artifacts via Copier's recopy semantics."
        ),
    )
    update_parser.add_argument(
        "--include-seeded",
        action="store_true",
        default=False,
        help="Also apply a migration-offered copied-seeded action (skipped by default).",
    )
    update_parser.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help="Skip the confirmation prompt when applying (unattended/CI use).",
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
