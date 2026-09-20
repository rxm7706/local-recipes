"""Pure dispatch path helpers and journal kinds (Story 22.1, FR-193 CAP-1).

Story 22.5 (FR-193 CAP-5) adds declared-surface overlap detection for
cross-station concurrent dispatch advisories.

Story 22.9 (FR-193 CAP-2/CAP-5) makes the dispatch BRANCH name carry its
station and puts the derivation here, once: ``dispatch_worktree_branch`` is
the sole site that renders a dispatch branch string, and
``resolve_dispatch_branch`` is the sole site that decides which branch a
station's work actually lives on. Everything else in the package -- worktree
provisioning, the in-flight conflict guard's git facts, and landing --
imports one of the two. Not every function here is pure: ``resolve_dispatch_
branch`` must ask git which branches exist; ``story_spec_candidates``/
``resolve_story_spec_path`` glob and stat the LOCAL working tree to find a
spec's physical path; ``spec_text_at_ref`` (Story 51.7/CAP-255) composes the
latter with a ``VcsPort.file_text_at_ref`` read to return a spec's content
as it stood at an arbitrary ref. All three take their I/O port (or read the
local filesystem directly) rather than reaching for one themselves, and
none of them write.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from pyforge.core.landing_evidence import DISPATCH_BRANCH_PREFIX

from .identity import StoryKey, normalize, render_filename_slug
from .policy import EffectivePolicy
from .tier_routing import TierLaunchResolution, resolve_tier_launch

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
#: Story 28.21 (CAP-4): push ``origin/dispatch/<slug>/<story>`` once the
#: session has a commitable result, before independent verify.
KIND_DISPATCH_PUSH = "dispatch-push"
#: Story 28.16 (parallel dispatch fan-out, CAP-3): one wave's membership,
#: cap, refused candidates, and per-member terminal outcomes.
KIND_DISPATCH_WAVE = "dispatch-wave"
#: Story 28.24 (CAP-7): supervisor commit/push/verify when the harness
#: cannot run shell.
KIND_DISPATCH_FINALIZE = "dispatch-finalize"
#: Story 51.4 (CAP-252): the supervisor stopped before verify/land because
#: the worktree spec is `blocked` or the entire diff is narration (the
#: tracked spec file itself) with no code progress behind it.
KIND_DISPATCH_BLOCKED = "dispatch-blocked"

_DISPATCH_RUNS_DIRNAME = "dispatch-runs"
_WORKTREES_DIRNAME = ".worktrees"
_DISPATCH_WORKTREE_PREFIX = "dispatch-"

#: Story 22.9. A dispatch branch is ``dispatch/<slug>/<story_key>``. The
#: station segment is load-bearing, not cosmetic:
#: ``_ensure_dispatch_worktree`` resolves an existing worktree BY BRANCH
#: NAME -- it still does -- so under the old station-less
#: ``marshal/<story_key>`` name two stations sharing a story key
#: (``pyforge-atlas 20.1`` and ``pyforge-doctor 20.1``) resolved to ONE
#: branch and silently shared a tree. With the slug in the name that
#: lookup can no longer cross stations.
#:
#: The literal lives in ``pyforge.core`` because both packages need it:
#: marshal mints these branches, and ``pyforge.core.landing_evidence``
#: must recognize them or a dispatch landing stops classifying. Imported,
#: never re-spelled.
_DISPATCH_BRANCH_PREFIX = DISPATCH_BRANCH_PREFIX

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
    completion_stop_reason: str | None = None
    verification_verdict: str | None = None
    verification_failed_gate: str | None = None
    # Story 28.15 (CAP-17): the station's own `warn`-mode scope-violation
    # advisories from the LATEST dispatch verification -- a tuple of plain
    # ``{code, message, path}`` dicts (JSON-safe), never journal-only (AC4:
    # ``marshal status``/``fleet-picture`` must render them). Empty when the
    # station's declared mode is `hard`/`off`, or when `warn` mode produced
    # no violation.
    verification_scope_advisories: tuple[dict[str, object], ...] = ()
    landing_verdict: str | None = None
    # Story 53.2 review (I1): `execute_dispatch_land`'s envelope findings
    # (MRS-DISP-047/048), a tuple of plain JSON-safe dicts -- same shape and
    # same "never journal-only" rationale as `verification_scope_advisories`.
    landing_findings: tuple[dict[str, object], ...] = ()
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


def spec_text_at_ref(
    vcs: VcsPort,
    repo_root: Path,
    slug: str,
    story: str,
    *,
    ref: str = "origin/main",
) -> str | None:
    """A story's tracked spec content as it stood at ``ref`` (Story 51.7/
    CAP-255) -- the impure half of ``core.promotion.corroborated_merged_
    story_keys``'s injected ``spec_status_for`` reader (the pure half,
    ``core.promotion.read_spec_status``, parses the returned text).

    Resolves the spec's repo-relative PATH against the LOCAL working tree
    via ``resolve_story_spec_path`` -- the physical filename, once minted,
    is stable across a story's status lifecycle; only the frontmatter
    value inside it changes on promotion -- then reads that path's byte
    content specifically at ``ref`` via ``VcsPort.file_text_at_ref``,
    never the local working tree's own copy (which may be dirty, stale, or
    simply sit on a different branch). Reads the local filesystem (path
    resolution) and asks git for ref content; performs no writes.

    Returns ``None`` (fails closed, never corroborating a landing) when
    ``story`` does not parse as a story key, no local candidate resolves,
    or ``ref`` has no such path (a spec minted after ``ref`` was fetched,
    or not yet fetched at all)."""
    path = resolve_story_spec_path(repo_root, slug, story)
    if path is None:
        return None
    root = canonical_repo_root(repo_root)
    try:
        rel = path.relative_to(root)
    except ValueError:
        return None
    return vcs.file_text_at_ref(repo_root, ref, rel.as_posix())


def relocated_spec_path(spec_path: Path, repo_root: Path, worktree: Path) -> Path:
    """Map a primary-tree spec onto the dispatch worktree copy.

    Harness prompts must never receive ``repo_root`` paths: bmad-build-auto
    writes status/baseline onto whatever path is named, and that leaked
    onto operator ``main`` (Story 42.5). Already-relocated paths are
    returned unchanged.
    """
    spec = spec_path.resolve()
    wt = worktree.resolve()
    root = canonical_repo_root(repo_root)
    try:
        spec.relative_to(wt)
    except ValueError:
        pass
    else:
        return spec
    try:
        relative = spec.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"spec_path {str(spec)!r} is neither under worktree "
            f"{str(wt)!r} nor repo root {str(root)!r}"
        ) from exc
    return wt / relative


def expected_story_spec_glob(repo_root: Path, slug: str, story: str) -> str | None:
    """The tracked spec glob operators must author (Story 28.19, CAP-2).

    Returns a repo-root-relative ``spec-<e>-<n>-*.md`` path under the
    station's ``planning-artifacts/specs/`` tree, or ``None`` when ``story``
    does not parse as a story key.
    """
    try:
        key = normalize(story)
    except ValueError:
        return None
    specs = planning_specs_dir(repo_root, slug)
    rel_root = canonical_repo_root(repo_root)
    try:
        rel_specs = specs.relative_to(rel_root)
    except ValueError:
        rel_specs = specs
    return f"{rel_specs.as_posix()}/spec-{render_filename_slug(key)}-*.md"


_DIFFICULTY_RE = re.compile(
    r"^difficulty:\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*$", re.MULTILINE
)


def read_declared_difficulty(spec_text: str) -> str | None:
    match = _DIFFICULTY_RE.search(spec_text.replace("\r\n", "\n").replace("\r", "\n"))
    return match.group(1) if match else None


def resolve_dispatch_model(
    policy: EffectivePolicy, *, difficulty: str | None
) -> str | None:
    model, _, _, _ = resolve_dispatch_model_with_retry_escalation(
        policy, difficulty=difficulty
    )
    return model


def resolve_dispatch_model_with_retry_escalation(
    policy: EffectivePolicy,
    *,
    difficulty: str | None,
    prior_failed_attempts: int = 0,
) -> tuple[str | None, bool, str | None, str | None]:
    """Resolve the launch model and optionally floor-raise on dispatch retry.

    Story 33.6 (spec-adaptive-model-tiering CAP-2 on factory dispatch):
    when ``prior_failed_attempts`` reaches ``max_dev_attempts``, the dev-stage
    model is floor-raised to the review-tier model from the tier map — never
    a downgrade, never a spin-style on-disk policy.toml write.
    """
    from .dispatch_retry import (
        apply_dispatch_retry_floor_raise,
        should_dispatch_retry_escalate,
    )

    resolution = resolve_tier_launch(
        policy, difficulty, allow_unmapped_fallback=True
    )
    dev_model = resolution.resolved_models.get("dev")
    base_model: str | None
    if isinstance(dev_model, str) and dev_model:
        base_model = dev_model
    else:
        base_model = None
        for model in resolution.resolved_models.values():
            if isinstance(model, str) and model:
                base_model = model
                break

    review_model = resolution.resolved_models.get("review")
    review_model_str = review_model if isinstance(review_model, str) else None

    seed = policy.seed_view()
    max_dev_field = seed.get("max_dev_attempts")
    max_dev_attempts = (
        max_dev_field.value if max_dev_field is not None else 2
    )
    if not isinstance(max_dev_attempts, int) or isinstance(max_dev_attempts, bool):
        max_dev_attempts = 2

    if should_dispatch_retry_escalate(prior_failed_attempts, max_dev_attempts):
        return apply_dispatch_retry_floor_raise(base_model, review_model_str)
    return base_model, False, None, None


def resolve_tier_harness(
    policy: EffectivePolicy,
    *,
    difficulty: str | None,
    session_log: str | None = None,
    excluded_harnesses: frozenset[str] | None = None,
) -> TierLaunchResolution:
    """Launch-time tier routing for factory dispatch harness selection."""
    return resolve_tier_launch(
        policy,
        difficulty,
        session_log=session_log,
        excluded_harnesses=excluded_harnesses,
        allow_unmapped_fallback=True,
    )


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


def _safe_ref_segment(raw: str, fallback: str) -> str:
    """One path-and-ref-safe segment: the sanitization ``dispatch_worktree_
    path`` has always applied to the story key, extracted so the BRANCH name
    and the WORKTREE path derive their segments identically (Story 22.9).

    They must agree because ``resolve_dispatch_branch`` decides branch
    attribution by comparing a branch-derived expectation against a
    path-derived location; a key that sanitized on one side but not the
    other would make the two diverge (and could render a ref git rejects).
    Dot runs collapse to one dot and leading/trailing dots and dashes are
    stripped: ``git check-ref-format`` rejects a ref containing ``..``
    anywhere or a component that starts or ends with ``.``, and ``..`` is
    also the segment that would traverse as a path. A segment left empty by
    all of that becomes ``fallback``. Ordinary keys keep their single dot
    (``22.9`` -> ``22.9``).
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw)
    cleaned = re.sub(r"\.{2,}", ".", cleaned).strip("-.")
    return cleaned or fallback


