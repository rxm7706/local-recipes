"""Unit tests for ``pyforge.doctor.sources.marshal.gather_story_status``
(Story 6.4) -- covers the spec's I/O & Edge-Case Matrix rows for
``story_status``: false-green, hand-landed (no run record), and no Tier-3
feeds present.

Both ``target`` and ``loop_root`` are ``tmp_path`` fixtures -- no real
``~/.bmad-loops`` or real git history dependency. ``target`` is still
``git init``-ed, and carries one baseline commit on ``main`` (see
``_init_repo``) so that both landing-evidence routes can actually RUN and
find nothing, rather than failing to run at all -- ``gather_story_status``
routes its merge-commit-grep and main-subject-log calls through
``cli_bridge.run_git``, which needs a real (even if trivial) repository, and
a query that could not run is deliberately not treated as a query that found
nothing. This test file is not subject to the package's sole-subprocess
restriction (only ``pyforge/doctor/cli_bridge.py`` is), so driving real
``git`` here to build fixtures is fine.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.core.landing_evidence import StoryKeyRef
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import marshal

# See test_sources_ledger.py's own note: a contributor's git config (commit
# signing, a global core.hooksPath) or an inherited GIT_DIR must not decide
# whether this suite passes. The scrub must mutate os.environ rather than build
# a private env dict, because `cli_bridge.run_git` -- the path the module under
# test takes -- reads os.environ itself at call time.
_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(target: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=target,
        capture_output=True,
        text=True,
        check=True,
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
    # A baseline commit, so the ref `main` actually EXISTS. A commitless repo
    # makes Route 3's `git log --format=%s main` exit 128, which the gather now
    # (correctly) treats as "could not query" rather than "queried and found
    # nothing" -- so every false-green assertion here would have been reached
    # via an unqueried route, which is precisely the false conviction the
    # inconclusive branch exists to prevent. Committing once makes these
    # fixtures exercise the real path: Route 3 runs, finds no matching subject,
    # and the story falls through to the harness verdict on its merits.
    _git(target, "commit", "-q", "--allow-empty", "-m", "chore: initialize fixture")


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


def _write_ledger(target: Path, slug: str, statuses: dict[str, str]) -> None:
    """A minimal tracked ``sprint-status-ledger.yaml`` -- Story 27.3's
    ``known_keys`` corroboration source, distinct from the gitignored Tier-3
    feed ``_write_feed`` writes."""
    ledger = (
        target
        / "_bmad-output"
        / "projects"
        / f"pyforge-{slug}"
        / "planning-artifacts"
        / "sprint-status-ledger.yaml"
    )
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:"]
    lines.extend(f"  {key}: {value}" for key, value in statuses.items())
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_policy(target: Path, slug: str, merge_subject_template: str) -> None:
    """A minimal ``marshal-policy.toml`` declaring only the one key Story
    27.1 reads per-project instead of the hardcoded repo default."""
    policy = (
        target / "_bmad-output" / "projects" / f"pyforge-{slug}"
        / "planning-artifacts" / "marshal-policy.toml"
    )
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        f'merge_subject_template = "{merge_subject_template}"\n', encoding="utf-8"
    )


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
    _commit(target, "Merge bmad-loop/run/1-1-foo into loop/pyforge-warden (bmad-loop)")
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


# --- Story 27.1: templated merge subject, scoped to the project's OWN
# marshal-policy.toml rather than the hardcoded repo default -------------


def test_own_scoped_template_merge_suppresses_the_false_green(tmp_path: Path) -> None:
    """A station's own ``merge_subject_template`` (read from its tracked
    policy file) is valid Route 2 landing evidence, exactly like the bare
    legacy default used to be for every project unconditionally."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_policy(target, "doctor", "Merge pyforge-doctor/{key} into main")
    _commit(target, "Merge pyforge-doctor/1-1 into main")
    _write_feed(target, "doctor", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"audited": 1}


