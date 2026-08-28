"""Pure dispatch path helpers and journal kinds (Story 22.1, FR-193 CAP-1).

Story 22.5 (FR-193 CAP-5) adds declared-surface overlap detection for
cross-station concurrent dispatch advisories.

Story 22.9 (FR-193 CAP-2/CAP-5) makes the dispatch BRANCH name carry its
station and puts the derivation here, once: ``dispatch_worktree_branch`` is
the sole site that renders a dispatch branch string, and
``resolve_dispatch_branch`` is the sole site that decides which branch a
station's work actually lives on. Everything else in the package -- worktree
provisioning, the in-flight conflict guard's git facts, and landing --
imports one of the two. The one function that is NOT pure is
``resolve_dispatch_branch``: it must ask git which branches exist, so it
takes a ``VcsPort`` (the same read-only port the CLI already holds) and
performs no writes.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .identity import StoryKey, normalize, render_filename_slug
from .policy import EffectivePolicy

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..ports.vcs import VcsPort

KIND_DISPATCH_LAUNCH = "dispatch-launch"
KIND_DISPATCH_SUPERVISOR_ATTACH = "dispatch-supervisor-attach"
KIND_DISPATCH_OPERATOR_ATTACH = "dispatch-operator-attach"
KIND_DISPATCH_OPERATOR_RESUME = "dispatch-operator-resume"
KIND_DISPATCH_COMPLETION = "dispatch-completion"
KIND_DISPATCH_VERIFICATION = "dispatch-verification"
KIND_DISPATCH_LAND = "dispatch-land"
KIND_DISPATCH_TIMING = "dispatch-timing"
KIND_DISPATCH_PRESERVE = "dispatch-preserve"

_DISPATCH_RUNS_DIRNAME = "dispatch-runs"
_WORKTREES_DIRNAME = ".worktrees"
_DISPATCH_WORKTREE_PREFIX = "dispatch-"

#: Story 22.9. A dispatch branch is ``dispatch/<slug>/<story_key>`` -- the
#: station segment is what makes two stations sharing a story key
#: (``pyforge-atlas 20.1`` and ``pyforge-doctor 20.1``) structurally unable
#: to collide, back when ``_ensure_dispatch_worktree`` resolved an existing
#: worktree BY BRANCH NAME and would have handed one station the other's
#: tree.
_DISPATCH_BRANCH_PREFIX = "dispatch"

#: The pre-22.9 station-less name (``marshal/<story_key>``). Still rendered
#: -- never minted -- so in-flight and preserved branches under the old
#: shape stay resolvable instead of being silently stranded.
_LEGACY_DISPATCH_BRANCH_PREFIX = "marshal"


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
    story_started_at: str | None = None
    story_ended_at: str | None = None
    baseline_revision: str | None = None
    final_revision: str | None = None
    preserve_ref: str | None = None


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


def dispatch_worktree_branch(slug: str, story_key: str) -> str:
    """The ONE dispatch-branch derivation (Story 22.9).

    ``slug`` is a required positional, deliberately: the pre-22.9 signature
    was ``dispatch_worktree_branch(story_key)``, so any consumer that was
    not updated fails loudly with a ``TypeError`` instead of quietly
    rendering a station-less name that could resolve another station's
    worktree.
    """
    return f"{_DISPATCH_BRANCH_PREFIX}/{slug}/{story_key}"


def legacy_dispatch_worktree_branch(story_key: str) -> str:
    """The pre-22.9 station-less branch name -- read, never minted."""
    return f"{_LEGACY_DISPATCH_BRANCH_PREFIX}/{story_key}"


@dataclass(frozen=True)
class DispatchBranchResolution:
    """Which branch a station's dispatch work actually lives on (22.9).

    ``branch`` is always the station-scoped name. ``resolved`` is the branch
    that EXISTS and demonstrably belongs to this station (either
    ``branch`` itself, or -- for work started before 22.9 -- the legacy
    ``marshal/<key>`` name, in which case ``legacy`` is ``True``); it is
    ``None`` when no branch exists yet and the caller may mint ``branch``.
    ``refusal`` is set (and ``resolved`` is ``None``) when a legacy branch
    exists that cannot be attributed to this station: the loud land-first
    message, never a silent reuse of another station's tree.
    """

    branch: str
    resolved: str | None = None
    legacy: bool = False
    refusal: str | None = None

    @property
    def effective_branch(self) -> str:
        """The branch to act on: the resolved one, else the name to mint."""
        return self.branch if self.resolved is None else self.resolved


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right


def format_legacy_branch_refusal(
    *,
    legacy_branch: str,
    branch: str,
    checked_out_at: Path | None,
) -> str:
    """The land-first refusal for an unattributable legacy branch (22.9)."""
    where = (
        f"is checked out at {str(checked_out_at)!r}, which is not this "
        "station's dispatch worktree"
        if checked_out_at is not None
        else "still exists with work that predates station-scoped branch "
        "names and cannot be attributed to a station"
    )
    return (
        f"legacy dispatch branch {legacy_branch!r} {where} — refusing to "
        f"reuse it for {branch!r}. Land that branch first (merge its PR onto "
        "main), then delete it; re-dispatch afterwards and the work lands on "
        f"{branch!r}."
    )


def resolve_dispatch_branch(
    vcs: VcsPort,
    repo_root: Path,
    *,
    slug: str,
    story_key: str,
    worktree: Path | None = None,
) -> DispatchBranchResolution:
    """Resolve the branch holding ``slug``'s ``story_key`` dispatch (22.9).

    The single place the legacy ``marshal/<key>`` name is reconciled, shared
    by worktree provisioning, the completion supervisor's git facts, and
    landing so all three agree. Attribution of a legacy branch is a git
    fact, never a guess: the branch is this station's only when the worktree
    git has it checked out IS this station's dispatch worktree
    (``worktree``, defaulting to ``dispatch_worktree_path``). A legacy
    branch with no worktree cannot be attributed at all, so it refuses.

    Read-only. Raises whatever ``vcs`` raises (``VcsCommandError``); every
    caller already handles it.
    """
    branch = dispatch_worktree_branch(slug, story_key)
    if vcs.branch_exists(repo_root, branch):
        return DispatchBranchResolution(branch=branch, resolved=branch)

    legacy_branch = legacy_dispatch_worktree_branch(story_key)
    expected = (
        worktree
        if worktree is not None
        else dispatch_worktree_path(repo_root, slug, story_key)
    )
    legacy_worktree = vcs.worktree_path_for_branch(repo_root, legacy_branch)
    if legacy_worktree is not None:
        if _same_path(legacy_worktree, expected):
            return DispatchBranchResolution(
                branch=branch, resolved=legacy_branch, legacy=True
            )
        return DispatchBranchResolution(
            branch=branch,
            refusal=format_legacy_branch_refusal(
                legacy_branch=legacy_branch,
                branch=branch,
                checked_out_at=legacy_worktree,
            ),
        )
    if vcs.branch_exists(repo_root, legacy_branch):
        return DispatchBranchResolution(
            branch=branch,
            refusal=format_legacy_branch_refusal(
                legacy_branch=legacy_branch,
                branch=branch,
                checked_out_at=None,
            ),
        )
    return DispatchBranchResolution(branch=branch)


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
