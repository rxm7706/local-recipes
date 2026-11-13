"""``cli/deploy.py``'s completion reconcile, read against this checkout's scripts.

Story 116.4 (spec-pyforge-marshal:CAP-305): the tree-read guard runs every package-half test off the tree (a working
directory outside the repository, ``cli/config.py`` anchored in a bare checkout), and these tests fail there:
each advances the sprint ledger through ``scripts/promote_sprint_status.py``'s ``apply_epic_rollups``, which
``cli/deploy.py`` loads from the checkout ``checkout_root()`` names.
They moved here, marked ``live_tree``; each fails, never skips, when what it reads is absent. Every other
test stays in ``test_deploy.py``, and this module imports the helpers both use from it by name.
"""

from __future__ import annotations

import json

import pytest
from test_deploy import (
    _VALID_SPEC,
    _args,
    _FakeReconcileHarness,
    _FakeVcs,
    _ledger_text,
    _not_loop_native_subject,
    _tracked_path,
    _write_ledger,
    _write_tier3_feed,
    _write_tier3_spec,
    _write_tracked_spec,
)

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.cli import deploy as deploy_module

pytestmark = pytest.mark.live_tree


@pytest.fixture(autouse=True)
def _no_active_project_env(monkeypatch):
    """``test_deploy.py``'s autouse fixture, declared here as well: an autouse fixture does not follow an import."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)


def test_reconcile_completions_advances_and_promotes_a_not_loop_native_story(tmp_path, capsys, monkeypatch):
    """The headline scenario (I/O matrix row 1): a backlog story merged via
    a plain GitHub PR, with a valid, durable Tier-3 spec -- advances the
    ledger AND promotes the spec, in two dedicated commits, and closes
    the Tier-3 feed divergence for the same key (a pre-existing feed is
    set up here so this happy path stays finding-free; the feed-missing
    MRS-DEPLOY-027 case has its own dedicated test below)."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    feed_path = _write_tier3_feed(tmp_path, "acme", "development_status:\n  5-9-title: backlog\n")
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["advanced"] == ["5.9"]
    assert payload["data"]["promoted"] == ["5.9"]
    assert payload["data"]["missing_from_ledger"] == []
    assert payload["findings"] == []
    assert payload["verdict"] == "clean"
    assert exit_code == 0

    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    dest = _tracked_path(tmp_path, "acme", "5-9-title")
    assert dest.read_text(encoding="utf-8") == _VALID_SPEC
    # The Tier-3 feed's own divergence was also closed, since it existed.
    assert "5-9-title: done" in feed_path.read_text(encoding="utf-8")

    # Two dedicated commits, one per concern (AD-29's "only promotion
    # paths" precedent, applied symmetrically to the ledger commit too).
    # The Tier-3 feed repair-write is never git-committed (Tier-3 is
    # gitignored).
    assert len(vcs.commit_calls) == 2
    ledger_commit = next(c for c in vcs.commit_calls if c[0] == (ledger_path,))
    assert "advance" in ledger_commit[1]
    spec_commit = next(c for c in vcs.commit_calls if c[0] == (dest,))
    assert "promote" in spec_commit[1]


def test_reconcile_completions_rolls_epic_to_done_when_last_open_story_advances(tmp_path, capsys, monkeypatch):
    """Story 83.22: reconcile-completions applies the sync's epic roll-up after advancing story rows."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("epic-5", "in-progress"), ("5-9-title", "backlog")))
    _write_tier3_feed(
        tmp_path,
        "acme",
        "development_status:\n  epic-5: in-progress\n  5-9-title: backlog\n",
    )
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    assert exit_code == 0
    ledger_text = ledger_path.read_text(encoding="utf-8")
    assert "5-9-title: done" in ledger_text
    assert "epic-5: done" in ledger_text


def test_reconcile_completions_already_promoted_spec_still_advances_the_ledger(tmp_path, capsys, monkeypatch):
    """A key corroborated via `scan.already_promoted` (a valid,
    git-committed tracked copy already exists in the archive --
    `_write_tracked_spec`) rather than `scan.plan.to_promote`, with the
    ledger row still `backlog`, AND with real merge evidence in history.
    Corroboration requires a durable, valid spec (`to_promote UNION
    already_promoted`) AND real merge evidence, so the ledger still
    advances to `done`; there is nothing left to promote for this key."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    _write_tracked_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    _write_tier3_feed(tmp_path, "acme", "development_status:\n  5-9-title: backlog\n")
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert payload["data"]["missing_from_ledger"] == []
    assert payload["data"]["advanced"] == ["5.9"]
    assert payload["data"]["promoted"] == []
    assert exit_code == 0
    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    # Exactly one commit -- the ledger's own; nothing left to promote.
    assert len(vcs.commit_calls) == 1
    assert vcs.commit_calls[0][0] == (ledger_path,)


def test_reconcile_completions_closes_the_tier3_feed_divergence_after_a_successful_advance(
    tmp_path, capsys, monkeypatch
):
    """Spec Change Log, 2026-08-12, item 2: after a successful ledger
    commit, the Tier-3 feed for the project is closed for exactly the
    advanced keys, reusing `scripts/promote_sprint_status.py`'s own
    repair-feed logic -- no separate `sprint-ledger-sync --repair-feed`
    invocation required by the operator."""
    monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)
    _write_tier3_spec(tmp_path, "acme", "5-9-title", _VALID_SPEC)
    ledger_path = _write_ledger(tmp_path, "acme", _ledger_text(("5-9-title", "backlog")))
    feed_path = _write_tier3_feed(tmp_path, "acme", "development_status:\n  5-9-title: backlog\n")
    vcs = _FakeVcs(main_subjects=(_not_loop_native_subject("5-9-title"),))
    harness = _FakeReconcileHarness(ledger_statuses=(("5-9-title", "backlog"),))

    exit_code = deploy_module.run_reconcile_completions(_args(), vcs=vcs, fs=LocalFs(), harness=harness)

    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []
    assert exit_code == 0
    assert "5-9-title: done" in ledger_path.read_text(encoding="utf-8")
    assert "5-9-title: done" in feed_path.read_text(encoding="utf-8")
    # The Tier-3 feed is gitignored -- never git-committed by this step.
    assert (feed_path,) not in [paths for paths, _ in vcs.commit_calls]
