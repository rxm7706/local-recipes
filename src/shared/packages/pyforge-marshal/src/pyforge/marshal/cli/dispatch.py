"""``marshal factory dispatch`` (Story 22.1, FR-193 CAP-1) -- launch exactly
one worktree-isolated ``bmad-build-auto`` session under marshal governance."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from pyforge.core.process import PosixProcess, ProcessPort

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadbuild import BmadBuildHarness, BuildHarnessError
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import dispatch as dispatch_core
from ..core import policy
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

_JOURNAL_FILENAME = "journal.jsonl"
_LOG_FILENAME = "session.log"
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


def latest_dispatch_run_dir(repo_root: Path, slug: str) -> Path | None:
    runs_parent = dispatch_core.dispatch_runs_dir(repo_root, slug)
    if not runs_parent.is_dir():
        return None
    candidates = [child for child in runs_parent.iterdir() if child.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


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
    folded = fold(text.splitlines(), {})
    story_key: str | None = None
    session_pid: int | None = None
    model: str | None = None
    worktree_path: str | None = None
    launched_at: datetime | None = None
    for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH):
        if entry.phase == Phase.INTENT:
            story_key = entry.payload.get("story_key")
            if isinstance(story_key, str):
                story_key = story_key
            model_val = entry.payload.get("model")
            model = model_val if isinstance(model_val, str) else None
            wt = entry.payload.get("worktree_path")
            worktree_path = wt if isinstance(wt, str) else None
            try:
                launched_at = datetime.fromisoformat(
                    entry.ts.replace("Z", "+00:00")
                )
            except ValueError:
                launched_at = None
        elif entry.phase == Phase.OUTCOME:
            pid_val = entry.payload.get("session_pid")
            if isinstance(pid_val, int):
                session_pid = pid_val
            elif isinstance(pid_val, str) and pid_val.isdigit():
                session_pid = int(pid_val)
    return dispatch_core.DispatchJournalFacts(
        story_key=story_key if isinstance(story_key, str) else None,
        session_pid=session_pid,
        model=model,
        launched_at=launched_at,
        worktree_path=worktree_path,
    )


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

    return _emit(args, data, findings)
