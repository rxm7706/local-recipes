"""``marshal factory dispatch`` (Story 22.1, FR-193 CAP-1) -- launch exactly
one worktree-isolated ``bmad-build-auto`` session under marshal governance."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadbuild import BmadBuildHarness, BuildHarnessError
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import dispatch as dispatch_core
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
from ..ports.vcs import VcsPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
)

if TYPE_CHECKING:
    from ..core.context import MarshalContext


@dataclass(frozen=True)
class DispatchPreflightConflict:
    """A dispatch refusal with its registered finding code (Story 22.2/22.5)."""

    code: str
    message: str
    in_flight_story_key: str

_JOURNAL_FILENAME = "journal.jsonl"
_LOG_FILENAME = "session.log"
_SUPERVISOR_LOG_FILENAME = "dispatch-supervisor.log"
_BASE_REF = "origin/main"


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


def _emit(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    command = "factory dispatch"
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
    project_data: dict[str, object] = {}
    candidate = conventional_project_policy_path(slug)
    if candidate.is_file():
        try:
            project_data = dict(_read_project_policy(candidate))
        except PolicyIOError:
            project_data = {}
    effective, _findings = policy.compose(project_slug=slug, project=project_data, flags={})
    return effective


def _ensure_dispatch_worktree(
    vcs: VcsPort, repo_root: Path, slug: str, story_key: str
) -> Path:
    branch = dispatch_core.dispatch_worktree_branch(story_key)
    worktree = dispatch_core.dispatch_worktree_path(repo_root, slug, story_key)
    existing = vcs.worktree_path_for_branch(repo_root, branch)
    if existing is not None:
        return existing
    if worktree.exists():
        return worktree
    vcs.add_worktree(repo_root, worktree, branch, base=_BASE_REF)
    return worktree


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
    if journal.baseline_head_sha is None:
        return DispatchSessionVerdict.LIVE if (
            journal.session_pid is not None and process.is_alive(journal.session_pid)
        ) else None
    session_alive = (
        journal.session_pid is not None and process.is_alive(journal.session_pid)
    )
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
    fs = fs if fs is not None else LocalFs()
    vcs = vcs if vcs is not None else GitVcs()
    build_harness = build_harness if build_harness is not None else BmadBuildHarness()
    process = process if process is not None else PosixProcess()

    slug = args.slug
    story = args.story
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug, "story": story}

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-DISP-001",
                severity=Severity.ERROR,
                message=f"malformed project slug {slug!r}",
            )
        )
        return _emit(args, data, findings)

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
        return _emit(args, data, findings)
    data["story_key"] = render_feed_key(story_key)

    if not build_harness.binary_present():
        findings.append(
            Finding(
                code="MRS-DISP-003",
                severity=Severity.ERROR,
                message="session harness binary not found on PATH (cursor)",
            )
        )
        return _emit(args, data, findings)

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
        return _emit(args, data, findings)

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
        return _emit(args, data, findings)
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
        return _emit(args, data, findings)

    effective_policy = _compose_policy(slug)
    difficulty = dispatch_core.read_declared_difficulty(spec_text)
    model = dispatch_core.resolve_dispatch_model(effective_policy, difficulty=difficulty)
    budget_env = dispatch_core.build_budget_env(effective_policy)
    data["model"] = model
    data["budget_env"] = dict(budget_env)

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
        return _emit(args, data, findings)

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
        worktree = _ensure_dispatch_worktree(vcs, repo_root, slug, render_feed_key(story_key))
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code="MRS-DISP-006",
                severity=Severity.ERROR,
                message=f"cannot provision dispatch worktree: {exc}",
            )
        )
        return _emit(args, data, findings)
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
        return _emit(args, data, findings)
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
        return _emit(args, data, findings)

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
        return _emit(args, data, findings)

    log_path = run_dir / _LOG_FILENAME
    data["log"] = str(log_path)
    try:
        launch = build_harness.dispatch(
            worktree,
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
        return _emit(args, data, findings)

    data["session_pid"] = launch.pid
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

    return _emit(args, data, findings)


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
