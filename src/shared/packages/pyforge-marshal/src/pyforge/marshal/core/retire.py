"""Fleet-wide branch retirement classification (Story 4.10, FR-63/AD-47) --
the PURE evidence-classification core ``cli/retire.py``'s ``marshal retire``
delegates to.

**Why this module never reads ``TaskPhaseSnapshot`` directly (AD-4).**
Keeping the pure core's input shape to three plain facts
(``merged_by_patch_id: bool``, ``run_concluded: bool``,
``recorded_merge_sha: str | None``) rather than the whole harness-native
snapshot type means this classification has zero coupling to bmad-loop's own
field names/spellings -- ``cli/retire.py`` is the one place that translates
``TaskPhaseSnapshot.phase == "done"`` into the ``recorded_merge_sha`` fact
this module actually consumes (mirrors AD-33's "git is a repo-fact
authority, journal/harness is a process-fact authority, and something at the
CLI boundary translates between them" pattern every other Epic 4 story
already established).

**The evidence bar.** A branch is PROPOSED for retirement only when all
three facts are independently, positively established:

1. ``merged_by_patch_id`` -- ``VcsPort.is_branch_merged``'s own patch-CONTENT
   equivalence check (Story 1.8), never bare commit-SHA ancestry.
2. ``run_concluded`` -- ``VcsPort.worktree_path_for_branch(...) is None``: no
   live worktree is currently checked out on this branch, the git-truthful
   proxy for "its run concluded" -- no harness-reported run-status field says
   this more directly (see ``cli/retire.py``'s own docstring).
3. ``recorded_merge_sha`` -- non-``None`` only when the harness's own
   ``TaskPhaseSnapshot.phase`` reached ``"done"`` AND recorded a
   ``commit_sha`` for it -- the harness's own terminus and merge sha for
   that story, never re-derived from commit-subject matching.

Any one fact being false/``None`` refuses the branch -- never a silent drop:
``classify_retirement`` always returns either a ``RetirementProposal`` (all
three true) or an ``InsufficientEvidence`` (naming every fact that could not
be established, via ``.missing``).

``is_structurally_excluded`` is the ``loop/*`` prefix hard filter (the
station-branch exclusion, applied BEFORE evidence-gathering even runs) --
structural, never policy-configurable, per this story's own Never bullet.

Pure data only (AD-4): no I/O, no subprocess, no clock, no
``..adapters`` import.
"""

from __future__ import annotations

from dataclasses import dataclass

# The loop-home station-branch prefix every bmad-loop-provisioned home's own
# branch carries (``f"loop/{slug}"``, ``cli/init.py``'s ``add_worktree``
# convention) -- excluded structurally, unconditionally, before any
# evidence-gathering runs against it (this story's own Never bullet: no
# policy key governs this exclusion).
_STATION_BRANCH_PREFIX = "loop/"


@dataclass(frozen=True)
class RetirementCandidate:
    """One task-scoped, worktree-isolated per-story branch under
    consideration for retirement: which project (``slug``), which branch
    (``branch``, bmad-loop's own ``TaskPhaseSnapshot.branch`` verbatim), and
    which story it belongs to (``story_key``, Marshal's canonical dot form,
    already normalized by the caller via ``core.identity.normalize`` -- this
    module has no notion of a raw, un-normalized harness key)."""

    slug: str
    branch: str
    story_key: str


@dataclass(frozen=True)
class RetirementProposal:
    """``classify_retirement``'s PROPOSED outcome: every one of the three
    evidence facts was independently established. ``recorded_merge_sha`` is
    carried here (never re-derived by a caller) so the proposal's own report
    line can name the exact evidence (``merged_by_patch_id: true``,
    ``worktree: null``, ``recorded_merge_sha: <sha>``) without a second
    lookup."""

    candidate: RetirementCandidate
    recorded_merge_sha: str


@dataclass(frozen=True)
class InsufficientEvidence:
    """``classify_retirement``'s REFUSED outcome: ``missing`` names every
    fact (one or more of ``"merged_by_patch_id"``, ``"run_concluded"``,
    ``"story_done_with_sha"``) that could not be positively established --
    never a bare boolean refusal with no explanation. A branch reported here
    is OMITTED from the proposal list, never silently dropped: the sweep's
    own ``insufficient_evidence`` report entry is built directly from this
    value."""

    candidate: RetirementCandidate
    missing: tuple[str, ...]


def is_structurally_excluded(branch: str) -> bool:
    """``True`` if ``branch`` carries the station-branch prefix
    (``"loop/<slug>"``) -- excluded before evidence-gathering ever runs
    against it, unconditionally, for every project, every run (this story's
    own Never bullet: no policy key governs this). Also the defense-in-depth
    guard against a malformed harness snapshot that names a station branch
    as a task's own ``branch`` field (should never happen -- see the I/O
    matrix)."""
    return branch.startswith(_STATION_BRANCH_PREFIX)


def classify_retirement(
    candidate: RetirementCandidate,
    *,
    merged_by_patch_id: bool,
    run_concluded: bool,
    recorded_merge_sha: str | None,
) -> RetirementProposal | InsufficientEvidence:
    """The sole classification decision (pure, AD-4): PROPOSED only when all
    three facts are true/non-``None`` together; REFUSED (``Insufficient
    Evidence``) otherwise, naming every fact that failed. ``missing`` lists
    facts in the SAME fixed order the spec's own Always bullet enumerates
    them (``merged_by_patch_id``, ``run_concluded``, ``story_done_with_sha``)
    -- deterministic, never set-ordered."""
    missing: list[str] = []
    if not merged_by_patch_id:
        missing.append("merged_by_patch_id")
    if not run_concluded:
        missing.append("run_concluded")
    if recorded_merge_sha is None:
        missing.append("story_done_with_sha")
    if missing:
        return InsufficientEvidence(candidate=candidate, missing=tuple(missing))
    return RetirementProposal(candidate=candidate, recorded_merge_sha=recorded_merge_sha)
