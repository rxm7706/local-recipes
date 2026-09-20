"""``marshal refresh`` (Story 15.1, FR-133..FR-135, AD-21) -- one command
that refreshes every BMAD loop home from ``main``.

For each discovered ``loop/<slug>`` worktree (the SAME fleet enumeration
``marshal status``/``retire`` already use -- never a hardcoded station
list): report the home's behind-count vs ``origin/<base>`` (an unreadable
home is reported, never silently omitted); fast-forward ONLY a clean tree
(dirty homes refused by name; never force-push; never ``scripts/bmad-switch``);
push the updated branch targeting ``loop/<slug>`` only; re-render
``.bmad-loop/policy.toml`` via the SAME ``write_policy_toml`` path
``marshal config --write-harness-policy`` uses; regenerate the station's
Tier-3 ``sprint-status.yaml`` from its tracked ``epics.md`` (the
``sprint_plan.py generate`` script ``bmad-sprint-planning`` itself uses --
found live 2026-09-10 that nothing kept this in sync with
``sprint-status-ledger.yaml``, so ``marshal factory spin``/``bmad-loop``
silently saw a stale story set while ``marshal factory dispatch``/
``bmad-build-auto`` correctly read the tracked ledger). Each step reports
``done | skipped | failed``. A home whose fast-forward succeeded but whose
policy re-render did not is marked ``incomplete`` (FR-135).

Finding codes:
- ``MRS-REFRESH-001`` -- malformed ``--project`` (UNEVALUABLE)
- ``MRS-REFRESH-002`` -- fleet enumerate/fetch failure, or unreadable home
- ``MRS-REFRESH-003`` -- dirty-tree refusal / FF failure / push failure
- ``MRS-REFRESH-006`` -- harness-policy re-render failure
- ``MRS-REFRESH-007`` -- FF succeeded without successful re-render (incomplete)
- ``MRS-REFRESH-008`` -- sprint-status.yaml regeneration failure

No Story 15.2 ledger-promotion scope.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError

from ..adapters.harness_bmadloop import HarnessPolicyWriteError, write_policy_toml
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import policy as policy_core
from ..core.context import slug_from_loop_branch
from ..core.model import Finding, Severity, build_envelope
from ..core.refresh import (
    STEP_FAST_FORWARD,
    STEP_PUSH,
    STEP_RENDER_POLICY,
    STEP_SYNC_STATUS,
    HomeRefreshResult,
    RefreshStep,
    home_result_to_dict,
    is_incomplete_refresh,
    ordered_steps,
)
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.vcs import VcsPort
from .config import (
    PolicyIOError,
    _read_project_policy,
    _suppress_downstream_pipe_close,
    conventional_project_policy_path,
)

_MRS_REFRESH_001 = "MRS-REFRESH-001"
_MRS_REFRESH_002 = "MRS-REFRESH-002"
_MRS_REFRESH_003 = "MRS-REFRESH-003"
_MRS_REFRESH_006 = "MRS-REFRESH-006"
_MRS_REFRESH_007 = "MRS-REFRESH-007"
_MRS_REFRESH_008 = "MRS-REFRESH-008"

_DEFAULT_BASE = "main"
_SYNC_STATUS_TIMEOUT_S = 60


def add_refresh_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "refresh",
        help=(
            "Refresh every loop home from main: behind-count, fast-forward, "
            "push loop/<slug>, re-render harness policy (FR-133..135)."
        ),
        description=(
            "For every currently-attached loop/<slug> worktree (or just "
            "--project SLUG): report commits behind origin/<base>, "
            "fast-forward clean trees only (dirty refused by name; never "
            "force-push), push loop/<slug> only, and re-render "
            ".bmad-loop/policy.toml as a checked step."
        ),
    )
    parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help="Scope the refresh to one project slug (default: the whole fleet).",
    )
    parser.add_argument(
        "--base",
        default=_DEFAULT_BASE,
        metavar="BRANCH",
        help=f"Remote branch to fetch/fast-forward from (default: {_DEFAULT_BASE}).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_refresh)


def _compose_effective(slug: str) -> policy_core.EffectivePolicy:
    """Compose EffectivePolicy for ``slug`` (same path as ``marshal config``)."""
    project_data: dict[str, object] = {}
    if policy_core._is_valid_project_slug(slug):
        candidate = conventional_project_policy_path(slug)
        try:
            present = candidate.is_file()
        except OSError:
            present = True
        if present:
            try:
                project_data = dict(_read_project_policy(candidate))
            except PolicyIOError:
                project_data = {}
    effective, _findings = policy_core.compose(project_slug=slug, project=project_data, flags={})
    return effective


def _render_policy_step(slug: str, home: Path, findings: list[Finding]) -> RefreshStep:
    try:
        effective = _compose_effective(slug)
        written = write_policy_toml(effective, home)
        return RefreshStep(STEP_RENDER_POLICY, "done", f"wrote {written}")
    except (HarnessPolicyWriteError, OSError, ValueError) as exc:
        findings.append(
            Finding(
                code=_MRS_REFRESH_006,
                severity=Severity.WARN,
                message=f"home {slug!r}: harness policy re-render failed: {exc}",
                path=str(home),
            )
        )
        return RefreshStep(STEP_RENDER_POLICY, "failed", str(exc))


def _sync_status_step(slug: str, git_repo_root: Path, findings: list[Finding]) -> RefreshStep:
    """Regenerate ``slug``'s Tier-3 ``sprint-status.yaml`` from its tracked
    ``epics.md``, via the same script ``bmad-sprint-planning`` uses. Writes
    to the SHARED physical ``_bmad-output/projects/<slug>/`` location every
    worktree symlinks to -- independent of any loop home's own git state, so
    this runs on every call regardless of the fast-forward outcome above."""
    project_dir = git_repo_root / "_bmad-output" / "projects" / slug
    epic_file = project_dir / "planning-artifacts" / "epics.md"
    if not epic_file.is_file():
        return RefreshStep(STEP_SYNC_STATUS, "skipped", "no epics.md")
    script = git_repo_root / ".claude" / "skills" / "bmad-sprint-planning" / "scripts" / "sprint_plan.py"
    if not script.is_file():
        return RefreshStep(STEP_SYNC_STATUS, "skipped", "sprint_plan.py not found")
    impl_dir = project_dir / "implementation-artifacts"
    argv = [
        "uv",
        "run",
        str(script),
        "generate",
        "--epic-file",
        str(epic_file),
        "--status-file",
        str(impl_dir / "sprint-status.yaml"),
        "--stories-dir",
        str(impl_dir),
        "--project",
        slug,
        "--date",
        datetime.now().strftime("%m-%d-%Y %H:%M"),
    ]
    # Story 52.1 (SPEC-pyforge-core CAP-6): routed through the ONE sanctioned
    # subprocess seam. `PosixProcess.run` never raises for a non-zero exit
    # (that case is classified below) and raises `ProcessError` for the
    # launch/timeout failures the raw `(OSError, subprocess.TimeoutExpired)`
    # clause used to catch. Two seam deltas are intentional: `stdin=DEVNULL`
    # (a child that prompts reads EOF instead of hanging) and
    # `encoding="utf-8", errors="replace"` (undecodable output is replaced,
    # never raised as a decode error).
    try:
        result = PosixProcess().run(argv, cwd=git_repo_root, timeout_s=_SYNC_STATUS_TIMEOUT_S)
    except ProcessError as exc:
        findings.append(
            Finding(
                code=_MRS_REFRESH_008,
                severity=Severity.WARN,
                message=f"home {slug!r}: sprint-status sync failed to launch: {exc}",
                path=str(project_dir),
            )
        )
        return RefreshStep(STEP_SYNC_STATUS, "failed", str(exc))
    try:
        report = json.loads(result.stdout) if result.stdout else {}
    except json.JSONDecodeError:
        report = {}
    if result.returncode != 0 or not report.get("ok"):
        detail = report.get("error") or result.stderr.strip() or result.stdout.strip()
        findings.append(
            Finding(
                code=_MRS_REFRESH_008,
                severity=Severity.WARN,
                message=f"home {slug!r}: sprint-status sync failed: {detail}",
                path=str(project_dir),
            )
        )
        return RefreshStep(STEP_SYNC_STATUS, "failed", detail)
    new_entries = report.get("new_entries") or []
    detail = f"{len(new_entries)} new entries" if new_entries else "in sync"
    return RefreshStep(STEP_SYNC_STATUS, "done", detail)


def _refresh_one_home(
    *,
    vcs: VcsPort,
    git_repo_root: Path,
    slug: str,
    home: Path,
    tip_ref: str,
    findings: list[Finding],
) -> HomeRefreshResult:
    branch = f"loop/{slug}"
    path_str = str(home)

    behind_count: int | None = None
    current_ref: str | None = None
    try:
        current_ref = vcs.worktree_head_sha(home)
        behind_count = vcs.commits_behind(home, tip_ref)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_REFRESH_002,
                severity=Severity.WARN,
                message=f"home {slug!r} at {home} is unreadable: {exc}",
                path=path_str,
            )
        )
        steps = ordered_steps(
            fast_forward=RefreshStep(STEP_FAST_FORWARD, "skipped", "home unreadable"),
            push=RefreshStep(STEP_PUSH, "skipped", "home unreadable"),
            render_policy=RefreshStep(STEP_RENDER_POLICY, "skipped", "home unreadable"),
            sync_status=_sync_status_step(slug, git_repo_root, findings),
        )
        return HomeRefreshResult(
            slug=slug,
            path=path_str,
            branch=branch,
            readable=False,
            behind_count=None,
            current_ref=None,
            steps=steps,
            incomplete=False,
            refused_reason=f"unreadable: {exc}",
        )

    try:
        dirty = vcs.has_uncommitted_changes(home)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_REFRESH_003,
                severity=Severity.WARN,
                message=f"home {slug!r}: cannot probe working-tree dirt: {exc}",
                path=path_str,
            )
        )
        steps = ordered_steps(
            fast_forward=RefreshStep(STEP_FAST_FORWARD, "failed", f"dirt probe failed: {exc}"),
            push=RefreshStep(STEP_PUSH, "skipped", "fast-forward did not succeed"),
            render_policy=RefreshStep(STEP_RENDER_POLICY, "skipped", "dirt probe failed"),
            sync_status=_sync_status_step(slug, git_repo_root, findings),
        )
        return HomeRefreshResult(
            slug=slug,
            path=path_str,
            branch=branch,
            readable=True,
            behind_count=behind_count,
            current_ref=current_ref,
            steps=steps,
            incomplete=False,
            refused_reason="dirty-probe-failed",
        )

    if dirty:
        findings.append(
            Finding(
                code=_MRS_REFRESH_003,
                severity=Severity.WARN,
                message=(
                    f"home {slug!r} at {home} has a dirty working tree -- "
                    "refusing fast-forward (FR-134); never force-pushed"
                ),
                path=path_str,
            )
        )
        render_step = _render_policy_step(slug, home, findings)
        steps = ordered_steps(
            fast_forward=RefreshStep(STEP_FAST_FORWARD, "failed", "dirty working tree"),
            push=RefreshStep(STEP_PUSH, "skipped", "fast-forward refused"),
            render_policy=render_step,
            sync_status=_sync_status_step(slug, git_repo_root, findings),
        )
        return HomeRefreshResult(
            slug=slug,
            path=path_str,
            branch=branch,
            readable=True,
            behind_count=behind_count,
            current_ref=current_ref,
            steps=steps,
            incomplete=is_incomplete_refresh(steps),
            refused_reason="dirty",
        )

    if behind_count == 0:
        ff_step = RefreshStep(STEP_FAST_FORWARD, "skipped", f"already current with {tip_ref}")
    else:
        try:
            new_sha = vcs.fast_forward(home, tip_ref)
            current_ref = new_sha
            ff_step = RefreshStep(
                STEP_FAST_FORWARD,
                "done",
                f"fast-forwarded to {tip_ref} ({new_sha[:12]})",
            )
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_REFRESH_003,
                    severity=Severity.WARN,
                    message=(f"home {slug!r}: fast-forward to {tip_ref} failed: {exc}"),
                    path=path_str,
                )
            )
            render_step = _render_policy_step(slug, home, findings)
            steps = ordered_steps(
                fast_forward=RefreshStep(STEP_FAST_FORWARD, "failed", str(exc)),
                push=RefreshStep(STEP_PUSH, "skipped", "fast-forward did not succeed"),
                render_policy=render_step,
                sync_status=_sync_status_step(slug, git_repo_root, findings),
            )
            return HomeRefreshResult(
                slug=slug,
                path=path_str,
                branch=branch,
                readable=True,
                behind_count=behind_count,
                current_ref=current_ref,
                steps=steps,
                incomplete=is_incomplete_refresh(steps),
                refused_reason=f"fast-forward failed: {exc}",
            )

    if ff_step.status == "done":
        try:
            # Push via the shared repo root; branch name is loop/<slug> only.
            vcs.push(git_repo_root, branch)
            push_step = RefreshStep(STEP_PUSH, "done", f"pushed {branch} to origin")
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_REFRESH_003,
                    severity=Severity.WARN,
                    message=f"home {slug!r}: push of {branch} failed: {exc}",
                    path=path_str,
                )
            )
            push_step = RefreshStep(STEP_PUSH, "failed", str(exc))
    else:
        push_step = RefreshStep(STEP_PUSH, "skipped", "nothing new to push")

    render_step = _render_policy_step(slug, home, findings)
    steps = ordered_steps(
        fast_forward=ff_step,
        push=push_step,
        render_policy=render_step,
        sync_status=_sync_status_step(slug, git_repo_root, findings),
    )
    incomplete = is_incomplete_refresh(steps)
    if incomplete:
        findings.append(
            Finding(
                code=_MRS_REFRESH_007,
                severity=Severity.WARN,
                message=(
                    f"home {slug!r}: fast-forwarded but harness policy was "
                    "not re-rendered -- incompletely refreshed (FR-135)"
                ),
                path=path_str,
            )
        )
    return HomeRefreshResult(
        slug=slug,
        path=path_str,
        branch=branch,
        readable=True,
        behind_count=behind_count,
        current_ref=current_ref,
        steps=steps,
        incomplete=incomplete,
        refused_reason=None,
    )


def _render_text(homes: list[dict[str, object]], findings: tuple[Finding, ...]) -> str:
    lines: list[str] = []
    if not homes:
        lines.append("no loop homes found")
    for home in homes:
        slug = home.get("slug", "?")
        behind = home.get("behind_count")
        behind_s = "?" if behind is None else str(behind)
        flag = " INCOMPLETE" if home.get("incomplete") else ""
        refused = home.get("refused_reason")
        refused_s = f" refused={refused}" if refused else ""
        lines.append(f"{slug}: behind={behind_s}{flag}{refused_s}")
        for step in home.get("steps") or ():
            if not isinstance(step, dict):
                continue
            detail = step.get("detail") or ""
            detail_s = f" ({detail})" if detail else ""
            lines.append(f"  {step.get('name')}: {step.get('status')}{detail_s}")
    for finding in findings:
        lines.append(f"[{finding.severity.value}] {finding.code}: {finding.message}")
    return "\n".join(lines)


def run_refresh(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
) -> int:
    """Fleet-homes refresh entry point (Story 15.1)."""
    findings: list[Finding] = []
    base = getattr(args, "base", None) or _DEFAULT_BASE
    data: dict[str, object] = {"base": base, "homes": []}
    if vcs is None:
        vcs = GitVcs()

    tip_ref = f"origin/{base}"

    if args.project is not None and not policy_core._is_valid_project_slug(args.project):
        findings.append(
            Finding(
                code=_MRS_REFRESH_001,
                severity=Severity.ERROR,
                message=(f"malformed --project {args.project!r} -- expected a plain project slug (no path separators)"),
            )
        )
        return _emit(args, data, findings)

    try:
        git_repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_REFRESH_002,
                severity=Severity.WARN,
                message=f"cannot resolve the repo root: {exc}",
            )
        )
        return _emit(args, data, findings)

    data["repo_root"] = str(git_repo_root)

    try:
        worktrees = vcs.list_worktrees(git_repo_root)
    except VcsCommandError as exc:
        findings.append(
            Finding(
                code=_MRS_REFRESH_002,
                severity=Severity.WARN,
                message=f"cannot enumerate loop-home worktrees: {exc}",
            )
        )
        return _emit(args, data, findings)

    fleet: list[tuple[str, Path]] = []
    for entry in worktrees:
        slug = slug_from_loop_branch(entry.branch)
        if slug is None:
            continue
        if args.project is not None and slug != args.project:
            continue
        fleet.append((slug, entry.path))

    if fleet:
        try:
            vcs.fetch(git_repo_root, "origin", base)
        except VcsCommandError as exc:
            findings.append(
                Finding(
                    code=_MRS_REFRESH_002,
                    severity=Severity.WARN,
                    message=f"cannot fetch origin/{base}: {exc}",
                )
            )
            return _emit(args, data, findings)

    homes_out: list[dict[str, object]] = []
    for slug, home in fleet:
        result = _refresh_one_home(
            vcs=vcs,
            git_repo_root=git_repo_root,
            slug=slug,
            home=home,
            tip_ref=tip_ref,
            findings=findings,
        )
        homes_out.append(home_result_to_dict(result))

    data["homes"] = homes_out
    return _emit(args, data, findings)


def _emit(
    args: argparse.Namespace,
    data: dict[str, object],
    findings: list[Finding],
) -> int:
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="refresh",
        verdict=verdict_value,
        data=data,
        findings=findings,
    )
    try:
        if getattr(args, "format", "text") == "json":
            print(
                json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True),
                flush=True,
            )
        else:
            print(
                _render_text(
                    list(data.get("homes") or []),  # type: ignore[arg-type]
                    envelope.findings,
                ),
                flush=True,
            )
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)
