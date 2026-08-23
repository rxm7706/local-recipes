"""pyforge.testing_kit — shared test-support kit (FR-130 / Story 19.2).

Four mock families seeded from Marshal's already-real mocks (not rewritten).
Q-26: own leaf package ``pyforge-testing-kit``, not ``pyforge.core.testing``.

PEP 420: this package must NOT ship ``src/pyforge/__init__.py`` — ``pyforge``
is a shared namespace across stations.
"""

from __future__ import annotations

from pyforge.testing_kit.auth_http_time import FrozenClock, MockGitHubAPI
from pyforge.testing_kit.cli_runner import CliRunner, MockRunner
from pyforge.testing_kit.db_factory import (
    LoopHome,
    MockSupervisor,
    RunJournal,
    RunStateFactory,
    record_factory,
)
from pyforge.testing_kit.page_object import BasePage, MockWorktree, WorktreePage

__version__ = "0.1.0"

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
