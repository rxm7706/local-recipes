"""``marshal land``'s ledger promotion, read against this checkout's scripts (Story 4.8).

Story 116.4 (spec-pyforge-marshal:CAP-305): the tree-read guard runs every package-half test off the tree (a working
directory outside the repository, ``cli/config.py`` anchored in a bare checkout), and these tests fail there:
each promotes or rolls the sprint ledger through ``scripts/promote_sprint_status.py``, which ``cli/land.py``
loads from the checkout ``checkout_root()`` names.
They moved here, marked ``live_tree``; each fails, never skips, when what it reads is absent. Every other
test stays in ``test_land.py``, and this module imports the helpers both use from it by name.
"""

from __future__ import annotations

import json

import pytest
from test_land import (
    _BMADLOOP_WAVE_SUBJECT,
    _args,
    _FakeForge,
    _FakeVcs,
    _patch_repo,
    _payload,
    _published_ledger_83_21,
    _rule_policy,
    _TimingOutPublishVcs,
    _write_project_policy,
    _write_sprint_ledger,
    _write_tier3_feed,
)

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.cli import deploy as deploy_module
from pyforge.marshal.cli import land as land_module
from pyforge.marshal.core.identity import StoryKey

pytestmark = pytest.mark.live_tree


@pytest.fixture(autouse=True)
def _no_active_project_env(monkeypatch):
    """``test_land.py``'s autouse fixture, declared here as well: an autouse fixture does not follow an import."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)


def test_sprint_ledger_promoted_on_merge(tmp_path, capsys, monkeypatch):
    policy_path = _write_project_policy(tmp_path, _rule_policy(required_check=None))
    _patch_repo(monkeypatch, tmp_path, policy_path=policy_path)
    ledger_path = _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        changed_paths=("docs/notes.md",),
    )
    forge = _FakeForge(existing=None)

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=forge)

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["merged"] is True
    assert "4-4-batch" in payload["data"]["sprint_ledger_promoted"]
    assert "MRS-LAND-011" not in [f["code"] for f in payload["findings"]]
    assert "4-4-batch: done" in ledger_path.read_text(encoding="utf-8")
    assert any("sprint-status ledger" in msg for _r, _p, msg in vcs.commit_paths_calls)


def _journal_entries(deploy_run) -> list[dict]:
    text = (deploy_run.run_dir / "journal.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line]


def test_a_failed_ledger_publish_pairs_its_intent_with_an_outcome_ok_false(tmp_path):
    """Story 68.1 AC 4 (AD-6): INTENT, then OUTCOME `ok: false` naming the error, then MRS-LAND-011 and
    `()` -- never an INTENT left open while the run reports success."""
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    fs = LocalFs()
    vcs = _TimingOutPublishVcs()
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-1")
    findings: list = []

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(4, 4)], deploy_run, findings, base="main"
    )

    assert promoted == ()
    ledger_entries = [e for e in _journal_entries(deploy_run) if e["kind"] == "land-sprint-ledger-promotion"]
    assert [e["phase"] for e in ledger_entries] == ["intent", "outcome"]
    intent, outcome = ledger_entries
    assert outcome["intent_id"] == intent["id"]
    assert outcome["payload"]["ok"] is False
    assert "timed out after 120.0s" in outcome["payload"]["error"]
    assert outcome["payload"]["promoted"] == ["4-4-batch"]
    [finding] = [f for f in findings if f.code == "MRS-LAND-011"]
    assert finding.severity.name == "WARN"
    assert "timed out after 120.0s" in finding.message


def test_a_landed_ledger_publish_journals_an_outcome_ok_true(tmp_path):
    _write_sprint_ledger(tmp_path, "acme", {"4-4-batch": "in-progress"})
    fs = LocalFs()
    vcs = _FakeVcs()
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-1")
    findings: list = []

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(4, 4)], deploy_run, findings, base="main"
    )

    assert promoted == ("4-4-batch",)
    outcomes = [
        e
        for e in _journal_entries(deploy_run)
        if e["kind"] == "land-sprint-ledger-promotion" and e["phase"] == "outcome"
    ]
    assert [e["payload"]["ok"] for e in outcomes] == [True]
    assert not [f for f in findings if f.code == "MRS-LAND-011"]


def test_a_feed_only_ledger_sync_names_the_wave_keys_in_its_preflight_reason(tmp_path):
    """Story 68.1: when the Tier-3 feed advances rows but every wave key is already `done`, nothing was
    `promoted` -- the reason falls back to the wave's own story keys, so the hook's journal still names one."""
    ledger_path = _write_sprint_ledger(tmp_path, "acme", {"epic-4": "in-progress", "4-4-batch": "done"})
    feed_path = tmp_path / "_bmad-output" / "projects" / "acme" / "implementation-artifacts" / "sprint-status.yaml"
    feed_path.parent.mkdir(parents=True)
    feed_path.write_text(
        "development_status:\n  epic-4: in-progress\n  4-4-batch: done\n  4-5-follow-up: backlog\n",
        encoding="utf-8",
    )
    fs = LocalFs()
    vcs = _FakeVcs()
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-1")

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(4, 4)], deploy_run, [], base="main"
    )

    assert promoted == ("acme",)
    assert "4-5-follow-up" in ledger_path.read_text(encoding="utf-8")
    [reason] = vcs.isolated_promote_reasons
    assert reason is not None
    assert "story 4.4" in reason


def test_land_already_landed_path_rolls_the_last_open_story_s_epic_to_done(tmp_path, capsys, monkeypatch):
    _patch_repo(monkeypatch, tmp_path)
    _write_sprint_ledger(tmp_path, "acme", {"epic-4": "in-progress", "4-4-batch": "review"})
    vcs = _FakeVcs(
        existing_branches=frozenset({"loop/acme"}),
        wave_subjects=(_BMADLOOP_WAVE_SUBJECT,),
        base_subjects=(_BMADLOOP_WAVE_SUBJECT,),
    )

    exit_code = land_module.run_land(_args(), vcs=vcs, fs=LocalFs(), forge=_FakeForge(existing=None))

    payload = _payload(capsys)
    assert exit_code == 0
    assert payload["data"]["already_landed"] is True
    statuses = land_module._parse_sprint_ledger_statuses(_published_ledger_83_21(vcs))
    assert statuses == {"4-4-batch": "done", "epic-4": "done"}


def test_promote_feed_sync_guard_judges_origin_main_not_stale_local_ledger(tmp_path):
    """When the primary ledger lags origin/main, a feed that drops a remote-only backlog key is refused."""
    _write_sprint_ledger(
        tmp_path,
        "acme",
        {"12-1-a": "done"},
    )
    remote_twin = "development_status:\n  12-1-a: done\n  12-2-b: backlog\n"
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  12-1-a: done\n")
    fs = LocalFs()
    vcs = _FakeVcs(remote_ledger_text=remote_twin)
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-83-22")
    findings: list = []

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(12, 1)], deploy_run, findings, base="main"
    )

    assert promoted == ()
    assert not vcs.isolated_promote_calls
    refusal = next(f for f in findings if f.code == "MRS-LAND-011" and "feed would drop" in f.message)
    assert "12-2-b" in refusal.message


def test_promote_feed_sync_guard_mutation_local_ledger_parser_would_sync_the_drop(tmp_path, monkeypatch):
    remote_twin = "development_status:\n  12-1-a: done\n  12-2-b: backlog\n"
    local_text = "development_status:\n  12-1-a: done\n"
    _write_sprint_ledger(tmp_path, "acme", {"12-1-a": "done"})
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  12-1-a: done\n")
    fs = LocalFs()
    vcs = _FakeVcs(remote_ledger_text=remote_twin)
    deploy_run = deploy_module._DeployRun(fs, tmp_path, "acme", "writer-83-22-mut")
    findings: list = []

    monkeypatch.setattr(
        land_module,
        "_parse_sync_sprint_status_text",
        lambda _fresh: land_module._parse_sprint_ledger_statuses(local_text),
    )

    promoted = land_module._promote_sprint_ledger(
        fs, vcs, tmp_path, "acme", [StoryKey(12, 1)], deploy_run, findings, base="main"
    )

    assert promoted == ("acme",)
    assert vcs.isolated_promote_calls
    published = vcs.isolated_promote_calls[0][3][0][1]
    assert "12-2-b" not in published


def test_promote_feed_sync_refuses_un_finish_against_origin_main(tmp_path):
    remote_twin = "development_status:\n  12-1-a: done\n"
    _write_sprint_ledger(tmp_path, "acme", {"12-1-a": "backlog"})
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  12-1-a: backlog\n")
    fs = LocalFs()
    vcs = _FakeVcs(remote_ledger_text=remote_twin)
    findings: list = []

    land_module._promote_sprint_ledger(
        fs,
        vcs,
        tmp_path,
        "acme",
        [StoryKey(12, 1)],
        deploy_module._DeployRun(fs, tmp_path, "acme", "w"),
        findings,
        base="main",
    )

    refusal = next(f for f in findings if "un-finish" in f.message)
    assert "12-1-a" in refusal.message
    assert not vcs.isolated_promote_calls


def test_roll_up_epic_rows_reads_rows_below_a_column_zero_comment(tmp_path):
    text = "development_status:\n# wave note\n  epic-4: in-progress\n  4-4-batch: done\n  4-5-other: done\n"
    promote_mod = land_module._load_promote_sprint_status_module()
    rollup = land_module._sync_epic_rollup(promote_mod)
    assert rollup is not None
    rolled = land_module._roll_up_epic_rows(text, rollup)
    statuses = land_module._parse_sync_sprint_status_text(rolled)
    assert statuses["epic-4"] == "done"


def test_roll_up_epic_rows_mutation_land_parser_misses_comment_below_rows():
    text = "development_status:\n# wave note\n  epic-4: in-progress\n  4-4-batch: done\n  4-5-other: done\n"
    promote_mod = land_module._load_promote_sprint_status_module()
    rollup = land_module._sync_epic_rollup(promote_mod)
    assert rollup is not None
    statuses = {
        key: value.partition("#")[0].strip() for key, value in land_module._parse_sprint_ledger_statuses(text).items()
    }
    rolled = rollup(dict(statuses))
    assert rolled.get("epic-4") != "done"
