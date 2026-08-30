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
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadbuild import BmadBuildHarness, BuildHarnessError
from ..adapters.harness_bmadloop import HarnessError, resolve_loop_runner
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import dispatch as dispatch_core
from ..core import dispatch_fleet
from ..core import policy
from ..core.dispatch_completion import (
    DispatchCompletionInput,
    DispatchGitFacts,
    DispatchSessionVerdict,
    judge_dispatch_completion,
    zombie_redispatch_evidence,
)
from ..core.spec_surface import parse_declared_surface
from ..dispatch_supervisor.__main__ import gather_dispatch_git_facts
from ..core.identity import normalize, render_feed_key
from ..core.journal import JournalEntryId, Phase, build_entry, fold, mint_run_id, prepare_for_write
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.build_harness import BuildHarnessPort
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from ..ports.vcs import VcsPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
    read_repo_policy_defaults,
)

if TYPE_CHECKING:
    from ..core.context import MarshalContext


@dataclass(frozen=True)
class DispatchPreflightConflict:
    """A dispatch refusal with its registered finding code (Story 22.2/22.5)."""

    code: str
    message: str
    in_flight_story_key: str


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
            "and returns promptly."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug (station).")
    parser.add_argument("story", help="The backlog story key to dispatch.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
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
    except (OSError, UnicodeEncodeError):
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _compose_policy(slug: str) -> policy.EffectivePolicy:
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
        project_slug=slug, repo_defaults=repo_defaults, project=project_data, flags={}
    )
    return effective


@dataclass(frozen=True)
class DispatchWorktreeResolution:
    """A provisioned dispatch worktree, or the refusal that stopped it (22.9)."""

    branch: str
    worktree: Path | None = None
    legacy: bool = False
    refusal: str | None = None


def _ensure_dispatch_worktree(
    vcs: VcsPort, repo_root: Path, slug: str, story_key: str
) -> DispatchWorktreeResolution:
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
        return DispatchWorktreeResolution(
            branch=resolution.branch, refusal=resolution.refusal
        )
    branch = resolution.effective_branch
    existing = vcs.worktree_path_for_branch(repo_root, branch)
    if existing is not None:
        return DispatchWorktreeResolution(
            branch=branch, worktree=existing, legacy=resolution.legacy
        )
    if worktree.exists():
        return DispatchWorktreeResolution(
            branch=branch, worktree=worktree, legacy=resolution.legacy
        )
    vcs.add_worktree(repo_root, worktree, branch, base=_BASE_REF)
    return DispatchWorktreeResolution(
        branch=branch, worktree=worktree, legacy=resolution.legacy
    )


def iter_dispatch_run_dirs(repo_root: Path, slug: str) -> tuple[Path, ...]:
    runs_parent = dispatch_core.dispatch_runs_dir(repo_root, slug)
    if not runs_parent.is_dir():
        return ()
    return tuple(sorted((p for p in runs_parent.iterdir() if p.is_dir()), key=lambda p: p.name))


def latest_dispatch_run_dir(repo_root: Path, slug: str) -> Path | None:
    dirs = iter_dispatch_run_dirs(repo_root, slug)
    if not dirs:
        return None
    return dirs[-1]


