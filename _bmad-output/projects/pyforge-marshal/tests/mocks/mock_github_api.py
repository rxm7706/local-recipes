"""
Mock GitHub API for unit tests.

Stubs GitHub PR, branch, and repository operations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


class MockGitHubAPI:
    """Mock GitHub API for testing."""

    def __init__(self, owner: str = "test-owner", repo: str = "test-repo"):
        self.owner = owner
        self.repo = repo
        self.pull_requests: Dict[int, Dict[str, Any]] = {}
        self.branches: Dict[str, Dict[str, Any]] = {}
        self.pr_counter = 0

    def create_pull_request(
        self,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> Dict[str, Any]:
        """Simulate PR creation."""
        self.pr_counter += 1
        pr = {
            "number": self.pr_counter,
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "state": "open",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "html_url": f"https://github.com/{self.owner}/{self.repo}/pull/{self.pr_counter}",
        }
        self.pull_requests[self.pr_counter] = pr
        self.branches[head] = {"name": head, "sha": f"abc{self.pr_counter}def"}
        return pr

    def get_pull_request(self, number: int) -> Optional[Dict[str, Any]]:
        """Get PR by number."""
        return self.pull_requests.get(number)

    def merge_pull_request(self, number: int) -> bool:
        """Simulate PR merge."""
        if number in self.pull_requests:
            self.pull_requests[number]["state"] = "merged"
            self.pull_requests[number]["merged_at"] = datetime.now().isoformat()
            return True
        return False

    def delete_branch(self, branch: str) -> bool:
        """Simulate branch deletion."""
        if branch in self.branches:
            del self.branches[branch]
            return True
        return False

    def get_branch(self, branch: str) -> Optional[Dict[str, Any]]:
        """Get branch info."""
        return self.branches.get(branch)

    def list_pull_requests(self, state: str = "all") -> List[Dict[str, Any]]:
        """List PRs filtered by state."""
        if state == "all":
            return list(self.pull_requests.values())
        return [pr for pr in self.pull_requests.values() if pr["state"] == state]

    def update_pull_request(
        self,
        number: int,
        title: str = None,
        body: str = None,
    ) -> bool:
        """Update PR metadata."""
        if number not in self.pull_requests:
            return False
        pr = self.pull_requests[number]
        if title:
            pr["title"] = title
        if body:
            pr["body"] = body
        pr["updated_at"] = datetime.now().isoformat()
        return True
