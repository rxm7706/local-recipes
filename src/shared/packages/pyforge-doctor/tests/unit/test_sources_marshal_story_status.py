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
import os
import subprocess
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import marshal

# See test_sources_ledger.py's own note: a contributor's git config (commit
# signing, a global core.hooksPath) or an inherited GIT_DIR must not decide
# whether this suite passes -- cli_bridge.run_git forwards os.environ verbatim,
# so the module under test would inherit them too.
_GIT_ENV = {
    k: v
    for k, v in os.environ.items()
    if k not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"}
}


def _git(target: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=target,
        capture_output=True,
        text=True,
        check=True,
        env=_GIT_ENV,
    )
    return result.stdout


def _init_repo(target: Path) -> None:
    # --initial-branch=main matters here beyond determinism: gather_story_status's
    # Route 3 queries the literal ref `main`, so a contributor whose
    # init.defaultBranch is `master` would otherwise silently exercise a
    # different branch of the code than CI does.
    _git(target, "init", "-q", "--initial-branch=main")
    _git(target, "config", "user.email", "doctor-test@example.com")
    _git(target, "config", "user.name", "Doctor Test")
    _git(target, "config", "commit.gpgsign", "false")
    _git(target, "config", "core.hooksPath", "/dev/null")


def _commit(target: Path, subject: str) -> str:
    """Empty commit carrying ``subject`` -- the git-visible evidence the two
    landing routes actually read."""
    _git(target, "commit", "-q", "--allow-empty", "-m", subject)
    return _git(target, "rev-parse", "HEAD").strip()


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


# --- Route 1: merge commit naming the key ---------------------------------
#
# Every test above builds a commitless repo, where BOTH git routes fail closed
# and every assertion therefore holds via the failure path -- deleting either
# route's implementation would leave those tests green. The next three tests
# exercise the routes' SUCCESS paths, which is where their real logic lives.


def test_merge_commit_naming_the_key_suppresses_the_false_green(
    tmp_path: Path,
) -> None:
    """Route 1: a merge commit whose message contains ``/<key> into`` is
    landing evidence, even though the harness recorded no commit_sha and says
    the story was deferred."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "Merge bmad-loop/run/1-1-foo into loop/pyforge-warden")
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"audited": 1}


def test_merge_commit_for_a_different_key_does_not_suppress(tmp_path: Path) -> None:
    """The Route 1 grep is fixed-string and key-specific: a merge commit for a
    NEIGHBOURING story must not launder this one."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "Merge bmad-loop/run/9-9-other into loop/pyforge-warden")
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].evidence["key"] == "1-1-foo"


# --- Route 3: hand-landed, named in a commit subject on main ---------------


def test_hand_landed_commit_subject_on_main_suppresses_the_false_green(
    tmp_path: Path,
) -> None:
    """Route 3: a commit SUBJECT reachable from ``main`` naming both the slug
    and ``Story <epic>.<seq>``. This is the most intricate rule in the port
    and the one with no coverage before now."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "warden: Story 1.1 — the scaffold lands")
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_route3_requires_both_the_slug_and_the_story_phrase(tmp_path: Path) -> None:
    """Naming the story number without the station slug (or vice versa) is NOT
    evidence -- both must appear in the same subject."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "mason: Story 1.1 — a different station's story 1.1")
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL


# --- Cannot-evaluate is a WARN, never a FAIL -------------------------------


def test_non_repository_target_warns_instead_of_accusing(tmp_path: Path) -> None:
    """Two of the three evidence routes are git queries. With no repository
    they fail closed, and without a probe the story would fall through to the
    NOT_LANDED test and be reported as a false green on evidence that was
    never gathered -- convicting a story for an infrastructure failure."""
    target = tmp_path / "target"
    target.mkdir()  # deliberately NOT a git repository
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert finding.source is Source.STORY_STATUS
    assert finding.evidence["feeds"] == 1
    assert finding.evidence["audited"] == 0


# --- Malformed harness state degrades, never crashes -----------------------


def test_non_dict_task_value_does_not_crash_the_gather(tmp_path: Path) -> None:
    """A ``state.json`` mapping a story key to a non-dict value must be
    skipped, not raise. The module's contract is "degrades, never crashes";
    an AttributeError escaping here would take down the whole multi-station
    gather over one malformed record."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    for malformed in ("not-a-dict", ["a", "list"], 7):
        _write_state(loop_root, "warden", "run1", {"1-1-foo": malformed})

        findings = marshal.gather_story_status(target, loop_root=loop_root)

        assert len(findings) == 1
        assert findings[0].status is DoctorStatus.OK


def test_malformed_task_entry_does_not_un_audit_its_neighbours(
    tmp_path: Path,
) -> None:
    """One bad entry must cost only itself. Guarding the whole loop with a
    single try/except would drop every entry after the malformed one, so those
    stories would read as "no run record" and go silently unaudited -- a
    false-green produced by the false-green detector."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo", "2-2-bar"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root,
        "warden",
        "run1",
        {
            "1-1-foo": "malformed-and-listed-first",
            "2-2-bar": {"phase": "deferred", "commit_sha": None},
        },
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    # The healthy neighbour is still judged despite its malformed predecessor.
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].evidence["key"] == "2-2-bar"


def test_non_dict_tasks_payload_is_skipped(tmp_path: Path) -> None:
    """``tasks`` itself being a list (not a dict) is the same class of
    malformation one level up."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)

    loop_root = tmp_path / "loop_root"
    state = loop_root / "pyforge-warden" / ".bmad-loop" / "runs" / "r1" / "state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"tasks": ["not", "a", "dict"]}), encoding="utf-8")

    assert marshal._harness_tasks(loop_root, "warden") == {}


# --- Most-advanced run record selection ------------------------------------


def test_later_run_with_a_commit_sha_wins_over_an_earlier_deferral(
    tmp_path: Path,
) -> None:
    """``_harness_tasks``'s whole reason for existing: a later run can re-drive
    a story an earlier run deferred, so the record carrying a ``commit_sha``
    must win regardless of which run file it came from."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )
    _write_state(
        loop_root, "warden", "run2",
        {"1-1-foo": {"phase": "done", "commit_sha": "abc123"}},
    )

    assert marshal._harness_tasks(loop_root, "warden")["1-1-foo"]["commit_sha"] == (
        "abc123"
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_earlier_run_with_a_commit_sha_is_not_overwritten_by_a_later_deferral(
    tmp_path: Path,
) -> None:
    """The preference is for the record with evidence, NOT simply the last one
    read -- glob order must not decide the verdict."""
    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "done", "commit_sha": "abc123"}},
    )
    _write_state(
        loop_root, "warden", "run2",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    assert marshal._harness_tasks(loop_root, "warden")["1-1-foo"]["commit_sha"] == (
        "abc123"
    )
