"""Story 56.1 (spec-pyforge-marshal CAP-266): a refused dispatch landing whose
story has since landed on ``main`` reads as superseded.

The refusal stays the journal's process fact and is never deleted; ``marshal
status`` reports git's repository fact beside it (AD-5, AD-33). The marker is
set only on a positive, corroborated merge -- every read failure leaves it
off, so the refusal stays actionable rather than being hidden on a guess.

Fixtures are the two live cases that motivated the story: doctor 30.3 (PR
#1585) and marshal 46.6 (PR #1597), whose ``MRS-DISP-020`` refusals stayed in
``fleet-picture``'s ATTENTION after both PRs merged by another route.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import status as status_cli
from pyforge.marshal.core.dispatch_harness_done import FollowupReview
from pyforge.marshal.core.model import Finding, Severity
from pyforge.marshal.core.refs import ORIGIN_MAIN
from pyforge.marshal.core.status import FleetHomeFacts, build_fleet_row

# The journal payloads and `main` subjects, verbatim from the live runs
# pyforge-doctor-20260924T110838338Z-84c5006a and
# pyforge-marshal-20260925T064250213Z-f0621b0b (the gh stderr tail trimmed).
_DOCTOR_REFUSAL = (
    {
        "code": "MRS-DISP-020",
        "message": "merge of PR #1585 failed: gh pr merge 1585 --repo rxm7706/local-recipes --merge "
        "--match-head-commit dbb394c6a66324b27365b1a2bf7fa97ad561d47c --delete-branch --subject "
        "'Merge pyforge-doctor/30-3 into main' failed: X Pull request rxm7706/local-recipes#1585 is "
        "not mergeable: the merge commit cannot be cleanly created.",
        "severity": "error",
    },
)
_MARSHAL_REFUSAL = (
    {
        "code": "MRS-DISP-020",
        "message": "merge of PR #1597 failed: gh pr merge 1597 --repo rxm7706/local-recipes --merge "
        "--match-head-commit 48631c6423a6c507d5ac5fe57f52e9ad122edeb8 --delete-branch --subject "
        "'Merge pyforge-marshal/46-6 into main' failed: X Pull request rxm7706/local-recipes#1597 is "
        "not mergeable: the merge commit cannot be cleanly created.",
        "severity": "error",
    },
)
_DOCTOR_MERGE = "Merge pull request #1585 from rxm7706/dispatch/pyforge-doctor/30.3"
_MARSHAL_MERGE = "Merge pull request #1597 from rxm7706/dispatch/pyforge-marshal/46.6"
_UNRELATED = (
    "Merge pull request #1625 from rxm7706/session-close-capture-2026-09-26",
    "herald 26.1: story spec done with its triage log; memlogs; ledger promotes 26-1 and epic-26",
)
_WARN_ONLY = ({"code": "MRS-DISP-047", "severity": "warn", "message": "reconciled"},)


class _Vcs:
    def __init__(
        self,
        subjects: tuple[str, ...] = (),
        *,
        raises: bool = False,
        spec_texts: dict[str, str] | None = None,
        origin_subjects: tuple[str, ...] = (),
        origin_raises: bool = False,
    ) -> None:
        self.subjects = subjects
        self.raises = raises
        self.spec_texts = spec_texts or {}
        # Story 82.8: `origin/main` is read first and best-effort; it carries
        # nothing unless a test puts a merge there, so one history is modelled.
        self.origin_subjects = origin_subjects
        self.origin_raises = origin_raises
        self.commit_subjects_calls: list[str] = []
        self.file_reads: list[tuple[str, str]] = []

    def commit_subjects(self, repo_root: Path, ref: str) -> tuple[str, ...]:
        self.commit_subjects_calls.append(ref)
        if ref == ORIGIN_MAIN:
            if self.origin_raises:
                raise VcsCommandError("fatal: bad revision 'refs/remotes/origin/main'")
            return self.origin_subjects
        if self.raises:
            raise VcsCommandError("fatal: ambiguous argument 'main': unknown revision")
        return self.subjects

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        self.file_reads.append((ref, path))
        return self.spec_texts.get(path)


def _facts(slug: str, story: str | None, findings: tuple[dict[str, object], ...]) -> FleetHomeFacts:
    return FleetHomeFacts(
        slug=slug,
        branch=f"loop/{slug}",
        has_run=False,
        dispatch_story=story,
        dispatch_engine_alive=False,
        dispatch_completion_verdict="stopped_externally",
        dispatch_landing_findings=findings,
    )


def _superseded(
    facts: FleetHomeFacts,
    vcs: _Vcs,
    repo_root: Path,
    main: status_cli._MainSubjects | None = None,
) -> bool:
    return status_cli._landing_superseded(
        facts,
        slug=facts.slug,
        main=main if main is not None else status_cli._MainSubjects(),
        vcs=vcs,
        repo_root=repo_root,
    )


# --- the status edge (cli/status.py); the pure decision's own tests live in
# test_dispatch_landing.py -------------------------------------------------


def test_doctor_30_3_refusal_is_superseded_once_pr_1585_is_on_main(tmp_path: Path) -> None:
    vcs = _Vcs((_UNRELATED[0], _DOCTOR_MERGE, _UNRELATED[1]))
    assert _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path)
    assert vcs.commit_subjects_calls == [ORIGIN_MAIN, "refs/heads/main"]


def test_marshal_46_6_refusal_is_superseded_once_pr_1597_is_on_main(tmp_path: Path) -> None:
    vcs = _Vcs((_MARSHAL_MERGE, *_UNRELATED))
    assert _superseded(_facts("pyforge-marshal", "46.6", _MARSHAL_REFUSAL), vcs, tmp_path)


def test_a_merge_only_on_origin_main_supersedes_before_local_main_catches_up(tmp_path: Path) -> None:
    """Story 82.8 (DW-FU-4-14-9): the history is `origin/main` plus `main`, as `deploy` reads it, so a merge in the
    fetch-versus-fast-forward window already counts; an unfetched `origin/main` is the ordinary case."""
    vcs = _Vcs(_UNRELATED, origin_subjects=(_DOCTOR_MERGE,))
    assert _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path)
    assert vcs.commit_subjects_calls == [ORIGIN_MAIN, "refs/heads/main"]

    unfetched = _Vcs((_DOCTOR_MERGE,), origin_raises=True)
    assert _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), unfetched, tmp_path)


def test_a_readable_origin_main_does_not_excuse_an_unreadable_local_main(tmp_path: Path) -> None:
    vcs = _Vcs(raises=True, origin_subjects=(_DOCTOR_MERGE,))
    main = status_cli._MainSubjects()
    assert not _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path, main)
    assert main.attempted and main.subjects is None


def test_a_refusal_whose_story_is_not_on_main_stays_a_refusal(tmp_path: Path) -> None:
    vcs = _Vcs(_UNRELATED)
    assert not _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path)


def test_another_stations_landing_of_the_same_number_does_not_supersede(tmp_path: Path) -> None:
    """Grammar scoping: marshal's 30.3 landing is not doctor's."""
    vcs = _Vcs(("Merge pull request #900 from rxm7706/dispatch/pyforge-marshal/30.3",))
    assert not _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path)


def test_an_unreadable_main_leaves_the_marker_off_and_keeps_the_cause(tmp_path: Path) -> None:
    vcs = _Vcs(raises=True)
    main = status_cli._MainSubjects()
    assert not _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path, main)
    assert main.attempted and main.subjects is None
    assert isinstance(main.error, VcsCommandError)


def test_a_warn_only_landing_is_never_superseded_and_reads_no_main(tmp_path: Path) -> None:
    vcs = _Vcs((_DOCTOR_MERGE,))
    assert not _superseded(_facts("pyforge-doctor", "30.3", _WARN_ONLY), vcs, tmp_path)
    assert vcs.commit_subjects_calls == []


def test_a_row_without_landing_findings_reads_no_main(tmp_path: Path) -> None:
    vcs = _Vcs((_DOCTOR_MERGE,))
    assert not _superseded(_facts("pyforge-doctor", "30.3", ()), vcs, tmp_path)
    assert not _superseded(_facts("pyforge-doctor", None, _DOCTOR_REFUSAL), vcs, tmp_path)
    assert vcs.commit_subjects_calls == []


def test_an_unparseable_story_key_is_never_superseded(tmp_path: Path) -> None:
    vcs = _Vcs((_DOCTOR_MERGE,))
    assert not _superseded(_facts("pyforge-doctor", "not a key", _DOCTOR_REFUSAL), vcs, tmp_path)
    assert vcs.commit_subjects_calls == []


def test_main_is_read_once_for_every_refused_row_in_a_sweep(tmp_path: Path) -> None:
    vcs = _Vcs((_DOCTOR_MERGE, _MARSHAL_MERGE))
    main = status_cli._MainSubjects()
    assert _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path, main)
    assert _superseded(_facts("pyforge-marshal", "46.6", _MARSHAL_REFUSAL), vcs, tmp_path, main)
    assert vcs.commit_subjects_calls == [ORIGIN_MAIN, "refs/heads/main"]


def test_a_policy_error_leaves_the_marker_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _merged_with_policy_error(slug, main_subjects, *, spec_status_for=None):
        return (
            frozenset({"30.3"}),
            (Finding(code="MRS-POLICY-004", severity=Severity.ERROR, message="unreadable project policy"),),
            1,
        )

    monkeypatch.setattr(status_cli, "_merged_keys_for_slug", _merged_with_policy_error)
    vcs = _Vcs((_DOCTOR_MERGE,))
    assert not _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path)


# A bare station branch names a key with no intent to land it (the 2026-09-18
# `doctor/27-4-mint` incident, Story 51.7 / CAP-255): it corroborates only
# when the key's tracked spec reads `done` on origin/main.
_STATION_BRANCH_MERGE = "Merge pull request #1477 from rxm7706/doctor/27-4-mint"
_SPEC_REL = "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-27-4-example.md"


def _seed_spec(repo_root: Path) -> None:
    spec = repo_root / _SPEC_REL
    spec.parent.mkdir(parents=True)
    spec.write_text("---\nstatus: 'backlog'\n---\n", encoding="utf-8")


@pytest.mark.parametrize(("status_at_origin", "expected"), [("done", True), ("backlog", False)])
def test_a_station_branch_merge_supersedes_only_when_the_spec_reads_done_on_origin_main(
    tmp_path: Path, status_at_origin: str, expected: bool
) -> None:
    _seed_spec(tmp_path)
    vcs = _Vcs((_STATION_BRANCH_MERGE,), spec_texts={_SPEC_REL: f"---\nstatus: '{status_at_origin}'\n---\n"})
    assert _superseded(_facts("pyforge-doctor", "27.4", _DOCTOR_REFUSAL), vcs, tmp_path) is expected
    assert vcs.file_reads == [("refs/remotes/origin/main", _SPEC_REL)]


def test_the_spec_reader_answers_only_for_the_rows_own_key(tmp_path: Path) -> None:
    """Another key's station-branch merge is never looked up -- only this
    row's membership is asked about."""
    _seed_spec(tmp_path)
    vcs = _Vcs((_STATION_BRANCH_MERGE,), spec_texts={_SPEC_REL: "---\nstatus: 'done'\n---\n"})
    assert not _superseded(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), vcs, tmp_path)
    assert vcs.file_reads == []


