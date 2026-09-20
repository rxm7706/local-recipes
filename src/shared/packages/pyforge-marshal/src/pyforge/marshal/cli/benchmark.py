"""``marshal benchmark`` (Story 28.5, SPEC-marshal-token-economy CAP-9).

Builds the pinned wrapped-vs-unwrapped comparison artifact from two recorded
benchmark legs (layers off vs on). Live orchestration of both harness runs
is out of scope here — operators record each leg's ``state.json`` /
``usage_snapshot`` facts, then ``compare`` materializes the artifact.

The artifact lands under the project's Tier-3 ``implementation-artifacts/``
directory by default; ceiling recalibration notes cite this file.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_text

from ..adapters.harness_bmadloop import BmadLoopHarness
from ..core import policy
from ..core import structure_graph_dispatch_benchmark as sg_bench
from ..core import token_economy_benchmark as bench
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.harness import HarnessPort, RunStatusSnapshot
from .config import _suppress_downstream_pipe_close, repo_root
from .seed import resolve_context_layers


def add_benchmark_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "benchmark",
        help="Token-economy wrapped-vs-unwrapped benchmark (Story 28.5, CAP-9).",
        description=(
            "Build a per-layer before/after weighted-token comparison artifact "
            "from two recorded legs of the pinned benchmark story — layers off, "
            "then layers on. The equivalence gate voids the comparison when the "
            "on-leg does not match the off-leg's verdict, gate results, or "
            "reviewer engagement."
        ),
    )
    benchmark_sub = parser.add_subparsers(dest="benchmark_command", required=True)

    compare = benchmark_sub.add_parser(
        "compare",
        help="Build the comparison artifact from two legs.",
    )
    compare.add_argument(
        "--project",
        required=True,
        metavar="SLUG",
        help="BMAD project slug (e.g. pyforge-marshal).",
    )
    compare.add_argument(
        "--off",
        required=True,
        metavar="PATH",
        help="JSON file with the layers-off leg record, or a bmad-loop run id.",
    )
    compare.add_argument(
        "--on",
        required=True,
        metavar="PATH",
        help="JSON file with the layers-on leg record, or a bmad-loop run id.",
    )
    compare.add_argument(
        "--home",
        default=None,
        metavar="PATH",
        help=(
            "Loop home path when --off/--on name run ids instead of JSON files "
            "(default: loop/<project> under repo root)."
        ),
    )
    compare.add_argument(
        "--story",
        default=bench.PINNED_BENCHMARK_STORY_KEY,
        metavar="KEY",
        help=f"Pinned story key (default: {bench.PINNED_BENCHMARK_STORY_KEY}).",
    )
    compare.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help=(
            "Artifact output path (default: "
            "_bmad-output/projects/<slug>/implementation-artifacts/"
            "token-economy-benchmark-<timestamp>.json)."
        ),
    )
    compare.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Stdout format (default: text).",
    )
    compare.set_defaults(handler=run_benchmark_compare)

    measure_sg = benchmark_sub.add_parser(
        "structure-graph-dispatch",
        help="Measure dispatch structure-graph provisioning vs navigation (Story 28.31).",
    )
    measure_sg.add_argument(
        "--project",
        required=True,
        metavar="SLUG",
        help="BMAD project slug (e.g. pyforge-marshal).",
    )
    measure_sg.add_argument(
        "--index-build-seconds",
        type=float,
        required=True,
        metavar="SECS",
        help="Measured wall-clock seconds for ``codegraph init -y``.",
    )
    measure_sg.add_argument(
        "--index-bytes",
        type=int,
        required=True,
        metavar="BYTES",
        help="Measured ``.codegraph/codegraph.db`` size in bytes.",
    )
    measure_sg.add_argument(
        "--sync-seconds",
        type=float,
        default=None,
        metavar="SECS",
        help="Optional measured wall-clock seconds for ``codegraph sync -q``.",
    )
    measure_sg.add_argument(
        "--codegraph-reported-seconds",
        type=float,
        default=None,
        metavar="SECS",
        help="Optional seconds reported by codegraph init stdout.",
    )
    measure_sg.add_argument(
        "--files-indexed",
        type=int,
        default=None,
        metavar="N",
        help="Optional files-indexed count from codegraph init stdout.",
    )
    measure_sg.add_argument(
        "--nodes",
        type=int,
        default=None,
        metavar="N",
        help="Optional node count from codegraph init stdout.",
    )
    measure_sg.add_argument(
        "--edges",
        type=int,
        default=None,
        metavar="N",
        help="Optional edge count from codegraph init stdout.",
    )
    measure_sg.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help=(
            "Artifact output path (default: "
            "_bmad-output/projects/<slug>/planning-artifacts/benchmarks/"
            "structure-graph-dispatch-28-31.json)."
        ),
    )
    measure_sg.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Stdout format (default: text).",
    )
    measure_sg.set_defaults(handler=run_structure_graph_dispatch_measure)


def default_artifact_path(project_root: Path, project_slug: str) -> Path:
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H%M%SZ")
    return (
        project_root
        / "_bmad-output/projects"
        / project_slug
        / "implementation-artifacts"
        / f"token-economy-benchmark-{stamp}.json"
    )


def collect_leg_from_harness(
    *,
    home: Path,
    run_id: str,
    story_key: str,
    layers_mode: bench.LayersMode,
    context_layers: Mapping[str, Mapping[str, object]],
    harness: HarnessPort,
    policy_digest: str | None = None,
    cache_read_weight: float = bench.DEFAULT_CACHE_READ_WEIGHT,
) -> bench.BenchmarkLegRecord:
    """Collect one leg's facts from a completed harness run directory."""
    usage = harness.usage_snapshot(home, run_id)
    snapshot = harness.run_status_snapshot(home, run_id)
    if usage is None or snapshot is None:
        raise ValueError(f"could not read usage/status snapshot for run {run_id!r} under {home}")
    task_phase, reviewer_ran = _task_facts(home, run_id, snapshot, story_key)
    gate_fingerprint = tuple(sorted(snapshot.sweeps_refused.keys()))
    return bench.BenchmarkLegRecord(
        layers_mode=layers_mode,
        story_key=story_key,
        task_phase=task_phase,
        reviewer_ran=reviewer_ran,
        gate_fingerprint=gate_fingerprint,
        story_weighted_tokens=usage.story_weighted_tokens,
        run_weighted_tokens=usage.run_weighted_tokens,
        cache_read_weight=cache_read_weight,
        layer_savings=usage.layer_savings,
        context_layers=context_layers,
        run_id=run_id,
        policy_digest=policy_digest,
        story_cost_estimate_usd=usage.cost_estimate_usd,
        layer_savings_usd=usage.layer_savings_usd,
    )


