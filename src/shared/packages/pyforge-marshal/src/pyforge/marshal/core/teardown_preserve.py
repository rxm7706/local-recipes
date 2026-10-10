"""Teardown unpreserved-work scan (Story 87.7, CAP-287 / AD-81).

When ``pyforge.marshal.preserve_refs`` is on, ``run_teardown`` refuses while the
loop home holds recoverable work no durable ref reaches.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyforge.core.preserve_refs import (
    ARCHIVE_REF_PREFIX,
    ATTEMPT_PRESERVE_BRANCH_PREFIX,
    ATTEMPT_PRESERVE_DIRTY_PREFIX,
    PRESERVE_REF_PREFIX,
    list_local_preserve_tags,
    list_preserves,
    observe_preserve_debt,
    ref_on_origin,
    short_ref_name,
)

from ..ports.vcs import VcsPort, WorktreeEntry

_ORIGIN_MAIN = "refs/remotes/origin/main"
_PRESERVE_ARCHIVE_PREFIXES = (PRESERVE_REF_PREFIX, ARCHIVE_REF_PREFIX)
_FAILED_PATCH_GLOB = ".bmad-loop/runs/*/failed/*/changes.patch"
_BMAD_LOOP_BRANCH_PREFIX = "bmad-loop/"


@dataclass(frozen=True, slots=True)
class TeardownUnpreservedItem:
    """One abandonable item reported to the operator."""

    abandon_token: str
    message: str


@dataclass(frozen=True, slots=True)
class TeardownPreserveScan:
    items: tuple[TeardownUnpreservedItem, ...]
    preserve_debt_tags: tuple[str, ...]


def _commit_needs_preserve(vcs: VcsPort, repo_root: Path, tip: str) -> bool:
    """True when ``tip`` would be orphaned if its only ref were removed."""
    if vcs.is_commit_ancestor(repo_root, tip, _ORIGIN_MAIN):
        return False
    if vcs.commit_contained_in_tag_prefixes(repo_root, tip, _PRESERVE_ARCHIVE_PREFIXES):
        return False
    if vcs.commit_contained_in_remote_refs(repo_root, tip):
        return False
    return True


def _run_ids_under_home(home: Path) -> frozenset[str]:
    runs_dir = home / ".bmad-loop" / "runs"
    if not runs_dir.is_dir():
        return frozenset()
    return frozenset(child.name for child in runs_dir.iterdir() if child.is_dir() and not child.name.startswith("."))


def _reportable_failed_patches(home: Path) -> tuple[Path, ...]:
    pairs: list[Path] = []
    try:
        candidates = sorted(home.glob(_FAILED_PATCH_GLOB))
    except OSError:
        return ()
    for path in candidates:
        try:
            if path.is_file() and path.stat().st_size > 0:
                pairs.append(path)
        except OSError:
            continue
    return tuple(pairs)


def _preserve_sources_for_home(repo_root: Path, home: Path) -> frozenset[str]:
    """Every ``Preserve-Source`` value that names a patch under ``home``."""
    sources: set[str] = set()
    try:
        for record in list_preserves(repo_root):
            src = record.trailers.source.strip()
            if not src:
                continue
            sources.add(src)
            if not src.startswith("/"):
                sources.add(str(home / src))
                try:
                    sources.add(str((home / src).resolve().relative_to(home.resolve())))
                except ValueError:
                    pass
    except Exception:
        return frozenset()
    return frozenset(sources)


def _patch_abandon_token(home: Path, patch: Path) -> str:
    try:
        return patch.relative_to(home).as_posix()
    except ValueError:
        return patch.as_posix()


def _patch_covered_by_preserve(home: Path, patch: Path, sources: frozenset[str]) -> bool:
    token = _patch_abandon_token(home, patch)
    if token in sources:
        return True
    return str(patch) in sources or patch.name in sources


def _scratch_belongs_to_home(refname: str, run_ids: frozenset[str]) -> bool:
    short = short_ref_name(refname)
    if short.startswith(ATTEMPT_PRESERVE_DIRTY_PREFIX.removeprefix("refs/")):
        return True
    if not short.startswith(ATTEMPT_PRESERVE_BRANCH_PREFIX):
        return False
    rest = short[len(ATTEMPT_PRESERVE_BRANCH_PREFIX) :]
    run_part = rest.split("-", 1)[0] if rest else ""
    if run_part in run_ids:
        return True
    return any(rest.startswith(f"{run_id}-") for run_id in run_ids)


def _bmad_loop_branch_belongs(run_ids: frozenset[str], branch: str) -> bool:
    if not branch.startswith(_BMAD_LOOP_BRANCH_PREFIX):
        return False
    rest = branch[len(_BMAD_LOOP_BRANCH_PREFIX) :]
    run_id = rest.split("/", 1)[0] if rest else ""
    return run_id in run_ids


def scan_teardown_unpreserved(
    *,
    repo_root: Path,
    home: Path,
    slug: str,
    branch: str,
    vcs: VcsPort,
    nested_worktrees: tuple[WorktreeEntry, ...],
) -> TeardownPreserveScan:
    """Collect unpreserved items and local-only preserve tags (debt, not refusal)."""
    run_ids = _run_ids_under_home(home)
    preserve_sources = _preserve_sources_for_home(repo_root, home)
    items: list[TeardownUnpreservedItem] = []

    for patch in _reportable_failed_patches(home):
        if _patch_covered_by_preserve(home, patch, preserve_sources):
            continue
        token = _patch_abandon_token(home, patch)
        items.append(
            TeardownUnpreservedItem(
                abandon_token=token,
                message=f"unpreserved failed-story patch {token}",
            )
        )

    observation = observe_preserve_debt(repo_root)
    if observation is not None:
        for refname in observation.unpromoted_scratch:
            if not _scratch_belongs_to_home(refname, run_ids):
                continue
            token = short_ref_name(refname)
            items.append(
                TeardownUnpreservedItem(
                    abandon_token=token,
                    message=f"unpromoted engine scratch ref {token}",
                )
            )

    branches_to_check: set[str] = set()
    if branch:
        branches_to_check.add(branch)
    try:
        all_worktrees = vcs.list_worktrees(repo_root)
    except Exception:
        all_worktrees = nested_worktrees
    for wt in (*all_worktrees, *nested_worktrees):
        if wt.branch and home in wt.path.parents:
            if wt.branch.startswith(_BMAD_LOOP_BRANCH_PREFIX) and _bmad_loop_branch_belongs(run_ids, wt.branch):
                branches_to_check.add(wt.branch)
    for nested in nested_worktrees:
        if nested.branch:
            branches_to_check.add(nested.branch)

    for br in sorted(branches_to_check):
        if br == branch and vcs.remote_branch_exists(repo_root, br):
            continue
        try:
            tip = vcs.resolve_ref(repo_root, br)
        except Exception:
            continue
        if not _commit_needs_preserve(vcs, repo_root, tip):
            continue
        items.append(
            TeardownUnpreservedItem(
                abandon_token=br,
                message=f"branch {br} holds commits no durable ref reaches",
            )
        )

    debt_tags: list[str] = []
    if observation is not None:
        for tag in observation.local_only_tags:
            if tag.project_slug in {slug, f"pyforge-{slug}", slug.removeprefix("pyforge-")}:
                debt_tags.append(short_ref_name(tag.refname))
            elif tag.project_slug is None:
                debt_tags.append(short_ref_name(tag.refname))
        for tag in list_local_preserve_tags(repo_root):
            ref_short = short_ref_name(tag.refname)
            if ref_short not in debt_tags and not ref_on_origin(repo_root, tag.refname):
                if tag.project_slug in {slug, f"pyforge-{slug}", slug.removeprefix("pyforge-")}:
                    debt_tags.append(ref_short)

    deduped: dict[str, TeardownUnpreservedItem] = {}
    for item in items:
        deduped[item.abandon_token] = item
    return TeardownPreserveScan(
        items=tuple(sorted(deduped.values(), key=lambda i: i.abandon_token)),
        preserve_debt_tags=tuple(sorted(set(debt_tags))),
    )
