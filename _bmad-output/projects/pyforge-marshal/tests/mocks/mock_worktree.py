"""
Mock worktree for unit tests.

Simulates worktree creation/deletion without actual git operations.
"""

from pathlib import Path
from typing import Optional


class MockWorktree:
    """Mock git worktree for unit testing."""

    def __init__(self, path: Path, branch: str = "main"):
        self.path = path
        self.branch = branch
        self.created = False
        self.deleted = False

    def create(self, branch: str = None) -> bool:
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
