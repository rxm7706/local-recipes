"""dispatch_land_finalize's ledger publish, read against this checkout's scripts.

Story 116.4 (spec-pyforge-marshal:CAP-305): the tree-read guard runs every package-half test off the tree (a working
directory outside the repository, ``cli/config.py`` anchored in a bare checkout), and these tests fail there:
each publishes the sprint ledger through ``scripts/promote_sprint_status.py``, which the finalize step loads
from the checkout ``checkout_root()`` names.
They moved here, marked ``live_tree``; each fails, never skips, when what it reads is absent. Every other
test stays in ``test_dispatch_land_finalize.py``, and this module imports the helpers both use from it by name.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_dispatch_land_finalize import (
    _BACKLOG_LEDGER_64_1,
    _FEED_KEY_79,
    _SLUG_79,
    _NoScan,
    _PublishVcs,
    _stub_planned_finalize,
    _StubVcs,
    _write_feed_79,
)

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.core.status import render_ledger_advancements
from pyforge.marshal.dispatch_land_finalize.__main__ import (
    _FINALIZE_RESYNC_KIND,
    finalize_dispatch_land,
)

pytestmark = pytest.mark.live_tree


def test_the_64_1_replay_a_publish_timeout_inside_finalize_is_a_failed_landing(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC 4 + 5 end to end, with the REAL `_promote_sprint_ledger`: the publish is killed at the git timeout,
    `origin/main` still reads `backlog`. The promotion journals INTENT then OUTCOME `ok: false`; the resync
    observation carries `MRS-LAND-011` and `MRS-DISP-051`; finalize returns 1."""
    from pyforge.marshal.dispatch_land_finalize import __main__ as mod

    ledger = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "sprint-status-ledger.yaml"
    )
    ledger.parent.mkdir(parents=True)
    ledger.write_text(_BACKLOG_LEDGER_64_1, encoding="utf-8")

    class _TimingOutVcs(_StubVcs):
        def commit_paths_onto_remote_tip(self, repo_root, *, remote, ref, writes, message, preflight_skip_reason=None):
            raise VcsCommandError(
                f"git command timed out after 120.0s: git -C {repo_root} push origin abc:refs/heads/main"
            )

    vcs = _TimingOutVcs(ledger_text=_BACKLOG_LEDGER_64_1)
    monkeypatch.setattr(mod, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(mod, "GitVcs", lambda: vcs)
    monkeypatch.setattr(mod, "_scan_promotions", lambda *a, **k: _NoScan())
    monkeypatch.setattr(mod, "_resync_home_branch", lambda *a, **k: True)
    monkeypatch.setattr(mod, "_run_deferred_work_intake", lambda *a, **k: None)

    assert finalize_dispatch_land("pyforge-marshal", "64.1") == 1

    runs_dir = tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "implementation-artifacts" / "runs"
    [run_dir] = list(runs_dir.iterdir())
    entries = [
        json.loads(line) for line in (run_dir / "journal.jsonl").read_text(encoding="utf-8").splitlines() if line
    ]
    ledger_entries = [e for e in entries if e["kind"] == "land-sprint-ledger-promotion"]
    assert [e["phase"] for e in ledger_entries] == ["intent", "outcome"]
    assert ledger_entries[1]["payload"]["ok"] is False
    assert "timed out after 120.0s" in ledger_entries[1]["payload"]["error"]
    [observation] = [e for e in entries if e["kind"] == _FINALIZE_RESYNC_KIND]
    assert [f["code"] for f in observation["payload"]["findings"]] == ["MRS-LAND-011", "MRS-DISP-051"]
    assert "finding MRS-DISP-051" in capsys.readouterr().err


def test_a_plain_sprint_ledger_sync_reports_unchanged_once_the_feed_row_is_promoted(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC 1, second clause, through the sync's own entry point (`scripts/promote_sprint_status.py`, the module
    `marshal land` loads) over the tmp feed and the twin a landing leaves: after finalize promotes the feed row,
    a plain sync reports `unchanged` (Story 54.1 repairs feed-behind-twin drift on a bare sync before that)."""
    from pyforge.marshal.cli.land import _load_promote_sprint_status_module

    sync = _load_promote_sprint_status_module()
    assert sync is not None, "scripts/promote_sprint_status.py must load -- the AC is stated in its terms"
    monkeypatch.setattr(sync, "REPO_ROOT", tmp_path)
    feed = _write_feed_79(tmp_path)
    # The twin `_promote_sprint_ledger` writes: the sync's own render of the pre-landing feed, the landed key
    # advanced to done.
    feed_rel = f"_bmad-output/projects/{_SLUG_79}/implementation-artifacts/sprint-status.yaml"
    rendered = sync.render("marshal", feed_rel, sync._load_generate().parse_sprint_status(feed))
    twin_text, matched = render_ledger_advancements(rendered, frozenset({_FEED_KEY_79}))
    assert matched == {_FEED_KEY_79}
    twin = sync.ledger_path_for(_SLUG_79)
    twin.parent.mkdir(parents=True, exist_ok=True)
    twin.write_text(twin_text, encoding="utf-8")

    _stub_planned_finalize(monkeypatch, tmp_path, _PublishVcs(ledger_text=twin_text))
    assert finalize_dispatch_land(_SLUG_79, "79.1") == 0
    capsys.readouterr()

    assert sync.main(["--project", "marshal"]) == 0
    after = capsys.readouterr().out
    assert "wrote 0, unchanged 1, skipped 0, refused 0" in after
    assert twin.read_text(encoding="utf-8") == twin_text
