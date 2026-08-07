"""``marshal land`` (Story 4.8, FR-60/AD-40) -- takes one project's wave from
"gates passed" to "merged, branch retired, feed resynced" with no human in
the sequencing loop. A NEW top-level subcommand (``marshal land <slug>``,
sibling to ``deploy``/``gate``/``init`` -- NOT nested under ``deploy``,
per the story's own Code Map).

**Three already-shipped primitives, reused, never reimplemented, plus ONE
new one.** Wave discovery, the hygiene preflight, and PR open/update+labels
are the SAME sequence ``cli/deploy.py::run_batch_pr`` already performs,
calling the SAME private helpers that function itself calls
(``_evaluate_hygiene``/``_gather_gate_verdicts``/``_batch_pr_title``/
``_batch_pr_body``/``_batch_pr_redact``/``_DeployRun``/``_deploy_writer_id``/
``_reconcile_open_intents``) -- ``run_land`` never calls ``run_batch_pr``
itself (that function ends by building AND PRINTING its own envelope; a
second in-process call would either print a spurious second envelope or
need a "don't print" flag threaded through ``_emit`` no other caller needs
-- see the story's own Design Notes). Resync reuses ``cli/deploy.py::
reconcile_feed`` -- the non-printing core code review carved out of
``run_refresh_feed`` for exactly this reuse (the SAME "value-returning core,
plus a thin emit-and-print wrapper" split ``cli/gate.py``'s own
``evaluate_gate``/``run_evaluate`` already established) -- rather than
``run_refresh_feed`` itself, which would print a second envelope after
``land``'s own for the identical reason ``run_batch_pr`` is never called
directly. The ONE new primitive is
``ForgePort.merge_pr`` (Story 4.8): merge and branch retirement fold into a
SINGLE ``gh pr merge --delete-branch`` call, atomically, rather than two
racing round-trips.

**Required-check satisfaction is a SEPARATE, NEW poll from the hygiene
preflight's own required_check gate.** ``_evaluate_hygiene`` (reused
verbatim for the PR-open/update gate, exactly as ``batch-pr`` already uses
it) treats ANY non-``"success"`` conclusion -- including a check that has
not concluded yet -- as an identical, ERROR-tier block. That is the right
shape for "should this PR even open" but the wrong shape for "should this
ALREADY-OPEN PR be merged": a still-pending check is not a failure, and
refusing to merge over one must stay re-entrant (re-run once it concludes),
never escalate to the same tier as a genuine red check. This module's own
``_evaluate_required_checks`` re-polls the SAME ``landing_rules`` against
the SAME pinned ``head_sha`` for exactly that purpose, one poll per
invocation (AD-22: this package's own detached-execution default -- a
``time.sleep`` wait loop would be the first blocking CLI handler in this
codebase, and needs a ``ClockPort`` primitive this story's Code Map does not
authorize).

**Unacknowledged WARN-tier findings block the merge**, reusing
``cli/init.py``'s already-shipped acknowledgement store (Story 1.7,
``_ack_state_path``/``_read_acknowledged``) rather than inventing a second
mechanism -- an operator acks once via ``marshal preflight --acknowledge
<key>``; every subsequent unattended ``marshal land`` run honors it. This
module never WRITES to that store (acknowledging stays ``marshal
preflight``'s own action). The acknowledgement key is
``_required_check_ack_key(rule_name, required_check, slug)`` -- SCOPED per
rule/check/project, carried on the Finding's own ``path`` field, never the
bare ``MRS-LAND-005`` finding code (code review, 2026-08-06, both reviewers
independently, the single most severe finding against this story: the
ORIGINAL version checked the bare code, so one acknowledgement
permanently disabled the pending-check gate for every project/rule/check,
forever).

Every import of ``cli/deploy.py``'s/``cli/init.py``'s private helpers is
LOCAL, inside ``run_land`` -- never module-level. ``cli/init.py`` imports
``cli/deploy.py`` (``from . import deploy``), so a module-level import of
either from here would risk a load-order-fragile cycle the moment either of
those modules ever imports ``cli/land.py`` back (mirrors
``run_land_story``'s/``run_batch_pr``'s own identical, already-documented
convention in ``cli/deploy.py``)."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from ..adapters.forge_gh import GhForge
from ..adapters.fs_local import LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness
from ..adapters.process_posix import PosixProcess
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import policy, promotion
from ..core.journal import Phase
from ..core.landing import rule_applies
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.forge import ForgeCommandError, ForgePort, ForgeRef
from ..ports.fs import FsPort
from ..ports.vcs import VcsPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    repo_root,
)

if TYPE_CHECKING:
    # Story 5.6 (FR-65/AD-50): `run_land`'s `context` parameter below is
    # type-only -- this module's own internal logic is NOT retrofitted to
    # CONSUME it in this pass (see cli/main.py's own module docstring and
    # the spec's Design Notes); a real (non-TYPE_CHECKING) import would add
    # a runtime dependency this module doesn't otherwise need.
    from ..core.context import MarshalContext

# The same physical-repo constant ``cli/deploy.py::_FORGE_REPO`` already
# establishes -- every Marshal station lives inside this one repo, so this
# module names the SAME fact rather than importing deploy's private copy
# (a plain constant, not a helper this story's Code Map lists for reuse).
_FORGE_REPO = "rxm7706/local-recipes"
_MERGE_BASE_BRANCH_FALLBACK = "main"

_MRS_LAND_001 = "MRS-LAND-001"
_MRS_LAND_002 = "MRS-LAND-002"
_MRS_LAND_003 = "MRS-LAND-003"
_MRS_LAND_004 = "MRS-LAND-004"
_MRS_LAND_005 = "MRS-LAND-005"
_MRS_LAND_006 = "MRS-LAND-006"
_MRS_LAND_007 = "MRS-LAND-007"

# This module's own journal kinds (AD-28: distinct writer namespaces, never
# conflated with `cli/deploy.py`'s `_LAND_MERGE_KIND`/`_BATCH_PR_WRITE_KIND`
# -- the story's own literal wording). The PR-open/update intent/outcome
# pair below reuses `_BATCH_PR_WRITE_KIND` itself (imported from deploy.py),
# not a fourth kind here: it is the SAME underlying create_pr/update_pr
# action `batch-pr` already tracks, and a crashed `batch-pr` run's open
# intent should reconcile against a subsequent `land` run's evidence (and
# vice versa) rather than living in two unrelated namespaces for the
# identical action.
_LAND_MERGE_PR_KIND = "land-merge-pr"
_LAND_OBSERVATION_KIND = "land-observation"


def add_land_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``land`` subcommand on ``main.py``'s subparser tree --
    a NEW top-level command, sibling to ``deploy``/``gate``/``init``, not
    nested under ``deploy`` (the story's own Code Map is explicit)."""
    parser = subparsers.add_parser(
        "land",
        help="Merge a wave's landed stories and retire its branch, under required checks (FR-60).",
        description=(
            "Discovers <slug>'s wave of durable story keys, opens/updates "
            "its batch PR under the hygiene preflight (reusing 'deploy "
            "batch-pr''s own machinery), polls every fired required_check "
            "landing rule exactly once, refuses on a red check or an "
            "unacknowledged advisory finding, and otherwise merges the PR "
            "-- retiring its branch and resyncing the feed in the same "
            "run -- with no human in the sequencing loop."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_land)


def _required_check_ack_key(rule_name: str, required_check: str, slug: str) -> str:
    """The acknowledgement key a still-pending required check must appear
    under in ``cli/init.py``'s shared ack store before ``land`` will merge
    over it. Code review (2026-08-06, both reviewers independently, the
    single most severe finding against this story): the ORIGINAL version
    checked the bare ``MRS-LAND-005`` finding CODE against the ack set --
    since that code never varies by rule/check/project, a single
    ``marshal preflight --acknowledge MRS-LAND-005`` permanently disabled
    the pending-check merge gate for EVERY project, rule, and check,
    forever, directly contradicting this module's own "re-entrant, never
    silently treated as passing" design. Scoped to ``slug``/``rule_name``/
    ``required_check`` so one acknowledgement only ever bypasses the ONE
    still-pending check it names."""
    return f"{_MRS_LAND_005}:{slug}:{rule_name}:{required_check}"


def _evaluate_required_checks(
    landing_rules: tuple,
    changed_paths: tuple[str, ...],
    forge: ForgePort,
    repo_ref: ForgeRef,
    head_sha: str,
    slug: str,
) -> tuple[list[dict[str, object]], list[Finding], list[Finding], tuple[str, ...]]:
    """Story 4.8's OWN required-check poll (see this module's own docstring
    for why it is a SEPARATE evaluation from ``_evaluate_hygiene``'s
    already-shipped one): one ``ForgePort.check_run_status`` call per fired
    ``required_check`` rule, never a wait loop. Evaluated over ALL of
    ``landing_rules`` carrying a ``required_check`` (code review, 2026-08-06,
    both reviewers independently: a rule declaring BOTH ``label`` and
    ``required_check`` -- ``core.landing.LandingRule`` explicitly permits
    this -- previously never reached this function at all when it was
    called only over the required-check subset for GATING and separately
    excluded from ``_evaluate_hygiene``'s label-only subset, so its label
    silently never fired even after the check passed; this function now
    ALSO returns ``fired_labels`` for exactly this case, folded into the
    caller's label set alongside ``_evaluate_hygiene``'s own).

    Returns ``(report, error_findings, warn_findings, fired_labels)`` --
    ``"success"`` is satisfied, produces no finding, and fires the rule's
    own ``label`` (if any); a real, non-``"success"`` conclusion (or a
    ``ForgeCommandError``, treated identically: this run could not
    positively confirm success either way) is ``MRS-LAND-004``
    (``Verdict.GATE_FAILED``); ``None`` (not yet concluded) is
    ``MRS-LAND-005`` (``Verdict.WARN``, re-entrant -- AD-8's "an
    unevaluable/pending signal is NOT-YET-SAFE-TO-ACT, never silently
    treated as passing"), scoped via ``Finding.path`` to
    ``_required_check_ack_key`` so an acknowledgement is
    rule/check/project-specific. A wave with zero applicable
    ``required_check`` rules makes zero ``check_run_status`` calls (Task
    4's own AC)."""
    report: list[dict[str, object]] = []
    error_findings: list[Finding] = []
    warn_findings: list[Finding] = []
    fired_labels: list[str] = []
    for rule in landing_rules:
        if rule.required_check is None or not rule_applies(rule, changed_paths):
            continue
        try:
            status = forge.check_run_status(
                repo_ref, ForgeRef(head_sha), ForgeRef(rule.required_check)
            )
        except ForgeCommandError as exc:
            report.append(
                {"rule": rule.name, "required_check": rule.required_check, "status": None}
            )
            error_findings.append(
                Finding(
                    code=_MRS_LAND_004,
                    severity=Severity.ERROR,
                    message=(
                        f"cannot evaluate required_check {rule.required_check!r} "
                        f"(rule {rule.name!r}) on {head_sha!r} -- refusing to "
                        f"merge: {exc}"
                    ),
                )
            )
            continue
        report.append(
            {"rule": rule.name, "required_check": rule.required_check, "status": status}
        )
        if status == "success":
            if rule.label is not None:
                fired_labels.append(rule.label)
            continue
        if status is None:
            warn_findings.append(
                Finding(
                    code=_MRS_LAND_005,
                    severity=Severity.WARN,
                    message=(
                        f"required check {rule.required_check!r} (rule "
                        f"{rule.name!r}) has not yet concluded on {head_sha!r} "
                        "-- re-run 'marshal land' once it has, or "
                        "acknowledge "
                        f"{_required_check_ack_key(rule.name, rule.required_check, slug)!r} "
                        "via 'marshal preflight --acknowledge' to merge "
                        "anyway"
                    ),
                    path=_required_check_ack_key(rule.name, rule.required_check, slug),
                )
            )
        else:
            error_findings.append(
                Finding(
                    code=_MRS_LAND_004,
                    severity=Severity.ERROR,
                    message=(
                        f"required check {rule.required_check!r} (rule "
                        f"{rule.name!r}) is {status!r} (not 'success') on "
                        f"{head_sha!r} -- refusing to merge"
                    ),
                )
            )
    return report, error_findings, warn_findings, tuple(fired_labels)


def run_land(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
    forge: ForgePort | None = None,
    context: MarshalContext | None = None,
) -> int:
    # Story 5.6 (FR-65/AD-50): `context`, if `cli/main.py`'s dispatch
    # resolved one, is accepted but deliberately UNUSED here -- proving the
    # "resolved once at the front door" plumbing reaches this handler
    # without retrofitting its own internal policy/home-path derivation
    # (see this story's own Design Notes; `cli/main.py`'s module docstring
    # names the exact three already-shipped commands this applies to).
    del context
    # Local imports -- see this module's own docstring for why cli/deploy.py
    # and cli/init.py are never imported at module level here.
    from .deploy import (
        _BATCH_PR_WRITE_KIND,
        _DeployRun,
        _batch_pr_body,
        _batch_pr_redact,
        _batch_pr_title,
        _deploy_writer_id,
        _evaluate_hygiene,
        _gather_gate_verdicts,
        _land_redact_text,
        _reconcile_open_intents,
        reconcile_feed,
    )
    from .init import _ack_state_path, _home_path, _read_acknowledged

    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()
    forge = forge if forge is not None else GhForge()

    slug = args.slug
    findings: list[Finding] = []
    data: dict[str, object] = {
        "slug": slug,
        "opened": False,
        "updated": False,
        "merged": False,
    }

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-POLICY-006",
                severity=Severity.ERROR,
                message=(
                    f"malformed project slug {slug!r} -- must be one safe "
                    "path segment (letters, digits, '.', '_', '-'; not '.' "
                    "or '..'; at most 255 characters)"
                ),
            )
        )
        return _emit(args, data, findings)

    root = repo_root()
    home = _home_path(slug)
    head_branch = f"loop/{slug}"
    data["branch"] = head_branch

    try:
        git_repo_root = vcs.repo_common_root(home)
        branch_ok = vcs.branch_exists(git_repo_root, head_branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_LAND_001,
                severity=Severity.ERROR,
                message=(
                    f"cannot resolve the loop-home station branch "
                    f"{head_branch!r} for {slug!r}'s landing: {exc}"
                ),
            )
        )
        return _emit(args, data, findings)
    if not branch_ok:
        findings.append(
            Finding(
                code=_MRS_LAND_001,
                severity=Severity.ERROR,
                message=f"{head_branch!r} does not exist -- nothing to land for {slug!r}",
            )
        )
        return _emit(args, data, findings)

    project_data: Mapping[str, object] = {}
    if policy._is_valid_project_slug(slug):
        candidate = conventional_project_policy_path(slug)
        try:
            present = candidate.is_file()
        except OSError:
            present = True
        if present:
            try:
                project_data = _read_project_policy(candidate)
            except PolicyIOError as exc:
                findings.append(exc.finding)
                return _emit(args, data, findings)
    effective, policy_findings = policy.compose(project_slug=slug, project=project_data, flags={})
    findings.extend(policy_findings)

    # The malformed-landing_rules-hard-refuses precondition -- copied
    # verbatim from `batch-pr`'s own P1 review fix (`cli/deploy.py::
    # run_batch_pr`): `core/policy.py::compose` never raises, so a
    # malformed `landing_rules` layer degrades to an EMPTY rule set unless
    # refused here, before that empty set is ever trusted.
    if any(
        finding.severity is Severity.ERROR and "'landing_rules'" in finding.message
        for finding in policy_findings
    ):
        findings.append(
            Finding(
                code=_MRS_LAND_002,
                severity=Severity.ERROR,
                message=(
                    f"refusing to land {head_branch!r}: policy composition "
                    "reported a malformed 'landing_rules' layer above -- "
                    "proceeding would silently evaluate against an EMPTY "
                    "rule set instead of the project's declared rules; fix "
                    "the malformed layer and re-run land"
                ),
            )
        )
        return _emit(args, data, findings)

    base = effective.landing_base_branch.value
    template = effective.merge_subject_template.value
    landing_rules = effective.landing_rules.value
    merge_strategy = effective.landing_merge_strategy.value
    delete_branch = effective.landing_branch_retirement.value
    resync_enabled = effective.landing_resync.value
    data["base"] = base

    # --- wave discovery (byte-for-byte batch-pr's own sequence) ---------
    try:
        merge_base_sha = vcs.merge_base(git_repo_root, head_branch, base)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DEPLOY-007",
                severity=Severity.ERROR,
                message=(
                    f"cannot compute the merge base of {head_branch!r} and "
                    f"{base!r}: {exc}"
                ),
            )
        )
        return _emit(args, data, findings)
    try:
        wave_subjects = vcs.commit_subjects(git_repo_root, f"{merge_base_sha}..{head_branch}")
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DEPLOY-007",
                severity=Severity.ERROR,
                message=(
                    f"cannot enumerate commits between {merge_base_sha!r} and "
                    f"{head_branch!r}: {exc}"
                ),
            )
        )
        return _emit(args, data, findings)
    wave_keys = sorted(promotion.merged_story_keys(wave_subjects, template, slug))
    data["wave"] = [str(key) for key in wave_keys]

    if not wave_keys:
        # Clean no-op -- nothing merged since the last landing.
        return _emit(args, data, findings)

    try:
        base_subjects = vcs.commit_subjects(git_repo_root, base)
    except VcsCommandError:
        base_subjects = ()
    already_landed_keys = promotion.merged_story_keys(base_subjects, template, slug)

    deploy_run = _DeployRun(fs, root, slug, _deploy_writer_id("land"))
    _reconcile_open_intents(
        fs,
        root,
        slug,
        kind=_LAND_MERGE_PR_KIND,
        confirmed_story_keys=already_landed_keys,
        evidence_note=f"story key now reachable in {base!r}'s own commit history",
        deploy_run=deploy_run,
        findings=findings,
    )

    if wave_keys and all(key in already_landed_keys for key in wave_keys):
        # This wave already landed -- reused BATCH-PR's own already-landed
        # shortcut (never a fresh create_pr/update_pr). This run's only job
        # is confirming/retiring the branch and resyncing (the story's own
        # Always bullet).
        data["already_landed"] = True
        data["merged"] = True
        repo_ref = ForgeRef(_FORGE_REPO)
        try:
            existing = forge.find_open_pr(repo_ref, ForgeRef(head_branch))
        except ForgeCommandError as exc:
            findings.append(
                Finding(
                    code="MRS-DEPLOY-014",
                    severity=Severity.ERROR,
                    message=f"cannot look up an existing PR for {head_branch!r}: {exc}",
                )
            )
            data["branch_retired"] = None
        else:
            if existing is not None:
                # The forge still shows an open PR for this head branch --
                # ForgePort has no standalone "delete this branch"
                # primitive (deliberately, see this story's own Design
                # Notes), so this run has no remaining forge-side action to
                # retire it through.
                findings.append(
                    Finding(
                        code=_MRS_LAND_003,
                        severity=Severity.WARN,
                        message=(
                            f"{head_branch!r}'s wave is already reachable in "
                            f"{base!r}, but PR #{existing.number} is still "
                            "open on the forge -- branch retirement could not "
                            "be confirmed or re-driven through ForgePort"
                        ),
                    )
                )
                data["branch_retired"] = None
            else:
                data["branch_retired"] = True
        data["resynced"] = _run_resync_if_enabled(
            reconcile_feed, args, vcs, fs, resync_enabled, slug, findings
        )
        return _emit(args, data, findings)

    # --- PR open/update+labels (byte-for-byte batch-pr's own sequence) --
    try:
        head_sha = vcs.resolve_ref(git_repo_root, head_branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DEPLOY-007",
                severity=Severity.ERROR,
                message=f"cannot resolve {head_branch!r}'s own tip: {exc}",
            )
        )
        return _emit(args, data, findings)

    try:
        home_head_sha = vcs.worktree_head_sha(home)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DEPLOY-017",
                severity=Severity.ERROR,
                message=(
                    f"cannot confirm {home}'s own checked-out commit before "
                    f"gathering changed files for {head_branch!r}: {exc}"
                ),
            )
        )
        return _emit(args, data, findings)
    if home_head_sha != head_sha:
        findings.append(
            Finding(
                code="MRS-DEPLOY-017",
                severity=Severity.ERROR,
                message=(
                    f"{home}'s checked-out commit ({home_head_sha!r}) does not "
                    f"match {head_branch!r}'s resolved tip ({head_sha!r}) -- "
                    "refusing to trust changed_files against a possibly stale "
                    f"or detached worktree; re-sync {home} and re-run land"
                ),
            )
        )
        return _emit(args, data, findings)

    try:
        changed_paths = vcs.changed_files(git_repo_root, home, base=base)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DEPLOY-007",
                severity=Severity.ERROR,
                message=f"cannot gather {head_branch!r}'s changed files against {base!r}: {exc}",
            )
        )
        return _emit(args, data, findings)

    repo_ref = ForgeRef(_FORGE_REPO)
    head_branch_ref = ForgeRef(head_branch)

    # `_evaluate_hygiene` is reused VERBATIM for the PR-open/update gate
    # (the story's own Always bullet), but only over the LABEL-only rules
    # (`required_check is None`) -- a rule that ALSO carries a
    # `required_check` is evaluated EXCLUSIVELY by this module's own
    # `_evaluate_required_checks` below, never by both. `_evaluate_hygiene`
    # treats a check that has merely not concluded yet identically to a
    # real failure (an ERROR-tier block, unconditionally) -- reusing it
    # unfiltered for `land` would make this module's own idempotent,
    # re-entrant "pending -> WARN, re-run later" merge gate (this story's
    # whole reason to exist, per its own Design Notes) permanently
    # unreachable for any rule that also feeds hygiene: hygiene would
    # always refuse first, before the PR that step 2 gates even exists.
    label_only_rules = tuple(rule for rule in landing_rules if rule.required_check is None)
    hygiene_report, blocking_findings, hygiene_fired_labels = _evaluate_hygiene(
        label_only_rules, changed_paths, forge, repo_ref, head_sha
    )
    data["hygiene_rules"] = hygiene_report
    if blocking_findings:
        findings.extend(blocking_findings)
        return _emit(args, data, findings)

    # --- required-check satisfaction: evaluated HERE (one poll, before the
    # PR write) rather than after it -- `check_run_status` needs only
    # `head_sha`, not the PR's existence, and computing it now (rather than
    # after labels are applied) lets a rule carrying BOTH `label` AND
    # `required_check` still fire its label below, folded into the SAME
    # `add_labels` call `_evaluate_hygiene`'s own labels go through (code
    # review, 2026-08-06, both reviewers independently: a combined rule's
    # label previously never fired at all under `land`, since it was
    # excluded from `label_only_rules` above and the required-check path
    # never collected labels). The gate below (after the PR write) reuses
    # these SAME results -- never a second poll.
    (
        required_report,
        required_errors,
        required_warnings,
        required_fired_labels,
    ) = _evaluate_required_checks(landing_rules, changed_paths, forge, repo_ref, head_sha, slug)
    data["required_checks"] = required_report
    fired_labels = hygiene_fired_labels + required_fired_labels

    gate_verdicts = _gather_gate_verdicts(fs, root, slug)
    title_redacted = _batch_pr_redact(_batch_pr_title(slug, wave_keys))
    body_redacted = _batch_pr_redact(_batch_pr_body(wave_keys, gate_verdicts))
    if title_redacted is None or body_redacted is None:
        findings.append(
            Finding(
                code="MRS-DEPLOY-014",
                severity=Severity.ERROR,
                message="cannot redact the PR title/body -- refusing to write unredacted text through ForgePort",
            )
        )
        return _emit(args, data, findings)

    try:
        existing = forge.find_open_pr(repo_ref, head_branch_ref)
    except ForgeCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DEPLOY-014",
                severity=Severity.ERROR,
                message=f"cannot look up an existing PR for {head_branch!r}: {exc}",
            )
        )
        return _emit(args, data, findings)

    if existing is not None and existing.base != base:
        findings.append(
            Finding(
                code="MRS-DEPLOY-018",
                severity=Severity.ERROR,
                message=(
                    f"an open PR #{existing.number} already exists for "
                    f"{head_branch!r}, but targets base {existing.base!r}, "
                    f"not the policy-declared {base!r} -- refusing to update "
                    "a PR that may belong to an unrelated intent"
                ),
            )
        )
        return _emit(args, data, findings)

    _reconcile_open_intents(
        fs,
        root,
        slug,
        kind=_BATCH_PR_WRITE_KIND,
        confirmed_story_keys=set(),
        evidence_note="find_open_pr now shows a PR reflecting this content",
        deploy_run=deploy_run,
        findings=findings,
    )

    try:
        head_sha_now = vcs.resolve_ref(git_repo_root, head_branch)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DEPLOY-016",
                severity=Severity.ERROR,
                message=f"cannot reconfirm {head_branch!r}'s own tip immediately before the PR write: {exc}",
            )
        )
        return _emit(args, data, findings)
    if head_sha_now != head_sha:
        findings.append(
            Finding(
                code="MRS-DEPLOY-016",
                severity=Severity.ERROR,
                message=(
                    f"{head_branch!r} moved (from {head_sha!r} to "
                    f"{head_sha_now!r}) during hygiene evaluation -- refusing "
                    "to open/update a PR for content the hygiene preflight "
                    "never vetted; re-run land"
                ),
            )
        )
        return _emit(args, data, findings)

    pr_action = "create_pr" if existing is None else "update_pr"
    pr_intent_id = deploy_run.write(
        findings,
        kind=_BATCH_PR_WRITE_KIND,
        phase=Phase.INTENT,
        payload={"action": pr_action, "story_keys": [str(key) for key in wave_keys]},
    )
    try:
        if existing is None:
            pr = forge.create_pr(repo_ref, ForgeRef(base), head_branch_ref, title_redacted, body_redacted)
            data["opened"] = True
        else:
            pr = forge.update_pr(repo_ref, existing.number, title_redacted, body_redacted)
            data["updated"] = True
    except ForgeCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DEPLOY-014",
                severity=Severity.ERROR,
                message=f"cannot open/update the PR for {head_branch!r}: {exc}",
            )
        )
        return _emit(args, data, findings)

    data["pr_number"] = pr.number
    data["pr_url"] = pr.url
    if pr_intent_id is not None:
        deploy_run.write(
            findings,
            kind=_BATCH_PR_WRITE_KIND,
            phase=Phase.OUTCOME,
            payload={
                "action": pr_action,
                "story_keys": [str(key) for key in wave_keys],
                "pr_number": pr.number,
            },
            intent_id=pr_intent_id,
        )

    deduped_labels = tuple(sorted(set(fired_labels)))
    data["labels_applied"] = []
    if deduped_labels:
        try:
            forge.add_labels(repo_ref, pr.number, deduped_labels)
        except ForgeCommandError as exc:
            findings.append(
                Finding(
                    code="MRS-DEPLOY-014",
                    severity=Severity.ERROR,
                    message=(
                        f"PR #{pr.number} opened/updated, but applying "
                        f"label(s) {list(deduped_labels)} failed: {exc}"
                    ),
                )
            )
        else:
            data["labels_applied"] = list(deduped_labels)

    # --- required-check merge gate: reuses the results `_evaluate_
    # required_checks` already computed above (one poll per invocation --
    # never re-polled here). Every warning is always folded into `findings`
    # (code review, 2026-08-06, Edge Case Hunter: the original version only
    # did this inside the `if required_warnings and not required_errors`-
    # shaped branch below, so a WARN for one still-pending rule was
    # silently dropped whenever an UNRELATED rule's check had already
    # failed) -- independent of whether an unrelated rule's check also
    # failed outright.
    findings.extend(required_warnings)
    if required_errors:
        findings.extend(required_errors)
        return _emit(args, data, findings)

    # --- acknowledgement gate (reuses cli/init.py's shared store) -------
    # Each WARN's own `path` carries its `_required_check_ack_key` scope
    # (rule/check/project-specific -- see that function's own docstring for
    # why the bare finding CODE alone must never be the ack key).
    if required_warnings:
        ack_path = _ack_state_path()
        acknowledged = _read_acknowledged(fs, ack_path)
        blocked = False
        for warn_finding in required_warnings:
            if warn_finding.path not in acknowledged:
                blocked = True
                findings.append(
                    Finding(
                        code=_MRS_LAND_006,
                        severity=Severity.ERROR,
                        message=(
                            f"required-check finding {warn_finding.path!r} "
                            "from this run's own evaluation is not "
                            "acknowledged -- acknowledge it via 'marshal "
                            f"preflight --acknowledge {warn_finding.path}' "
                            "or wait for the check to conclude; refusing to "
                            "merge"
                        ),
                    )
                )
        if blocked:
            return _emit(args, data, findings)

    # --- merge + retire (one ForgePort call), journaled intent-before/ ---
    # outcome-after (AD-6). `expected_head_sha=head_sha` (code review,
    # 2026-08-06, both reviewers independently, the single most severe
    # finding against this story): `head_sha` is the SAME commit
    # `head_sha_now != head_sha` above already reconfirmed immediately
    # before the PR write, and the one this run's required-check poll
    # actually evaluated -- `merge_pr`'s own `--match-head-commit` refuses
    # atomically, forge-side, if a commit lands on the branch anywhere
    # between that poll and this call, closing the exact TOCTOU window a
    # bare PR-number merge would leave open.
    merge_intent_id = deploy_run.write(
        findings,
        kind=_LAND_MERGE_PR_KIND,
        phase=Phase.INTENT,
        payload={
            "action": "merge_pr",
            "story_keys": [str(key) for key in wave_keys],
            "pr_number": pr.number,
            "strategy": merge_strategy,
            "expected_head_sha": head_sha,
            "delete_branch": delete_branch,
        },
    )
    try:
        forge.merge_pr(
            repo_ref,
            pr.number,
            ForgeRef(merge_strategy),
            expected_head_sha=ForgeRef(head_sha),
            delete_branch=delete_branch,
        )
    except ForgeCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_LAND_007,
                severity=Severity.ERROR,
                message=f"merge of PR #{pr.number} failed: {exc}",
            )
        )
        return _emit(args, data, findings)

    data["merged"] = True
    data["branch_retired"] = delete_branch
    if merge_intent_id is not None:
        deploy_run.write(
            findings,
            kind=_LAND_MERGE_PR_KIND,
            phase=Phase.OUTCOME,
            payload={
                "action": "merge_pr",
                "story_keys": [str(key) for key in wave_keys],
                "pr_number": pr.number,
                "strategy": merge_strategy,
                "delete_branch": delete_branch,
            },
            intent_id=merge_intent_id,
        )

    # One journal OBSERVATION entry recording checks required/passed, what
    # merged, and under whose authority (the story's own Always bullet) --
    # redacted at capture via `_land_redact_text`, reused rather than
    # reimplemented (AD-34).
    required_summary = _land_redact_text(
        json.dumps([entry["required_check"] for entry in required_report])
    )
    deploy_run.write(
        findings,
        kind=_LAND_OBSERVATION_KIND,
        phase=Phase.OBSERVATION,
        payload={
            "story_keys": [str(key) for key in wave_keys],
            "pr_number": pr.number,
            "checks_required": required_summary,
            "checks_passed": True,
            "merge_strategy": merge_strategy,
            "branch_retired": delete_branch,
            "authority": "marshal land (automated)",
        },
    )

    data["resynced"] = _run_resync_if_enabled(
        reconcile_feed, args, vcs, fs, resync_enabled, slug, findings
    )

    return _emit(args, data, findings)


