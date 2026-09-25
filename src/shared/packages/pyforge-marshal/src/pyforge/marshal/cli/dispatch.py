"""``marshal factory dispatch`` (Story 22.1, FR-193 CAP-1) -- launch exactly
one worktree-isolated ``bmad-build-auto`` session under marshal governance.

Story 22.7 (FR-193 CAP-7) adds ``marshal factory drain``: the fleet-wide
campaign mode that reads every pyforge station's ordered backlog from its
TRACKED ``sprint-status-ledger.yaml`` (plus optional in-repo order
overrides), applies a campaign mode, and hands each station its next story
by calling ``dispatch_once`` -- the same primitive, once per station per
cycle, so the CAP-2 zombie refusal, the CAP-5 one-per-station guard, and the
CAP-5 cross-station overlap advisory are INHERITED, never re-implemented.
Chaining is structural rather than scripted: a detached campaign supervisor
re-runs the cycle, and a station whose story finished merge-through-finalize
(CAP-4: CI-green merge, scoped ``sprint-ledger-sync --project <station>``,
spec promotion) has an advanced ledger and a free slot, so the next cycle
dispatches its next story. This supersedes ``.cursor/pyforge-fleet-drain/``'s
hand-driven coordinator; campaign state lives in-repo under
``pyforge-marshal``, never in session-local ``.cursor/`` YAML.

Story 22.11 (FR-193 CAP-10) extends this same surface with two pure
read-scope/read-order overrides -- never a second campaign implementation:
``drain --station <slug>`` restricts one cycle to exactly one station's own
tracked backlog (``execute_fleet_cycle``'s ``station`` argument), and
``dispatch <slug> --stories k1,k2,...`` chains a caller-supplied ordered
sequence on that station instead of its ledger order
(``execute_fleet_cycle``'s ``explicit_stories`` argument, backed by
``dispatch_fleet.explicit_story_backlog``). ``dispatch --stories`` is a thin
translation layer over ``run_fleet_drain`` itself -- both surfaces share one
preflight/journal/campaign-supervisor implementation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadbuild import BmadBuildHarness, BuildHarnessError
from ..adapters.harness_bmadloop import HarnessError, resolve_loop_runner
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import dispatch as dispatch_core
from ..core import dispatch_fleet, dispatch_re_preflight, gate, harness_profile, policy
from ..core import promotion as promotion_core
from ..core.dispatch_completion import (
    DispatchGitFacts,
    DispatchSessionVerdict,
    is_spec_only_narration,
    zombie_redispatch_evidence,
)
from ..core.dispatch_harness_done import (
    blocks_harness_relaunch,
    followup_review_recommended,
    land_fail_operator_message,
    parse_blocking_condition,
    parse_spec_status,
)
from ..core.dispatch_landing import DispatchLandingVerdict
from ..core.dispatch_retry import (
    DispatchBlockKind,
    classify_dispatch_block,
    exclude_harness_profiles_after_transient_failure,
    prune_blocked_stories_merged_on_main,
)
from ..core.dispatch_supervisor_finalize import (
    finalize_attempt_failed,
    finalize_attempt_journaled,
    finalize_failure_worktree_path,
)
from ..core.dispatch_verification import (
    DispatchVerificationInput,
    DispatchVerificationVerdict,
    judge_dispatch_verification,
)
from ..core.identity import (
    MalformedStoryKeyError,
    StoryKey,
    normalize,
    render_feed_key,
)
from ..core.journal import (
    JournalEntryId,
    Phase,
    build_entry,
    fold,
    mint_run_id,
    prepare_for_write,
    resolve_land_findings_from_payload,
    resolve_scope_violation_advisories_from_payload,
    sidecar_texts_for_lines,
)
from ..core.model import Finding, Severity, build_envelope
from ..core.model_cost import (
    adapter_provider,
    catalog_declared,
    is_harness_default_model,
    provider_declaring_model,
)
from ..core.spec_deps import story_deps_from_epics, story_transitively_depends_on
from ..core.spec_surface import SurfaceParseError, parse_declared_surface
from ..core.supervise import count_unified_diff_lines, resolve_terminal_session_verdict
from ..core.verdict import compute_verdict, exit_code_for
from ..dispatch_land import execute_dispatch_land
from ..dispatch_supervisor.__main__ import gather_dispatch_git_facts
from ..dispatch_verify import evaluate_dispatch_verification
from ..ports.build_harness import BuildHarnessPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.vcs import VcsPort
from ..scope import format_scope_drift, verify_scope
from ..seed.detect.kit import probe_instrument
from ..seed.model.kit import KitItemId, kit_item
from ..seed.verbs.kit import render_deployed_skill
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    read_repo_policy_defaults,
)
from .land import _parse_sprint_ledger_statuses
from .seed import packaged_seed_model_version

if TYPE_CHECKING:
    from ..core.context import MarshalContext


@dataclass(frozen=True)
class DispatchPreflightConflict:
    """A dispatch refusal with its registered finding code (Story 22.2/22.5)."""

    code: str
    message: str
    in_flight_story_key: str
    overlap_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class DispatchAttempt:
    """One ``dispatch_once`` outcome: envelope ``data`` plus its findings."""

    data: dict[str, object]
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == Severity.ERROR)

    @property
    def launched(self) -> bool:
        """True when a session pid was recorded and nothing blocked it."""
        return not self.errors and self.data.get("session_pid") is not None


@dataclass(frozen=True)
class FleetCycleReport:
    """One fleet-drain cycle's per-station results, findings, and data."""

    results: tuple[dispatch_fleet.StationCycleResult, ...]
    findings: tuple[Finding, ...]
    data: dict[str, object]

    @property
    def complete(self) -> bool:
        return dispatch_fleet.campaign_complete(self.results)


_JOURNAL_FILENAME = "journal.jsonl"
_LOG_FILENAME = "session.log"
_SUPERVISOR_LOG_FILENAME = "dispatch-supervisor.log"
_FLEET_SUPERVISOR_LOG_FILENAME = "fleet-drain-supervisor.log"
_BASE_REF = "origin/main"

#: How long the detached campaign supervisor waits between cycles -- passed
#: to it, never slept on here. A cycle is cheap (ledger reads + git/process
#: facts) and a story takes minutes to hours, so this matches the per-story
#: supervisor's own 60 s tick.
_FLEET_TICK_SECONDS = 60

#: Short, matching `cli/land.py`'s own advisory-lock convention: a cycle is
#: cheap and the supervisor re-ticks, so waiting long buys nothing over
#: refusing and letting the next cycle retry.
_FLEET_CYCLE_LOCK_TIMEOUT_S = 5.0

#: The run-id shape `mint_run_id` produces. `--campaign` names a DIRECTORY
#: under the campaign runs tree, so anything path-shaped is refused.
_SAFE_CAMPAIGN_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _is_safe_campaign_id(raw: str) -> bool:
    return bool(_SAFE_CAMPAIGN_ID_RE.match(raw)) and raw not in {".", ".."}