# --- Story 73.1 (CAP-281): a follow-up review's story is on main from its FIRST landing ------------------

_LAUNCH_TIP = "1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d"
_TIP_RANGE = f"{_LAUNCH_TIP}..refs/remotes/origin/main"
_FOLLOWUP = FollowupReview(dw_id="DW-FRR-30-3", launch_origin_main_sha=_LAUNCH_TIP)


class _RangeVcs(_Vcs):
    """Answers per ref: the whole local ``main`` carries the story's first merge; the launch-tip range carries
    the run's own merge only when ``own_merge``."""

    def __init__(self, *, own_merge: bool = False, range_raises: bool = False) -> None:
        super().__init__((_DOCTOR_MERGE,))
        self.own_merge = own_merge
        self.range_raises = range_raises

    def commit_subjects(self, repo_root: Path, ref: str) -> tuple[str, ...]:
        self.commit_subjects_calls.append(ref)
        if ref == _TIP_RANGE:
            if self.range_raises:
                raise VcsCommandError("fatal: bad revision (test double)")
            return (_DOCTOR_MERGE,) if self.own_merge else ()
        if ref == ORIGIN_MAIN:
            return ()
        return (_DOCTOR_MERGE,)


def _followup_facts(followup_review: FollowupReview | None) -> FleetHomeFacts:
    return replace(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL), dispatch_followup_review=followup_review)


