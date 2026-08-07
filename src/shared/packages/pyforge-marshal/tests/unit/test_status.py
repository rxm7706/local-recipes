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

import jsonschema
import pytest

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.adapters.harness_bmadloop import HarnessError
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import spin as spin_module
from pyforge.marshal.cli import status as status_cli
from pyforge.marshal.core import status
from pyforge.marshal.core.identity import normalize, render_merge_subject
from pyforge.marshal.core.journal import (
    JournalEntryId,
    Phase,
    build_entry,
    prepare_for_write,
)
from pyforge.marshal.core.model import Severity
from pyforge.marshal.ports.harness import (
    DeferredStory,
    RunStatusSnapshot,
    TaskPhaseSnapshot,
)
from pyforge.marshal.ports.process import ProcessResult
from pyforge.marshal.ports.vcs import WorktreeEntry

_CANONICAL = Path("/repo/_bmad-output/projects/acme/implementation-artifacts")

# A fixed "now" for Story 5.1's `_FakeClock` -- any test that seeds a real
# run-launch journal entry needs a real datetime to subtract against (an
# `elapsed_seconds` computation only ever runs when a launch timestamp was
# actually recovered); tests with no run at all never engage it.
_FIXED_NOW = datetime(2026, 8, 6, 0, 30, 0, tzinfo=timezone.utc)

# Story 5.4: schema files this file's own `jsonschema.validate` tests load
# -- mirrors `test_init.py`'s own established `_SCHEMA_PATH` convention.
_SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal" / "schemas"
_STATUS_SCHEMA_PATH = _SCHEMAS_DIR / "status.json"
_ENVELOPE_SCHEMA_PATH = _SCHEMAS_DIR / "envelope.v1.json"


def _validate_against_status_schema(data: object) -> None:
    schema = json.loads(_STATUS_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)


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
            "escalation_reason": None,
            "escalation_artifact": None,
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

    # --- Story 5.3 (FR-38): escalation_reason/escalation_artifact ----------

    def test_non_escalated_row_reports_null_escalation_fields(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            tasks=(_task(phase="dev-running"),),
            supervisor_alive=True,
        )
        row, _ = status.build_fleet_row(facts)
        assert row["state"] == "running"
        assert row["escalation_reason"] is None
        assert row["escalation_artifact"] is None

    def test_escalated_row_reports_reason_and_spec_file_artifact(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            paused_stage="escalation",
            supervisor_alive=True,
            paused_reason="needs a human decision",
            escalated_spec_file="spec-1.2.md",
            escalated_task_phase="dev-running",
        )
        row, _ = status.build_fleet_row(facts)
        assert row["state"] == "paused-on-escalation"
        assert row["escalation_reason"] == "needs a human decision"
        assert row["escalation_artifact"] == "spec-1.2.md"

    def test_escalation_artifact_falls_back_to_task_phase_when_no_spec_file(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            paused_stage="escalation",
            supervisor_alive=True,
            paused_reason="needs a human decision",
            escalated_spec_file=None,
            escalated_task_phase="dev-running",
        )
        row, _ = status.build_fleet_row(facts)
        assert row["escalation_artifact"] == "dev-running"

    def test_escalated_but_dead_supervisor_reports_unsupervised_with_null_escalation_fields(
        self,
    ):
        """Code review (2026-08-07, both reviewers independently, the
        single most severe finding against this story): `paused_stage`
        still literally reads `"escalation"` and `paused_reason`/
        `escalated_spec_file` are both real, non-None values -- but
        `derive_home_state`'s own dead-supervisor override (already
        established, unchanged by this story) takes precedence, so the
        DERIVED state is `"unsupervised"`, not `"paused-on-escalation"`.
        The escalation fields must follow the derived state, never the
        raw facts -- reporting them here would silently exclude this row
        from `sort_fleet_rows`/`--escalations` (both key on `state`) while
        still leaking stale escalation data into its JSON payload."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            paused_stage="escalation",
            supervisor_alive=False,
            paused_reason="needs a human decision",
            escalated_spec_file="spec-1.2.md",
            escalated_task_phase="dev-running",
        )
        row, _ = status.build_fleet_row(facts)
        assert row["state"] == "unsupervised"
        assert row["escalation_reason"] is None
        assert row["escalation_artifact"] is None

    def test_escalated_but_finished_reports_stopped_with_null_escalation_fields(self):
        """Same root cause as the dead-supervisor case above, via
        `derive_home_state`'s OTHER precedence rule: `finished=True`
        reports `"stopped"` regardless of a stale `paused_stage`."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=True,
            paused_stage="escalation",
            supervisor_alive=True,
            paused_reason="needs a human decision",
            escalated_spec_file="spec-1.2.md",
        )
        row, _ = status.build_fleet_row(facts)
        assert row["state"] == "stopped"
        assert row["escalation_reason"] is None
        assert row["escalation_artifact"] is None


class TestSortFleetRows:
    """Story 5.3 (FR-38): escalated rows sort first, stable otherwise."""

    def _row(self, slug: str, state: str) -> dict[str, object]:
        return {"slug": slug, "state": state}

    def test_zero_escalations_order_unchanged(self):
        rows = [self._row("a", "idle"), self._row("b", "running"), self._row("c", "stopped")]
        assert status.sort_fleet_rows(rows) == rows

    def test_one_escalation_sorts_first(self):
        rows = [
            self._row("a", "idle"),
            self._row("b", "paused-on-escalation"),
            self._row("c", "running"),
        ]
        result = status.sort_fleet_rows(rows)
        assert [row["slug"] for row in result] == ["b", "a", "c"]

    def test_multiple_escalations_sort_first_stable_otherwise(self):
        rows = [
            self._row("a", "idle"),
            self._row("b", "paused-on-escalation"),
            self._row("c", "running"),
            self._row("d", "paused-on-escalation"),
            self._row("e", "stopped"),
        ]
        result = status.sort_fleet_rows(rows)
        assert [row["slug"] for row in result] == ["b", "d", "a", "c", "e"]

    def test_empty_rows_is_a_noop(self):
        assert status.sort_fleet_rows([]) == []


