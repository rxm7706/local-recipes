"""pyforge.testing_kit — shared test-support kit (FR-130 / Story 19.2).

Five families: four seeded from Marshal's already-real mocks (not rewritten), and the
feature-flag family (``pyforge.testing_kit.flags``, spec-feature-flag-governance CAP-4).
Q-26: own leaf package ``pyforge-testing-kit``, not ``pyforge.core.testing``.

PEP 420: this package must NOT ship ``src/pyforge/__init__.py`` — ``pyforge``
is a shared namespace across stations.
"""

from __future__ import annotations

from pyforge.testing_kit.auth_http_time import FrozenClock, MockGitHubAPI
from pyforge.testing_kit.branch_diff_guard import (
    ORIGIN_MAIN,
    changed_paths_since,
    commit_files,
    commit_subject,
    commits_since,
    diff_text_since,
    existed_at_ref,
    pyforge_import_offenders,
    unsanctioned_commits,
)
from pyforge.testing_kit.cli_runner import CliResult, CliRunner, MockRunner, invoke_cli
from pyforge.testing_kit.db_factory import (
    LoopHome,
    MockSupervisor,
    RunJournal,
    RunStateFactory,
    record_factory,
)
from pyforge.testing_kit.flags import (
    assert_flag_off_verb,
    flag_states,
    flagd_tree,
    installed_flags,
    make_flag_provider_fixture,
)
from pyforge.testing_kit.page_object import BasePage, MockWorktree, WorktreePage

__version__ = "0.1.0"

__all__ = [
    "BasePage",
    "CliResult",
    "CliRunner",
    "FrozenClock",
    "LoopHome",
    "MockGitHubAPI",
    "MockRunner",
    "MockSupervisor",
    "MockWorktree",
    "ORIGIN_MAIN",
    "RunJournal",
    "RunStateFactory",
    "WorktreePage",
    "assert_flag_off_verb",
    "changed_paths_since",
    "commit_files",
    "commit_subject",
    "commits_since",
    "diff_text_since",
    "existed_at_ref",
    "flag_states",
    "flagd_tree",
    "installed_flags",
    "invoke_cli",
    "make_flag_provider_fixture",
    "pyforge_import_offenders",
    "record_factory",
    "unsanctioned_commits",
]
