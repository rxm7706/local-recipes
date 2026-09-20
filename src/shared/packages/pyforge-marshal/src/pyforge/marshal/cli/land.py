"""``marshal land`` (Story 4.8, FR-60/AD-40) -- takes one project's wave from
"gates passed" to "merged, branch retired, feed resynced" with no human in
the sequencing loop. A NEW top-level subcommand (``marshal land <slug>``,
sibling to ``deploy``/``gate``/``init`` -- NOT nested under ``deploy``,
per the story's own Code Map).

**Three already-shipped primitives, reused, never reimplemented, plus ONE
new one (plus two more, Story 4.12's own ``fetch``/``fast_forward`` -- see
``_resync_home_branch``'s own docstring below).** Wave discovery, the
hygiene preflight, and PR open/update+labels
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
convention in ``cli/deploy.py``).

**A policy-true branch retirement is refused while this slug's own
bmad-loop run is still using the branch (Story 4.11, FR-172).** Before
honoring ``landing_branch_retirement``, ``run_land`` gathers the SAME
liveness facts ``marshal status`` gathers (``cli/status.py::
_gather_home_facts``) and checks them with ``core/status.py::is_run_live``
-- a live run downgrades ``delete_branch`` to ``False`` for THIS
invocation's ``merge_pr`` call only (never writing back to policy) and
raises ``MRS-LAND-008``, overridable with ``--retire-live-branch``. The
merge itself is never blocked by this gate -- only retirement is.

**A landing leaves the loop home current with `main` (Story 4.12, FR-173).**
``home`` shares the SAME ``.git`` as ``repo_root``, so a GitHub-side
``gh pr merge`` never updates any LOCAL ref there -- ``loop/<slug>`` goes
stale immediately, even between runs when nothing new lands. Gated by the
SAME ``landing_resync`` toggle ``_run_resync_if_enabled`` already uses, and
applicable ONLY when ``landing_merge_strategy == "merge"`` (a fast-forward
is impossible BY CONSTRUCTION under ``"squash"``/``"rebase"``, see
``_resync_home_branch``'s own docstring), ``_resync_home_branch`` runs
``VcsPort.fetch`` then ``VcsPort.fast_forward`` against ``origin/<base>``
from ALL THREE of this function's own wave-outcome exits -- the ``if not
wave_keys`` no-op (this story's own primary scenario: between-runs drift),
the already-landed shortcut, and the full-merge path -- setting
        ``data["home_current"]``. Any failure (a diverged branch, no network, a
        dirty tree, a held lock) is a new WARN finding (``MRS-LAND-009``), never
        escalated and never affecting this command's own exit.

    **Sprint-ledger promotion never writes the operator checkout (CAP-5).**
    ``_promote_sprint_ledger`` publishes onto ``origin/<base>`` through
    ``VcsPort.commit_paths_onto_remote_tip`` (throwaway detached worktree +
    fast-forward push). It must not ``commit_paths`` on ``repo_root()`` --
    that leftover diverged local ``main`` after every ``gh pr merge``."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from pyforge.core.process import PosixProcess, ProcessPort

from ..adapters.clock_system import SystemClock
from ..adapters.forge_gh import GhForge
from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import resolve_loop_runner
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import deferred_work, identity, policy, promotion
from ..core.identity import MalformedStoryKeyError, StoryKey
from ..core.journal import Phase
from ..core.landing import rule_applies
from ..core.model import Finding, Severity, build_envelope
from ..core.status import is_run_live, render_ledger_advancements
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.clock import ClockPort
from ..ports.forge import ForgeCommandError, ForgePort, ForgeRef
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.vcs import VcsPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    repo_root,
)

if TYPE_CHECKING:
    from pyforge.marshal.cli.deploy import _DeployRun

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
_MRS_LAND_008 = "MRS-LAND-008"
_MRS_LAND_009 = "MRS-LAND-009"
_MRS_LAND_010 = "MRS-LAND-010"
_MRS_LAND_011 = "MRS-LAND-011"

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
# Story 4.13's own journal kind -- distinct from `_PROMOTE_COMMIT_KIND`
# (`cli/deploy.py`'s own spec-promotion commit, a different writer
# namespace entirely per this module's own "distinct writer namespaces"
# discipline above).
_LAND_DEFERRED_WORK_KIND = "land-deferred-work-promotion"
# Story 15.2 (FR-136): sprint-status-ledger promotion on landing -- distinct
# from `_LAND_DEFERRED_WORK_KIND` (a different tracked twin).
_LAND_SPRINT_LEDGER_KIND = "land-sprint-ledger-promotion"

# Story 4.13 (AD-42's own precedent, `cli/deploy.py::_PROMOTE_LOCK_TIMEOUT_S`):
# how long `_promote_deferred_work` waits for a concurrent writer to release
# the tracked ledger's advisory lock before refusing cleanly (MRS-LAND-010).
# Short -- a re-run converges cheaply, so a long wait here buys little over
# just refusing and letting the next `land`/`deploy promote` invocation
# retry.
_LAND_DEFERRED_WORK_LOCK_TIMEOUT_S = 5.0
# Story 15.2 (FR-139 / AD-42): same short timeout for the sprint-status
# ledger lock -- concurrent `land` / `sprint-ledger-sync` writers serialize
# on `FsPort.acquire_advisory_lock`, never a second lock implementation.
_LAND_SPRINT_LEDGER_LOCK_TIMEOUT_S = 5.0
_LEDGER_DONE_STATUS = "done"


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
        "--retire-live-branch",
        action="store_true",
        default=False,
        help=(
            "Override refusal (Story 4.11): retire (delete) the loop-home "
            "station branch even while this slug's bmad-loop run is still "
            "live -- a supervisor confirmed alive with the run not yet "
            "finished, or a run whose journal/state could not be read far "
            "enough to prove it is NOT live. Without this flag, a live "
            "run downgrades a policy-true landing_branch_retirement to "
            "False for this invocation only (never mutating policy) and "
            "reports MRS-LAND-008. The merge itself always proceeds either "
            "way -- this flag affects ONLY whether the branch is retired "
            "afterward, never whether the wave lands."
        ),
    )
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
            status = forge.check_run_status(repo_ref, ForgeRef(head_sha), ForgeRef(rule.required_check))
        except ForgeCommandError as exc:
            report.append({"rule": rule.name, "required_check": rule.required_check, "status": None})
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
        report.append({"rule": rule.name, "required_check": rule.required_check, "status": status})
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
    harness: HarnessPort | None = None,
    process: ProcessPort | None = None,
    clock: ClockPort | None = None,
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
        _batch_pr_body,
        _batch_pr_redact,
        _batch_pr_title,
        _deploy_writer_id,
        _DeployRun,
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
    harness = harness if harness is not None else resolve_loop_runner()
    process = process if process is not None else PosixProcess()
    clock = clock if clock is not None else SystemClock()

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
                message=(f"cannot resolve the loop-home station branch {head_branch!r} for {slug!r}'s landing: {exc}"),
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
    if any(finding.severity is Severity.ERROR and "'landing_rules'" in finding.message for finding in policy_findings):
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
                message=(f"cannot compute the merge base of {head_branch!r} and {base!r}: {exc}"),
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
                message=(f"cannot enumerate commits between {merge_base_sha!r} and {head_branch!r}: {exc}"),
            )
        )
        return _emit(args, data, findings)
    wave_keys = sorted(promotion.merged_story_keys(wave_subjects, template, slug))
    data["wave"] = [str(key) for key in wave_keys]

    if not wave_keys:
        # Clean no-op -- nothing merged since the last landing. Still
        # resyncs the loop-home's own station branch to origin/<base>
        # (FR-173, Story 4.12) -- this is the story's own PRIMARY scenario:
        # between-runs drift accumulates unobserved exactly here, whether
        # or not this invocation finds anything new to land.
        home_current = _resync_home_branch(
            vcs, resync_enabled, merge_strategy, git_repo_root, home, base, head_branch, findings
        )
        if home_current is not None:
            data["home_current"] = home_current
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
            reconcile_feed,
            args,
            vcs,
            fs,
            resync_enabled,
            slug,
            findings,
            harness=harness,
            process=process,
        )
        promoted = _promote_deferred_work(fs, vcs, root, slug, wave_keys, clock, deploy_run, findings)
        if promoted:
            data["deferred_work_promoted"] = list(promoted)
        sprint_promoted = _promote_sprint_ledger(fs, vcs, root, slug, wave_keys, deploy_run, findings, base=base)
        if sprint_promoted:
            data["sprint_ledger_promoted"] = list(sprint_promoted)
        home_current = _resync_home_branch(
            vcs, resync_enabled, merge_strategy, git_repo_root, home, base, head_branch, findings
        )
        if home_current is not None:
            data["home_current"] = home_current
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
                        f"PR #{pr.number} opened/updated, but applying label(s) {list(deduped_labels)} failed: {exc}"
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

    # --- liveness gate (Story 4.11): a policy-true delete_branch is never
    # honored while THIS slug's own bmad-loop run is still using
    # head_branch -- confirmed 2026-08-09 against a live 9-story run,
    # avoided only because a human read the source first. Gathers the SAME
    # facts `marshal status` already gathers (`cli/status.py::
    # _gather_home_facts`, reused verbatim, never re-derived independently
    # here) ONLY when `delete_branch` is already True -- a project whose
    # `landing_branch_retirement` is False triggers no new I/O and no new
    # finding, unchanged from before this story. `_gather_home_facts`/
    # `_latest_run_dir`/`_resolve_harness_run_id_for_resume` are imported
    # LOCALLY, the same load-order-cycle reason every other cross-module
    # import in this function already documents.
    #
    # This check-then-act window (code review, 2026-08-09, both reviewers
    # independently) is intentionally left OPEN rather than re-verified
    # immediately before `forge.merge_pr` below: unlike `expected_head_sha`
    # (closed FORGE-SIDE, atomically, by `--match-head-commit` over a
    # required-check poll that can span minutes), there is no equivalent
    # atomic primitive for "this branch's run is still live" -- true
    # closure needs a cross-process lock between `land` and the bmad-loop
    # supervisor, out of this story's scope. The remaining window is one
    # local `deploy_run.write` journal call (no network, no polling) before
    # `merge_pr` is invoked -- as tight as this function's own established
    # intent-before/outcome-after ordering (AD-6) already places it.
    if delete_branch and not args.retire_live_branch:
        from .spin import _latest_run_dir, _resolve_harness_run_id_for_resume
        from .status import _gather_home_facts

        home_facts = _gather_home_facts(
            fs=fs,
            harness=harness,
            process=process,
            clock=clock,
            home=home,
            slug=slug,
            branch=head_branch,
            latest_run_dir=_latest_run_dir,
            resolve_harness_run_id=_resolve_harness_run_id_for_resume,
        )
        if is_run_live(home_facts):
            # Downgraded for THIS invocation's merge_pr call/journal payload
            # only -- never writes back to the on-disk `landing_branch_
            # retirement` policy value itself.
            delete_branch = False
            findings.append(
                Finding(
                    code=_MRS_LAND_008,
                    severity=Severity.WARN,
                    message=(
                        f"{slug!r}'s bmad-loop run is still using "
                        f"{head_branch!r} -- skipping branch retirement "
                        "this run (the merge still proceeds); pass "
                        "--retire-live-branch to retire it anyway"
                    ),
                )
            )

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
    # Render the merge subject (AD-24, Story 5.10) -- the SAME already-
    # shipped `identity.render_merge_subject` `deploy land-story` already
    # uses, from the wave's primary (lowest-sorted) key (`wave_keys[0]`; see
    # this story's own Design Notes for why a single key, not all wave
    # keys) -- never hand-typed, never a separate pre-merge PR-title-edit
    # call.
    subject = identity.render_merge_subject(wave_keys[0], template, slug)
    data["subject"] = subject

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
            subject=ForgeRef(subject),
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

    promoted = _promote_deferred_work(fs, vcs, root, slug, wave_keys, clock, deploy_run, findings)
    if promoted:
        data["deferred_work_promoted"] = list(promoted)
    sprint_promoted = _promote_sprint_ledger(fs, vcs, root, slug, wave_keys, deploy_run, findings, base=base)
    if sprint_promoted:
        data["sprint_ledger_promoted"] = list(sprint_promoted)

    # One journal OBSERVATION entry recording checks required/passed, what
    # merged, and under whose authority (the story's own Always bullet) --
    # redacted at capture via `_land_redact_text`, reused rather than
    # reimplemented (AD-34).
    required_summary = _land_redact_text(json.dumps([entry["required_check"] for entry in required_report]))
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
        reconcile_feed,
        args,
        vcs,
        fs,
        resync_enabled,
        slug,
        findings,
        harness=harness,
        process=process,
    )
    home_current = _resync_home_branch(
        vcs, resync_enabled, merge_strategy, git_repo_root, home, base, head_branch, findings
    )
    if home_current is not None:
        data["home_current"] = home_current

    return _emit(args, data, findings)


def _promote_deferred_work(
    fs: FsPort,
    vcs: VcsPort,
    root: Path,
    slug: str,
    wave_keys: list[StoryKey],
    clock: ClockPort,
    deploy_run: "_DeployRun",
    findings: list[Finding],
) -> tuple[str, ...]:
    """FR-175 (Story 4.13): promotes each landing story's Tier-3
    ``review-budget-followup`` deferral -- bmad-loop's own follow-up-review
    damping safety valve, written to the gitignored ``implementation-
    artifacts/deferred-work.md`` -- into the tracked ``planning-artifacts/
    deferred-work-ledger.md``, at the moment ``wave_keys`` is confirmed
    landed. Mirrors ``cli/deploy.py``'s own spec-promotion shape
    (``_scan_promotions``/``run_promote``, AD-42): a cheap unlocked read,
    the pure ``core.deferred_work`` classify/render core, THEN a lock ->
    write -> commit -> intent/outcome-journal sequence for the write alone.

    Reads both files fresh via ``fs.read_text`` (never a cached copy, per
    this story's own Boundaries) and returns ``()`` -- no lock acquired, no
    write, no finding -- when the Tier-3 file is absent/empty, no Tier-3
    block parses, or every parsed candidate is already promoted
    (``core.deferred_work.deferrals_to_promote``'s own idempotency check:
    a promoted id already present as a COMPLETE token anywhere in the
    tracked ledger's text -- never a bare substring test, which would
    false-positive on a prefix collision like ``"DW-FU-1-1"`` vs
    ``"DW-FU-1-10"`` -- is never re-appended). This single-shared-file
    idempotency check is simpler than ``cli/deploy.py::_already_promoted_keys``'s own
    ``vcs.path_has_uncommitted_changes`` guard by design (see this story's
    Design Notes for the deviation and its rationale) -- this operation
    reads, writes, AND commits the one shared ledger file within this one
    call, unlike ``run_promote``'s per-story tracked-file copies, which a
    separate, earlier, possibly-crashed invocation could have left
    uncommitted.

    A MISSING tracked ledger (no file at all -- a brand-new project) is
    treated as an empty one and bootstrapped on write (review finding,
    2026-08-10): the very first promotion for such a project must not be a
    silent, permanent no-op. A tracked ledger that EXISTED at the first,
    unlocked read but is gone by the time the lock is held is a different,
    genuinely anomalous case -- a concurrent deletion -- and is reported
    (``MRS-LAND-010`` WARN) rather than silently resurrected from stale
    pre-lock content.

    Otherwise: acquires an advisory lock on the tracked ledger path itself
    (a sibling ``.lock`` file, mirroring ``run_promote``'s own
    ``specs_dir`` lock), re-reads and re-filters under the lock (closing
    the window against a concurrent writer), appends every candidate's
    ``render_ledger_entry`` text, writes the whole file atomically, commits
    it in its OWN dedicated commit (never folded into any other write this
    run makes), and journals intent-before/outcome-after
    (``_LAND_DEFERRED_WORK_KIND``, mirroring ``_PROMOTE_COMMIT_KIND``'s own
    shape). Lock contention or a ``commit_paths`` failure fires ONE
    ``MRS-LAND-010`` WARN and returns ``()`` -- never blocking ``land``'s
    own exit code (the wave's own landing already succeeded by the time
    this best-effort step runs)."""
    tier3_path = root / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "deferred-work.md"
    tracked_path = root / "_bmad-output" / "projects" / slug / "planning-artifacts" / "deferred-work-ledger.md"

    tier3_text = fs.read_text(tier3_path)
    if not tier3_text:
        return ()
    candidates = deferred_work.parse_followup_deferrals(tier3_text)
    if not candidates:
        return ()

    tracked_text = fs.read_text(tracked_path)
    tracked_existed = tracked_text is not None
    if tracked_text is None:
        tracked_text = ""

    landing_keys = frozenset(wave_keys)
    if not deferred_work.deferrals_to_promote(candidates, landing_keys, tracked_text):
        return ()

    try:
        lock = fs.acquire_advisory_lock(tracked_path, timeout_s=_LAND_DEFERRED_WORK_LOCK_TIMEOUT_S)
    except FsError as exc:
        findings.append(
            Finding(
                code=_MRS_LAND_010,
                severity=Severity.WARN,
                message=(
                    f"cannot acquire the deferred-work-ledger lock on "
                    f"{str(tracked_path)!r} within "
                    f"{_LAND_DEFERRED_WORK_LOCK_TIMEOUT_S}s -- another land/"
                    f"promote is plausibly running concurrently for "
                    f"{slug!r}; nothing was promoted this run: {exc}"
                ),
            )
        )
        return ()

    try:
        fresh_tracked_text = fs.read_text(tracked_path)
        if fresh_tracked_text is None:
            if tracked_existed:
                findings.append(
                    Finding(
                        code=_MRS_LAND_010,
                        severity=Severity.WARN,
                        message=(
                            f"the tracked deferred-work ledger at "
                            f"{str(tracked_path)!r} existed moments ago but "
                            "is gone now -- skipping this run rather than "
                            "resurrecting it from stale pre-lock content"
                        ),
                    )
                )
                return ()
            fresh_tracked_text = ""
        to_promote = deferred_work.deferrals_to_promote(candidates, landing_keys, fresh_tracked_text)
        if not to_promote:
            return ()

        promoted_date = clock.now().date().isoformat()
        entry_text = "\n".join(
            deferred_work.render_ledger_entry(candidate, promoted_date=promoted_date) for candidate in to_promote
        )
        prefix = fresh_tracked_text.rstrip("\n")
        new_text = (prefix + "\n\n" if prefix else "") + entry_text
        try:
            fs.write_text_atomic(tracked_path, new_text)
        except FsError as exc:
            findings.append(
                Finding(
                    code=_MRS_LAND_010,
                    severity=Severity.WARN,
                    message=(f"cannot write the promoted deferred-work entries to {str(tracked_path)!r}: {exc}"),
                )
            )
            return ()

        promoted_ids = tuple(deferred_work.promoted_id(candidate.story_key) for candidate in to_promote)
        message = (
            f"marshal: promote {len(promoted_ids)} deferred-work "
            f"entr{'y' if len(promoted_ids) == 1 else 'ies'} for {slug!r}"
        )
        intent_id = deploy_run.write(
            findings,
            kind=_LAND_DEFERRED_WORK_KIND,
            phase=Phase.INTENT,
            payload={"action": "commit_paths", "promoted": list(promoted_ids)},
        )
        try:
            vcs.commit_paths(root, (tracked_path,), message)
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_LAND_010,
                    severity=Severity.WARN,
                    message=(
                        f"promoted deferred-work entries {list(promoted_ids)} "
                        f"written to {str(tracked_path)!r} but could not be "
                        f"committed: {exc}"
                    ),
                )
            )
            return ()
        if intent_id is not None:
            deploy_run.write(
                findings,
                kind=_LAND_DEFERRED_WORK_KIND,
                phase=Phase.OUTCOME,
                payload={
                    "action": "commit_paths",
                    "promoted": list(promoted_ids),
                    "commit_message": message,
                },
                intent_id=intent_id,
            )
        return promoted_ids
    finally:
        fs.release_advisory_lock(lock)


def _parse_sprint_ledger_statuses(text: str) -> dict[str, str]:
    """Tiny ``development_status:`` map parser -- same shape
    ``scripts/promote_sprint_status.py`` / Doctor's ledger sources use.
    Kept local so this CLI never imports those modules just to read a
    tracked twin."""
    out: dict[str, str] = {}
    in_block = False
    for raw in text.splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        if raw and not raw.startswith((" ", "\t")):
            break
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def _load_promote_sprint_status_module() -> object | None:
    """Install-free load of ``scripts/promote_sprint_status.py`` (Story 15.2 /
    Story 5.9 precedent in ``cli/deploy.py::_load_promote_sprint_status``).
    Returns ``None`` when the script is missing -- land still advances
    wave keys via ``render_ledger_advancements`` without the feed sync."""
    import importlib.util

    checkout_root = Path(__file__).resolve().parents[8]
    path = checkout_root / "scripts" / "promote_sprint_status.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_promote_sprint_status_land", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _land_feed_sync_refusal(
    promote_mod: object,
    existing: dict[str, str],
    incoming: dict[str, str],
) -> tuple[str, str] | None:
    """``(label, detail)`` naming why a feed-sync promotion must be refused,
    or ``None`` when the incoming feed is safe to promote as-is.

    ``regressions()`` only catches a key MOVING out of a protected state
    (done / story blocked) -- it does not catch a key the feed drops
    entirely while never having promoted it in the first place (e.g. a
    still-backlog story in a freshly-authored epic the Tier-3 feed has
    never seen). Mirrors ``promote_sprint_status.main()``'s own ``missing``
    computation (Story 48.1) -- that fix landed in the standalone CLI's
    ``main()`` only; ``_promote_sprint_ledger`` never routes through it, so
    the same guard is duplicated here rather than assumed inherited. Live
    incident 2026-09-10: this exact gap silently dropped pyforge-warden's
    Epic 12 backlog stories 6 seconds after this function auto-landed
    Story 12.1 (restored by hand, PR #1117)."""
    lost = promote_mod.regressions(existing, incoming)
    missing = [k for k in existing if k not in incoming]
    if not lost and not missing:
        return None
    if lost:
        detail = ", ".join(f"{k} ({old} -> {new})" for k, old, new in lost)
        return "un-finish", detail
    detail = ", ".join(sorted(missing))
    return "drop", detail


def _promote_sprint_ledger(
    fs: FsPort,
    vcs: VcsPort,
    root: Path,
    slug: str,
    wave_keys: list[StoryKey],
    deploy_run: "_DeployRun",
    findings: list[Finding],
    *,
    base: str,
) -> tuple[str, ...]:
    """FR-136 (Story 15.2): mechanically promote the tracked
    ``sprint-status-ledger.yaml`` when a wave lands -- deterministic
    trigger, never memory.

    Two steps under one ``FsPort.acquire_advisory_lock`` (FR-139 / AD-42 --
    never a second lock implementation):

    1. When a Tier-3 ``sprint-status.yaml`` feed is present, sync it into
       the tracked twin via ``scripts/promote_sprint_status.py``'s own
       ``render``/``regressions`` (downgrade refusal stays that script's;
       a refused sync is WARN-named, never a silent overwrite).
    2. Advance every ``wave_keys`` row that already exists in the twin to
       ``done`` via ``render_ledger_advancements`` (covers feed lag / a
       missing feed while the twin already carries the key).

    Returns the raw ledger keys newly moved to ``done`` this run (empty
    when already converged). Lock contention / write / commit failures
    fire ``MRS-LAND-011`` WARN and return ``()`` -- never blocking
    ``land``'s exit (the wave already landed).

    CAP-5: the commit is published onto ``origin/<base>`` via
    ``commit_paths_onto_remote_tip``. This function must not
    ``write_text_atomic`` + ``commit_paths`` on ``root`` -- that leftover
    diverged the operator ``main`` checkout after every GitHub merge."""
    if not wave_keys:
        return ()

    ledger_path = root / "_bmad-output" / "projects" / slug / "planning-artifacts" / "sprint-status-ledger.yaml"
    feed_path = root / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "sprint-status.yaml"

    feed_text = fs.read_text(feed_path)
    ledger_text = fs.read_text(ledger_path)
    if feed_text is None and ledger_text is None:
        return ()

    landing = frozenset(wave_keys)

    def _raw_keys_needing_done(text: str) -> frozenset[str]:
        statuses = _parse_sprint_ledger_statuses(text)
        needed: set[str] = set()
        for raw_key, status in statuses.items():
            if status == _LEDGER_DONE_STATUS:
                continue
            try:
                key = identity.normalize(raw_key)
            except MalformedStoryKeyError:
                continue
            if key in landing:
                needed.add(raw_key)
        return frozenset(needed)

    pre_needed = _raw_keys_needing_done(ledger_text or "")
    # Cheap unlocked preview: if the twin already marks every wave key
    # done AND there is no feed to sync, skip the lock entirely.
    if not pre_needed and feed_text is None:
        return ()

    try:
        lock = fs.acquire_advisory_lock(ledger_path, timeout_s=_LAND_SPRINT_LEDGER_LOCK_TIMEOUT_S)
    except FsError as exc:
        findings.append(
            Finding(
                code=_MRS_LAND_011,
                severity=Severity.WARN,
                message=(
                    f"cannot acquire the sprint-status-ledger lock on "
                    f"{str(ledger_path)!r} within "
                    f"{_LAND_SPRINT_LEDGER_LOCK_TIMEOUT_S}s -- another "
                    f"land/sprint-ledger-sync is plausibly running "
                    f"concurrently for {slug!r}; nothing was promoted "
                    f"this run: {exc}"
                ),
            )
        )
        return ()

    try:
        fresh_ledger = fs.read_text(ledger_path)
        if fresh_ledger is None:
            fresh_ledger = ""
        ledger_rel = f"_bmad-output/projects/{slug}/planning-artifacts/sprint-status-ledger.yaml"
        try:
            vcs.fetch(root, "origin", base)
            remote_text = vcs.file_text_at_ref(root, f"origin/{base}", ledger_rel)
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_LAND_011,
                    severity=Severity.WARN,
                    message=(
                        f"cannot fetch {base!r} before promoting the sprint "
                        f"ledger for {slug!r}; nothing was published this "
                        f"run: {exc}"
                    ),
                    path=str(ledger_path),
                )
            )
            return ()
        if remote_text is not None:
            fresh_ledger = remote_text

        promote_mod = _load_promote_sprint_status_module()
        project_key = slug.removeprefix("pyforge-")
        src_rel = f"_bmad-output/projects/{slug}/implementation-artifacts/sprint-status.yaml"
        working = fresh_ledger
        feed_synced = False

        if feed_text is not None and promote_mod is not None:
            try:
                gen = promote_mod._load_generate()
                incoming = gen.parse_sprint_status(feed_path)
            except Exception as exc:  # noqa: BLE001 -- best-effort feed sync
                findings.append(
                    Finding(
                        code=_MRS_LAND_011,
                        severity=Severity.WARN,
                        message=(f"Tier-3 sprint feed at {str(feed_path)!r} could not be parsed for promotion: {exc}"),
                        path=str(feed_path),
                    )
                )
                incoming = {}
            if incoming:
                existing = gen.parse_sprint_status(ledger_path) if fresh_ledger.strip() else {}
                refusal = _land_feed_sync_refusal(promote_mod, existing, incoming)
                if refusal is not None:
                    label, detail = refusal
                    findings.append(
                        Finding(
                            code=_MRS_LAND_011,
                            severity=Severity.WARN,
                            message=(
                                f"refusing to promote sprint ledger for {slug!r}: feed would {label} key(s): {detail}"
                            ),
                            path=str(ledger_path),
                        )
                    )
                else:
                    working = promote_mod.render(project_key, src_rel, incoming)
                    feed_synced = working != fresh_ledger

        needed = _raw_keys_needing_done(working)
        if not needed and not feed_synced:
            return ()

        new_text, matched = render_ledger_advancements(working, needed)
        if not matched and not feed_synced:
            return ()

        promoted_keys = tuple(sorted(matched))
        message = (
            f"marshal: promote sprint-status ledger for {slug!r} ({len(promoted_keys)} key(s) -> done)"
            if promoted_keys
            else f"marshal: promote sprint-status ledger for {slug!r} (feed sync)"
        )
        intent_id = deploy_run.write(
            findings,
            kind=_LAND_SPRINT_LEDGER_KIND,
            phase=Phase.INTENT,
            payload={
                "action": "commit_paths_onto_remote_tip",
                "promoted": list(promoted_keys),
                "feed_synced": feed_synced,
                "base": base,
            },
        )
        try:
            vcs.commit_paths_onto_remote_tip(
                root,
                remote="origin",
                ref=base,
                writes=((ledger_rel, new_text),),
                message=message,
            )
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_LAND_011,
                    severity=Severity.WARN,
                    message=(
                        f"promoted sprint-status ledger keys "
                        f"{list(promoted_keys)} written to "
                        f"{str(ledger_path)!r} but could not be committed: "
                        f"{exc}"
                    ),
                    path=str(ledger_path),
                )
            )
            return ()
        if intent_id is not None:
            deploy_run.write(
                findings,
                kind=_LAND_SPRINT_LEDGER_KIND,
                phase=Phase.OUTCOME,
                payload={
                    "action": "commit_paths_onto_remote_tip",
                    "promoted": list(promoted_keys),
                    "feed_synced": feed_synced,
                    "commit_message": message,
                    "base": base,
                },
                intent_id=intent_id,
            )
        # Report feed-only sync as the project key so the envelope still
        # names that promotion happened when every wave key was already done.
        if promoted_keys:
            return promoted_keys
        return (project_key,) if feed_synced else ()
    finally:
        fs.release_advisory_lock(lock)