# =============================================================================
# Story 5.4: `core.status.reconcile_ledger_vs_git` -- pure comparison core
# (AD-4), driven entirely by plain `frozenset[str]` args, no ports/I/O.
# =============================================================================


class TestReconcileLedgerVsGit:
    def test_full_agreement_reports_no_discrepancies(self):
        result = status.reconcile_ledger_vs_git(
            frozenset({"1.1", "1.2"}), frozenset({"1.1", "1.2"})
        )
        assert result == ()

    def test_empty_both_sides_reports_no_discrepancies(self):
        assert status.reconcile_ledger_vs_git(frozenset(), frozenset()) == ()

    def test_done_in_ledger_not_merged(self):
        result = status.reconcile_ledger_vs_git(
            frozenset({"1.1"}), frozenset()
        )
        assert result == (
            {"story_key": "1.1", "kind": "done-in-ledger-not-merged", "confidence": "unconfirmed"},
        )

    def test_merged_not_done_in_ledger(self):
        """The live incident this story exists to catch: a story git
        confirms as durably merged whose ledger status is anything other
        than done -- including absent entirely, the case exercised here."""
        result = status.reconcile_ledger_vs_git(
            frozenset(), frozenset({"4.1"})
        )
        assert result == (
            {"story_key": "4.1", "kind": "merged-not-done-in-ledger", "confidence": "confirmed"},
        )

    def test_both_directions_at_once_sorted_by_key_within_each_kind(self):
        result = status.reconcile_ledger_vs_git(
            frozenset({"1.2", "1.1"}), frozenset({"2.2", "2.1"})
        )
        assert result == (
            {"story_key": "1.1", "kind": "done-in-ledger-not-merged", "confidence": "unconfirmed"},
            {"story_key": "1.2", "kind": "done-in-ledger-not-merged", "confidence": "unconfirmed"},
            {"story_key": "2.1", "kind": "merged-not-done-in-ledger", "confidence": "confirmed"},
            {"story_key": "2.2", "kind": "merged-not-done-in-ledger", "confidence": "confirmed"},
        )

    def test_result_is_deterministic_regardless_of_set_construction_order(self):
        first = status.reconcile_ledger_vs_git(
            frozenset({"3.1", "1.1", "2.1"}), frozenset({"9.9", "5.5"})
        )
        second = status.reconcile_ledger_vs_git(
            frozenset({"2.1", "3.1", "1.1"}), frozenset({"5.5", "9.9"})
        )
        assert first == second


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
        repo_root_raises: bool = False,
        worktrees: tuple[WorktreeEntry, ...] = (),
        worktrees_raise: bool = False,
        commit_subjects_value: tuple[str, ...] = (),
        commit_subjects_raises: bool = False,
    ) -> None:
        self.repo_root_value = repo_root_value
        self.repo_root_raises = repo_root_raises
        self.worktrees = worktrees
        self.worktrees_raise = worktrees_raise
        # Story 5.4: `core.promotion.merged_story_keys`'s own git-evidence
        # gathering (`_reconcile_ledger`'s `vcs.commit_subjects(root,
        # "main")`) -- mirrors `test_deploy.py`'s own `_FakeVcs.
        # commit_subjects` convention.
        self.commit_subjects_value = commit_subjects_value
        self.commit_subjects_raises = commit_subjects_raises

    def repo_common_root(self, start):
        if self.repo_root_raises:
            raise VcsCommandError("cannot resolve repo root")
        return self.repo_root_value

    def list_worktrees(self, repo_root):
        if self.worktrees_raise:
            raise VcsCommandError("git worktree list failed")
        return self.worktrees

    def commit_subjects(self, repo_root, ref):
        if self.commit_subjects_raises:
            raise VcsCommandError("cannot read commit history")
        return self.commit_subjects_value


class _FakeHarness:
    """Keyed by ``(str(project), run_id)`` -- mirrors ``test_retire.py::
    _FakeHarness``'s own convention, widened by ``run_id`` since this
    command may resolve a distinct ``harness_run_id`` per project."""

    def __init__(
        self,
        snapshots: dict[tuple[str, str], RunStatusSnapshot | None] | None = None,
        *,
        ledger_statuses: tuple[tuple[str, str], ...] = (),
        ledger_raises: bool = False,
        ledger_error_message: str = "sprint status file not found",
    ) -> None:
        self.snapshots = snapshots or {}
        self.calls: list[tuple[str, str]] = []
        # Story 5.4: `_reconcile_ledger`'s `HarnessPort.ledger_story_statuses`
        # call -- `ledger_raises` mirrors `sprintstatus.load`'s own
        # `SprintStatusError` (missing file, invalid YAML, ...), always
        # surfaced by the real adapter as a `HarnessError`.
        self.ledger_statuses = ledger_statuses
        self.ledger_raises = ledger_raises
        self.ledger_error_message = ledger_error_message
        self.ledger_calls: list[Path] = []

    def run_status_snapshot(self, project, run_id):
        self.calls.append((str(project), run_id))
        return self.snapshots.get((str(project), run_id))

    def ledger_story_statuses(self, path):
        self.ledger_calls.append(path)
        if self.ledger_raises:
            raise HarnessError(self.ledger_error_message)
        return self.ledger_statuses


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


