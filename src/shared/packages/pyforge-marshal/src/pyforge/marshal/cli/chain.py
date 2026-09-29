"""``marshal chain`` (Story 17.4, FR-148/FR-149/FR-151, AD-72).

Orchestrated planning-chain regeneration for one named project. Nested
``regenerate`` verb mirrors ``deploy``/``seed`` shape. Default is dry-run;
``--apply`` may write the project's tracked sprint-status ledger only after
``scripts/promote_sprint_status.regressions`` clears every pre-existing
``done`` key. Orphans are reported, never deleted.

Finding codes (MRS-CHAIN-*):
- ``MRS-CHAIN-001`` -- missing / unevaluable project planning tree
- ``MRS-CHAIN-002`` -- phase failure mid-chain
- ``MRS-CHAIN-003`` -- done-key regression blocked the ledger write
- ``MRS-CHAIN-004`` -- orphan candidate reported (review-gated; not deleted)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path

from ..core.chain_regen import (
    CHAIN_PHASES,
    PlanPhaseRunner,
    RegenerationReport,
    find_orphans,
    ledger_file,
    parse_ledger_statuses,
    planning_dir,
    run_regeneration,
)
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from .config import _suppress_downstream_pipe_close, repo_root

_MRS_CHAIN_001 = "MRS-CHAIN-001"
_MRS_CHAIN_002 = "MRS-CHAIN-002"
_MRS_CHAIN_003 = "MRS-CHAIN-003"
_MRS_CHAIN_004 = "MRS-CHAIN-004"


def add_chain_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register ``chain`` with nested ``regenerate`` (FR-148)."""
    parser = subparsers.add_parser(
        "chain",
        help=("Orchestrate planning-chain regeneration for one project (FR-148/149/151; AD-72)."),
        description=(
            "Run a named project's Spec→PRD→Architecture→Epics regeneration "
            "in dependency order, preserve done story keys via the existing "
            "sprint-ledger guard, and report orphans for review — never "
            "auto-delete, never scripts/bmad-switch."
        ),
    )
    chain_sub = parser.add_subparsers(dest="chain_command", required=True)
    regen = chain_sub.add_parser(
        "regenerate",
        help="Regenerate one project's planning chain in dependency order.",
        description=(
            "Phases: " + " → ".join(CHAIN_PHASES) + ". Default dry-run; pass --apply to write the ledger when the "
            "done-key guard passes."
        ),
    )
    regen.add_argument(
        "--project",
        required=True,
        metavar="SLUG",
        help="Project slug under _bmad-output/projects/<slug>/ (required).",
    )
    regen.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Write the project's sprint-status-ledger.yaml when regressions() "
            "is empty. Default is dry-run (report only)."
        ),
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
    regen.set_defaults(handler=run_chain_regenerate)