def add_factory_dispatch_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    parser = factory_subparsers.add_parser(
        "dispatch",
        help="Launch one detached bmad-build-auto story session (Story 22.1).",
        description=(
            "Provisions a fresh isolated worktree from origin/main, launches "
            "exactly one detached session harness run with BMAD_ACTIVE_PROJECT "
            "per-invocation and physical artifact paths, journals the launch, "
            "and returns promptly. With --stories (Story 22.11, FR-193 "
            "CAP-10), chains a caller-supplied ordered sequence on this one "
            "station instead -- a thin translation over `factory drain`'s own "
            "campaign machinery (fleet-wide advisory lock, journal, detached "
            "supervisor), never a second implementation."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug (station).")
    parser.add_argument(
        "story",
        nargs="?",
        default=None,
        help="The backlog story key to dispatch (omit when passing --stories).",
    )
    parser.add_argument(
        "--stories",
        default=None,
        help=(
            "Comma-separated ordered story keys to chain on this station "
            "instead of a single story (Story 22.11, FR-193 CAP-10) -- "
            "launched one dispatch at a time via the same chaining "
            "`factory drain` already uses. Every key must already be "
            "eligible on the station's TRACKED backlog (not done, not "
            "unknown) or the whole sequence is refused before any "
            "worktree is provisioned."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--harness",
        default=None,
        help=(
            "Ordered session-harness preference for this invocation only "
            "(comma-separated profile names, e.g. cursor,claude). Overrides "
            "project/repo defaults without editing marshal-policy.toml."
        ),
    )
    parser.set_defaults(handler=run_dispatch)


def _writer_id() -> str:
    return f"dispatch-{os.getpid()}"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc_compact(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%S") + f"{moment.microsecond // 1000:03d}Z"


def _format_entry_ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _random_token() -> str:
    return secrets.token_hex(4)


def _dispatch_scope_refusal(repo_root: Path, slug: str) -> Finding | None:
    """Story 33.9 / FR-190 CAP-1 third call site: refuse before any launch work.

    Checks the parent ``BMAD_ACTIVE_PROJECT`` env (when set) and the sole
    ``verify_scope`` triangle against the dispatch slug.
    """
    env_slug = os.environ.get("BMAD_ACTIVE_PROJECT", "").strip()
    if env_slug and env_slug != slug:
        return Finding(
            code="MRS-DISP-041",
            severity=Severity.ERROR,
            message=(
                f"scope drift: dispatch resolved project {slug!r} disagrees with "
                f"BMAD_ACTIVE_PROJECT env {env_slug!r} -- use physical paths under "
                f"_bmad-output/projects/{slug}/ and never scripts/bmad-switch"
            ),
        )
    drift = verify_scope(repo_root, slug)
    if drift is not None:
        return Finding(
            code="MRS-DISP-041",
            severity=Severity.ERROR,
            message=format_scope_drift(drift),
        )
    return None


def _append_entry(fs: FsPort, run_dir: Path, entry, *, fsync: bool) -> None:
    prepared = prepare_for_write(entry)
    if prepared.sidecar_relative_path is not None:
        fs.write_text_atomic(run_dir / prepared.sidecar_relative_path, prepared.sidecar_content)
    fs.append_line(run_dir / _JOURNAL_FILENAME, prepared.line, fsync=fsync)


def _emit(
    args: argparse.Namespace,
    data: dict[str, object],
    findings: list[Finding],
    *,
    command: str = "factory dispatch",
) -> int:
    envelope = build_envelope(
        command=command,
        verdict=compute_verdict(tuple(findings)),
        data=data,
        findings=tuple(findings),
    )
    try:
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True), flush=True)
        else:
            lines = [f"command: {command}", f"verdict: {envelope.verdict.value}"]
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            for finding in findings:
                lines.append(f"finding {finding.code}: {finding.message}")
            print("\n".join(lines), flush=True)
    except OSError, UnicodeEncodeError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _policy_flags_from_harness_arg(raw: str | None) -> dict[str, object]:
    if raw is None or not str(raw).strip():
        return {}
    profiles = tuple(part.strip() for part in str(raw).split(",") if part.strip())
    if not profiles:
        return {}
    return {"harness_preference": profiles}


def _compose_policy(slug: str, *, flags: dict[str, object] | None = None) -> policy.EffectivePolicy:
    # Story 22.8: the repo-defaults layer (AD-16 layer 2) composes here too
    # -- `harness_preference` is repo-expressed on this machine
    # (`_bmad-output/policy-defaults.toml`). An unreadable file degrades to
    # an empty layer, the same silent-tolerant posture this helper already
    # takes for the project layer (run_config is the loud boundary).
    repo_defaults, _repo_finding = read_repo_policy_defaults()
    project_data: dict[str, object] = {}
    candidate = conventional_project_policy_path(slug)
    if candidate.is_file():
        try:
            project_data = dict(_read_project_policy(candidate))
        except PolicyIOError:
            project_data = {}
    effective, _findings = policy.compose(
        project_slug=slug,
        repo_defaults=repo_defaults,
        project=project_data,
        flags=dict(flags or {}),
    )
    return effective


def _surface_worktree_wip_before_dispatch(
    *,
    vcs: VcsPort,
    repo_root: Path,
    worktree: Path,
    baseline_head_sha: str,
) -> Finding | None:
    """Story 28.13 (CAP-15): report existing WIP before touching the worktree."""
    try:
        changed = vcs.changed_files(repo_root, worktree, base=baseline_head_sha)
    except VcsCommandError:
        return None
    if not changed:
        return None
    line_count: int | None
    try:
        patch = vcs.worktree_unified_patch(worktree, baseline_sha=baseline_head_sha)
        line_count = count_unified_diff_lines(patch)
    except VcsCommandError:
        line_count = None
    file_count = len(changed)
    detail = f"{file_count} changed file(s)"
    if line_count is not None:
        detail += f", {line_count} diff line(s)"
    else:
        detail += " (diff line count unavailable)"
    return Finding(
        code="MRS-DISP-036",
        severity=Severity.WARN,
        message=(f"worktree {worktree!r} already carries uncommitted changes before this dispatch proceeds: {detail}"),
    )


_SESSION_CHECK_ARGV = ("pixi", "run", "--frozen", "-e", "pyforge-guild", "steward", "session", "check", "--json")
_SESSION_CHECK_TIMEOUT_S = 60.0


def _surface_session_precondition_findings(*, process: ProcessPort, repo_root: Path) -> Finding | None:
    """Story 63.4 (spec-pyforge-steward CAP-5): shell ``steward session check
    --json`` right after ``repo_root`` resolves and fold a non-ok
    session-precondition verdict (pixi/pyforge-guild, bmad-method drift, the
    token-economy kit + codegraph index, gh auth/rate-limit, the Tier-3
    sprint-status feed) into a WARN finding -- non-blocking, mirroring
    ``_surface_worktree_wip_before_dispatch``'s shape. Never escalated to
    ERROR: a session-precondition gap is worth flagging before a dispatch
    launches, not worth refusing the launch over.
    """
    try:
        result = process.run(list(_SESSION_CHECK_ARGV), cwd=repo_root, timeout_s=_SESSION_CHECK_TIMEOUT_S)
    except ProcessError as exc:
        return Finding(
            code="MRS-DISP-049",
            severity=Severity.WARN,
            message=f"steward session check could not run: {exc} -- session preconditions unverified",
        )
    if result.returncode == 0:
        return None
    detail: str
    try:
        payload = json.loads(result.stdout)
        non_ok = [row.get("name", "?") for row in payload.get("findings", []) if not row.get("ok", True)]
        detail = f"non-ok findings: {', '.join(non_ok)}" if non_ok else "reported findings"
    except json.JSONDecodeError, AttributeError, TypeError:
        tail_lines = (result.stderr or result.stdout or "").strip().splitlines()
        detail = tail_lines[-1] if tail_lines else "steward session check reported findings"
    return Finding(
        code="MRS-DISP-049",
        severity=Severity.WARN,
        message=f"steward session check reported a non-ok session-precondition verdict: {detail}",
    )


def _seed_dispatch_output_layer(*, fs: FsPort, worktree: Path, context_payload: Mapping[str, object]) -> Finding | None:
    """Story 28.30 (CAP-3, dispatch half of the ``output`` layer): deploy
    the caveman output-compression skill into a fresh dispatch worktree
    when ``[context].output`` is enabled.

    Reuses ``seed/verbs/kit.py``'s own packaged-payload resolution
    (``probe_instrument``) and render step (``render_deployed_skill``) --
    the loop-home APPLY step itself (``_apply_caveman_skill``) is out of
    reach here: ``seed/``'s AD-11 write boundary is scoped to a loop home,
    and a dispatch worktree is not one, so this function writes directly
    through the same ``FsPort`` the rest of ``dispatch_once`` already uses.

    Never raises: an unavailable instrument or any write failure degrades
    to a named WARN finding -- Story 28.3's own
    ``kit-instrument-unavailable``/``kit-item-missing`` degrade shape --
    and the caller proceeds with the session unwrapped either way, matching
    every other layer's "an unavailable instrument disables its layer with
    a named finding, never blocks a run" contract. A layer declared off
    (the default) deploys nothing -- today's behavior, byte-identical."""
    item = kit_item(KitItemId.CAVEMAN_SKILL)
    layer = context_payload.get(item.layer)
    if not isinstance(layer, Mapping) or not layer.get("enabled", False):
        return None
    probe = probe_instrument(item)
    if not probe.available or probe.payload is None:
        return Finding(
            code="MRS-DISP-042",
            severity=Severity.WARN,
            message=(
                f"the {item.layer!r} layer is enabled but "
                f"{probe.reason or 'its instrument payload did not resolve'} -- "
                "this dispatch session runs unwrapped"
            ),
        )
    try:
        upstream = probe.payload.read_text(encoding="utf-8")
        model_version = packaged_seed_model_version()
        target = worktree / item.relpath
        fs.ensure_dir(target.parent)
        fs.write_text_atomic(target, render_deployed_skill(upstream, model_version))
    except (OSError, UnicodeDecodeError, ValueError, PyforgeError) as exc:
        return Finding(
            code="MRS-DISP-042",
            severity=Severity.WARN,
            message=(
                f"could not deploy the caveman {item.layer!r}-layer skill into "
                f"{worktree!r}: {type(exc).__name__}: {exc} -- this dispatch "
                "session runs unwrapped"
            ),
        )
    return None


def _spec_text_prefer_worktree(spec_path: Path, repo_root: Path, worktree: Path, main_text: str) -> str:
    """Prefer the worktree copy: main often still says ready-for-dev."""
    try:
        worktree_spec = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree)
    except ValueError:
        return main_text
    try:
        if worktree_spec.is_file():
            return worktree_spec.read_text(encoding="utf-8")
    except OSError:
        return main_text
    return main_text


def _verification_verdict_for_cap4(
    *,
    slug: str,
    story_key: StoryKey,
    worktree: Path,
    repo_root: Path,
    effective_policy: policy.EffectivePolicy,
    spec_text: str,
    process: ProcessPort,
    vcs: VcsPort,
) -> DispatchVerificationVerdict:
    """Independent verify only — never a harness self-report (CAP-3)."""
    try:
        envelope = evaluate_dispatch_verification(
            project_slug=slug,
            story_key=story_key,
            worktree=worktree,
            repo_root=repo_root,
            effective=effective_policy,
            spec_text=spec_text,
            process=process,
            vcs=vcs,
        )
    except ProcessError, VcsCommandError, OSError, TypeError, AttributeError:
        return DispatchVerificationVerdict.REFUSED
    return judge_dispatch_verification(DispatchVerificationInput(findings=tuple(envelope.findings)))


def _attempt_harness_done_cap4(
    *,
    slug: str,
    story_key: StoryKey,
    worktree: Path,
    repo_root: Path,
    effective_policy: policy.EffectivePolicy,
    spec_text: str,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
) -> tuple[DispatchLandingVerdict, str, object]:
    """Compose with the existing CAP-4 land path — never a second lander."""
    verification = _verification_verdict_for_cap4(
        slug=slug,
        story_key=story_key,
        worktree=worktree,
        repo_root=repo_root,
        effective_policy=effective_policy,
        spec_text=spec_text,
        process=process,
        vcs=vcs,
    )
    result, envelope = execute_dispatch_land(
        project_slug=slug,
        story_key=render_feed_key(story_key),
        worktree=worktree,
        repo_root=repo_root,
        verification_verdict=verification,
        effective=effective_policy,
        fs=fs,
        vcs=vcs,
        process=process,
    )
    named = envelope.data.get("pr_url")
    if named is None and result.pr_number is not None:
        named = f"PR #{result.pr_number}"
    if named is None:
        named = str(worktree)
    return result.verdict, str(named), envelope


def _latest_story_run_dir(fs: FsPort, repo_root: Path, slug: str, story_key: str) -> Path | None:
    feed_story = render_feed_key(normalize(story_key))
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key == feed_story:
            return run_dir
    return None


def _redispatch_blocked_pending_supervisor_finalize(
    *,
    fs: FsPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    worktree: Path,
) -> str | None:
    """Story 28.24: refuse redispatch over MRS-DISP-036 dirt until finalize."""
    run_dir = _latest_story_run_dir(fs, repo_root, slug, story_key)
    if run_dir is None:
        return None
    journal_path = run_dir / _JOURNAL_FILENAME
    text = fs.read_text(journal_path)
    if text is None:
        return None
    folded = fold(text.splitlines())
    if finalize_attempt_journaled(folded, run_dir.name):
        return None
    journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
    if journal.worktree_path is not None and Path(journal.worktree_path) != worktree:
        return None
    if journal.completion_verdict == DispatchSessionVerdict.COMPLETED.value:
        return None
    return (
        f"worktree {worktree!r} carries uncommitted changes from run "
        f"{run_dir.name!r}; supervisor finalize (commit/push/verify) has "
        "not been attempted yet — redispatch blocked (Story 28.24)"
    )


def gather_fleet_finalize_escalations(
    *,
    fs: FsPort,
    repo_root: Path,
) -> dict[str, dispatch_fleet.FinalizeEscalation]:
    """Active supervisor-finalize shell failures (Story 28.24, CAP-7).

    Examines only the newest dispatch run per station (Story 28.25) -- an
    older failed finalize that a later run has since superseded is not an
    active escalation, so the search does not walk past it. A failure whose
    worktree has since been removed (e.g. a manual push+PR recovery) is
    likewise treated as resolved rather than reported forever.
    """
    escalations: dict[str, dispatch_fleet.FinalizeEscalation] = {}
    for slug in dispatch_core.list_station_slugs(repo_root):
        feed_slug = dispatch_fleet.normalize_station_slug(slug)
        run_dir = latest_dispatch_run_dir(repo_root, slug)
        if run_dir is None:
            continue
        journal_path = run_dir / _JOURNAL_FILENAME
        text = fs.read_text(journal_path)
        if text is None:
            continue
        folded = fold(text.splitlines())
        if not finalize_attempt_failed(folded, run_dir.name):
            continue
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key is None:
            continue
        worktree = finalize_failure_worktree_path(folded, run_dir.name)
        if worktree is None:
            worktree = journal.worktree_path
        if worktree is None:
            continue
        if not Path(worktree).is_dir():
            continue
        escalations[feed_slug] = dispatch_fleet.FinalizeEscalation(
            story=journal.story_key,
            worktree_path=worktree,
        )
    return escalations


def _last_failed_dispatch_session_log(fs: FsPort, repo_root: Path, slug: str, story_key: str) -> str | None:
    feed_story = render_feed_key(normalize(story_key))
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key != feed_story:
            continue
        if journal.completion_verdict != DispatchSessionVerdict.FAILED.value:
            return None
        return fs.read_text(run_dir / _LOG_FILENAME)
    return None


def _count_prior_failed_dispatch_attempts(fs: FsPort, repo_root: Path, slug: str, story_key: str) -> int:
    """Count failed dispatch runs for this story since the last completion.

    Story 33.6 (CAP-2): mirrors spin's per-run struggle counter — a
    successful completion resets the streak so an old failure history does
    not floor-raise an unrelated later retry.
    """
    feed_story = render_feed_key(normalize(story_key))
    count = 0
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key != feed_story:
            continue
        if journal.completion_verdict == DispatchSessionVerdict.COMPLETED.value:
            break
        if journal.completion_verdict == DispatchSessionVerdict.FAILED.value:
            count += 1
    return count


@dataclass(frozen=True)
class DispatchWorktreeResolution:
    """A provisioned dispatch worktree, or the refusal that stopped it (22.9)."""

    branch: str
    worktree: Path | None = None
    legacy: bool = False
    refusal: str | None = None


def _ensure_dispatch_worktree(vcs: VcsPort, repo_root: Path, slug: str, story_key: str) -> DispatchWorktreeResolution:
    """Provision (or reuse) this station's dispatch worktree.

    Story 22.9: the branch carries the station, so two stations sharing a
    story key can no longer resolve each other's tree. A pre-22.9
    ``marshal/<key>`` branch is still reused when git shows it checked out
    at THIS station's dispatch worktree; otherwise it refuses loudly with
    the land-first remedy rather than attaching to a tree it cannot
    attribute.
    """
    # Derive the attribution path ONCE and hand it to the resolver, rather
    # than letting the resolver compute its own default and recomputing the
    # same thing here -- the other two callers already pass `worktree=`
    # explicitly, and a single basis cannot drift from itself.
    worktree = dispatch_core.dispatch_worktree_path(repo_root, slug, story_key)
    resolution = dispatch_core.resolve_dispatch_branch(
        vcs, repo_root, slug=slug, story_key=story_key, worktree=worktree
    )
    if resolution.refusal is not None:
        return DispatchWorktreeResolution(branch=resolution.branch, refusal=resolution.refusal)
    branch = resolution.effective_branch
    existing = vcs.worktree_path_for_branch(repo_root, branch)
    if existing is not None:
        return DispatchWorktreeResolution(branch=branch, worktree=existing, legacy=resolution.legacy)
    if worktree.exists():
        return DispatchWorktreeResolution(branch=branch, worktree=worktree, legacy=resolution.legacy)
    vcs.add_worktree(repo_root, worktree, branch, base=_BASE_REF)
    return DispatchWorktreeResolution(branch=branch, worktree=worktree, legacy=resolution.legacy)


#: Parallel-wave journals live under ``dispatch-runs/waves/<wave-id>/``
#: (Story 28.16). That container must never be treated as a per-story run
#: dir: sorted-by-name, ``waves`` sorts after every ``<slug>-<ts>-<hex>``
#: run id, so ``latest_dispatch_run_dir`` would otherwise return the empty
#: container and ``marshal status`` / ``fleet-picture`` go blind to a live
#: headroom/claude session (found 2026-09-18 on pyforge-marshal 46.4).
_DISPATCH_WAVES_DIRNAME = "waves"


def iter_dispatch_run_dirs(repo_root: Path, slug: str) -> tuple[Path, ...]:
    runs_parent = dispatch_core.dispatch_runs_dir(repo_root, slug)
    if not runs_parent.is_dir():
        return ()
    return tuple(
        sorted(
            (
                p
                for p in runs_parent.iterdir()
                if p.is_dir() and p.name != _DISPATCH_WAVES_DIRNAME and (p / _JOURNAL_FILENAME).is_file()
            ),
            key=lambda p: p.name,
        )
    )


def latest_dispatch_run_dir(repo_root: Path, slug: str) -> Path | None:
    dirs = iter_dispatch_run_dirs(repo_root, slug)
    if not dirs:
        return None
    return dirs[-1]


def gather_dispatch_journal_facts(fs: FsPort, run_dir: Path, run_id: str) -> dispatch_core.DispatchJournalFacts:
    journal_path = run_dir / _JOURNAL_FILENAME
    text = fs.read_text(journal_path)
    if text is None:
        return dispatch_core.DispatchJournalFacts(
            story_key=None,
            session_pid=None,
            model=None,
            launched_at=None,
            worktree_path=None,
        )
    lines = text.splitlines()
    sidecars = sidecar_texts_for_lines(
        lines,
        read_sidecar=lambda ref: fs.read_text(run_dir / ref),
    )
    folded = fold(lines, sidecars=sidecars)
    story_key: str | None = None
    session_pid: int | None = None
    model: str | None = None
    worktree_path: str | None = None
    launched_at: datetime | None = None
    baseline_head_sha: str | None = None
    supervisor_pid: int | None = None
    completion_verdict: str | None = None
    completion_stop_reason: str | None = None
    verification_verdict: str | None = None
    verification_failed_gate: str | None = None
    verification_scope_advisories: tuple[dict[str, object], ...] = ()
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.phase == Phase.INTENT:
            raw_story = entry.payload.get("story_key")
            story_key = raw_story if isinstance(raw_story, str) else None
            model_val = entry.payload.get("model")
            model = model_val if isinstance(model_val, str) else None
            wt = entry.payload.get("worktree_path")
            worktree_path = wt if isinstance(wt, str) else None
            baseline_val = entry.payload.get("baseline_head_sha")
            baseline_head_sha = baseline_val if isinstance(baseline_val, str) else None
            try:
                launched_at = datetime.fromisoformat(entry.ts.replace("Z", "+00:00"))
            except ValueError:
                launched_at = None
        elif entry.phase == Phase.OUTCOME:
            pid_val = entry.payload.get("session_pid")
            if isinstance(pid_val, int):
                session_pid = pid_val
            elif isinstance(pid_val, str) and pid_val.isdigit():
                session_pid = int(pid_val)
            sup_val = entry.payload.get("supervisor_pid")
            if isinstance(sup_val, int):
                supervisor_pid = sup_val
            elif isinstance(sup_val, str) and sup_val.isdigit():
                supervisor_pid = int(sup_val)
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_COMPLETION):
        if entry.phase == Phase.OUTCOME:
            verdict_val = entry.payload.get("verdict")
            if isinstance(verdict_val, str):
                completion_verdict = verdict_val
            stop_val = entry.payload.get("stop_reason")
            if isinstance(stop_val, str):
                completion_stop_reason = stop_val
    landing_verdict: str | None = None
    landing_findings: tuple[dict[str, object], ...] = ()
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAND):
        if entry.phase == Phase.OUTCOME:
            if entry.payload.get("ok"):
                verdict_val = entry.payload.get("verdict")
                if isinstance(verdict_val, str):
                    landing_verdict = verdict_val
            # Story 53.2 review (I1): read regardless of `ok` -- a refused
            # landing (MRS-DISP-048) is exactly the case this must surface.
            landing_findings = resolve_land_findings_from_payload(entry.payload)
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION):
        if entry.phase == Phase.OUTCOME:
            vval = entry.payload.get("verdict")
            if isinstance(vval, str):
                verification_verdict = vval
            gate_val = entry.payload.get("failed_gate")
            if isinstance(gate_val, str):
                verification_failed_gate = gate_val
            # Story 28.15 (CAP-17): best-effort, matching every other
            # journal-payload read in this function -- a malformed/missing
            # entry degrades to the empty tuple rather than raising, never
            # a fabricated advisory.
            verification_scope_advisories = resolve_scope_violation_advisories_from_payload(
                entry.payload, sidecars=sidecars
            )
    story_started_at: str | None = None
    story_ended_at: str | None = None
    baseline_revision: str | None = None
    final_revision: str | None = None
    preserve_ref: str | None = None
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_TIMING):
        if entry.phase == Phase.OUTCOME:
            raw_started = entry.payload.get("story_started_at")
            if isinstance(raw_started, str):
                story_started_at = raw_started
            raw_ended = entry.payload.get("story_ended_at")
            if isinstance(raw_ended, str):
                story_ended_at = raw_ended
            raw_baseline = entry.payload.get("baseline_revision")
            if isinstance(raw_baseline, str):
                baseline_revision = raw_baseline
            raw_final = entry.payload.get("final_revision")
            if isinstance(raw_final, str):
                final_revision = raw_final
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_PRESERVE):
        if entry.phase == Phase.OUTCOME:
            raw_ref = entry.payload.get("preserve_ref")
            if isinstance(raw_ref, str):
                preserve_ref = raw_ref
    if baseline_revision is None and baseline_head_sha is not None:
        baseline_revision = baseline_head_sha
    if story_started_at is None and launched_at is not None:
        story_started_at = _format_entry_ts(launched_at)
    return dispatch_core.DispatchJournalFacts(
        story_key=story_key,
        session_pid=session_pid,
        model=model,
        launched_at=launched_at,
        worktree_path=worktree_path,
        baseline_head_sha=baseline_head_sha,
        supervisor_pid=supervisor_pid,
        completion_verdict=completion_verdict,
        completion_stop_reason=completion_stop_reason,
        verification_verdict=verification_verdict,
        verification_failed_gate=verification_failed_gate,
        verification_scope_advisories=verification_scope_advisories,
        landing_verdict=landing_verdict,
        landing_findings=landing_findings,
        story_started_at=story_started_at,
        story_ended_at=story_ended_at,
        baseline_revision=baseline_revision,
        final_revision=final_revision,
        preserve_ref=preserve_ref,
    )


def resolve_dispatch_session_verdict(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    journal: dispatch_core.DispatchJournalFacts,
    effective_policy: policy.EffectivePolicy,
    run_dir: Path | None = None,
    spec_relative_path: str | None = None,
) -> DispatchSessionVerdict | None:
    if journal.completion_verdict in {
        DispatchSessionVerdict.COMPLETED.value,
        DispatchSessionVerdict.FAILED.value,
        DispatchSessionVerdict.STOPPED_EXTERNALLY.value,
        # Story 51.11 (CAP-258): an already-committed `blocked` verdict must
        # not be re-derived from fresh git facts, which would re-introduce
        # the exact bug this story fixes (stale facts read STOPPED_EXTERNALLY).
        DispatchSessionVerdict.BLOCKED.value,
    }:
        return DispatchSessionVerdict(journal.completion_verdict)
    from ..core.dispatch_supervisor_state import landing_journal_indicates_complete

    if landing_journal_indicates_complete(journal.landing_verdict):
        return DispatchSessionVerdict.COMPLETED
    if journal.story_key is None or journal.worktree_path is None:
        return None
    session_alive = journal.session_pid is not None and process.is_alive(journal.session_pid)
    if journal.baseline_head_sha is None:
        return DispatchSessionVerdict.LIVE if session_alive else None
    try:
        git_facts = gather_dispatch_git_facts(
            vcs,
            fs=fs,
            repo_root=repo_root,
            worktree=Path(journal.worktree_path),
            story_key=journal.story_key,
            project_slug=slug,
            baseline_head_sha=journal.baseline_head_sha,
            merge_subject_template=effective_policy.merge_subject_template.value,
        )
    except VcsCommandError, ValueError:
        return DispatchSessionVerdict.LIVE if session_alive else None
    session_log: str | None = None
    if run_dir is not None:
        session_log = fs.read_text(run_dir / _LOG_FILENAME)
    return resolve_terminal_session_verdict(
        session_alive=session_alive,
        git=git_facts,
        verification_verdict=journal.verification_verdict,
        detach_reason=journal.completion_stop_reason,
        session_log=session_log,
        spec_relative_path=spec_relative_path,
    )


def _live_dispatch_evidence(
    *,
    journal: dispatch_core.DispatchJournalFacts,
    verdict: DispatchSessionVerdict,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    effective_policy: policy.EffectivePolicy,
    harness_reported_failure: bool = False,
) -> str:
    story_key = journal.story_key or "unknown"
    if journal.baseline_head_sha is None or journal.worktree_path is None:
        return (
            zombie_redispatch_evidence(
                story_key=story_key,
                verdict=verdict,
                git=DispatchGitFacts(
                    baseline_head_sha="",
                    current_head_sha="",
                    changed_paths=(),
                    branch_merged=False,
                    story_merged_on_main=False,
                ),
                session_alive=journal.session_pid is not None and process.is_alive(journal.session_pid),
                harness_reported_failure=harness_reported_failure,
            )
            or f"story {story_key!r} dispatch session is still live"
        )
    git_facts = gather_dispatch_git_facts(
        vcs,
        fs=fs,
        repo_root=repo_root,
        worktree=Path(journal.worktree_path),
        story_key=journal.story_key,
        project_slug=slug,
        baseline_head_sha=journal.baseline_head_sha,
        merge_subject_template=effective_policy.merge_subject_template.value,
    )
    return (
        zombie_redispatch_evidence(
            story_key=story_key,
            verdict=verdict,
            git=git_facts,
            session_alive=journal.session_pid is not None and process.is_alive(journal.session_pid),
            harness_reported_failure=harness_reported_failure,
        )
        or f"story {story_key!r} dispatch session is still live"
    )


def _epics_path(repo_root: Path, slug: str) -> Path:
    return (
        dispatch_core.canonical_repo_root(repo_root)
        / "_bmad-output"
        / "projects"
        / slug
        / "planning-artifacts"
        / "epics.md"
    )


def _load_station_deps_graph(repo_root: Path, slug: str) -> dict[str, tuple]:
    path = _epics_path(repo_root, slug)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return story_deps_from_epics(text)


def _effective_surface_for_spec(
    *,
    spec_text: str,
    story_key: StoryKey,
    slug: str,
    effective_policy: policy.EffectivePolicy,
) -> tuple[str, ...] | None:
    """Effective frozen surface for wave/conflict checks (AD-27).

    Returns ``None`` when the spec's surface declaration is unsupported
    (multi-line YAML block) -- conservative: never fan out unknown surfaces.
    """
    try:
        spec_surface = parse_declared_surface(spec_text)
    except SurfaceParseError:
        return None
    policy_surface = gate.resolve_policy_surface(effective_policy.epic_surfaces.value, story_key.epic, slug)
    return gate.compute_effective_surface(policy_surface, spec_surface)


def resolve_max_parallel(
    effective_policy: policy.EffectivePolicy,
    *,
    cli_override: int | None = None,
    policy_flags: dict[str, object] | None = None,
) -> int:
    """Factory-dispatch parallel cap (Story 28.16, CAP-4; Story 33.8, CAP-6).

    Reads ``dispatch.max_parallel`` only -- never bmad-loop scm
    ``max_parallel`` (SEED). Default serial (=1)."""
    del policy_flags  # compose() already merged flags into ``effective_policy``.
    if cli_override is not None:
        return max(1, int(cli_override))
    dispatch_block = effective_policy.dispatch.value
    if not isinstance(dispatch_block, Mapping):
        return 1
    raw = dispatch_block.get("max_parallel", 1)
    validated = policy._valid_parallel_count(raw)
    return max(1, int(validated if validated is not None else 1))


