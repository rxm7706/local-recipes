"""Story 28.23: fleet-picture ATTENTION names stranded dispatch work."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"

_STORY = "28-23-stranded-work-signal-after-terminal-verify-fail"
_BRANCH = f"dispatch/pyforge-marshal/{_STORY}"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location("fleet_picture_stranded_work_test", FLEET_PICTURE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_stranded_work_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _terminal_live_row(**overrides):
    row = {
        "story": _STORY,
        "dispatch_completion_verdict": "failed",
        "dispatch_phase": None,
        "dispatch_verification_verdict": "refused",
    }
    row.update(overrides)
    return row


def test_terminal_dead_tail_is_not_treated_as_active_dispatch():
    mod = _load_fleet_picture()
    assert mod.dispatch_terminal_dead_tail(_terminal_live_row())
    assert not mod.dispatch_active(_terminal_live_row())


def test_blocked_verdict_dead_tail_is_not_treated_as_active_dispatch():
    """Story 51.11 (CAP-258): a `blocked` completion verdict is a terminal
    dead-tail case too, matching `failed`/`stopped_externally`."""
    mod = _load_fleet_picture()
    row = _terminal_live_row(dispatch_completion_verdict="blocked")
    assert mod.dispatch_terminal_dead_tail(row)
    assert not mod.dispatch_active(row)


def test_unpushed_dispatch_branch_attention_line():
    mod = _load_fleet_picture()
    live_row = {
        **_terminal_live_row(),
        "dispatch_stranded_work": {
            "kind": "unpushed-branch",
            "ref": _BRANCH,
            "story": _STORY,
            "files": 3,
            "remedy": f"git push origin {_BRANCH}",
        },
    }
    lines = mod._dispatch_stranded_work_needs_lines(
        slug="marshal",
        story=_STORY,
        live_row=live_row,
        open_prs_by_head={},
    )
    assert len(lines) == 1
    assert "unpushed branch" in lines[0]
    assert _BRANCH in lines[0]


def test_open_pr_attention_line_when_no_unpushed_signal():
    mod = _load_fleet_picture()
    lines = mod._dispatch_stranded_work_needs_lines(
        slug="marshal",
        story=_STORY,
        live_row=_terminal_live_row(),
        open_prs_by_head={_BRANCH: {"number": 1000, "title": "dispatch marshal 28.23", "headRefName": _BRANCH}},
    )
    assert len(lines) == 1
    assert "open unmerged PR #1000" in lines[0]
    assert _BRANCH in lines[0]


def test_live_verify_tail_produces_no_stranded_attention_line():
    mod = _load_fleet_picture()
    live_row = _terminal_live_row(dispatch_phase="verifying")
    lines = mod._dispatch_stranded_work_needs_lines(
        slug="marshal",
        story=_STORY,
        live_row=live_row,
        open_prs_by_head={_BRANCH: {"number": 1, "title": "x"}},
    )
    assert lines == []