def _args(
    *,
    project: str | None = None,
    format: str = "json",
    run: str | None = None,
    escalations: bool = False,
    reconcile_ledger: bool = False,
):
    return argparse.Namespace(
        project=project,
        format=format,
        run=run,
        escalations=escalations,
        reconcile_ledger=reconcile_ledger,
    )


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
    run_id: str,
    *,
    cost_estimate: int,
    story_key: str = "1.1",
    ts: str = "2026-08-06T00:05:00.000Z",
) -> str:
    entry = build_entry(
        id=JournalEntryId("supervisor-1", 1),
        ts=ts,
        run_id=run_id,
        kind="budget-usage",
        phase=Phase.OBSERVATION,
        payload={"story_key": story_key, "cost_estimate": cost_estimate},
    )
    return prepare_for_write(entry).line


def _manual_landing_line(
    run_id: str,
    *,
    story_key: str,
    gate_verdict: str,
    ts: str = "2026-08-06T00:07:00.000Z",
) -> str:
    """A minimal, valid ``"manual-landing"`` journal line -- the SAME shape
    ``cli/deploy.py``'s own ``run_land_story`` journals (Story 4.3's own
    ``_LAND_KIND``), the one real source ``_gather_gate_verdicts`` reads a
    per-story gate verdict from."""
    entry = build_entry(
        id=JournalEntryId("deploy-1", 1),
        ts=ts,
        run_id=run_id,
        kind="manual-landing",
        phase=Phase.OBSERVATION,
        payload={
            "story_key": story_key,
            "justification": "because",
            "merge_sha": "deadbeef",
            "gate_verdict": gate_verdict,
        },
    )
    return prepare_for_write(entry).line