def dispatch_worktree_branch(slug: str, story_key: str) -> str:
    """The ONE dispatch-branch derivation (Story 22.9).

    ``slug`` is a required positional, deliberately: the pre-22.9 signature
    was ``dispatch_worktree_branch(story_key)``, so any consumer that was
    not updated fails loudly with a ``TypeError`` instead of quietly
    rendering a station-less name that could resolve another station's
    worktree.

    Both segments are sanitized by ``_safe_ref_segment`` -- the SAME rule
    ``dispatch_worktree_path`` applies -- so a slug or key carrying ``/`` or
    ``..`` can neither traverse nor split this name into extra ref
    components. Ordinary inputs (``pyforge-marshal``, ``22.9``) render
    unchanged.
    """
    return (
        f"{_DISPATCH_BRANCH_PREFIX}"
        f"/{_safe_ref_segment(slug, 'project')}"
        f"/{_safe_ref_segment(story_key, 'story')}"
    )


def legacy_dispatch_worktree_branch(story_key: str) -> str:
    """The pre-22.9 station-less branch name -- read, never minted."""
    return f"{_LEGACY_DISPATCH_BRANCH_PREFIX}/{_safe_ref_segment(story_key, 'story')}"


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


def _lexically_normalized(path: Path) -> PurePath:
    """``path`` with ``..`` collapsed, without touching the filesystem.

    ``PurePath.parts`` already drops ``.`` segments, duplicate separators
    and trailing slashes, so ``..`` is the only spelling difference left
    that would make two names for the same worktree compare unequal. Done
    by hand rather than with ``os.path.normpath`` because AD-4 forbids
    ``pyforge.marshal.core`` from importing ``os`` at all.
    """
    parts: list[str] = []
    for part in path.parts:
        if part == ".." and parts and parts[-1] not in ("..", path.anchor):
            parts.pop()
            continue
        parts.append(part)
    return PurePath(*parts) if parts else PurePath(".")


