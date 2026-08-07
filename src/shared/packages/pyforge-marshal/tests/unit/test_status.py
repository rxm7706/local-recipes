"""Unit tests for ``pyforge.marshal.core.status`` (Story 1.6, FR-4/FR-8,
AD-4) -- ``evaluate_homes``'s pure isolation-check logic driven entirely by
plain ``HomeFacts``/``MainCheckoutFacts`` objects (no ports, no I/O; that
lives in ``cli/init.py::run_homes`` and its own tests). Covers every row of
the spec's I/O & Edge-Case Matrix.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import spin as spin_module
from pyforge.marshal.cli import status as status_cli
from pyforge.marshal.core import status
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.journal import (
    JournalEntryId,
    Phase,
    build_entry,
    prepare_for_write,
)
from pyforge.marshal.core.model import Severity
from pyforge.marshal.ports.harness import RunStatusSnapshot, TaskPhaseSnapshot
from pyforge.marshal.ports.process import ProcessResult
from pyforge.marshal.ports.vcs import WorktreeEntry

_CANONICAL = Path("/repo/_bmad-output/projects/acme/implementation-artifacts")

# A fixed "now" for Story 5.1's `_FakeClock` -- any test that seeds a real
# run-launch journal entry needs a real datetime to subtract against (an
# `elapsed_seconds` computation only ever runs when a launch timestamp was
# actually recovered); tests with no run at all never engage it.
_FIXED_NOW = datetime(2026, 8, 6, 0, 30, 0, tzinfo=timezone.utc)


def _home(
    *,
    path: Path = Path("/loop-homes/acme"),
    branch: str = "loop/acme",
    marker: str | None = None,
    symlink: Path | None = None,
    tier3_local: Path | None = None,
    tier3_canonical: Path = _CANONICAL,
    link_occupied: bool = False,
    tier3_canonical_is_dir: bool = True,
) -> status.HomeFacts:
    return status.HomeFacts(
        path=path,
        branch=branch,
        marker_text=marker,
        symlink_target=symlink,
        tier3_local_realpath=tier3_local,
        tier3_canonical_realpath=tier3_canonical,
        link_occupied=link_occupied,
        tier3_canonical_is_dir=tier3_canonical_is_dir,
    )


def _main(
    *,
    path: Path = Path("/repo"),
    branch: str | None = "main",
    marker: str | None = None,
    symlink: Path | None = None,
    link_occupied: bool = False,
) -> status.MainCheckoutFacts:
    return status.MainCheckoutFacts(
        path=path,
        branch=branch,
        marker_text=marker,
        symlink_target=symlink,
        link_occupied=link_occupied,
    )


_CLEAN_MAIN = _main()


# --- HomeFacts invariant ---------------------------------------------------------


def test_home_facts_rejects_a_non_loop_branch():
    with pytest.raises(ValueError, match="loop/"):
        status.HomeFacts(
            path=Path("/x"),
            branch="main",
            marker_text=None,
            symlink_target=None,
            tier3_local_realpath=None,
            tier3_canonical_realpath=Path("/y"),
        )


# --- two clean homes: exit-0, no findings -----------------------------------------


def test_two_clean_homes_are_not_desynced():
    acme_canonical = Path("/repo/_bmad-output/projects/acme/implementation-artifacts")
    beta_canonical = Path("/repo/_bmad-output/projects/beta/implementation-artifacts")
    acme = _home(
        path=Path("/loop-homes/acme"),
        branch="loop/acme",
        marker="acme\n",
        symlink=Path("projects/acme/planning-artifacts"),
        tier3_local=acme_canonical,
        tier3_canonical=acme_canonical,
    )
    beta = _home(
        path=Path("/loop-homes/beta"),
        branch="loop/beta",
        marker="beta\n",
        symlink=Path("projects/beta/planning-artifacts"),
        tier3_local=beta_canonical,
        tier3_canonical=beta_canonical,
    )
    result = status.evaluate_homes((acme, beta), _CLEAN_MAIN)
    assert result.findings == ()
    assert [row["desynced"] for row in result.homes] == [False, False]
    assert result.main_checkout["desynced"] is False
    assert [row["slug"] for row in result.homes] == ["acme", "beta"]
    assert [row["active_project"] for row in result.homes] == ["acme", "beta"]


# --- marker/symlink desync: MRS-HOMES-001 -----------------------------------------


def test_home_marker_symlink_desync_reports_mrs_homes_001():
    home = _home(
        marker="other-project\n",
        symlink=Path("projects/yet-another/planning-artifacts"),
        tier3_local=_CANONICAL,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-001"
    assert finding.severity is Severity.ERROR
    assert str(home.path) in finding.path
    assert "other-project" in finding.message
    assert "yet-another" in finding.message
    assert result.homes[0]["desynced"] is True


# --- the blind spot: agrees with itself but not its own branch --------------------


def test_home_agrees_with_itself_but_not_branch_reports_mrs_homes_001():
    """Closes the deferred-work blind spot: MRS-INIT-003's own two-way check
    would treat this as clean (marker == symlink), but the home's directory
    is keyed by loop/bar, not the foo both agree on."""
    home = _home(
        branch="loop/bar",
        marker="foo\n",
        symlink=Path("projects/foo/planning-artifacts"),
        tier3_local=_CANONICAL,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-001"
    assert "foo" in finding.message
    assert "bar" in finding.message
    row = result.homes[0]
    assert row["slug"] == "bar"  # branch-derived, never the marker/symlink value
    assert row["active_project"] == "foo"
    assert row["desynced"] is True


def test_marker_alone_present_and_matching_branch_is_not_a_violation():
    """A legitimately partial provision (interrupted before the symlink
    step) always agrees with the branch by construction -- not a violation."""
    home = _home(marker="acme\n", symlink=None, tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert result.findings == ()
    row = result.homes[0]
    assert row["active_project"] == "acme"
    assert row["desynced"] is False


def test_marker_alone_present_and_disagreeing_with_branch_is_a_violation():
    """Unlike MRS-INIT-003's own two-way rule (which requires BOTH marker
    and symlink present before comparing), the branch is ALWAYS known, so a
    single divergent field is itself real evidence of tampering."""
    home = _home(branch="loop/acme", marker="rogue\n", symlink=None, tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    assert result.findings[0].code == "MRS-HOMES-001"
    assert "rogue" in result.findings[0].message
    assert result.homes[0]["desynced"] is True


def test_unrecognized_symlink_shape_is_a_violation():
    """Ported from cli/init.py's own MRS-INIT-003: a symlink target that
    EXISTS but doesn't parse as projects/<slug>/planning-artifacts is
    evidence of hand configuration, reported on its own."""
    home = _home(marker=None, symlink=Path("/somewhere/else"), tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    assert result.findings[0].code == "MRS-HOMES-001"
    assert "unrecognized" in result.findings[0].message


def test_occupied_planning_artifacts_is_a_violation():
    """A real (non-symlink) occupant at the planning-artifacts path is one
    step further gone than an unrecognized symlink target -- previously it
    read as benign absence (review finding)."""
    home = _home(marker="acme\n", symlink=None, link_occupied=True, tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    assert result.findings[0].code == "MRS-HOMES-001"
    assert "occupied" in result.findings[0].message
    assert result.homes[0]["desynced"] is True


def test_all_three_slugs_disagreeing_names_every_pair():
    """The multi-corruption case (review finding): with marker, symlink,
    and branch all pairwise disagreeing, the finding must name EVERY
    disagreeing value, not just the first pair."""
    home = _home(
        branch="loop/zeta",
        marker="alpha\n",
        symlink=Path("projects/beta/planning-artifacts"),
        tier3_local=None,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    message = result.findings[0].message
    assert "alpha" in message
    assert "beta" in message
    assert "zeta" in message


# --- Tier-3 realpath mismatch: MRS-HOMES-002 --------------------------------------


def test_tier3_realpath_mismatch_reports_mrs_homes_002():
    home = _home(
        marker="acme\n",
        symlink=Path("projects/acme/planning-artifacts"),
        tier3_local=Path("/somewhere/else"),
        tier3_canonical=_CANONICAL,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-002"
    assert "/somewhere/else" in finding.message
    assert str(_CANONICAL) in finding.message
    assert result.homes[0]["desynced"] is True


def test_tier3_and_slug_mismatch_both_fire_independently():
    home = _home(
        marker="other\n",
        symlink=Path("projects/yet-another/planning-artifacts"),
        tier3_local=Path("/somewhere/else"),
        tier3_canonical=_CANONICAL,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    codes = [finding.code for finding in result.findings]
    assert codes == ["MRS-HOMES-001", "MRS-HOMES-002"]
    assert result.homes[0]["desynced"] is True


def test_unprovisioned_tier3_backlink_is_not_a_violation():
    home = _home(marker="acme\n", symlink=Path("projects/acme/planning-artifacts"), tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert result.findings == ()
    assert result.homes[0]["desynced"] is False


def test_backlink_dangling_at_the_canonical_path_is_a_violation():
    """The backlink resolves to the RIGHT path, but the canonical store
    itself is gone (review finding: previously blessed as clean) -- marshal
    init's own convergence check has always required is_dir(canonical)."""
    home = _home(
        marker="acme\n",
        symlink=Path("projects/acme/planning-artifacts"),
        tier3_local=_CANONICAL,
        tier3_canonical=_CANONICAL,
        tier3_canonical_is_dir=False,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-002"
    assert "does not exist" in finding.message
    assert result.homes[0]["desynced"] is True


def test_missing_canonical_store_without_a_backlink_is_not_a_violation():
    """The dangling-backlink check only applies when a backlink exists --
    an unprovisioned home whose canonical store also doesn't exist yet is
    still just 'never provisioned'."""
    home = _home(marker="acme\n", symlink=Path("projects/acme/planning-artifacts"), tier3_local=None, tier3_canonical_is_dir=False)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert result.findings == ()
    assert result.homes[0]["desynced"] is False


# --- main checkout: two-way check, same code --------------------------------------


def test_main_checkout_desync_reports_mrs_homes_001_naming_main():
    main = _main(marker="other\n", symlink=Path("projects/elsewhere/planning-artifacts"))
    home = _home(marker="acme\n", symlink=Path("projects/acme/planning-artifacts"), tier3_local=_CANONICAL)
    result = status.evaluate_homes((home,), main)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-001"
    assert str(main.path) in finding.path
    assert "main checkout" in finding.message
    assert result.main_checkout["desynced"] is True
    assert result.homes[0]["desynced"] is False  # unaffected


def test_main_checkout_untouched_is_self_consistent():
    """'Untouched' == both absent, matching the spec's own framing: there is
    no stored baseline, only self-consistency at invocation time."""
    result = status.evaluate_homes((), _CLEAN_MAIN)
    assert result.findings == ()
    assert result.main_checkout == {
        "path": str(_CLEAN_MAIN.path),
        "branch": "main",
        "slug": None,
        "active_project": None,
        "desynced": False,
    }


def test_main_checkout_marker_alone_present_is_not_a_violation():
    """The main checkout has no branch-derived third leg -- a single
    present field is a benign partial state, exactly MRS-INIT-003's own
    two-way rule."""
    main = _main(marker="acme\n", symlink=None)
    result = status.evaluate_homes((), main)
    assert result.findings == ()
    assert result.main_checkout["desynced"] is False


def test_main_checkout_occupied_planning_artifacts_is_a_violation():
    """Same occupancy rule as a home's (review finding): a real directory
    materialized at the main checkout's planning-artifacts path is named,
    never read as 'symlink absent'."""
    main = _main(marker=None, symlink=None, link_occupied=True)
    result = status.evaluate_homes((), main)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-001"
    assert "main checkout" in finding.message
    assert "occupied" in finding.message
    assert result.main_checkout["desynced"] is True


# --- zero/one home -----------------------------------------------------------------


def test_zero_homes_reports_empty_homes_and_the_main_checkout():
    result = status.evaluate_homes((), _CLEAN_MAIN)
    assert result.homes == ()
    assert result.main_checkout["path"] == str(_CLEAN_MAIN.path)


def test_one_home_reports_a_single_row():
    home = _home(marker="acme\n", symlink=Path("projects/acme/planning-artifacts"), tier3_local=_CANONICAL)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.homes) == 1
    assert result.findings == ()