def _open_intent_line(
    run_id: str,
    *,
    kind: str = "story-spec-commit",
    ts: str = "2026-08-06T00:08:00.000Z",
) -> str:
    """A minimal, valid ``phase: intent`` journal line with no matching
    ``outcome`` -- ``core.journal.fold``'s own ``FoldResult.open_intents``
    reports it as still-open."""
    entry = build_entry(
        id=JournalEntryId("deploy-1", 2),
        ts=ts,
        run_id=run_id,
        kind=kind,
        phase=Phase.INTENT,
        payload={"story_keys": ["1.1"]},
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
    paused_reason: str | None = None,
    escalated_spec_file: str | None = None,
    escalated_task_phase: str | None = None,
) -> RunStatusSnapshot:
    return RunStatusSnapshot(
        paused_stage=paused_stage,
        paused_story_key=None,
        paused_reason=paused_reason,
        escalated_spec_file=escalated_spec_file,
        escalated_task_phase=escalated_task_phase,
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

    # --- Story 5.3 (FR-38): --escalations + fleet-summary sort -------------

    def test_fleet_summary_sorts_escalated_rows_first(
        self, tmp_path, capsys, monkeypatch
    ):
        _stub_latest_run_dir(
            monkeypatch, run_dir_map={"acme": None, "beta": None, "gamma": None}
        )
        run_dir_beta = _seed_run_journal(
            tmp_path,
            run_id="beta-run1",
            lines=[
                _outcome_line("beta-run1", pid=4242, harness_run_id="hrid-beta"),
                _supervisor_attach_line("beta-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(
            monkeypatch,
            run_dir_map={"acme": None, "beta": run_dir_beta, "gamma": None},
        )
        homes = {
            slug: tmp_path / "loop-homes" / slug for slug in ("acme", "beta", "gamma")
        }
        vcs = _FakeVcs(
            worktrees=tuple(
                WorktreeEntry(path=homes[slug], branch=f"loop/{slug}")
                for slug in ("acme", "beta", "gamma")
            )
        )
        harness = _FakeHarness(
            snapshots={
                (str(homes["beta"]), "hrid-beta"): _snapshot(
                    paused_stage="escalation",
                    paused_reason="needs a human decision",
                    escalated_spec_file="spec-1.2.md",
                )
            }
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
        homes_rows = payload["data"]["homes"]
        assert [row["slug"] for row in homes_rows] == ["beta", "acme", "gamma"]
        assert homes_rows[0]["state"] == "paused-on-escalation"
        assert homes_rows[0]["escalation_reason"] == "needs a human decision"
        assert homes_rows[0]["escalation_artifact"] == "spec-1.2.md"
        assert exit_code == 0

    def test_escalations_flag_with_zero_matches_is_a_clean_empty_list(
        self, tmp_path, capsys, monkeypatch
    ):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None})
        vcs = _FakeVcs(
            worktrees=(
                WorktreeEntry(path=tmp_path / "loop-homes" / "acme", branch="loop/acme"),
                WorktreeEntry(path=tmp_path / "loop-homes" / "beta", branch="loop/beta"),
            )
        )

        exit_code = status_cli.run_status(
            _args(escalations=True),
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

    def test_escalations_flag_with_matches_filters_to_only_escalated(
        self, tmp_path, capsys, monkeypatch
    ):
        run_dir_beta = _seed_run_journal(
            tmp_path,
            run_id="beta-run1",
            lines=[
                _outcome_line("beta-run1", pid=4242, harness_run_id="hrid-beta"),
                _supervisor_attach_line("beta-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(
            monkeypatch, run_dir_map={"acme": None, "beta": run_dir_beta}
        )
        homes = {slug: tmp_path / "loop-homes" / slug for slug in ("acme", "beta")}
        vcs = _FakeVcs(
            worktrees=(
                WorktreeEntry(path=homes["acme"], branch="loop/acme"),
                WorktreeEntry(path=homes["beta"], branch="loop/beta"),
            )
        )
        harness = _FakeHarness(
            snapshots={
                (str(homes["beta"]), "hrid-beta"): _snapshot(
                    paused_stage="escalation",
                    paused_reason="needs a human decision",
                    escalated_task_phase="dev-running",
                )
            }
        )
        process = _FakeProcess(alive_pids=frozenset({5252}))

        exit_code = status_cli.run_status(
            _args(escalations=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        homes_rows = payload["data"]["homes"]
        assert len(homes_rows) == 1
        assert homes_rows[0]["slug"] == "beta"
        assert homes_rows[0]["state"] == "paused-on-escalation"
        # No spec file was recorded -- falls back to the task phase.
        assert homes_rows[0]["escalation_artifact"] == "dev-running"
        assert exit_code == 0

    def test_escalations_flag_combined_with_project_scope(
        self, tmp_path, capsys, monkeypatch
    ):
        run_dir_beta = _seed_run_journal(
            tmp_path,
            run_id="beta-run1",
            lines=[
                _outcome_line("beta-run1", pid=4242, harness_run_id="hrid-beta"),
                _supervisor_attach_line("beta-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(
            monkeypatch, run_dir_map={"acme": None, "beta": run_dir_beta}
        )
        homes = {slug: tmp_path / "loop-homes" / slug for slug in ("acme", "beta")}
        vcs = _FakeVcs(
            worktrees=(
                WorktreeEntry(path=homes["acme"], branch="loop/acme"),
                WorktreeEntry(path=homes["beta"], branch="loop/beta"),
            )
        )
        harness = _FakeHarness(
            snapshots={
                (str(homes["beta"]), "hrid-beta"): _snapshot(
                    paused_stage="escalation", paused_reason="needs a decision"
                )
            }
        )
        process = _FakeProcess(alive_pids=frozenset({5252}))

        # Scoped to "acme" (not escalated) -- the filter applies on TOP of
        # the scope, so the result is empty even though "beta" IS escalated.
        exit_code = status_cli.run_status(
            _args(project="acme", escalations=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"]["homes"] == []
        assert exit_code == 0

        # Scoped to "beta" (escalated) -- the filter keeps it.
        exit_code = status_cli.run_status(
            _args(project="beta", escalations=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert len(payload["data"]["homes"]) == 1
        assert payload["data"]["homes"][0]["slug"] == "beta"
        assert exit_code == 0

    def test_text_format_marks_escalated_row(self, tmp_path, capsys, monkeypatch):
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
                    paused_stage="escalation",
                    paused_reason="needs a human decision",
                    escalated_spec_file="spec-1.2.md",
                )
            }
        )
        process = _FakeProcess(alive_pids=frozenset({5252}))

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        assert "[ESCALATED]" in out
        assert "needs a human decision" in out
        assert "spec-1.2.md" in out
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


# =============================================================================
# Story 5.2: RunDetailFacts / build_run_detail (`marshal status --run
# <run_id> --project <slug>`, FR-37/NFR-12) -- covers every row of the
# spec's I/O & Edge-Case Matrix, pure-core level (no ports, no I/O).
# =============================================================================


def _deferred(story_key: str = "1.2") -> DeferredStory:
    return DeferredStory(
        story_key=story_key,
        reason="blocked on external review",
        attempt=2,
        branch="loop/acme/1.2",
        worktree_path="/loop-homes/acme/.worktrees/1.2",
        spec_file="spec-1.2.md",
    )


def _intent_dict(story_key: str = "1.1") -> dict[str, object]:
    """A plain, already-rendered ``JournalEntry.to_json_dict()`` shape --
    ``build_run_detail`` reports ``RunDetailFacts.open_intents`` verbatim,
    so the pure-core tests never need a real ``JournalEntry``."""
    return {
        "id": {"writer_id": "deploy-1", "counter": 2},
        "ts": "2026-08-06T00:08:00.000Z",
        "run_id": "acme-run1",
        "story": story_key,
        "kind": "story-spec-commit",
        "phase": "intent",
        "payload": {"story_keys": [story_key]},
    }


class TestBuildRunDetail:
    def test_not_found_reports_mrs_status_004(self):
        facts = status.RunDetailFacts(project="acme", run_id="acme-run9", found=False)
        row, finding = status.build_run_detail(facts)
        assert row == {
            "project": "acme",
            "run_id": "acme-run9",
            "found": False,
            "state_readable": None,
            "finished": None,
            "paused_stage": None,
            "paused_story_key": None,
            "paused_reason": None,
            "escalated_spec_file": None,
            "escalated_task_phase": None,
            "stories": [],
            "deferred": [],
            "open_intents": [],
        }
        assert finding is not None
        assert finding.code == "MRS-STATUS-004"
        assert finding.severity is Severity.WARN
        assert "acme-run9" in finding.message

    def test_state_unreadable_nulls_out_snapshot_fields_and_warns(self):
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=False,
            gate_verdicts={"1.1": "clean"},
            budget_by_story={"1.1": 500},
            open_intents=(_intent_dict(),),
        )
        row, finding = status.build_run_detail(facts)
        assert row["found"] is True
        assert row["state_readable"] is False
        assert row["finished"] is None
        assert row["paused_stage"] is None
        assert row["stories"] == []
        assert row["deferred"] == []
        # Journal-sourced facts stay populated -- unaffected by a dead/
        # detached loop home (a distinct failure source from state.json).
        assert row["open_intents"] == [_intent_dict()]
        assert finding is not None
        assert finding.code == "MRS-STATUS-002"
        assert finding.severity is Severity.WARN
        assert "acme-run1" in finding.message

    def test_empty_tasks_is_no_crash_empty_stories_no_finding(self):
        facts = status.RunDetailFacts(
            project="acme", run_id="acme-run1", found=True, state_readable=True
        )
        row, finding = status.build_run_detail(facts)
        assert row["stories"] == []
        assert finding is None

    def test_story_with_gate_verdict_is_named(self):
        task = TaskPhaseSnapshot(
            story_key="1.1", phase="done", commit_sha="cafe123", branch=""
        )
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            tasks=(task,),
            gate_verdicts={"1.1": "clean"},
        )
        row, finding = status.build_run_detail(facts)
        assert row["stories"] == [
            {
                "story_key": "1.1",
                "phase": "done",
                "commit_sha": "cafe123",
                "branch": "",
                "gate_verdict": "clean",
                "budget_consumed": None,
            }
        ]
        assert finding is None

    def test_story_without_gate_verdict_is_null_not_fabricated(self):
        task = TaskPhaseSnapshot(story_key="1.1", phase="dev-running", commit_sha=None)
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            tasks=(task,),
            gate_verdicts={},
        )
        row, _ = status.build_run_detail(facts)
        assert row["stories"][0]["gate_verdict"] is None

    def test_story_sequence_reported_verbatim_never_resorted_or_deduped(self):
        """The spec's own Always bullet: ``state.json``'s own ``tasks``
        iteration order, a duplicate story key reported as-is."""
        tasks = (
            TaskPhaseSnapshot(story_key="1.2", phase="done", commit_sha="aaa"),
            TaskPhaseSnapshot(story_key="1.1", phase="dev-running", commit_sha=None),
            TaskPhaseSnapshot(story_key="1.2", phase="review-verify", commit_sha="bbb"),
        )
        facts = status.RunDetailFacts(
            project="acme", run_id="acme-run1", found=True, state_readable=True,
            tasks=tasks,
        )
        row, _ = status.build_run_detail(facts)
        assert [s["story_key"] for s in row["stories"]] == ["1.2", "1.1", "1.2"]

    def test_escalation_paused_names_reason_and_artifact(self):
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            paused_stage="escalation",
            paused_story_key="1.3",
            paused_reason="ambiguous spec",
            escalated_spec_file="spec-1.3.md",
            escalated_task_phase="dev-verify",
        )
        row, finding = status.build_run_detail(facts)
        assert row["paused_stage"] == "escalation"
        assert row["paused_story_key"] == "1.3"
        assert row["paused_reason"] == "ambiguous spec"
        assert row["escalated_spec_file"] == "spec-1.3.md"
        assert row["escalated_task_phase"] == "dev-verify"
        assert finding is None

    def test_deferred_stories_listed_with_reason_and_attempt(self):
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            deferred=(_deferred(),),
        )
        row, _ = status.build_run_detail(facts)
        assert row["deferred"] == [
            {
                "story_key": "1.2",
                "reason": "blocked on external review",
                "attempt": 2,
                "branch": "loop/acme/1.2",
                "worktree_path": "/loop-homes/acme/.worktrees/1.2",
                "spec_file": "spec-1.2.md",
            }
        ]

    def test_open_intent_reported_verbatim_never_reinterpreted(self):
        intent = _intent_dict()
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            open_intents=(intent,),
        )
        row, _ = status.build_run_detail(facts)
        assert row["open_intents"] == [intent]

    def test_budget_consumed_grouped_per_story_key_not_a_single_latest(self):
        """Story 5.2's own genuinely different aggregation from Story 5.1's
        fleet row: EACH story key's own latest value, not one overall
        latest."""
        tasks = (
            TaskPhaseSnapshot(story_key="1.1", phase="done", commit_sha="a"),
            TaskPhaseSnapshot(story_key="1.2", phase="dev-running", commit_sha=None),
        )
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            tasks=tasks,
            budget_by_story={"1.1": 1000, "1.2": 2500},
        )
        row, _ = status.build_run_detail(facts)
        by_key = {s["story_key"]: s["budget_consumed"] for s in row["stories"]}
        assert by_key == {"1.1": 1000, "1.2": 2500}

    def test_story_with_no_budget_usage_entry_reports_null_not_zero(self):
        task = TaskPhaseSnapshot(story_key="1.1", phase="dev-running", commit_sha=None)
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            tasks=(task,),
            budget_by_story={},
        )
        row, _ = status.build_run_detail(facts)
        assert row["stories"][0]["budget_consumed"] is None

    def test_render_story_key_best_effort_renders_dot_form(self):
        key = normalize("1.2")
        assert status._render_story_key_best_effort(str(key)) == "1.2"

    def test_render_story_key_best_effort_falls_back_to_raw_on_unparseable(self):
        assert status._render_story_key_best_effort("not-a-story-key") == (
            "not-a-story-key"
        )


# =============================================================================
# Story 5.2: `cli/status.py`'s ``--run <run_id> --project <slug>`` path --
# I/O matrix, fake VcsPort/HarnessPort doubles, real LocalFs against a REAL
# tmp_path journal file (mirrors TestRunStatus's own established shape).
# =============================================================================


def _run_detail_dir(tmp_path: Path, *, slug: str, run_id: str) -> Path:
    """The EXACT path ``cli/status.py::_run_detail`` computes -- the
    project's own canonical Tier-3 store, never a home-relative path (this
    command reads run directories directly off the repo root/slug, mirroring
    ``cli/deploy.py::_gather_gate_verdicts``'s own identical convention)."""
    return (
        tmp_path
        / "_bmad-output"
        / "projects"
        / slug
        / "implementation-artifacts"
        / "runs"
        / run_id
    )


def _seed_run_detail_journal(
    tmp_path: Path, *, slug: str, run_id: str, lines: list[str]
) -> Path:
    run_dir = _run_detail_dir(tmp_path, slug=slug, run_id=run_id)
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_dir


class TestRunDetail:
    def test_run_without_project_refuses_before_any_io_mrs_status_003(self, capsys):
        exit_code = status_cli.run_status(
            _args(run="acme-run1"),
            vcs=_FakeVcs(),
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        codes = [f["code"] for f in payload["findings"]]
        assert codes == ["MRS-STATUS-003"]
        assert payload["verdict"] == "unevaluable"
        assert exit_code == 1

    def test_repo_root_failure_never_fabricates_a_confirmed_absent_run(
        self, capsys
    ):
        """Code review (2026-08-07, Edge Case Hunter): a `VcsCommandError`
        resolving the repo root means the filesystem was never consulted
        -- whether the run exists is genuinely UNKNOWN, not confirmed
        absent. Must report ONLY the repo-root finding, never also
        synthesize `MRS-STATUS-004`'s "no run directory found" claim on
        top of it (mirrors `run_status`'s own identical `VcsCommandError`
        handling for the fleet-summary path)."""
        exit_code = status_cli.run_status(
            _args(project="acme", run="acme-run1"),
            vcs=_FakeVcs(repo_root_raises=True),
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        codes = [f["code"] for f in payload["findings"]]
        assert codes == ["MRS-STATUS-002"]
        assert "found" not in payload["data"]
        assert exit_code == 0

    def test_run_id_with_no_matching_directory_reports_mrs_status_004(
        self, tmp_path, capsys
    ):
        vcs = _FakeVcs(repo_root_value=tmp_path)
        exit_code = status_cli.run_status(
            _args(project="acme", run="acme-run-does-not-exist"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"]["found"] is False
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-004" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_full_run_detail_reports_stories_gate_verdicts_budget_and_open_intent(
        self, tmp_path, capsys
    ):
        slug = "acme"
        run_id = "acme-run1"
        _seed_run_detail_journal(
            tmp_path,
            slug=slug,
            run_id=run_id,
            lines=[
                _outcome_line(run_id, pid=4242, harness_run_id="hrid-1"),
                _manual_landing_line(run_id, story_key="1.1", gate_verdict="clean"),
                _budget_usage_line(
                    run_id, story_key="1.1", cost_estimate=1000,
                    ts="2026-08-06T00:05:00.000Z",
                ),
                _budget_usage_line(
                    run_id, story_key="1.1", cost_estimate=1500,
                    ts="2026-08-06T00:06:00.000Z",
                ),
                _budget_usage_line(
                    run_id, story_key="1.2", cost_estimate=300,
                    ts="2026-08-06T00:06:30.000Z",
                ),
                _open_intent_line(run_id),
            ],
        )
        home = tmp_path / "loop-homes" / slug
        vcs = _FakeVcs(
            repo_root_value=tmp_path,
            worktrees=(WorktreeEntry(path=home, branch=f"loop/{slug}"),),
        )
        tasks = (
            _task(story_key="1.1", phase="done"),
            _task(story_key="1.2", phase="dev-running"),
        )
        harness = _FakeHarness(
            snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=tasks)}
        )

        exit_code = status_cli.run_status(
            _args(project=slug, run=run_id),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        data = payload["data"]
        assert data["project"] == slug
        assert data["run_id"] == run_id
        assert data["found"] is True
        assert data["state_readable"] is True
        assert data["finished"] is False

        by_key = {s["story_key"]: s for s in data["stories"]}
        assert by_key["1.1"]["gate_verdict"] == "clean"
        assert by_key["1.1"]["budget_consumed"] == 1500
        assert by_key["1.2"]["gate_verdict"] is None
        assert by_key["1.2"]["budget_consumed"] == 300

        assert len(data["open_intents"]) == 1
        assert data["open_intents"][0]["kind"] == "story-spec-commit"
        assert exit_code == 0

    def test_run_paused_on_escalation_names_reason_and_artifact(
        self, tmp_path, capsys
    ):
        slug = "acme"
        run_id = "acme-run1"
        _seed_run_detail_journal(
            tmp_path,
            slug=slug,
            run_id=run_id,
            lines=[_outcome_line(run_id, pid=4242, harness_run_id="hrid-1")],
        )
        home = tmp_path / "loop-homes" / slug
        vcs = _FakeVcs(
            repo_root_value=tmp_path,
            worktrees=(WorktreeEntry(path=home, branch=f"loop/{slug}"),),
        )
        snapshot = RunStatusSnapshot(
            paused_stage="escalation",
            paused_story_key="1.3",
            paused_reason="ambiguous spec",
            escalated_spec_file="spec-1.3.md",
            escalated_task_phase="dev-verify",
            deferred=(),
            finished=False,
            tasks=(),
        )
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): snapshot})

        exit_code = status_cli.run_status(
            _args(project=slug, run=run_id),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        data = payload["data"]
        assert data["paused_stage"] == "escalation"
        assert data["paused_story_key"] == "1.3"
        assert data["escalated_spec_file"] == "spec-1.3.md"
        assert exit_code == 0

    def test_run_with_deferred_stories_lists_every_one(self, tmp_path, capsys):
        slug = "acme"
        run_id = "acme-run1"
        _seed_run_detail_journal(
            tmp_path,
            slug=slug,
            run_id=run_id,
            lines=[_outcome_line(run_id, pid=4242, harness_run_id="hrid-1")],
        )
        home = tmp_path / "loop-homes" / slug
        vcs = _FakeVcs(
            repo_root_value=tmp_path,
            worktrees=(WorktreeEntry(path=home, branch=f"loop/{slug}"),),
        )
        deferred = DeferredStory(
            story_key="1.4",
            reason="waiting on upstream",
            attempt=1,
            branch="loop/acme/1.4",
            worktree_path="/loop-homes/acme/.worktrees/1.4",
            spec_file="spec-1.4.md",
        )
        snapshot = RunStatusSnapshot(
            paused_stage=None,
            paused_story_key=None,
            paused_reason=None,
            escalated_spec_file=None,
            escalated_task_phase=None,
            deferred=(deferred,),
            finished=False,
            tasks=(),
        )
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): snapshot})

        exit_code = status_cli.run_status(
            _args(project=slug, run=run_id),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["deferred"] == [
            {
                "story_key": "1.4",
                "reason": "waiting on upstream",
                "attempt": 1,
                "branch": "loop/acme/1.4",
                "worktree_path": "/loop-homes/acme/.worktrees/1.4",
                "spec_file": "spec-1.4.md",
            }
        ]
        assert exit_code == 0

    def test_run_with_empty_tasks_reports_empty_stories_no_crash(
        self, tmp_path, capsys
    ):
        slug = "acme"
        run_id = "acme-run1"
        _seed_run_detail_journal(
            tmp_path,
            slug=slug,
            run_id=run_id,
            lines=[_outcome_line(run_id, pid=4242, harness_run_id="hrid-1")],
        )
        home = tmp_path / "loop-homes" / slug
        vcs = _FakeVcs(
            repo_root_value=tmp_path,
            worktrees=(WorktreeEntry(path=home, branch=f"loop/{slug}"),),
        )
        harness = _FakeHarness(
            snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=())}
        )

        exit_code = status_cli.run_status(
            _args(project=slug, run=run_id),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["stories"] == []
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_no_loop_home_attached_degrades_state_readable_but_keeps_journal_facts(
        self, tmp_path, capsys
    ):
        """No ``loop/acme`` worktree currently attached -- ``state.json``
        cannot be read at all, but the run's own journal-sourced facts
        (gate verdicts, consumption, open intents) stay populated (a dead/
        detached loop home is a different failure source, per the spec's
        own Design Notes)."""
        slug = "acme"
        run_id = "acme-run1"
        _seed_run_detail_journal(
            tmp_path,
            slug=slug,
            run_id=run_id,
            lines=[
                _outcome_line(run_id, pid=4242, harness_run_id="hrid-1"),
                _manual_landing_line(run_id, story_key="1.1", gate_verdict="clean"),
            ],
        )
        vcs = _FakeVcs(repo_root_value=tmp_path, worktrees=())

        exit_code = status_cli.run_status(
            _args(project=slug, run=run_id),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        data = payload["data"]
        assert data["found"] is True
        assert data["state_readable"] is False
        assert data["stories"] == []
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-002" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_text_format_run_detail_renders_without_crashing(self, tmp_path, capsys):
        slug = "acme"
        run_id = "acme-run1"
        _seed_run_detail_journal(
            tmp_path,
            slug=slug,
            run_id=run_id,
            lines=[_outcome_line(run_id, pid=4242, harness_run_id="hrid-1")],
        )
        home = tmp_path / "loop-homes" / slug
        vcs = _FakeVcs(
            repo_root_value=tmp_path,
            worktrees=(WorktreeEntry(path=home, branch=f"loop/{slug}"),),
        )
        harness = _FakeHarness(
            snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=())}
        )

        exit_code = status_cli.run_status(
            _args(project=slug, run=run_id, format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        assert "--run" in out
        assert "stories: 0" in out
        assert exit_code == 0

    def test_run_status_with_default_ports_and_run_flag_does_not_crash(self, capsys):
        """Smoke test over the real GitVcs/LocalFs/BmadLoopHarness default
        construction path (mirrors ``TestRunStatus``'s own identical
        precedent) -- a run id naming nothing real for a project naming
        nothing real stays a clean, reportable 'not found', never a
        crash."""
        exit_code = status_cli.run_status(
            _args(project="no-such-project-xyz", run="no-such-run-xyz")
        )

        assert isinstance(exit_code, int)
        payload = _payload(capsys)
        assert payload["data"]["found"] is False


# =============================================================================
# Story 5.4: `cli/status.py`'s ``--reconcile-ledger --project <slug>`` path
# -- I/O matrix, fake VcsPort/HarnessPort doubles (mirrors ``TestRunStatus``/
# ``TestRunDetail``'s own established shape). ``status_cli.repo_root`` is
# monkeypatched to a real ``tmp_path`` -- `_reconcile_ledger` resolves BOTH
# the ledger path and the project-policy lookup off that module-level
# function (mirrors `test_deploy.py`'s own identical
# ``monkeypatch.setattr(deploy_module, "repo_root", lambda: tmp_path)``
# convention), never off `VcsPort.repo_common_root` (which `--run`'s own
# `_run_detail` uses instead -- a DIFFERENT resolution path, per
# `core/status.py`'s own module docstring precedent in `_scan_promotions`).
# =============================================================================

_DEFAULT_MERGE_TEMPLATE = "Merge {key} into main"


def _merged_subject(key: str) -> str:
    return render_merge_subject(normalize(key), _DEFAULT_MERGE_TEMPLATE)


class TestReconcileLedgerCli:
    def test_without_project_refuses_before_any_io_mrs_status_006(self, capsys):
        vcs = _FakeVcs()
        harness = _FakeHarness()
        exit_code = status_cli.run_status(
            _args(reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        codes = [f["code"] for f in payload["findings"]]
        assert codes == ["MRS-STATUS-006"]
        assert payload["verdict"] == "unevaluable"
        assert exit_code == 1
        # Refused before any I/O -- the ledger was never even looked up.
        assert harness.ledger_calls == []
        # Code review (2026-08-07, Edge Case Hunter): this refusal path's
        # own data_version-2 payload must still satisfy schemas/status.json
        # (required: ["project", "discrepancies"]) -- the original version
        # omitted `discrepancies` entirely, failing its own published
        # schema for exactly this invocation.
        assert payload["data"]["discrepancies"] == []
        _validate_against_status_schema(payload["data"])

    def test_run_and_reconcile_ledger_together_is_mutually_exclusive(self, capsys):
        """Code review (2026-08-07, Edge Case Hunter): the original version
        let `--reconcile-ledger` silently win over `--run` with no signal
        that `--run` was ignored."""
        vcs = _FakeVcs()
        harness = _FakeHarness()
        exit_code = status_cli.run_status(
            _args(project="acme", run="acme-run1", reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        codes = [f["code"] for f in payload["findings"]]
        assert codes == ["MRS-STATUS-006"]
        assert exit_code == 1
        assert harness.ledger_calls == []
        assert payload["data"]["discrepancies"] == []
        _validate_against_status_schema(payload["data"])

    def test_missing_ledger_file_reports_mrs_status_005(
        self, tmp_path, capsys, monkeypatch
    ):
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        vcs = _FakeVcs()
        harness = _FakeHarness(
            ledger_raises=True,
            ledger_error_message="sprint status file not found: acme",
        )
        exit_code = status_cli.run_status(
            _args(project="acme", reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        codes = [f["code"] for f in payload["findings"]]
        assert codes == ["MRS-STATUS-005"]
        assert payload["data"]["discrepancies"] == []
        assert payload["verdict"] == "warn"
        assert exit_code == 0
        assert payload["data_version"] == 2

    def test_git_history_unreadable_reports_mrs_status_007(
        self, tmp_path, capsys, monkeypatch
    ):
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        vcs = _FakeVcs(commit_subjects_raises=True)
        harness = _FakeHarness(ledger_statuses=(("1-1-title", "done"),))
        exit_code = status_cli.run_status(
            _args(project="acme", reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        codes = [f["code"] for f in payload["findings"]]
        assert codes == ["MRS-STATUS-007"]
        assert payload["data"]["discrepancies"] == []
        assert payload["verdict"] == "unevaluable"
        assert exit_code == 1

    def test_full_agreement_is_clean_with_no_discrepancies(
        self, tmp_path, capsys, monkeypatch
    ):
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        vcs = _FakeVcs(commit_subjects_value=(_merged_subject("1.1"),))
        harness = _FakeHarness(ledger_statuses=(("1-1-title", "done"),))
        exit_code = status_cli.run_status(
            _args(project="acme", reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"] == {"project": "acme", "discrepancies": []}
        assert payload["findings"] == []
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_done_in_ledger_not_merged_is_reported_never_a_finding(
        self, tmp_path, capsys, monkeypatch
    ):
        """The "silent stale ledger" case, in reverse of the live incident:
        a story the ledger claims done that git does not confirm. Named in
        `data.discrepancies`, never a `Finding` (the spec's own I/O
        matrix: "No finding -- reported, not an error")."""
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        vcs = _FakeVcs(commit_subjects_value=())
        harness = _FakeHarness(ledger_statuses=(("1-1-title", "done"),))
        exit_code = status_cli.run_status(
            _args(project="acme", reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"]["discrepancies"] == [
            {"story_key": "1.1", "kind": "done-in-ledger-not-merged", "confidence": "unconfirmed"}
        ]
        assert payload["findings"] == []
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_merged_not_done_in_ledger_is_reported_never_a_finding(
        self, tmp_path, capsys, monkeypatch
    ):
        """The live incident this story exists to catch: Epic 4's own
        stories sat at ``review`` in the tracked ledger for hours after
        their PRs had actually merged."""
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        vcs = _FakeVcs(commit_subjects_value=(_merged_subject("4.1"),))
        harness = _FakeHarness(ledger_statuses=(("4-1-title", "review"),))
        exit_code = status_cli.run_status(
            _args(project="acme", reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"]["discrepancies"] == [
            {"story_key": "4.1", "kind": "merged-not-done-in-ledger", "confidence": "confirmed"}
        ]
        assert payload["findings"] == []
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_malformed_ledger_key_is_skipped_never_a_crash(
        self, tmp_path, capsys, monkeypatch
    ):
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        vcs = _FakeVcs(commit_subjects_value=())
        harness = _FakeHarness(
            ledger_statuses=(
                ("epic-1", "done"),  # an epic marker, not a story key
                ("1-1-title", "done"),
            )
        )
        exit_code = status_cli.run_status(
            _args(project="acme", reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"]["discrepancies"] == [
            {"story_key": "1.1", "kind": "done-in-ledger-not-merged", "confidence": "unconfirmed"}
        ]
        assert payload["findings"] == []
        assert exit_code == 0

    def test_json_data_payload_matches_status_schema(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        vcs = _FakeVcs(commit_subjects_value=(_merged_subject("4.1"),))
        harness = _FakeHarness(ledger_statuses=(("4-1-title", "review"),))
        exit_code = status_cli.run_status(
            _args(project="acme", reconcile_ledger=True),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert exit_code == 0
        assert payload["data_version"] == 2
        status_schema = json.loads(_STATUS_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(instance=payload["data"], schema=status_schema)
        envelope_schema = json.loads(_ENVELOPE_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(instance=payload, schema=envelope_schema)

    def test_text_format_renders_without_crashing(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        vcs = _FakeVcs(commit_subjects_value=(_merged_subject("4.1"),))
        harness = _FakeHarness(ledger_statuses=(("4-1-title", "review"),))
        exit_code = status_cli.run_status(
            _args(project="acme", reconcile_ledger=True, format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        out = capsys.readouterr().out
        assert "--reconcile-ledger" in out
        assert "discrepancies: 1" in out
        assert "4.1 merged-not-done-in-ledger" in out
        assert exit_code == 0
