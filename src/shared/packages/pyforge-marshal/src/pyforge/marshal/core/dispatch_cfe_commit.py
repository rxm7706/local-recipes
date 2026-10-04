"""Dispatch never commits the conda-forge-expert surface outside a sanctioned retro (Story 83.19).

Every station's "CFE not replaced" meta-test runs
``pyforge.testing_kit.branch_diff_guard.unsanctioned_commits``, which refuses a branch
commit that touches the CFE surface unless its subject starts ``retro:`` /
``retro(<scope>):`` AND the CFE ``CHANGELOG.md`` moves in the same commit (Rule 2). A
dispatch ``wip:`` checkpoint can never satisfy that, so dispatch's own commits leave the
surface out, and verification commits it once as ``retro(cfe):`` or refuses.

One owner. The surface is defined by ``pyforge.testing_kit.cfe_surface`` and the Rule-2
retro subject by ``branch_diff_guard``. A production station never depends on the testing
kit at runtime, so the constants below are marshal's mirror of that owner, not a second
definition: ``tests/unit/test_dispatch_cfe_commit.py`` fails the build when they differ
from the kit's, and checks :func:`unsanctioned_cfe_entries` against ``unsanctioned_commits``
itself on real git repositories.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from pathlib import Path

from .commit_vcs import CommittingVcs
from .egress import to_redacted_text
from .model import Finding, Severity

#: Mirror of ``pyforge.testing_kit.cfe_surface.CFE_CHANGELOG_PATH``.
CFE_CHANGELOG_PATH = ".claude/skills/conda-forge-expert/CHANGELOG.md"

#: Mirror of ``pyforge.testing_kit.cfe_surface.CFE_SURFACE_PREFIXES``.
CFE_SURFACE_PREFIXES: tuple[str, ...] = (
    ".claude/skills/conda-forge-expert/",
    ".claude/scripts/conda-forge-expert/",
)

#: Mirror of ``pyforge.testing_kit.cfe_surface.CFE_SURFACE_FILES``.
CFE_SURFACE_FILES: frozenset[str] = frozenset({".claude/tools/conda_forge_server.py"})

#: Mirror of ``pyforge.testing_kit.cfe_surface.CFE_GIT_PATHSPECS`` (``git log`` / ``git diff``).
CFE_GIT_PATHSPECS: tuple[str, ...] = (
    ".claude/skills/conda-forge-expert",
    ".claude/scripts/conda-forge-expert",
    ".claude/tools/conda_forge_server.py",
)

#: Mirror of ``branch_diff_guard._RETRO_SUBJECT``: ``retro:`` or ``retro(<scope>):``.
RETRO_SUBJECT = re.compile(r"^retro(\([^)]*\))?:")

CFE_COMMIT_GATE_CODE = "MRS-GATE-020"

RULE2_REQUIREMENT = (
    "Rule 2: a commit touching the conda-forge-expert surface must have a subject starting "
    "`retro:` or `retro(<scope>):` and move the CFE CHANGELOG.md in the same commit"
)

RETRO_CFE_COMMIT_SUBJECT = "retro(cfe): dispatch session CFE changes (Story 83.19)"


def is_cfe_surface_path(path: str) -> bool:
    """True when the repo-relative ``path`` is on the CFE surface."""
    normalized = path.replace("\\", "/")
    return normalized in CFE_SURFACE_FILES or normalized.startswith(CFE_SURFACE_PREFIXES)


def paths_excluding_cfe(paths: Iterable[str]) -> tuple[Path, ...]:
    """Repo-relative ``Path``s from ``paths`` that a dispatch commit may carry, in order."""
    return tuple(Path(path) for path in paths if not is_cfe_surface_path(path))


def pending_cfe_paths(paths: Iterable[str]) -> tuple[str, ...]:
    """The CFE-surface paths among ``paths``, sorted."""
    return tuple(sorted(path for path in paths if is_cfe_surface_path(path)))


@dataclass(frozen=True)
class CfeRetroCommitResult:
    committed: bool
    paths: tuple[str, ...] = ()
    finding: Finding | None = None


def commit_pending_cfe_retro(
    vcs: CommittingVcs,
    *,
    worktree: Path,
    changed_paths: Iterable[str],
) -> CfeRetroCommitResult:
    """Commit the uncommitted CFE paths once, as ``retro(cfe):``, when Rule 2 holds.

    No CFE path pending: nothing to do. CFE paths pending without the CFE ``CHANGELOG.md``
    among them: refuse naming Rule 2 and commit nothing."""
    cfe_paths = pending_cfe_paths(changed_paths)
    if not cfe_paths:
        return CfeRetroCommitResult(committed=False)
    if CFE_CHANGELOG_PATH not in cfe_paths:
        return CfeRetroCommitResult(
            committed=False,
            paths=cfe_paths,
            finding=Finding(
                code=CFE_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=(
                    f"dispatch cannot land conda-forge-expert edits without a {CFE_CHANGELOG_PATH} change "
                    f"in the same commit -- {RULE2_REQUIREMENT}; pending CFE paths: {', '.join(cfe_paths)}"
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
            paths=cfe_paths,
            finding=Finding(
                code=CFE_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=f"dispatch could not commit the pending CFE paths as {RETRO_CFE_COMMIT_SUBJECT!r}: {exc}",
            ),
        )
    return CfeRetroCommitResult(committed=True, paths=cfe_paths)


def unsanctioned_cfe_entries(
    commits: Iterable[tuple[str, str, Collection[str]]],
    dirty: Iterable[str],
) -> list[str]:
    """``unsanctioned_commits``'s verdict over already-read git facts.

    ``commits`` are ``(sha, subject, files)`` for each non-merge commit on ``base..HEAD``
    touching the surface; ``dirty`` is ``git diff --name-only HEAD`` under the surface. Each
    entry has the guard's own shape: ``"<sha10> <subject>"``, then ``"uncommitted: ..."``."""
    bad = [
        f"{sha[:10]} {subject}"
        for sha, subject, files in commits
        if not (RETRO_SUBJECT.match(subject) and CFE_CHANGELOG_PATH in files)
    ]
    dirty_paths = list(dirty)
    if dirty_paths:
        bad.append("uncommitted: " + ", ".join(dirty_paths))
    return bad


def findings_for_unsanctioned_cfe_entries(entries: Collection[str], *, base: str) -> tuple[Finding, ...]:
    """One ``MRS-GATE-020`` naming every offending commit, or nothing."""
    if not entries:
        return ()
    return (
        Finding(
            code=CFE_COMMIT_GATE_CODE,
            severity=Severity.ERROR,
            message=(
                f"the conda-forge-expert surface moved on {base}..HEAD outside a sanctioned retro "
                f"({RULE2_REQUIREMENT}): {'; '.join(entries)}"
            ),
        ),
    )