# --- finding ordering: homes (in order), then main checkout -----------------------


def test_findings_are_ordered_homes_then_main_checkout():
    desynced_home = _home(
        path=Path("/loop-homes/acme"),
        branch="loop/acme",
        marker="other\n",
        symlink=Path("projects/yet-another/planning-artifacts"),
        tier3_local=_CANONICAL,
    )
    desynced_main = _main(marker="x\n", symlink=Path("projects/y/planning-artifacts"))
    result = status.evaluate_homes((desynced_home,), desynced_main)
    assert [f.path for f in result.findings] == [
        str(desynced_home.path),
        str(desynced_main.path),
    ]


# --- drift guard: this module's private slug-parsing helpers must stay -----
# byte-identical to cli/init.py's own copies (this module's docstring
# explains WHY they are duplicated rather than imported -- core/ never
# imports from cli/). A silent divergence between the two would make
# `marshal homes` and `marshal init` disagree about what counts as a valid
# symlink/marker shape (review finding: no test previously proved this).


def test_slug_from_marker_matches_cli_init_copy():
    from pyforge.marshal.cli import init as init_cli

    for value in (None, "", "  ", "acme", "  acme  \n", "acme\n"):
        assert status._slug_from_marker(value) == init_cli._slug_from_marker(value)


def test_slug_from_symlink_target_matches_cli_init_copy():
    from pyforge.marshal.cli import init as init_cli

    for target in (
        None,
        Path("projects/acme/planning-artifacts"),
        Path("/absolute/projects/acme/planning-artifacts"),
        Path("projects/acme/other-artifacts"),
        Path("wrong/depth"),
        Path("projects/acme/nested/planning-artifacts"),
    ):
        assert status._slug_from_symlink_target(
            target
        ) == init_cli._slug_from_symlink_target(target)