def _live_dispatch_story_keys(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    effective_policy: policy.EffectivePolicy,
) -> tuple[str, ...]:
    """Every LIVE factory-dispatch story key on ``slug`` (Story 28.16)."""
    live: list[str] = []
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key is None:
            continue
        verdict = resolve_dispatch_session_verdict(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
            run_dir=run_dir,
        )
        if verdict == DispatchSessionVerdict.LIVE:
            live.append(journal.story_key)
    return tuple(live)


def station_finalize_pending_story(
    *,
    fs: FsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    backlog: Sequence[str],
    effective_policy: policy.EffectivePolicy,
) -> tuple[str, str] | None:
    """``(story, evidence)`` when this station's head is mid-finalize (50.1).

    Part A's impure half: walk the MOST RECENT dispatch run, read the four
    facts the journal already carries (``story_key``, ``supervisor_pid``,
    ``completion_verdict``, ``landing_verdict``), and hand them plus the
    tracked-ledger fact to the pure ``is_finalize_pending``.

    This is deliberately NOT a second completion judgment:
    ``resolve_dispatch_session_verdict`` / ``judge_dispatch_completion``
    are untouched, and nothing here reads the session's own self-report.
    ``spin``'s in-flight probe has treated a live ``supervisor_pid`` as in
    flight since Story 34.1; the dispatch path simply never learned it.
    """
    # The verdict stays on journal + process facts (Epic 50 HARD boundary);
    # the policy is accepted for call-site symmetry with every other
    # station-level probe, never consulted.
    del effective_policy
    from ..core.dispatch_supervisor_state import landing_journal_indicates_complete

    run_dir = latest_dispatch_run_dir(repo_root, slug)
    if run_dir is None:
        return None
    journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
    if journal.story_key is None:
        return None
    on_backlog: str | None = None
    for raw in backlog:
        try:
            if render_feed_key(normalize(raw)) == journal.story_key:
                on_backlog = raw
                break
        except MalformedStoryKeyError:
            continue
    supervisor_alive = journal.supervisor_pid is not None and process.is_alive(journal.supervisor_pid)
    landing_complete = landing_journal_indicates_complete(journal.landing_verdict)
    session_alive = journal.session_pid is not None and process.is_alive(journal.session_pid)
    if session_alive and not landing_complete:
        # A session still running is plain in-flight, not finalize-pending:
        # CAP-2's own verdict already reads LIVE and the MRS-DISP-011 relay
        # reports it. Clause (a) is about the window AFTER the session exits,
        # so it must never pre-empt that already-correct path.
        return None
    if not dispatch_fleet.is_finalize_pending(
        supervisor_alive=supervisor_alive,
        completion_journaled=journal.completion_verdict is not None,
        landing_complete=landing_complete,
        story_on_backlog=on_backlog is not None,
    ):
        return None
    assert on_backlog is not None
    if landing_complete:
        evidence = (
            f"run {run_dir.name!r} journaled dispatch-land "
            f"{journal.landing_verdict!r} and the tracked ledger still says "
            "backlog -- finalize (ledger sync + spec promotion) is mid-flight"
        )
    else:
        evidence = (
            f"run {run_dir.name!r} has a live supervisor "
            f"(pid {journal.supervisor_pid}) and no dispatch-completion "
            "entry -- the landing path has not finished"
        )
    return on_backlog, evidence


def station_in_flight_conflict(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
    harness_reported_failure: bool = False,
    candidate_spec_text: str | None = None,
    deps_graph: Mapping[str, tuple] | None = None,
    parallel_dispatch: bool = False,
) -> DispatchPreflightConflict | None:
    """Refuse when an in-flight story blocks this candidate (22.5 / 28.16).

    Story 28.16 narrows the 22.5 guard when ``parallel_dispatch`` is true:
    unrelated LIVE stories with disjoint surfaces do NOT refuse. With
    ``parallel_dispatch`` false (``max_parallel`` unset or ``1``), behavior
    stays byte-identical to today's serial drain (``MRS-DISP-021`` on any
    other LIVE story).
    """
    feed_story = render_feed_key(normalize(story_key))
    candidate_surface: tuple[str, ...] | None = None
    if candidate_spec_text is not None:
        try:
            candidate_surface = _effective_surface_for_spec(
                spec_text=candidate_spec_text,
                story_key=normalize(story_key),
                slug=slug,
                effective_policy=effective_policy,
            )
        except ValueError:
            candidate_surface = None
    graph = dict(deps_graph or {})
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key is None:
            continue
        verdict = resolve_dispatch_session_verdict(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
            run_dir=run_dir,
        )
        if verdict != DispatchSessionVerdict.LIVE:
            continue
        evidence = _live_dispatch_evidence(
            journal=journal,
            verdict=verdict,
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            effective_policy=effective_policy,
            harness_reported_failure=harness_reported_failure,
        )
        in_flight = journal.story_key
        if in_flight == feed_story:
            return DispatchPreflightConflict(
                code="MRS-DISP-011",
                message=f"refusing redispatch: {evidence}",
                in_flight_story_key=in_flight,
            )
        if not parallel_dispatch:
            return DispatchPreflightConflict(
                code="MRS-DISP-021",
                message=(f"refusing dispatch: station {slug!r} already has in-flight story {in_flight!r} ({evidence})"),
                in_flight_story_key=in_flight,
            )
        if story_transitively_depends_on(feed_story, in_flight, graph):
            return DispatchPreflightConflict(
                code="MRS-DISP-035",
                message=(
                    f"refusing dispatch: story {feed_story!r} depends on in-flight story {in_flight!r} ({evidence})"
                ),
                in_flight_story_key=in_flight,
            )
        if candidate_surface is not None:
            in_flight_spec = dispatch_core.resolve_story_spec_path(repo_root, slug, in_flight)
            if in_flight_spec is not None:
                try:
                    in_flight_text = in_flight_spec.read_text(encoding="utf-8")
                except OSError:
                    in_flight_text = None
                if in_flight_text is not None:
                    in_flight_surface = _effective_surface_for_spec(
                        spec_text=in_flight_text,
                        story_key=normalize(in_flight),
                        slug=slug,
                        effective_policy=effective_policy,
                    )
                    overlapping = dispatch_core.find_declared_surface_overlaps(candidate_surface, in_flight_surface)
                    if overlapping:
                        pair_desc = ", ".join(f"{left!r} ∩ {right!r}" for left, right in overlapping)
                        paths = tuple(f"{left} ∩ {right}" for left, right in overlapping)
                        return DispatchPreflightConflict(
                            code="MRS-DISP-034",
                            message=(
                                f"refusing dispatch: effective surfaces of "
                                f"{feed_story!r} and in-flight {in_flight!r} "
                                f"intersect ({pair_desc}); {evidence}"
                            ),
                            in_flight_story_key=in_flight,
                            overlap_paths=paths,
                        )
    return None


def _iter_spin_run_dirs(home: Path, slug: str) -> tuple[Path, ...]:
    """Marshal spin run directories under a loop home (Story 34.1).

    Mirrors ``cli/spin.py::_latest_run_dir``'s own glob location and sort
    order, but returns every matching directory so a guard can walk newest-
    first rather than inspecting only the lexicographically latest id.
    """
    runs_dir = home / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs"
    try:
        return tuple(
            sorted(
                (path for path in runs_dir.glob(f"{slug}-*") if path.is_dir()),
                key=lambda path: path.name,
            )
        )
    except OSError:
        return ()


def spin_loop_home_in_flight_conflict(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    harness: HarnessPort,
    home: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
) -> DispatchPreflightConflict | None:
    """Refuse ``factory spin`` when this loop home already has a live run (34.1).

    A narrowed call into ``station_in_flight_conflict`` for live factory-
    dispatch sessions on the SAME home, then the spin-specific ``runs/``
    journals dispatch's guard does not walk. Reuses ``DispatchPreflightConflict``
    and ``MRS-DISP-021`` -- never a second, independently-drifting guard.
    """
    dispatch_conflict = station_in_flight_conflict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=home,
        slug=slug,
        story_key=story_key,
        effective_policy=effective_policy,
        parallel_dispatch=False,
    )
    if dispatch_conflict is not None:
        return dispatch_conflict

    from .status import _gather_run_journal_facts

    for run_dir in reversed(_iter_spin_run_dirs(home, slug)):
        run_id = run_dir.name
        journal_facts = _gather_run_journal_facts(fs, run_dir, run_id)
        launch_pid = journal_facts.launch_pid
        supervisor_pid = journal_facts.supervisor_pid
        launch_alive = launch_pid is not None and process.is_alive(launch_pid)
        supervisor_alive = supervisor_pid is not None and process.is_alive(supervisor_pid)
        if not launch_alive and not supervisor_alive:
            continue
        harness_run_id = journal_facts.harness_run_id
        snapshot = harness.run_status_snapshot(home, harness_run_id) if harness_run_id else None
        if snapshot is not None and snapshot.finished:
            continue
        evidence_parts = [f"run {run_id!r}"]
        if launch_pid is not None:
            evidence_parts.append(f"pid {launch_pid}")
        if supervisor_pid is not None:
            evidence_parts.append(f"supervisor pid {supervisor_pid}")
        evidence = ", ".join(evidence_parts)
        return DispatchPreflightConflict(
            code="MRS-DISP-021",
            message=(f"refusing spin: station {slug!r} already has in-flight spin ({evidence})"),
            in_flight_story_key=run_id,
        )
    return None


def cross_station_surface_overlap_advisories(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    requested_slug: str,
    requested_story_key: str,
    requested_spec_text: str,
) -> tuple[Finding, ...]:
    """Loud WARN advisories for overlapping declared surfaces (Story 22.5)."""
    requested_surface = parse_declared_surface(requested_spec_text)
    feed_requested = render_feed_key(normalize(requested_story_key))
    advisories: list[Finding] = []
    for station_slug in dispatch_core.list_station_slugs(repo_root):
        station_policy = _compose_policy(station_slug)
        for run_dir in reversed(iter_dispatch_run_dirs(repo_root, station_slug)):
            journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
            if journal.story_key is None:
                continue
            if station_slug == requested_slug and journal.story_key == feed_requested:
                continue
            verdict = resolve_dispatch_session_verdict(
                fs=fs,
                vcs=vcs,
                process=process,
                repo_root=repo_root,
                slug=station_slug,
                journal=journal,
                effective_policy=station_policy,
                run_dir=run_dir,
            )
            if verdict != DispatchSessionVerdict.LIVE:
                continue
            in_flight_spec = dispatch_core.resolve_story_spec_path(repo_root, station_slug, journal.story_key)
            if in_flight_spec is None:
                continue
            try:
                in_flight_text = in_flight_spec.read_text(encoding="utf-8")
            except OSError:
                continue
            in_flight_surface = parse_declared_surface(in_flight_text)
            overlapping = dispatch_core.find_declared_surface_overlaps(requested_surface, in_flight_surface)
            if not overlapping:
                continue
            advisories.append(
                Finding(
                    code="MRS-DISP-022",
                    severity=Severity.WARN,
                    message=dispatch_core.format_surface_overlap_advisory(
                        in_flight_station=station_slug,
                        in_flight_story_key=journal.story_key,
                        requested_station=requested_slug,
                        requested_story_key=feed_requested,
                        overlapping=overlapping,
                    ),
                )
            )
            break
    return tuple(advisories)


def station_story_block_facts(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
) -> dispatch_fleet.StationBlockEvidence | None:
    """Evidence + environment/story classification for a blocked story (34.3).

    Story 22.7: the fleet driver needs to know "is this station's next story
    blocked?" without inventing a second completion judgment. It reuses
    CAP-2's own verdict resolution verbatim -- only the MOST RECENT run for
    that story counts, so a story that failed once and was later re-driven to
    ``live``/``completed`` is not treated as blocked forever.
    """
    feed_story = render_feed_key(normalize(story_key))
    for run_dir in reversed(iter_dispatch_run_dirs(repo_root, slug)):
        journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
        if journal.story_key != feed_story:
            continue

        # Story 51.4 (CAP-252): resolve the worktree's own tracked spec once
        # per run, before verdict resolution -- a deliberate `status: blocked`
        # (the 27.3 incident) or a diff that collapses to just that spec file
        # (narration, not work -- the 51.3 incident) must both read as
        # no-progress to `resolve_dispatch_session_verdict` itself, not only
        # to the block-reason checks below it (2026-09-19 review pass: the
        # original placement inside the `verdict == FAILED` branch meant
        # `resolve_dispatch_session_verdict`'s own `has_git_progress` call
        # never saw a narration-only diff as no-progress, so the campaign
        # could resolve LIVE/STOPPED_EXTERNALLY instead of FAILED for it).
        spec_status: str | None = None
        spec_blocking_condition: str | None = None
        spec_relative_path: str | None = None
        if journal.worktree_path is not None:
            worktree_path = Path(journal.worktree_path)
            spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, feed_story)
            if spec_path is not None:
                try:
                    worktree_spec_path = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree_path)
                except ValueError:
                    worktree_spec_path = None
                if worktree_spec_path is not None:
                    spec_text = fs.read_text(worktree_spec_path)
                    if spec_text is not None:
                        spec_status = parse_spec_status(spec_text)
                        spec_blocking_condition = parse_blocking_condition(spec_text)
                    try:
                        spec_relative_path = str(worktree_spec_path.resolve().relative_to(worktree_path.resolve()))
                    except ValueError:
                        spec_relative_path = None

        verdict = resolve_dispatch_session_verdict(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
            run_dir=run_dir,
            spec_relative_path=spec_relative_path,
        )
        if verdict == DispatchSessionVerdict.FAILED:
            session_log = fs.read_text(run_dir / _LOG_FILENAME)
            changed_path_count = 0
            git_progress_unknown = False
            git_changed_paths: tuple[str, ...] = ()
            if journal.worktree_path is not None and journal.baseline_head_sha:
                try:
                    git_facts = gather_dispatch_git_facts(
                        vcs,
                        fs=fs,
                        repo_root=repo_root,
                        worktree=Path(journal.worktree_path),
                        story_key=feed_story,
                        project_slug=slug,
                        baseline_head_sha=journal.baseline_head_sha,
                        merge_subject_template=effective_policy.merge_subject_template.value,
                    )
                    changed_path_count = len(git_facts.changed_paths)
                    git_changed_paths = git_facts.changed_paths
                except VcsCommandError, ValueError:
                    git_progress_unknown = True

            # Story 50.1 Part B: ahead of the transient/terminal split, so
            # an already-landed head is never re-dispatched (TRANSIENT) NOR
            # halts the station (TERMINAL) -- it advances, exactly the way
            # MRS-DISP-040 does. ``git_progress_unknown`` means the campaign
            # could not observe the changed paths at all, and an unobserved
            # zero is never treated as an observed one. Checked before the
            # blocked-spec check below (2026-09-19 review pass) so a worktree
            # that is both already-landed and carries a stale `blocked` spec
            # still reports the more definitive, terminal fact.
            if not git_progress_unknown and dispatch_fleet.is_already_landed_self_refusal(
                changed_path_count=changed_path_count,
                session_log=session_log,
            ):
                return dispatch_fleet.StationBlockEvidence(
                    reason=(
                        f"{dispatch_fleet.ALREADY_LANDED_ADVANCE_PREFIX}: the "
                        f"last dispatch of {feed_story!r} (run "
                        f"{run_dir.name!r}) refused itself with zero changed "
                        "paths and merged evidence in its session log -- the "
                        "work is already landed, so the station advances "
                        "instead of relaunching it"
                    ),
                    block_class=dispatch_fleet.FleetBlockClass.STORY,
                )

            # Story 51.4 (CAP-252): the worktree's own tracked spec may name
            # the block reason itself -- a deliberate `status: blocked` (the
            # 27.3 incident) surfaces here, before the transient/terminal
            # classification below.
            if spec_status == "blocked":
                return dispatch_fleet.StationBlockEvidence(
                    reason=(
                        f"the last dispatch of {feed_story!r} (run "
                        f"{run_dir.name!r}) left its tracked spec "
                        f"status: blocked (blocking condition: "
                        f"{spec_blocking_condition or 'not stated'})"
                    ),
                    block_class=dispatch_fleet.FleetBlockClass.STORY,
                )
            # Story 51.4 (CAP-252): a diff that collapses to just the
            # tracked spec file is narration, not work -- read it as
            # zero-progress here so a harness-ceiling termination (the
            # 51.3 incident) classifies TRANSIENT/re-dispatchable via the
            # existing session-log check below, not TERMINAL.
            classify_changed_path_count = changed_path_count
            if not git_progress_unknown and is_spec_only_narration(git_changed_paths, spec_relative_path):
                classify_changed_path_count = 0
            block_kind = classify_dispatch_block(
                session_log=session_log,
                failed_gate=journal.verification_failed_gate,
                changed_path_count=classify_changed_path_count,
            )
            if block_kind is DispatchBlockKind.TRANSIENT:
                return None
            gate = journal.verification_failed_gate
            detail = f", failed gate {gate}" if gate else ""
            reason = (
                f"the last dispatch of {feed_story!r} (run {run_dir.name!r}) "
                f"ended 'failed' by git and process facts{detail}"
            )
            block_class = dispatch_fleet.classify_fleet_block(
                changed_path_count=changed_path_count,
                has_review_verify_evidence=dispatch_fleet.has_review_verify_cycle_evidence(
                    verification_verdict=journal.verification_verdict,
                    verification_failed_gate=journal.verification_failed_gate,
                    completion_stop_reason=journal.completion_stop_reason,
                ),
            )
            if git_progress_unknown:
                block_class = dispatch_fleet.FleetBlockClass.STORY
            return dispatch_fleet.StationBlockEvidence(reason=reason, block_class=block_class)
        return None
    return None


def station_story_blocked_evidence(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
) -> str | None:
    facts = station_story_block_facts(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        effective_policy=effective_policy,
    )
    return facts.reason if facts is not None else None


def live_dispatch_conflict(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    story_key: str,
    effective_policy: policy.EffectivePolicy,
    harness_reported_failure: bool = False,
) -> str | None:
    """Same-story live redispatch refusal (Story 22.2); delegates to CAP-5 guard."""
    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        story_key=story_key,
        effective_policy=effective_policy,
        harness_reported_failure=harness_reported_failure,
    )
    if conflict is None or conflict.code != "MRS-DISP-011":
        return None
    return conflict.message.removeprefix("refusing redispatch: ")


