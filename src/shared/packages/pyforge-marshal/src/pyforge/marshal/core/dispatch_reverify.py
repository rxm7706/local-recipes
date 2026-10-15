"""Whether a re-landing may reuse its run's verified verdict (Story 102.1, spec-pyforge-marshal CAP-161).

CAP-161 (single-story-dispatch CAP-3) makes the driver verify a story before any landing, never on a session's
self-report. When a dispatch's PR conflicts with ``main`` and ``main`` is merged into the branch, the head moves and
the land-only path re-runs the full verification although the story's own code did not change. With the station
policy ``dispatch.landing_reverify = "on-code-change"`` that path may reuse the run's latest FULL verified verdict
when this module judges the move exempt: every non-planning path of the story's own diff is byte-identical to what
that verdict judged, and every other non-planning change came from ``main``. GitHub CI still judges the combined
tree before any merge (CAP-284); ``dispatch_verify.py`` gathers the git facts and runs the narrow re-check
(``attempt_verdict_reuse``).

Pure (AD-4): facts in, a decision out. No git, no clock, no file read.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from .dispatch import KIND_DISPATCH_VERIFICATION
from .dispatch_landing import MEMLOG_BASENAME, SPEC_SURFACE_BASELINE_REL
from .journal import FoldResult, JournalEntry, Phase

#: The OUTCOME payload keys this story adds to ``dispatch-verification``.
MODE_FIELD = "mode"
HEAD_SHA_FIELD = "head_sha"
REUSED_VERIFICATION_ID_FIELD = "reused_verification_id"
REUSED_HEAD_SHA_FIELD = "reused_head_sha"
REUSE_EVIDENCE_FIELD = "reuse_evidence"
REUSE_DECLINED_FIELD = "reuse_declined"
#: Review fix 1: the digest of the gate set a full verification ran (``verify_gate_set``), so a reuse can tell when
#: the gates themselves moved since the verdict -- a station policy edit, a derivation change, a new derived command.
GATE_DIGEST_FIELD = "gate_digest"

#: ``mode`` values: a full independent verification, or a reuse of one.
MODE_FULL = "full"
MODE_REUSED = "reused"

#: The basis of an exempt decision.
BASIS_HEAD_UNCHANGED = "head-unchanged"
BASIS_MERGE_OF_MAIN = "merge-of-main"

#: The closed reasons a reuse is declined (each re-verifies in full).
REASON_NO_VERIFIED_VERDICT = "no-verified-verdict"
REASON_DIRTY_WORKTREE = "dirty-worktree"
REASON_NO_STORY_DIFF = "no-story-diff"
REASON_NOT_ON_FIRST_PARENT_CHAIN = "not-on-first-parent-chain"
REASON_STORY_COMMIT = "story-commit"
REASON_OCTOPUS_MERGE = "octopus-merge"
REASON_MERGE_NOT_OF_MAIN = "merge-not-of-main"
REASON_MERGE_CONFLICT_OUTSIDE_PLANNING = "merge-conflict-outside-planning"
REASON_MERGE_TOUCHES_STORY_FILE = "merge-touches-story-file"
REASON_MERGE_RESOLUTION_OUTSIDE_PLANNING = "merge-resolution-outside-planning"
REASON_GIT_READ_FAILED = "git-read-failed"
REASON_RECHECK_FAILED = "recheck-failed"
# Review fixes (2026-10-15, PR #2238).
REASON_GATE_SET_CHANGED = "gate-set-changed"
REASON_MERGE_TOUCHES_POLICY = "merge-touches-policy"
REASON_MERGE_STALE_AGAINST_MAIN = "merge-stale-against-main"
REASON_NO_STORY_SPEC = "no-story-spec"

#: The longest first-parent chain from the current head down to the verified head that is judged at all.
MAX_CHAIN_COMMITS = 64

#: How many paths one evidence list carries before it is cut (the counts stay whole).
_EVIDENCE_PATH_CAP = 20

_PLANNING_ROOTS: tuple[tuple[str, ...], ...] = (("docs", "dreams"), (".claude", "memory"))
#: Never planning: a station's policy holds the very verify commands a verdict ran.
POLICY_BASENAME = "marshal-policy.toml"
#: Never planning: Python a test run could import (a ``conftest.py`` is collected wherever it sits).
_CODE_SUFFIXES: tuple[str, ...] = (".py", ".pyi")


def gate_set_digest(commands: Sequence[str]) -> str:
    """Review fix 1: a stable digest of an ordered gate set -- each command whitespace-collapsed, as
    ``check_spec_binding`` compares them -- so two verifications that would run the same gates digest alike."""
    joined = "\n".join(" ".join(command.split()) for command in commands)
    return "sha256:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _normalize(path: str) -> str:
    normalized = path.replace("\\", "/")
    return normalized[2:] if normalized.startswith("./") else normalized


def is_planning_path(path: str, *, story_spec_rel: str | None = None) -> bool:
    """True when ``path`` is a planning file a merge of ``main`` may change or conflict on without unseating a
    verified verdict: anywhere under exactly ``_bmad-output/projects/<one segment>/planning-artifacts/``, under
    ``docs/dreams/`` or ``.claude/memory/``, a Spec memlog under ``docs/governance/``, or the spec-surface baseline.

    Never planning (review fix 4, PR #2238): a path with an empty, ``.`` or ``..`` segment; a Python file (a
    ``conftest.py`` is collected wherever it sits); any ``marshal-policy.toml`` (it declares the verify commands a
    verdict ran); ``story_spec_rel``, the story's own tracked spec (its success signal and declared surface bind the
    verification). The narrow re-check judges the planning files instead."""
    normalized = _normalize(path)
    segments = normalized.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        return False
    basename = segments[-1]
    if story_spec_rel is not None and normalized == _normalize(story_spec_rel):
        return False
    if basename == POLICY_BASENAME or basename.endswith(_CODE_SUFFIXES):
        return False
    if normalized == SPEC_SURFACE_BASELINE_REL:
        return True
    if len(segments) >= 5 and segments[:2] == ["_bmad-output", "projects"] and segments[3] == "planning-artifacts":
        return True
    if len(segments) >= 4 and segments[:2] == ["docs", "governance"] and basename == MEMLOG_BASENAME:
        return True
    return any(len(segments) > len(root) and tuple(segments[: len(root)]) == root for root in _PLANNING_ROOTS)


@dataclass(frozen=True)
class ReuseCandidate:
    """The full verified verdict a re-landing may reuse: its OUTCOME's journal id and the head it judged, plus its
    scope advisories, carried onto a reused OUTCOME so ``marshal status`` keeps naming them."""

    writer_id: str
    counter: int
    head_sha: str
    scope_advisories: tuple[Mapping[str, object], ...] = ()
    gate_digest: str | None = None

    def id_payload(self) -> dict[str, object]:
        return {"writer_id": self.writer_id, "counter": self.counter}


#: Reads a full OUTCOME's scope advisories (they may sit in a sidecar only the caller can resolve).
AdvisoriesReader = Callable[[JournalEntry], tuple[Mapping[str, object], ...]]


def _id_from_payload(raw: object) -> tuple[str, int] | None:
    if not isinstance(raw, Mapping):
        return None
    writer_id = raw.get("writer_id")
    counter = raw.get("counter")
    if not isinstance(writer_id, str) or not writer_id:
        return None
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
        return None
    return writer_id, counter


def _non_empty_str(raw: object) -> str | None:
    return raw if isinstance(raw, str) and raw else None


def latest_reusable_verdict(
    folded: FoldResult,
    run_id: str,
    *,
    advisories_of: AdvisoriesReader | None = None,
) -> ReuseCandidate | None:
    """The run's reusable verdict, or ``None``.

    Only the run's LATEST ``dispatch-verification`` OUTCOME is considered, and it must read ``verified``: a later
    refusal is never skipped over. A full OUTCOME must carry ``head_sha`` (a verdict journaled before Story 102.1, or
    on a dirty tree, carries none and is never reused). A reused OUTCOME names the full verdict it reused
    (``reused_verification_id`` and ``reused_head_sha``), and that full verdict is the candidate: a reuse is never
    the base of another. Review fix 5: the named base must be in this run's journal, read ``verified`` and
    ``mode: full``, and carry the same ``head_sha`` the reuse names, or there is no candidate. ``advisories_of`` is
    an optional ``(entry) -> tuple`` that reads a full OUTCOME's scope advisories (they may sit in a sidecar the caller
    resolves)."""
    outcomes = [
        entry
        for entry in folded.by_kind(KIND_DISPATCH_VERIFICATION)
        if entry.run_id == run_id and entry.phase == Phase.OUTCOME
    ]
    if not outcomes:
        return None
    latest = outcomes[-1]
    if latest.payload.get("verdict") != "verified":
        return None
    if latest.payload.get(MODE_FIELD) == MODE_REUSED:
        ident = _id_from_payload(latest.payload.get(REUSED_VERIFICATION_ID_FIELD))
        head = _non_empty_str(latest.payload.get(REUSED_HEAD_SHA_FIELD))
        if ident is None or head is None:
            return None
        base = next(
            (
                entry
                for entry in outcomes
                if entry.id.writer_id == ident[0] and entry.id.counter == ident[1] and entry is not latest
            ),
            None,
        )
        if (
            base is None
            or base.payload.get("verdict") != "verified"
            or base.payload.get(MODE_FIELD) != MODE_FULL
            or base.payload.get(HEAD_SHA_FIELD) != head
        ):
            return None
        return ReuseCandidate(
            writer_id=ident[0],
            counter=ident[1],
            head_sha=head,
            scope_advisories=_advisories(base, advisories_of),
            gate_digest=_non_empty_str(base.payload.get(GATE_DIGEST_FIELD)),
        )
    head = _non_empty_str(latest.payload.get(HEAD_SHA_FIELD))
    if head is None:
        return None
    return ReuseCandidate(
        writer_id=latest.id.writer_id,
        counter=latest.id.counter,
        head_sha=head,
        scope_advisories=_advisories(latest, advisories_of),
        gate_digest=_non_empty_str(latest.payload.get(GATE_DIGEST_FIELD)),
    )


def _advisories(entry: JournalEntry, advisories_of: AdvisoriesReader | None) -> tuple[Mapping[str, object], ...]:
    if advisories_of is not None:
        found = advisories_of(entry)
        return tuple(item for item in found if isinstance(item, Mapping))
    raw = entry.payload.get("scope_violation_advisories")
    if isinstance(raw, list):
        return tuple(item for item in raw if isinstance(item, Mapping))
    return ()


@dataclass(frozen=True)
class ChainCommit:
    """One commit on the first-parent chain from the current head down to (not including) the verified head.

    ``changed_paths`` is its diff against its first parent. For a merge (two parents),
    ``second_parent_on_main`` says whether its second parent is on ``origin/main``'s first-parent chain (a state main
    was itself in, review fix 2 -- not merely an ancestor of it),
    ``replay_conflicts`` is what ``git merge-tree --write-tree`` reports conflicted when the merge is replayed, and
    ``resolution_paths`` is where the merge's tree differs from that replay (hand-made changes, conflict
    resolutions)."""

    sha: str
    parents: tuple[str, ...]
    changed_paths: tuple[str, ...] = ()
    second_parent_on_main: bool = False
    replay_conflicts: tuple[str, ...] = ()
    resolution_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReuseFacts:
    """What git says about the move from the verified head to the current head. ``chain`` lists the first-parent
    chain newest first and is ``None`` when the verified head is not on it (or the chain is too long)."""

    verified_head: str
    current_head: str
    story_paths: tuple[str, ...]
    chain: tuple[ChainCommit, ...] | None
    story_spec_rel: str | None = None
    #: Review fix 2: the paths a merge brought from main whose content at the current head is not current
    #: ``origin/main``'s (a merge of a main commit later reverted, or main moving the same path again since).
    stale_main_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReuseDecision:
    """``exempt`` with its ``basis``, or a declined ``reason`` and its ``detail``; ``evidence`` is the bounded,
    JSON-safe record the journal carries either way."""

    exempt: bool
    reason: str
    detail: str = ""
    basis: str | None = None
    evidence: Mapping[str, object] = field(default_factory=dict)


def declined(reason: str, detail: str = "", evidence: Mapping[str, object] | None = None) -> ReuseDecision:
    """A not-exempt decision: the re-landing re-verifies in full."""
    return ReuseDecision(exempt=False, reason=reason, detail=detail, evidence=dict(evidence or {}))


def _cap(paths: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(paths)[:_EVIDENCE_PATH_CAP]


def judge_verdict_reuse(facts: ReuseFacts) -> ReuseDecision:
    """Story 102.1: whether the move from ``facts.verified_head`` to ``facts.current_head`` leaves the verified
    verdict standing.

    Exempt when the story's diff is not empty and either the head did not move (``head-unchanged``), or every
    commit on the first-parent chain, oldest first, is (``merge-of-main``):

    * a merge of main -- exactly two parents, the second on ``origin/main``'s first-parent chain; no replayed conflict
      outside planning paths; a first-parent diff that touches no ``marshal-policy.toml`` and no non-planning path of
      the story's own diff; a tree that differs from the replay only in planning paths; or
    * a planning-only commit -- one parent, every changed path a planning path;

    and every non-planning path a merge brought from main still reads current ``origin/main``'s content.

    The first commit that is neither declines with its reason. The checks run in a fixed order so the journaled
    reason is the most specific one: a replayed conflict is named before the overlap it implies."""
    spec = facts.story_spec_rel

    def planning(path: str) -> bool:
        return is_planning_path(path, story_spec_rel=spec)

    story_code = frozenset(path for path in facts.story_paths if not planning(path))
    evidence: dict[str, object] = {
        "verified_head": facts.verified_head,
        "current_head": facts.current_head,
        "story_paths": len(facts.story_paths),
        "story_code_paths": len(story_code),
    }
    if not facts.story_paths:
        return declined(REASON_NO_STORY_DIFF, "the verified head carries no change against origin/main", evidence)
    if facts.verified_head == facts.current_head:
        evidence["basis"] = BASIS_HEAD_UNCHANGED
        evidence["commits"] = []
        return ReuseDecision(
            exempt=True, reason="exempt", basis=BASIS_HEAD_UNCHANGED, detail="head unchanged", evidence=evidence
        )
    if facts.chain is None or not facts.chain:
        return declined(
            REASON_NOT_ON_FIRST_PARENT_CHAIN,
            f"{facts.verified_head} is not on {facts.current_head}'s first-parent chain within {MAX_CHAIN_COMMITS} commits",
            evidence,
        )
    records: list[dict[str, object]] = []
    for commit in reversed(facts.chain):
        if len(commit.parents) == 1:
            outside = [path for path in commit.changed_paths if not planning(path)]
            if outside:
                return declined(
                    REASON_STORY_COMMIT,
                    f"commit {commit.sha} changes non-planning path(s): {', '.join(_cap(outside))}",
                    evidence,
                )
            records.append({"sha": commit.sha, "kind": "planning", "paths": _cap(commit.changed_paths)})
            continue
        if len(commit.parents) != 2:
            return declined(
                REASON_OCTOPUS_MERGE, f"merge {commit.sha} has {len(commit.parents)} parents, not two", evidence
            )
        if not commit.second_parent_on_main:
            return declined(
                REASON_MERGE_NOT_OF_MAIN,
                f"merge {commit.sha}'s second parent {commit.parents[1]} is not on origin/main",
                evidence,
            )
        code_conflicts = [path for path in commit.replay_conflicts if not planning(path)]
        if code_conflicts:
            return declined(
                REASON_MERGE_CONFLICT_OUTSIDE_PLANNING,
                f"merge {commit.sha} conflicts outside planning paths: {', '.join(_cap(code_conflicts))}",
                evidence,
            )
        policies = [path for path in commit.changed_paths if path.rsplit("/", 1)[-1] == POLICY_BASENAME]
        if policies:
            return declined(
                REASON_MERGE_TOUCHES_POLICY,
                f"merge {commit.sha} changes a station policy (its verify commands may move): {', '.join(_cap(policies))}",
                evidence,
            )
        touched = sorted(set(commit.changed_paths) & story_code)
        if touched:
            return declined(
                REASON_MERGE_TOUCHES_STORY_FILE,
                f"merge {commit.sha} changes the story's own path(s): {', '.join(_cap(touched))}",
                evidence,
            )
        resolution = [path for path in commit.resolution_paths if not planning(path)]
        if resolution:
            return declined(
                REASON_MERGE_RESOLUTION_OUTSIDE_PLANNING,
                f"merge {commit.sha} carries hand-made change(s) outside planning paths: {', '.join(_cap(resolution))}",
                evidence,
            )
        records.append(
            {
                "sha": commit.sha,
                "kind": "merge",
                "second_parent": commit.parents[1],
                "paths_from_main": len(commit.changed_paths),
                "planning_conflicts": _cap(commit.replay_conflicts),
                "planning_resolutions": _cap(commit.resolution_paths),
            }
        )
    stale = [path for path in facts.stale_main_paths if not planning(path)]
    if stale:
        return declined(
            REASON_MERGE_STALE_AGAINST_MAIN,
            f"path(s) a merge brought from main no longer read origin/main's content: {', '.join(_cap(stale))}",
            evidence,
        )
    evidence["basis"] = BASIS_MERGE_OF_MAIN
    evidence["commit_count"] = len(records)
    evidence["commits"] = records[:_EVIDENCE_PATH_CAP]
    return ReuseDecision(
        exempt=True,
        reason="exempt",
        basis=BASIS_MERGE_OF_MAIN,
        detail=f"{len(records)} commit(s) since the verified head, each a merge of main or planning-only",
        evidence=evidence,
    )