# =============================================================================
# Story 4.5: DomainField / reconcile_feed_domains / classify_resync_outcome
# (AD-33) -- covers every row of the spec's I/O & Edge-Case Matrix.
# =============================================================================


def test_domain_field_rejects_an_unrecognized_domain():
    with pytest.raises(ValueError, match="git.*journal"):
        status.DomainField(value=True, domain="repo")  # type: ignore[arg-type]


def test_domain_field_to_dict_round_trips():
    field = status.DomainField(value=42, domain="journal")
    assert status.domain_field_to_dict(field) == {"value": 42, "domain": "journal"}


def test_reconcile_claimed_commit_matching_merged_keys_is_no_finding():
    key = normalize("1.2")
    report = status.reconcile_feed_domains(
        frozenset({key}),
        (status.ClaimedCommit(story_key=key, claimed_commit_sha="deadbeef"),),
    )
    assert report.findings == ()
    assert len(report.stories) == 1
    row = report.stories[0]
    assert row["story_key"] == "1.2"
    assert row["durable"] == status.DomainField(value=True, domain="git")
    assert row["claimed_commit_sha"] == status.DomainField(
        value="deadbeef", domain="journal"
    )


def test_reconcile_claimed_commit_not_in_merged_keys_is_mrs_status_001():
    """The harness claims a commit landed; git's own merged_story_keys
    disagrees -- reported, never resolved either way (AD-33)."""
    key = normalize("2.1")
    report = status.reconcile_feed_domains(
        frozenset(),
        (status.ClaimedCommit(story_key=key, claimed_commit_sha="cafebabe"),),
    )
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.code == "MRS-STATUS-001"
    assert finding.severity is Severity.WARN
    assert "2.1" in finding.message
    assert "cafebabe" in finding.message
    row = report.stories[0]
    # `durable` (git) is never overridden by the journal's claim.
    assert row["durable"].value is False
    assert row["claimed_commit_sha"].value == "cafebabe"