def test_a_follow_up_refusal_is_not_superseded_by_the_stories_first_landing(tmp_path: Path) -> None:
    """Story 30.3 is on `main` from its first landing, so the whole-`main` read would mark the refused
    REVIEW landing superseded; only the launch-tip range can say the review itself landed."""
    vcs = _RangeVcs()
    main = status_cli._MainSubjects()

    assert not _superseded(_followup_facts(_FOLLOWUP), vcs, tmp_path, main)
    assert vcs.commit_subjects_calls == [_TIP_RANGE]
    assert not main.attempted  # the sweep's shared whole-`main` read is never taken for this row


def test_a_follow_up_refusal_is_superseded_once_its_own_merge_reaches_origin_main(tmp_path: Path) -> None:
    vcs = _RangeVcs(own_merge=True)

    assert _superseded(_followup_facts(_FOLLOWUP), vcs, tmp_path)
    assert vcs.commit_subjects_calls == [_TIP_RANGE]


def test_the_same_refusal_without_the_marker_is_still_superseded_by_the_stories_merge(tmp_path: Path) -> None:
    vcs = _RangeVcs()

    assert _superseded(_followup_facts(None), vcs, tmp_path)
    assert vcs.commit_subjects_calls == [ORIGIN_MAIN, "refs/heads/main"]