def _task_facts(home: Path, run_id: str, snapshot: RunStatusSnapshot, story_key: str) -> tuple[str, bool]:
    review_cycle = _review_cycle_from_state(home, run_id, story_key)
    for task in snapshot.tasks:
        if task.story_key == story_key:
            reviewer_ran = review_cycle > 0 or _reviewer_ran_from_phase(task.phase)
            return task.phase, reviewer_ran
    return "missing", False


def _review_cycle_from_state(home: Path, run_id: str, story_key: str) -> int:
    state_path = home / ".bmad-loop" / "runs" / run_id / "state.json"
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError, TypeError, ValueError:
        return 0
    tasks = payload.get("tasks")
    if not isinstance(tasks, Mapping):
        return 0
    for task in tasks.values():
        if not isinstance(task, Mapping):
            continue
        if task.get("story_key") == story_key:
            try:
                return int(task.get("review_cycle") or 0)
            except TypeError, ValueError:
                return 0
    return 0


def _reviewer_ran_from_phase(phase: str) -> bool:
    return phase in {"done", "review", "review-verify", "review_verify"}


def _load_leg(
    spec: str,
    *,
    home: Path,
    story_key: str,
    layers_mode: bench.LayersMode,
    context_layers: Mapping[str, Mapping[str, object]],
    harness: HarnessPort,
    policy_digest: str | None,
) -> bench.BenchmarkLegRecord:
    path = Path(spec)
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        leg = bench.leg_from_mapping(payload)
        if leg.layers_mode != layers_mode:
            raise ValueError(f"{path}: layers_mode={leg.layers_mode!r} expected {layers_mode!r}")
        return leg
    return collect_leg_from_harness(
        home=home,
        run_id=spec,
        story_key=story_key,
        layers_mode=layers_mode,
        context_layers=context_layers,
        harness=harness,
        policy_digest=policy_digest,
    )


