"""Page-object mock family.

Seeded from Marshal's ``archive/.../tests/mocks/mock_worktree.py``
(MockWorktree) — a navigable workspace surface without real git ops — plus a
minimal ``BasePage`` so the family presents a page-object shape. Not rewritten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class BasePage:
    """Minimal page-object base for station UI / surface tests.

    Stations subclass and bind selectors / locators; the kit only owns the
    shared contract (a named root path and a validity check).
    """

    def __init__(self, root: Path | str, name: str = "page"):
        self.root = Path(root)
        self.name = name

    def is_valid(self) -> bool:
        """Default: valid when the root path exists."""
        return self.root.exists()


class MockWorktree:
    """Mock git worktree for unit testing (seeded from Marshal MockWorktree)."""

    def __init__(self, path: Path, branch: str = "main"):
        self.path = path
        self.branch = branch
        self.created = False
        self.deleted = False

    def create(self, branch: str | None = None) -> bool:
        """Simulate worktree creation."""
        self.created = True
        if branch:
            self.branch = branch
        return True

    def delete(self) -> bool:
        """Simulate worktree deletion."""
        if self.created and not self.deleted:
            self.deleted = True
            return True
        return False

    def is_valid(self) -> bool:
        """Check if worktree is valid (created and not deleted)."""
        return self.created and not self.deleted

    def get_branch(self) -> Optional[str]:
        """Get current branch."""
        if self.is_valid():
            return self.branch
        return None


class WorktreePage(BasePage):
    """Page-object view over a ``MockWorktree`` (seeded surface, not a rewrite)."""

    def __init__(self, worktree: MockWorktree, name: str = "worktree"):
        super().__init__(root=worktree.path, name=name)
        self.worktree = worktree

    def is_valid(self) -> bool:
        return self.worktree.is_valid()

    def open(self, branch: str | None = None) -> bool:
        """Open / create the worktree surface."""
        return self.worktree.create(branch=branch)

    def close(self) -> bool:
        """Close / delete the worktree surface."""
        return self.worktree.delete()
