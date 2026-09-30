"""Mechanical dispatch-land healing (Story 28.20, CAP-4).

Pure classification and the ledger and memlog unions live in ``core.dispatch_landing``; this
module orchestrates git/forge recovery when ``gh pr merge`` fails. Lives
outside ``core/`` so it may import ``adapters`` (AD-4), mirroring
``dispatch_land.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .adapters.vcs_git import VcsCommandError
from .core.chain_regen import parse_ledger_statuses, render_ledger_statuses
from .core.dispatch_landing import (
    is_mechanical_conflict_path,
    is_memlog_path,
    sprint_ledger_rel_path,
    three_way_ledger_statuses,
    union_memlog_texts,
    unknown_conflict_paths,
)
from .core.refs import local_branch_ref
from .ports.forge import ForgeCommandError, ForgePort, ForgeRef, PrInfo
from .ports.fs import FsPort
from .ports.vcs import VcsPort

# GitHub merge states where ``merge-tree`` is authoritative — stale API
# mergeability only (PR #985 DIRTY path). Excludes ``BLOCKED`` (red CI) and
# ``BEHIND`` (branch lag); those must not bypass gates via local merge.
_STALE_GITHUB_MERGE_STATES = frozenset({"CONFLICTING", "DIRTY"})


@dataclass(frozen=True)
class DispatchLandHealResult:
    """Outcome of a post-merge-failure heal attempt."""

    healed: bool
    landed_via_local_merge: bool = False
    retried_forge_merge: bool = False
    escalated_paths: tuple[str, ...] = ()
    healed_memlog_paths: tuple[str, ...] = ()


def _ledger_path(project_slug: str) -> str:
    return sprint_ledger_rel_path(project_slug)


def try_heal_dispatch_land_merge(
    *,
    project_slug: str,
    git_repo_root: Path,
    worktree: Path,
    base: str,
    head_branch: str,
    head_sha: str,
    subject: str,
    merge_strategy: str,
    delete_branch: bool,
    repo_ref: ForgeRef,
    pr: PrInfo,
    fs: FsPort,
    vcs: VcsPort,
    forge: ForgePort,
    probe_ref: str | None = None,
) -> DispatchLandHealResult:
    """Attempt ledger union or local main advance after ``merge_pr`` fails.

    ``probe_ref`` is what conflicts are measured against and what the ledger union merges --
    ``dispatch land`` passes ``refs/remotes/origin/main`` right after fetching it, the ref GitHub
    merges against (Story 59.1). ``base`` stays the local branch the local-merge fallback merges
    into and pushes. ``probe_ref`` defaults to ``base``'s full ref. Every git read of ``base`` or
    ``head_branch`` names ``refs/heads/<branch>``, so a tag of the same name cannot stand in
    (Story 61.1). Only the landing project's own sprint ledger and append-only Spec memlogs
    (``.memlog.md``, Story 78.1) are mechanical; any other conflicted path, and any memlog that
    is not append-only on both sides, escalates by name."""
    del head_sha, fs
    probe = probe_ref if probe_ref is not None else local_branch_ref(base)
    ledger_rel = _ledger_path(project_slug)
    try:
        conflict_paths = vcs.merge_tree_conflict_paths(git_repo_root, probe, local_branch_ref(head_branch))
    except VcsCommandError:
        return DispatchLandHealResult(healed=False)

    unknown = unknown_conflict_paths(conflict_paths, ledger_rel=ledger_rel)
    memlog_paths = tuple(sorted(p for p in conflict_paths if is_memlog_path(p)))
    resolutions: dict[str, str] = {}
    if memlog_paths or ledger_rel in conflict_paths:
        resolved = _resolve_mechanical_conflicts(
            git_repo_root=git_repo_root,
            probe=probe,
            head_branch=head_branch,
            ledger_rel=ledger_rel,
            conflict_paths=conflict_paths,
            memlog_paths=memlog_paths,
            vcs=vcs,
        )
        if resolved is None:
            return DispatchLandHealResult(healed=False, escalated_paths=unknown)
        resolutions, unresolved_memlogs = resolved
        unknown = tuple(sorted({*unknown, *unresolved_memlogs}))
    if unknown:
        return DispatchLandHealResult(healed=False, escalated_paths=unknown)

    try:
        merge_state = forge.pr_merge_state(repo_ref, pr.number)
    except ForgeCommandError:
        merge_state = "UNKNOWN"

    if conflict_paths and all(is_mechanical_conflict_path(p, ledger_rel=ledger_rel) for p in conflict_paths):
        # Story 59.1 review (high): the union heal is the whole answer for this attempt. Once
        # its merge is committed the branch probes clean while `merge_state` is the stale
        # pre-heal read, so falling through to the local-`main` advance would land the branch
        # on `main` past whatever made the forge refuse (a red check, a rejected push). The
        # #985 recovery still runs on the NEXT landing attempt, with a fresh probe and state.
        healed = _try_union_heal(
            project_slug=project_slug,
            git_repo_root=git_repo_root,
            worktree=worktree,
            probe=probe,
            head_branch=head_branch,
            subject=subject,
            merge_strategy=merge_strategy,
            delete_branch=delete_branch,
            repo_ref=repo_ref,
            pr=pr,
            resolutions=resolutions,
            has_ledger=ledger_rel in resolutions,
            has_memlogs=bool(memlog_paths),
            vcs=vcs,
            forge=forge,
        )
        return DispatchLandHealResult(
            healed=healed,
            retried_forge_merge=healed,
            healed_memlog_paths=memlog_paths if healed else (),
        )

    if not conflict_paths and merge_state in _STALE_GITHUB_MERGE_STATES:
        if _try_local_main_advance(
            git_repo_root=git_repo_root,
            base=base,
            head_branch=head_branch,
            subject=subject,
            delete_branch=delete_branch,
            repo_ref=repo_ref,
            pr=pr,
            vcs=vcs,
            forge=forge,
        ):
            return DispatchLandHealResult(healed=True, landed_via_local_merge=True)

    return DispatchLandHealResult(healed=False)


def _resolve_mechanical_conflicts(
    *,
    git_repo_root: Path,
    probe: str,
    head_branch: str,
    ledger_rel: str,
    conflict_paths: tuple[str, ...],
    memlog_paths: tuple[str, ...],
    vcs: VcsPort,
) -> tuple[dict[str, str], tuple[str, ...]] | None:
    """Story 59.1 (CAP-269) and Story 78.1 (CAP-283): the resolved text of every conflicted
    mechanical path, plus the memlogs with no resolution, or ``None`` on a git read failure.

    The ledger is resolved three-way against the merge base (``three_way_ledger_statuses``): a row
    one side changed takes that change, deletions hold, and precedence settles only a row both
    sides changed. A memlog is resolved by ``union_memlog_texts``: both sides only appended, or it
    is unresolved -- never merged line by line, so no entry is ever dropped."""
    try:
        head_ref = local_branch_ref(head_branch)
        base_sha = vcs.merge_base(git_repo_root, probe, head_ref)

        def texts(rel: str) -> tuple[str, str, str]:
            return (
                vcs.file_text_at_ref(git_repo_root, base_sha, rel) or "",
                vcs.file_text_at_ref(git_repo_root, probe, rel) or "",
                vcs.file_text_at_ref(git_repo_root, head_ref, rel) or "",
            )

        resolutions: dict[str, str] = {}
        if ledger_rel in conflict_paths:
            base_text, main_text, branch_text = texts(ledger_rel)
            merged_map = three_way_ledger_statuses(
                parse_ledger_statuses(base_text),
                parse_ledger_statuses(main_text),
                parse_ledger_statuses(branch_text),
            )
            resolutions[ledger_rel] = render_ledger_statuses(main_text or branch_text, merged_map)
        unresolved: list[str] = []
        for rel in memlog_paths:
            union = union_memlog_texts(*texts(rel))
            if union is None:
                unresolved.append(rel)
            else:
                resolutions[rel] = union
    except VcsCommandError:
        return None
    return resolutions, tuple(unresolved)


def _try_union_heal(
    *,
    project_slug: str,
    git_repo_root: Path,
    worktree: Path,
    probe: str,
    head_branch: str,
    subject: str,
    merge_strategy: str,
    delete_branch: bool,
    repo_ref: ForgeRef,
    pr: PrInfo,
    resolutions: Mapping[str, str],
    has_ledger: bool,
    has_memlogs: bool,
    vcs: VcsPort,
    forge: ForgePort,
) -> bool:
    """Story 59.1 (CAP-269): heal a ledger-only conflict with a real merge of ``probe`` into the
    dispatch branch -- a single-parent union commit (the Story 28.20 original) cleared a same-row
    status conflict but never adjacent added rows, since the retried three-way merge still saw
    both sides change the same lines. Story 78.1 (CAP-283) puts every conflicted memlog's
    resolution in the same ``resolutions`` map, so one merge heals them all. Any other conflicted
    path aborts the merge inside ``merge_ref_resolving``: nothing is committed or pushed."""
    what = " and ".join(name for name, present in (("sprint ledger", has_ledger), ("memlogs", has_memlogs)) if present)
    message = f"marshal: union {what} for {project_slug!r} while merging the base (CAP-4 heal)"
    try:
        vcs.merge_ref_resolving(worktree, probe, resolutions=resolutions, message=message)
        vcs.push(git_repo_root, head_branch)
        new_sha = vcs.resolve_ref(git_repo_root, head_branch)
    except VcsCommandError:
        return False

    try:
        forge.merge_pr(
            repo_ref,
            pr.number,
            ForgeRef(merge_strategy),
            expected_head_sha=ForgeRef(new_sha),
            delete_branch=delete_branch,
            subject=ForgeRef(subject),
        )
    except ForgeCommandError:
        return False
    return True


def _try_local_main_advance(
    *,
    git_repo_root: Path,
    base: str,
    head_branch: str,
    subject: str,
    delete_branch: bool,
    repo_ref: ForgeRef,
    pr: PrInfo,
    vcs: VcsPort,
    forge: ForgePort,
) -> bool:
    try:
        vcs.merge_branch(git_repo_root, local_branch_ref(head_branch), into=base, subject=subject)
    except VcsCommandError:
        return False

    try:
        vcs.push(git_repo_root, base)
    except VcsCommandError:
        return False

    try:
        forge.close_pr(repo_ref, pr.number)
    except ForgeCommandError:
        return False

    if delete_branch:
        try:
            vcs.delete_branch(git_repo_root, head_branch, force=True)
        except VcsCommandError:
            pass
    return True
