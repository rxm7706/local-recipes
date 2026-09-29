"""Auth / HTTP / time mock family.

Seeded from Marshal's ``archive/.../tests/mocks/mock_github_api.py``
(MockGitHubAPI) plus the timing surface of ``mock_supervisor.py``
(heartbeat interval / idle threshold) as ``FrozenClock``. Not rewritten.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional


class MockGitHubAPI:
    """Mock GitHub API for testing (seeded from Marshal MockGitHubAPI)."""

    def __init__(self, owner: str = "test-owner", repo: str = "test-repo"):
        self.owner = owner
        self.repo = repo
        self.pull_requests: dict[int, dict[str, Any]] = {}
        self.branches: dict[str, dict[str, Any]] = {}
        self.pr_counter = 0

    def create_pull_request(
        self,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> dict[str, Any]:
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
            "html_url": (f"https://github.com/{self.owner}/{self.repo}/pull/{self.pr_counter}"),
        }
        self.pull_requests[self.pr_counter] = pr
        self.branches[head] = {"name": head, "sha": f"abc{self.pr_counter}def"}
        return pr

    def get_pull_request(self, number: int) -> Optional[dict[str, Any]]:
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

    def get_branch(self, branch: str) -> Optional[dict[str, Any]]:
        """Get branch info."""
        return self.branches.get(branch)

    def list_pull_requests(self, state: str = "all") -> list[dict[str, Any]]:
        """List PRs filtered by state."""
        if state == "all":
            return list(self.pull_requests.values())
        return [pr for pr in self.pull_requests.values() if pr["state"] == state]

    def update_pull_request(
        self,
        number: int,
        title: str | None = None,
        body: str | None = None,
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


class FrozenClock:
    """Deterministic clock for auth/HTTP/time tests.

    Seeded from Marshal MockSupervisor's timing constants (heartbeat_interval /
    idle_threshold): stations advance time explicitly rather than sleeping.
    """

    def __init__(
        self,
        start: datetime | None = None,
        *,
        heartbeat_interval: int = 5,
        idle_threshold: int = 60,
    ):
        self._now = start or datetime(2026, 1, 1, 0, 0, 0)
        self.heartbeat_interval = heartbeat_interval
        self.idle_threshold = idle_threshold

    def now(self) -> datetime:
        """Current frozen instant."""
        return self._now

    def advance(self, seconds: float) -> datetime:
        """Advance the clock by ``seconds`` and return the new instant."""
        self._now = self._now + timedelta(seconds=seconds)
        return self._now

    def advance_heartbeat(self) -> datetime:
        """Advance by one heartbeat interval (supervisor seed default: 5s)."""
        return self.advance(self.heartbeat_interval)

    def is_idle(self, idle_seconds: float) -> bool:
        """Whether ``idle_seconds`` meets the idle threshold (default: 60s)."""
        return idle_seconds >= self.idle_threshold