def run_dispatch(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    build_harness: BuildHarnessPort | None = None,
    process: ProcessPort | None = None,
    harness: HarnessPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    """``marshal factory dispatch <slug> <story>`` -- or, with ``--stories``
    (Story 22.11, FR-193 CAP-10), a caller-supplied ordered sequence chained
    on this one station via ``run_fleet_drain``'s existing campaign machinery
    -- never a second preflight, landing, or campaign-journal path.
    """
    del context
    raw_story = getattr(args, "story", None)
    raw_stories = getattr(args, "stories", None)
    if raw_story and raw_stories:
        finding = Finding(
            code="MRS-DISP-032",
            severity=Severity.ERROR,
            message="pass exactly one of a `story` positional or `--stories` -- not both",
        )
        return _emit(args, {"slug": args.slug}, [finding])
    if not raw_story and not raw_stories:
        finding = Finding(
            code="MRS-DISP-032",
            severity=Severity.ERROR,
            message="pass exactly one of a `story` positional or `--stories`",
        )
        return _emit(args, {"slug": args.slug}, [finding])
    if raw_stories:
        # Extend the surface, don't fork it (the spec's own Approach): a
        # caller-supplied sequence is just `drain --mode drain_to_zero
        # --station <slug> --stories <raw_stories>` under the hood -- the
        # SAME chaining/preflight/journal machinery Story 22.7 built,
        # scoped to this one station's explicit list instead of its ledger
        # order.
        drain_args = argparse.Namespace(
            mode=dispatch_fleet.FleetCampaignMode.DRAIN_TO_ZERO.value,
            station=args.slug,
            stories=raw_stories,
            leave_remaining=0,
            once=False,
            max_cycles=0,
            tick_seconds=_FLEET_TICK_SECONDS,
            campaign=None,
            format=getattr(args, "format", "text"),
            harness=getattr(args, "harness", None),
            max_in_flight=getattr(args, "max_in_flight", None),
        )
        return run_fleet_drain(
            drain_args,
            fs=fs,
            vcs=vcs,
            build_harness=build_harness,
            process=process,
            harness=harness,
        )
    policy_flags = _policy_flags_from_harness_arg(getattr(args, "harness", None))
    attempt = dispatch_once(
        slug=args.slug,
        story=raw_story,
        fs=fs,
        vcs=vcs,
        build_harness=build_harness,
        process=process,
        policy_flags=policy_flags or None,
    )
    return _emit(args, dict(attempt.data), list(attempt.findings))


def dispatch_once(
    *,
    slug: str,
    story: str,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    build_harness: BuildHarnessPort | None = None,
    process: ProcessPort | None = None,
    policy_flags: dict[str, object] | None = None,
    parallel_dispatch: bool = False,
) -> DispatchAttempt:
    """Launch exactly one governed story session and report data + findings.

    The whole body of ``marshal factory dispatch`` minus its envelope
    rendering -- extracted verbatim (Story 22.7) so the fleet-drain mode can
    call the SAME primitive once per station per cycle instead of shelling
    out and re-parsing an envelope, or (worse) re-implementing the CAP-2
    zombie refusal, the CAP-5 per-station guard, or the CAP-5 cross-station
    overlap advisory. ``run_dispatch`` is now the thin argparse/emit shell
    over this function; its behavior is unchanged.
    """
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    build_harness = build_harness if build_harness is not None else BmadBuildHarness()
    process = process if process is not None else PosixProcess()

    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug, "story": story}

    def _done() -> DispatchAttempt:
        return DispatchAttempt(data=data, findings=tuple(findings))

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-DISP-001",
                severity=Severity.ERROR,
                message=f"malformed project slug {slug!r}",
            )
        )
        return _done()

    try:
        story_key = normalize(story)
    except ValueError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-002",
                severity=Severity.ERROR,
                message=f"malformed story key {story!r}: {exc}",
            )
        )
        return _done()
    data["story_key"] = render_feed_key(story_key)

    try:
        repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-004",
                severity=Severity.ERROR,
                message=f"cannot resolve repository root: {exc}",
            )
        )
        return _done()

    session_finding = _surface_session_precondition_findings(process=process, repo_root=repo_root)
    if session_finding is not None:
        findings.append(session_finding)

    scope_refusal = _dispatch_scope_refusal(repo_root, slug)
    if scope_refusal is not None:
        findings.append(scope_refusal)
        return _done()

    spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, story)
    if spec_path is None:
        findings.append(
            Finding(
                code="MRS-DISP-005",
                severity=Severity.ERROR,
                message=(
                    f"no tracked spec found for story {render_feed_key(story_key)!r} "
                    f"under {dispatch_core.planning_specs_dir(repo_root, slug)!r}"
                ),
            )
        )
        return _done()
    data["spec_path"] = str(spec_path)

    try:
        spec_text = spec_path.read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-005",
                severity=Severity.ERROR,
                message=f"cannot read spec {spec_path!r}: {exc}",
            )
        )
        return _done()

    effective_policy = _compose_policy(slug, flags=policy_flags)
    difficulty = dispatch_core.read_declared_difficulty(spec_text)
    session_log = _last_failed_dispatch_session_log(fs, repo_root, slug, render_feed_key(story_key))
    prior_failed_attempts = _count_prior_failed_dispatch_attempts(fs, repo_root, slug, render_feed_key(story_key))
    tier_resolution = dispatch_core.resolve_tier_harness(
        effective_policy,
        difficulty=difficulty,
        session_log=session_log,
    )
    model, escalated, from_model, to_model = dispatch_core.resolve_dispatch_model_with_retry_escalation(
        effective_policy,
        difficulty=difficulty,
        prior_failed_attempts=prior_failed_attempts,
    )
    budget_env = dispatch_core.build_budget_env(effective_policy)
    data["model"] = model
    data["budget_env"] = dict(budget_env)
    if escalated:
        data["escalated"] = True
        data["from_model"] = from_model
        data["to_model"] = to_model
    if tier_resolution.resolved_models:
        data["resolved_models"] = dict(tier_resolution.resolved_models)
    if tier_resolution.serving_pools:
        data["serving_pool"] = dict(tier_resolution.serving_pools)
    # Story 28.1 (SPEC-marshal-token-economy CAP-1): the SAME composition
    # site `adapters/harness_bmadloop.py::render_policy_toml` (bmad-loop
    # spin) resolves its `[context]` block from -- one function, both
    # engines. Story 28.2 (CAP-2) makes the `wire` entry of this SAME
    # payload load-bearing on this engine: it is handed to
    # `BuildHarnessPort.dispatch` below, which resolves the profile's
    # declared wrapper against it. Every other layer stays declaration-only
    # until its own story lands.
    context_payload = policy.resolve_context_layers(effective_policy)
    data["context"] = context_payload
    # Story 28.2 (CAP-2): seed the wire disposition to OFF here, the moment
    # the `[context]` payload it derives from exists, so `data["wire"]` is
    # present on EVERY envelope this verb can still emit -- including the
    # `BuildHarnessError` path below, which returns without ever reaching
    # the launch result and so used to omit the key from precisely the
    # envelope an operator most wants to inspect. `ports/build_harness.py`
    # promises the disposition is "a recorded fact of every dispatch", and
    # `cli/spin.py` echoes its own unconditionally; a key that is sometimes
    # absent makes every consumer guard a read that was specified not to
    # need one. Overwritten with the real decision once a launch returns.
    data["wire"] = harness_profile.WireWrap(applied=False).journal_payload()

    # Story 22.8 (FR-193 CAP-8): profile-aware harness resolution -- the
    # policy's ordered `harness_preference` walked to the first profile
    # whose binary resolves AND whose authcheck passes. Binary presence
    # alone was necessary-but-insufficient (2026-08-27: three real
    # dispatches died on cursor's auth wall with the binary on PATH), so
    # every skipped candidate is a structured finding, never silent.
    # Story 28.11 (CAP-12): when the tier map names a harness for dev,
    # that profile leads the walk instead of the flat preference alone.
    # Story 50.3 (CAP-246): an EXPLICIT `--harness` (the composed
    # `harness_preference` FLAG layer, never the default/repo/project
    # layer) outranks that tier-map lead -- the walk starts from the
    # flag's own profiles and a tier-map harness the flag does not name
    # contributes nothing to it. Without the flag (layer stays default/
    # repo_defaults/project) this is unchanged: the tier map still leads.
    preference = tuple(effective_policy.harness_preference.value)
    explicit_harness_flag = effective_policy.harness_preference.layer == policy.PolicyLayer.FLAG
    if tier_resolution.harness_profile is not None and not explicit_harness_flag:
        preference = (tier_resolution.harness_profile,) + tuple(
            name for name in preference if name != tier_resolution.harness_profile
        )
    preference = exclude_harness_profiles_after_transient_failure(preference, session_log)
    if not preference:
        preference = tuple(effective_policy.harness_preference.value)
    resolution = build_harness.binary_present(preference, repo_root=repo_root)
    for profile_error in resolution.profile_errors:
        findings.append(Finding(code="MRS-DISP-028", severity=Severity.WARN, message=profile_error))
    for skip in resolution.skipped:
        findings.append(
            Finding(
                code="MRS-DISP-027",
                severity=Severity.WARN,
                message=f"harness profile {skip.profile!r} skipped: {skip.reason}",
            )
        )
    if not resolution:
        tried = (
            "; ".join(f"{s.profile}: {s.reason}" for s in resolution.skipped)
            or "empty harness_preference -- no candidate to try"
        )
        findings.append(
            Finding(
                code="MRS-DISP-003",
                severity=Severity.ERROR,
                message=f"no dispatchable session-harness profile ({tried})",
            )
        )
        return _done()
    data["harness_profile"] = resolution.profile

    # 2026-09-12 (dispatch-tier-routing-fails-safe): the tier-mapped model
    # was resolved BEFORE this live binary+authcheck walk ran, from a
    # bare-string model_tier_map entry that carries no harness of its own
    # (see core/tier_routing.py::resolve_tier_launch) -- so it can name a
    # model that belongs to a DIFFERENT provider than whichever profile the
    # walk above actually landed on (harness_preference has no bmad-loop
    # counterpart, a candidate's auth/binary failed, a transient exclusion
    # kicked in, etc.). render_policy_toml (the bmad-loop `spin` engine)
    # already guards this same mismatch at render time; this is the SAME
    # guard for the `dispatch` engine, applied once the REAL harness is
    # known. A mismatch drops the model override entirely (never launches a
    # real, live-verified harness with a model it was never meant to
    # receive) rather than block the dispatch outright -- the harness's own
    # default model is always a safe fallback.
    resolved_provider = adapter_provider(resolution.profile)
    catalog = effective_policy.model_cost_catalog.value
    model_provider = provider_declaring_model(catalog, data["model"]) if data["model"] else None
    # Story 51.5 (CAP-253): `provider_declaring_model` returns `None` both
    # for a genuinely uncatalogued model id and, by documented design, for
    # the harness's own default/alias ids (`sonnet`/`opus`/`haiku` -- the
    # catalog is a declared PRICE snapshot, not a model registry, see
    # `is_harness_default_model`). The ORIGINAL guard below only fired on
    # the cross-provider case (`model_provider` names a DIFFERENT
    # provider); widen it so a model catalogued under NO provider at all,
    # and not one of the harness's own default/alias ids, ALSO WARNs --
    # a genuinely foreign or mistyped model id must not reach a live
    # launch uncaught -- while the cross-provider case and the harness's
    # own default/alias ids stay exactly as before.
    #
    # `provider_declaring_model` also returns `None` whenever NO catalog is
    # declared at all -- most stations (e.g. a cursor-only
    # `harness_preference` with no `model_cost_catalog` block) never
    # declare one. Without gating on `catalog_declared`, a correctly
    # tier-mapped, correctly resolved model on one of those stations reads
    # as "uncatalogued" too and gets its override dropped on every real
    # dispatch. There is nothing to compare against when no catalog was
    # ever declared, so that case must stay silent, same as pre-story --
    # only a DECLARED catalog that omits the model is suspicious.
    model_uncatalogued = (
        data["model"] is not None
        and model_provider is None
        and not is_harness_default_model(data["model"])
        and catalog_declared(catalog)
    )
    model_cross_provider = model_provider is not None and model_provider != resolved_provider
    if model_cross_provider or model_uncatalogued:
        if model_provider is not None:
            provider_clause = (
                f"is catalogued under provider {model_provider!r}, but the "
                f"live-verified harness {resolution.profile!r} resolves to "
                f"provider {resolved_provider!r}"
            )
        else:
            provider_clause = (
                "is catalogued under no known provider despite a declared "
                "cost catalog, and is not the live-verified harness "
                f"{resolution.profile!r}'s own default/alias model id"
            )
        findings.append(
            Finding(
                code="MRS-DISP-043",
                severity=Severity.WARN,
                message=(
                    f"tier-mapped model {data['model']!r} {provider_clause} "
                    "-- dropping the model override for this dispatch; the "
                    "harness's own default applies"
                ),
            )
        )
        # Story 50.3: `model` (not just `data["model"]`) must drop too --
        # it is what the intent journal entry and the live
        # `build_harness.dispatch(model=model, ...)` call below actually
        # use. Leaving the local variable at its mismatched value would
        # journal and LAUNCH the foreign-provider model even though the
        # envelope's own `data["model"]` correctly reported the drop.
        model = None
        # The escalation triple is read straight from these locals when the
        # intent entry is built further down (`if escalated: ...`) -- if
        # only `model` were reset, a run that had escalated before the
        # mismatch fired would journal `model: null` alongside a stale
        # `escalated: true`/`from_model`/`to_model`, a self-contradictory
        # persisted entry.
        escalated = False
        from_model = None
        to_model = None
        data["model"] = None
        data.pop("escalated", None)
        data.pop("from_model", None)
        data.pop("to_model", None)
        if "resolved_models" in data:
            data["resolved_models"] = {
                stage: stage_model for stage, stage_model in data["resolved_models"].items() if stage != "dev"
            }

    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        story_key=render_feed_key(story_key),
        effective_policy=effective_policy,
        candidate_spec_text=spec_text,
        deps_graph=_load_station_deps_graph(repo_root, slug),
        parallel_dispatch=parallel_dispatch,
    )
    if conflict is not None:
        findings.append(
            Finding(
                code=conflict.code,
                severity=Severity.ERROR,
                message=conflict.message,
            )
        )
        data["in_flight_story"] = conflict.in_flight_story_key
        return _done()

    findings.extend(
        cross_station_surface_overlap_advisories(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            requested_slug=slug,
            requested_story_key=render_feed_key(story_key),
            requested_spec_text=spec_text,
        )
    )

    try:
        provisioned = _ensure_dispatch_worktree(vcs, repo_root, slug, render_feed_key(story_key))
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-006",
                severity=Severity.ERROR,
                message=f"cannot provision dispatch worktree: {exc}",
            )
        )
        return _done()
    data["branch"] = provisioned.branch
    if provisioned.refusal is not None:
        findings.append(
            Finding(
                code="MRS-DISP-030",
                severity=Severity.ERROR,
                message=provisioned.refusal,
            )
        )
        return _done()
    if provisioned.legacy:
        findings.append(
            Finding(
                code="MRS-DISP-031",
                severity=Severity.WARN,
                message=(
                    f"story {render_feed_key(story_key)!r} is still on the "
                    f"pre-22.9 branch name {provisioned.branch!r} and lands "
                    "from there; it migrates to "
                    f"{dispatch_core.dispatch_worktree_branch(slug, render_feed_key(story_key))!r} "
                    "once that legacy branch is landed AND deleted — while "
                    "it survives, a later dispatch of this story is refused "
                    "(MRS-DISP-030) rather than migrated"
                ),
            )
        )
    worktree = provisioned.worktree
    if worktree is None:
        findings.append(
            Finding(
                code="MRS-DISP-006",
                severity=Severity.ERROR,
                message=(
                    "cannot provision dispatch worktree: branch "
                    f"{provisioned.branch!r} resolved with neither a worktree "
                    "nor a refusal"
                ),
            )
        )
        return _done()
    data["worktree_path"] = str(worktree)
    output_finding = _seed_dispatch_output_layer(fs=fs, worktree=worktree, context_payload=context_payload)
    if output_finding is not None:
        findings.append(output_finding)
    try:
        spec_path = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree)
    except ValueError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-005",
                severity=Severity.ERROR,
                message=f"cannot relocate spec into dispatch worktree: {exc}",
            )
        )
        return _done()
    data["spec_path"] = str(spec_path)

    try:
        baseline_head_sha = vcs.worktree_head_sha(worktree)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-012",
                severity=Severity.ERROR,
                message=f"cannot read dispatch worktree baseline head: {exc}",
            )
        )
        return _done()
    data["baseline_head_sha"] = baseline_head_sha

    wip_finding = _surface_worktree_wip_before_dispatch(
        vcs=vcs,
        repo_root=repo_root,
        worktree=worktree,
        baseline_head_sha=baseline_head_sha,
    )
    if wip_finding is not None:
        block_detail = _redispatch_blocked_pending_supervisor_finalize(
            fs=fs,
            repo_root=repo_root,
            slug=slug,
            story_key=render_feed_key(story_key),
            worktree=worktree,
        )
        if block_detail is not None:
            findings.append(
                Finding(
                    code="MRS-DISP-039",
                    severity=Severity.ERROR,
                    message=block_detail,
                )
            )
            return _done()
        findings.append(wip_finding)

    # Story 29.2: worktree spec status: done (follow-up not recommended)
    # is session-terminal. CAP-4 only — never another bmad-build-auto
    # because main's ledger is still backlog.
    live_spec_text = _spec_text_prefer_worktree(spec_path, repo_root, worktree, spec_text)
    if blocks_harness_relaunch(
        parse_spec_status(live_spec_text),
        followup_review_recommended(live_spec_text),
    ):
        data["harness_done_land_only"] = True
        land_verdict, named_target, _land_envelope = _attempt_harness_done_cap4(
            slug=slug,
            story_key=story_key,
            worktree=worktree,
            repo_root=repo_root,
            effective_policy=effective_policy,
            spec_text=live_spec_text,
            fs=fs,
            vcs=vcs,
            process=process,
        )
        data["land_verdict"] = land_verdict.value
        data["land_named_target"] = named_target
        if land_verdict in {
            DispatchLandingVerdict.LANDED,
            DispatchLandingVerdict.ALREADY_LANDED,
        }:
            return _done()
        findings.append(
            Finding(
                code="MRS-DISP-040",
                severity=Severity.ERROR,
                message=land_fail_operator_message(
                    story_key=render_feed_key(story_key),
                    named_target=named_target,
                    land_verdict=land_verdict.value,
                ),
            )
        )
        return _done()

    # Story 51.4 (spec-pyforge-marshal CAP-252): a worktree spec left
    # `status: blocked` by its last session (the 27.3 incident) must not be
    # relaunched without an operator decision -- distinct from the `done`
    # branch above, this never attempts a CAP-4 land either.
    if parse_spec_status(live_spec_text) == "blocked":
        data["harness_blocked_no_relaunch"] = True
        findings.append(
            Finding(
                code="MRS-DISP-045",
                severity=Severity.ERROR,
                message=(
                    f"story {render_feed_key(story_key)!r} worktree spec is "
                    f"status: blocked -- not relaunching bmad-build-auto without "
                    f"an operator decision (blocking condition: "
                    f"{parse_blocking_condition(live_spec_text) or 'not stated'})"
                ),
            )
        )
        return _done()

    writer_id = _writer_id()
    mint_moment = _now_utc()
    run_id = mint_run_id(slug, _format_utc_compact(mint_moment), _random_token())
    data["run_id"] = run_id
    run_dir = dispatch_core.dispatch_run_dir(repo_root, slug, run_id)

    try:
        fs.ensure_dir(run_dir.parent)
        fs.create_dir_exclusive(run_dir)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-007",
                severity=Severity.ERROR,
                message=f"cannot create dispatch run directory {run_dir!r}: {exc}",
            )
        )
        return _done()

    intent_entry = build_entry(
        id=JournalEntryId(writer_id, 0),
        ts=_format_entry_ts(mint_moment),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={
            "story_key": render_feed_key(story_key),
            "spec_path": str(spec_path),
            "worktree_path": str(worktree),
            "model": model,
            "budget_env": dict(budget_env),
            "bmad_active_project": slug,
            "baseline_head_sha": baseline_head_sha,
            "harness_profile": resolution.profile,
            "context": context_payload,
            **(
                {
                    "escalated": True,
                    "from_model": from_model,
                    "to_model": to_model,
                }
                if escalated
                else {}
            ),
        },
    )
    try:
        _append_entry(fs, run_dir, intent_entry, fsync=True)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-007",
                severity=Severity.ERROR,
                message=f"cannot journal dispatch intent: {exc}",
            )
        )
        return _done()

    log_path = run_dir / _LOG_FILENAME
    data["log"] = str(log_path)
    try:
        launch = build_harness.dispatch(
            worktree,
            resolution=resolution,
            project_slug=slug,
            story_key=render_feed_key(story_key),
            spec_path=spec_path,
            model=model,
            budget_env=budget_env,
            log_path=log_path,
            # Story 28.2 (CAP-2): the wire layer's own resolved entry --
            # never the whole `[context]` payload. The launch seam has no
            # business reading a layer it does not implement.
            wire_layer=context_payload[harness_profile.WIRE_LAYER_NAME],
        )
    except BuildHarnessError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-008",
                severity=Severity.ERROR,
                message=f"cannot launch session harness: {exc}",
            )
        )
        outcome_entry = build_entry(
            id=JournalEntryId(writer_id, 1),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=intent_entry.id,
            payload={"ok": False, "error": str(exc)},
        )
        try:
            _append_entry(fs, run_dir, outcome_entry, fsync=False)
        except FsError:
            pass
        return _done()

    data["session_pid"] = launch.pid
    data["session_model"] = launch.model
    if launch.model_omitted_reason is not None:
        findings.append(
            Finding(
                code="MRS-DISP-029",
                severity=Severity.WARN,
                message=launch.model_omitted_reason,
            )
        )
    # Story 28.2 (CAP-2): what the wire layer actually did to THIS launch --
    # echoed and journaled whether it applied, degraded, or stayed off, so
    # "was this session wrapped?" is a recorded fact rather than an
    # inference from an argv nobody kept. A degradation over an ENABLED
    # layer additionally raises MRS-DISP-033 (WARN): the layer disabling
    # itself is always named, never silent -- and never blocking, the
    # session is already live and unwrapped.
    # A harness that returns no decision at all (the port's field is
    # optional) composes the SAME off-shape through `WireWrap` rather than a
    # hand-spelled literal -- `journal_payload()` is the one spelling of
    # this payload, so adding a field to `WireWrap` cannot silently leave a
    # call site behind.
    wire = launch.wire if launch.wire is not None else harness_profile.WireWrap(applied=False)
    data["wire"] = wire.journal_payload()
    if wire.reason is not None:
        findings.append(
            Finding(
                code="MRS-DISP-033",
                severity=Severity.WARN,
                message=wire.reason,
            )
        )
    outcome_entry = build_entry(
        id=JournalEntryId(writer_id, 1),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.OUTCOME,
        intent_id=intent_entry.id,
        payload={
            "ok": True,
            "session_pid": launch.pid,
            "model": launch.model,
            "budget_env": dict(launch.budget_env),
            "harness_profile": launch.profile,
            # A fresh dict per call (never the one already in `data`), so
            # the journal payload and the echoed envelope can never alias.
            "wire": wire.journal_payload(),
        },
    )
    try:
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-009",
                severity=Severity.WARN,
                message=(f"session launched (pid {launch.pid}) but outcome journal write failed: {exc}"),
            )
        )

    if not process.is_alive(launch.pid):
        findings.append(
            Finding(
                code="MRS-DISP-010",
                severity=Severity.WARN,
                message=(
                    f"session harness reported pid {launch.pid} but the process is not alive immediately after launch"
                ),
            )
        )

    supervisor_log = run_dir / _SUPERVISOR_LOG_FILENAME
    data["supervisor_log"] = str(supervisor_log)
    try:
        supervisor_pid = process.spawn_detached(
            [
                sys.executable,
                "-m",
                "pyforge.marshal.dispatch_supervisor",
                str(repo_root),
                slug,
                run_id,
                str(launch.pid),
                str(worktree),
                render_feed_key(story_key),
                baseline_head_sha,
                effective_policy.merge_subject_template.value,
                str(supervisor_log),
            ],
            cwd=repo_root,
            log_path=supervisor_log,
        )
    except ProcessError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-013",
                severity=Severity.WARN,
                message=(
                    f"session launched (pid {launch.pid}) but dispatch "
                    f"completion supervisor could not be spawned: {exc} "
                    f"(supervisor log: {str(supervisor_log)!r})"
                ),
            )
        )
    else:
        data["supervisor_pid"] = supervisor_pid
        supervisor_outcome = build_entry(
            id=JournalEntryId(writer_id, 2),
            ts=_format_entry_ts(_now_utc()),
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=intent_entry.id,
            payload={"supervisor_pid": supervisor_pid},
        )
        try:
            _append_entry(fs, run_dir, supervisor_outcome, fsync=False)
        except FsError:
            pass

    return _done()


