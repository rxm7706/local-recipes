"""Story 84.4 — GitHub-only marker skips unlinked reconcile when flagged on."""

from __future__ import annotations

import logging

import pytest
from test_sync_reconcile_propagation import CONFIG, FakeTransport, ScheduleFakeTransport

from pyforge.steward.sync import (
    SYNC_GITHUB_ONLY_MARKER_FLAG,
    GitHubOnlyMarker,
    SyncConfig,
    reconcile,
    reconcile_schedule_batch,
)


def _config_with_marker(marker: GitHubOnlyMarker) -> SyncConfig:
    return SyncConfig(**{**CONFIG.__dict__, "github_only_marker": marker})


@pytest.fixture
def flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.sync._github_only_marker_feature_enabled", lambda: True)


@pytest.fixture
def flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pyforge.steward.sync._github_only_marker_feature_enabled", lambda: False)


def test_flag_on_labeled_unlinked_item_is_skipped_ok(flag_on, caplog):
    caplog.set_level(logging.INFO)
    transport = FakeTransport(
        github_fields={"gh_status": "To Do"},
        github_content={
            "number": 1,
            "repository": {"owner": {"login": "o"}, "name": "r"},
            "assignees": {"nodes": []},
            "labels": {"nodes": [{"name": "github-only"}]},
        },
    )
    config = _config_with_marker(GitHubOnlyMarker(label="github-only"))

    result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)

    assert result.ok is True
    assert "skipped github-only" in result.summary
    assert transport.write_calls() == []
    assert any("skipped github-only" in record.message for record in caplog.records)


def test_unlinked_without_marker_still_fails_loud(flag_on):
    transport = FakeTransport(github_fields={"gh_status": "To Do"})
    config = _config_with_marker(GitHubOnlyMarker(label="github-only"))

    result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)

    assert result.ok is False
    assert "unlinked" in result.summary


def test_flag_off_marker_does_not_skip(flag_off):
    transport = FakeTransport(
        github_fields={"gh_status": "To Do"},
        github_content={
            "number": 1,
            "repository": {"owner": {"login": "o"}, "name": "r"},
            "assignees": {"nodes": []},
            "labels": {"nodes": [{"name": "github-only"}]},
        },
    )
    config = _config_with_marker(GitHubOnlyMarker(label="github-only"))

    result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)

    assert result.ok is False
    assert "unlinked" in result.summary


def test_no_marker_in_config_behaves_as_before(flag_on):
    transport = FakeTransport(
        github_fields={"gh_status": "To Do"},
        github_content={
            "number": 1,
            "repository": {"owner": {"login": "o"}, "name": "r"},
            "assignees": {"nodes": []},
            "labels": {"nodes": [{"name": "github-only"}]},
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is False
    assert "unlinked" in result.summary


def test_field_value_marker_skips_when_flag_on(flag_on):
    transport = FakeTransport(
        github_fields={"gh_status": "To Do", "PVTF_scope": "GitHub only"},
    )
    config = _config_with_marker(GitHubOnlyMarker(field_id="PVTF_scope", field_value="GitHub only"))

    result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)

    assert result.ok is True
    assert "skipped github-only" in result.summary


def test_schedule_batch_skips_marked_item_and_syncs_linked(flag_on):
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {"fields": {"gh_status": "To Do", "PVTF_scope": "GitHub only"}},
            "ITEM_2": {
                "fields": {
                    "gh_link": "PROJ-1",
                    "gh_status": "In Progress",
                    "gh_baseline": '{"status": "In Progress"}',
                }
            },
        },
        jira_issues={
            "PROJ-1": {
                "fields": {
                    "jira_link": "ITEM_2",
                    "jira_baseline": '{"status": "In Progress"}',
                    "status": {"name": "In Progress"},
                },
                "transitions": [],
            }
        },
    )
    config = _config_with_marker(GitHubOnlyMarker(field_id="PVTF_scope", field_value="GitHub only"))

    result = reconcile_schedule_batch(config=config, transport=transport)

    assert result.ok is True
    by_id = {entry["github_item_id"]: entry for entry in result.details["candidates"]}
    assert by_id["ITEM_1"]["ok"] is True
    assert "skipped github-only" in by_id["ITEM_1"]["summary"]
    assert by_id["ITEM_2"]["ok"] is True


def test_tracked_flags_tree_carries_sync_github_only_marker_off_by_default():
    import json
    from pathlib import Path

    tree = Path(__file__).resolve().parents[5] / "platform" / "config" / "flags.json"
    entry = json.loads(tree.read_text(encoding="utf-8"))["flags"][SYNC_GITHUB_ONLY_MARKER_FLAG]
    assert entry["defaultVariant"] == "off"
    assert entry["metadata"]["story"] == "84-4-sync-skips-a-board-item-marked-github-only"
