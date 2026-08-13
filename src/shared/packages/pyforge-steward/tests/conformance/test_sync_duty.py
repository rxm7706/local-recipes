"""`SyncDuty`/`steward sync` -- Epic 8, Story 8.1. `reconcile`/`load_config`
have their own dedicated test files; this one exercises `SyncDuty.run()`
itself: the no-verb degrade (AD-7), a config-load failure surfacing as a
named `DutyResult`, and CLI-arg threading through `main()` end-to-end --
none of which the other two files' direct-function-call tests cover.
"""

from __future__ import annotations

import json

import pytest
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.sync import TransportResponse

_VALID_CONFIG = """\
github:
  project_id: PVT_abc123
  status_field_id: gh_status
  link_field_id: gh_link
  baseline_field_id: gh_baseline
jira:
  base_url: https://example.atlassian.net
  project_key: PROJ
  link_field_id: jira_link
  baseline_field_id: jira_baseline
"""


def test_sync_with_no_verb_reports_available_verbs_via_cli(capsys):
    rc = main(["sync"])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "reconcile" in out


def test_sync_reconcile_with_missing_config_is_a_named_failure(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.yaml"

    rc = main(["sync", "reconcile", "--github-item", "ITEM_1", "--config", str(missing)])

    assert rc == EXIT_FAILED
    err = capsys.readouterr().err
    assert "sync config not found" in err


def test_sync_reconcile_dry_run_via_cli_threads_args_through_with_no_writes(tmp_path, monkeypatch, capsys):
    """Proves `--github-item`/`--config`/`--dry-run` actually reach
    `reconcile` through `SyncDuty.run()`'s dispatch, not just that the
    lower-level functions behave correctly in isolation."""
    config_path = tmp_path / "sync-config.yaml"
    config_path.write_text(_VALID_CONFIG, encoding="utf-8")

    write_calls: list[str] = []

    def fake_transport(request):
        method = request.get_method()
        url = request.full_url
        if url == "https://api.github.com/graphql":
            body = json.loads(request.data)
            if "fieldId" in body["variables"]:
                write_calls.append(url)
            node = {
                "id": "ITEM_1",
                "fieldValues": {
                    "nodes": [
                        {"text": "PROJ-1", "field": {"id": "gh_link"}},
                        {"text": "In Progress", "field": {"id": "gh_status"}},
                        {"text": '{"status": "To Do"}', "field": {"id": "gh_baseline"}},
                    ]
                },
            }
            return TransportResponse(status=200, body=json.dumps({"data": {"node": node}}).encode())
        if method in ("POST", "PUT"):
            write_calls.append(url)
        payload = {
            "fields": {
                "status": {"name": "To Do"},
                "jira_link": "ITEM_1",
                "jira_baseline": '{"status": "To Do"}',
            }
        }
        return TransportResponse(status=200, body=json.dumps(payload).encode())

    monkeypatch.setattr("pyforge.steward.sync._default_transport", fake_transport)

    rc = main(
        ["sync", "reconcile", "--github-item", "ITEM_1", "--config", str(config_path), "--dry-run"]
    )

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "push_to_jira" in out
    assert write_calls == []  # --dry-run: computed the decision, made no write calls


def test_sync_reconcile_schedule_via_cli_dispatches_to_the_batch_reconciler(tmp_path, monkeypatch, capsys):
    """Story 8.4 AC1: `--schedule` reaches `reconcile_schedule_batch` (not
    the single-pair `reconcile`) through `SyncDuty.run()`'s dispatch, with
    no `--github-item`/`--jira-issue` given. A board with zero linked items
    is sufficient to prove the CLI flag reaches the batch path --
    `reconcile_schedule_batch`'s own direct-call tests
    (`test_sync_reconcile_propagation.py`) cover multi-candidate dispatch in
    depth."""
    config_path = tmp_path / "sync-config.yaml"
    config_path.write_text(_VALID_CONFIG, encoding="utf-8")

    def fake_transport(request):
        payload = {
            "data": {
                "node": {
                    "items": {
                        "nodes": [],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        }
        return TransportResponse(status=200, body=json.dumps(payload).encode())

    monkeypatch.setattr("pyforge.steward.sync._default_transport", fake_transport)

    rc = main(["sync", "reconcile", "--schedule", "--config", str(config_path)])

    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert "0 candidates" in out
