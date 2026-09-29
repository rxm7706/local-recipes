"""``marshal planning`` (Stories 21.2–21.5, FR-192 CAP-1…CAP-5).

Nested ``chain-regenerate`` orchestrates the Full Dream→…→orphan-report
planning chain through the FR-52 ``SkillInvokePort`` seam against any
station by CAP-5 parameters only (``project_slug``, ``dream_path``,
``chain_mode``, ``preserve_code_status``, ``stage``, ``apply_orphans``,
``resume``). Defaults: Full chain, preserve on, stage/apply off.
``auto_commit`` is never offered. Cross-station runs use physical
``_bmad-output/projects/<slug>/…`` paths + ``BMAD_ACTIVE_PROJECT`` per
invoke — never ``scripts/bmad-switch``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Literal

from ..adapters.skill_invoke_harness import PlanSkillInvoker
from ..core.chain_regen import (
    FULL_CHAIN_PHASES,
    OrchestratedChainReport,
    run_orchestrated_chain,
)
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from .config import _suppress_downstream_pipe_close, repo_root

# Reuse Story 17.4 codes where meanings align; 005 is planning-only blocked.
_MRS_PLAN_001 = "MRS-CHAIN-001"  # missing / unevaluable inputs
_MRS_PLAN_002 = "MRS-CHAIN-005"  # skill blocked mid-chain (halt)
_MRS_PLAN_003 = "MRS-CHAIN-002"  # phase failure after retries

ChainModeArg = Literal["full", "minimal"]


def resolve_chain_mode(args: argparse.Namespace) -> ChainModeArg:
    """Resolve CAP-5 ``chain_mode`` from ``--chain-mode`` / ``--minimal``.

    Default is ``full``. ``--minimal`` alone selects ``minimal``. When both
    are present they must agree (``--minimal`` implies ``minimal``).
    """
    explicit = getattr(args, "chain_mode", None)
    minimal_flag = bool(getattr(args, "minimal", False))
    if explicit is None:
        return "minimal" if minimal_flag else "full"
    if minimal_flag and explicit != "minimal":
        raise ValueError(
            f"--minimal conflicts with --chain-mode {explicit!r} (omit --minimal or pass --chain-mode minimal)"
        )
    if explicit not in ("full", "minimal"):
        raise ValueError(f"invalid chain_mode: {explicit!r}")
    return explicit  # type: ignore[return-value]


def add_planning_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register ``planning`` with nested ``chain-regenerate``."""
    parser = subparsers.add_parser(
        "planning",
        help=("Orchestrate planning-chain regeneration (FR-192 CAP-1…CAP-5; Stories 21.2–21.5)."),
        description=(
            "CAP-5: same workflow against any station by parameters only "
            "(project_slug, dream_path, chain_mode, preserve_code_status, "
            "stage, apply_orphans, resume). Never scripts/bmad-switch; "
            "auto_commit is not offered."
        ),
    )
    planning_sub = parser.add_subparsers(dest="planning_command", required=True)
    regen = planning_sub.add_parser(
        "chain-regenerate",
        help=("Regenerate one project's planning chain (CAP-5 parameterized; Full default)."),
        description=(
            "CAP-5 parameters — project_slug (--project), dream_path (--dream), "
            "chain_mode (--chain-mode / --minimal; default full), "
            "preserve_code_status (--preserve-code-status / "
            "--no-preserve-code-status; default true), stage (--stage; "
            "default false), apply_orphans (--apply-orphans; default false), "
            "resume (--resume). auto_commit is not offered (always false). "
            "Physical paths under _bmad-output/projects/<slug>/; never "
            "scripts/bmad-switch. Full phases: " + " → ".join(FULL_CHAIN_PHASES) + "."
        ),
    )
    regen.add_argument(
        "--project",
        required=True,
        metavar="SLUG",
        help=("CAP-5 project_slug: station under _bmad-output/projects/<slug>/ (required)."),
    )
    regen.add_argument(
        "--dream",
        required=True,
        metavar="PATH",
        help="CAP-5 dream_path: Dream markdown (repo-relative or absolute).",
    )
    regen.add_argument(
        "--chain-mode",
        choices=("full", "minimal"),
        default=None,
        dest="chain_mode",
        help=(
            "CAP-5 chain_mode: full (default) or minimal. Mutually consistent "
            "with --minimal; conflict if --minimal and --chain-mode full."
        ),
    )
    regen.add_argument(
        "--minimal",
        action="store_true",
        help=("CAP-5 chain_mode shortcut: skip research and brief (same as --chain-mode minimal)."),
    )
    regen.add_argument(
        "--resume",
        action="store_true",
        help=("CAP-5 resume: continue the latest incomplete .chain-regen journal for --project."),
    )
    regen.add_argument(
        "--root",
        default=None,
        metavar="PATH",
        help=("Repo root to operate on (default: this checkout). Fixtures pass an isolated tree; live runs omit this."),
    )
    regen.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    regen.add_argument(
        "--live",
        action="store_true",
        help=(
            "Use the live session-harness skill invoker (default: plan/dry-run "
            "invoker; no LLM). Sets BMAD_ACTIVE_PROJECT per invoke; never "
            "scripts/bmad-switch."
        ),
    )
    # CAP-2 preserve flag + CAP-4 orphan apply/stage gates (CAP-5 docs in 21.5).
    regen.add_argument(
        "--preserve-code-status",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=("CAP-5 preserve_code_status (CAP-2): keep done/in-progress/backlog across epics regen (default: true)."),
    )
    regen.add_argument(
        "--apply-orphans",
        action="store_true",
        help=(
            "CAP-5 apply_orphans (CAP-4): delete orphaned spec artifacts from "
            "disk after the orphan manifest is written (default: false / "
            "leave on disk). Never commits."
        ),
    )
    regen.add_argument(
        "--stage",
        action="store_true",
        help=(
            "CAP-5 stage (CAP-4): git-add regenerated planning paths and "
            "orphan deletions into the index without committing "
            "(default: false / leave unstaged). auto_commit is not offered."
        ),
    )
    regen.set_defaults(handler=run_planning_chain_regenerate)


