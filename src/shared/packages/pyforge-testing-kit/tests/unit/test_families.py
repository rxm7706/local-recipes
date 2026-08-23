"""Fixture-covered unit tests for the four mock families (Story 19.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.testing_kit import (
    BasePage,
    CliRunner,
    FrozenClock,
    LoopHome,
    MockGitHubAPI,
    MockRunner,
    MockSupervisor,
    MockWorktree,
    RunJournal,
    WorktreePage,
    record_factory,
)


@pytest.fixture
def runner() -> MockRunner:
    return CliRunner("story-19-2", execution_time=0.5)


@pytest.fixture
def worktree(tmp_path: Path) -> MockWorktree:
    return MockWorktree(tmp_path / "wt", branch="feature")


@pytest.fixture
def github() -> MockGitHubAPI:
    return MockGitHubAPI(owner="rxm7706", repo="local-recipes")


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock()


def test_cli_runner_executes_and_records_verdict(runner: MockRunner) -> None:
    assert runner.run() is True
    runner.set_verdict("WARNING")
    runner.add_finding("MRS-TEST-001", "warn", "seeded")
    result = runner.get_result()
    assert result["executed"] is True
    assert result["verdict"] == "WARNING"
    assert result["findings"][0]["code"] == "MRS-TEST-001"
    assert result["execution_time"] == 0.5


def test_cli_runner_rejects_invalid_verdict(runner: MockRunner) -> None:
    with pytest.raises(ValueError, match="Invalid verdict"):
        runner.set_verdict("NOPE")


def test_page_object_worktree_lifecycle(worktree: MockWorktree) -> None:
    page = WorktreePage(worktree)
    assert page.is_valid() is False
    assert page.open(branch="marshal/19-2") is True
    assert page.is_valid() is True
    assert worktree.get_branch() == "marshal/19-2"
    assert page.close() is True
    assert page.is_valid() is False


def test_base_page_validity(tmp_path: Path) -> None:
    missing = BasePage(tmp_path / "gone")
    assert missing.is_valid() is False
    present = BasePage(tmp_path)
    assert present.is_valid() is True


def test_db_factory_loop_home_and_journal(tmp_path: Path) -> None:
    home = LoopHome.provision(tmp_path / "home")
    try:
        assert home.state_file.is_file()
        journal = RunJournal(store=home.tier3_store)
        journal.append("test", {"k": 1})
        assert journal.read_all()[0]["event"] == "test"
        assert record_factory(code="X", severity="error", message="m", extra=1) == {
            "code": "X",
            "severity": "error",
            "message": "m",
            "extra": 1,
        }
    finally:
        home.teardown()
    assert not home.path.exists()


def test_db_factory_supervisor_run_state() -> None:
    supervisor = MockSupervisor("run-1")
    assert supervisor.attach() is True
    assert supervisor.send_heartbeat() is True
    assert supervisor.detect_idle(60) is True
    assert supervisor.escalate("stall", {"sec": 60}) is True
    assert supervisor.get_escalations()[0]["type"] == "stall"
    assert supervisor.detach() is True
    assert supervisor.send_heartbeat() is False


def test_auth_http_time_github_api(github: MockGitHubAPI) -> None:
    pr = github.create_pull_request("Story 19.2", head="marshal/19-2")
    assert pr["number"] == 1
    assert github.get_pull_request(1)["state"] == "open"
    assert github.merge_pull_request(1) is True
    assert github.get_pull_request(1)["state"] == "merged"
    assert github.delete_branch("marshal/19-2") is True
    assert github.get_branch("marshal/19-2") is None


def test_auth_http_time_frozen_clock(clock: FrozenClock) -> None:
    start = clock.now()
    clock.advance_heartbeat()
    assert (clock.now() - start).total_seconds() == clock.heartbeat_interval
    assert clock.is_idle(59) is False
    assert clock.is_idle(60) is True
