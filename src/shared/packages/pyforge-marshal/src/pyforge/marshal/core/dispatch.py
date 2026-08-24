"""Pure dispatch path helpers and journal kinds (Story 22.1, FR-193 CAP-1).

Story 22.5 (FR-193 CAP-5) adds declared-surface overlap detection for
cross-station concurrent dispatch advisories.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .identity import StoryKey, normalize, render_filename_slug
from .policy import EffectivePolicy

KIND_DISPATCH_LAUNCH = "dispatch-launch"
KIND_DISPATCH_SUPERVISOR_ATTACH = "dispatch-supervisor-attach"
KIND_DISPATCH_COMPLETION = "dispatch-completion"
KIND_DISPATCH_VERIFICATION = "dispatch-verification"
KIND_DISPATCH_LAND = "dispatch-land"

_DISPATCH_RUNS_DIRNAME = "dispatch-runs"
_WORKTREES_DIRNAME = ".worktrees"
_DISPATCH_WORKTREE_PREFIX = "dispatch-"


@dataclass(frozen=True)
class DispatchJournalFacts:
    """Facts recovered from a dispatch run's journal (Story 22.1/22.2)."""

    story_key: str | None
    session_pid: int | None
    model: str | None
    launched_at: datetime | None
    worktree_path: str | None
    baseline_head_sha: str | None = None
    supervisor_pid: int | None = None
    completion_verdict: str | None = None
    verification_verdict: str | None = None
    verification_failed_gate: str | None = None
    landing_verdict: str | None = None
    harness_self_report_shipped: bool = False


def canonical_repo_root(repo_root: Path) -> Path:
    return repo_root.resolve()


def planning_specs_dir(repo_root: Path, slug: str) -> Path:
    return (
        canonical_repo_root(repo_root)
        / "_bmad-output"
        / "projects"
        / slug
        / "planning-artifacts"
        / "specs"
    )


def dispatch_runs_dir(repo_root: Path, slug: str) -> Path:
    return (
        canonical_repo_root(repo_root)
        / "_bmad-output"
        / "projects"
        / slug
        / "implementation-artifacts"
        / _DISPATCH_RUNS_DIRNAME
    )


def dispatch_run_dir(repo_root: Path, slug: str, run_id: str) -> Path:
    return dispatch_runs_dir(repo_root, slug) / run_id


def story_spec_candidates(repo_root: Path, slug: str, key: StoryKey) -> list[Path]:
    specs = planning_specs_dir(repo_root, slug)
    stem = f"spec-{render_filename_slug(key)}"
    try:
        titled = sorted(specs.glob(f"{stem}-*.md"))
    except OSError:
        titled = []
    return [specs / f"{stem}.md", *titled]


def resolve_story_spec_path(repo_root: Path, slug: str, story: str) -> Path | None:
    try:
        key = normalize(story)
    except ValueError:
        return None
    for candidate in story_spec_candidates(repo_root, slug, key):
        if candidate.is_file():
            return candidate
    return None


_DIFFICULTY_RE = re.compile(
    r"^difficulty:\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*$", re.MULTILINE
)


def read_declared_difficulty(spec_text: str) -> str | None:
    match = _DIFFICULTY_RE.search(spec_text.replace("\r\n", "\n").replace("\r", "\n"))
    return match.group(1) if match else None


def resolve_dispatch_model(
    policy: EffectivePolicy, *, difficulty: str | None
) -> str | None:
    tier_map = policy.model_tier_map.value
    if not isinstance(tier_map, Mapping) or not tier_map:
        return None
    chosen = difficulty if difficulty in tier_map else None
    if chosen is None:
        for fallback in ("default", "medium", "standard"):
            if fallback in tier_map:
                chosen = fallback
                break
        if chosen is None:
            chosen = next(iter(tier_map))
    stages = tier_map.get(chosen)
    if not isinstance(stages, Mapping):
        return None
    for stage in ("dev", "build", "implement"):
        model = stages.get(stage)
        if isinstance(model, str) and model:
            return model
    for model in stages.values():
        if isinstance(model, str) and model:
            return model
    return None