def test_reconcile_claimed_commit_none_is_no_finding_git_stands_alone():
    key = normalize("3.1")
    report = status.reconcile_feed_domains(frozenset({key}), (
        status.ClaimedCommit(story_key=key, claimed_commit_sha=None),
    ))
    assert report.findings == ()
    row = report.stories[0]
    assert row["durable"].value is True
    assert row["claimed_commit_sha"].value is None


def test_reconcile_empty_state_is_clean():
    report = status.reconcile_feed_domains(frozenset(), ())
    assert report.stories == ()
    assert report.findings == ()


def test_reconcile_every_field_is_tagged_with_its_own_domain():
    key = normalize("4.5")
    report = status.reconcile_feed_domains(
        frozenset({key}),
        (status.ClaimedCommit(story_key=key, claimed_commit_sha="sha1"),),
    )
    row = report.stories[0]
    assert row["durable"].domain == "git"
    assert row["claimed_commit_sha"].domain == "journal"


def test_reconcile_is_sorted_deterministically_for_the_noop_property():
    keys = [normalize(k) for k in ("3.1", "1.2", "2.4")]
    report = status.reconcile_feed_domains(frozenset(keys), ())
    assert [row["story_key"] for row in report.stories] == ["1.2", "2.4", "3.1"]


def test_reconcile_duplicate_story_key_prefers_later_phase_non_none_sha():
    """Code review (2026-08-06, P3, Edge Case Hunter): two
    ``TaskPhaseSnapshot``-derived claims for the SAME story key (a real
    shape -- dev/review/done-phase snapshots of one task) must resolve by
    an explicit, deterministic precedence, never by which happened to be
    LAST in a dict comprehension's own iteration order."""
    key = normalize("5.1")
    earlier = status.ClaimedCommit(
        story_key=key, claimed_commit_sha="earliersha", phase="review-verify"
    )
    later = status.ClaimedCommit(
        story_key=key, claimed_commit_sha="donesha", phase="done"
    )
    # Feed them in BOTH orders -- the result must not depend on input order.
    report_forward = status.reconcile_feed_domains(frozenset({key}), (earlier, later))
    report_reverse = status.reconcile_feed_domains(frozenset({key}), (later, earlier))
    assert report_forward.stories[0]["claimed_commit_sha"].value == "donesha"
    assert report_reverse.stories[0]["claimed_commit_sha"].value == "donesha"


def test_reconcile_duplicate_story_key_prefers_non_none_sha_over_none():
    key = normalize("5.2")
    no_claim = status.ClaimedCommit(story_key=key, claimed_commit_sha=None, phase="done")
    has_claim = status.ClaimedCommit(
        story_key=key, claimed_commit_sha="sha123", phase="dev-running"
    )
    report = status.reconcile_feed_domains(frozenset({key}), (no_claim, has_claim))
    assert report.stories[0]["claimed_commit_sha"].value == "sha123"