def run_structure_graph_dispatch_measure(args: argparse.Namespace) -> int:
    """Materialize the Story 28.31 spike benchmark artifact from live measurements."""
    findings: list[Finding] = []
    root = repo_root()
    slug = str(args.project).strip()

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-BENCH-001",
                severity=Severity.HARD,
                message=f"invalid project slug: {slug!r}",
            )
        )
        return _emit_sg(args, findings, {})

    index_build = sg_bench.IndexBuildMeasurement(
        wall_clock_seconds=float(args.index_build_seconds),
        index_bytes=int(args.index_bytes),
        codegraph_reported_seconds=args.codegraph_reported_seconds,
        files_indexed=args.files_indexed,
        nodes=args.nodes,
        edges=args.edges,
    )
    navigation = sg_bench.measure_navigation_without_graph(root)
    sync_from_base = (
        sg_bench.SyncMeasurement(wall_clock_seconds=float(args.sync_seconds)) if args.sync_seconds is not None else None
    )
    environment: dict[str, object] = {
        "repo_root": str(root),
        "project_slug": slug,
        "representative_story_key": sg_bench.REPRESENTATIVE_STORY_KEY,
        "navigation_manifest_paths": list(sg_bench.REPRESENTATIVE_NAVIGATION_PATHS),
        "chars_per_token": sg_bench.CHARS_PER_TOKEN,
        "navigation_overhead_factor": sg_bench.NAVIGATION_OVERHEAD_FACTOR,
    }
    loop_home_reference = {
        "source": "marshal preflight pyforge-marshal (2026-09-10 live reference)",
        "wall_clock_seconds": 21,
        "index_bytes": 229 * 1024 * 1024,
        "note": "Loop-home index amortizes across many stories; dispatch is one story.",
    }
    artifact = sg_bench.build_artifact(
        index_build=index_build,
        navigation=navigation,
        sync_from_base=sync_from_base,
        environment=environment,
        loop_home_reference=loop_home_reference,
    )
    output = Path(args.output).resolve() if args.output else sg_bench.default_artifact_path(root, slug)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            output,
            json.dumps(artifact.to_json_dict(), indent=2, sort_keys=True),
        )
    except OSError as exc:
        findings.append(
            Finding(
                code="MRS-BENCH-003",
                severity=Severity.HARD,
                message=f"could not write benchmark artifact to {output}: {exc}",
            )
        )
        return _emit_sg(args, findings, {})

    data: dict[str, object] = {
        "artifact_path": str(output),
        "recommendation": artifact.recommendation,
        "recommendation_rationale": artifact.recommendation_rationale,
        "index_build_seconds": artifact.index_build.wall_clock_seconds,
        "navigation_estimated_tokens": artifact.navigation_without_graph.estimated_tokens,
    }
    return _emit_sg(args, findings, data)