def gather_dispatch_journal_facts(
    fs: FsPort, run_dir: Path, run_id: str
) -> dispatch_core.DispatchJournalFacts:
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
    folded = fold(text.splitlines())
    story_key: str | None = None
    session_pid: int | None = None
    model: str | None = None
    worktree_path: str | None = None
    launched_at: datetime | None = None
    baseline_head_sha: str | None = None
    supervisor_pid: int | None = None
    completion_verdict: str | None = None
    verification_verdict: str | None = None
    verification_failed_gate: str | None = None
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
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_VERIFICATION):
        if entry.phase == Phase.OUTCOME:
            vval = entry.payload.get("verdict")
            if isinstance(vval, str):
                verification_verdict = vval
            gate_val = entry.payload.get("failed_gate")
            if isinstance(gate_val, str):
                verification_failed_gate = gate_val
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
        verification_verdict=verification_verdict,
        verification_failed_gate=verification_failed_gate,
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
) -> DispatchSessionVerdict | None:
    if journal.completion_verdict in {
        DispatchSessionVerdict.COMPLETED.value,
        DispatchSessionVerdict.FAILED.value,
    }:
        return DispatchSessionVerdict(journal.completion_verdict)
    if journal.story_key is None or journal.worktree_path is None:
        return None
    session_alive = (
        journal.session_pid is not None and process.is_alive(journal.session_pid)
    )
    # Independent verification (Story 22.3's dispatch_verify.py -- real gate
    # commands re-run against the worktree, never a self-report) already
    # judged this dispatch REFUSED. Combined with a confirmed-dead process,
    # that is strong, non-self-reported evidence the session is gone, not
    # merely idle -- git.changed_paths staying nonzero forever (once ANY
    # real edit landed before the crash) must not keep judge_dispatch_
    # completion's has_git_progress() reading this LIVE, or a crashed
    # supervisor's last-known-good evidence blocks redispatch indefinitely
    # (live 2026-08-29: atlas Story 21.1's dispatch supervisor crashed on
    # compose_dispatch_policy's tomllib bug, and MRS-DISP-011 kept refusing
    # redispatch on the same 8-changed-paths evidence for hours after).
    # Deliberately gated on session_alive being False too: a session that
    # IS still running with a currently-refused gate (mid-development, not
    # yet green) must stay LIVE -- verification_verdict alone is not proof
    # of death, only the conjunction with a confirmed-dead process is.
    if not session_alive and journal.verification_verdict == "refused":
        return DispatchSessionVerdict.FAILED
    if journal.baseline_head_sha is None:
        return DispatchSessionVerdict.LIVE if session_alive else None
    try:
        git_facts = gather_dispatch_git_facts(
            vcs,
            repo_root=repo_root,
            worktree=Path(journal.worktree_path),
            story_key=journal.story_key,
            project_slug=slug,
            baseline_head_sha=journal.baseline_head_sha,
            merge_subject_template=effective_policy.merge_subject_template.value,
        )
    except (VcsCommandError, ValueError):
        return DispatchSessionVerdict.LIVE if session_alive else None
    return judge_dispatch_completion(
        DispatchCompletionInput(session_alive=session_alive, git=git_facts)
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
        return zombie_redispatch_evidence(
            story_key=story_key,
            verdict=verdict,
            git=DispatchGitFacts(
                baseline_head_sha="",
                current_head_sha="",
                changed_paths=(),
                branch_merged=False,
                story_merged_on_main=False,
            ),
            session_alive=journal.session_pid is not None
            and process.is_alive(journal.session_pid),
            harness_reported_failure=harness_reported_failure,
        ) or f"story {story_key!r} dispatch session is still live"
    git_facts = gather_dispatch_git_facts(
        vcs,
        repo_root=repo_root,
        worktree=Path(journal.worktree_path),
        story_key=journal.story_key,
        project_slug=slug,
        baseline_head_sha=journal.baseline_head_sha,
        merge_subject_template=effective_policy.merge_subject_template.value,
    )
    return zombie_redispatch_evidence(
        story_key=story_key,
        verdict=verdict,
        git=git_facts,
        session_alive=journal.session_pid is not None
        and process.is_alive(journal.session_pid),
        harness_reported_failure=harness_reported_failure,
    ) or f"story {story_key!r} dispatch session is still live"


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
) -> DispatchPreflightConflict | None:
    """Refuse when the station already has any live in-flight story (22.5)."""
    feed_story = render_feed_key(normalize(story_key))
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
        return DispatchPreflightConflict(
            code="MRS-DISP-021",
            message=(
                f"refusing dispatch: station {slug!r} already has in-flight "
                f"story {in_flight!r} ({evidence})"
            ),
            in_flight_story_key=in_flight,
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
            if (
                station_slug == requested_slug
                and journal.story_key == feed_requested
            ):
                continue
            verdict = resolve_dispatch_session_verdict(
                fs=fs,
                vcs=vcs,
                process=process,
                repo_root=repo_root,
                slug=station_slug,
                journal=journal,
                effective_policy=station_policy,
            )
            if verdict != DispatchSessionVerdict.LIVE:
                continue
            in_flight_spec = dispatch_core.resolve_story_spec_path(
                repo_root, station_slug, journal.story_key
            )
            if in_flight_spec is None:
                continue
            try:
                in_flight_text = in_flight_spec.read_text(encoding="utf-8")
            except OSError:
                continue
            in_flight_surface = parse_declared_surface(in_flight_text)
            overlapping = dispatch_core.find_declared_surface_overlaps(
                requested_surface, in_flight_surface
            )
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
    """Evidence that ``story_key``'s most recent dispatch on ``slug`` HALTed.

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
        verdict = resolve_dispatch_session_verdict(
            fs=fs,
            vcs=vcs,
            process=process,
            repo_root=repo_root,
            slug=slug,
            journal=journal,
            effective_policy=effective_policy,
        )
        if verdict == DispatchSessionVerdict.FAILED:
            gate = journal.verification_failed_gate
            detail = f", failed gate {gate}" if gate else ""
            return (
                f"the last dispatch of {feed_story!r} (run {run_dir.name!r}) "
                f"ended 'failed' by git and process facts{detail}"
            )
        return None
    return None


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
    context: MarshalContext | None = None,
) -> int:
    del context
    attempt = dispatch_once(
        slug=args.slug,
        story=args.story,
        fs=fs,
        vcs=vcs,
        build_harness=build_harness,
        process=process,
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

    effective_policy = _compose_policy(slug)
    difficulty = dispatch_core.read_declared_difficulty(spec_text)
    model = dispatch_core.resolve_dispatch_model(effective_policy, difficulty=difficulty)
    budget_env = dispatch_core.build_budget_env(effective_policy)
    data["model"] = model
    data["budget_env"] = dict(budget_env)

    # Story 22.8 (FR-193 CAP-8): profile-aware harness resolution -- the
    # policy's ordered `harness_preference` walked to the first profile
    # whose binary resolves AND whose authcheck passes. Binary presence
    # alone was necessary-but-insufficient (2026-08-27: three real
    # dispatches died on cursor's auth wall with the binary on PATH), so
    # every skipped candidate is a structured finding, never silent.
    preference = tuple(effective_policy.harness_preference.value)
    resolution = build_harness.binary_present(preference, repo_root=repo_root)
    for profile_error in resolution.profile_errors:
        findings.append(
            Finding(code="MRS-DISP-028", severity=Severity.WARN, message=profile_error)
        )
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

    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        story_key=render_feed_key(story_key),
        effective_policy=effective_policy,
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
        provisioned = _ensure_dispatch_worktree(
            vcs, repo_root, slug, render_feed_key(story_key)
        )
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
        },
    )
    try:
        _append_entry(fs, run_dir, outcome_entry, fsync=False)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-009",
                severity=Severity.WARN,
                message=(
                    f"session launched (pid {launch.pid}) but outcome journal "
                    f"write failed: {exc}"
                ),
            )
        )

    if not process.is_alive(launch.pid):
        findings.append(
            Finding(
                code="MRS-DISP-010",
                severity=Severity.WARN,
                message=(
                    f"session harness reported pid {launch.pid} but the "
                    "process is not alive immediately after launch"
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
    session_alive = (
        journal.session_pid is not None and process.is_alive(journal.session_pid)
    )
    supervisor_alive = (
        journal.supervisor_pid is not None
        and process.is_alive(journal.supervisor_pid)
    )
    verdict = resolve_dispatch_session_verdict(
        fs=fs,
        vcs=vcs,
        process=process,
        repo_root=repo_root,
        slug=slug,
        journal=journal,
        effective_policy=effective_policy,
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
                    f"no live dispatch session on station {slug!r} "
                    f"(session pid {journal.session_pid} is not alive)"
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
        except (OSError, UnicodeEncodeError):
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
        except (OSError, UnicodeEncodeError):
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
        except (OSError, UnicodeEncodeError):
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
        except (OSError, UnicodeEncodeError):
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
        "--leave-remaining",
        type=int,
        default=1,
        help=(
            "Under --mode leave_one, how many backlog stories to leave "
            "untouched per station (default: 1)."
        ),
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
    parser.set_defaults(handler=run_fleet_drain)


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
) -> dict[str, str]:
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
    for story in backlog:
        if story in configured_skips:
            continue
        if story in campaign_blocked:
            blocked[story] = campaign_blocked[story]
            continue
        try:
            evidence = station_story_blocked_evidence(
                fs=fs,
                vcs=vcs,
                process=process,
                repo_root=repo_root,
                slug=slug,
                story_key=story,
                effective_policy=effective_policy,
            )
        except (VcsCommandError, ValueError):
            evidence = None
        if evidence is None:
            break
        blocked[story] = evidence
    return blocked


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
    liveness = next(
        (f for f in errors if f.code in {"MRS-DISP-011", "MRS-DISP-021"}), None
    )
    if liveness is not None:
        in_flight = attempt.data.get("in_flight_story")
        findings.append(
            Finding(
                code="MRS-DRAIN-006",
                severity=Severity.WARN,
                message=(
                    f"station {slug!r}: no dispatch this cycle -- "
                    f"{liveness.code} {liveness.message}"
                ),
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
) -> FleetCycleReport:
    """One fleet-drain cycle: plan every station, dispatch the eligible ones."""
    findings: list[Finding] = []
    results: list[dispatch_fleet.StationCycleResult] = []
    overrides, configured_skips, config_findings = _read_fleet_queue_config(fs, repo_root)
    findings.extend(config_findings)

    slugs = dispatch_fleet.fleet_station_slugs(
        dispatch_core.list_station_slugs(repo_root)
    )
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
            statuses = harness.ledger_story_statuses(ledger_path)
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

        backlog = dispatch_fleet.station_backlog(
            statuses, order_override=overrides.get(slug)
        )
        effective_policy = _compose_policy(slug)
        station_skips = configured_skips.get(slug, {})
        blocked = _station_blocked_map(
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
            declared_skips=station_skips,
        )
        for story, reason in plan.skipped:
            basis = (
                "declared skip policy"
                if story in station_skips
                else f"blocked, and {mode.value} skips past it"
            )
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
            findings.append(
                Finding(
                    code="MRS-DRAIN-005",
                    severity=Severity.WARN,
                    message=(
                        f"station {slug!r}: story {plan.blocked_story!r} is "
                        f"blocked -- {plan.blocked_reason}. It stays in the "
                        "backlog, is never auto-retried, and is never forced "
                        f"past; re-run with --mode "
                        f"{dispatch_fleet.FleetCampaignMode.SKIP_ON_BLOCKED.value} "
                        "to move on to this station's next story."
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

        # Per-station isolation: one station's git/fs failure must never
        # abort the cycle, because the loop is alphabetical and an abort
        # would silently starve every station after it -- forever, since the
        # supervisor reproduces the identical crash every tick and no cycle
        # is journaled at all. `dispatch_once` itself converts most failures
        # into findings, but not every path it reaches is guarded (a
        # worktree deleted under a still-live session makes
        # `_live_dispatch_evidence` re-raise `VcsCommandError`), so the
        # station is reported refused and the campaign moves on.
        try:
            attempt = dispatch_once(
                slug=slug,
                story=plan.next_story,
                fs=fs,
                vcs=vcs,
                build_harness=build_harness,
                process=process,
            )
        except (VcsCommandError, FsError, ProcessError, OSError, ValueError) as exc:
            reason = f"dispatch raised {type(exc).__name__}: {exc}"
            findings.append(
                Finding(
                    code="MRS-DRAIN-011",
                    severity=Severity.ERROR,
                    message=(
                        f"station {slug!r}: dispatching {plan.next_story!r} "
                        f"failed unexpectedly -- {reason}. The station is "
                        "left in backlog and the rest of the fleet continues."
                    ),
                )
            )
            campaign_blocked.setdefault(slug, {})[plan.next_story] = reason
            results.append(
                dispatch_fleet.StationCycleResult(
                    slug=slug,
                    status=dispatch_fleet.StationCycleStatus.REFUSED,
                    remaining=len(backlog),
                    story=plan.next_story,
                    detail=reason,
                    skipped=plan.skipped,
                )
            )
            continue
        status, detail, attempt_findings = _classify_attempt(slug, plan.next_story, attempt)
        findings.extend(attempt_findings)
        if status is dispatch_fleet.StationCycleStatus.REFUSED:
            campaign_blocked.setdefault(slug, {})[plan.next_story] = (
                detail or "dispatch refused"
            )
        results.append(
            dispatch_fleet.StationCycleResult(
                slug=slug,
                status=status,
                remaining=len(backlog),
                story=plan.next_story,
                detail=detail,
                skipped=plan.skipped,
            )
        )

    unresolved = dispatch_fleet.unresolved_stations(results)
    data: dict[str, object] = {
        "mode": mode.value,
        "stations": [result.to_payload() for result in results],
        "remaining_total": sum(result.remaining for result in results),
        "dispatched": [
            result.slug
            for result in results
            if result.status is dispatch_fleet.StationCycleStatus.DISPATCHED
        ],
        # What `complete` does NOT mean: `complete` is "this campaign can do
        # nothing more", and these stations still have work marshal could not
        # take (unreadable ledger, blocked head story, everything skipped,
        # `leave_one`'s deliberate tail).
        "unresolved": [
            {"station": r.slug, "status": r.status.value, "remaining": r.remaining}
            for r in unresolved
        ],
    }
    return FleetCycleReport(
        results=tuple(results), findings=tuple(findings), data=data
    )


def _campaign_blocked_from_journal(
    fs: FsPort, run_dir: Path, run_id: str
) -> dict[str, dict[str, str]]:
    """Rebuild "which stations are blocked" from this campaign's own journal.

    Campaign state lives in the journal (the Spec's in-repo store), never in
    a driver process's memory: each cycle runs in its own process under the
    detached supervisor, and without this a station whose queued story was
    refused for a non-liveness reason (no tracked spec, an unlaunchable
    harness) would be retried on every single tick forever.
    """
    blocked: dict[str, dict[str, str]] = {}
    try:
        text = fs.read_text(run_dir / _JOURNAL_FILENAME)
    except (FsError, ValueError):
        return blocked
    if text is None:
        return blocked
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
        except (FsError, ValueError):
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
            blocked.setdefault(slug, {})[story] = (
                detail if isinstance(detail, str) and detail else "dispatch refused"
            )
    return blocked


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
) -> int:
    """Detach the campaign supervisor -- the loop that chains next stories.

    Mirrors the per-story dispatch supervisor's own shape (AD-22/Story 3.4):
    the operator's foreground invocation runs ONE cycle and returns, and all
    waiting lives in ``pyforge.marshal.dispatch_fleet_supervisor`` -- so the
    ~600 s watchdog that killed the hand ritual's busy-waiting parent has
    nothing to kill here. Raises ``ProcessError`` when the spawn fails; the
    cycle that already ran still stands.
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
        findings.append(
            Finding(code="MRS-DRAIN-001", severity=Severity.ERROR, message=str(exc))
        )
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
        report = execute_fleet_cycle(
            repo_root=repo_root,
            mode=mode,
            leave_remaining=leave_remaining,
            campaign_blocked=_campaign_blocked_from_journal(fs, run_dir, run_id),
            fs=fs,
            vcs=vcs,
            build_harness=build_harness,
            process=process,
            harness=harness,
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
            )
            data["supervisor_log"] = str(run_dir / _FLEET_SUPERVISOR_LOG_FILENAME)
        except ProcessError as exc:
            findings.append(
                Finding(
                    code="MRS-DRAIN-007",
                    severity=Severity.WARN,
                    message=(
                        f"the cycle completed but the campaign supervisor "
                        f"could not be spawned: {exc} -- re-run "
                        f"`marshal factory drain --mode {mode.value} "
                        f"--campaign {run_id}` to advance THIS campaign "
                        "(omitting --campaign mints a new one, which starts "
                        "with an empty blocked map and spawns a second "
                        "supervisor)"
                    ),
                )
            )

    if getattr(args, "format", "text") != "json":
        try:
            print(dispatch_fleet.render_cycle_summary(report.results), flush=True)
        except (OSError, UnicodeEncodeError):
            _suppress_downstream_pipe_close()
    return _emit(args, data, findings, command="factory drain")