def _load_promote() -> object:
    """Same install-free import as ``cli/deploy._load_promote_sprint_status``."""
    checkout_root = Path(__file__).resolve().parents[8]
    path = checkout_root / "scripts" / "promote_sprint_status.py"
    spec = importlib.util.spec_from_file_location("_promote_sprint_status_chain", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_ledger(path: Path, statuses: Mapping[str, str], *, project: str) -> None:
    promote = _load_promote()
    text = promote.render(project, "implementation-artifacts/sprint-status.yaml", dict(statuses))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_chain_regenerate(args: argparse.Namespace) -> int:
    """CLI entry for ``marshal chain regenerate``."""
    findings: list[Finding] = []
    slug = str(args.project).strip()
    root = Path(args.root).resolve() if args.root else repo_root()
    apply = bool(args.apply)

    planning = planning_dir(root, slug)
    if not planning.is_dir():
        findings.append(
            Finding(
                code=_MRS_CHAIN_001,
                severity=Severity.WARN,
                message=(f"project {slug!r}: planning-artifacts missing under {planning} — unevaluable"),
                path=str(planning),
            )
        )
        return _emit(args, findings, report=None)

    promote = _load_promote()
    lp = ledger_file(root, slug)
    before: dict[str, str] = {}
    if lp.is_file():
        before = parse_ledger_statuses(lp.read_text(encoding="utf-8"))

    runner = PlanPhaseRunner()
    report = run_regeneration(
        root=root,
        project=slug,
        runner=runner,
        regressions_fn=promote.regressions,
        apply=apply,
        statuses_before=before,
        write_ledger=((lambda path, statuses: _write_ledger(path, statuses, project=slug)) if apply else None),
    )

    for outcome in report.phases:
        if outcome.status == "failed":
            findings.append(
                Finding(
                    code=_MRS_CHAIN_002,
                    severity=Severity.ERROR,
                    message=(f"project {slug!r}: phase {outcome.name!r} failed: {outcome.detail}"),
                    path=str(planning),
                )
            )

    if report.regressions_blocked:
        detail = ", ".join(f"{k} ({old}→{new})" for k, old, new in report.regressions_blocked)
        findings.append(
            Finding(
                code=_MRS_CHAIN_003,
                severity=Severity.ERROR,
                message=(f"project {slug!r}: refused ledger write — done-key regressions blocked: {detail}"),
                path=str(lp),
            )
        )

    # Always re-scan so dry-run still surfaces orphans even if runner was noop.
    orphans = report.orphans or find_orphans(root, slug)
    for orphan in orphans:
        findings.append(
            Finding(
                code=_MRS_CHAIN_004,
                severity=Severity.WARN,
                message=f"orphan {orphan.kind}: {orphan.reason}",
                path=orphan.path,
            )
        )

    return _emit(args, findings, report=report)


def _report_to_dict(report: RegenerationReport) -> dict[str, object]:
    return {
        "project": report.project,
        "apply": report.apply,
        "wrote_ledger": report.wrote_ledger,
        "phases": [
            {
                "name": p.name,
                "status": p.status,
                "detail": p.detail,
                "skill": p.skill,
            }
            for p in report.phases
        ],
        "preserved_done_keys": list(report.preserved_done_keys),
        "regressions_blocked": [{"key": k, "old": o, "new": n} for k, o, n in report.regressions_blocked],
        "statuses_before": dict(report.statuses_before),
        "statuses_after": dict(report.statuses_after),
        "orphans": [{"kind": o.kind, "path": o.path, "reason": o.reason} for o in report.orphans],
    }


def _emit(
    args: argparse.Namespace,
    findings: list[Finding],
    *,
    report: RegenerationReport | None,
) -> int:
    verdict = compute_verdict(findings)
    data: dict[str, object] = {}
    if report is not None:
        data["chain_regeneration"] = _report_to_dict(report)
    envelope = build_envelope(
        command="chain regenerate",
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
    report: RegenerationReport | None,
    findings: list[Finding],
    verdict: object,
) -> None:
    if report is None:
        print(f"chain regenerate: verdict={verdict}")
    else:
        mode = "apply" if report.apply else "dry-run"
        print(
            f"chain regenerate [{mode}] project={report.project} wrote_ledger={report.wrote_ledger} verdict={verdict}"
        )
        print("phases:")
        for p in report.phases:
            print(f"  - {p.name}: {p.status} ({p.detail})")
        if report.preserved_done_keys:
            print("preserved_done_keys:")
            for k in report.preserved_done_keys:
                print(f"  - {k}")
        if report.regressions_blocked:
            print("regressions_blocked:")
            for k, o, n in report.regressions_blocked:
                print(f"  - {k}: {o} → {n}")
        if report.orphans:
            print("orphans (not deleted):")
            for o in report.orphans:
                print(f"  - [{o.kind}] {o.path}: {o.reason}")
    for f in findings:
        print(f"{f.code} {f.severity.value}: {f.message}")