def _spawn_dispatch_supervisor(
    *,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    run_id: str,
    session_pid: int,
    worktree: Path,
    story_key: str,
    baseline_head_sha: str,
    merge_subject_template: str,
    run_dir: Path,
) -> int | None:
    supervisor_log = run_dir / _SUPERVISOR_LOG_FILENAME
    try:
        return process.spawn_detached(
            [
                sys.executable,
                "-m",
                "pyforge.marshal.dispatch_supervisor",
                str(repo_root),
                slug,
                run_id,
                str(session_pid),
                str(worktree),
                story_key,
                baseline_head_sha,
                merge_subject_template,
                str(supervisor_log),
            ],
            cwd=repo_root,
            log_path=supervisor_log,
        )
    except ProcessError:
        return None


def _load_latest_dispatch_context(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    slug: str,
) -> tuple[Path, Path, str, dispatch_core.DispatchJournalFacts, policy.EffectivePolicy] | None:
    del process
    try:
        repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError:
        return None
    run_dir = latest_dispatch_run_dir(repo_root, slug)
    if run_dir is None:
        return None
    journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
    if journal.story_key is None or journal.worktree_path is None:
        return None
    if journal.session_pid is None or journal.baseline_head_sha is None:
        return None
    return repo_root, run_dir, run_dir.name, journal, _compose_policy(slug)


def _ensure_dispatch_supervision(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    run_dir: Path,
    run_id: str,
    slug: str,
    journal: dispatch_core.DispatchJournalFacts,
    effective_policy: policy.EffectivePolicy,
    operator_kind: str,
) -> tuple[int | None, list[Finding], dict[str, object]]:
    """Re-spawn dispatch supervisor when dead; journal operator attach/resume."""
    findings: list[Finding] = []
    data: dict[str, object] = {
        "slug": slug,
        "run_id": run_id,
        "story_key": journal.story_key,
    }
    session_alive = journal.session_pid is not None and process.is_alive(journal.session_pid)
    supervisor_alive = journal.supervisor_pid is not None and process.is_alive(journal.supervisor_pid)
    verdict = resolve_dispatch_session_verdict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        journal=journal,
        effective_policy=effective_policy,
        run_dir=run_dir,
    )
    data["session_alive"] = session_alive
    data["supervisor_alive"] = supervisor_alive
    data["completion_verdict"] = verdict.value if verdict is not None else None
    if verdict not in {DispatchSessionVerdict.LIVE, None}:
        findings.append(
            Finding(
                code="MRS-DISP-023",
                severity=Severity.ERROR,
                message=(
                    f"no live dispatch to recover on station {slug!r}: "
                    f"completion verdict is {verdict.value if verdict else 'unknown'!r}"
                ),
            )
        )
        return None, findings, data
    if not session_alive and verdict != DispatchSessionVerdict.LIVE:
        findings.append(
            Finding(
                code="MRS-DISP-023",
                severity=Severity.ERROR,
                message=(
                    f"no live dispatch session on station {slug!r} (session pid {journal.session_pid} is not alive)"
                ),
            )
        )
        return None, findings, data
    new_supervisor_pid: int | None = journal.supervisor_pid
    if not supervisor_alive:
        respawned = _spawn_dispatch_supervisor(
            process=process,
            repo_root=repo_root,
            slug=slug,
            run_id=run_id,
            session_pid=journal.session_pid,
            worktree=Path(journal.worktree_path),
            story_key=journal.story_key,
            baseline_head_sha=journal.baseline_head_sha,
            merge_subject_template=effective_policy.merge_subject_template.value,
            run_dir=run_dir,
        )
        if respawned is None:
            findings.append(
                Finding(
                    code="MRS-DISP-024",
                    severity=Severity.WARN,
                    message=(
                        "dispatch session is live but completion supervisor "
                        "could not be re-spawned; run continues unsupervised"
                    ),
                )
            )
        else:
            new_supervisor_pid = respawned
            data["supervisor_pid"] = respawned
            writer_id = _writer_id()
            kind = (
                dispatch_core.KIND_DISPATCH_OPERATOR_ATTACH
                if operator_kind == "attach"
                else dispatch_core.KIND_DISPATCH_OPERATOR_RESUME
            )
            entry = build_entry(
                id=JournalEntryId(writer_id, 0),
                ts=_format_entry_ts(_now_utc()),
                run_id=run_id,
                kind=kind,
                phase=Phase.OBSERVATION,
                payload={
                    "supervisor_pid": respawned,
                    "session_pid": journal.session_pid,
                    "reconciled_unsupervised": not supervisor_alive,
                },
            )
            try:
                _append_entry(fs, run_dir, entry, fsync=True)
            except FsError as exc:
                findings.append(
                    Finding(
                        code="MRS-DISP-025",
                        severity=Severity.WARN,
                        message=f"supervision recovered but operator journal failed: {exc}",
                    )
                )
    data["log"] = str(run_dir / _LOG_FILENAME)
    return new_supervisor_pid, findings, data