def test_sibling_bare_default_merge_does_not_suppress_once_scoped(
    tmp_path: Path,
) -> None:
    """The live incident, mirrored on the story-status side: once a station
    declares its OWN scoped template, a sibling's plain ``Merge <key> into
    main`` -- rendered from THAT sibling's still-unscoped legacy default --
    must not be read as this station's landing evidence, even when the
    numeric key coincides."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_policy(target, "doctor", "Merge pyforge-doctor/{key} into main")
    # A sibling's own (unscoped) legacy-default merge, same numeric key.
    _commit(target, "Merge 1-1 into main")
    _write_feed(target, "doctor", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].evidence["key"] == "1-1-foo"


# --- Story 27.3 (CAP-80): a station's legacy-template history stays
# attributed once its template moves, corroborated by its own tracked
# ledger's `done` entries -------------------------------------------------


def test_own_legacy_merge_suppresses_the_false_green_once_template_moves(
    tmp_path: Path,
) -> None:
    """The live regression this story fixes: marshal landed `34-3` on
    2026-09-12 as `Merge 34-3 into main` under the then-default template;
    once marshal's policy moved to a scoped form (PR #1467), that subject
    must still count as marshal's own landing evidence -- corroborated by
    the tracked ledger already marking `34-3` `done`."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_policy(target, "marshal", "Merge pyforge-marshal/{key} into main")
    _write_ledger(target, "marshal", {"34-3-factory-drain": "done"})
    _commit(target, "Merge 34-3 into main")
    _write_feed(target, "marshal", ["34-3-factory-drain"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "marshal", "run1",
        {"34-3-factory-drain": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"audited": 1}


def test_keys_from_merge_subjects_attributes_own_legacy_form_once_ledger_confirms_done(
    tmp_path: Path,
) -> None:
    """Unit-level proof at the corroboration boundary itself."""
    target = tmp_path / "target"
    target.mkdir()
    _write_policy(target, "marshal", "Merge pyforge-marshal/{key} into main")
    _write_ledger(target, "marshal", {"34-3-factory-drain": "done"})

    keys = marshal._keys_from_merge_subjects(
        target, ("Merge 34-3 into main",), project_slug="pyforge-marshal",
    )

    assert keys == frozenset({StoryKeyRef(34, 3)})


def test_keys_from_merge_subjects_does_not_attribute_a_not_yet_done_key(
    tmp_path: Path,
) -> None:
    """A coincidentally-numbered key present in this station's own ledger
    but not (yet) `done` must not corroborate -- only a `done` entry does
    (mirrors the sibling-collision fixture `sources/ledger.py`'s own
    ``test_sibling_default_template_merge_is_not_attributed_when_station_
    has_its_own`` pins)."""
    target = tmp_path / "target"
    target.mkdir()
    _write_policy(target, "marshal", "Merge pyforge-marshal/{key} into main")
    _write_ledger(target, "marshal", {"34-3-factory-drain": "backlog"})

    keys = marshal._keys_from_merge_subjects(
        target, ("Merge 34-3 into main",), project_slug="pyforge-marshal",
    )

    assert keys == frozenset()


def test_keys_from_merge_subjects_no_tracked_ledger_attributes_nothing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _write_policy(target, "marshal", "Merge pyforge-marshal/{key} into main")
    # deliberately no sprint-status-ledger.yaml at all

    keys = marshal._keys_from_merge_subjects(
        target, ("Merge 34-3 into main",), project_slug="pyforge-marshal",
    )

    assert keys == frozenset()


def test_keys_from_main_commits_attributes_own_legacy_form_once_ledger_confirms_done(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _write_policy(target, "marshal", "Merge pyforge-marshal/{key} into main")
    _write_ledger(target, "marshal", {"34-3-factory-drain": "done"})

    keys = marshal._keys_from_main_commits(
        target,
        [("deadbeef", "Merge 34-3 into main")],
        project_slug="pyforge-marshal",
    )

    assert keys == frozenset({StoryKeyRef(34, 3)})


def test_keys_from_main_commits_does_not_attribute_a_not_yet_done_key(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _write_policy(target, "marshal", "Merge pyforge-marshal/{key} into main")
    _write_ledger(target, "marshal", {"34-3-factory-drain": "backlog"})

    keys = marshal._keys_from_main_commits(
        target,
        [("deadbeef", "Merge 34-3 into main")],
        project_slug="pyforge-marshal",
    )

    assert keys == frozenset()


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
    _commit(target, "Story 1.1 — the scaffold lands")
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_route3_requires_matching_story_ref_not_a_neighbour(tmp_path: Path) -> None:
    """A commit naming a different story number must not launder this one."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "Story 2.2 — a neighbouring story")
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


def test_harness_tasks_prefers_published_plane_over_loop_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root,
        "warden",
        "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    def _published(_slug: str) -> dict[str, dict]:
        return {"1-1-foo": {"phase": "done", "commit_sha": "from-plane"}}

    monkeypatch.setattr(marshal, "_published_story_tasks", _published)
    tasks = marshal._harness_tasks(loop_root, "warden")
    assert tasks["1-1-foo"]["commit_sha"] == "from-plane"


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


# --- The green verdict must not vouch for what it never checked ------------


def test_ok_message_does_not_claim_evidence_for_unchecked_stories(
    tmp_path: Path,
) -> None:
    """A `done` key with no run record takes the SILENT branch -- it is counted
    into `audited` but never checked against any evidence route. The message
    used to assert "every `done` story is backed by a merge commit or a recorded
    commit sha" over that population; measured live against this repo, 19 of 27
    audited keys were in exactly that state."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo", "2-2-bar"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "done", "commit_sha": "abc123"}},
    )  # 2-2-bar deliberately has no run record

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    message = findings[0].message
    assert findings[0].status is DoctorStatus.OK
    assert "2 audited" in message
    assert "1 with no run record (unchecked)" in message
    # The overstated claim must be gone, not merely qualified.
    assert "every `done` story is backed" not in message


def test_unreadable_run_records_are_counted_not_silently_dropped(
    tmp_path: Path,
) -> None:
    """A malformed run record is skipped, which makes the story indistinguishable
    from "no run record at all" -- the detector's silent branch. Corrupt harness
    state is exactly what a broken loop run leaves behind, so a false-green could
    pass as clean with nothing in the report to show a record was dropped."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(loop_root, "warden", "run1", {"1-1-foo": "not-a-dict"})

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert "1 with an unreadable run record" in findings[0].message
    # And NOT counted as "no run record": the record existed, it was unusable.
    assert "no run record" not in findings[0].message


def test_a_fully_evidenced_audit_reports_no_caveats(tmp_path: Path) -> None:
    """The counters are additive, not always-on: with every story backed by a
    recorded commit there is nothing to qualify."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "done", "commit_sha": "abc123"}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert findings[0].message == (
        "no `done` story contradicts its landing evidence (1 audited)"
    )
    # Evidence shape is pinned by the spec's I/O matrix -- unchanged.
    assert findings[0].evidence == {"audited": 1}