def build_budget_env(policy: EffectivePolicy) -> dict[str, str]:
    seed = policy.seed_view()
    env: dict[str, str] = {}
    for key in (
        "max_tokens_per_story",
        "max_tokens_per_run",
        "max_wall_clock_minutes_per_story",
        "max_wall_clock_minutes_per_run",
    ):
        field = seed.get(key)
        if field is not None:
            env[f"MARSHAL_{key.upper()}"] = str(field.value)
    return env


def dispatch_worktree_branch(story_key: str) -> str:
    return f"marshal/{story_key}"


def dispatch_worktree_path(repo_root: Path, slug: str, story_key: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", story_key).strip("-") or "story"
    return canonical_repo_root(repo_root) / _WORKTREES_DIRNAME / f"{_DISPATCH_WORKTREE_PREFIX}{slug}-{safe}"


def sanitize_worktree_name(repo_root: Path, slug: str, story_key: str) -> str:
    return dispatch_worktree_path(repo_root, slug, story_key).name


def list_station_slugs(repo_root: Path) -> tuple[str, ...]:
    """BMAD project slugs under ``_bmad-output/projects/`` (Story 22.5)."""
    projects = canonical_repo_root(repo_root) / "_bmad-output" / "projects"
    if not projects.is_dir():
        return ()
    try:
        return tuple(sorted(p.name for p in projects.iterdir() if p.is_dir()))
    except OSError:
        return ()


def _glob_probe_paths(glob: str) -> tuple[str, ...]:
    """Sample concrete paths a glob might match (overlap heuristic only)."""
    cleaned = glob.rstrip("/")
    if cleaned.endswith("/**"):
        base = cleaned[:-3]
        return (base, f"{base}/x", f"{base}/x/y")
    if cleaned.endswith("/*"):
        base = cleaned[:-2]
        return (base, f"{base}/x")
    if any(ch in cleaned for ch in "*?[]"):
        concrete = cleaned.replace("**", "x").replace("*", "x").replace("?", "x")
        return (concrete,)
    return (cleaned,)


def declared_globs_overlap(glob_a: str, glob_b: str) -> bool:
    """True when two declared surface globs could match the same path."""
    if glob_a == glob_b:
        return True
    stem_a = glob_a.rstrip("*").rstrip("/")
    stem_b = glob_b.rstrip("*").rstrip("/")
    if stem_a == stem_b:
        return True
    if stem_a.startswith(stem_b + "/") or stem_b.startswith(stem_a + "/"):
        return True
    for probe in _glob_probe_paths(glob_a) + _glob_probe_paths(glob_b):
        if fnmatch.fnmatch(probe, glob_a) and fnmatch.fnmatch(probe, glob_b):
            return True
    return False


def find_declared_surface_overlaps(
    left: tuple[str, ...] | None,
    right: tuple[str, ...] | None,
) -> tuple[tuple[str, str], ...]:
    """Pairs of overlapping globs between two declared surfaces (Story 22.5)."""
    if left is None or right is None:
        return ()
    pairs: list[tuple[str, str]] = []
    for glob_a in left:
        for glob_b in right:
            if declared_globs_overlap(glob_a, glob_b):
                pairs.append((glob_a, glob_b))
    return tuple(pairs)


def format_surface_overlap_advisory(
    *,
    in_flight_station: str,
    in_flight_story_key: str,
    requested_station: str,
    requested_story_key: str,
    overlapping: tuple[tuple[str, str], ...],
) -> str:
    pair_desc = ", ".join(f"{left!r} ∩ {right!r}" for left, right in overlapping)
    return (
        "LOUD ADVISORY: declared frozen surfaces overlap between in-flight "
        f"story {in_flight_story_key!r} on station {in_flight_station!r} and "
        f"requested dispatch {requested_story_key!r} on "
        f"{requested_station!r}: {pair_desc}"
    )