def _run_resync_if_enabled(
    reconcile_feed, args, vcs, fs, resync_enabled: bool, slug: str, findings: list[Finding]
) -> bool:
    """Gated by ``landing_resync`` (Story 4.7): calls ``cli/deploy.py::
    reconcile_feed`` in-process (the non-printing core ``run_refresh_feed``
    itself calls, before its own ``_emit`` -- see this module's own
    docstring for why ``land`` reuses the core rather than the printing
    wrapper) -- ``False`` skips it entirely, reporting
    ``data["resynced"]: false`` with no finding, per the story's own Always
    bullet. Any findings the reconciliation itself surfaces are folded into
    THIS run's own ``findings`` list -- never silently dropped, and never
    printed as a second envelope."""
    if not resync_enabled:
        return False
    refresh_args = argparse.Namespace(project=slug, format=args.format)
    _resync_data, resync_findings = reconcile_feed(
        refresh_args, vcs=vcs, fs=fs, process=PosixProcess(), harness=BmadLoopHarness()
    )
    findings.extend(resync_findings)
    return True


def _emit(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    """The envelope-build-then-print tail every ``cli/deploy.py`` command
    shares, mirrored here for this module's own single command (AD-14: one
    envelope shape per command)."""
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(command="land", verdict=verdict_value, data=data, findings=tuple(findings))

    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text_land(envelope.data, envelope.findings)

    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()

    return exit_code_for(envelope.verdict)


def _render_text_land(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching ``cli/deploy.py``'s own
    ``_render_text*`` convention."""
    slug = data.get("slug") or "(no active project)"
    lines = [f"land: {slug!r}"]
    if "branch" in data:
        lines.append(f"branch: {data['branch']!r}")
    wave = data.get("wave")
    if wave is not None:
        lines.append(f"wave: {len(wave)} stor{'y' if len(wave) == 1 else 'ies'} ({', '.join(wave)})")
    if data.get("already_landed"):
        lines.append("already landed -- confirming retirement/resync only")
    if data.get("opened"):
        lines.append(f"opened: PR #{data.get('pr_number')} ({data.get('pr_url')})")
    elif data.get("updated"):
        lines.append(f"updated: PR #{data.get('pr_number')} ({data.get('pr_url')})")
    lines.append(f"merged: {data.get('merged')}")
    if "branch_retired" in data:
        lines.append(f"branch retired: {data.get('branch_retired')}")
    if "resynced" in data:
        lines.append(f"resynced: {data.get('resynced')}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)
