"""`cli/deploy.py`'s text renderers: pure projections of the same envelope `--format json` prints.

Story 60.1 touched `cli/deploy.py` (its push-route ref now names the full ref), which put the
module under the touched-module unit coverage floor at 77.3%; its four text renderers had no
test of their own. Each is exercised through every branch it has.
"""

from __future__ import annotations

from pyforge.marshal.cli.deploy import (
    _render_text_batch_pr,
    _render_text_land_story,
    _render_text_recover_spec,
    _render_text_refresh_feed,
)
from pyforge.marshal.core.model import Finding, Severity

_FINDING = Finding(code="MRS-DEPLOY-003", severity=Severity.WARN, message="origin/main not fetched")


def test_recover_spec_lists_snapshots_or_what_was_recovered() -> None:
    with_snapshots = _render_text_recover_spec(
        {"slug": "acme", "key": "1-1", "snapshots": [{"path": "/a/spec.md", "mtime": "2026-09-27"}]}, (_FINDING,)
    )
    assert with_snapshots.splitlines() == [
        "deploy recover-spec: 'acme' '1-1'",
        "snapshot candidates (most recent first):",
        "  '/a/spec.md' (mtime: 2026-09-27)",
        "findings:",
        "  MRS-DEPLOY-003 [warn] origin/main not fetched",
    ]
    recovered = _render_text_recover_spec({"slug": "acme", "key": "1-1", "recovered_path": "/p", "recovered": True}, ())
    assert recovered.splitlines()[1:] == [
        "snapshot candidates: none",
        "recovered_path: '/p'",
        "recovered: epics-derived contract-only spec written",
    ]
    present = _render_text_recover_spec({"key": "1-1", "already_present": True}, ())
    assert present.splitlines() == [
        "deploy recover-spec: '(no active project)' '1-1'",
        "snapshot candidates: none",
        "already present -- not overwritten",
    ]


def test_land_story_renders_a_merge_and_its_conformance_audit() -> None:
    merged = _render_text_land_story(
        {
            "slug": "acme",
            "key": "1-1",
            "branch": "loop/acme",
            "gate_verdict": "pass",
            "merge_sha": "abc123",
            "subject": "Merge acme/1-1 into main",
            "non_conforming_merges": ["hand merge"],
            "since": "2026-09-01",
        },
        (_FINDING,),
    )
    assert merged.splitlines() == [
        "deploy land-story: 'acme' '1-1'",
        "branch: 'loop/acme'",
        "gate verdict: pass",
        "merge sha: abc123",
        "subject: 'Merge acme/1-1 into main'",
        "conformance audit: 1 non-conforming merge(s) since '2026-09-01'",
        "  'hand merge'",
        "findings:",
        "  MRS-DEPLOY-003 [warn] origin/main not fetched",
    ]
    unaudited = _render_text_land_story({"slug": "acme", "key": "1-1", "merge_sha": "abc", "subject": "s"}, ())
    assert "conformance audit: could not enumerate (see findings)" in unaudited.splitlines()
    noop = _render_text_land_story({"key": "1-1", "already_merged": True}, ())
    assert noop.splitlines() == [
        "deploy land-story: '(no active project)' '1-1'",
        "already merged -- no-op (no gate run, no merge attempted)",
    ]


def test_batch_pr_renders_opened_updated_and_neither() -> None:
    opened = _render_text_batch_pr(
        {
            "slug": "acme",
            "branch": "loop/acme",
            "wave": ["1-1", "1-2"],
            "hygiene_rules": [{"name": "maintenance-label", "applies": True, "satisfied": True}],
            "opened": True,
            "pr_number": 7,
            "pr_url": "https://example/pr/7",
            "labels_applied": ["maintenance"],
        },
        (_FINDING,),
    )
    assert opened.splitlines() == [
        "deploy batch-pr: 'acme'",
        "branch: 'loop/acme'",
        "wave: 2 stories (1-1, 1-2)",
        "hygiene rules:",
        "  'maintenance-label' applies=True satisfied=True",
        "opened: PR #7 (https://example/pr/7)",
        "labels applied: maintenance",
        "findings:",
        "  MRS-DEPLOY-003 [warn] origin/main not fetched",
    ]
    updated = _render_text_batch_pr(
        {"slug": "acme", "wave": ["1-1"], "updated": True, "pr_number": 7, "pr_url": "u"}, ()
    )
    assert updated.splitlines()[1:] == ["wave: 1 story (1-1)", "updated: PR #7 (u)"]
    landed = _render_text_batch_pr({"already_landed": True}, ())
    assert landed.splitlines() == [
        "deploy batch-pr: '(no active project)'",
        "already landed -- no-op (no PR write attempted)",
        "opened: false, updated: false",
    ]


def test_refresh_feed_renders_stories_and_the_resync() -> None:
    row = {
        "story_key": "1-1",
        "durable": {"value": True},
        "claimed_commit_sha": {"value": "abc123"},
    }
    ran = _render_text_refresh_feed({"slug": "acme", "stories": [row], "resync_commands": ["a", "b"]}, (_FINDING,))
    assert ran.splitlines() == [
        "deploy refresh-feed: 'acme'",
        "stories: 1",
        "  1-1: durable=True (git), claimed_commit_sha='abc123' (journal)",
        "resync commands run: 2",
        "findings:",
        "  MRS-DEPLOY-003 [warn] origin/main not fetched",
    ]
    skipped = _render_text_refresh_feed({"resync_skipped": True}, ())
    assert skipped.splitlines() == [
        "deploy refresh-feed: '(no active project)'",
        "stories: none",
        "resync: skipped (landing_resync is false)",
    ]