# --- classify_resync_outcome -------------------------------------------------


def test_classify_resync_outcome_never_ran_reports_mrs_deploy_019():
    report, finding = status.classify_resync_outcome(
        "echo hi", None, failure_reason="could not launch"
    )
    assert report == {"command": "echo hi", "resolvable": False, "returncode": None}
    assert finding.code == "MRS-DEPLOY-019"
    assert finding.severity is Severity.ERROR
    assert "could not launch" in finding.message


def test_classify_resync_outcome_nonzero_exit_reports_mrs_deploy_020():
    result = ProcessResult(returncode=1, stdout="", stderr="boom")
    report, finding = status.classify_resync_outcome("false", result)
    assert report["resolvable"] is True
    assert report["returncode"] == 1
    assert finding.code == "MRS-DEPLOY-020"
    assert "exited 1" in finding.message


def test_classify_resync_outcome_signal_kill_names_the_signal():
    result = ProcessResult(returncode=-9, stdout="", stderr="")
    _, finding = status.classify_resync_outcome("cmd", result)
    assert "terminated by signal 9" in finding.message


def test_classify_resync_outcome_success_is_no_finding():
    result = ProcessResult(returncode=0, stdout="ok", stderr="")
    report, finding = status.classify_resync_outcome("true", result)
    assert finding is None
    assert report == {
        "command": "true",
        "resolvable": True,
        "returncode": 0,
        "stdout": "ok",
        "stderr": "",
    }


# =============================================================================
# Story 5.1: derive_home_state / build_fleet_row (`marshal status`,
# FR-36/AD-5) -- covers every row of the spec's I/O & Edge-Case Matrix.
# =============================================================================


def _task(story_key: str = "1.1", phase: str = "dev-running") -> TaskPhaseSnapshot:
    return TaskPhaseSnapshot(
        story_key=story_key, phase=phase, commit_sha=None, branch=""
    )


class TestDeriveHomeState:
    def test_dead_supervisor_on_unfinished_run_is_unsupervised_regardless_of_journal(
        self,
    ):
        """The AC's own unconditional wording: a journal that still claims
        'running'/'paused' is exactly the stale state a crashed supervisor
        leaves behind -- liveness overrides it."""
        state = status.derive_home_state(
            finished=False,
            paused_stage="escalation",
            tasks=(_task(phase="dev-running"),),
            supervisor_alive=False,
        )
        assert state == "unsupervised"

    def test_finished_run_is_stopped_even_if_supervisor_already_exited(self):
        """A finished run's own supervisor sidecar naturally exits once its
        watched harness process does -- liveness is never consulted once
        finished is True."""
        state = status.derive_home_state(
            finished=True, paused_stage=None, tasks=(), supervisor_alive=False
        )
        assert state == "stopped"

    def test_paused_on_escalation(self):
        state = status.derive_home_state(
            finished=False,
            paused_stage="escalation",
            tasks=(),
            supervisor_alive=True,
        )
        assert state == "paused-on-escalation"

    def test_non_escalation_pause_stage_is_not_paused_on_escalation(self):
        state = status.derive_home_state(
            finished=False,
            paused_stage="spec-approval",
            tasks=(),
            supervisor_alive=True,
        )
        assert state != "paused-on-escalation"

    def test_in_flight_task_is_running_and_names_that_story(self):
        tasks = (
            _task(story_key="1.1", phase="done"),
            _task(story_key="1.2", phase="dev-running"),
        )
        state = status.derive_home_state(
            finished=False, paused_stage=None, tasks=tasks, supervisor_alive=True
        )
        assert state == "running"

    def test_deferred_task_alone_is_not_running(self):
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(_task(phase="deferred"),),
            supervisor_alive=True,
        )
        assert state == "idle"

    def test_every_task_done_is_idle(self):
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(_task(phase="done"),),
            supervisor_alive=True,
        )
        assert state == "idle"

    def test_no_tasks_at_all_is_idle(self):
        state = status.derive_home_state(
            finished=False, paused_stage=None, tasks=(), supervisor_alive=True
        )
        assert state == "idle"

    def test_supervisor_alive_none_never_triggers_unsupervised(self):
        """A caller with no pid to probe never reaches this function with a
        real pid absent (it degrades to journal_unreadable instead) -- but
        the pure function itself must not misreport an unknown liveness as
        a crash."""
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(_task(phase="dev-running"),),
            supervisor_alive=None,
        )
        assert state == "running"


