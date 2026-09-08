"""Re-export Marshal's four mock families from the shared kit (Story 19.2).

The archived Marshal mocks under
``archive/_bmad-output/projects/pyforge-marshal/tests/mocks/`` seeded
``pyforge-testing-kit``. This module is the station-local re-export so
Marshal tests import the shared kit rather than a local duplicate.
"""

from __future__ import annotations

from pyforge.testing_kit import (  # noqa: F401 — re-export surface
    BasePage,
    CliRunner,
    FrozenClock,
    LoopHome,
    MockGitHubAPI,
    MockRunner,
    MockSupervisor,
    MockWorktree,
    RunJournal,
    RunStateFactory,
    WorktreePage,
    record_factory,
)

__all__ = [
    "BasePage",
    "CliRunner",
    "FrozenClock",
    "LoopHome",
    "MockGitHubAPI",
    "MockRunner",
    "MockSupervisor",
    "MockWorktree",
    "RunJournal",
    "RunStateFactory",
    "WorktreePage",
    "record_factory",
]
