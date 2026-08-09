"""Unit tests for ``pyforge.doctor.sources.marshal.gather_story_status``
(Story 6.4) -- covers the spec's I/O & Edge-Case Matrix rows for
``story_status``: false-green, hand-landed (no run record), and no Tier-3
feeds present.

Both ``target`` and ``loop_root`` are ``tmp_path`` fixtures -- no real
``~/.bmad-loops`` or real git history dependency. ``target`` is still
``git init``-ed (with no commits naming any story) because
``gather_story_status`` routes its merge-commit-grep and main-subject-log
calls through ``cli_bridge.run_git``, which needs a real (even if trivial)
repository to not error -- this test file is not subject to the package's
sole-subprocess restriction (only ``pyforge/doctor/cli_bridge.py`` is), so
driving real ``git`` here to build fixtures is fine.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import marshal


def _init_repo(target: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(
        ["git", "config", "user.email", "doctor-test@example.com"],
        cwd=target,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Doctor Test"], cwd=target, check=True
    )


def _write_feed(target: Path, slug: str, done_keys: list[str]) -> None:
    feed = (
        target
        / "_bmad-output"
        / "projects"
        / f"pyforge-{slug}"
        / "implementation-artifacts"
        / "sprint-status.yaml"
    )
    feed.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:"]
    lines.extend(f"  {key}: done" for key in done_keys)
    feed.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_state(loop_root: Path, slug: str, run: str, tasks: dict) -> None:
    state = loop_root / f"pyforge-{slug}" / ".bmad-loop" / "runs" / run / "state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")


# --- False-green story -------------------------------------------------


def test_false_green_story_reports_fail(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root,
        "warden",
        "run1",
        {
            "1-1-foo": {
                "phase": "deferred",
                "commit_sha": None,
                "defer_reason": "review did not converge",
            }
        },
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.STORY_STATUS
    assert finding.check == "story-status"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["slug"] == "warden"
    assert finding.evidence["key"] == "1-1-foo"
    assert finding.evidence["phase"] == "deferred"
    assert finding.evidence["audited"] == 1
    assert "review did not converge" in finding.message


def test_false_green_escalated_and_abandoned_phases_also_report_fail(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "mason", ["2-3-bar", "2-4-baz"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root,
        "mason",
        "run1",
        {
            "2-3-bar": {"phase": "escalated", "commit_sha": None},
            "2-4-baz": {"phase": "abandoned", "commit_sha": None},
        },
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 2
    assert {f.evidence["key"] for f in findings} == {"2-3-bar", "2-4-baz"}
    assert all(f.status is DoctorStatus.FAIL for f in findings)


# --- Story backed by a recorded commit_sha ---------------------------------


def test_story_backed_by_commit_sha_produces_no_fail_finding(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root,
        "warden",
        "run1",
        {"1-1-foo": {"phase": "done", "commit_sha": "abc123deadbeef"}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"audited": 1}


# --- Hand-landed story: no run record at all --------------------------


def test_hand_landed_story_with_no_run_record_stays_silent(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    # loop_root exists but has no run record for this slug/key at all.
    loop_root = tmp_path / "loop_root"
    loop_root.mkdir()

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"audited": 1}


# --- No Tier-3 feeds present at all -----------------------------------


def test_no_tier3_feeds_present_reports_ok_with_zero_audited(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    # deliberately no _bmad-output/projects/pyforge-*/implementation-artifacts/

    loop_root = tmp_path / "loop_root"

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.STORY_STATUS
    assert finding.check == "story-status"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"audited": 0}


# --- Multi-feed aggregation ----------------------------------------------


def test_false_greens_across_multiple_station_feeds_are_all_reported(
    tmp_path: Path,
) -> None:
    """The Tier-3 glob spans every station's feed, not just one -- a
    false-green in "warden" must not suppress or merge with one in "mason",
    and a clean third station must not produce a spurious finding. Every
    finding's evidence carries the FINAL total `audited` count across all
    three feeds, not a per-feed running count."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])
    _write_feed(target, "mason", ["2-2-bar"])
    _write_feed(target, "doctor", ["3-3-baz"])  # clean: backed by commit_sha

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )
    _write_state(
        loop_root, "mason", "run1",
        {"2-2-bar": {"phase": "escalated", "commit_sha": None}},
    )
    _write_state(
        loop_root, "doctor", "run1",
        {"3-3-baz": {"phase": "done", "commit_sha": "cafef00d"}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 2
    assert {f.evidence["slug"] for f in findings} == {"warden", "mason"}
    assert all(f.status is DoctorStatus.FAIL for f in findings)
    assert all(f.evidence["audited"] == 3 for f in findings)
