"""Mechanical dispatch-land healing (Story 28.20, CAP-4).

Pure classification and ledger union live in ``core.dispatch_landing``; this
module orchestrates git/forge recovery when ``gh pr merge`` fails. Lives
outside ``core/`` so it may import ``adapters`` (AD-4), mirroring
``dispatch_land.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .adapters.vcs_git import VcsCommandError
from .core.chain_regen import parse_ledger_statuses, write_ledger_statuses
from .core.dispatch_landing import (
    is_mechanical_conflict_path,
    sprint_ledger_rel_path,
    union_sprint_ledger_maps,
    unknown_conflict_paths,
)
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
) -> DispatchLandHealResult:
    """Attempt ledger union or local main advance after ``merge_pr`` fails."""
    del head_sha, fs
    try:
        conflict_paths = vcs.merge_tree_conflict_paths(git_repo_root, base, head_branch)
    except VcsCommandError:
        return DispatchLandHealResult(healed=False)

    unknown = unknown_conflict_paths(conflict_paths)
    if unknown:
        return DispatchLandHealResult(healed=False, escalated_paths=unknown)

    try:
        merge_state = forge.pr_merge_state(repo_ref, pr.number)
    except ForgeCommandError:
        merge_state = "UNKNOWN"

    ledger_rel = _ledger_path(project_slug)
    ledger_file = worktree / ledger_rel

    if conflict_paths and all(is_mechanical_conflict_path(p) for p in conflict_paths):
        if _try_ledger_union_heal(
            project_slug=project_slug,
            git_repo_root=git_repo_root,
            worktree=worktree,
            base=base,
            head_branch=head_branch,
            subject=subject,
            merge_strategy=merge_strategy,
            delete_branch=delete_branch,
            repo_ref=repo_ref,
            pr=pr,
            ledger_rel=ledger_rel,
            ledger_file=ledger_file,
            vcs=vcs,
            forge=forge,
        ):
            return DispatchLandHealResult(healed=True, retried_forge_merge=True)

    # Re-probe after ledger union: conflicts may be cleared and GitHub may
    # still report DIRTY while merge-tree is clean (single-pass #985 recovery).
    try:
        conflict_paths = vcs.merge_tree_conflict_paths(git_repo_root, base, head_branch)
    except VcsCommandError:
        return DispatchLandHealResult(healed=False)

    unknown = unknown_conflict_paths(conflict_paths)
    if unknown:
        return DispatchLandHealResult(healed=False, escalated_paths=unknown)

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


def _try_ledger_union_heal(
    *,
    project_slug: str,
    git_repo_root: Path,
    worktree: Path,
    base: str,
    head_branch: str,
    subject: str,
    merge_strategy: str,
    delete_branch: bool,
    repo_ref: ForgeRef,
    pr: PrInfo,
    ledger_rel: str,
    ledger_file: Path,
    vcs: VcsPort,
    forge: ForgePort,
) -> bool:
    main_text = vcs.file_text_at_ref(git_repo_root, base, ledger_rel) or ""
    branch_text = vcs.file_text_at_ref(git_repo_root, head_branch, ledger_rel) or ""
    merged_map = union_sprint_ledger_maps(
        parse_ledger_statuses(main_text),
        parse_ledger_statuses(branch_text),
    )
    try:
        write_ledger_statuses(ledger_file, merged_map)
    except OSError:
        return False

    message = f"marshal: union sprint ledger for {project_slug!r} (CAP-4 heal)"
    try:
        rel_ledger = ledger_file.relative_to(worktree)
        vcs.commit_paths(worktree, (rel_ledger,), message)
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
        vcs.merge_branch(git_repo_root, head_branch, into=base, subject=subject)
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