def _resync_home_branch(
    vcs: VcsPort,
    resync_enabled: bool,
    merge_strategy: str,
    git_repo_root: Path,
    home: Path,
    base: str,
    head_branch: str,
    findings: list[Finding],
) -> bool | None:
    """FR-173 (Story 4.12): fast-forwards the loop-home's own checked-out
    station branch (``head_branch``, at ``home``) to ``origin/<base>`` --
    ``home`` shares the SAME ``.git`` as ``repo_root``, so a GitHub-side
    ``gh pr merge`` never updates any LOCAL ref there, and ``head_branch``
    goes stale immediately (even between runs when nothing new lands --
    this story's own named primary scenario). Called from ALL THREE of
    ``run_land``'s own wave-outcome exits (the ``if not wave_keys`` no-op,
    the already-landed shortcut, and the full-merge path), always gated on
    the SAME ``landing_resync`` toggle ``_run_resync_if_enabled`` already
    uses (no new policy key).

    Returns ``None`` -- meaning ``data["home_current"]`` stays ABSENT,
    byte-identical to ``resync_enabled=False`` -- when either
    ``resync_enabled`` is ``False`` or ``merge_strategy`` is not
    ``"merge"``: under ``"squash"``/``"rebase"`` the landed commits are
    never ancestors of ``origin/<base>``, so ``fast_forward`` is impossible
    BY CONSTRUCTION, on every invocation, permanently -- firing a WARN that
    can never clear would be noise, not signal, so this resync capability
    is deliberately restricted to the ``"merge"`` strategy only (Boundaries
    & Constraints, corrected 2026-08-09).

    Before touching anything, reconfirms ``home`` is still checked out at
    ``head_branch``'s own tip (``VcsPort.worktree_head_sha`` vs
    ``VcsPort.resolve_ref``, the SAME pair the full-merge path above already
    uses for the identical reason at ``MRS-DEPLOY-017``) -- for the no-op and
    already-landed call sites this IS the only identity check ever reached,
    since neither has an earlier ``MRS-DEPLOY-017``-style pre-check of its
    own. ``fast_forward`` itself only ever asks "is this a fast-forward from
    whatever HEAD currently is," so without this guard a `home` that had
    drifted onto a different ref (or a detached HEAD) would get THAT ref
    silently advanced while ``head_branch`` stayed stale and ``home_current``
    still reported ``True`` (code review, 2026-08-10). A mismatch is reported
    exactly like any other resync failure -- one ``MRS-LAND-009`` WARN, no
    fast-forward attempted.

    Otherwise runs ``VcsPort.fetch`` (updates ONLY ``refs/remotes/origin/
    <base>``, a network read) then ``VcsPort.fast_forward`` (``git merge
    --ff-only``, never a forced merge/``--no-ff``/rebase/``reset --hard``)
    against ``home``, each in its own ``try`` so the WARN names the step
    that actually failed (code review, 2026-08-10). Success -- fast-forwarded
    OR already current, both of which ``--ff-only`` treats identically --
    returns ``True`` with no finding. Any failure (a diverged branch, e.g. a
    live bmad-loop run that kept committing past the landed wave; no
    network; a dirty working tree; a held lock) fires ONE new
    ``MRS-LAND-009`` WARN naming ``head_branch`` and git's own precise
    reason, and returns ``False`` -- never escalated, never affecting
    ``land``'s own exit code (AD-7: only the verdict STRING may move to
    ``warn``; the merge that matters, the wave landing on ``base``, already
    succeeded by the time this best-effort step runs). Never pushes the
    fast-forwarded branch to any remote -- Story 3.8's own stage-boundary
    push watcher already keeps a LIVE run's branch current; out of this
    story's scope."""
    if not resync_enabled or merge_strategy != "merge":
        return None

    def _warn(message: str) -> bool:
        findings.append(Finding(code=_MRS_LAND_009, severity=Severity.WARN, message=message))
        return False

    try:
        expected_sha = vcs.resolve_ref(git_repo_root, head_branch)
    except VcsCommandError as exc:
        return _warn(f"could not resolve {head_branch!r}'s own tip before resyncing with 'origin/{base}': {exc}")
    try:
        home_sha = vcs.worktree_head_sha(home)
    except VcsCommandError as exc:
        return _warn(
            f"could not confirm {home}'s own checked-out commit before "
            f"resyncing {head_branch!r} with 'origin/{base}': {exc}"
        )
    if home_sha != expected_sha:
        return _warn(
            f"{home}'s checked-out commit ({home_sha!r}) no longer matches "
            f"{head_branch!r}'s own tip ({expected_sha!r}) -- skipping resync "
            "rather than fast-forwarding whatever is actually checked out"
        )

    try:
        vcs.fetch(git_repo_root, "origin", base)
    except VcsCommandError as exc:
        return _warn(f"could not fetch {base!r} from origin for {head_branch!r}: {exc}")

    try:
        vcs.fast_forward(home, f"origin/{base}")
    except VcsCommandError as exc:
        return _warn(f"could not fast-forward {head_branch!r} in {home} to 'origin/{base}': {exc}")
    return True