def add_factory_dispatch_attach_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    parser = factory_subparsers.add_parser(
        "dispatch-attach",
        help="Recover supervision and follow a live dispatch session log (Story 22.6).",
        description=(
            "Re-spawns the dispatch completion supervisor when it died, journals "
            "the operator attach, then execs tail on the session log — never "
            "busy-waits in Python."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug (station).")
    parser.set_defaults(handler=run_dispatch_attach)


def add_factory_dispatch_resume_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    parser = factory_subparsers.add_parser(
        "dispatch-resume",
        help="Re-spawn dispatch supervision without blocking (Story 22.6).",
        description=(
            "Re-spawns the dispatch completion supervisor when it died and "
            "returns promptly — unsupervised git progress is reconciled by "
            "the supervisor from facts, not operator session state."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug (station).")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_dispatch_resume)


def run_dispatch_attach(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    process: ProcessPort | None = None,
) -> int:
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    process = process if process is not None else PosixProcess()
    slug = args.slug
    if not policy._is_valid_project_slug(slug):
        finding = Finding(
            code="MRS-DISP-001",
            severity=Severity.ERROR,
            message=f"malformed project slug {slug!r}",
        )
        try:
            print(
                f"error: {finding.code} [{finding.severity.value}] {finding.message}",
                file=sys.stderr,
                flush=True,
            )
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
        return exit_code_for(compute_verdict((finding,)))
    loaded = _load_latest_dispatch_context(fs=fs, vcs=vcs, process=process, slug=slug)
    if loaded is None:
        finding = Finding(
            code="MRS-DISP-023",
            severity=Severity.ERROR,
            message=f"no dispatch run found for station {slug!r}",
        )
        try:
            print(
                f"error: {finding.code} [{finding.severity.value}] {finding.message}",
                file=sys.stderr,
                flush=True,
            )
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
        return exit_code_for(compute_verdict((finding,)))
    repo_root, run_dir, run_id, journal, effective_policy = loaded
    _, findings, data = _ensure_dispatch_supervision(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        run_dir=run_dir,
        run_id=run_id,
        slug=slug,
        journal=journal,
        effective_policy=effective_policy,
        operator_kind="attach",
    )
    if any(f.severity == Severity.ERROR for f in findings):
        try:
            for finding in findings:
                if finding.severity == Severity.ERROR:
                    print(
                        f"error: {finding.code} [{finding.severity.value}] {finding.message}",
                        file=sys.stderr,
                        flush=True,
                    )
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
        return exit_code_for(compute_verdict(tuple(findings)))
    log_path = Path(str(data["log"]))
    try:
        # Story 14.4, CAP-6: stays raw os.execvp, exempted file-level in
        # test_process_sole_ownership.py -- REPLACES this process's own
        # image with `tail -F` so `marshal attach` hands the user's
        # terminal straight to the live dispatch log (Ctrl-C exits tail,
        # not a subprocess). pyforge.core.process's ProcessPort has no
        # analog: it launches and either waits (run) or detaches
        # (spawn_detached) a CHILD, never replaces the caller's own
        # process -- a fundamentally different primitive, not a second
        # implementation of subprocess launching.
        os.execvp("tail", ["tail", "-F", str(log_path)])
    except OSError as exc:
        finding = Finding(
            code="MRS-DISP-026",
            severity=Severity.ERROR,
            message=f"cannot exec tail on dispatch log {log_path!r}: {exc}",
        )
        try:
            print(
                f"error: {finding.code} [{finding.severity.value}] {finding.message}",
                file=sys.stderr,
                flush=True,
            )
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
        return exit_code_for(compute_verdict((finding,)))
    return 0


def run_dispatch_resume(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    process: ProcessPort | None = None,
) -> int:
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    process = process if process is not None else PosixProcess()
    slug = args.slug
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug}
    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-DISP-001",
                severity=Severity.ERROR,
                message=f"malformed project slug {slug!r}",
            )
        )
        return _emit(args, data, findings)
    loaded = _load_latest_dispatch_context(fs=fs, vcs=vcs, process=process, slug=slug)
    if loaded is None:
        findings.append(
            Finding(
                code="MRS-DISP-023",
                severity=Severity.ERROR,
                message=f"no dispatch run found for station {slug!r}",
            )
        )
        return _emit(args, data, findings)
    repo_root, run_dir, run_id, journal, effective_policy = loaded
    _, sup_findings, sup_data = _ensure_dispatch_supervision(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        run_dir=run_dir,
        run_id=run_id,
        slug=slug,
        journal=journal,
        effective_policy=effective_policy,
        operator_kind="resume",
    )
    findings.extend(sup_findings)
    data.update(sup_data)
    return _emit(args, data, findings)


# =============================================================================
# Story 22.7 (FR-193 CAP-7): fleet-wide drain as a marshal-orchestrated mode.
#
# Everything below COMPOSES already-shipped primitives and adds exactly one
# new decision -- "which story does this station get next" -- whose pure core
# lives in `core/dispatch_fleet.py`:
#
#   queue      <- HarnessPort.ledger_story_statuses over each station's
#                 TRACKED sprint-status-ledger.yaml (the same parser
#                 `marshal status --reconcile-ledger` already uses), plus an
#                 OPTIONAL in-repo override file. Never `.cursor/…/queues.yaml`.
#   preflight  <- dispatch_once -> station_in_flight_conflict (CAP-2/CAP-5)
#   parallel   <- dispatch_once launches DETACHED and returns, so issuing one
#                 dispatch per station in a cycle leaves eight sessions
#                 running concurrently. FR-184's in-loop max_parallel clamp
#                 is not read, written, or referenced anywhere here.
#   land+chain <- the per-story dispatch supervisor each launch spawns already
#                 owns verify -> land -> `dispatch_land_finalize` (merge,
#                 scoped `sprint-ledger-sync --project <station>`, spec
#                 promotion). The fleet mode adds no landing path at all: it
#                 re-reads the advanced ledger on the next cycle, finds the
#                 station's slot free, and dispatches the next story.
# =============================================================================


def add_factory_drain_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    parser = factory_subparsers.add_parser(
        "drain",
        help="Fleet-wide drain across every pyforge station (Story 22.7).",
        description=(
            "Reads each pyforge station's ordered backlog from its TRACKED "
            "sprint-status-ledger.yaml (plus optional in-repo order "
            "overrides), applies the named campaign mode, preflights every "
            "dispatch through the shipped zombie/in-flight refusals, and "
            "launches one story per station -- detached, so stations run in "
            "parallel. Unless --once is given, a detached campaign "
            "supervisor re-runs the cycle so each station's next story is "
            "chained once its predecessor's merge-through-finalize advances "
            "the tracked ledger. --mode is REQUIRED and never defaulted."
        ),
    )
    parser.add_argument(
        "--mode",
        default=None,
        help=(
            "Campaign mode: "
            + " | ".join(dispatch_fleet.CAMPAIGN_MODES)
            + " (required -- a missing or unknown mode is refused, never "
            "silently defaulted)."
        ),
    )
    parser.add_argument(
        "--station",
        default=None,
        help=(
            "Restrict this campaign to exactly one station's own tracked "
            "backlog (Story 22.11, FR-193 CAP-10) -- accepts either the "
            "bare name (`scribe`) or the full slug (`pyforge-scribe`). "
            "Every other station is untouched by this invocation. Omit "
            "for the fleet-wide default (all live pyforge stations)."
        ),
    )
    parser.add_argument(
        "--stories",
        default=None,
        help=(
            "Chain a caller-supplied ordered story-key sequence on "
            "--station's own backlog instead of its ledger order (Story "
            "22.11, FR-193 CAP-10) -- comma-separated, requires --station. "
            "Normally reached via `marshal factory dispatch <slug> "
            "--stories ...`; --once/--campaign chaining consumes this "
            "same flag across supervised cycles."
        ),
    )
    parser.add_argument(
        "--leave-remaining",
        type=int,
        default=1,
        help=("Under --mode leave_one, how many backlog stories to leave untouched per station (default: 1)."),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one cycle and return; spawn no campaign supervisor.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=0,
        help="Campaign-supervisor cycle ceiling (0 = until the campaign completes).",
    )
    parser.add_argument(
        "--tick-seconds",
        type=int,
        default=_FLEET_TICK_SECONDS,
        help=f"Campaign-supervisor delay between cycles (default: {_FLEET_TICK_SECONDS}).",
    )
    parser.add_argument(
        "--campaign",
        default=None,
        help=(
            "Reuse an existing campaign run id instead of minting one -- how "
            "the detached campaign supervisor keeps every cycle on one "
            "journal (and so remembers which stations are blocked)."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--harness",
        default=None,
        help=(
            "Ordered session-harness preference for every dispatch this "
            "campaign launches (comma-separated profile names, e.g. "
            "cursor,claude). Overrides project/repo defaults without "
            "editing marshal-policy.toml."
        ),
    )
    parser.add_argument(
        "--max-in-flight",
        type=int,
        default=None,
        dest="max_in_flight",
        help=(
            "Within-station parallel dispatch cap for this campaign (Story "
            "28.16) -- overrides project policy max_parallel. Default: "
            "policy value or 1 (serial, byte-identical to today's drain)."
        ),
    )
    parser.add_argument(
        "--retry-environment-blocks",
        action="store_true",
        help=(
            "Under drain_to_zero or leave_one, skip past environment-classified "
            "blocks (zero git progress, zero review/verify evidence) so the "
            "next story dispatches. Story-classified failures still halt the "
            "station. Also honored under skip_on_blocked (the default there)."
        ),
    )
    parser.set_defaults(handler=run_fleet_drain)


def _preflight_explicit_story_specs(repo_root: Path, slug: str, stories: tuple[str, ...]) -> tuple[str, ...]:
    """Stories in ``stories`` with no tracked spec -- fast-fail before mint."""
    missing: list[str] = []
    for story in stories:
        if dispatch_core.resolve_story_spec_path(repo_root, slug, story) is None:
            missing.append(story)
    return tuple(missing)


def _predicate_payload(predicate: dispatch_re_preflight.RefusePredicate) -> dict[str, str]:
    return {
        "gate": predicate.gate,
        "spec_fingerprint": predicate.spec_fingerprint,
        "verify_fingerprint": predicate.verify_fingerprint,
        "digest": predicate.digest(),
    }


def _predicate_from_payload(raw: object) -> dispatch_re_preflight.RefusePredicate | None:
    if not isinstance(raw, dict):
        return None
    gate = raw.get("gate")
    spec = raw.get("spec_fingerprint")
    verify = raw.get("verify_fingerprint")
    if not isinstance(gate, str) or not isinstance(spec, str) or not isinstance(verify, str):
        return None
    return dispatch_re_preflight.RefusePredicate(
        gate=gate,
        spec_fingerprint=spec,
        verify_fingerprint=verify,
    )


def _primary_checkout_is_clean_main(vcs: VcsPort, repo_root: Path) -> bool:
    """``True`` only when the primary checkout (``repo_root``) is a clean,
    unmoved local ``main`` -- the same "is this checkout safe to trust"
    gate ``cli/land.py::_resync_home_branch`` already encodes for
    fast-forwarding (Story 51.9, re-mint of 51.3). Any git failure is
    treated as "not safe to trust" rather than propagated -- the caller
    falls back to reading ``origin/main`` directly in that case, never
    crashes the campaign's own ledger read."""
    try:
        if vcs.has_uncommitted_changes(repo_root):
            return False
        return vcs.worktree_head_sha(repo_root) == vcs.resolve_ref(repo_root, "main")
    except VcsCommandError:
        return False


def _station_ledger_statuses(
    *,
    harness: HarnessPort,
    vcs: VcsPort,
    repo_root: Path,
    ledger_path: Path,
) -> tuple[tuple[str, str], ...]:
    """One station's ledger statuses (Story 51.9, re-mint of 51.3).

    ``_promote_sprint_ledger`` (CAP-5) publishes a promotion onto
    ``origin/main`` WITHOUT ever touching the primary checkout's own
    working tree -- so a sibling station's finalize can promote a story to
    ``done`` while this campaign's primary checkout sits stale, dirty, or
    on a different branch. Trusts the local ``HarnessPort`` read only when
    ``repo_root`` is verifiably a clean, unmoved ``main`` (byte-identical
    to before this story); otherwise reads ``origin/main``'s own copy of
    the ledger via ``VcsPort.file_text_at_ref`` and the pre-existing
    ``_parse_sprint_ledger_statuses`` text scanner, falling back to the
    local ``HarnessPort`` read when the remote read fails or the ledger is
    absent at ``origin/main``. Raises only what
    ``HarnessPort.ledger_story_statuses`` itself already raises -- every
    call site's own pre-existing exception handling is unchanged."""
    if _primary_checkout_is_clean_main(vcs, repo_root):
        return harness.ledger_story_statuses(ledger_path)
    remote_text: str | None = None
    try:
        rel_path = ledger_path.relative_to(dispatch_core.canonical_repo_root(repo_root)).as_posix()
        # Review pass 2026-09-19 (VG1): refresh the local cache of
        # `origin/main` first -- without this, a stale cached ref could
        # silently defeat the fallback in exactly the scenario it exists
        # to fix. Same swallow-and-fall-back handling as the read itself.
        vcs.fetch(repo_root, "origin", "main")
        remote_text = vcs.file_text_at_ref(repo_root, "origin/main", rel_path)
    except VcsCommandError, ValueError:
        remote_text = None
    if remote_text is None:
        return harness.ledger_story_statuses(ledger_path)
    return tuple(_parse_sprint_ledger_statuses(remote_text).items())


def gather_fleet_missing_spec_escalations(
    *,
    fs: FsPort,
    harness: HarnessPort,
    vcs: VcsPort,
    repo_root: Path,
) -> dict[str, dispatch_fleet.MissingSpecEscalation]:
    """Active ``MRS-DISP-005`` campaign blocks that still lack a tracked spec.

    Story 28.19 (CAP-2): operators must never read ``idle`` while remaining
    backlog is blocked on a missing spec. Reads the latest fleet-drain
    campaign journal only -- never auto-authors specs.
    """
    run_id = dispatch_fleet.latest_fleet_campaign_run_id(repo_root)
    if run_id is None:
        return {}
    run_dir = dispatch_fleet.fleet_run_dir(repo_root, run_id)
    blocked, _predicates = _campaign_blocked_from_journal(fs, run_dir, run_id)
    escalations: dict[str, dispatch_fleet.MissingSpecEscalation] = {}
    for slug, stories in blocked.items():
        for story, detail in stories.items():
            gate = dispatch_re_preflight.parse_refuse_gate(detail)
            if gate != "MRS-DISP-005":
                continue
            if dispatch_core.resolve_story_spec_path(repo_root, slug, story) is not None:
                continue
            expected = dispatch_core.expected_story_spec_glob(repo_root, slug, story)
            if expected is None:
                continue
            ledger_path = dispatch_fleet.station_ledger_path(repo_root, slug)
            try:
                statuses = _station_ledger_statuses(
                    harness=harness, vcs=vcs, repo_root=repo_root, ledger_path=ledger_path
                )
            except HarnessError, OSError, ValueError:
                continue
            backlog = dispatch_fleet.station_backlog(statuses)
            if not backlog:
                continue
            try:
                blocked_key = normalize(story)
            except ValueError:
                continue
            if not any(normalize(raw_key) == blocked_key for raw_key in backlog):
                continue
            escalations[slug] = dispatch_fleet.MissingSpecEscalation(
                story=render_feed_key(blocked_key),
                expected_spec_glob=expected,
            )
            break
    return escalations


def _reconcile_campaign_blocked_for_re_preflight(
    *,
    repo_root: Path,
    blocked: dict[str, dict[str, str]],
    prior_predicates: dict[str, dict[str, dispatch_re_preflight.RefusePredicate]],
    policy_flags: dict[str, object] | None,
) -> tuple[dict[str, dict[str, str]], list[Finding]]:
    """Drop or rate-limit campaign blocks whose refuse predicate can change."""
    findings: list[Finding] = []
    reconciled: dict[str, dict[str, str]] = {}
    for slug, station_blocked in blocked.items():
        effective_policy = _compose_policy(slug, flags=policy_flags)
        verify_commands = effective_policy.verify_commands.value
        prior = prior_predicates.get(slug, {})
        kept, results = dispatch_re_preflight.reconcile_station_re_preflight(
            repo_root=repo_root,
            slug=slug,
            blocked=station_blocked,
            verify_commands=verify_commands,
            prior_predicates=prior,
        )
        if kept:
            reconciled[slug] = kept
        for result in results:
            if result.decision is dispatch_re_preflight.RePreflightDecision.CLEARED:
                continue
            if result.decision is dispatch_re_preflight.RePreflightDecision.RATE_LIMITED:
                findings.append(
                    Finding(
                        code="MRS-DRAIN-017",
                        severity=Severity.WARN,
                        message=(
                            f"station {slug!r}: story {result.story!r} remains "
                            f"blocked on {result.gate} with an unchanged refuse "
                            "predicate -- rate-limited this tick, not re-dispatched"
                        ),
                    )
                )
    return reconciled, findings


def _reconcile_campaign_blocked(
    *,
    vcs: VcsPort,
    repo_root: Path,
    blocked: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    """Drop blocked entries for stories already merged on origin/main."""
    if not blocked:
        return blocked
    fetch = getattr(vcs, "fetch", None)
    if fetch is None:
        return blocked
    try:
        fetch(repo_root, "origin", "main")
        subjects = vcs.commit_subjects(repo_root, _BASE_REF)
    except VcsCommandError, AttributeError:
        return blocked
    reconciled: dict[str, dict[str, str]] = {}
    for slug, station_blocked in blocked.items():
        effective_policy = _compose_policy(slug)

        def _spec_status_for(candidate_key: StoryKey, *, _slug: str = slug) -> str | None:
            # Story 51.7/CAP-255: the same station-branch corroboration
            # `dispatch_land`/`dispatch_supervisor` apply -- a mint/
            # fallout/fix PR's station-branch merge must not prune a
            # campaign's blocked entry as though it had actually landed.
            # Fails closed (never corroborates) on any git read failure.
            try:
                spec_text = dispatch_core.spec_text_at_ref(vcs, repo_root, _slug, str(candidate_key))
            except VcsCommandError:
                return None
            return promotion_core.read_spec_status(spec_text)

        merged = promotion_core.corroborated_merged_story_keys(
            subjects,
            effective_policy.merge_subject_template.value,
            slug,
            spec_status_for=_spec_status_for,
        )
        merged_feed = frozenset(render_feed_key(key) for key in merged)
        reconciled[slug] = prune_blocked_stories_merged_on_main(
            station_blocked,
            merged_story_keys=merged_feed,
        )
    return reconciled


def _load_station_story_deps(
    fs: FsPort, repo_root: Path, slug: str
) -> dict[StoryKey, dispatch_fleet.ParsedStoryDeps] | None:
    """Read declared ``Deps:`` edges for one station (Story 28.12).

    Returns ``None`` when no epics doc could be read -- ``station_backlog``
    keeps its legacy story-key ordering. Returns a (possibly empty) mapping
    when at least one epics-family doc parsed successfully.
    """
    combined: dict[StoryKey, dispatch_fleet.ParsedStoryDeps] = {}
    read_any = False
    for path in dispatch_fleet.station_epics_paths(repo_root, slug):
        text = fs.read_text(path)
        if text is None:
            continue
        read_any = True
        combined.update(dispatch_fleet.parse_epics_dependencies(text))
    if not read_any:
        return None
    return combined


def _read_fleet_queue_config(
    fs: FsPort, repo_root: Path
) -> tuple[dict[str, tuple[str, ...]], dict[str, dict[str, str]], list[Finding]]:
    """Read the OPTIONAL in-repo order-override / skip-policy file.

    The in-repo analog of the interim runner's ``queues.yaml``
    ``order_overrides``/``skip_policies`` blocks -- minus its ``stations:``
    block, which was a regenerated copy of state the tracked ledgers already
    hold. Absent (the default) means "ledger order, no skips"; unreadable or
    malformed is reported, never silently treated as absent.

    Every ``skip_policies`` entry is an operator's DECLARED skip, honored
    under every campaign mode -- the interim runner's own entries all carried
    ``action: skip_on_blocked`` while the campaign ran ``drain_to_zero``.
    Mode governs DERIVED blocks (CAP-2 failure evidence), not these.
    """
    findings: list[Finding] = []
    path = dispatch_fleet.queue_config_path(repo_root)
    text = fs.read_text(path)
    if text is None:
        return {}, {}, findings
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-008",
                severity=Severity.WARN,
                message=(
                    f"cannot parse fleet queue overrides at {path}: {exc} "
                    "-- falling back to tracked-ledger order with no skips"
                ),
                path=str(path),
            )
        )
        return {}, {}, findings
    if document is None:
        return {}, {}, findings
    if not isinstance(document, dict):
        findings.append(
            Finding(
                code="MRS-DRAIN-008",
                severity=Severity.WARN,
                message=(
                    f"fleet queue overrides at {path} must be a mapping, got "
                    f"{type(document).__name__} -- falling back to "
                    "tracked-ledger order with no skips"
                ),
                path=str(path),
            )
        )
        return {}, {}, findings

    overrides: dict[str, tuple[str, ...]] = {}
    raw_overrides = document.get("order_overrides") or {}
    if isinstance(raw_overrides, dict):
        for raw_station, raw_keys in raw_overrides.items():
            if not isinstance(raw_keys, list):
                continue
            slug = dispatch_fleet.normalize_station_slug(str(raw_station))
            overrides[slug] = tuple(str(k) for k in raw_keys if isinstance(k, str))

    skips: dict[str, dict[str, str]] = {}
    raw_skips = document.get("skip_policies") or []
    if isinstance(raw_skips, list):
        for entry in raw_skips:
            if not isinstance(entry, dict):
                continue
            raw_station = entry.get("station")
            raw_story = entry.get("story")
            if not isinstance(raw_station, str) or not isinstance(raw_story, str):
                continue
            slug = dispatch_fleet.normalize_station_slug(raw_station)
            reason = entry.get("reason")
            skips.setdefault(slug, {})[raw_story] = (
                str(reason) if isinstance(reason, str) and reason else "declared skip policy"
            )
    return overrides, skips, findings


def _station_blocked_map(
    *,
    fs: FsPort,
    vcs: VcsPort,
    process: ProcessPort,
    repo_root: Path,
    slug: str,
    backlog: tuple[str, ...],
    configured_skips: dict[str, str],
    campaign_blocked: dict[str, str],
    effective_policy: policy.EffectivePolicy,
) -> tuple[dict[str, str], dict[str, dispatch_fleet.FleetBlockClass]]:
    """DERIVED blocks at the HEAD of ``backlog``, with their evidence.

    Walks the backlog only as far as the first dispatchable story: under
    every mode the queue decision stops there, so probing the tail would be
    pure cost. A story is blocked when this campaign already saw a
    non-liveness refusal for it, or when CAP-2's own facts say its last
    dispatch ended ``failed``.

    ``configured_skips`` is read here ONLY to keep walking past a story the
    operator declared skipped -- those never enter the returned map, because
    a hand-declared skip is honored under every mode while a derived block
    is what the campaign mode governs (see ``plan_station_queue``).
    """
    blocked: dict[str, str] = {}
    block_classes: dict[str, dispatch_fleet.FleetBlockClass] = {}
    for story in backlog:
        if story in configured_skips:
            continue
        if story in campaign_blocked:
            blocked[story] = campaign_blocked[story]
            block_classes[story] = dispatch_fleet.FleetBlockClass.STORY
            continue
        try:
            facts = station_story_block_facts(
                fs=fs,
                vcs=vcs,
                process=process,
                repo_root=repo_root,
                slug=slug,
                story_key=story,
                effective_policy=effective_policy,
            )
        except VcsCommandError, ValueError:
            facts = None
        if facts is None:
            break
        blocked[story] = facts.reason
        block_classes[story] = facts.block_class
    return blocked, block_classes


def _classify_attempt(
    slug: str, story: str, attempt: DispatchAttempt
) -> tuple[dispatch_fleet.StationCycleStatus, str | None, list[Finding]]:
    """Turn one ``dispatch_once`` outcome into a station status + findings.

    A liveness refusal (CAP-2's MRS-DISP-011, CAP-5's MRS-DISP-021) is the
    NORMAL state of a healthy campaign -- eight stations working means eight
    busy stations -- so it is relayed as a campaign-level WARN that names the
    original code and the in-flight story verbatim, rather than surfaced at
    its own ERROR tier, which would red every cycle. Every other refusal is
    relayed as-is, keeping its own registered code and severity: a missing
    spec is a real problem the operator must see.
    """
    findings: list[Finding] = []
    errors = attempt.errors
    if not errors:
        # Advisories (e.g. CAP-5's MRS-DISP-022 overlap) still surface.
        findings.extend(attempt.findings)
        return dispatch_fleet.StationCycleStatus.DISPATCHED, None, findings
    liveness = next((f for f in errors if f.code in {"MRS-DISP-011", "MRS-DISP-021"}), None)
    if liveness is not None:
        in_flight = attempt.data.get("in_flight_story")
        findings.append(
            Finding(
                code="MRS-DRAIN-006",
                severity=Severity.WARN,
                message=(f"station {slug!r}: no dispatch this cycle -- {liveness.code} {liveness.message}"),
            )
        )
        detail = f"{liveness.code}: in flight {in_flight!r}" if in_flight else liveness.code
        return dispatch_fleet.StationCycleStatus.IN_FLIGHT, detail, findings
    findings.extend(attempt.findings)
    first = errors[0]
    return (
        dispatch_fleet.StationCycleStatus.REFUSED,
        f"{first.code}: {first.message}",
        findings,
    )


def _wave_journal_writer_id(wave_id: str) -> str:
    """Filesystem-safe journal writer id for a dispatch wave (Story 33.8).

    ``wave_id`` embeds ISO-8601 timestamps with uppercase ``T``/``Z`` that
    violate ``core.journal``'s ``writer_id`` pattern; hash instead.
    """
    import hashlib

    digest = hashlib.sha256(wave_id.encode()).hexdigest()[:24]
    return f"wave-{digest}"


def _journal_dispatch_wave(
    fs: FsPort,
    repo_root: Path,
    slug: str,
    wave: dispatch_fleet.WaveBatch,
    *,
    surfaces: Mapping[str, tuple[str, ...] | None],
) -> None:
    """Record one parallel wave intent (Story 28.16, CAP-3)."""
    import hashlib

    members_payload = []
    for story in wave.members:
        surface = surfaces.get(story) or ()
        digest = hashlib.sha256(repr(surface).encode()).hexdigest()
        members_payload.append({"story": story, "surfaces_hash": digest})
    refused_payload = [
        {
            "story": r.story,
            "reason": r.reason,
            **({"overlap_with": r.overlap_with} if r.overlap_with else {}),
            **({"paths": list(r.paths)} if r.paths else {}),
        }
        for r in wave.refused
    ]
    wave_run = dispatch_core.dispatch_runs_dir(repo_root, slug) / _DISPATCH_WAVES_DIRNAME / wave.wave_id
    fs.ensure_dir(wave_run)
    intent = build_entry(
        id=JournalEntryId(_wave_journal_writer_id(wave.wave_id), 0),
        ts=_format_entry_ts(_now_utc()),
        run_id=wave.wave_id,
        kind=dispatch_core.KIND_DISPATCH_WAVE,
        phase=Phase.INTENT,
        payload={
            "wave_id": wave.wave_id,
            "station": slug,
            "max_parallel": wave.max_parallel,
            "members": members_payload,
            "refused": refused_payload,
        },
    )
    _append_entry(fs, wave_run, intent, fsync=True)


def execute_fleet_cycle(
    *,
    repo_root: Path,
    mode: dispatch_fleet.FleetCampaignMode,
    leave_remaining: int,
    campaign_blocked: dict[str, dict[str, str]],
    fs: FsPort,
    vcs: VcsPort,
    build_harness: BuildHarnessPort,
    process: ProcessPort,
    harness: HarnessPort,
    station: str | None = None,
    explicit_stories: tuple[str, ...] | None = None,
    policy_flags: dict[str, object] | None = None,
    max_in_flight: int | None = None,
    retry_environment_blocks: bool = False,
) -> FleetCycleReport:
    """One fleet-drain cycle: plan every station, dispatch the eligible ones.

    Story 22.11 (FR-193 CAP-10): ``station``, when given, restricts this
    cycle to exactly one station's own tracked backlog -- every other
    station's ledger is never even read, so it is provably untouched by
    this invocation. ``explicit_stories``, when given (only meaningful
    alongside ``station``), replaces that one station's ledger-derived
    backlog with the caller's own ordered sequence (re-filtered to
    not-yet-``done`` every cycle) instead of reordering the full backlog
    the way ``order_override`` does.
    """
    if explicit_stories is not None and station is None:
        # Story 22.11 patch pass (review finding): `explicit_stories` is
        # only meaningful scoped to one station -- without this guard, a
        # future caller passing it alone would silently apply the caller's
        # sequence as every station's own backlog instead of just one.
        raise ValueError("explicit_stories requires station")
    findings: list[Finding] = []
    results: list[dispatch_fleet.StationCycleResult] = []
    overrides, configured_skips, config_findings = _read_fleet_queue_config(fs, repo_root)
    findings.extend(config_findings)

    slugs = dispatch_fleet.fleet_station_slugs(dispatch_core.list_station_slugs(repo_root))
    if station is not None:
        normalized_station = dispatch_fleet.normalize_station_slug(station)
        if normalized_station not in slugs:
            findings.append(
                Finding(
                    code="MRS-DRAIN-013",
                    severity=Severity.ERROR,
                    message=(
                        f"unknown station {normalized_station!r}: not among "
                        f"the live pyforge stations ({', '.join(slugs) or 'none found'})"
                    ),
                )
            )
            return FleetCycleReport(
                results=(),
                findings=tuple(findings),
                data={
                    "mode": mode.value,
                    "stations": [],
                    "remaining_total": 0,
                    "dispatched": [],
                    "unresolved": [],
                },
            )
        slugs = (normalized_station,)
    if not slugs:
        # Distinct from "every station is drained": `campaign_complete(())`
        # is vacuously True, so without this the operator would get a clean,
        # findings-free "campaign complete" from a repo where the projects
        # tree was simply unreadable or absent -- a false green.
        findings.append(
            Finding(
                code="MRS-DRAIN-012",
                severity=Severity.ERROR,
                message=(
                    "no pyforge stations found under "
                    f"{dispatch_core.canonical_repo_root(repo_root)}"
                    "/_bmad-output/projects -- an empty fleet is reported, "
                    "never treated as a drained one"
                ),
            )
        )
    for slug in slugs:
        ledger_path = dispatch_fleet.station_ledger_path(repo_root, slug)
        try:
            statuses = _station_ledger_statuses(harness=harness, vcs=vcs, repo_root=repo_root, ledger_path=ledger_path)
        except (HarnessError, OSError, ValueError) as exc:
            findings.append(
                Finding(
                    code="MRS-DRAIN-003",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: cannot read the tracked ledger at "
                        f"{ledger_path}: {exc} -- station excluded from this "
                        "campaign (its backlog is unknown, never assumed empty)"
                    ),
                    path=str(ledger_path),
                )
            )
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus.LEDGER_UNREADABLE,
                    remaining=0,
                    detail=str(exc),
                )
            )
            continue

        backlog = (
            dispatch_fleet.explicit_story_backlog(statuses, explicit_stories)
            if explicit_stories is not None
            else dispatch_fleet.station_backlog(
                statuses,
                order_override=overrides.get(slug),
                deps_by_story=(None if overrides.get(slug) else _load_station_story_deps(fs, repo_root, slug)),
            )
        )
        effective_policy = _compose_policy(slug, flags=policy_flags)
        station_skips = configured_skips.get(slug, {})
        # Story 50.1 Part A: the ~45 s window between session exit and ledger
        # promotion. Reported IN_FLIGHT (deliberately absent from
        # TERMINAL_STATION_STATUSES), so this station provisions nothing this
        # cycle and the campaign chains its next ready story on the following
        # one instead of re-dispatching or blocking on the story it just landed.
        finalize_pending = station_finalize_pending_story(
            fs=fs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            backlog=backlog,
            effective_policy=effective_policy,
        )
        if finalize_pending is not None:
            pending_story, pending_evidence = finalize_pending
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus.IN_FLIGHT,
                    remaining=len(backlog),
                    story=pending_story,
                    detail=pending_evidence,
                )
            )
            findings.append(
                Finding(
                    code="MRS-DRAIN-006",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: no dispatch this cycle -- story "
                        f"{pending_story!r} is finalizing: {pending_evidence}"
                    ),
                )
            )
            continue
        blocked, block_classes = _station_blocked_map(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            backlog=backlog,
            configured_skips=station_skips,
            campaign_blocked=campaign_blocked.get(slug, {}),
            effective_policy=effective_policy,
        )
        plan = dispatch_fleet.plan_station_queue(
            slug=slug,
            backlog=backlog,
            mode=mode,
            leave_remaining=leave_remaining,
            blocked=blocked,
            block_classes=block_classes,
            retry_environment_blocks=retry_environment_blocks,
            declared_skips=station_skips,
        )
        for story, reason in plan.skipped:
            if story in station_skips:
                basis = "declared skip policy"
            elif dispatch_fleet.is_harness_done_advance_reason(reason):
                basis = "harness-done CAP-4 (MRS-DISP-040); remaining backlog continues"
            elif reason.startswith(dispatch_fleet.ALREADY_LANDED_ADVANCE_PREFIX):
                # Story 50.1 Part B: named for what it is -- an advance past
                # work that already landed -- never mislabelled "blocked".
                basis = "already landed (Story 50.1); remaining backlog continues"
            elif block_classes.get(story) is dispatch_fleet.FleetBlockClass.ENVIRONMENT:
                basis = "environment-classified block"
            else:
                basis = f"blocked, and {mode.value} skips past it"
            findings.append(
                Finding(
                    code="MRS-DRAIN-004",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: skipping story {story!r} "
                        f"({basis}) -- {reason}. It stays in the backlog "
                        "and is never auto-retried."
                    ),
                )
            )
        if plan.outcome is dispatch_fleet.StationQueueOutcome.BLOCKED:
            blocked_class = (
                block_classes.get(plan.blocked_story or "")
                if plan.blocked_story
                else dispatch_fleet.FleetBlockClass.STORY
            )
            retry_hint = (
                f"re-run with --mode "
                f"{dispatch_fleet.FleetCampaignMode.SKIP_ON_BLOCKED.value} "
                "or --retry-environment-blocks"
                if blocked_class is dispatch_fleet.FleetBlockClass.ENVIRONMENT
                else (
                    f"re-run with --mode "
                    f"{dispatch_fleet.FleetCampaignMode.SKIP_ON_BLOCKED.value} "
                    "does not skip genuine story failures -- manual override "
                    "required"
                )
            )
            findings.append(
                Finding(
                    code="MRS-DRAIN-005",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: story {plan.blocked_story!r} is "
                        f"blocked ({blocked_class.value}) -- "
                        f"{plan.blocked_reason}. It stays in the "
                        "backlog, is never auto-retried, and is never forced "
                        f"past; {retry_hint} to move on to this station's "
                        "next story."
                    ),
                )
            )
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus.BLOCKED,
                    remaining=len(backlog),
                    story=plan.blocked_story,
                    detail=plan.blocked_reason,
                    skipped=plan.skipped,
                )
            )
            continue
        if plan.next_story is None:
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus(plan.outcome.value),
                    remaining=len(backlog),
                    skipped=plan.skipped,
                )
            )
            continue

        parallel_cap = resolve_max_parallel(
            effective_policy,
            cli_override=max_in_flight,
            policy_flags=policy_flags,
        )
        stories_to_dispatch: tuple[str, ...] = ()
        wave_detail: str | None = None
        if parallel_cap <= 1:
            if plan.next_story is not None:
                stories_to_dispatch = (plan.next_story,)
        else:
            live_stories = _live_dispatch_story_keys(
                fs=fs,
                vcs=vcs,
                process=process,
                repo_root=repo_root,
                slug=slug,
                effective_policy=effective_policy,
            )
            if live_stories:
                results.append(
                    dispatch_fleet.StationCycleResult(
                        slug=slug,
                        status=dispatch_fleet.StationCycleStatus.IN_FLIGHT,
                        remaining=len(backlog),
                        story=live_stories[0],
                        detail=(
                            f"wave in flight: {', '.join(live_stories)} "
                            "(waiting for terminal outcomes before next batch)"
                        ),
                        skipped=plan.skipped,
                    )
                )
                findings.append(
                    Finding(
                        code="MRS-DRAIN-006",
                        severity=Severity.WARN,
                        message=(
                            f"station {slug!r}: no dispatch this cycle -- "
                            f"waiting on in-flight wave member(s) "
                            f"{', '.join(live_stories)!r}"
                        ),
                    )
                )
                continue
            deps_graph = _load_station_deps_graph(repo_root, slug)
            ready = dispatch_fleet.ordered_ready_backlog(backlog, statuses, deps_graph)
            eligible = tuple(story for story in ready if story not in blocked and story not in station_skips)
            surfaces: dict[str, tuple[str, ...] | None] = {}
            for story in eligible:
                spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, story)
                if spec_path is None:
                    surfaces[story] = None
                    continue
                try:
                    spec_text = spec_path.read_text(encoding="utf-8")
                except OSError:
                    surfaces[story] = None
                    continue
                try:
                    surfaces[story] = _effective_surface_for_spec(
                        spec_text=spec_text,
                        story_key=normalize(story),
                        slug=slug,
                        effective_policy=effective_policy,
                    )
                except ValueError:
                    surfaces[story] = None
            wave_id = mint_run_id(slug, _format_utc_compact(_now_utc()), _random_token())
            wave = dispatch_fleet.build_wave_batch(
                wave_id=wave_id,
                ready=eligible,
                cap=parallel_cap,
                surfaces=surfaces,
                deps_graph=deps_graph,
            )
            stories_to_dispatch = wave.members
            if wave.members:
                _journal_dispatch_wave(fs, repo_root, slug, wave, surfaces=surfaces)
            for ref in wave.refused:
                overlap = f" (overlap with {ref.overlap_with}: {', '.join(ref.paths)})" if ref.overlap_with else ""
                findings.append(
                    Finding(
                        code="MRS-DRAIN-016",
                        severity=Severity.WARN,
                        message=(f"station {slug!r}: wave {wave_id} refused {ref.story!r}: {ref.reason}{overlap}"),
                    )
                )
            if wave.members:
                wave_detail = f"wave {wave_id}: {', '.join(wave.members)} (max_parallel={parallel_cap})"

        if not stories_to_dispatch:
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus(plan.outcome.value),
                    remaining=len(backlog),
                    skipped=plan.skipped,
                )
            )
            continue

        dispatched_any = False
        in_flight_any = False
        refused_any = False
        last_detail: str | None = wave_detail
        primary_story = stories_to_dispatch[0]
        pending = list(stories_to_dispatch)
        seen_dispatch: set[str] = set()
        while pending:
            story = pending.pop(0)
            if story in seen_dispatch:
                continue
            seen_dispatch.add(story)
            try:
                attempt = dispatch_once(
                    slug=slug,
                    story=story,
                    fs=fs,
                    vcs=vcs,
                    build_harness=build_harness,
                    process=process,
                    policy_flags=policy_flags,
                    parallel_dispatch=parallel_cap > 1,
                )
            except (VcsCommandError, FsError, ProcessError, OSError, ValueError) as exc:
                reason = f"dispatch raised {type(exc).__name__}: {exc}"
                findings.append(
                    Finding(
                        code="MRS-DRAIN-011",
                        severity=Severity.ERROR,
                        message=(
                            f"station {slug!r}: dispatching {story!r} "
                            f"failed unexpectedly -- {reason}. The station is "
                            "left in backlog and the rest of the fleet continues."
                        ),
                    )
                )
                campaign_blocked.setdefault(slug, {})[story] = reason
                refused_any = True
                last_detail = reason
                continue
            status, detail, attempt_findings = _classify_attempt(slug, story, attempt)
            findings.extend(attempt_findings)
            if status is dispatch_fleet.StationCycleStatus.REFUSED:
                campaign_blocked.setdefault(slug, {})[story] = detail or "dispatch refused"
                refused_any = True
                if parallel_cap <= 1 and dispatch_fleet.is_harness_done_advance_reason(detail or ""):
                    follow_blocked, follow_classes = _station_blocked_map(
                        fs=fs,
                        vcs=vcs,
                        process=process,
                        repo_root=repo_root,
                        slug=slug,
                        backlog=backlog,
                        configured_skips=station_skips,
                        campaign_blocked=campaign_blocked.get(slug, {}),
                        effective_policy=effective_policy,
                    )
                    follow = dispatch_fleet.plan_station_queue(
                        slug=slug,
                        backlog=backlog,
                        mode=mode,
                        leave_remaining=leave_remaining,
                        blocked=follow_blocked,
                        block_classes=follow_classes,
                        retry_environment_blocks=retry_environment_blocks,
                        declared_skips=station_skips,
                    )
                    if follow.next_story and follow.next_story not in seen_dispatch:
                        pending.append(follow.next_story)
                        findings.append(
                            Finding(
                                code="MRS-DRAIN-004",
                                severity=Severity.WARN,
                                message=(
                                    f"station {slug!r}: skipping story {story!r} "
                                    "(harness-done CAP-4 (MRS-DISP-040); "
                                    "remaining backlog continues) -- "
                                    f"{detail}. Dispatching {follow.next_story!r} "
                                    "this cycle."
                                ),
                            )
                        )
            elif status is dispatch_fleet.StationCycleStatus.DISPATCHED:
                dispatched_any = True
            elif status is dispatch_fleet.StationCycleStatus.IN_FLIGHT:
                in_flight_any = True
            if detail:
                last_detail = detail

        if dispatched_any:
            cycle_status = dispatch_fleet.StationCycleStatus.DISPATCHED
        elif in_flight_any:
            cycle_status = dispatch_fleet.StationCycleStatus.IN_FLIGHT
        elif refused_any:
            cycle_status = dispatch_fleet.StationCycleStatus.REFUSED
        else:
            cycle_status = dispatch_fleet.StationCycleStatus.IN_FLIGHT
        refuse_predicate_payload: dict[str, str] | None = None
        if cycle_status is dispatch_fleet.StationCycleStatus.REFUSED and last_detail:
            gate = dispatch_re_preflight.parse_refuse_gate(last_detail)
            if dispatch_re_preflight.is_re_preflightable_gate(gate):
                assert gate is not None
                predicate = dispatch_re_preflight.compute_refuse_predicate(
                    repo_root=repo_root,
                    slug=slug,
                    story=primary_story,
                    gate=gate,
                    verify_commands=effective_policy.verify_commands.value,
                )
                refuse_predicate_payload = _predicate_payload(predicate)
        results.append(
            dispatch_fleet.StationCycleResult(
                slug=slug,
                status=cycle_status,
                remaining=len(backlog),
                story=primary_story,
                detail=last_detail,
                skipped=plan.skipped,
                refuse_predicate=refuse_predicate_payload,
            )
        )

    unresolved = dispatch_fleet.unresolved_stations(results)
    data: dict[str, object] = {
        "mode": mode.value,
        "stations": [result.to_payload() for result in results],
        "remaining_total": sum(result.remaining for result in results),
        "dispatched": [
            result.slug for result in results if result.status is dispatch_fleet.StationCycleStatus.DISPATCHED
        ],
        # What `complete` does NOT mean: `complete` is "this campaign can do
        # nothing more", and these stations still have work marshal could not
        # take (unreadable ledger, blocked head story, everything skipped,
        # `leave_one`'s deliberate tail).
        "unresolved": [{"station": r.slug, "status": r.status.value, "remaining": r.remaining} for r in unresolved],
    }
    return FleetCycleReport(results=tuple(results), findings=tuple(findings), data=data)


