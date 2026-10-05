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

from ..ports.vcs import VcsPort
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
# Story 83.24: an unsanctioned CFE commit already on the branch -- terminal (no fix turn, no retry).
CFE_BRANCH_COMMIT_GATE_CODE = "MRS-GATE-021"

RULE2_REQUIREMENT = (
    "Rule 2: a commit touching the conda-forge-expert surface must have a subject starting "
    "`retro:` or `retro(<scope>):` and move the CFE CHANGELOG.md in the same commit"
)

_CFE_SKILL_PATH = ".claude/skills/conda-forge-expert/SKILL.md"
_CFE_VERSION_RE = re.compile(r"(?m)^version:\s*([0-9]+(?:\.[0-9]+)*+)\s*$")


def is_cfe_surface_path(path: str) -> bool:
    """True when the repo-relative ``path`` is on the CFE surface."""
    normalized = path.replace("\\", "/")
    return normalized in CFE_SURFACE_FILES or normalized.startswith(CFE_SURFACE_PREFIXES)


def paths_excluding_cfe(paths: Iterable[str]) -> tuple[Path, ...]:
    """Repo-relative ``Path``s from ``paths`` that a dispatch commit may carry, in order.

    Story 83.24: prefer :func:`non_retro_commit_paths` for porcelain-aware rename pairs."""
    return tuple(Path(path) for path in paths if not is_cfe_surface_path(path))


def pending_cfe_paths(paths: Iterable[str]) -> tuple[str, ...]:
    """The CFE-surface paths among ``paths``, sorted.

    Story 83.24: prefer :func:`pending_cfe_paths_from_status` when porcelain records are available."""
    return tuple(sorted(path for path in paths if is_cfe_surface_path(path)))


def _record_sides(path: str, original: str | None) -> tuple[str, ...]:
    return (path, original) if original is not None else (path,)


def partition_status_records_for_cfe(
    records: Iterable[tuple[str, str, str | None]],
) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    """Split porcelain records into non-retro commit paths and CFE pending paths (Story 83.24).

    A record is CFE when either side is on the CFE surface; the whole record stays out of non-retro
    commits and every side joins the retro pending set."""
    commit_paths: list[Path] = []
    cfe_paths: list[str] = []
    seen_commit: set[str] = set()
    seen_cfe: set[str] = set()

    for _status, path, original in records:
        sides = _record_sides(path, original)
        if any(is_cfe_surface_path(side) for side in sides):
            for side in sides:
                if side not in seen_cfe:
                    seen_cfe.add(side)
                    cfe_paths.append(side)
        else:
            for side in sides:
                if side not in seen_commit and side not in seen_cfe:
                    seen_commit.add(side)
                    commit_paths.append(Path(side))
    return tuple(commit_paths), tuple(sorted(cfe_paths))


def non_retro_commit_paths(
    vcs: VcsPort,
    *,
    worktree: Path,
    extra_paths: Iterable[str] = (),
    repo_root: Path | None = None,
) -> tuple[Path, ...]:
    """Paths a dispatch non-retro commit may carry, excluding CFE rename pairs."""
    getter = getattr(vcs, "status_porcelain_z_records", None)
    if getter is None:
        root = repo_root if repo_root is not None else worktree
        commit_paths = paths_excluding_cfe(vcs.changed_files(root, worktree, base="HEAD"))
    else:
        commit_paths, _ = partition_status_records_for_cfe(getter(worktree))
    extras: list[Path] = []
    seen = {path.as_posix() for path in commit_paths}
    for path in extra_paths:
        if is_cfe_surface_path(path) or path in seen:
            continue
        seen.add(path)
        extras.append(Path(path))
    return commit_paths + tuple(extras)


def pending_cfe_paths_from_status(vcs: VcsPort, *, worktree: Path) -> tuple[str, ...]:
    """CFE pending paths from porcelain records (both sides of a CFE rename)."""
    _, cfe_paths = partition_status_records_for_cfe(vcs.status_porcelain_z_records(worktree))
    return cfe_paths