# --- Cannot-evaluate is never a conviction ---------------------------------


def test_a_missing_main_branch_does_not_convict_a_hand_landed_story(
    tmp_path: Path,
) -> None:
    """Route 3 queries the literal ref ``main``. On a PR checkout, a shallow
    clone, or a repo whose default branch is named otherwise, that query FAILS
    -- and a failed query used to be indistinguishable from "queried `main`,
    found nothing", so a genuinely hand-landed story fell through to the
    harness verdict and was accused of being a false green.

    The repo-level ``rev-parse --git-dir`` probe does not cover this: the repo
    is perfectly valid, it just has no ``main``."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])
    _commit(target, "Story 1.1 - foo, landed by hand")

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )

    # Control: with `main` present, Route 3 finds the subject and stays quiet.
    assert marshal.gather_story_status(
        target, loop_root=loop_root
    )[0].status is DoctorStatus.OK

    _git(target, "branch", "-m", "main", "pr-branch")

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert [f.status for f in findings] == [DoctorStatus.OK]
    assert "1 whose git landing evidence could not be queried" in findings[0].message


def test_a_story_with_a_record_but_no_evidence_is_not_vouched_for(
    tmp_path: Path,
) -> None:
    """A story whose harness phase is neither a landing signal nor one of the
    NOT_LANDED verdicts (``review-running``, ``in-progress``, ...) reaches the
    end of every route with nothing found. It is not an accusation -- but it is
    not a verified landing either, and counting it silently into ``audited``
    made the green vouch for a story it never established anything about."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "warden", "run1",
        {"1-1-foo": {"phase": "review-running", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert [f.status for f in findings] == [DoctorStatus.OK]
    assert (
        "1 with no landing evidence and no harness verdict" in findings[0].message
    )


# --- Malformed harness state, revisited ------------------------------------


def test_a_non_scalar_phase_value_does_not_crash_the_gather(
    tmp_path: Path,
) -> None:
    """``phase in NOT_LANDED`` HASHES ``phase``, so a JSON record giving it a
    list or a dict raised ``TypeError: unhashable type`` straight out of the
    gather. ``_harness_tasks``'s ``isinstance(task, dict)`` guard validates the
    CONTAINER and never the values inside it, and ``phase`` is the only value
    fed to a hash-requiring operation."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    for phase in (["deferred"], {"was": "deferred"}, 7):
        _write_state(
            loop_root, "warden", "run1",
            {"1-1-foo": {"phase": phase, "commit_sha": None}},
        )

        findings = marshal.gather_story_status(target, loop_root=loop_root)

        assert [f.status for f in findings] == [DoctorStatus.OK]


def test_a_truncated_run_record_file_is_counted_not_silently_dropped(
    tmp_path: Path,
) -> None:
    """A truncated ``state.json`` is the likeliest corruption a killed loop run
    leaves behind, and it fails at ``json.loads`` -- the WHOLE-FILE branch,
    which the per-entry counter never touched. Its story then read as "no run
    record (unchecked)", indistinguishable from a genuinely hand-landed one:
    corrupt harness state passing as a clean audit, which is the exact
    conflation the counter exists to prevent."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    state = loop_root / "pyforge-warden" / ".bmad-loop" / "runs" / "r1" / "state.json"
    state.parent.mkdir(parents=True)
    state.write_text('{"tasks": {"1-1-foo": {"phase": "defe', encoding="utf-8")

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert [f.status for f in findings] == [DoctorStatus.OK]
    assert "1 run record file(s) unreadable" in findings[0].message


def test_malformed_records_for_unaudited_keys_do_not_inflate_the_caveat(
    tmp_path: Path,
) -> None:
    """The caveat qualifies the AUDIT, so it must count audited stories -- not
    every malformed entry found anywhere under the station's run history. An
    accumulator that counted all of them could print "1 audited, 3 run
    record(s) unreadable": a count exceeding its own denominator, qualifying a
    result whose evidence was in fact complete."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    for i in (1, 2, 3):
        _write_state(loop_root, "warden", f"r{i}", {f"9-{i}-not-in-any-feed": "bad"})
    _write_state(
        loop_root, "warden", "r9",
        {"1-1-foo": {"phase": "done", "commit_sha": "abc123"}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert findings[0].message == (
        "no `done` story contradicts its landing evidence (1 audited)"
    )


def test_a_superseded_malformed_record_is_not_counted(tmp_path: Path) -> None:
    """A key malformed in one run and valid in a later one is fully evidenced
    -- ``_harness_tasks`` already prefers the record carrying a ``commit_sha``
    -- so the caveat must not report it as unreadable."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    loop_root = tmp_path / "loop_root"
    _write_state(loop_root, "warden", "run1", {"1-1-foo": "malformed"})
    _write_state(
        loop_root, "warden", "run2",
        {"1-1-foo": {"phase": "done", "commit_sha": "abc123"}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert findings[0].message == (
        "no `done` story contradicts its landing evidence (1 audited)"
    )


def test_an_unreadable_feed_is_named_rather_than_silently_dropped(
    tmp_path: Path,
) -> None:
    """A feed that cannot be decoded drops a WHOLE station from the audit. The
    OK Finding must not then read as a confident green over a station it never
    opened. (Escalating to WARN and putting the count in ``evidence`` would
    change the OK Finding's evidence shape, which the spec's I/O matrix pins --
    that decision stays deferred; the message caveat does not need it.)"""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])
    _write_feed(target, "atlas", ["2-1-bar"])

    broken = (
        target / "_bmad-output" / "projects" / "pyforge-warden"
        / "implementation-artifacts" / "sprint-status.yaml"
    )
    broken.write_bytes(b"development_status:\n  1-1-f\xe9o: done\n")

    findings = marshal.gather_story_status(target, loop_root=tmp_path / "loop_root")

    assert [f.status for f in findings] == [DoctorStatus.OK]
    assert "1 sprint feed(s) unreadable" in findings[0].message
    assert findings[0].evidence == {"audited": 1}  # only atlas's key was audited


# --- Story 20.9: standing false positives go green via shared grammar ------


@pytest.mark.parametrize(
    ("slug", "key", "subject", "commit_sha"),
    [
        (
            "marshal",
            "8-2-region-parser",
            "Story 8.2: region parser -- span discovery, nesting rejection, fence awareness",
            "accc097e6a",
        ),
        (
            "marshal",
            "10-1-copier-engine",
            "recover marshal 10-1 (Copier engine wrapper — the single seam)",
            "5290c9bcd2",
        ),
        (
            "mason",
            "3-7-asymmetric-receipts",
            (
                "recover mason 3.7 (asymmetric receipts, partial failure and idempotence) "
                "from run 20260813-145934-3eb0's failed/ preserved patch"
            ),
            "03d8fc8c86",
        ),
    ],
)
def test_standing_false_positives_suppress_via_grammar(
    tmp_path: Path,
    slug: str,
    key: str,
    subject: str,
    commit_sha: str,
) -> None:
    """Marshal 8-2, marshal 10-1, mason 3-7 -- live false positives before 20.9."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _git(target, "commit", "-q", "--allow-empty", "-m", subject)
    _write_feed(target, slug, [key])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root,
        slug,
        "run1",
        {key: {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"audited": 1}


# --- The branch-name fallback (mirrors marshal's own promotion.py) ---------
#
# Live 2026-08-28: doctor's story-status Routes 2/3 never tried the
# `land/<station>-<epic>-<seq>` / `bmad-loop/<run>/<key>` branch-name
# grammars when a GitHub PR merge subject's branch didn't carry a
# station-prefixed segment -- marshal's own `promotion.py::_classify_merge_
# subject` already had this fallback; doctor's port never picked it up.
# Confirmed to have produced a false-positive FAIL for all 25 genuinely-
# landed stories audited that session.


def test_land_branch_wrapped_in_a_github_pr_subject_suppresses_the_false_green(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(
        target,
        "Merge pull request #395 from rxm7706/land/doctor-6-9-ledger",
    )
    _write_feed(target, "doctor", ["6-9-the-scripts-shims-retire"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"6-9-the-scripts-shims-retire": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_bmadloop_branch_wrapped_in_a_github_pr_subject_suppresses_the_false_green(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(
        target,
        "Merge pull request #602 from rxm7706/bmad-loop/20260811-190409-5c73/8-2-region-parser",
    )
    _write_feed(target, "marshal", ["8-2-region-parser"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "marshal", "run1",
        {"8-2-region-parser": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_an_unrelated_pr_branch_does_not_suppress(tmp_path: Path) -> None:
    """The fallback still requires a REAL branch-name grammar match -- a
    ``maintenance/`` branch (not shaped like ``land/<station>-<epic>-<seq>``
    or ``bmad-loop/<run>/<key>``) must not launder every open story. The
    branch is deliberately key-free so Route 4 (loose co-occurrence) cannot
    fire either -- this isolates the branch-name fallback specifically."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(
        target,
        "Merge pull request #543 from rxm7706/maintenance/doctor-ledger-sync",
    )
    _write_feed(target, "doctor", ["11-1-due-for-verification"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"11-1-due-for-verification": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL


# --- Route 4: loose station+key co-occurrence, last resort -----------------


def test_loose_co_occurrence_suppresses_a_hand_authored_landing_commit(
    tmp_path: Path,
) -> None:
    """Real shape, confirmed live 2026-08-28 (doctor 11-1's actual landing
    commit): no anchored grammar shape matches "<station>: promote story
    <e>.<s> to done in the tracked ledger", but the station and the exact
    key genuinely co-occur."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "doctor: promote story 11.1 to done in the tracked ledger")
    _write_feed(target, "doctor", ["11-1-due-for-verification"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"11-1-due-for-verification": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_loose_co_occurrence_does_not_confuse_a_longer_key(tmp_path: Path) -> None:
    """"11.10" must not satisfy key "11-1" -- the digit-boundary guard."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "doctor: promote story 11.10 to done in the tracked ledger")
    _write_feed(target, "doctor", ["11-1-due-for-verification"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"11-1-due-for-verification": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL


def test_loose_co_occurrence_requires_the_station_too(tmp_path: Path) -> None:
    """The key alone, without the station word, must not suppress -- a
    neighbouring station's commit mentioning the same numeric key must not
    launder this one."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "marshal: promote story 11.1 to done in the tracked ledger")
    _write_feed(target, "doctor", ["11-1-due-for-verification"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"11-1-due-for-verification": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL


def test_loose_co_occurrence_does_not_confuse_an_unsuffixed_key_with_a_suffixed_one(
    tmp_path: Path,
) -> None:
    """A commit naming the bare key ("11.1") must not satisfy a search for
    its lettered split-story sibling ("11-1a") -- review-pass finding
    (2026-08-28): the original key regex was built from epic/seq only,
    silently dropping ``StoryKeyRef.suffix``."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "doctor: promote story 11.1 to done in the tracked ledger")
    _write_feed(target, "doctor", ["11-1a-suffixed-sibling"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"11-1a-suffixed-sibling": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL


def test_loose_co_occurrence_does_not_confuse_a_suffixed_key_with_the_bare_one(
    tmp_path: Path,
) -> None:
    """The reverse: a commit naming the LETTERED key must not satisfy a
    search for the bare, unsuffixed key -- two genuinely different stories
    under the split-story convention."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "doctor: promote story 11.1a to done in the tracked ledger")
    _write_feed(target, "doctor", ["11-1-bare-story"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"11-1-bare-story": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.FAIL


def test_loose_co_occurrence_matches_the_exact_suffixed_key(tmp_path: Path) -> None:
    """The positive case: a commit naming the SAME lettered key suppresses
    the false green, exactly like the bare-key case."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _commit(target, "doctor: promote story 11.1a to done in the tracked ledger")
    _write_feed(target, "doctor", ["11-1a-suffixed-story"])

    loop_root = tmp_path / "loop_root"
    _write_state(
        loop_root, "doctor", "run1",
        {"11-1a-suffixed-story": {"phase": "deferred", "commit_sha": None}},
    )

    findings = marshal.gather_story_status(target, loop_root=loop_root)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- The documented loop_root default --------------------------------------


def test_loop_root_defaults_to_the_bmad_loops_dir_under_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every other test here passes ``loop_root`` explicitly, so the documented
    default (``Path.home() / ".bmad-loops"``, matching the source script's own
    hardcoded ``LOOP_ROOT``) had no coverage at all -- ``".bmad-loop"`` for
    ``".bmad-loops"`` would have shipped green."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    home = tmp_path / "home"
    _write_state(
        home / ".bmad-loops", "warden", "run1",
        {"1-1-foo": {"phase": "deferred", "commit_sha": None}},
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    findings = marshal.gather_story_status(target)

    assert [f.status for f in findings] == [DoctorStatus.FAIL]
    assert findings[0].evidence["key"] == "1-1-foo"


def test_an_unresolvable_home_degrades_instead_of_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``Path.home()`` RAISES ``RuntimeError`` when ``HOME`` is unset and the
    uid has no passwd entry -- the ordinary rootless-container shape. It
    escaped before any Finding could be built, including for the no-feeds case
    the spec documents as a vacuous OK."""
    target = tmp_path / "target"
    target.mkdir()
    _init_repo(target)
    _write_feed(target, "warden", ["1-1-foo"])

    def _no_home(cls: type[Path]) -> Path:
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(Path, "home", classmethod(_no_home))

    findings = marshal.gather_story_status(target)

    assert [f.status for f in findings] == [DoctorStatus.OK]
    # No harness records visible, so every audited story is "no run record".
    assert "1 with no run record (unchecked)" in findings[0].message
