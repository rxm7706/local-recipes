"""Structure-graph dispatch provisioning benchmark (Story 28.31).

Pure comparison and artifact shaping for the dispatch-worktree spike:
measure ``codegraph init -y`` wall-clock and index size against the
estimated token cost of file navigation without a graph for the same
representative story. The recommendation — build per-worktree, share a
repo-level index via ``init``/``sync``, or stay spin-only — is derived
from the comparison, not assumed.

Follows Story 28.5's benchmark-artifact discipline (pinned inputs,
reproducible JSON, no subprocess in this module — AD-4).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict

LEDGER_KEY = "28-31-structure-graph-codegraph-for-dispatch-provisioning-cost-weighed-against-a-single-story-session"
REPRESENTATIVE_STORY_KEY = "28-31"
ARTIFACT_SCHEMA = "marshal-structure-graph-dispatch-benchmark/v1"
# Same chars/4 heuristic caveman and headroom use for rough token estimates.
CHARS_PER_TOKEN = 4
# Agents re-read, grep, and partially scan — multiplier on manifest bytes.
NAVIGATION_OVERHEAD_FACTOR = 1.5

Recommendation = Literal["build-per-worktree", "share-repo-level-index", "spin-only"]

# Files a dispatch agent reads when implementing Story 28.31 without codegraph.
REPRESENTATIVE_NAVIGATION_PATHS: tuple[str, ...] = (
    "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/"
    "spec-28-31-structure-graph-codegraph-for-dispatch-provisioning-cost-weighed-against-a-single-story-session.md",
    "src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py",
    "src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py",
    "src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/kit.py",
    "src/shared/packages/pyforge-marshal/tests/unit/test_seed_kit.py",
    "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/"
    "spec-28-5-the-pinned-wrapped-vs-unwrapped-benchmark.md",
    "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/"
    "spec-28-33-the-structure-graph-reference-is-wired-for-spin-unblocking-the-already-built-loop-home-index.md",
    "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md",
    "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/token_economy_benchmark.py",
)


class NavigationFileRow(TypedDict):
    relpath: str
    bytes: int
    estimated_tokens: int


@dataclass(frozen=True)
class IndexBuildMeasurement:
    """Live ``codegraph init -y`` facts."""

    wall_clock_seconds: float
    index_bytes: int
    codegraph_reported_seconds: float | None
    files_indexed: int | None
    nodes: int | None
    edges: int | None
    llm_tokens: int = 0  # provisioning is subprocess-only; always zero


@dataclass(frozen=True)
class NavigationMeasurement:
    """Estimated file-navigation cost without a graph."""

    manifest_bytes: int
    estimated_tokens: int
    overhead_factor: float
    files: tuple[NavigationFileRow, ...]


@dataclass(frozen=True)
class SyncMeasurement:
    """Optional ``codegraph sync -q`` facts when a base index exists."""

    wall_clock_seconds: float


@dataclass(frozen=True)
class BenchmarkArtifact:
    schema: str
    ledger_key: str
    representative_story_key: str
    measured_at: str
    environment_digest: str
    index_build: IndexBuildMeasurement
    navigation_without_graph: NavigationMeasurement
    sync_from_base: SyncMeasurement | None
    recommendation: Recommendation
    recommendation_rationale: str
    loop_home_reference: Mapping[str, object] | None

    def to_json_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["index_build"] = asdict(self.index_build)
        payload["navigation_without_graph"] = asdict(self.navigation_without_graph)
        if self.sync_from_base is not None:
            payload["sync_from_base"] = asdict(self.sync_from_base)
        return payload


def estimate_tokens_from_bytes(num_bytes: int) -> int:
    return max(0, num_bytes // CHARS_PER_TOKEN)


def measure_navigation_without_graph(
    repo_root: Path,
    *,
    paths: Sequence[str] = REPRESENTATIVE_NAVIGATION_PATHS,
    overhead_factor: float = NAVIGATION_OVERHEAD_FACTOR,
) -> NavigationMeasurement:
    """Sum manifest file bytes and apply the exploration overhead factor."""
    rows: list[NavigationFileRow] = []
    total_bytes = 0
    for relpath in paths:
        path = repo_root / relpath
        if not path.is_file():
            continue
        nbytes = path.stat().st_size
        total_bytes += nbytes
        rows.append(
            {
                "relpath": relpath,
                "bytes": nbytes,
                "estimated_tokens": estimate_tokens_from_bytes(nbytes),
            }
        )
    base_tokens = estimate_tokens_from_bytes(total_bytes)
    estimated = int(base_tokens * overhead_factor)
    return NavigationMeasurement(
        manifest_bytes=total_bytes,
        estimated_tokens=estimated,
        overhead_factor=overhead_factor,
        files=tuple(rows),
    )


def derive_recommendation(
    *,
    index_build: IndexBuildMeasurement,
    navigation: NavigationMeasurement,
    sync_from_base: SyncMeasurement | None,
) -> tuple[Recommendation, str]:
    """Compare provisioning cost against single-story navigation savings.

    Token savings from codegraph are modeled conservatively as 60% of the
    navigation manifest (queries replace bulk file reads). Wall-clock is
    compared against a 60s dispatch provisioning budget per worktree.
    """
    estimated_savings_tokens = int(navigation.estimated_tokens * 0.6)
    init_seconds = index_build.wall_clock_seconds
    sync_seconds = sync_from_base.wall_clock_seconds if sync_from_base else None

    if estimated_savings_tokens < 5000:
        return (
            "spin-only",
            "Estimated navigation cost without a graph is below 5k tokens "
            f"({navigation.estimated_tokens} with overhead) — not enough to "
            f"justify even a {init_seconds:.1f}s index build for a single "
            "dispatch session.",
        )

    if sync_seconds is not None and sync_seconds < init_seconds * 0.5:
        return (
            "share-repo-level-index",
            f"A shared base index plus ``codegraph sync -q`` ({sync_seconds:.1f}s) "
            f"costs far less than a fresh ``codegraph init -y`` ({init_seconds:.1f}s, "
            f"{index_build.index_bytes // (1024 * 1024)}MiB) while the same story "
            f"would spend ~{navigation.estimated_tokens} tokens on unaided file "
            f"navigation (~{estimated_savings_tokens} recoverable). "
            "``seed/verbs/kit.py`` already distinguishes init (create) from sync "
            "(refresh) — dispatch should copy or reference the loop-home/primary "
            "``.codegraph/`` and sync, not init per worktree.",
        )

    if init_seconds > 60 and estimated_savings_tokens < navigation.estimated_tokens:
        return (
            "share-repo-level-index",
            f"Fresh init ({init_seconds:.1f}s) exceeds a 60s per-worktree budget "
            f"while navigation savings (~{estimated_savings_tokens} tokens) remain "
            "positive — share one repo-level index rather than init per dispatch "
            "worktree.",
        )

    if init_seconds <= 60 and estimated_savings_tokens >= navigation.estimated_tokens // 2:
        return (
            "build-per-worktree",
            f"Init ({init_seconds:.1f}s, {index_build.index_bytes // (1024 * 1024)}MiB) "
            f"is under the 60s budget and saves ~{estimated_savings_tokens} tokens "
            f"against ~{navigation.estimated_tokens} unaided navigation — building "
            "per dispatch worktree is net-positive for a single-story session.",
        )

    return (
        "spin-only",
        "Provisioning cost and navigation savings are inconclusive on the "
        "conservative model — keep structure-graph spin-only for dispatch until "
        "a live dispatch session records actual graph-hit telemetry.",
    )


def digest_environment(environment: Mapping[str, object]) -> str:
    blob = json.dumps(environment, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def build_artifact(
    *,
    index_build: IndexBuildMeasurement,
    navigation: NavigationMeasurement,
    sync_from_base: SyncMeasurement | None,
    environment: Mapping[str, object],
    loop_home_reference: Mapping[str, object] | None = None,
) -> BenchmarkArtifact:
    recommendation, rationale = derive_recommendation(
        index_build=index_build,
        navigation=navigation,
        sync_from_base=sync_from_base,
    )
    return BenchmarkArtifact(
        schema=ARTIFACT_SCHEMA,
        ledger_key=LEDGER_KEY,
        representative_story_key=REPRESENTATIVE_STORY_KEY,
        measured_at=datetime.now(tz=UTC).isoformat(),
        environment_digest=digest_environment(environment),
        index_build=index_build,
        navigation_without_graph=navigation,
        sync_from_base=sync_from_base,
        recommendation=recommendation,
        recommendation_rationale=rationale,
        loop_home_reference=loop_home_reference,
    )


def default_artifact_path(project_root: Path, project_slug: str) -> Path:
    return (
        project_root
        / "_bmad-output/projects"
        / project_slug
        / "planning-artifacts"
        / "benchmarks"
        / "structure-graph-dispatch-28-31.json"
    )
