"""Dispatch run work preservation (Story 22.6, FR-193 CAP-6, Epic 1 discipline).

Pure path helpers for the ``changes.patch`` analog under a dispatch run dir.
Git capture lives on ``VcsPort.worktree_unified_patch`` (``adapters/vcs_git``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


def _safe_segment(story_key: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", story_key).strip("-")
    return cleaned or "story"


def failed_patch_path(run_dir: Path, story_key: str) -> Path:
    """``run_dir/failed/<story>/changes.patch`` — dispatch's recovery ref."""
    return run_dir / "failed" / _safe_segment(story_key) / "changes.patch"


@dataclass(frozen=True)
class DispatchPreserveResult:
    """Outcome of parking recoverable dispatch work."""

    patch_path: Path | None
    patch_relative: str | None
    had_commits: bool
    had_uncommitted: bool


def relative_preserve_ref(run_dir: Path, patch_path: Path) -> str:
    """Repo-neutral ref string for journal / status (posix relative to run_dir)."""
    return patch_path.relative_to(run_dir).as_posix()