def read_cfe_skill_version(repo_root: Path) -> str:
    """Read the live ``version:`` from the CFE ``SKILL.md`` (Story 83.24 retro subject)."""
    skill = repo_root / _CFE_SKILL_PATH
    text = skill.read_text(encoding="utf-8")
    match = _CFE_VERSION_RE.search(text)
    if not match:
        raise ValueError(f"could not read CFE version from {_CFE_SKILL_PATH}")
    return match.group(1)


def retro_cfe_commit_subject(*, story_key: str, cfe_version: str) -> str:
    """``retro(cfe): vX.Y.Z -- dispatch session CFE changes (Story N.M)`` (Story 83.24)."""
    return f"retro(cfe): v{cfe_version} -- dispatch session CFE changes (Story {story_key})"


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
    story_key: str,
    repo_root: Path,
) -> CfeRetroCommitResult:
    """Commit the uncommitted CFE paths once, as ``retro(cfe):``, when Rule 2 holds.

    No CFE path pending: nothing to do. CFE paths pending without the CFE ``CHANGELOG.md``
    among them: refuse naming Rule 2 and commit nothing."""
    try:
        cfe_paths = pending_cfe_paths_from_status(vcs, worktree=worktree)
    except AttributeError:
        cfe_paths = pending_cfe_paths(changed_paths)
    except Exception as exc:
        return CfeRetroCommitResult(
            committed=False,
            finding=Finding(
                code=CFE_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=f"dispatch CFE retro commit could not read porcelain status: {exc}",
            ),
        )
    if not cfe_paths:
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
        cfe_version = read_cfe_skill_version(repo_root)
        subject = retro_cfe_commit_subject(story_key=story_key, cfe_version=cfe_version)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return CfeRetroCommitResult(
            committed=False,
            paths=cfe_paths,
            finding=Finding(
                code=CFE_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=f"dispatch could not build the CFE retro commit subject: {exc}",
            ),
        )
    try:
        vcs.commit_paths(
            worktree,
            tuple(Path(path) for path in cfe_paths),
            to_redacted_text(subject),
        )
    except Exception as exc:
        return CfeRetroCommitResult(
            committed=False,
            paths=cfe_paths,
            finding=Finding(
                code=CFE_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=f"dispatch could not commit the pending CFE paths as {subject!r}: {exc}",
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
    """One finding per unsanctioned shape -- ``MRS-GATE-021`` on-branch, ``MRS-GATE-020`` uncommitted."""
    if not entries:
        return ()
    branch_entries = [entry for entry in entries if not entry.startswith("uncommitted:")]
    dirty_entries = [entry for entry in entries if entry.startswith("uncommitted:")]
    findings: list[Finding] = []
    if branch_entries:
        findings.append(
            Finding(
                code=CFE_BRANCH_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=(
                    f"the conda-forge-expert surface moved on {base}..HEAD outside a sanctioned retro "
                    f"({RULE2_REQUIREMENT}): {'; '.join(branch_entries)}"
                ),
            )
        )
    if dirty_entries:
        findings.append(
            Finding(
                code=CFE_COMMIT_GATE_CODE,
                severity=Severity.ERROR,
                message=(
                    f"the conda-forge-expert surface has uncommitted changes outside a sanctioned retro "
                    f"({RULE2_REQUIREMENT}): {'; '.join(dirty_entries)}"
                ),
            )
        )
    return tuple(findings)


def unsanctioned_cfe_commit_entries(entries: Collection[str]) -> tuple[str, ...]:
    """Committed unsanctioned entries only (not ``uncommitted:`` lines)."""
    return tuple(entry for entry in entries if not entry.startswith("uncommitted:"))


def is_terminal_cfe_verify_refusal(failed_gate: str | None) -> bool:
    """True when verification refused for an on-branch CFE violation (Story 83.24)."""
    return failed_gate == CFE_BRANCH_COMMIT_GATE_CODE
