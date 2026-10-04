"""Story 84.4 — GitHub-only marker skips unlinked reconcile when flagged on."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from pyforge.core.flags import read_boolean as _read_boolean_flag
from test_sync_reconcile_propagation import CONFIG, FakeTransport, ScheduleFakeTransport

from pyforge.steward.sync import (
    SYNC_GITHUB_ONLY_MARKER_FLAG,
    GitHubOnlyMarker,
    SyncConfig,
    reconcile,
    reconcile_schedule_batch,
)

_FLAG_FIXTURE_METADATA = {
    "owner": "steward",
    "story": "84-5-github-only-marker-tests",
    "created": "2026-10-03",
    "on_everywhere": "",
    "cleanup_by": "",
}


def _write_flagd_tree(
    tmp_path: Path,
    variant: str,
    name: str,
    *,
    include_marker_flag: bool = True,
    overlays: dict[str, dict[str, str]] | None = None,
    broken_overlay: bool = False,
) -> Path:
    flags: dict = {}
    if include_marker_flag:
        flags[SYNC_GITHUB_ONLY_MARKER_FLAG] = {
            "state": "ENABLED",
            "variants": {"on": True, "off": False},
            "defaultVariant": variant,
            "metadata": dict(_FLAG_FIXTURE_METADATA),
        }
    path = tmp_path / name
    path.write_text(json.dumps({"flags": flags}), encoding="utf-8")
    overlay_path = path.with_name("flag-overlays.json")
    if broken_overlay:
        overlay_path.write_text("{", encoding="utf-8")
    elif overlays is not None:
        overlay_path.write_text(json.dumps(overlays), encoding="utf-8")
    return path


def _config_with_marker(marker: GitHubOnlyMarker) -> SyncConfig:
    return SyncConfig(**{**CONFIG.__dict__, "github_only_marker": marker})


@pytest.fixture
def flag_on(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_write_flagd_tree(tmp_path, "on", "flags-on.json")))


@pytest.fixture
def flag_off(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_write_flagd_tree(tmp_path, "off", "flags-off.json")))


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


def test_near_miss_text_field_values_do_not_skip(flag_on):
    config = _config_with_marker(GitHubOnlyMarker(field_id="PVTF_scope", field_value="GitHub only"))
    for value in ("github only", "GitHub only (temp)", "not GitHub only"):
        transport = FakeTransport(github_fields={"gh_status": "To Do", "PVTF_scope": value})
        result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)
        assert result.ok is False, value
        assert "unlinked" in result.summary


def test_near_miss_single_select_field_values_do_not_skip(flag_on):
    config = _config_with_marker(GitHubOnlyMarker(field_id="PVTF_scope", field_value="GitHub only"))
    for value in ("github only", "GitHub only (temp)", "not GitHub only"):
        transport = FakeTransport(
            github_fields={"gh_status": "To Do"},
            github_single_select_fields={"PVTF_scope": value},
        )
        result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)
        assert result.ok is False, value
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


def _schedule_transport_marked_and_linked():
    return ScheduleFakeTransport(
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


def test_schedule_batch_completes_when_overlay_unreadable(caplog, monkeypatch, tmp_path):
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    tree = _write_flagd_tree(tmp_path, "on", "flags-on.json", broken_overlay=True)
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    caplog.set_level(logging.WARNING)
    config = _config_with_marker(GitHubOnlyMarker(field_id="PVTF_scope", field_value="GitHub only"))

    result = reconcile_schedule_batch(config=config, transport=_schedule_transport_marked_and_linked())

    by_id = {entry["github_item_id"]: entry for entry in result.details["candidates"]}
    assert by_id["ITEM_1"]["ok"] is False
    assert "unlinked" in by_id["ITEM_1"]["summary"]
    assert by_id["ITEM_2"]["ok"] is True
    assert len(result.details["candidates"]) == 2
    assert any(
        SYNC_GITHUB_ONLY_MARKER_FLAG in record.message and record.levelno == logging.WARNING
        for record in caplog.records
    )


def test_schedule_batch_production_env_flag_off_marked_item_unlinked(monkeypatch, tmp_path, caplog):
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    tree = _write_flagd_tree(
        tmp_path,
        "on",
        "flags-on.json",
        overlays={
            "dev": {SYNC_GITHUB_ONLY_MARKER_FLAG: "on"},
            "staging": {SYNC_GITHUB_ONLY_MARKER_FLAG: "on"},
            "production": {SYNC_GITHUB_ONLY_MARKER_FLAG: "off"},
        },
    )
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "production")
    caplog.set_level(logging.WARNING)
    config = _config_with_marker(GitHubOnlyMarker(field_id="PVTF_scope", field_value="GitHub only"))

    result = reconcile_schedule_batch(config=config, transport=_schedule_transport_marked_and_linked())

    by_id = {entry["github_item_id"]: entry for entry in result.details["candidates"]}
    assert by_id["ITEM_1"]["ok"] is False
    assert "unlinked" in by_id["ITEM_1"]["summary"]
    assert by_id["ITEM_2"]["ok"] is True
    assert not any(
        SYNC_GITHUB_ONLY_MARKER_FLAG in record.message and record.levelno >= logging.WARNING
        for record in caplog.records
    )


def test_schedule_batch_prod_alias_env_flag_off_marked_item_unlinked(monkeypatch, tmp_path, caplog):
    """PYFORGE_ENVIRONMENT=prod is unknown; flag gate warns and treats marker off."""
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    tree = _write_flagd_tree(tmp_path, "on", "flags-on.json")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "prod")
    caplog.set_level(logging.WARNING)
    config = _config_with_marker(GitHubOnlyMarker(label="github-only"))
    transport = ScheduleFakeTransport(
        items={
            "ITEM_1": {
                "fields": {"gh_status": "To Do"},
                "content": {
                    "number": 1,
                    "repository": {"owner": {"login": "o"}, "name": "r"},
                    "assignees": {"nodes": []},
                    "labels": {"nodes": [{"name": "github-only"}]},
                },
            },
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

    result = reconcile_schedule_batch(config=config, transport=transport)

    assert len(result.details["candidates"]) == 2
    by_id = {entry["github_item_id"]: entry for entry in result.details["candidates"]}
    assert by_id["ITEM_1"]["ok"] is False
    assert "unlinked" in by_id["ITEM_1"]["summary"]
    assert by_id["ITEM_2"]["ok"] is True
    assert any(
        SYNC_GITHUB_ONLY_MARKER_FLAG in record.message and record.levelno == logging.WARNING
        for record in caplog.records
    )


def test_schedule_batch_unknown_env_without_marker_never_reads_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "not-a-real-env")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(_write_flagd_tree(tmp_path, "on", "flags-on.json")))
    flag_reads: list[str] = []

    def _track_read(key: str, *args, **kwargs):
        flag_reads.append(key)
        return _read_boolean_flag(key, *args, **kwargs)

    monkeypatch.setattr("pyforge.steward.sync.read_boolean", _track_read)

    result = reconcile_schedule_batch(
        config=CONFIG,
        transport=ScheduleFakeTransport(items={"ITEM_1": {"fields": {"gh_status": "To Do"}}}),
    )

    assert flag_reads == []
    assert result.details["candidates"][0]["ok"] is False
    assert "unlinked" in result.details["candidates"][0]["summary"]


def test_marked_unlinked_fails_when_flag_tree_lacks_marker_key(monkeypatch, tmp_path):
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH",
        str(_write_flagd_tree(tmp_path, "on", "flags-on.json", include_marker_flag=False)),
    )
    config = _config_with_marker(GitHubOnlyMarker(label="github-only"))
    transport = FakeTransport(
        github_fields={"gh_status": "To Do"},
        github_content={
            "number": 1,
            "repository": {"owner": {"login": "o"}, "name": "r"},
            "assignees": {"nodes": []},
            "labels": {"nodes": [{"name": "github-only"}]},
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)

    assert result.ok is False
    assert "unlinked" in result.summary


def test_marked_unlinked_fails_when_no_flag_tree(monkeypatch, tmp_path):
    """No discoverable flag tree: read_boolean falls back to default False (flag off)."""
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    config = _config_with_marker(GitHubOnlyMarker(label="github-only"))
    transport = FakeTransport(
        github_fields={"gh_status": "To Do"},
        github_content={
            "number": 1,
            "repository": {"owner": {"login": "o"}, "name": "r"},
            "assignees": {"nodes": []},
            "labels": {"nodes": [{"name": "github-only"}]},
        },
    )

    result = reconcile(github_item_id="ITEM_1", config=config, transport=transport)

    assert result.ok is False
    assert "unlinked" in result.summary


def test_tracked_flags_tree_carries_sync_github_only_marker_off_by_default():
    tree = Path(__file__).resolve().parents[5] / "platform" / "config" / "flags.json"
    entry = json.loads(tree.read_text(encoding="utf-8"))["flags"][SYNC_GITHUB_ONLY_MARKER_FLAG]
    assert entry["defaultVariant"] == "off"
    assert entry["metadata"]["story"] == "84-4-sync-skips-a-board-item-marked-github-only"


def test_the_marker_flag_key_is_the_shipped_key():
    """The constant the sync gate reads is the key flags.json ships (and the flag gate looks for)."""
    assert SYNC_GITHUB_ONLY_MARKER_FLAG == "pyforge.steward.sync_github_only_marker"