class TestBuildFleetRow:
    def test_no_run_yet_is_idle_no_finding(self):
        facts = status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=False)
        row, finding = status.build_fleet_row(facts)
        assert row == {
            "slug": "acme",
            "branch": "loop/acme",
            "state": "idle",
            "current_story": None,
            "elapsed_seconds": None,
            "budget_consumed": None,
        }
        assert finding is None

    def test_journal_unreadable_reports_unknown_and_warns(self):
        facts = status.FleetHomeFacts(
            slug="acme", branch="loop/acme", has_run=True, journal_unreadable=True
        )
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "unknown"
        assert row["current_story"] is None
        assert finding is not None
        assert finding.code == "MRS-STATUS-002"
        assert finding.severity is Severity.WARN
        assert "acme" in finding.message

    def test_running_run_reports_current_story_elapsed_and_budget(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            paused_stage=None,
            tasks=(_task(story_key="1.1", phase="dev-running"),),
            supervisor_alive=True,
            elapsed_seconds=42.5,
            budget_consumed=1234,
        )
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "running"
        assert row["current_story"] == "1.1"
        assert row["elapsed_seconds"] == 42.5
        assert row["budget_consumed"] == 1234
        assert finding is None

    def test_no_budget_relevant_entry_reports_null_not_an_error(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=True,
            supervisor_alive=True,
        )
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "stopped"
        assert row["budget_consumed"] is None
        assert finding is None


# =============================================================================
# Story 5.1: `cli/status.py`'s ``run_status`` -- I/O matrix, fake VcsPort/
# HarnessPort/ProcessPort/ClockPort doubles (mirrors ``test_retire.py``'s
# established shape); real ``LocalFs`` against a REAL ``tmp_path`` journal
# file, same as every ``cli/deploy.py``/``cli/retire.py`` test.
# =============================================================================


class _FakeVcs:
    def __init__(
        self,
        *,
        repo_root_value: Path = Path("/fake-repo-root"),
        worktrees: tuple[WorktreeEntry, ...] = (),
        worktrees_raise: bool = False,
    ) -> None:
        self.repo_root_value = repo_root_value
        self.worktrees = worktrees
        self.worktrees_raise = worktrees_raise

    def repo_common_root(self, start):
        return self.repo_root_value

    def list_worktrees(self, repo_root):
        if self.worktrees_raise:
            raise VcsCommandError("git worktree list failed")
        return self.worktrees


class _FakeHarness:
    """Keyed by ``(str(project), run_id)`` -- mirrors ``test_retire.py::
    _FakeHarness``'s own convention, widened by ``run_id`` since this
    command may resolve a distinct ``harness_run_id`` per project."""

    def __init__(
        self, snapshots: dict[tuple[str, str], RunStatusSnapshot | None] | None = None
    ) -> None:
        self.snapshots = snapshots or {}
        self.calls: list[tuple[str, str]] = []

    def run_status_snapshot(self, project, run_id):
        self.calls.append((str(project), run_id))
        return self.snapshots.get((str(project), run_id))


class _FakeProcess:
    def __init__(self, alive_pids: frozenset[int] = frozenset()) -> None:
        self.alive_pids = alive_pids
        self.calls: list[int] = []

    def is_alive(self, pid: int) -> bool:
        self.calls.append(pid)
        return pid in self.alive_pids


class _FakeClock:
    def __init__(self, now):
        self._now = now

    def now(self):
        return self._now

    def monotonic(self) -> float:
        return 0.0


def _args(*, project: str | None = None, format: str = "json"):
    return argparse.Namespace(project=project, format=format)


def _payload(capsys):
    return json.loads(capsys.readouterr().out)


def _outcome_line(
    run_id: str,
    *,
    pid: int | None,
    harness_run_id: str | None,
    ts: str = "2026-08-06T00:00:00.000Z",
) -> str:
    """A minimal, valid ``phase: outcome`` ``run-launch`` journal line --
    the SAME shape ``cli/spin.py`` itself journals (``{"pid": ...,
    "harness_run_id": ...}``). Mirrors ``test_spin.py::_outcome_line``'s
    identical shape."""
    entry = build_entry(
        id=JournalEntryId("spin-1", 1),
        ts=ts,
        run_id=run_id,
        kind="run-launch",
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("spin-1", 0),
        payload={"pid": pid, "harness_run_id": harness_run_id},
    )
    return prepare_for_write(entry).line