def _campaign_blocked_from_journal(
    fs: FsPort, run_dir: Path, run_id: str
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, dispatch_re_preflight.RefusePredicate]]]:
    """Rebuild campaign blocks and last refuse predicates from the journal.

    Campaign state lives in the journal (the Spec's in-repo store), never in
    a driver process's memory: each cycle runs in its own process under the
    detached supervisor, and without this a station whose queued story was
    refused for a non-liveness reason (no tracked spec, an unlaunchable
    harness) would be retried on every single tick forever.
    """
    blocked: dict[str, dict[str, str]] = {}
    predicates: dict[str, dict[str, dispatch_re_preflight.RefusePredicate]] = {}
    try:
        text = fs.read_text(run_dir / _JOURNAL_FILENAME)
    except FsError, ValueError:
        return blocked, predicates
    if text is None:
        return blocked, predicates
    lines = text.split("\n")
    # AD-30 sidecars are NOT optional on this read side. A cycle payload
    # carries one row per station plus every skip reason and refusal detail,
    # and eight stations cross `SIDECAR_THRESHOLD_BYTES` (4 KiB) well before
    # a real campaign finishes -- at which point `prepare_for_write` writes
    # the payload to `blobs/` and leaves a `{"sidecar_ref": ...}` pointer.
    # Folding without resolving those pointers quarantines the very entries
    # this function exists to read, so a station refused for a non-liveness
    # reason (no tracked spec) would be silently retried on every 60 s tick
    # forever and the campaign could never report itself complete.
    # Deferred import, matching `cli/deploy.py`'s own `.gate` convention: a
    # module-level `from .gate import ...` here would be load-order fragile
    # (gate -> spin -> dispatch). The helper is reused rather than re-copied.
    from .gate import _sidecar_refs_for_fold

    sidecars: dict[str, str | None] = {}
    for ref in _sidecar_refs_for_fold(lines):
        try:
            sidecars[ref] = fs.read_text(run_dir / ref)
        except FsError, ValueError:
            sidecars[ref] = None
    folded = fold(lines, sidecars=sidecars)
    for entry in folded.by_kind(dispatch_fleet.KIND_FLEET_CYCLE):
        if entry.run_id != run_id or entry.phase != Phase.OUTCOME:
            continue
        stations = entry.payload.get("stations")
        if not isinstance(stations, list):
            continue
        for row in stations:
            if not isinstance(row, dict):
                continue
            if row.get("status") != dispatch_fleet.StationCycleStatus.REFUSED.value:
                continue
            slug = row.get("station")
            story = row.get("story")
            if not isinstance(slug, str) or not isinstance(story, str):
                continue
            detail = row.get("detail")
            blocked.setdefault(slug, {})[story] = detail if isinstance(detail, str) and detail else "dispatch refused"
            predicate = _predicate_from_payload(row.get("refuse_predicate"))
            if predicate is not None:
                predicates.setdefault(slug, {})[story] = predicate
    return blocked, predicates