def _same_path(left: Path, right: Path) -> bool:
    """Do two path spellings name the same worktree?

    ``resolve()`` is the real answer (it follows symlinks). Its fallback
    matters: ``resolve()`` can raise ``OSError`` (a symlink loop, an
    over-long name), and a bare ``left == right`` there would call two
    spellings of ONE worktree different and raise a spurious
    ``MRS-DISP-030`` refusal on a dispatch that should have proceeded --
    so the fallback compares lexically normalized forms instead.
    """
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return _lexically_normalized(left) == _lexically_normalized(right)


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
    landing so all three agree.

    Attribution of a legacy branch is a git fact, never a guess: a legacy
    branch belongs to this station only when the worktree git reports it
    checked out at is this station's dispatch worktree -- ``worktree``,
    which defaults to ``dispatch_worktree_path(repo_root, slug,
    story_key)`` and which existing runs pass explicitly from their
    journal. A legacy branch git has checked out somewhere else belongs to
    another station; a legacy branch with no worktree at all cannot be
    attributed to any station. Both refuse.

    Read-only. Raises whatever ``vcs`` raises (``VcsCommandError``); every
    caller already handles it. Callers must act on ``resolved``, not on
    ``effective_branch``, whenever they are about to ask git about the
    branch: ``resolved is None`` means no branch of this story's exists.
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
    # Story 22.9: both segments go through `_safe_ref_segment`, the same
    # rule `dispatch_worktree_branch` applies, so the branch name and this
    # path never disagree about a key -- `resolve_dispatch_branch` compares
    # one against the other to attribute a legacy branch.
    safe_slug = _safe_ref_segment(slug, "project")
    safe_key = _safe_ref_segment(story_key, "story")
    return (
        canonical_repo_root(repo_root)
        / _WORKTREES_DIRNAME
        / f"{_DISPATCH_WORKTREE_PREFIX}{safe_slug}-{safe_key}"
    )


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