def _supervisor_attach_line(
    run_id: str, *, pid: int, ts: str = "2026-08-06T00:00:30.000Z"
) -> str:
    """A minimal, valid ``"supervisor-attach"`` journal line -- the SAME
    shape ``supervisor/__main__.py`` itself journals (``{"pid": ...,
    "watched_pid": ...}``). Code review (2026-08-07, Blind Hunter): this is
    the SUPERVISOR SIDECAR's own pid, a genuinely different process than
    ``_outcome_line``'s ``run-launch`` pid (the detached harness process)
    -- every test exercising the supervisor-liveness override must journal
    this SEPARATELY, never reuse the launch pid, or the test cannot
    distinguish "reads the right pid" from "reads a coincidentally
    identical wrong one"."""
    entry = build_entry(
        id=JournalEntryId("supervisor-1", 1),
        ts=ts,
        run_id=run_id,
        kind="supervisor-attach",
        phase=Phase.OBSERVATION,
        payload={"pid": pid, "watched_pid": 4242},
    )
    return prepare_for_write(entry).line


def _budget_usage_line(
    run_id: str, *, cost_estimate: int, ts: str = "2026-08-06T00:05:00.000Z"
) -> str:
    entry = build_entry(
        id=JournalEntryId("supervisor-1", 1),
        ts=ts,
        run_id=run_id,
        kind="budget-usage",
        phase=Phase.OBSERVATION,
        payload={"story_key": "1.1", "cost_estimate": cost_estimate},
    )
    return prepare_for_write(entry).line


def _seed_run_journal(tmp_path: Path, *, run_id: str, lines: list[str]) -> Path:
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_dir


def _stub_latest_run_dir(monkeypatch, run_dir_map: dict[str, Path | None]) -> None:
    """Stubs ONLY ``cli/spin.py``'s own ``_latest_run_dir`` -- the SAME
    per-module-attribute patching ``test_retire.py::_stub_run_discovery``
    establishes (``cli/status.py`` imports it LOCALLY inside ``run_status``,
    so the live function is re-resolved off ``spin_module`` at call time).
    ``_resolve_harness_run_id_for_resume`` stays REAL: it reads the SAME
    real journal file ``cli/status.py``'s own journal-fold logic reads,
    proving both read paths agree on one real file rather than two
    independently-stubbed answers."""

    def _latest_run_dir(home, slug):
        return run_dir_map.get(slug)

    monkeypatch.setattr(spin_module, "_latest_run_dir", _latest_run_dir)


def _snapshot(
    *,
    finished: bool = False,
    paused_stage: str | None = None,
    tasks: tuple[TaskPhaseSnapshot, ...] = (),
) -> RunStatusSnapshot:
    return RunStatusSnapshot(
        paused_stage=paused_stage,
        paused_story_key=None,
        paused_reason=None,
        escalated_spec_file=None,
        escalated_task_phase=None,
        deferred=(),
        finished=finished,
        tasks=tasks,
    )