def _emit_sg(args: argparse.Namespace, findings: list[Finding], data: dict[str, object]) -> int:
    verdict = compute_verdict(findings)
    envelope = build_envelope(
        command="benchmark structure-graph-dispatch",
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
            print(f"structure-graph-dispatch recommendation={data.get('recommendation')} verdict={envelope.verdict}")
            if data.get("artifact_path"):
                print(f"artifact: {data['artifact_path']}")
            if data.get("recommendation_rationale"):
                print(f"rationale: {data['recommendation_rationale']}")
            for finding in findings:
                print(f"{finding.code} {finding.severity.value}: {finding.message}")
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def run_benchmark_compare(
    args: argparse.Namespace,
    *,
    harness: HarnessPort | None = None,
) -> int:
    findings: list[Finding] = []
    root = repo_root()
    slug = str(args.project).strip()
    story_key = str(args.story).strip()
    home = Path(args.home).resolve() if args.home else root / "loop" / slug

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-BENCH-001",
                severity=Severity.HARD,
                message=f"invalid project slug: {slug!r}",
            )
        )
        return _emit(args, findings, {})

    context_layers = resolve_context_layers(root, slug)
    policy_digest = bench.digest_context_layers(context_layers)
    harness = harness or BmadLoopHarness()

    try:
        off_leg = _load_leg(
            args.off,
            home=home,
            story_key=story_key,
            layers_mode="off",
            context_layers=context_layers,
            harness=harness,
            policy_digest=policy_digest,
        )
        on_leg = _load_leg(
            args.on,
            home=home,
            story_key=story_key,
            layers_mode="on",
            context_layers=context_layers,
            harness=harness,
            policy_digest=policy_digest,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        findings.append(
            Finding(
                code="MRS-BENCH-002",
                severity=Severity.HARD,
                message=f"could not load benchmark leg: {exc}",
            )
        )
        return _emit(args, findings, {})

    environment: dict[str, object] = {
        "repo_root": str(root),
        "project_slug": slug,
        "loop_home": str(home),
        "pinned_story_key": story_key,
        "cache_read_weight": bench.DEFAULT_CACHE_READ_WEIGHT,
    }
    artifact = bench.build_artifact(
        off_leg=off_leg,
        on_leg=on_leg,
        environment=environment,
        policy_digest=policy_digest,
    )
    output = Path(args.output).resolve() if args.output else default_artifact_path(root, slug)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(output, json.dumps(artifact.to_json_dict(), indent=2, sort_keys=True))
    except OSError as exc:
        findings.append(
            Finding(
                code="MRS-BENCH-003",
                severity=Severity.HARD,
                message=f"could not write benchmark artifact to {output}: {exc}",
            )
        )
        return _emit(args, findings, {})

    if artifact.void:
        findings.append(
            Finding(
                code="MRS-BENCH-004",
                severity=Severity.WARN,
                message=(
                    "equivalence gate failed — comparison artifact written but void: "
                    + "; ".join(artifact.equivalence_gate.reasons)
                ),
            )
        )

    data: dict[str, object] = {
        "artifact_path": str(output),
        "void": artifact.void,
        "equivalence_passed": artifact.equivalence_gate.passed,
        "totals": dict(artifact.totals),
        "layer_comparison": list(artifact.layer_comparison),
    }
    return _emit(args, findings, data)


def _emit(args: argparse.Namespace, findings: list[Finding], data: dict[str, object]) -> int:
    verdict = compute_verdict(findings)
    envelope = build_envelope(
        command="benchmark compare",
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
            _print_text(data, findings, envelope.verdict, void=bool(data.get("void")))
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _print_text(
    data: dict[str, object],
    findings: list[Finding],
    verdict: object,
    *,
    void: bool,
) -> None:
    print(f"benchmark compare void={void} equivalence_passed={data.get('equivalence_passed')} verdict={verdict}")
    if data.get("artifact_path"):
        print(f"artifact: {data['artifact_path']}")
    totals = data.get("totals")
    if isinstance(totals, Mapping):
        print(
            "weighted tokens: "
            f"before={totals.get('weighted_tokens_before')} "
            f"after={totals.get('weighted_tokens_after')} "
            f"delta={totals.get('weighted_tokens_delta')}"
        )
    layers = data.get("layer_comparison")
    if isinstance(layers, list) and layers:
        print("per-layer:")
        for row in layers:
            if not isinstance(row, Mapping):
                continue
            print(
                f"  - {row.get('layer')}: savings before={row.get('savings_before')} after={row.get('savings_after')}"
            )
    for finding in findings:
        print(f"{finding.code} {finding.severity.value}: {finding.message}")