def _run_resync_if_enabled(
    reconcile_feed,
    args,
    vcs,
    fs,
    resync_enabled: bool,
    slug: str,
    findings: list[Finding],
    *,
    harness: HarnessPort,
    process: ProcessPort,
) -> bool:
    """Gated by ``landing_resync`` (Story 4.7): calls ``cli/deploy.py::
    reconcile_feed`` in-process (the non-printing core ``run_refresh_feed``
    itself calls, before its own ``_emit`` -- see this module's own
    docstring for why ``land`` reuses the core rather than the printing
    wrapper) -- ``False`` skips it entirely, reporting
    ``data["resynced"]: false`` with no finding, per the story's own Always
    bullet. Any findings the reconciliation itself surfaces are folded into
    THIS run's own ``findings`` list -- never silently dropped, and never
    printed as a second envelope.

    ``harness``/``process`` are ``run_land``'s own DI params (Story 4.11),
    threaded through rather than each call constructing its own default
    adapter -- one instantiation policy for both of this function's own
    port uses, never two independently-drifting ones."""
    if not resync_enabled:
        return False
    refresh_args = argparse.Namespace(project=slug, format=args.format)
    _resync_data, resync_findings = reconcile_feed(refresh_args, vcs=vcs, fs=fs, process=process, harness=harness)
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
    if "subject" in data:
        lines.append(f"subject: {data['subject']!r}")
    if "branch_retired" in data:
        lines.append(f"branch retired: {data.get('branch_retired')}")
    if "resynced" in data:
        lines.append(f"resynced: {data.get('resynced')}")
    if "home_current" in data:
        lines.append(f"home current with {data.get('base')!r}: {data.get('home_current')}")
    if "deferred_work_promoted" in data:
        promoted = data["deferred_work_promoted"]
        lines.append(f"deferred work promoted: {', '.join(promoted)}")
    if "sprint_ledger_promoted" in data:
        promoted = data["sprint_ledger_promoted"]
        lines.append(f"sprint ledger promoted: {', '.join(promoted)}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)