class TestRunStatus:
    def test_no_loop_homes_is_a_clean_noop(self, capsys):
        vcs = _FakeVcs(worktrees=())
        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"]["homes"] == []
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_project_naming_a_nonexistent_project_is_a_clean_noop(self, capsys):
        home = Path("/loop-homes/acme")
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        exit_code = status_cli.run_status(
            _args(project="no-such-project"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"]["homes"] == []
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_fleet_worktree_listing_failure_reports_warn(self, capsys):
        vcs = _FakeVcs(worktrees_raise=True)
        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-002" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_home_with_no_run_yet_is_idle(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert len(payload["data"]["homes"]) == 1
        row = payload["data"]["homes"][0]
        assert row["state"] == "idle"
        assert row["current_story"] is None
        assert row["elapsed_seconds"] is None
        assert row["budget_consumed"] is None
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_home_with_running_supervisor_and_in_flight_task_is_running(
        self, tmp_path, capsys, monkeypatch
    ):
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[
                _outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
                # A DIFFERENT pid than the launch line's -- the supervisor
                # sidecar is a separate process (code review, 2026-08-07,
                # Blind Hunter). `alive_pids` below checks the SUPERVISOR's
                # own pid, never the launch pid.
                _supervisor_attach_line("acme-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={
                (str(home), "hrid-1"): _snapshot(
                    finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),)
                )
            }
        )
        process = _FakeProcess(alive_pids=frozenset({5252}))
        clock = _FakeClock(now=datetime(2026, 8, 6, 0, 10, 0, tzinfo=timezone.utc))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=clock,
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["state"] == "running"
        assert row["current_story"] == "1.1"
        assert row["elapsed_seconds"] == pytest.approx(600.0)
        assert exit_code == 0

    def test_home_paused_on_escalation(self, tmp_path, capsys, monkeypatch):
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[
                _outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
                _supervisor_attach_line("acme-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={(str(home), "hrid-1"): _snapshot(paused_stage="escalation")}
        )
        process = _FakeProcess(alive_pids=frozenset({5252}))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["homes"][0]["state"] == "paused-on-escalation"
        assert exit_code == 0

    def test_home_whose_run_finished_is_stopped(self, tmp_path, capsys, monkeypatch):
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[_outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1")],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={(str(home), "hrid-1"): _snapshot(finished=True)}
        )
        # Supervisor already exited -- must NOT report unsupervised.
        process = _FakeProcess(alive_pids=frozenset())

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["homes"][0]["state"] == "stopped"
        assert exit_code == 0

    def test_home_with_dead_supervisor_is_unsupervised(
        self, tmp_path, capsys, monkeypatch
    ):
        """The supervisor pid (5252) is journaled and dead while the
        DIFFERENT harness/launch pid (4242) is alive -- code review,
        2026-08-07, Blind Hunter's own worked scenario for the bug this
        test now actually exercises: a crashed supervisor with the watched
        harness process still running must still report `unsupervised`."""
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[
                _outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
                _supervisor_attach_line("acme-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={
                (str(home), "hrid-1"): _snapshot(
                    finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),)
                )
            }
        )
        # 4242 (the harness) is alive; 5252 (the supervisor) is NOT.
        process = _FakeProcess(alive_pids=frozenset({4242}))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["homes"][0]["state"] == "unsupervised"
        assert exit_code == 0

    def test_missing_journal_reports_unknown_and_warns(
        self, tmp_path, capsys, monkeypatch
    ):
        run_dir = tmp_path / "runs" / "acme-run1"
        run_dir.mkdir(parents=True)  # no journal.jsonl written at all
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["state"] == "unknown"
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-002" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_malformed_journal_no_recoverable_pid_reports_unknown_and_warns(
        self, tmp_path, capsys, monkeypatch
    ):
        run_dir = _seed_run_journal(
            tmp_path, run_id="acme-run1", lines=["{not valid json at all"]
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["state"] == "unknown"
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-002" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_budget_consumed_reads_last_journaled_usage_observation(
        self, tmp_path, capsys, monkeypatch
    ):
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[
                _outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
                _supervisor_attach_line("acme-run1", pid=5252),
                _budget_usage_line("acme-run1", cost_estimate=1000),
                _budget_usage_line(
                    "acme-run1", cost_estimate=2500, ts="2026-08-06T00:10:00.000Z"
                ),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=())}
        )
        process = _FakeProcess(alive_pids=frozenset({5252}))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["homes"][0]["budget_consumed"] == 2500
        assert exit_code == 0

    def test_no_budget_usage_entry_reports_null(self, tmp_path, capsys, monkeypatch):
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[
                _outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
                _supervisor_attach_line("acme-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=())}
        )
        process = _FakeProcess(alive_pids=frozenset({5252}))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["homes"][0]["budget_consumed"] is None
        assert exit_code == 0

    def test_project_flag_scopes_to_one_slug(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None})
        home_a = tmp_path / "loop-homes" / "acme"
        home_b = tmp_path / "loop-homes" / "beta"
        vcs = _FakeVcs(
            worktrees=(
                WorktreeEntry(path=home_a, branch="loop/acme"),
                WorktreeEntry(path=home_b, branch="loop/beta"),
            )
        )

        exit_code = status_cli.run_status(
            _args(project="beta"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert len(payload["data"]["homes"]) == 1
        assert payload["data"]["homes"][0]["slug"] == "beta"
        assert exit_code == 0

    def test_seven_homes_all_reported(self, tmp_path, capsys, monkeypatch):
        slugs = [f"proj{i}" for i in range(7)]
        _stub_latest_run_dir(monkeypatch, run_dir_map={slug: None for slug in slugs})
        worktrees = tuple(
            WorktreeEntry(path=tmp_path / "loop-homes" / slug, branch=f"loop/{slug}")
            for slug in slugs
        )
        vcs = _FakeVcs(worktrees=worktrees)

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert len(payload["data"]["homes"]) == 7
        assert all(row["state"] == "idle" for row in payload["data"]["homes"])
        assert exit_code == 0

    def test_text_format_renders_without_crashing(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        assert "status:" in out
        assert "acme" in out
        assert "idle" in out
        assert exit_code == 0

    def test_run_status_with_default_ports_does_not_crash(self, capsys):
        """Smoke test over the real GitVcs/LocalFs/BmadLoopHarness/
        PosixProcess/SystemClock default construction path -- mirrors
        ``test_retire.py::test_run_retire_with_default_ports_does_not_crash``.
        Scoped to a slug naming no real project so it stays deterministic
        regardless of ambient fleet state on the machine running this test.
        Runs against the REAL repo this test executes from (mirrors
        ``test_retire.py``'s own identical rationale for the same test)."""
        exit_code = status_cli.run_status(_args(project="no-such-project-xyz"))

        assert isinstance(exit_code, int)
        payload = _payload(capsys)
        assert payload["data"]["homes"] == []