def run_planning_chain_regenerate(args: argparse.Namespace) -> int:
    """CLI entry for ``marshal planning chain-regenerate``."""
    findings: list[Finding] = []
    slug = str(args.project).strip()
    root = Path(args.root).resolve() if args.root else repo_root()
    dream = Path(args.dream)
    if not dream.is_absolute():
        dream = (root / dream).resolve()

    if not slug or "/" in slug or "\\" in slug or ".." in slug:
        findings.append(
            Finding(
                code=_MRS_PLAN_001,
                severity=Severity.ERROR,
                message=f"invalid project slug: {slug!r}",
                path=str(root),
            )
        )
        return _emit(args, findings, report=None)

    try:
        mode = resolve_chain_mode(args)
    except ValueError as exc:
        findings.append(
            Finding(
                code=_MRS_PLAN_001,
                severity=Severity.ERROR,
                message=str(exc),
                path="flags: --minimal/--chain-mode",
            )
        )
        return _emit(args, findings, report=None)

    if args.live:
        from ..adapters.skill_invoke_harness import HarnessSkillInvoker

        invoker = HarnessSkillInvoker(live=True)
    else:
        invoker = PlanSkillInvoker()

    try:
        from ..adapters.vcs_git import stage_index_paths

        report = run_orchestrated_chain(
            root=root,
            project=slug,
            dream=dream,
            invoker=invoker,
            mode=mode,
            resume=bool(args.resume),
            auto_commit=False,
            preserve_code_status=bool(args.preserve_code_status),
            apply_orphans=bool(args.apply_orphans),
            stage=bool(args.stage),
            stager=stage_index_paths if args.stage else None,
        )
    except FileNotFoundError as exc:
        findings.append(
            Finding(
                code=_MRS_PLAN_001,
                severity=Severity.ERROR,
                message=str(exc),
                path=str(root),
            )
        )
        return _emit(args, findings, report=None)
    except ValueError as exc:
        findings.append(
            Finding(
                code=_MRS_PLAN_001,
                severity=Severity.ERROR,
                message=str(exc),
                path=str(root),
            )
        )
        return _emit(args, findings, report=None)
    except Exception as exc:  # noqa: BLE001 — envelope, never raw traceback
        from ..adapters.skill_invoke_harness import SkillInvokeError

        if not isinstance(exc, (SkillInvokeError, OSError)):
            raise
        findings.append(
            Finding(
                code=_MRS_PLAN_003,
                severity=Severity.ERROR,
                message=f"skill harness error: {exc}",
                path=str(root),
            )
        )
        return _emit(args, findings, report=None)

    if report.status == "blocked":
        findings.append(
            Finding(
                code=_MRS_PLAN_002,
                severity=Severity.ERROR,
                message=(f"project {slug!r}: chain blocked mid-run (journal at {report.run_dir})"),
                path=report.run_dir,
            )
        )
    elif report.status == "failed":
        findings.append(
            Finding(
                code=_MRS_PLAN_003,
                severity=Severity.ERROR,
                message=(f"project {slug!r}: chain failed mid-run (journal at {report.run_dir})"),
                path=report.run_dir,
            )
        )

    return _emit(args, findings, report=report)


