"""Story 84.4 — GitHub-only marker skips unlinked reconcile when flagged on."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from test_sync_reconcile_propagation import CONFIG, FakeTransport, ScheduleFakeTransport

from pyforge.steward.sync import (
    SYNC_GITHUB_ONLY_MARKER_FLAG,
    GitHubOnlyMarker,
    SyncConfig,
    reconcile,
    reconcile_schedule_batch,
)


def _write_flag_tree(tmp_path: Path, variant: str, name: str) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(
            {
                "flags": {
                    SYNC_GITHUB_ONLY_MARKER_FLAG: {
                        "state": "ENABLED",
                        "variants": {"on": True, "off": False},
                        "defaultVariant": variant,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def _config_with_marker(marker: GitHubOnlyMarker) -> SyncConfig:
    return SyncConfig(**{**CONFIG.__dict__, "github_only_marker": marker})


@pytest.fixture
def flag_on(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_write_flag_tree(tmp_path, "on", "flags-on.json")))


@pytest.fixture
def flag_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_write_flag_tree(tmp_path, "off", "flags-off.json")))


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


def test_near_miss_labels_do_not_skip(flag_on):
    config = _config_with_marker(GitHubOnlyMarker(label="github-only"))
    for label in ("not-github-only", "GitHub-Only", "GitHub only (temp)"):
        transport = FakeTransport(
            github_fields={"gh_status": "To Do"},
            github_content={
                "number": 1,
                "repository": {"owner": {"login": "o"}, "name": "r"},
                "assignees": {"nodes": []},
                "labels": {"nodes": [{"name": label}]},
            },
        )
        result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)
        assert result.ok is False, label
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


def test_single_select_marker_skips_when_flag_on(flag_on):
    transport = FakeTransport(
        github_fields={"gh_status": "To Do"},
        github_single_select_fields={"PVTF_scope": "GitHub only"},
    )
    config = _config_with_marker(GitHubOnlyMarker(field_id="PVTF_scope", field_value="GitHub only"))

    result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)

    assert result.ok is True
    assert "skipped github-only" in result.summary


def test_single_select_on_status_field_does_not_change_reconcile_status_when_flag_off(flag_off):
    """M2: single-select on the status field id must not override TEXT `gh.status`."""
    transport = FakeTransport(
        github_fields={
            "gh_link": "PROJ-1",
            "gh_status": "To Do",
            "gh_baseline": '{"status": "To Do"}',
        },
        github_single_select_fields={CONFIG.github_status_field_id: "In Progress"},
        jira_fields={
            "jira_link": "ITEM_1",
            "jira_baseline": '{"status": "To Do"}',
            "status": {"name": "To Do"},
        },
        jira_transitions=[],
    )

    result = reconcile(github_item_id="ITEM_1", config=CONFIG, transport=transport)

    assert result.ok is True
    assert "no_op" in result.summary


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
    assert "1 skip (github-only): ITEM_1" in result.summary
    by_id = {entry["github_item_id"]: entry for entry in result.details["candidates"]}
    assert by_id["ITEM_1"]["ok"] is True
    assert "skipped github-only" in by_id["ITEM_1"]["summary"]
    assert by_id["ITEM_2"]["ok"] is True


def test_schedule_batch_completes_when_flag_unreadable(monkeypatch, tmp_path, flag_on):
    broken = tmp_path / "broken-overlay.json"
    broken.write_text("{", encoding="utf-8")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_write_flag_tree(tmp_path, "on", "flags-on.json")))
    monkeypatch.setenv("PYFORGE_FLAG_OVERLAYS_PATH", str(broken))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")

    config = _config_with_marker(GitHubOnlyMarker(label="github-only"))

    result = reconcile_schedule_batch(
        config=config,
        transport=ScheduleFakeTransport(
            items={"ITEM_1": {"fields": {"gh_status": "To Do"}}},
        ),
    )

    assert "failed" in result.summary or "unlinked" in result.summary
    assert result.details["candidates"][0]["ok"] is False


def test_tracked_flags_tree_carries_sync_github_only_marker_off_by_default():
    tree = Path(__file__).resolve().parents[5] / "platform" / "config" / "flags.json"
    entry = json.loads(tree.read_text(encoding="utf-8"))["flags"][SYNC_GITHUB_ONLY_MARKER_FLAG]
    assert entry["defaultVariant"] == "off"
    assert entry["metadata"]["story"] == "84-4-sync-skips-a-board-item-marked-github-only"
