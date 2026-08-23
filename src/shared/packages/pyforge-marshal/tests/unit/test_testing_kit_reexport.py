"""Marshal re-exports the shared testing kit (Story 19.2 seed-station proof)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pyforge.testing_kit as kit
from pyforge.testing_kit import CliRunner, MockGitHubAPI

_SUPPORT = Path(__file__).resolve().parents[1] / "support" / "testing_kit.py"


def test_marshal_imports_cli_runner_from_shared_kit() -> None:
    runner = CliRunner("marshal-reexport")
    assert runner.run() is True
    assert runner.get_result()["story_id"] == "marshal-reexport"


def test_marshal_imports_auth_http_from_shared_kit() -> None:
    api = MockGitHubAPI()
    pr = api.create_pull_request("reexport", head="local")
    assert pr["number"] == 1


def test_marshal_support_module_reexports_from_shared_kit() -> None:
    """Load the station-local shim and prove it re-exports kit objects (not a copy)."""
    module_name = "marshal_tests_support_testing_kit"
    spec = importlib.util.spec_from_file_location(module_name, _SUPPORT)
    assert spec is not None and spec.loader is not None
    support = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = support
    spec.loader.exec_module(support)

    assert support.CliRunner is kit.CliRunner
    assert support.MockGitHubAPI is kit.MockGitHubAPI
    assert support.MockWorktree is kit.MockWorktree
    assert support.MockSupervisor is kit.MockSupervisor
    assert support.FrozenClock is kit.FrozenClock
    assert support.record_factory is kit.record_factory

    runner = support.CliRunner("via-shim")
    assert runner.run() is True
    assert runner.get_result()["story_id"] == "via-shim"