def _report_to_dict(report: OrchestratedChainReport) -> dict[str, object]:
    return {
        "project": report.project,
        "dream": report.dream,
        "mode": report.mode,
        "run_id": report.run_id,
        "run_dir": report.run_dir,
        "status": report.status,
        "auto_commit": report.auto_commit,
        "orphan_manifest_written": report.orphan_manifest_written,
        "preserve_code_status_hook": report.preserve_code_status_hook,
        "apply_orphans_hook": report.apply_orphans_hook,
        "stage_hook": report.stage_hook,
        "phases": [
            {
                "name": p.name,
                "status": p.status,
                "detail": p.detail,
                "skill": p.skill,
                "attempts": p.attempts,
            }
            for p in report.phases
        ],
        "orphans": [{"kind": o.kind, "path": o.path, "reason": o.reason} for o in report.orphans],
    }


def _emit(
    args: argparse.Namespace,
    findings: list[Finding],
    *,
    report: OrchestratedChainReport | None,
) -> int:
    verdict = compute_verdict(findings)
    data: dict[str, object] = {}
    if report is not None:
        data["planning_chain_regeneration"] = _report_to_dict(report)
    envelope = build_envelope(
        command="planning chain-regenerate",
        verdict=verdict,
        data=data,
        findings=tuple(findings),
    )
    try:
        if args.format == "json":
            print(
                json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True),
                flush=True,
            )
        else:
            _print_text(report, findings, envelope.verdict)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _print_text(
    report: OrchestratedChainReport | None,
    findings: list[Finding],
    verdict: object,
) -> None:
    if report is None:
        print(f"planning chain-regenerate: verdict={verdict}")
    else:
        print(
            f"planning chain-regenerate mode={report.mode} "
            f"project={report.project} status={report.status} "
            f"auto_commit={report.auto_commit} verdict={verdict}"
        )
        print(f"run_dir: {report.run_dir}")
        print("phases:")
        for p in report.phases:
            print(f"  - {p.name}: {p.status} (attempts={p.attempts}; {p.detail})")
        if report.orphans:
            print("orphans (not deleted):")
            for o in report.orphans:
                print(f"  - [{o.kind}] {o.path}: {o.reason}")
        print(
            "hooks: "
            f"preserve_code_status={report.preserve_code_status_hook} "
            f"apply_orphans={report.apply_orphans_hook} "
            f"stage={report.stage_hook}"
        )
    for f in findings:
        print(f"{f.code} {f.severity.value}: {f.message}")