def _journal_fleet_cycle(
    fs: FsPort,
    run_dir: Path,
    run_id: str,
    report: FleetCycleReport,
    findings: list[Finding],
) -> None:
    """Journal one cycle's intent/outcome pair under ``pyforge-marshal``.

    ``writer_id`` carries this process's pid, so successive supervised cycles
    (each its own process, all sharing one campaign run id) never collide on
    a journal entry id.
    """
    writer_id = f"fleet-drain-{os.getpid()}"
    intent = build_entry(
        id=JournalEntryId(writer_id, 0),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_fleet.KIND_FLEET_CYCLE,
        phase=Phase.INTENT,
        payload={"mode": report.data.get("mode")},
    )
    outcome = build_entry(
        id=JournalEntryId(writer_id, 1),
        ts=_format_entry_ts(_now_utc()),
        run_id=run_id,
        kind=dispatch_fleet.KIND_FLEET_CYCLE,
        phase=Phase.OUTCOME,
        intent_id=intent.id,
        payload={
            "ok": True,
            "complete": report.complete,
            "stations": [result.to_payload() for result in report.results],
        },
    )
    try:
        _append_entry(fs, run_dir, intent, fsync=True)
        _append_entry(fs, run_dir, outcome, fsync=False)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-009",
                severity=Severity.WARN,
                message=f"the fleet cycle ran but could not be journaled: {exc}",
            )
        )


def _spawn_campaign_supervisor(
    *,
    process: ProcessPort,
    repo_root: Path,
    run_dir: Path,
    run_id: str,
    mode: dispatch_fleet.FleetCampaignMode,
    leave_remaining: int,
    max_cycles: int,
    tick_seconds: int,
    station: str | None = None,
    stories: tuple[str, ...] | None = None,
    harness: str | None = None,
    max_in_flight: int | None = None,
) -> int:
    """Detach the campaign supervisor -- the loop that chains next stories.

    Mirrors the per-story dispatch supervisor's own shape (AD-22/Story 3.4):
    the operator's foreground invocation runs ONE cycle and returns, and all
    waiting lives in ``pyforge.marshal.dispatch_fleet_supervisor`` -- so the
    ~600 s watchdog that killed the hand ritual's busy-waiting parent has
    nothing to kill here. Raises ``ProcessError`` when the spawn fails; the
    cycle that already ran still stands.

    Story 22.11 (FR-193 CAP-10): ``station``/``stories`` are threaded
    through so every SUPERVISED tick re-runs the SAME scoped/sequenced
    campaign -- omitting them here would silently widen a station-scoped or
    explicit-sequence campaign back to fleet-wide/ledger-order on its very
    first re-tick.
    """
    return process.spawn_detached(
        [
            sys.executable,
            "-m",
            "pyforge.marshal.dispatch_fleet_supervisor",
            str(repo_root),
            run_id,
            mode.value,
            str(leave_remaining),
            str(max_cycles),
            str(tick_seconds),
            station or "",
            ",".join(stories) if stories else "",
            harness or "",
            str(max_in_flight) if max_in_flight is not None else "",
        ],
        cwd=repo_root,
        log_path=run_dir / _FLEET_SUPERVISOR_LOG_FILENAME,
    )


def run_fleet_drain(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    vcs: VcsPort | None = None,
    build_harness: BuildHarnessPort | None = None,
    process: ProcessPort | None = None,
    harness: HarnessPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    """``marshal factory drain`` -- the one documented fleet-drain command.

    Runs exactly ONE cycle and returns; unless ``--once`` is given (or the
    campaign is already complete) it then detaches
    ``pyforge.marshal.dispatch_fleet_supervisor``, which re-runs this same
    command on a tick until the campaign completes. Nothing here waits.
    """
    del context
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    build_harness = build_harness if build_harness is not None else BmadBuildHarness()
    process = process if process is not None else PosixProcess()
    harness = harness if harness is not None else resolve_loop_runner()

    findings: list[Finding] = []
    data: dict[str, object] = {}

    try:
        mode = dispatch_fleet.parse_campaign_mode(getattr(args, "mode", None))
    except dispatch_fleet.InvalidCampaignModeError as exc:
        findings.append(Finding(code="MRS-DRAIN-001", severity=Severity.ERROR, message=str(exc)))
        return _emit(args, data, findings, command="factory drain")
    data["mode"] = mode.value

    leave_remaining = max(0, int(getattr(args, "leave_remaining", 1) or 0))
    once = bool(getattr(args, "once", False))
    # A NEGATIVE ceiling is refused rather than clamped: `max(0, -1)` is 0,
    # and 0 means UNBOUNDED here -- silently the opposite of what the
    # operator asked for.
    raw_max_cycles = int(getattr(args, "max_cycles", 0) or 0)
    if raw_max_cycles < 0:
        findings.append(
            Finding(
                code="MRS-DRAIN-001",
                severity=Severity.ERROR,
                message=(
                    f"--max-cycles must be >= 0, got {raw_max_cycles} "
                    "(0 means 'until the campaign completes', so a negative "
                    "value cannot be clamped to it without inverting the ask)"
                ),
            )
        )
        return _emit(args, data, findings, command="factory drain")
    max_cycles = raw_max_cycles
    tick_seconds = max(1, int(getattr(args, "tick_seconds", _FLEET_TICK_SECONDS) or 1))

    try:
        repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-002",
                severity=Severity.ERROR,
                message=f"cannot resolve repository root: {exc}",
            )
        )
        return _emit(args, data, findings, command="factory drain")

    # Story 22.11 (FR-193 CAP-10): --station restricts this campaign to one
    # station's own tracked backlog (unknown-station refusal lives inside
    # `execute_fleet_cycle`, which re-checks it every cycle -- cheap and
    # correct on every supervised tick, not just the first). --stories
    # names an explicit ordered sequence on that station instead of its
    # ledger order; it REQUIRES --station, since a sequence names exactly
    # one station's backlog.
    raw_station = getattr(args, "station", None)
    station: str | None = None
    if raw_station is not None and str(raw_station).strip():
        station = dispatch_fleet.normalize_station_slug(str(raw_station))
        data["station"] = station

    raw_stories = getattr(args, "stories", None)
    explicit_stories: tuple[str, ...] | None = None
    if raw_stories:
        explicit_stories = dispatch_fleet.parse_story_sequence(raw_stories)
        if not explicit_stories:
            findings.append(
                Finding(
                    code="MRS-DISP-032",
                    severity=Severity.ERROR,
                    message="--stories must name at least one non-blank story key",
                )
            )
            return _emit(args, data, findings, command="factory drain")
        data["stories"] = list(explicit_stories)
        if station is None:
            findings.append(
                Finding(
                    code="MRS-DRAIN-014",
                    severity=Severity.ERROR,
                    message=(
                        "--stories requires --station -- an explicit "
                        "sequence names exactly one station's backlog, "
                        "never the whole fleet's"
                    ),
                )
            )
            return _emit(args, data, findings, command="factory drain")

    raw_campaign = getattr(args, "campaign", None)
    if raw_campaign is not None and not _is_safe_campaign_id(str(raw_campaign)):
        # `--campaign` names a DIRECTORY under the campaign runs tree, so an
        # unvalidated value escapes it (`--campaign ../../x`) and `ensure_dir`
        # would happily create it.
        findings.append(
            Finding(
                code="MRS-DRAIN-001",
                severity=Severity.ERROR,
                message=(
                    f"malformed campaign id {raw_campaign!r}: expected the "
                    "run-id shape marshal mints (letters, digits, '.', '_', "
                    "'-'), never a path"
                ),
            )
        )
        return _emit(args, data, findings, command="factory drain")

    if explicit_stories is not None:
        # First cycle of a FRESH campaign only: every named key must
        # already be eligible on the station's tracked backlog before
        # anything is minted or provisioned. A later supervised tick
        # always passes --campaign naming a run this SAME flow already
        # minted, so it is deliberately NOT re-validated then -- a key
        # that legitimately landed (flipped to `done`) between cycles
        # must not be misread as an unknown/invalid one;
        # `explicit_story_backlog`'s own per-cycle re-derivation already
        # drops it correctly. An operator-typed `--campaign` id that
        # never actually ran (no run directory on disk) is still a first
        # launch in every way that matters here, so it is validated like
        # one rather than trusted as a resume (review finding, Story
        # 22.11 patch pass).
        is_resumed = raw_campaign is not None and fs.is_dir(dispatch_fleet.fleet_run_dir(repo_root, str(raw_campaign)))
        if not is_resumed:
            assert station is not None  # enforced above: --stories requires --station
            # Check station liveness BEFORE touching the filesystem for its
            # ledger -- an unknown `--station` must surface as MRS-DRAIN-013
            # ("not among the live stations") rather than as a misleading
            # MRS-DRAIN-015 ledger-read failure (review finding, Story 22.11
            # patch pass; `execute_fleet_cycle` re-checks this too, cheaply,
            # on every cycle).
            live_slugs = dispatch_fleet.fleet_station_slugs(dispatch_core.list_station_slugs(repo_root))
            if station not in live_slugs:
                findings.append(
                    Finding(
                        code="MRS-DRAIN-013",
                        severity=Severity.ERROR,
                        message=(
                            f"unknown station {station!r}: not among the live "
                            f"pyforge stations ({', '.join(live_slugs) or 'none found'})"
                        ),
                    )
                )
                return _emit(args, data, findings, command="factory drain")
            ledger_path = dispatch_fleet.station_ledger_path(repo_root, station)
            try:
                statuses = _station_ledger_statuses(
                    harness=harness, vcs=vcs, repo_root=repo_root, ledger_path=ledger_path
                )
            except (HarnessError, OSError, ValueError) as exc:
                findings.append(
                    Finding(
                        code="MRS-DRAIN-015",
                        severity=Severity.ERROR,
                        message=(
                            f"station {station!r}: cannot read the tracked "
                            f"ledger at {ledger_path}: {exc} -- nothing was "
                            "provisioned"
                        ),
                        path=str(ledger_path),
                    )
                )
                return _emit(args, data, findings, command="factory drain")
            backlog = dispatch_fleet.station_backlog(statuses)
            unresolved = dispatch_fleet.unresolved_story_sequence_keys(explicit_stories, backlog)
            if unresolved:
                findings.append(
                    Finding(
                        code="MRS-DISP-032",
                        severity=Severity.ERROR,
                        message=(
                            f"refusing dispatch: --stories names key(s) unknown "
                            f"or already done on station {station!r}'s tracked "
                            f"backlog: {', '.join(unresolved)} -- nothing was "
                            "provisioned"
                        ),
                    )
                )
                return _emit(args, data, findings, command="factory drain")
            missing_specs = _preflight_explicit_story_specs(repo_root, station, explicit_stories)
            if missing_specs:
                findings.append(
                    Finding(
                        code="MRS-DISP-004",
                        severity=Severity.ERROR,
                        message=(
                            f"refusing dispatch: --stories names key(s) with "
                            f"no tracked spec on station {station!r}: "
                            f"{', '.join(missing_specs)} -- nothing was "
                            "provisioned"
                        ),
                    )
                )
                return _emit(args, data, findings, command="factory drain")

    policy_flags = _policy_flags_from_harness_arg(getattr(args, "harness", None))
    if policy_flags:
        data["harness_preference_override"] = list(policy_flags.get("harness_preference", ()))

    run_id = raw_campaign or mint_run_id(
        dispatch_fleet.FLEET_JOURNAL_SLUG,
        _format_utc_compact(_now_utc()),
        _random_token(),
    )
    data["campaign"] = run_id
    run_dir = dispatch_fleet.fleet_run_dir(repo_root, run_id)
    try:
        fs.ensure_dir(run_dir)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-009",
                severity=Severity.WARN,
                message=f"cannot create campaign run directory {run_dir}: {exc}",
            )
        )

    # The interim runner's singleton-coordinator rule (COORDINATOR.md's
    # hand-maintained STATUS.md owner/state table), made STRUCTURAL: one
    # FLEET-WIDE advisory lock, held for the whole cycle, so two concurrent
    # drains can never both see the same station's slot free and both call
    # `dispatch_once` on it. The lock is deliberately not scoped to the
    # campaign id -- two DIFFERENT campaigns racing is the exact duplicate-
    # dispatch shape this guard exists to prevent. A refusal is cheap to
    # recover from: the detached supervisor simply ticks again.
    try:
        cycle_lock = fs.acquire_advisory_lock(
            dispatch_fleet.fleet_cycle_lock_path(repo_root),
            timeout_s=_FLEET_CYCLE_LOCK_TIMEOUT_S,
        )
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DRAIN-010",
                severity=Severity.ERROR,
                message=(
                    f"another fleet-drain cycle holds the campaign lock "
                    f"(waited {_FLEET_CYCLE_LOCK_TIMEOUT_S}s): {exc}. Exactly "
                    "one drain cycle runs at a time fleet-wide -- nothing was "
                    "dispatched, and no campaign supervisor was spawned."
                ),
            )
        )
        return _emit(args, data, findings, command="factory drain")

    try:
        campaign_blocked, prior_predicates = _campaign_blocked_from_journal(fs, run_dir, run_id)
        campaign_blocked = _reconcile_campaign_blocked(
            vcs=vcs,
            repo_root=repo_root,
            blocked=campaign_blocked,
        )
        campaign_blocked, re_preflight_findings = _reconcile_campaign_blocked_for_re_preflight(
            repo_root=repo_root,
            blocked=campaign_blocked,
            prior_predicates=prior_predicates,
            policy_flags=policy_flags or None,
        )
        findings.extend(re_preflight_findings)
        report = execute_fleet_cycle(
            repo_root=repo_root,
            mode=mode,
            leave_remaining=leave_remaining,
            campaign_blocked=campaign_blocked,
            fs=fs,
            vcs=vcs,
            build_harness=build_harness,
            process=process,
            harness=harness,
            station=station,
            explicit_stories=explicit_stories,
            policy_flags=policy_flags or None,
            max_in_flight=getattr(args, "max_in_flight", None),
            retry_environment_blocks=bool(getattr(args, "retry_environment_blocks", False)),
        )
        _journal_fleet_cycle(fs, run_dir, run_id, report, findings)
    finally:
        try:
            fs.release_advisory_lock(cycle_lock)
        except FsError:
            pass

    data.update(report.data)
    data["complete"] = report.complete
    findings.extend(report.findings)

    if not once and not report.complete:
        try:
            data["supervisor_pid"] = _spawn_campaign_supervisor(
                process=process,
                repo_root=repo_root,
                run_dir=run_dir,
                run_id=run_id,
                mode=mode,
                leave_remaining=leave_remaining,
                max_cycles=max_cycles,
                tick_seconds=tick_seconds,
                station=station,
                stories=explicit_stories,
                harness=getattr(args, "harness", None),
                max_in_flight=getattr(args, "max_in_flight", None),
            )
            data["supervisor_log"] = str(run_dir / _FLEET_SUPERVISOR_LOG_FILENAME)
        except ProcessError as exc:
            # Story 22.11 patch pass: a station-scoped/sequenced campaign's
            # recovery command must repeat --station/--stories, or following
            # this message literally silently widens the resumed cycle back
            # to fleet-wide/ledger-order (review finding).
            recovery_flags = ""
            if station:
                recovery_flags += f" --station {station}"
            if explicit_stories:
                recovery_flags += f" --stories {','.join(explicit_stories)}"
            findings.append(
                Finding(
                    code="MRS-DRAIN-007",
                    severity=Severity.WARN,
                    message=(
                        f"the cycle completed but the campaign supervisor "
                        f"could not be spawned: {exc} -- re-run "
                        f"`marshal factory drain --mode {mode.value}"
                        f"{recovery_flags} --campaign {run_id}` to advance "
                        "THIS campaign (omitting --campaign mints a new one, "
                        "which starts with an empty blocked map and spawns a "
                        "second supervisor)"
                    ),
                )
            )

    if getattr(args, "format", "text") != "json":
        try:
            print(dispatch_fleet.render_cycle_summary(report.results), flush=True)
        except OSError, UnicodeEncodeError:
            _suppress_downstream_pipe_close()
    return _emit(args, data, findings, command="factory drain")