def test_a_follow_up_refusal_with_no_recorded_tip_is_never_superseded_and_reads_nothing(tmp_path: Path) -> None:
    vcs = _RangeVcs(own_merge=True)

    assert not _superseded(_followup_facts(FollowupReview(dw_id="DW-FRR-30-3")), vcs, tmp_path)
    assert vcs.commit_subjects_calls == []


def test_an_unreadable_launch_tip_range_leaves_a_follow_up_refusal_actionable(tmp_path: Path) -> None:
    vcs = _RangeVcs(own_merge=True, range_raises=True)

    assert not _superseded(_followup_facts(_FOLLOWUP), vcs, tmp_path)
    assert vcs.commit_subjects_calls == [_TIP_RANGE]


# --- the JSON row (core/status.py) -------------------------------------------


def test_the_row_carries_the_marker_beside_unchanged_findings() -> None:
    plain, _ = build_fleet_row(_facts("pyforge-doctor", "30.3", _DOCTOR_REFUSAL))
    marked_facts = FleetHomeFacts(
        slug="pyforge-doctor",
        branch="loop/pyforge-doctor",
        has_run=False,
        dispatch_story="30.3",
        dispatch_engine_alive=False,
        dispatch_completion_verdict="stopped_externally",
        dispatch_landing_findings=_DOCTOR_REFUSAL,
        dispatch_landing_superseded=True,
    )
    marked, _ = build_fleet_row(marked_facts)
    assert "dispatch_landing_superseded" not in plain
    assert marked["dispatch_landing_superseded"] is True
    assert marked["dispatch_landing_findings"] == plain["dispatch_landing_findings"] == list(_DOCTOR_REFUSAL)
    assert {k: v for k, v in marked.items() if k != "dispatch_landing_superseded"} == plain


def test_the_row_names_the_dispatch_story_when_current_story_does_not() -> None:
    """Review 1 (medium): a run whose completion reads `completed` keeps the
    loop home's `current_story` (here none), so the landing's story travels
    on the row as `dispatch_story`."""
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="46.6",
        dispatch_engine_alive=False,
        dispatch_completion_verdict="completed",
        dispatch_landing_findings=_MARSHAL_REFUSAL,
        dispatch_landing_superseded=True,
    )
    row, _ = build_fleet_row(facts)
    assert row["dispatch_story"] == "46.6"
    assert row.get("current_story") != "46.6"
    assert row["dispatch_landing_superseded"] is True
