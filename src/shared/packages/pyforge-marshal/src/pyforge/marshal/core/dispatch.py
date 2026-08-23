"""Pure dispatch path helpers and journal kinds (Story 22.1, FR-193 CAP-1)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .identity import StoryKey, normalize, render_filename_slug
from .policy import EffectivePolicy

KIND_DISPATCH_LAUNCH = "dispatch-launch"

_DISPATCH_RUNS_DIRNAME = "dispatch-runs"
_WORKTREES_DIRNAME = ".worktrees"
_DISPATCH_WORKTREE_PREFIX = "dispatch-"


@dataclass(frozen=True)
class DispatchJournalFacts:
    """Facts recovered from a dispatch run's journal (Story 22.1)."""

    story_key: str | None
    session_pid: int | None
    model: str | None
    launched_at: datetime | None
    worktree_path: str | None


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
