"""Dispatch branch durability before verify (Story 28.21, CAP-4).

Pure eligibility only: a commitable result exists and the branch is
attributable. The supervisor performs the push and journals the outcome.
"""

from __future__ import annotations

from .dispatch_completion import DispatchGitFacts, has_git_progress


def may_push_dispatch_branch_before_verify(
    git: DispatchGitFacts,
    *,
    branch_refusal: str | None = None,
) -> bool:
    """True when git shows progress and the branch is not refused."""
    if branch_refusal is not None:
        return False
    return has_git_progress(git)
