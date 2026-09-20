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

Story 28.3 adds a SEVENTH verb, ``kit`` (``run_kit`` ->
``seed.verbs.kit.run_kit``): Genesis's provisioning of the per-loop-home
token-economy kit (SPEC-marshal-token-economy CAP-3/CAP-4). It follows every
convention above -- thin plumbing, keyword-only injection seams
(``manifest``/``fs``), dry-run by default with ``--apply``, ``--json``/
``--quiet`` -- and adds this module's ONE new boundary read:
``resolve_context_layers`` reads the TARGET repo's policy files (repo
defaults + the project layer) and folds them through ``core.policy``'s own
``compose``/``resolve_context_layers``, so both ``check`` and ``kit`` get
Story 28.1's declaration from the single composition site CAP-1 requires
rather than a second parser. It is resolved against the ``--repo-root`` the
operator named, NOT against ``cli/config.repo_root()`` (which derives from
this module's install location and would read the main checkout's policy for
every loop home).
"""

from __future__ import annotations

import argparse
import json
import os
import tomllib
from collections.abc import Callable, Mapping
from importlib import resources
from pathlib import Path

from ..adapters.fs_local import LocalFs
from ..core import policy
from ..core.verdict import EXIT_OK
from ..ports.fs import FsPort
from ..seed.detect.findings import Severity
from ..seed.detect.kit import KitCheck
from ..seed.errors import ConformanceFailure, InternalError, SeedError, UsageError
from ..seed.migrate import registry as migrate_registry
from ..seed.model.manifest import Manifest, ManifestError, load_manifest
from ..seed.model.version import ModelVersion
from ..seed.plan.types import Plan
from ..seed.verbs.adopt import FIRST_CLAIM_MARKER, AdoptResult
from ..seed.verbs.adopt import run_adopt as _run_adopt_verb
from ..seed.verbs.check import CheckReport
from ..seed.verbs.check import run_check as _run_check_verb
from ..seed.verbs.explain import render_explain_text
from ..seed.verbs.explain import run_explain as _run_explain_verb
from ..seed.verbs.init import InitResult
from ..seed.verbs.init import run_init as _run_init_verb
from ..seed.verbs.kit import KitAction, KitResult, timeout_note
from ..seed.verbs.kit import run_kit as _run_kit_verb
from ..seed.verbs.update import UpdateResult
from ..seed.verbs.update import run_update as _run_update_verb
from ..seed.verbs.version import render_version_text
from ..seed.verbs.version import run_version as _run_version_verb
from .config import PROJECT_POLICY_RELPATH, REPO_POLICY_DEFAULTS_RELPATH

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


def packaged_seed_model_version() -> ModelVersion:
    """The bundled manifest's ``model_version``, for a caller that needs the
    clock but not the model (Story 28.3: ``cli/init.py``'s preflight stamps
    it into the deployed skill's managed-region marker).

    A thin public wrapper over ``_load_packaged_manifest`` rather than a
    second loader, so ``cli/init.py`` never reaches into this module's
    private namespace and there is still exactly one place the packaged
    manifest is read from. Propagates ``ManifestError`` unchanged -- a
    broken installation, which the caller reports in its own vocabulary."""
    return _load_packaged_manifest().model_version


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
            remedy=("pass an existing directory to --repo-root, or omit it to check the current working directory"),
        )
    return candidate


#: The BMAD active-project marker a provisioned loop home carries
#: (`cli/init.py` writes it). Read here -- and ONLY here, at the CLI
#: boundary -- so `marshal seed check`/`kit` invoked against a loop home can
#: find that home's own project policy without an explicit `--project`.
_ACTIVE_PROJECT_MARKER_RELPATH = "_bmad/custom/.active-project"

#: `cli/config.py`'s two policy-file conventions, re-resolved against the
#: TARGET repo rather than against this module's own install location.
#: `cli/config.repo_root()` derives the root from `__file__` -- correct for
#: `marshal config`, which always means "this checkout's policy", and WRONG
#: here: `marshal seed check --repo-root <loop home>` must read the LOOP
#: HOME's policy, and marshal is installed once from the main checkout for
#: every home. The relpath templates are imported from `cli/config.py`
#: rather than re-spelled, so the two can never disagree about where a
#: policy file lives.
_REPO_DEFAULTS_RELPATH = REPO_POLICY_DEFAULTS_RELPATH
_PROJECT_POLICY_RELPATH = PROJECT_POLICY_RELPATH


def _read_toml_or_empty(path: Path) -> Mapping[str, object]:
    """A parsed TOML mapping, or ``{}`` for anything unreadable.

    Deliberately silent: a policy layer that cannot be read composes to
    "nothing declared", which resolves every ``[context]`` layer OFF and so
    produces no kit findings. Degrading toward OFF is the only safe
    direction here -- the alternative (guessing a layer is on) would report
    a missing kit for a home that never asked for one."""
    try:
        with open(path, "rb") as handle:
            payload = tomllib.load(handle)
    except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _resolve_project_slug(repo_root: Path, explicit: str | None) -> str:
    """The project whose policy layer applies to ``repo_root``.

    Precedence mirrors `cli/config.py`'s own (`--project` beats
    `BMAD_ACTIVE_PROJECT`) and then adds the one source that is specific to
    a loop home: the home's own `_bmad/custom/.active-project` marker. That
    marker is what makes `marshal seed check --repo-root <home>` work with
    no flags at all -- CLAUDE.md's standing rule is that a parallel agent
    passes `BMAD_ACTIVE_PROJECT` per invocation and never runs
    `scripts/bmad-switch`, so a stale env var must not be the only answer
    available. `is not None`, never `or`: an explicit `--project ""` wins
    over the env var, the same trap `run_config` documents."""
    if explicit is not None:
        return explicit
    from_env = os.environ.get("BMAD_ACTIVE_PROJECT", "")
    if from_env:
        return from_env
    marker = repo_root / _ACTIVE_PROJECT_MARKER_RELPATH
    try:
        return marker.read_text(encoding="utf-8").strip()
    except OSError, UnicodeDecodeError:
        return ""


def resolve_context_layers(repo_root: Path, explicit_slug: str | None) -> dict[str, dict[str, object]]:
    """Story 28.1's `[context]` declaration, resolved for ``repo_root``.

    All the file I/O one CLI boundary owes the pure layers below it: read
    the repo-defaults layer, read the project layer, fold them through the
    SAME `policy.compose` every other marshal command uses, and expand the
    result through the SAME `policy.resolve_context_layers` both engines
    already call. No second parser and no second "layer absent = off" rule
    -- CAP-1's own requirement is that every consumer resolves the
    declaration from one composition site.

    Never raises: a malformed slug, an unreadable file, or a malformed
    `[context]` block all compose to "nothing declared" (`compose` reports
    those as `MRS-POLICY-*` findings, which this read-only path does not
    surface -- `marshal config` is the command that exists to show them)."""
    slug = _resolve_project_slug(repo_root, explicit_slug)
    repo_defaults = _read_toml_or_empty(repo_root / _REPO_DEFAULTS_RELPATH)
    project: Mapping[str, object] = {}
    if slug and policy._is_valid_project_slug(slug):
        project = _read_toml_or_empty(repo_root / _PROJECT_POLICY_RELPATH.format(slug=slug))
        effective, _ = policy.compose(project_slug=slug, repo_defaults=repo_defaults, project=project, flags={})
    else:
        effective, _ = policy.compose(project_slug="", repo_defaults=repo_defaults, project={}, flags={})
    return policy.resolve_context_layers(effective)


def _render_kit_text(checks: tuple[KitCheck, ...]) -> list[str]:
    """The kit section both `check` and `kit` render -- one line per item,
    status first so a scan down the column reads as a checklist."""
    if not checks:
        return []
    lines = [f"token-economy kit ({len(checks)} check(s)):"]
    for check in checks:
        lines.append(f"  [{check.status.value}] {check.item_id}: {check.detail}")
    return lines


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
    lines.extend(_render_kit_text(report.kit))
    lines.append(f"result: {'FAIL' if report.failing else 'OK'}")
    return "\n".join(lines)


def _print_seed_error(
    exc: SeedError,
    *,
    verb: str,
    as_json: bool,
    quiet: bool = False,
) -> None:
    """Render a caught ``SeedError`` the same way a clean/failing run is
    rendered: honoring ``--json`` on the error path exactly as it is
    honored on the success path (review finding -- a CI harness that
    unconditionally parses stdout as JSON whenever ``--json`` was passed
    must get JSON on every exit code, not text on some and JSON on
    others). Story 12.5 wraps every JSON emission in the schema-stable
    ``{verb, ok, error|result}`` envelope (FR-123 / NFR-12). ``--quiet``
    suppresses text chatter but never swallows JSON or error text."""
    if as_json:
        print(json.dumps(_json_error_envelope(verb, exc), indent=2))
    elif not quiet:
        print(str(exc))


def _flag(args: argparse.Namespace, name: str, default: bool = False) -> bool:
    """Read a boolean CLI flag with a default, so older hand-built
    ``argparse.Namespace`` test fixtures that pre-date Story 12.5's
    ``--json``/``--quiet``/``--dry-run`` wiring keep working."""
    return bool(getattr(args, name, default))


def _json_ok_envelope(verb: str, result: dict[str, object]) -> dict[str, object]:
    """Schema-stable success envelope shared by every ``marshal seed`` verb
    (Story 12.5, FR-123 / NFR-12): fixed top-level keys ``verb``/``ok``/
    ``result``, verb-specific payload nested under ``result``."""
    return {"verb": verb, "ok": True, "result": result}


def _json_error_envelope(verb: str, exc: SeedError) -> dict[str, object]:
    """Schema-stable error envelope: same top-level keys as success, with
    ``ok: false`` and ``error`` carrying the S-7.2 leaf's type/message/
    remedy (never a bare traceback)."""
    return {
        "verb": verb,
        "ok": False,
        "error": {
            "type": type(exc).__name__,
            "message": exc.message,
            "remedy": exc.remedy,
        },
    }


def _emit_success(
    *,
    verb: str,
    as_json: bool,
    quiet: bool,
    result: dict[str, object] | None = None,
    text: str | None = None,
) -> None:
    """Print either the schema-stable JSON envelope or the human text
    report. ``--quiet`` suppresses text; JSON is always emitted when
    ``--json`` is set (machine consumers need the payload)."""
    if as_json:
        print(json.dumps(_json_ok_envelope(verb, result or {}), indent=2))
    elif not quiet and text is not None:
        print(text)


def _add_json_quiet_flags(parser: argparse.ArgumentParser) -> None:
    """FR-123: every seed verb accepts ``--json`` and ``--quiet``."""
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Emit the schema-stable JSON envelope instead of the text report.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress human-readable stdout (JSON still emitted when --json is set).",
    )


def _add_project_flag(parser: argparse.ArgumentParser) -> None:
    """Story 28.3: which project's policy layer supplies the ``[context]``
    declaration. Omitted resolves through ``BMAD_ACTIVE_PROJECT`` and then
    the target home's own ``_bmad/custom/.active-project`` marker (see
    ``_resolve_project_slug``) -- so an operator inside a provisioned loop
    home never has to pass it."""
    parser.add_argument(
        "--project",
        dest="project",
        default=None,
        metavar="SLUG",
        help=(
            "Project whose marshal-policy.toml supplies the [context] declaration"
            " (default: BMAD_ACTIVE_PROJECT, then the home's own active-project marker)."
        ),
    )


def _add_dry_run_flag(parser: argparse.ArgumentParser) -> None:
    """FR-124: mutating verbs accept ``--dry-run`` explicitly."""
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=False,
        help="Compute and print the plan without applying it.",
    )


def _plan_result_dict(plan: Plan) -> dict[str, object]:
    return plan.to_json_dict()


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
        # Story 28.3: the ONE boundary read this verb owes the pure layer --
        # the target repo's own `[context]` declaration. Resolved here, never
        # inside `seed.verbs.check`, matching this module's own established
        # "the CLI does the file I/O and calls the verb" split.
        report = _run_check_verb(
            repo_root,
            manifest,
            strict=args.strict,
            context_layers=resolve_context_layers(repo_root, getattr(args, "project", None)),
        )
    except ManifestError as exc:
        wrapped = InternalError(
            f"the packaged seed manifest could not be loaded: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the packaged manifest.yaml ships inside"
                " the distribution and its absence or corruption is a broken"
                " installation, not a problem with the repository being checked"
            ),
        )
        _print_seed_error(wrapped, verb="check", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, verb="check", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, verb="check", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code

    _emit_success(
        verb="check",
        as_json=_flag(args, "json"),
        quiet=_flag(args, "quiet"),
        result=report.to_json_dict(),
        text=_render_check_report_text(report),
    )

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
    except EOFError, KeyboardInterrupt:
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
    (FR-84/AD-60's own idempotence case). Story 12.5 adds ``--json`` (the
    schema-stable envelope nests ``plan.to_json_dict()`` under ``result``);
    this remains the human text path.

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
            lines.append(f"  {skipped.artifact_id} ({skipped.target_path}): matched --skip {skipped.pattern!r}")
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
        if _flag(args, "dry_run") and args.apply:
            raise UsageError(
                "--dry-run and --apply are mutually exclusive",
                remedy="pass exactly one of --dry-run (default) or --apply",
            )
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
        _print_seed_error(wrapped, verb="adopt", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, verb="adopt", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, verb="adopt", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code

    status: str
    if result.declined:
        status = "declined"
        footer = "adopt: apply declined; nothing was applied."
    elif result.applied is not None:
        status = "applied"
        if result.applied:
            footer = f"adopt: applied {len(result.applied)} artifact(s): {', '.join(result.applied)}"
        else:
            footer = "adopt: plan was empty; nothing to apply."
    else:
        status = "dry-run"
        footer = "adopt: dry-run; re-run with --apply to execute this plan."

    text = f"{_render_plan_text(result.plan)}\n{footer}"
    _emit_success(
        verb="adopt",
        as_json=_flag(args, "json"),
        quiet=_flag(args, "quiet"),
        result={
            "status": status,
            "plan": _plan_result_dict(result.plan),
            "applied": list(result.applied) if result.applied is not None else None,
            "declined": result.declined,
        },
        text=text,
    )

    return EXIT_OK


def _render_init_result_text(result: InitResult) -> str:
    """The human-readable ``marshal seed init`` report -- mirrors ``_render_
    plan_text``'s per-action listing (id, target path, rationale). Story 12.5
    adds an explicit ``--dry-run`` path (FR-124); when ``result.dry_run`` is
    set the footer names the dry-run rather than claiming apply happened."""
    lines = [f"marshal seed init -- slug {result.slug!r}:"]
    if not result.plan.actions:
        lines.append("  plan is empty; nothing to do")
    else:
        lines.append(f"  plan ({len(result.plan.actions)} action(s)):")
        for action in result.plan.actions:
            lines.append(f"    {action.artifact_id} ({action.target_path}): {action.rationale}")
        if result.dry_run or result.applied is None:
            lines.append("dry-run; re-run without --dry-run to apply this plan.")
        else:
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
    init``'s own docstring). Story 12.5 wires ``--dry-run``/``--json``/
    ``--quiet`` (FR-123/FR-124).

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
            dry_run=_flag(args, "dry_run"),
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
        _print_seed_error(wrapped, verb="init", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, verb="init", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, verb="init", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code

    _emit_success(
        verb="init",
        as_json=_flag(args, "json"),
        quiet=_flag(args, "quiet"),
        result={
            "slug": result.slug,
            "dry_run": result.dry_run,
            "plan": _plan_result_dict(result.plan),
            "applied": list(result.applied) if result.applied is not None else None,
        },
        text=_render_init_result_text(result),
    )
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
                lines.append(f"  {skipped.artifact_id} ({skipped.target_path}): matched --skip {skipped.pattern!r}")
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
        if _flag(args, "dry_run") and args.run:
            raise UsageError(
                "--dry-run and --run are mutually exclusive",
                remedy="pass exactly one of --dry-run (default) or --run",
            )
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
        _print_seed_error(wrapped, verb="update", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, verb="update", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, verb="update", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code

    status: str
    lines = [_render_update_plan_text(result.plan)]
    if result.referenced_dep_findings:
        lines.append(_render_referenced_dep_findings_text(result.referenced_dep_findings))
    if result.declined:
        status = "declined"
        lines.append("update: apply declined; nothing was applied.")
    elif result.applied is not None:
        status = "applied"
        if result.applied:
            lines.append(f"update: applied {len(result.applied)} artifact(s): {', '.join(result.applied)}")
        else:
            lines.append("update: plan was empty; nothing to apply.")
    else:
        status = "dry-run"
        lines.append("update: dry-run; re-run with --run to execute this plan.")

    _emit_success(
        verb="update",
        as_json=_flag(args, "json"),
        quiet=_flag(args, "quiet"),
        result={
            "status": status,
            "plan": _plan_result_dict(result.plan),
            "applied": list(result.applied) if result.applied is not None else None,
            "declined": result.declined,
            "referenced_dep_findings": [finding.to_json_dict() for finding in result.referenced_dep_findings],
        },
        text="\n".join(lines),
    )

    return EXIT_OK


def _render_kit_result_text(result: KitResult) -> str:
    """The human-readable ``marshal seed kit`` report: one line per item's
    ACTION (what this invocation did), then the post-state checks, then the
    findings. Actions and checks are both shown because they answer
    different questions -- "what did you just do" and "what is true now" --
    and a report that collapsed them could not distinguish an apply that
    worked from one that silently did not take."""
    header = "marshal seed kit -- applied" if result.applied else "marshal seed kit -- dry-run"
    lines = [f"{header} ({len(result.outcomes)} item(s)):"]
    # The ceiling is stated wherever a codegraph step is actually on the
    # table -- an operator reading "applied" for a step that can block for
    # minutes deserves the number, and one whose layers are all off does not
    # need the noise.
    if any(
        outcome.item_id == "codegraph-index"
        for outcome in result.outcomes
        if outcome.action in (KitAction.APPLIED, KitAction.PLANNED, KitAction.FAILED)
    ):
        lines.append(f"  note: {timeout_note()}")
    for outcome in result.outcomes:
        lines.append(f"  [{outcome.action.value}] {outcome.item_id}: {outcome.detail}")
    lines.extend(_render_kit_text(result.checks))
    if result.findings:
        lines.append(f"findings ({len(result.findings)}):")
        for finding in result.findings:
            lines.append(f"  {finding.severity.value} {finding.path}: {finding.message}")
    if not result.applied:
        lines.append("kit: dry-run; re-run with --apply to provision this kit.")
    return "\n".join(lines)


def run_kit(
    args: argparse.Namespace,
    *,
    manifest: Manifest | None = None,
    fs: FsPort | None = None,
) -> int:
    """``marshal seed kit`` (Story 28.3): thin CLI plumbing over
    ``seed.verbs.kit.run_kit`` -- Genesis's provisioning of the per-loop-home
    token-economy kit (SPEC-marshal-token-economy CAP-3/CAP-4).

    ``manifest``/``fs`` are the same keyword-only test-injection seams the
    other verbs establish; production callers supply neither.

    Always ``EXIT_OK`` on a completed run, whatever the kit's state. That is
    not laxity, it is the spec's constraint made structural: "an unavailable
    instrument disables its layer with a named finding, never blocks a run",
    and "never blocking a seed on a missing optional instrument" is one of
    this story's explicit Never bullets. A non-zero exit here would make an
    unavailable optional instrument fail a provisioning step -- exactly the
    outcome forbidden. The findings are still reported (text and ``--json``),
    and ``marshal seed check`` is where they enter a graded report."""
    try:
        if _flag(args, "dry_run") and args.apply:
            raise UsageError(
                "--dry-run and --apply are mutually exclusive",
                remedy="pass exactly one of --dry-run (default) or --apply",
            )
        repo_root = _resolve_repo_root(args.repo_root)
        if manifest is None:
            manifest = _load_packaged_manifest()
        result: KitResult = _run_kit_verb(
            repo_root,
            resolve_context_layers(repo_root, getattr(args, "project", None)),
            manifest.model_version,
            fs=fs if fs is not None else LocalFs(),
            apply=args.apply,
        )
    except ManifestError as exc:
        wrapped = InternalError(
            f"the packaged seed manifest could not be loaded: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the packaged manifest.yaml ships inside"
                " the distribution and its absence or corruption is a broken"
                " installation, not a problem with the loop home being provisioned"
            ),
        )
        _print_seed_error(wrapped, verb="kit", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, verb="kit", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, verb="kit", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code

    _emit_success(
        verb="kit",
        as_json=_flag(args, "json"),
        quiet=_flag(args, "quiet"),
        result=result.to_json_dict(),
        text=_render_kit_result_text(result),
    )
    return EXIT_OK


def run_explain(args: argparse.Namespace, *, manifest: Manifest | None = None) -> int:
    """``marshal seed explain`` (Story 11.6): thin CLI plumbing over
    ``seed.verbs.explain.run_explain`` -- read-only manifest lookup."""
    try:
        if manifest is None:
            manifest = _load_packaged_manifest()
        report = _run_explain_verb(manifest, args.artifact)
    except ManifestError as exc:
        wrapped = InternalError(
            f"the packaged seed manifest could not be loaded: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the packaged manifest.yaml ships inside"
                " the distribution and its absence or corruption is a broken"
                " installation, not a problem with the query"
            ),
        )
        _print_seed_error(wrapped, verb="explain", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, verb="explain", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, verb="explain", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code

    _emit_success(
        verb="explain",
        as_json=_flag(args, "json"),
        quiet=_flag(args, "quiet"),
        result=report.to_json_dict(),
        text=render_explain_text(report),
    )
    return EXIT_OK


def run_version(args: argparse.Namespace, *, manifest: Manifest | None = None) -> int:
    """``marshal seed version`` (Story 11.6): thin CLI plumbing over
    ``seed.verbs.version.run_version`` -- read-only version reporting."""
    try:
        repo_root = _resolve_repo_root(args.repo_root)
        if manifest is None:
            manifest = _load_packaged_manifest()
        report = _run_version_verb(manifest, repo_root)
    except ManifestError as exc:
        wrapped = InternalError(
            f"the packaged seed manifest could not be loaded: {exc}",
            remedy=(
                "reinstall pyforge-marshal -- the packaged manifest.yaml ships inside"
                " the distribution and its absence or corruption is a broken"
                " installation"
            ),
        )
        _print_seed_error(wrapped, verb="version", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code
    except SeedError as exc:
        _print_seed_error(exc, verb="version", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 -- the CLI backstop; see run_check's docstring.
        wrapped = InternalError(
            f"an unanticipated internal failure occurred: {exc}",
            remedy=(
                "this is unexpected -- please file a bug report against"
                " pyforge-marshal with the full command and output"
            ),
        )
        _print_seed_error(wrapped, verb="version", as_json=_flag(args, "json"), quiet=_flag(args, "quiet"))
        return wrapped.exit_code

    _emit_success(
        verb="version",
        as_json=_flag(args, "json"),
        quiet=_flag(args, "quiet"),
        result=report.to_json_dict(),
        text=render_version_text(report),
    )
    return EXIT_OK


def add_seed_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``seed`` subcommand on ``main.py``'s subparser tree, with
    seven nested verb actions -- mirrors ``cli/gate.py::add_gate_subparser``'s
    identical nested-subparsers shape, one level down (seven verbs instead of
    one ``evaluate`` action). Story 12.5 wires ``--json``/``--quiet`` on every
    verb and ``--dry-run`` on the mutating ones (FR-123/FR-124); Story 28.3
    adds the seventh verb, ``kit``, plus ``--project`` on ``check``/``kit``
    (the two verbs that read a ``[context]`` declaration)."""
    parser = subparsers.add_parser(
        "seed",
        help="Scaffold/adopt/check/update a project from Marshal's seed templates (AD-70).",
        description=(
            "The seed-installer noun group. `check` (Story 10.5), `adopt` "
            "(Story 10.6), `init` (Story 10.7), `update` (Story 11.4), `explain`, and"
            " `version` (Story 11.6) are real, as is `kit` (Story 28.3, the"
            " per-loop-home token-economy kit)."
        ),
    )
    seed_subparsers = parser.add_subparsers(dest="seed_command", required=True)

    init_parser = seed_subparsers.add_parser(
        "init",
        help="Scaffold a brand-new project from Marshal's seed templates.",
        description=(
            "Story 10.7: bootstrap (mkdir + git init if needed) -> detect -> plan ->"
            " preconditions -> apply DIRECTLY by default; --dry-run computes the plan"
            " without applying (FR-124). FR-78's non-empty-directory refusal is this"
            " verb's own safety gate."
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
    _add_dry_run_flag(init_parser)
    _add_json_quiet_flags(init_parser)
    init_parser.set_defaults(handler=run_init)

    adopt_parser = seed_subparsers.add_parser(
        "adopt",
        help="Adopt an existing project onto Marshal's seed templates.",
        description=(
            "Story 10.6: detect -> plan -> confirm -> apply -> state-write. Dry-run"
            " by default -- writes only .marshal/plan.json and prints it; --apply"
            " executes the plan (prompting for confirmation unless --yes is given)."
            " --dry-run is accepted explicitly (FR-124)."
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
    _add_dry_run_flag(adopt_parser)
    _add_json_quiet_flags(adopt_parser)
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
    _add_project_flag(check_parser)
    _add_json_quiet_flags(check_parser)
    check_parser.set_defaults(handler=run_check)

    kit_parser = seed_subparsers.add_parser(
        "kit",
        help="Provision the per-loop-home token-economy kit (Story 28.3).",
        description=(
            "Story 28.3 (SPEC-marshal-token-economy CAP-3/CAP-4): deploy the caveman"
            " skill with Genesis's articulate carve-out, create the loop-home-scoped"
            " CCR store directory, and build or resync the codegraph index -- each"
            " gated by its own `[context]` layer. Dry-run by default; --apply"
            " provisions. An unavailable instrument skips its layer with a named"
            f" finding and never fails the run. Cost: {timeout_note()}."
        ),
    )
    kit_parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=None,
        metavar="PATH",
        help="The loop home to provision (default: the current working directory).",
    )
    kit_parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute the plan (default: dry-run -- compute and print it only).",
    )
    _add_project_flag(kit_parser)
    _add_dry_run_flag(kit_parser)
    _add_json_quiet_flags(kit_parser)
    kit_parser.set_defaults(handler=run_kit)

    update_parser = seed_subparsers.add_parser(
        "update",
        help="Apply pending seed-template updates to a project.",
        description=(
            "Story 11.4: detect -> plan (migrations + absent entries + wholesale"
            " regenerate, merged) -> confirm -> apply -> state-write. Dry-run by"
            " default -- writes only .marshal/plan.json and prints it; --run executes"
            " the plan (prompting for confirmation unless --yes is given)."
            " --dry-run is accepted explicitly (FR-124)."
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
    _add_dry_run_flag(update_parser)
    _add_json_quiet_flags(update_parser)
    update_parser.set_defaults(handler=run_update)

    explain_parser = seed_subparsers.add_parser(
        "explain",
        help="Explain a manifest artifact's class, rationale, and update behavior.",
        description=(
            "Story 11.6: read-only lookup by artifact id or repo path; hybrid entries include region names and anchors."
        ),
    )
    explain_parser.add_argument(
        "artifact",
        metavar="ARTIFACT",
        help="Manifest artifact id or repo-relative path (e.g. agents-md or AGENTS.md).",
    )
    _add_json_quiet_flags(explain_parser)
    explain_parser.set_defaults(handler=run_explain)

    version_parser = seed_subparsers.add_parser(
        "version",
        help="Report CLI, bundled model, and adopted repo model versions.",
        description=(
            "Story 11.6: read-only version report (FR-125) -- CLI semver, bundled"
            " manifest model_version, and adopted repo model_version when present."
        ),
    )
    version_parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=None,
        metavar="PATH",
        help="Repo whose adopted model version to read (default: cwd).",
    )
    _add_json_quiet_flags(version_parser)
    version_parser.set_defaults(handler=run_version)
