"""Dispatch commit paths that must never carry the CFE surface (Story 83.19)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyforge.testing_kit.branch_diff_guard import ORIGIN_MAIN, unsanctioned_commits
from pyforge.testing_kit.cfe_surface import (
    CFE_CHANGELOG_PATH,
    CFE_GIT_PATHSPECS,
    RULE2_RETRO_SUBJECT_HINT,
    is_cfe_surface_path,
    partition_paths,
)

from .commit_vcs import CommittingVcs
from .egress import to_redacted_text
from .model import Finding, Severity

CFE_COMMIT_GATE_CODE = "MRS-GATE-020"

RETRO_CFE_COMMIT_SUBJECT = "retro(cfe): dispatch session CFE changes (Story 83.19)"


def paths_excluding_cfe(paths: tuple[str, ...] | list[str]) -> tuple[Path, ...]:
    """Repo-relative ``Path``s dispatch may commit outside a sanctioned retro."""
    non_cfe, _ = partition_paths(tuple(paths))
    return tuple(Path(path) for path in non_cfe)


def pending_cfe_paths(changed_paths: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """CFE-surface paths among ``changed_paths``."""
    _, cfe = partition_paths(tuple(changed_paths))
    return cfe


@dataclass(frozen=True)
class CfeRetroCommitResult:
    committed: bool
    finding: Finding | None = None


def commit_pending_cfe_retro(
    vcs: CommittingVcs,
    *,
    worktree: Path,
    changed_paths: tuple[str, ...],
) -> CfeRetroCommitResult:
    """Commit remaining CFE edits in one ``retro(cfe):`` commit when Rule 2 is satisfied."""
    cfe_paths = pending_cfe_paths(changed_paths)
    if not cfe_paths:
        return CfeRetroCommitResult(committed=False)
    if CFE_CHANGELOG_PATH not in cfe_paths:
        return CfeRetroCommitResult(
            committed=False,
            finding=Finding(
                code=CFE_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=(
                    "dispatch CFE edits cannot land without a CFE CHANGELOG.md change in the same "
                    f"commit — Rule 2 requires {RULE2_RETRO_SUBJECT_HINT}; "
                    f"pending CFE paths: {', '.join(cfe_paths)}"
                ),
            ),
        )
    try:
        vcs.commit_paths(
            worktree,
            tuple(Path(path) for path in cfe_paths),
            to_redacted_text(RETRO_CFE_COMMIT_SUBJECT),
        )
    except Exception as exc:
        return CfeRetroCommitResult(
            committed=False,
            finding=Finding(
                code=CFE_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=f"dispatch could not commit pending CFE paths as retro(cfe): {exc}",
            ),
        )
    return CfeRetroCommitResult(committed=True)


def findings_for_unsanctioned_cfe_commits(worktree: Path, *, base: str = ORIGIN_MAIN) -> tuple[Finding, ...]:
    """Refuse when ``base..HEAD`` carries a non-retro CFE commit or uncommitted CFE dirty paths."""
    bad = unsanctioned_commits(
        worktree,
        pathspec=CFE_GIT_PATHSPECS,
        changelog_path=CFE_CHANGELOG_PATH,
        base=base,
    )
    if not bad:
        return ()
    detail = "; ".join(bad)
    return (
        Finding(
            code=CFE_COMMIT_GATE_CODE,
            severity=Severity.ERROR,
            message=(
                "conda-forge-expert surface changed vs origin/main outside a sanctioned retro commit "
                f"({RULE2_RETRO_SUBJECT_HINT}): {detail}"
            ),
        ),
    )


def filter_story_py_paths_excluding_cfe(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Story-scoped ruff paths must not include CFE ``.py`` files (defensive)."""
    return tuple(path for path in paths if not is_cfe_surface_path(path))
