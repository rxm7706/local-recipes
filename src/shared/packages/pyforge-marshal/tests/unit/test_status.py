"""Unit tests for ``pyforge.marshal.core.status`` (Story 1.6, FR-4/FR-8,
AD-4) -- ``evaluate_homes``'s pure isolation-check logic driven entirely by
plain ``HomeFacts``/``MainCheckoutFacts`` objects (no ports, no I/O; that
lives in ``cli/init.py::run_homes`` and its own tests). Covers every row of
the spec's I/O & Edge-Case Matrix.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pytest
from pyforge.core.process import ProcessError, ProcessResult
from pyforge.core.report import BASE_ENVELOPE_SCHEMA, compose

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
from pyforge.marshal.core.policy import DEFAULT_POLICY
from pyforge.marshal.ports.harness import (
    DeferredStory,
    HarnessRunTerminalVerdict,
    RunStatusSnapshot,
    TaskPhaseSnapshot,
)
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
    home = _home(
        marker="acme\n",
        symlink=Path("projects/acme/planning-artifacts"),
        tier3_local=None,
        tier3_canonical_is_dir=False,
    )
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
        assert status._slug_from_symlink_target(target) == init_cli._slug_from_symlink_target(target)


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
    assert row["claimed_commit_sha"] == status.DomainField(value="deadbeef", domain="journal")


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
    report = status.reconcile_feed_domains(
        frozenset({key}), (status.ClaimedCommit(story_key=key, claimed_commit_sha=None),)
    )
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
    earlier = status.ClaimedCommit(story_key=key, claimed_commit_sha="earliersha", phase="review-verify")
    later = status.ClaimedCommit(story_key=key, claimed_commit_sha="donesha", phase="done")
    # Feed them in BOTH orders -- the result must not depend on input order.
    report_forward = status.reconcile_feed_domains(frozenset({key}), (earlier, later))
    report_reverse = status.reconcile_feed_domains(frozenset({key}), (later, earlier))
    assert report_forward.stories[0]["claimed_commit_sha"].value == "donesha"
    assert report_reverse.stories[0]["claimed_commit_sha"].value == "donesha"


def test_reconcile_duplicate_story_key_prefers_non_none_sha_over_none():
    key = normalize("5.2")
    no_claim = status.ClaimedCommit(story_key=key, claimed_commit_sha=None, phase="done")
    has_claim = status.ClaimedCommit(story_key=key, claimed_commit_sha="sha123", phase="dev-running")
    report = status.reconcile_feed_domains(frozenset({key}), (no_claim, has_claim))
    assert report.stories[0]["claimed_commit_sha"].value == "sha123"


# --- classify_resync_outcome -------------------------------------------------


def test_classify_resync_outcome_never_ran_reports_mrs_deploy_019():
    report, finding = status.classify_resync_outcome("echo hi", None, failure_reason="could not launch")
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
    return TaskPhaseSnapshot(story_key=story_key, phase=phase, commit_sha=None, branch="")


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
        state = status.derive_home_state(finished=True, paused_stage=None, tasks=(), supervisor_alive=False)
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
        state = status.derive_home_state(finished=False, paused_stage=None, tasks=tasks, supervisor_alive=True)
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
        state = status.derive_home_state(finished=False, paused_stage=None, tasks=(), supervisor_alive=True)
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

    # --- Story 5.8 (FR-36/AD-5): `engine_alive` is a one-directional
    # softening signal over the dead-supervisor branch -- covers every
    # `engine_alive`-related row of the spec's own I/O & Edge-Case Matrix.

    def test_engine_alive_softens_dead_supervisor_with_task_in_flight(self):
        """Matrix row: dead supervisor, engine alive, task in flight ->
        `running` -- the 2026-08-11 incident's own shape at the pure
        derivation level."""
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(_task(phase="dev-running"),),
            supervisor_alive=False,
            engine_alive=True,
        )
        assert state == "running"

    def test_engine_alive_softens_dead_supervisor_with_no_task(self):
        """Matrix row: dead supervisor, engine alive, no in-flight task ->
        `idle`."""
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(),
            supervisor_alive=False,
            engine_alive=True,
        )
        assert state == "idle"

    def test_engine_alive_softens_dead_supervisor_paused_on_escalation(self):
        """Matrix row: dead supervisor, engine alive, paused on escalation
        -> `paused-on-escalation`."""
        state = status.derive_home_state(
            finished=False,
            paused_stage="escalation",
            tasks=(),
            supervisor_alive=False,
            engine_alive=True,
        )
        assert state == "paused-on-escalation"

    def test_engine_alive_false_still_reports_unsupervised(self):
        """Matrix row: dead supervisor, engine also dead -> `unsupervised`
        (unchanged) -- only `engine_alive is True` may soften the branch,
        never `False`."""
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(_task(phase="dev-running"),),
            supervisor_alive=False,
            engine_alive=False,
        )
        assert state == "unsupervised"

    def test_engine_alive_none_still_reports_unsupervised(self):
        """Matrix row: dead supervisor, engine liveness unprobed ->
        `unsupervised` (unchanged, the safe default) -- an unprobed engine
        is never treated as confirmed alive."""
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(_task(phase="dev-running"),),
            supervisor_alive=False,
            engine_alive=None,
        )
        assert state == "unsupervised"

    def test_engine_alive_never_consulted_once_finished(self):
        """Matrix row: finished run, supervisor already exited -> `stopped`;
        `engine_alive` never consulted -- a confirmed-alive engine must not
        turn an already-finished run into anything but `stopped`."""
        state = status.derive_home_state(
            finished=True,
            paused_stage=None,
            tasks=(),
            supervisor_alive=False,
            engine_alive=True,
        )
        assert state == "stopped"

    # --- Story 25.5 (CAP-5, DW-BL011-1): the 0.11 `awaiting-operator`
    # parked state -- covers every parked row of the spec's own I/O matrix.

    def test_parked_only_run_is_awaiting_operator_not_running(self):
        """Matrix row 'Parked-only run': terminal-set fix -- before this
        story a parked task read as in-flight and the run reported
        `running` with the parked story as 'current' (the DW's mislabel)."""
        tasks = (
            _task(story_key="25.1", phase="done"),
            _task(story_key="25.2", phase="awaiting-operator"),
        )
        state = status.derive_home_state(finished=False, paused_stage=None, tasks=tasks, supervisor_alive=True)
        assert state == "awaiting-operator"

    def test_parked_plus_active_stays_running(self):
        """Matrix row 'Parked + active': a park never blocks siblings --
        a run actively driving another story stays `running`."""
        tasks = (
            _task(story_key="25.2", phase="awaiting-operator"),
            _task(story_key="25.3", phase="dev-running"),
        )
        state = status.derive_home_state(finished=False, paused_stage=None, tasks=tasks, supervisor_alive=True)
        assert state == "running"

    def test_parked_plus_finished_is_awaiting_operator_not_stopped(self):
        """Matrix row 'Parked + finished': the confirm is the next action,
        not a re-spin -- the park outranks `stopped`."""
        state = status.derive_home_state(
            finished=True,
            paused_stage=None,
            tasks=(_task(story_key="25.2", phase="awaiting-operator"),),
            supervisor_alive=False,
        )
        assert state == "awaiting-operator"

    def test_parked_plus_dead_supervisor_is_awaiting_operator_never_dead(self):
        """Matrix row 'Parked + dead supervisor': a parked run's processes
        naturally wind down while the human actions stay owed -- never
        `unsupervised`."""
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(_task(story_key="25.2", phase="awaiting-operator"),),
            supervisor_alive=False,
            engine_alive=False,
        )
        assert state == "awaiting-operator"

    def test_parked_plus_escalation_pause_stays_paused_on_escalation(self):
        """Matrix row 'Parked + escalation pause': escalation outranks the
        park -- it is run-halting by design; a park never is."""
        state = status.derive_home_state(
            finished=False,
            paused_stage="escalation",
            tasks=(_task(story_key="25.2", phase="awaiting-operator"),),
            supervisor_alive=True,
        )
        assert state == "paused-on-escalation"

    def test_escalated_only_tasks_still_report_idle_not_awaiting_operator(self):
        """Terminal-set regression guard: widening the set must not turn a
        plain all-escalated (no park) run into the new state."""
        state = status.derive_home_state(
            finished=False,
            paused_stage=None,
            tasks=(_task(phase="escalated"),),
            supervisor_alive=True,
        )
        assert state == "idle"


class TestIsRunLive:
    """Story 4.11's own pure predicate: the full boolean matrix over
    ``FleetHomeFacts``, no I/O. Deliberately reads the RAW facts, never
    ``derive_home_state``'s own state string -- see ``is_run_live``'s own
    docstring."""

    def test_no_run_ever_is_not_live(self):
        facts = status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=False)
        assert status.is_run_live(facts) is False

    def test_journal_unreadable_is_conservatively_live(self):
        """Liveness cannot be proven either way -- mirrors core/retire.py's
        own 'an unprovable fact is refused, never defaulted to delete'."""
        facts = status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=True, journal_unreadable=True)
        assert status.is_run_live(facts) is True

    def test_journal_unreadable_is_live_even_if_finished_also_claims_true(self):
        """journal_unreadable takes precedence over every other field --
        mirrors build_fleet_row's own identical precedence."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            journal_unreadable=True,
            finished=True,
            supervisor_alive=False,
        )
        assert status.is_run_live(facts) is True

    def test_finished_run_is_not_live(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=True,
            supervisor_alive=True,
        )
        assert status.is_run_live(facts) is False

    def test_dead_supervisor_on_unfinished_run_is_not_live(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            supervisor_alive=False,
        )
        assert status.is_run_live(facts) is False

    def test_alive_supervisor_with_task_in_flight_is_live(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            supervisor_alive=True,
            tasks=(_task(phase="dev-running"),),
        )
        assert status.is_run_live(facts) is True

    def test_alive_supervisor_between_stories_is_still_live(self):
        """The live-between-stories case derive_home_state's own 'idle'
        state collapses away -- is_run_live must still catch it."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            supervisor_alive=True,
            tasks=(_task(phase="done"),),
        )
        assert status.is_run_live(facts) is True

    def test_alive_supervisor_paused_on_escalation_is_live(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            supervisor_alive=True,
            paused_stage="escalation",
        )
        assert status.is_run_live(facts) is True

    def test_supervisor_alive_none_is_not_live(self):
        """Never reachable from a real `_gather_home_facts` call (a real pid
        absence degrades to journal_unreadable instead), but the pure
        predicate itself must never treat an unproven `None` as `True`."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            supervisor_alive=None,
        )
        assert status.is_run_live(facts) is False


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
            "escalation_preserve_ref": None,
            "parked_stories": (),
            "unpushed_work": None,
            "failed_patches": (),
        }
        assert finding is None

    def test_missing_spec_escalation_overrides_idle_with_awaiting_operator(self):
        """Story 28.19: remaining backlog + MRS-DISP-005 must not read idle."""
        spec_glob = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-39-4-*.md"
        facts = status.FleetHomeFacts(
            slug="pyforge-marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            missing_spec_escalation_story="39.4",
            missing_spec_escalation_glob=spec_glob,
        )
        row, finding = status.build_fleet_row(facts)
        assert finding is None
        assert row["state"] == "awaiting-operator"
        assert row["current_story"] == "39.4"
        assert row["missing_spec_escalation_glob"] == spec_glob
        assert "missing tracked spec" in row["awaiting_operator_remedy"]

    def test_journal_unreadable_reports_unknown_and_warns(self):
        facts = status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=True, journal_unreadable=True)
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

    def test_dead_supervisor_alive_engine_reports_running_not_unsupervised(self):
        """Story 5.8: `build_fleet_row` threads `facts.engine_alive` through
        to `derive_home_state` -- a dead supervisor sidecar behind a
        confirmed-alive engine with an in-flight task must report
        `"running"`, never `"unsupervised"`."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            tasks=(_task(story_key="1.1", phase="dev-running"),),
            supervisor_alive=False,
            engine_alive=True,
        )
        row, _ = status.build_fleet_row(facts)
        assert row["state"] == "running"
        assert row["current_story"] == "1.1"

    # --- Story 25.5 (CAP-5): parked rows + the two new row fields ---------

    def test_parked_row_names_state_parked_stories_and_current_story(self):
        """Matrix row 'Parked-only run' at the row level: the machine
        `state` field keeps the BARE token (the remedy suffix is the text
        projection's), `parked_stories` lists the parked keys in task
        order, and `current_story` falls back to the first parked key --
        the story the operator owes."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            tasks=(
                _task(story_key="25.1", phase="done"),
                _task(story_key="25.2", phase="awaiting-operator"),
            ),
            supervisor_alive=True,
        )
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "awaiting-operator"
        assert row["current_story"] == "25.2"
        assert row["parked_stories"] == ("25.2",)
        assert finding is None

    def test_parked_plus_active_row_never_hides_the_active_story(self):
        """Matrix row 'Parked + active': `running`, current = the ACTIVE
        story; the parked key still rides in `parked_stories` (a park
        never blocks siblings, but the operator still owes it)."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            tasks=(
                _task(story_key="25.2", phase="awaiting-operator"),
                _task(story_key="25.3", phase="dev-running"),
            ),
            supervisor_alive=True,
        )
        row, _ = status.build_fleet_row(facts)
        assert row["state"] == "running"
        assert row["current_story"] == "25.3"
        assert row["parked_stories"] == ("25.2",)

    def test_escalated_row_carries_preserve_ref(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            paused_stage="escalation",
            supervisor_alive=True,
            paused_reason="needs a human decision",
            escalated_spec_file="spec-1.2.md",
            escalated_preserve_ref="attempt-preserve/run1-abc123",
        )
        row, _ = status.build_fleet_row(facts)
        assert row["state"] == "paused-on-escalation"
        assert row["escalation_preserve_ref"] == "attempt-preserve/run1-abc123"

    def test_non_escalated_row_nulls_preserve_ref_like_the_sibling_fields(self):
        """`escalation_preserve_ref` follows the DERIVED state exactly like
        `escalation_reason`/`escalation_artifact` (the 2026-08-07 review
        gating, mirrored) -- a stale ref never leaks into a non-escalated
        row's payload."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            finished=False,
            tasks=(_task(phase="dev-running"),),
            supervisor_alive=True,
            escalated_preserve_ref="attempt-preserve/run1-abc123",
        )
        row, _ = status.build_fleet_row(facts)
        assert row["state"] == "running"
        assert row["escalation_preserve_ref"] is None

    def test_journal_unreadable_suppressed_when_factory_dispatch_is_running(self):
        facts = status.FleetHomeFacts(
            slug="marshal",
            branch="loop/pyforge-marshal",
            has_run=True,
            journal_unreadable=True,
            dispatch_story="28-9-planning-graph-retrieval-behind-the-scribe-seam",
            dispatch_engine_alive=True,
            dispatch_elapsed_seconds=12.0,
        )
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "running"
        assert row["current_story"] == "28-9-planning-graph-retrieval-behind-the-scribe-seam"
        assert row["dispatch_phase"] == "building"
        assert finding is None

    def test_chaining_phase_surfaces_running_after_land(self):
        facts = status.FleetHomeFacts(
            slug="marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story="28-9-planning-graph-retrieval-behind-the-scribe-seam",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=True,
            dispatch_landing_verdict="landed",
            dispatch_elapsed_seconds=900.0,
        )
        row, finding = status.build_fleet_row(facts)
        assert finding is None
        assert row["state"] == "running"
        assert row["dispatch_phase"] == "chaining"

    def test_completed_dispatch_with_dead_supervisor_is_not_running(self):
        facts = status.FleetHomeFacts(
            slug="scribe",
            branch="loop/pyforge-scribe",
            has_run=False,
            dispatch_story="6.3",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=False,
            dispatch_completion_verdict="completed",
            dispatch_elapsed_seconds=100000.0,
        )
        row, finding = status.build_fleet_row(facts)
        assert finding is None
        assert row["state"] == "idle"
        assert row.get("dispatch_phase") is None

    def test_terminal_completed_dispatch_clears_unreadable_loop_journal_row(self):
        facts = status.FleetHomeFacts(
            slug="scribe",
            branch="loop/pyforge-scribe",
            has_run=True,
            journal_unreadable=True,
            dispatch_story="6.3",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=False,
            dispatch_completion_verdict="completed",
        )
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "idle"
        assert finding is None


class TestDeriveDispatchPhase:
    def test_building_when_harness_alive(self):
        facts = status.FleetHomeFacts(
            slug="marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story="28-5-example",
            dispatch_engine_alive=True,
        )
        assert status.derive_dispatch_phase(facts) == "building"

    def test_verifying_when_session_dead_and_not_landed(self):
        facts = status.FleetHomeFacts(
            slug="marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story="28-5-example",
            dispatch_engine_alive=False,
            dispatch_completion_verdict="live",
        )
        assert status.derive_dispatch_phase(facts) == "verifying"

    def test_chaining_when_land_journal_succeeded(self):
        facts = status.FleetHomeFacts(
            slug="marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story="28-9-example",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=True,
            dispatch_landing_verdict="landed",
        )
        assert status.derive_dispatch_phase(facts) == "chaining"

    def test_chaining_when_completion_verdict_completed(self):
        facts = status.FleetHomeFacts(
            slug="marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story="28-9-example",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=True,
            dispatch_completion_verdict="completed",
        )
        assert status.derive_dispatch_phase(facts) == "chaining"

    def test_completed_with_dead_tail_is_not_chaining(self):
        facts = status.FleetHomeFacts(
            slug="scribe",
            branch="loop/pyforge-scribe",
            has_run=False,
            dispatch_story="6.3",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=False,
            dispatch_completion_verdict="completed",
        )
        assert status.derive_dispatch_phase(facts) is None

    def test_failed_with_dead_tail_is_not_verifying(self):
        facts = status.FleetHomeFacts(
            slug="marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story="28-13-example",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=False,
            dispatch_completion_verdict="failed",
            dispatch_verification_verdict="refused",
            dispatch_verification_failed_gate="MRS-GATE-001",
        )
        assert status.derive_dispatch_phase(facts) is None

    def test_stopped_externally_with_dead_tail_is_not_verifying(self):
        facts = status.FleetHomeFacts(
            slug="pyforge-marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story="28-23-stranded-work-signal-after-terminal-verify-fail",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=False,
            dispatch_completion_verdict="stopped_externally",
            dispatch_verification_verdict="refused",
            dispatch_verification_failed_gate="MRS-GATE-001",
        )
        assert status.derive_dispatch_phase(facts) is None

    def test_blocked_with_dead_tail_is_not_verifying(self):
        """Story 51.11 (CAP-258): a `blocked` completion verdict with a dead
        tail must resolve None like `failed`/`stopped_externally`, not fall
        through to the final `return "verifying"` -- else fleet-picture would
        show a self-halted blocked story as perpetually verifying."""
        facts = status.FleetHomeFacts(
            slug="pyforge-marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story="51-11-example",
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=False,
            dispatch_completion_verdict="blocked",
        )
        assert status.derive_dispatch_phase(facts) is None

    def test_none_without_dispatch_story(self):
        facts = status.FleetHomeFacts(slug="marshal", branch="loop/pyforge-marshal", has_run=False)
        assert status.derive_dispatch_phase(facts) is None


class TestDeriveDispatchStrandedWork:
    _STORY = "28-23-stranded-work-signal-after-terminal-verify-fail"
    _BRANCH = f"dispatch/pyforge-marshal/{_STORY}"

    def _terminal_facts(self, **overrides) -> status.FleetHomeFacts:
        base = dict(
            slug="pyforge-marshal",
            branch="loop/pyforge-marshal",
            has_run=False,
            dispatch_story=self._STORY,
            dispatch_engine_alive=False,
            dispatch_supervisor_alive=False,
            dispatch_completion_verdict="failed",
        )
        base.update(overrides)
        return status.FleetHomeFacts(**base)

    def test_unpushed_dispatch_branch_is_named(self):
        facts = self._terminal_facts()
        unpushed = {
            self._BRANCH: {
                "files": 4,
                "stat": "4 files changed",
                "remedy": f"git push origin {self._BRANCH}",
            }
        }
        signal = status.derive_dispatch_stranded_work(facts, unpushed_by_ref=unpushed)
        assert signal is not None
        assert signal["kind"] == "unpushed-branch"
        assert signal["ref"] == self._BRANCH
        assert signal["story"] == self._STORY

    def test_blocked_verdict_dead_tail_surfaces_stranded_work(self):
        """Story 51.11 (CAP-258): a `blocked` completion verdict is a
        terminal dead-tail case too -- the tuple gap would have made this
        silently return None (no stranded-work signal) instead."""
        facts = self._terminal_facts(dispatch_completion_verdict="blocked")
        unpushed = {
            self._BRANCH: {
                "files": 3,
                "stat": "3 files changed",
                "remedy": f"git push origin {self._BRANCH}",
            }
        }
        signal = status.derive_dispatch_stranded_work(facts, unpushed_by_ref=unpushed)
        assert signal is not None
        assert signal["kind"] == "unpushed-branch"

    def test_live_tail_does_not_surface_stranded_work(self):
        facts = self._terminal_facts(dispatch_supervisor_alive=True)
        unpushed = {self._BRANCH: {"files": 1, "stat": "1 file changed", "remedy": "push"}}
        assert status.derive_dispatch_stranded_work(facts, unpushed_by_ref=unpushed) is None

    def test_completed_dispatch_does_not_surface_stranded_work(self):
        facts = self._terminal_facts(dispatch_completion_verdict="completed")
        unpushed = {self._BRANCH: {"files": 1, "stat": "1 file changed", "remedy": "push"}}
        assert status.derive_dispatch_stranded_work(facts, unpushed_by_ref=unpushed) is None

    def test_detector_unavailable_is_unknown_not_clean(self):
        facts = self._terminal_facts()
        assert status.derive_dispatch_stranded_work(facts, unpushed_by_ref=None) is None

    def test_build_fleet_row_publishes_stranded_work_without_running_overlay(self):
        unpushed = {
            self._BRANCH: {
                "files": 2,
                "stat": "2 files changed",
                "remedy": f"git push origin {self._BRANCH}",
            }
        }
        facts = self._terminal_facts(
            dispatch_stranded_work=status.derive_dispatch_stranded_work(
                self._terminal_facts(), unpushed_by_ref=unpushed
            )
        )
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "idle"
        assert row.get("dispatch_phase") is None
        assert row.get("dispatch_completion_verdict") == "failed"
        assert row.get("current_story") == self._STORY
        assert row.get("dispatch_stranded_work") is not None
        assert finding is None


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
        result = status.reconcile_ledger_vs_git(frozenset({"1.1", "1.2"}), frozenset({"1.1", "1.2"}))
        assert result == ()

    def test_empty_both_sides_reports_no_discrepancies(self):
        assert status.reconcile_ledger_vs_git(frozenset(), frozenset()) == ()

    def test_done_in_ledger_not_merged(self):
        result = status.reconcile_ledger_vs_git(frozenset({"1.1"}), frozenset())
        assert result == ({"story_key": "1.1", "kind": "done-in-ledger-not-merged", "confidence": "unconfirmed"},)

    def test_merged_not_done_in_ledger(self):
        """The live incident this story exists to catch: a story git
        confirms as durably merged whose ledger status is anything other
        than done -- including absent entirely, the case exercised here."""
        result = status.reconcile_ledger_vs_git(frozenset(), frozenset({"4.1"}))
        assert result == ({"story_key": "4.1", "kind": "merged-not-done-in-ledger", "confidence": "confirmed"},)

    def test_both_directions_at_once_sorted_by_key_within_each_kind(self):
        result = status.reconcile_ledger_vs_git(frozenset({"1.2", "1.1"}), frozenset({"2.2", "2.1"}))
        assert result == (
            {"story_key": "1.1", "kind": "done-in-ledger-not-merged", "confidence": "unconfirmed"},
            {"story_key": "1.2", "kind": "done-in-ledger-not-merged", "confidence": "unconfirmed"},
            {"story_key": "2.1", "kind": "merged-not-done-in-ledger", "confidence": "confirmed"},
            {"story_key": "2.2", "kind": "merged-not-done-in-ledger", "confidence": "confirmed"},
        )

    def test_result_is_deterministic_regardless_of_set_construction_order(self):
        first = status.reconcile_ledger_vs_git(frozenset({"3.1", "1.1", "2.1"}), frozenset({"9.9", "5.5"}))
        second = status.reconcile_ledger_vs_git(frozenset({"2.1", "3.1", "1.1"}), frozenset({"5.5", "9.9"}))
        assert first == second


# =============================================================================
# Story 5.9 ("a story finished by hand is not invisible to the ledger"):
# `core.status.not_loop_native_completions`/`render_ledger_advancements` --
# pure, no I/O, no fixtures touching disk or git; every input is a plain
# value. Reported label is `"not-loop-native"` (Spec Change Log,
# 2026-08-12), never `"bmad-quick-dev"`.
# =============================================================================


class TestNotLoopNativeCompletions:
    """``not_loop_native_candidates`` models the CALLER's own already-
    computed `(corroborated_keys & full_merged_keys) - marshal_native_keys`
    difference (review fix, 2026-08-12, low-severity: this function's
    signature was narrowed to take that already-computed set directly
    instead of re-deriving it -- closing a two-places-compute-the-same-
    thing desync risk; see `cli/deploy.py::run_reconcile_completions`,
    which computes it exactly once and passes the same value to both this
    function and its own `MRS-DEPLOY-026` finding). Eligibility now also
    requires the row's CURRENT status be literally `backlog` (review fix,
    2026-08-12, medium-severity: `blocked`/`in-progress`/`optional` must
    never be silently force-advanced), so the signature takes
    `ledger_backlog_keys` -- already-filtered to that one status -- rather
    than the two `ledger_done_keys`/`ledger_all_keys` sets this function
    used to take."""

    def test_corroborated_non_native_key_at_backlog_is_advanced(self):
        """The headline case: a not-loop-native-completed story present in
        the caller's own `not_loop_native_candidates`, with a live ledger
        row at `backlog`."""
        result = status.not_loop_native_completions(
            ledger_backlog_keys=frozenset({"5.9"}),
            not_loop_native_candidates=frozenset({"5.9"}),
        )
        assert result == frozenset({"5.9"})

    def test_marshal_native_key_is_excluded_by_the_callers_own_candidate_set(self):
        """A key landed via `deploy land-story`/bmad-loop -- Story 5.4's
        own sync already owns this case -- is excluded by the CALLER's own
        `(corroborated_keys & full_merged_keys) - marshal_native_keys`
        computation before it ever reaches this function; modeled here by
        simply never including it in `not_loop_native_candidates`."""
        result = status.not_loop_native_completions(
            ledger_backlog_keys=frozenset({"4.3"}),
            not_loop_native_candidates=frozenset(),  # caller already excluded 4.3
        )
        assert result == frozenset()

    def test_uncorroborated_key_is_excluded_even_if_present_in_ledger(self):
        """A git match with no valid/durable spec -- possible cross-project
        collision -- never triggers a write on its own; the caller never
        adds it to `not_loop_native_candidates` in the first place."""
        result = status.not_loop_native_completions(
            ledger_backlog_keys=frozenset({"7.1"}),
            not_loop_native_candidates=frozenset(),
        )
        assert result == frozenset()

    def test_key_absent_from_ledger_is_excluded_never_invented(self):
        """This story's own Boundaries: "never advance a key absent from
        the ledger map entirely" -- a candidate key with no ledger row at
        all is absent from `ledger_backlog_keys` too."""
        result = status.not_loop_native_completions(
            ledger_backlog_keys=frozenset(),
            not_loop_native_candidates=frozenset({"9.1"}),
        )
        assert result == frozenset()

    def test_already_done_key_is_a_clean_no_op(self):
        """AD-21's convergence property: already `done` never re-advances,
        never re-reports -- modeled by the key being ABSENT from
        `ledger_backlog_keys` (its row is `done`, not `backlog`)."""
        result = status.not_loop_native_completions(
            ledger_backlog_keys=frozenset(),
            not_loop_native_candidates=frozenset({"5.9"}),
        )
        assert result == frozenset()

    def test_blocked_row_is_never_force_advanced(self):
        """Review fix, 2026-08-12, medium-severity: a `blocked` row is a
        DELIBERATE operator signal -- corroborated git+spec evidence must
        never silently overwrite it. Modeled by the key being absent from
        `ledger_backlog_keys` (its row is `blocked`, not `backlog`)."""
        result = status.not_loop_native_completions(
            ledger_backlog_keys=frozenset(),
            not_loop_native_candidates=frozenset({"6.1"}),
        )
        assert result == frozenset()

    def test_in_progress_row_is_never_force_advanced(self):
        result = status.not_loop_native_completions(
            ledger_backlog_keys=frozenset(),
            not_loop_native_candidates=frozenset({"6.2"}),
        )
        assert result == frozenset()

    def test_mixed_batch_advances_only_the_eligible_keys(self):
        """One key of each disqualifying shape, plus one genuinely
        eligible key, in a single call -- proves the conditions combine
        correctly, not just in isolation. `4.3` (Marshal-driven) is
        modeled as already excluded from `not_loop_native_candidates`,
        mirroring what the caller's own difference would produce; `1.1`
        is a candidate but its row is NOT `backlog` (done/blocked/etc.,
        absent from `ledger_backlog_keys`); `9.1` has no row at all."""
        result = status.not_loop_native_completions(
            ledger_backlog_keys=frozenset({"5.9"}),
            not_loop_native_candidates=frozenset({"1.1", "5.9", "9.1"}),
        )
        assert result == frozenset({"5.9"})

    def test_empty_everything_is_empty(self):
        assert (
            status.not_loop_native_completions(
                ledger_backlog_keys=frozenset(),
                not_loop_native_candidates=frozenset(),
            )
            == frozenset()
        )


class TestRenderLedgerAdvancements:
    _LEDGER = (
        "# GENERATED -- do not hand-edit.\n"
        "#\n"
        "# project: marshal\n"
        "development_status:\n"
        "  1-1-package-spine: done\n"
        "  5-8-a-dead-supervisor-sidecar: backlog\n"
        "  5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger: backlog\n"
    )

    def test_no_raw_keys_returns_the_text_unchanged(self):
        result, matched = status.render_ledger_advancements(self._LEDGER, frozenset())
        assert result == self._LEDGER
        assert matched == frozenset()

    def test_only_the_named_line_changes_byte_for_byte_otherwise(self):
        raw_key = "5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger"
        result, matched = status.render_ledger_advancements(self._LEDGER, frozenset({raw_key}))

        expected = self._LEDGER.replace(f"{raw_key}: backlog", f"{raw_key}: done")
        assert result == expected
        assert matched == frozenset({raw_key})
        # Every OTHER line is untouched, including the sibling backlog row.
        assert "5-8-a-dead-supervisor-sidecar: backlog" in result
        assert "1-1-package-spine: done" in result
        assert "# project: marshal" in result

    def test_multiple_raw_keys_all_advance_in_one_pass(self):
        raw_keys = frozenset(
            {
                "5-8-a-dead-supervisor-sidecar",
                "5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger",
            }
        )
        result, matched = status.render_ledger_advancements(self._LEDGER, raw_keys)
        assert "5-8-a-dead-supervisor-sidecar: done" in result
        assert "5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger: done" in result
        assert "1-1-package-spine: done" in result  # unaffected, already done
        assert matched == raw_keys

    def test_a_key_already_done_is_rewritten_to_done_again_idempotently(self):
        result, matched = status.render_ledger_advancements(self._LEDGER, frozenset({"1-1-package-spine"}))
        assert result == self._LEDGER  # `done` -> `done` is byte-identical
        assert matched == frozenset({"1-1-package-spine"})

    def test_unmatched_raw_key_is_silently_ignored_never_raises(self):
        result, matched = status.render_ledger_advancements(self._LEDGER, frozenset({"99-9-nonexistent"}))
        assert result == self._LEDGER
        assert matched == frozenset()

    def test_partial_match_reports_only_what_actually_matched(self):
        """Review fix, 2026-08-12, high-severity: the second key does not
        exist in the ledger text -- the caller must see it as UNMATCHED,
        never over-reported as advanced."""
        raw_key = "5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger"
        result, matched = status.render_ledger_advancements(self._LEDGER, frozenset({raw_key, "99-9-nonexistent"}))
        assert f"{raw_key}: done" in result
        assert matched == frozenset({raw_key})

    def test_indentation_is_preserved(self):
        raw_key = "5-9-a-story-finished-by-hand-isnt-invisible-to-the-ledger"
        result, _matched = status.render_ledger_advancements(self._LEDGER, frozenset({raw_key}))
        assert f"  {raw_key}: done" in result
        assert f"   {raw_key}: done" not in result

    def test_a_key_that_is_a_textual_prefix_of_another_never_cross_matches(self):
        """Exact match on the WHOLE pre-colon segment, never a prefix
        test -- a hypothetical "5-9" must never match the real
        "5-9-a-story-finished-by-hand..." row."""
        result, matched = status.render_ledger_advancements(self._LEDGER, frozenset({"5-9"}))
        assert result == self._LEDGER
        assert matched == frozenset()

    def test_trailing_newline_is_preserved_exactly(self):
        text = "development_status:\n  5-9-x: backlog\n"
        result, matched = status.render_ledger_advancements(text, frozenset({"5-9-x"}))
        assert result == "development_status:\n  5-9-x: done\n"
        assert result.endswith("\n")
        assert matched == frozenset({"5-9-x"})

    def test_no_trailing_newline_is_preserved_exactly(self):
        text = "development_status:\n  5-9-x: backlog"
        result, matched = status.render_ledger_advancements(text, frozenset({"5-9-x"}))
        assert result == "development_status:\n  5-9-x: done"
        assert not result.endswith("\n\n")
        assert matched == frozenset({"5-9-x"})

    def test_crlf_line_endings_are_preserved_line_by_line(self):
        """Review fix, 2026-08-12, medium-severity: a CRLF-checked-out
        file used to have exactly its matched line's ending silently
        downgraded to bare `\\n`, producing a file with MIXED endings --
        every line's own ending, matched or not, must round-trip exactly."""
        text = "development_status:\r\n  5-8-a: backlog\r\n  5-9-x: backlog\r\n"
        result, matched = status.render_ledger_advancements(text, frozenset({"5-9-x"}))
        assert result == "development_status:\r\n  5-8-a: backlog\r\n  5-9-x: done\r\n"
        assert matched == frozenset({"5-9-x"})

    def test_trailing_comment_on_a_matched_line_is_preserved(self):
        """Review fix, 2026-08-12, medium-severity: a trailing `# comment`
        after the status value used to be silently dropped on a matched
        line."""
        text = "development_status:\n  5-9-x: backlog  # some note\n"
        result, matched = status.render_ledger_advancements(text, frozenset({"5-9-x"}))
        assert result == "development_status:\n  5-9-x: done  # some note\n"
        assert matched == frozenset({"5-9-x"})


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
        commit_subjects_error: str = "cannot read commit history",
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
        # Story 4.14 (review finding, 2026-08-10, pass 5): the raised text
        # is now settable, because `GitVcs` wraps git's OWN stderr and git's
        # stderr for the exact failure `MRS-STATUS-011`'s cause 1 exists for
        # -- a missing local `main` -- is THREE lines. A single-line default
        # made every existing test blind to interpolating it unsanitized.
        self.commit_subjects_error = commit_subjects_error
        # Story 4.14 (review finding, 2026-08-10, pass 4): "`main`'s commit
        # subjects are read at most ONCE per invocation and reused for every
        # home" is a load-bearing invariant -- KEEP instruction #3 in this
        # story's own spec, and a claim asserted at four separate doc sites
        # -- but nothing observed it, so deleting the `main_subjects_
        # attempted` guard left the whole suite green while turning one `git
        # log` per sweep into one per home. Counted here, mirroring
        # `_FakeHarness.calls`'s own convention in this same file.
        self.commit_subjects_calls: list[tuple[Path, str]] = []

    def repo_common_root(self, start):
        if self.repo_root_raises:
            raise VcsCommandError("cannot resolve repo root")
        return self.repo_root_value

    def list_worktrees(self, repo_root):
        if self.worktrees_raise:
            raise VcsCommandError("git worktree list failed")
        return self.worktrees

    def commit_subjects(self, repo_root, ref):
        self.commit_subjects_calls.append((repo_root, ref))
        if self.commit_subjects_raises:
            raise VcsCommandError(self.commit_subjects_error)
        return self.commit_subjects_value


class _FakeHarness:
    """Keyed by ``(str(project), run_id)`` -- mirrors ``test_retire.py::
    _FakeHarness``'s own convention, widened by ``run_id`` since this
    command may resolve a distinct ``harness_run_id`` per project."""

    def __init__(
        self,
        snapshots: dict[tuple[str, str], RunStatusSnapshot | None] | None = None,
        *,
        terminal_verdicts: dict[tuple[str, str], HarnessRunTerminalVerdict] | None = None,
        ledger_statuses: tuple[tuple[str, str], ...] = (),
        ledger_raises: bool = False,
        ledger_error_message: str = "sprint status file not found",
    ) -> None:
        self.snapshots = snapshots or {}
        self.terminal_verdicts = terminal_verdicts or {}
        self.calls: list[tuple[str, str]] = []
        self.terminal_verdict_calls: list[tuple[str, str]] = []
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

    def run_terminal_verdict(self, project, run_id):
        self.terminal_verdict_calls.append((str(project), run_id))
        return self.terminal_verdicts.get((str(project), run_id), "unknown")

    def ledger_story_statuses(self, path):
        self.ledger_calls.append(path)
        if self.ledger_raises:
            raise HarnessError(self.ledger_error_message)
        return self.ledger_statuses


class _FakeProcess:
    """Story 5.5 extends this fake with a ``run`` method for
    ``_gather_unpushed_work_findings``'s own single ``ProcessPort.run``
    call. Defaults to a clean, findings-free detector response (valid JSON,
    an empty ``findings`` list) so every PRE-5.5 test that constructs a
    bare ``_FakeProcess()`` (never configuring ``run_*``) keeps its own
    already-established assertions -- a `run` call this test never
    anticipated must never inject a surprise finding into its own verdict."""

    def __init__(
        self,
        alive_pids: frozenset[int] = frozenset(),
        *,
        run_result: ProcessResult | None = None,
        run_raises: bool = False,
    ) -> None:
        self.alive_pids = alive_pids
        self.calls: list[int] = []
        self.run_calls: list[tuple[tuple[str, ...], Path]] = []
        self.run_result = run_result
        self.run_raises = run_raises

    def is_alive(self, pid: int) -> bool:
        self.calls.append(pid)
        return pid in self.alive_pids

    def run(self, argv, *, cwd, timeout_s=None):
        self.run_calls.append((tuple(argv), cwd))
        if self.run_raises:
            raise ProcessError("cannot launch the unpushed-work detector")
        if self.run_result is not None:
            return self.run_result
        return ProcessResult(
            returncode=0,
            stdout=json.dumps({"base": "origin/main", "findings": []}),
            stderr="",
        )


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


def _resume_outcome_line(
    run_id: str,
    *,
    pid: int | None,
    harness_run_id: str | None,
    ts: str = "2026-08-06T00:10:00.000Z",
) -> str:
    """A minimal, valid ``phase: outcome`` ``run-resume`` journal line --
    the SAME shape as ``_outcome_line`` but ``kind="run-resume"``, the
    kind a `bmad-loop resume` journals for a run that already has an
    earlier ``run-launch`` entry. Story 5.8 (code review, 2026-08-12,
    Blind Hunter): exercises the resume branch of
    ``_gather_run_journal_facts``'s launch-pid resolution, which a dead
    engine-liveness regression could silently never reach again."""
    entry = build_entry(
        id=JournalEntryId("spin-1", 2),
        ts=ts,
        run_id=run_id,
        kind="run-resume",
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("spin-1", 0),
        payload={"pid": pid, "harness_run_id": harness_run_id},
    )
    return prepare_for_write(entry).line


def _supervisor_attach_line(run_id: str, *, pid: int, ts: str = "2026-08-06T00:00:30.000Z") -> str:
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


def _local_run_id(launch_ts: str, *, offset_seconds: float, suffix: str = "abcd") -> str:
    """A bmad-loop-shaped run id (``YYYYMMDD-HHMMSS-<suffix>``) whose
    embedded prefix is ``launch_ts`` (an ISO-8601 UTC ``_outcome_line``
    timestamp) plus ``offset_seconds``, converted to the SAME local
    timezone ``_discover_harness_run_id_by_filesystem`` itself converts
    to (``.astimezone()``, no argument) -- keeps these tests correct
    under any timezone the suite happens to run in, mirroring the
    production conversion exactly rather than assuming UTC."""
    launched_at = datetime.fromisoformat(launch_ts.replace("Z", "+00:00"))
    local = (launched_at + timedelta(seconds=offset_seconds)).astimezone()
    return f"{local.strftime('%Y%m%d-%H%M%S')}-{suffix}"


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
    escalated_preserve_ref: str | None = None,
    sweeps_refused: dict[str, str] | None = None,
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
        escalated_preserve_ref=escalated_preserve_ref,
        sweeps_refused=sweeps_refused if sweeps_refused is not None else {},
    )


class TestDiscoverHarnessRunIdByFilesystem:
    """Isolated unit tests of ``_discover_harness_run_id_by_filesystem``
    itself (adversarial review, 2026-08-15, second pass -- Blind Hunter's
    own LOW finding: coverage was previously only indirect, through the
    full ``run_status`` path with exactly one seeded directory)."""

    def test_no_runs_directory_returns_none(self, tmp_path):
        launched_at = datetime(2026, 8, 6, tzinfo=timezone.utc)
        assert status_cli._discover_harness_run_id_by_filesystem(tmp_path, launched_at) is None

    def test_launched_at_none_returns_none_without_touching_disk(self, tmp_path):
        # No `.bmad-loop/runs/` created at all -- if this read the
        # filesystem before checking `launched_at`, it would still
        # correctly return None here, so this test only pins the
        # documented short-circuit contract, not a behavior difference.
        assert status_cli._discover_harness_run_id_by_filesystem(tmp_path, None) is None

    def test_picks_the_closest_candidate_not_the_lexicographic_latest(self, tmp_path):
        launch_ts = "2026-08-06T00:00:00.000Z"
        launched_at = datetime.fromisoformat(launch_ts.replace("Z", "+00:00"))
        closest = _local_run_id(launch_ts, offset_seconds=10)
        # Lexicographically LATER than `closest` (later suffix), but
        # further away in real time -- must NOT win.
        farther_but_later_name = _local_run_id(launch_ts, offset_seconds=200, suffix="zzzz")
        for run_id in (closest, farther_but_later_name):
            d = tmp_path / ".bmad-loop" / "runs" / run_id
            d.mkdir(parents=True)
            (d / "state.json").write_text("{}", encoding="utf-8")

        result = status_cli._discover_harness_run_id_by_filesystem(tmp_path, launched_at)

        assert result == closest

    def test_ignores_a_directory_with_no_state_json(self, tmp_path):
        launch_ts = "2026-08-06T00:00:00.000Z"
        launched_at = datetime.fromisoformat(launch_ts.replace("Z", "+00:00"))
        no_state = _local_run_id(launch_ts, offset_seconds=1)
        (tmp_path / ".bmad-loop" / "runs" / no_state).mkdir(parents=True)
        # (deliberately no state.json written inside `no_state`)

        result = status_cli._discover_harness_run_id_by_filesystem(tmp_path, launched_at)

        assert result is None

    def test_ignores_a_plain_file_entry(self, tmp_path):
        launch_ts = "2026-08-06T00:00:00.000Z"
        launched_at = datetime.fromisoformat(launch_ts.replace("Z", "+00:00"))
        runs_dir = tmp_path / ".bmad-loop" / "runs"
        runs_dir.mkdir(parents=True)
        stray_name = _local_run_id(launch_ts, offset_seconds=1)
        (runs_dir / stray_name).write_text("not a directory", encoding="utf-8")

        result = status_cli._discover_harness_run_id_by_filesystem(tmp_path, launched_at)

        assert result is None

    def test_ignores_a_directory_whose_name_does_not_parse_as_a_timestamp(self, tmp_path):
        launch_ts = "2026-08-06T00:00:00.000Z"
        launched_at = datetime.fromisoformat(launch_ts.replace("Z", "+00:00"))
        d = tmp_path / ".bmad-loop" / "runs" / "not-a-timestamp-shaped-name"
        d.mkdir(parents=True)
        (d / "state.json").write_text("{}", encoding="utf-8")

        result = status_cli._discover_harness_run_id_by_filesystem(tmp_path, launched_at)

        assert result is None


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

    def test_home_with_running_supervisor_and_in_flight_task_is_running(self, tmp_path, capsys, monkeypatch):
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
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
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
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): _snapshot(paused_stage="escalation")})
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
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): _snapshot(finished=True)})
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

    def test_home_with_dead_supervisor_but_alive_engine_is_not_unsupervised(self, tmp_path, capsys, monkeypatch):
        """Story 5.8 (2026-08-11 incident): the supervisor pid (5252) is
        journaled and dead while the DIFFERENT harness/launch pid (4242,
        the engine) is alive -- this test used to assert `unsupervised`
        for exactly this scenario (code review, 2026-08-07, Blind Hunter's
        own worked case for a DIFFERENT bug: probing the wrong pid for
        supervisor liveness). Now that `_gather_home_facts` also probes
        the launch pid as `engine_alive`, a crashed supervisor with the
        watched harness process still running must report the run's real
        state (`running`, from the in-flight task), never `unsupervised`."""
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
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
            }
        )
        # 4242 (the harness/engine) is alive; 5252 (the supervisor) is NOT.
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
        assert payload["data"]["homes"][0]["state"] == "running"
        assert exit_code == 0

    def test_home_with_supervisor_and_engine_both_dead_is_unsupervised(self, tmp_path, capsys, monkeypatch):
        """The genuinely-stalled case this story must NOT soften: both the
        supervisor pid (5252) and the harness/engine pid (4242) are dead
        -- `engine_alive` reads `False`, which never softens the branch,
        so the row still reports `unsupervised` exactly as before this
        story."""
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
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
            }
        )
        # Neither 4242 (the engine) nor 5252 (the supervisor) is alive.
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
        assert payload["data"]["homes"][0]["state"] == "unsupervised"
        assert exit_code == 0

    def test_home_with_supervisor_never_attached_and_engine_alive_reproduces_2026_08_11(
        self, tmp_path, capsys, monkeypatch
    ):
        """The exact 2026-08-11 reproduction (spec's own I/O matrix row):
        a run resumed via a bare `bmad-loop resume` that never re-spawns a
        supervisor sidecar at all -- no `supervisor-attach`/`supervisor-
        heartbeat` entry is ever journaled, so `supervisor_pid` is `None`
        and `supervisor_alive` degrades to `False` (`_gather_home_facts`'s
        own "never attached is treated identically to confirmed-dead"
        rule) -- while the engine's own launch pid is alive and a story is
        in flight. The row must derive its real state, never
        `unsupervised`."""
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[_outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1")],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
            }
        )
        # Only 4242 (the engine) is alive -- no supervisor pid was ever
        # journaled at all.
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
        state = payload["data"]["homes"][0]["state"]
        assert state != "unsupervised"
        assert state == "running"
        assert exit_code == 0

    def test_home_with_supervisor_never_attached_and_engine_dead_is_unsupervised(self, tmp_path, capsys, monkeypatch):
        """Acceptance criterion: the IDENTICAL scenario to the 2026-08-11
        reproduction above (no supervisor pid ever journaled) except the
        engine process has ALSO exited -- the row must still report
        `unsupervised`, since `engine_alive` reads `False`, which never
        softens the branch."""
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[_outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1")],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
            }
        )
        # Neither pid is alive: no supervisor pid was ever journaled, and
        # the engine's own launch pid (4242) has also exited.
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
        assert payload["data"]["homes"][0]["state"] == "unsupervised"
        assert exit_code == 0

    def test_engine_alive_reflects_the_resumed_pid_not_the_original_launch_pid(self, tmp_path, capsys, monkeypatch):
        """Code review (2026-08-12, Blind Hunter, Story 5.8): a run that
        was launched, then resumed under a NEW pid (the original launch
        process exited, `bmad-loop resume` spawned a different one) --
        `journal_facts.launch_pid` must reflect the RESUME entry's pid,
        not stay pinned to the original launch entry's now-dead one, or
        `engine_alive` silently reads `False` for every resumed run and
        this story's own fix never actually fires for the scenario it
        exists to fix."""
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[
                _outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
                _resume_outcome_line("acme-run1", pid=7777, harness_run_id="hrid-1"),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
            }
        )
        # 4242 (the ORIGINAL launch pid) is dead; 7777 (the resumed pid)
        # is alive; no supervisor pid was ever journaled.
        process = _FakeProcess(alive_pids=frozenset({7777}))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["homes"][0]["state"] == "running"
        assert exit_code == 0

    def test_dead_supervisor_alive_engine_state_matches_across_text_and_json(self, tmp_path, capsys, monkeypatch):
        """Acceptance criterion (AD-14 parity): a dead-supervisor-alive-
        engine row must carry the SAME derived state under both
        `--format text` and `--format json` -- the text view is a pure
        projection of the same envelope, never a second, independently
        derived rendering."""
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
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
            }
        )
        process = _FakeProcess(alive_pids=frozenset({4242}))

        exit_code = status_cli.run_status(
            _args(format="json"),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )
        json_state = _payload(capsys)["data"]["homes"][0]["state"]
        assert exit_code == 0

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )
        text_out = capsys.readouterr().out
        assert exit_code == 0

        assert json_state == "running"
        assert f": {json_state} " in text_out

    def test_missing_journal_reports_unknown_and_warns(self, tmp_path, capsys, monkeypatch):
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

    def test_poisoned_harness_run_id_recovers_via_filesystem_discovery(self, tmp_path, capsys, monkeypatch):
        """2026-08-15, ``spec-marshal-status-harness-run-id-poisoning``
        CAP-1: a launch-time poll timeout (``MRS-SPIN-004``) journals
        ``harness_run_id: null`` PERMANENTLY -- reproduced live against a
        real, healthy ``pyforge-doctor`` run that reported `unknown` for
        its entire life despite a real, readable bmad-loop run directory
        sitting on disk the whole time. This test seeds exactly that
        shape, PLUS a supervisor-attach line and a stale, out-of-window
        sibling run directory -- proving both real recovery (a healthy
        `running` state, not just an unattributed `current_story`) and
        that the discovery correctly ignores an unrelated older run
        sitting in the same `.bmad-loop/runs/` directory (adversarial
        review, 2026-08-15, second pass: a bare single-directory fixture
        does not exercise the disambiguation the fix actually needs)."""
        launch_ts = "2026-08-06T00:00:00.000Z"
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[
                _outcome_line("acme-run1", pid=4242, harness_run_id=None, ts=launch_ts),
                _supervisor_attach_line("acme-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        correct_id = _local_run_id(launch_ts, offset_seconds=8)  # 8s after launch
        stale_id = _local_run_id(launch_ts, offset_seconds=-3 * 3600)  # 3h before -- must be ignored
        for run_id in (correct_id, stale_id):
            run_dir_bmad = home / ".bmad-loop" / "runs" / run_id
            run_dir_bmad.mkdir(parents=True)
            (run_dir_bmad / "state.json").write_text("{}", encoding="utf-8")
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            snapshots={
                (str(home), correct_id): _snapshot(
                    finished=False, tasks=(_task(story_key="9.1", phase="dev-running"),)
                ),
                # A DIFFERENT run's snapshot -- if the stale sibling were
                # ever wrongly picked, this is what would leak into the row.
                (str(home), stale_id): _snapshot(finished=True),
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
        row = payload["data"]["homes"][0]
        assert row["state"] == "running"
        assert row["current_story"] == "9.1"
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-002" not in codes
        assert exit_code == 0

    def test_poisoned_harness_run_id_with_no_run_dir_still_reports_unknown(self, tmp_path, capsys, monkeypatch):
        """CAP-2 regression guard: the filesystem fallback must not turn
        a GENUINELY unrecoverable poisoned journal into a false-positive
        state. No `.bmad-loop/runs/` directory exists at all here --
        `MRS-STATUS-002`/`unknown` must fire exactly as it did before this
        fallback existed."""
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[_outcome_line("acme-run1", pid=4242, harness_run_id=None)],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        # No `.bmad-loop/runs/` directory created at all.
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

    def test_poisoned_harness_run_id_only_stale_siblings_still_reports_unknown(self, tmp_path, capsys, monkeypatch):
        """CAP-2 regression guard, disambiguation variant: real
        `.bmad-loop/runs/` entries exist, but ALL of them fall outside the
        correlation window -- the fallback must refuse to guess rather
        than attribute a stale, unrelated run's state to this home."""
        launch_ts = "2026-08-06T00:00:00.000Z"
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[_outcome_line("acme-run1", pid=4242, harness_run_id=None, ts=launch_ts)],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        stale_id = _local_run_id(launch_ts, offset_seconds=-2 * 24 * 3600)  # 2 days before
        stale_dir = home / ".bmad-loop" / "runs" / stale_id
        stale_dir.mkdir(parents=True)
        (stale_dir / "state.json").write_text("{}", encoding="utf-8")
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        # A snapshot IS registered for the stale id -- if it were ever
        # (wrongly) selected, this would prove it by returning "stopped"
        # instead of "unknown".
        harness = _FakeHarness(snapshots={(str(home), stale_id): _snapshot(finished=True)})

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
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

    def test_malformed_journal_no_recoverable_pid_reports_unknown_and_warns(self, tmp_path, capsys, monkeypatch):
        run_dir = _seed_run_journal(tmp_path, run_id="acme-run1", lines=["{not valid json at all"])
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

    def test_budget_consumed_reads_last_journaled_usage_observation(self, tmp_path, capsys, monkeypatch):
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[
                _outcome_line("acme-run1", pid=4242, harness_run_id="hrid-1"),
                _supervisor_attach_line("acme-run1", pid=5252),
                _budget_usage_line("acme-run1", cost_estimate=1000),
                _budget_usage_line("acme-run1", cost_estimate=2500, ts="2026-08-06T00:10:00.000Z"),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=())})
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
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=())})
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
        worktrees = tuple(WorktreeEntry(path=tmp_path / "loop-homes" / slug, branch=f"loop/{slug}") for slug in slugs)
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

    def test_fleet_summary_sorts_escalated_rows_first(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None, "gamma": None})
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
        homes = {slug: tmp_path / "loop-homes" / slug for slug in ("acme", "beta", "gamma")}
        vcs = _FakeVcs(
            worktrees=tuple(
                WorktreeEntry(path=homes[slug], branch=f"loop/{slug}") for slug in ("acme", "beta", "gamma")
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

    def test_escalations_flag_with_zero_matches_is_a_clean_empty_list(self, tmp_path, capsys, monkeypatch):
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

    def test_escalations_flag_with_matches_filters_to_only_escalated(self, tmp_path, capsys, monkeypatch):
        run_dir_beta = _seed_run_journal(
            tmp_path,
            run_id="beta-run1",
            lines=[
                _outcome_line("beta-run1", pid=4242, harness_run_id="hrid-beta"),
                _supervisor_attach_line("beta-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": run_dir_beta})
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

    def test_escalations_flag_combined_with_project_scope(self, tmp_path, capsys, monkeypatch):
        run_dir_beta = _seed_run_journal(
            tmp_path,
            run_id="beta-run1",
            lines=[
                _outcome_line("beta-run1", pid=4242, harness_run_id="hrid-beta"),
                _supervisor_attach_line("beta-run1", pid=5252),
            ],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": run_dir_beta})
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


def _write_dispatch_run_journal(
    repo_root: Path,
    slug: str,
    run_id: str,
    *,
    harness_profile: str,
    layer_savings: dict[str, object],
) -> None:
    """Story 46.5 (CAP-193) test-fixture helper -- writes one dispatch-run's
    ``journal.jsonl`` under ``<repo_root>/_bmad-output/projects/<slug>/
    implementation-artifacts/dispatch-runs/<run_id>/`` (a DIFFERENT tree
    from the loop-home's own ``.bmad-loop/runs/`` journal this file's other
    fixtures seed): one ``dispatch-launch`` outcome entry naming
    ``harness_profile``, then one ``budget-usage`` entry carrying
    ``layer_savings`` -- mirrors ``test_layer_savings_sources.py::
    _write_run_journal``'s shape."""
    run_dir = repo_root / "_bmad-output/projects" / slug / "implementation-artifacts/dispatch-runs" / run_id
    run_dir.mkdir(parents=True)
    lines = [
        json.dumps(
            {
                "kind": "dispatch-launch",
                "phase": "outcome",
                "payload": {"ok": True, "harness_profile": harness_profile},
            }
        ),
        json.dumps(
            {
                "kind": "budget-usage",
                "phase": "observation",
                "payload": {"layer_savings": layer_savings},
            }
        ),
    ]
    (run_dir / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestFormatRollupByHarness:
    """Story 46.5 (CAP-193): pure formatter unit tests for
    ``_format_rollup_by_harness``, sibling of ``_format_savings_summary``."""

    def test_empty_and_no_data_statuses_render_blank(self) -> None:
        assert status_cli._format_rollup_by_harness({}) == ""
        assert status_cli._format_rollup_by_harness({"status": "no-dispatch-journals", "harnesses": {}}) == ""
        assert status_cli._format_rollup_by_harness({"status": "no-savings-samples", "harnesses": {}}) == ""

    def test_renders_both_harnesses_own_currency_no_blended_total(self) -> None:
        rollup = {
            "status": "ok",
            "harnesses": {
                "claude": {
                    "currency": "usd",
                    "silent": {"output_compression_saved": [500]},
                    "configured": {"wire_compression_saved": [200]},
                    "runs": 1,
                },
                "cursor": {
                    "currency": "quota-burn",
                    "silent": {"derived_context_cache_hits": [3]},
                    "configured": {},
                    "runs": 1,
                },
            },
        }
        text = status_cli._format_rollup_by_harness(rollup)
        assert "usd" in text
        assert "quota-burn" in text
        assert "claude" in text and "cursor" in text
        # No raw dict repr() leakage (the exact shape the spec calls out).
        assert "{'output_compression_saved'" not in text
        # No blended cross-harness total anywhere in the rendering.
        assert "total" not in text.lower()

    def test_formats_byte_and_graph_hits_values_without_repr(self) -> None:
        rollup = {
            "status": "ok",
            "harnesses": {
                "claude": {
                    "currency": "usd",
                    "silent": {
                        "output_compression_saved": [500, 1536],
                        "graph_hits_vs_file_reads": [
                            (12, 3),
                            "unavailable: no codegraph stats",
                        ],
                    },
                    "configured": {"wire_compression_saved": [2048]},
                    "runs": 2,
                },
            },
        }
        text = status_cli._format_rollup_by_harness(rollup)
        # Byte-valued keys go through `_format_bytes` per element, not a
        # raw int/list.
        assert "output_compression_saved=500B, 1.5KB" in text
        assert "wire_compression_saved=2.0KB" in text
        # `graph_hits_vs_file_reads`: tuple -> "hits/reads", string element
        # (a combined error/unavailable reason) passes through as-is.
        assert "graph_hits_vs_file_reads=12/3, unavailable: no codegraph stats" in text
        # No raw Python list/tuple repr() anywhere in the rendering.
        assert "[500" not in text
        assert "(12, 3)" not in text


class TestSavingsRollupByHarness:
    """Story 46.5 (CAP-193): ``run_status``-level envelope wiring."""

    def test_project_scoped_status_carries_rollup(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(
            repo_root_value=tmp_path,
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        )
        _write_dispatch_run_journal(
            tmp_path,
            "acme",
            "run-claude",
            harness_profile="claude",
            layer_savings={"output_compression_saved": 500},
        )
        _write_dispatch_run_journal(
            tmp_path,
            "acme",
            "run-cursor",
            harness_profile="cursor",
            layer_savings={"derived_context_cache_hits": 3},
        )

        exit_code = status_cli.run_status(
            _args(project="acme"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        rollup = payload["data"]["savings_rollup_by_harness"]
        assert rollup["status"] == "ok"
        assert rollup["harnesses"]["claude"]["currency"] == "usd"
        assert rollup["harnesses"]["cursor"]["currency"] == "quota-burn"
        assert exit_code == 0

        exit_code = status_cli.run_status(
            _args(project="acme", format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        text_out = capsys.readouterr().out
        assert exit_code == 0
        assert "usd" in text_out
        assert "quota-burn" in text_out

    def test_whole_fleet_status_has_no_rollup_key(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(
            repo_root_value=tmp_path,
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert "savings_rollup_by_harness" not in payload["data"]
        assert exit_code == 0


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
            "sweeps_refused": None,
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
        facts = status.RunDetailFacts(project="acme", run_id="acme-run1", found=True, state_readable=True)
        row, finding = status.build_run_detail(facts)
        assert row["stories"] == []
        assert finding is None

    def test_story_with_gate_verdict_is_named(self):
        task = TaskPhaseSnapshot(story_key="1.1", phase="done", commit_sha="cafe123", branch="")
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
                "preserve_ref": None,
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
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
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
                "preserve_ref": None,
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

    # --- Story 25.5 (CAP-5): preserve_ref + sweeps_refused ------------------

    def test_story_rows_carry_preserve_ref_verbatim(self):
        """Matrix row 'preserve_ref present': the recovery pointer is
        reported VERBATIM (never re-validated against git) on the task's
        own row."""
        task = TaskPhaseSnapshot(
            story_key="1.4",
            phase="escalated",
            commit_sha=None,
            preserve_ref="attempt-preserve/run1-abc123",
        )
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            tasks=(task,),
        )
        row, _ = status.build_run_detail(facts)
        assert row["stories"][0]["preserve_ref"] == "attempt-preserve/run1-abc123"

    def test_deferred_rows_carry_preserve_ref_verbatim(self):
        deferred_story = DeferredStory(
            story_key="1.2",
            reason="verify exhausted",
            attempt=2,
            branch="",
            worktree_path="",
            spec_file=None,
            preserve_ref="refs/attempt-preserve-dirty/run1-def456",
        )
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            deferred=(deferred_story,),
        )
        row, _ = status.build_run_detail(facts)
        assert row["deferred"][0]["preserve_ref"] == "refs/attempt-preserve-dirty/run1-def456"

    def test_sweeps_refused_dict_is_carried_verbatim(self):
        """Matrix row 'sweeps_refused': trigger -> reason slug, the closed
        `SWEEP_REFUSED_*` vocabulary, reported as-is."""
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            sweeps_refused={"epic-1": "dirty"},
        )
        row, _ = status.build_run_detail(facts)
        assert row["sweeps_refused"] == {"epic-1": "dirty"}

    def test_sweeps_refused_empty_is_reported_as_empty_not_null(self):
        """Matrix row 'sweeps_refused empty': `{}` = a READABLE state that
        refused nothing -- distinct from null (unreadable)."""
        facts = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=True,
            sweeps_refused={},
        )
        row, _ = status.build_run_detail(facts)
        assert row["sweeps_refused"] == {}

    def test_sweeps_refused_unreadable_state_reports_null_never_fabricated(self):
        """Matrix row 'sweeps_refused unreadable': null, never a fabricated
        `{}`-clean -- both via the facts-level `None` and via
        `state_readable=False` (the same gating every sibling
        snapshot-sourced field already follows)."""
        no_snapshot = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=False,
        )
        row, _ = status.build_run_detail(no_snapshot)
        assert row["sweeps_refused"] is None

        stale_dict = status.RunDetailFacts(
            project="acme",
            run_id="acme-run1",
            found=True,
            state_readable=False,
            sweeps_refused={"epic-1": "dirty"},
        )
        row, _ = status.build_run_detail(stale_dict)
        assert row["sweeps_refused"] is None

    def test_render_story_key_best_effort_renders_dot_form(self):
        key = normalize("1.2")
        assert status._render_story_key_best_effort(str(key)) == "1.2"

    def test_render_story_key_best_effort_falls_back_to_raw_on_unparseable(self):
        assert status._render_story_key_best_effort("not-a-story-key") == ("not-a-story-key")


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
    return tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs" / run_id


def _seed_run_detail_journal(tmp_path: Path, *, slug: str, run_id: str, lines: list[str]) -> Path:
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

    def test_repo_root_failure_never_fabricates_a_confirmed_absent_run(self, capsys):
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

    def test_run_id_with_no_matching_directory_reports_mrs_status_004(self, tmp_path, capsys):
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

    def test_full_run_detail_reports_stories_gate_verdicts_budget_and_open_intent(self, tmp_path, capsys):
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
                    run_id,
                    story_key="1.1",
                    cost_estimate=1000,
                    ts="2026-08-06T00:05:00.000Z",
                ),
                _budget_usage_line(
                    run_id,
                    story_key="1.1",
                    cost_estimate=1500,
                    ts="2026-08-06T00:06:00.000Z",
                ),
                _budget_usage_line(
                    run_id,
                    story_key="1.2",
                    cost_estimate=300,
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
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=tasks)})

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

    def test_run_detail_threads_sweeps_refused_from_the_snapshot(self, tmp_path, capsys):
        """Story 25.5 (CAP-5): `_run_detail` threads the snapshot's own
        `sweeps_refused` dict through to the row; with NO snapshot at all
        (no attached loop home) the field reports null -- never a
        fabricated `{}`-clean."""
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
            snapshots={
                (str(home), "hrid-1"): _snapshot(
                    finished=False,
                    tasks=(_task(story_key="1.1", phase="done"),),
                    sweeps_refused={"epic-1": "dirty"},
                )
            }
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
        assert payload["data"]["sweeps_refused"] == {"epic-1": "dirty"}
        assert exit_code == 0

        # No attached loop home -> no snapshot -> null, with the reused
        # MRS-STATUS-002 degrade (unchanged behavior for every sibling
        # snapshot-sourced field).
        vcs_no_home = _FakeVcs(repo_root_value=tmp_path, worktrees=())
        exit_code = status_cli.run_status(
            _args(project=slug, run=run_id),
            vcs=vcs_no_home,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert payload["data"]["sweeps_refused"] is None
        assert exit_code == 0

    def test_run_paused_on_escalation_names_reason_and_artifact(self, tmp_path, capsys):
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
                "preserve_ref": None,
            }
        ]
        assert exit_code == 0

    def test_run_with_empty_tasks_reports_empty_stories_no_crash(self, tmp_path, capsys):
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
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=())})

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

    def test_no_loop_home_attached_degrades_state_readable_but_keeps_journal_facts(self, tmp_path, capsys):
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
        harness = _FakeHarness(snapshots={(str(home), "hrid-1"): _snapshot(finished=False, tasks=())})

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
        exit_code = status_cli.run_status(_args(project="no-such-project-xyz", run="no-such-run-xyz"))

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

#: Story 50.4/FR-191 CAP-247: the repo default now carries a `{slug}`
#: placeholder -- pulled from `DEFAULT_POLICY` (not hardcoded) so this
#: helper always matches whatever `run_status`'s own effective policy
#: template actually is.
_DEFAULT_MERGE_TEMPLATE = str(DEFAULT_POLICY["merge_subject_template"])


def _merged_subject(key: str, *, project_slug: str = "acme") -> str:
    return render_merge_subject(normalize(key), _DEFAULT_MERGE_TEMPLATE, project_slug)


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

    def test_missing_ledger_file_reports_mrs_status_005(self, tmp_path, capsys, monkeypatch):
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

    def test_git_history_unreadable_reports_mrs_status_007(self, tmp_path, capsys, monkeypatch):
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

    def test_git_failure_still_reports_this_project_policy_diagnostics(self, tmp_path, capsys, monkeypatch):
        """Story 4.14 review finding (2026-08-10, pass 2): this view's own
        project-policy diagnostics must survive a git-read failure. The
        pre-4.14 shipped code resolved the policy BEFORE reading git, so a
        malformed project-policy TOML still reported its `MRS-POLICY-004`;
        pass 1's refactor returned early on the git failure and silently
        dropped it. Both findings must be present."""
        monkeypatch.setattr(status_cli, "repo_root", lambda: tmp_path)
        bad_policy = tmp_path / "bad-policy.toml"
        bad_policy.write_text("not [ valid toml", encoding="utf-8")
        monkeypatch.setattr(status_cli, "conventional_project_policy_path", lambda slug: bad_policy)
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
        # The pre-existing shipped diagnostic, never silently dropped, and
        # in the SAME order the pre-4.14 code emitted it (policy resolved
        # first, git reported second). This view surfaces such findings at
        # FACE VALUE -- unlike the default fleet sweep, which must degrade
        # them to a WARN.
        assert codes == ["MRS-POLICY-004", "MRS-STATUS-007"]
        assert payload["data"]["discrepancies"] == []
        # `MRS-STATUS-007`'s own UNEVALUABLE still dominates the composed
        # verdict (this view genuinely could not evaluate anything) -- the
        # added policy finding changes what is REPORTED, never the tier.
        assert exit_code == 1

    def test_full_agreement_is_clean_with_no_discrepancies(self, tmp_path, capsys, monkeypatch):
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

    def test_done_in_ledger_not_merged_is_reported_never_a_finding(self, tmp_path, capsys, monkeypatch):
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

    def test_merged_not_done_in_ledger_is_reported_never_a_finding(self, tmp_path, capsys, monkeypatch):
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

    def test_malformed_ledger_key_is_skipped_never_a_crash(self, tmp_path, capsys, monkeypatch):
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
        jsonschema.validate(instance=payload, schema=compose(BASE_ENVELOPE_SCHEMA, envelope_schema))

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


# =============================================================================
# Story 5.5 (durability as a reported fleet-status dimension, FR-62/AD-48):
# `run_status`'s fleet-summary path folds `scripts/unpushed_work_check.py
# --json --branches-only`'s own findings onto each home's row, matched by
# `ref == f"loop/{slug}"`. Covers the spec's own I/O & Edge-Case Matrix.
# =============================================================================


def _unpushed_result(*findings: dict[str, object], base: str = "origin/main") -> ProcessResult:
    # Code review (2026-08-07, Edge Case Hunter): the real
    # `scripts/unpushed_work_check.py::main` always returns 1 in --json
    # mode (the early `return 0` only exists on the plain-text OK-clean
    # path), never 0 -- fixed so this fixture can't mask a future change
    # that starts trusting returncode 0 vs. 1 in production code.
    return ProcessResult(
        returncode=1,
        stdout=json.dumps({"base": base, "findings": list(findings)}),
        stderr="",
    )


def _unpushed_finding(
    ref: str,
    *,
    files: int = 3,
    stat: str = "3 files changed, 40 insertions(+)",
    remedy: str | None = None,
) -> dict[str, object]:
    return {
        "kind": "unpushed-branch",
        "ref": ref,
        "files": files,
        "stat": stat,
        "remedy": remedy or f"git push origin {ref}",
    }


class TestUnpushedWork:
    def test_no_unpushed_work_anywhere_is_null_with_no_finding(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        process = _FakeProcess(run_result=_unpushed_result())

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["unpushed_work"] is None
        assert [f["code"] for f in payload["findings"]] == []
        assert payload["verdict"] == "clean"
        assert exit_code == 0
        # The detector ran exactly once for the whole sweep.
        assert len(process.run_calls) == 1
        argv, cwd = process.run_calls[0]
        # Code review (2026-08-07, Edge Case Hunter): `sys.executable`,
        # never a bare `"python3"` off PATH.
        assert argv[0] == sys.executable
        assert argv[-2:] == ("--json", "--branches-only")

    def test_matching_branch_folds_evidence_onto_the_row_and_warns(self, tmp_path, capsys, monkeypatch):
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
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
            }
        )
        process = _FakeProcess(
            alive_pids=frozenset({5252}),
            run_result=_unpushed_result(_unpushed_finding("loop/acme", files=9, stat="9 files changed")),
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["unpushed_work"] == {
            "files": 9,
            "stat": "9 files changed",
            "remedy": "git push origin loop/acme",
        }
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-008" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_finding_ref_matching_no_known_home_is_ignored(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        process = _FakeProcess(
            run_result=_unpushed_result(_unpushed_finding("recover/some-other-branch")),
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["unpushed_work"] is None
        assert [f["code"] for f in payload["findings"]] == []
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_detector_script_launch_failure_reports_null_and_warns(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        process = _FakeProcess(run_raises=True)

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["unpushed_work"] is None
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-009" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_detector_unknown_exit_code_is_treated_as_unavailable(self, tmp_path, capsys, monkeypatch):
        """The documented UNKNOWN/exit-2 case prints PLAIN TEXT even with
        --json passed -- never JSON-parseable; this test's own `run_result`
        mirrors that shape exactly (non-JSON stdout, returncode 2)."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        process = _FakeProcess(
            run_result=ProcessResult(
                returncode=2,
                stdout="UNKNOWN: could not list remote branches (offline?)\n",
                stderr="",
            )
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["unpushed_work"] is None
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-009" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_malformed_json_output_is_treated_as_unavailable(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        process = _FakeProcess(run_result=ProcessResult(returncode=0, stdout="{not valid json", stderr=""))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["unpushed_work"] is None
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-009" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_journal_unreadable_row_still_surfaces_real_unpushed_work(self, tmp_path, capsys, monkeypatch):
        """Code review (2026-08-07, Blind Hunter, the single most severe
        finding against this story, independently confirmed): unlike
        `escalation_reason`/`escalation_artifact` (Story 5.3), whose ONLY
        source is the same journal that's unreadable here,
        `unpushed_work`'s source is a COMPLETELY INDEPENDENT signal (a git
        branch-vs-remote diff) that has nothing to do with journal
        readability. A degraded (`journal_unreadable`) row must still
        surface real unpushed-work evidence -- suppressing it would be the
        exact false-green this story exists to eliminate, for precisely
        the population most likely to carry real, unrescued local-only
        work (a home whose journal write itself got interrupted)."""
        run_dir = _seed_run_journal(tmp_path, run_id="acme-run1", lines=["{not valid json at all"])
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        process = _FakeProcess(
            run_result=_unpushed_result(_unpushed_finding("loop/acme")),
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["state"] == "unknown"
        assert row["unpushed_work"] is not None
        assert row["unpushed_work"]["files"] == 3
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-002" in codes
        assert "MRS-STATUS-008" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_has_run_false_row_still_surfaces_real_unpushed_work(self, tmp_path, capsys, monkeypatch):
        """Same root cause and fix as the journal-unreadable case above,
        for the `has_run=False` ("idle", no run yet) row shape -- a
        brand-new home that has never run bmad-loop can still have a real,
        at-risk branch."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        process = _FakeProcess(
            run_result=_unpushed_result(_unpushed_finding("loop/acme")),
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["state"] == "idle"
        assert row["unpushed_work"] is not None
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-008" in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_detector_skipped_entirely_when_fleet_is_empty(self, capsys):
        vcs = _FakeVcs(worktrees=())
        process = _FakeProcess()

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["homes"] == []
        assert process.run_calls == []
        assert exit_code == 0

    def test_text_format_matches_json_presence_of_unpushed_work(self, tmp_path, capsys, monkeypatch):
        # An idle (has_run=False) row hardcodes unpushed_work: None
        # regardless of a matching finding (see
        # test_has_run_false_row_never_surfaces_unpushed_work above) -- a
        # running home is needed here to reach the row shape that actually
        # surfaces it, so this text/json parity check exercises something
        # real.
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
                (str(home), "hrid-1"): _snapshot(finished=False, tasks=(_task(story_key="1.1", phase="dev-running"),))
            }
        )
        process = _FakeProcess(
            alive_pids=frozenset({5252}),
            run_result=_unpushed_result(_unpushed_finding("loop/acme", files=5, stat="5 files changed")),
        )

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        assert "UNPUSHED files=5" in out
        assert exit_code == 0


# =============================================================================
# Story 4.14: the failed-story safety net is reported (FR-176) -- covers
# every row of the spec's I/O & Edge-Case Matrix for `_gather_failed_patches`
# plus the `MRS-STATUS-010`/`011` classification wired into `run_status`'s
# existing per-home loop, AND each of the spec's three Acceptance Criteria
# explicitly (`--project SLUG` scoping, per-home independence under one bad
# policy, and a repeated sweep being byte-identical). Mirrors
# `TestUnpushedWork`'s own fixture convention (real `tmp_path` + `LocalFs()`);
# `_merged_subject` (Story 5.4's own helper, above) builds a commit subject
# `core.promotion.merged_story_keys` will recognize as a durable merge for a
# given story key, against the bare default `merge_subject_template` -- no
# real `_bmad-output/projects/acme/` project exists in this repo, so `acme`'s
# composed policy always falls through to that default, the SAME latent
# coupling `TestReconcileLedgerCli` already relies on.
#
# Review finding (2026-08-10, pass 2): the story-dir fixtures below use REAL
# bmad-loop directory names -- long multi-hyphen titles and a two-digit epic
# -- not only synthetic `4-13-title` stubs. Pass 1's all-synthetic fixtures
# are precisely why a feature that was wrong on 2 of 3 real WARNs still
# passed its own unit suite.
# =============================================================================

#: A real bmad-loop failed-story directory name (this very story's own epic).
_REAL_STORY_DIR = "4-11-marshal-land-refuses-while-a-run-is-in-flight"
#: A real two-digit-epic directory name (`pyforge-atlas` carries 12.1/12.2
#: patches on the live fleet) -- `normalize` must not mis-parse the epic.
_TWO_DIGIT_EPIC_DIR = "12-1-the-atlas-pipeline-reports-its-own-freshness"


def _seed_failed_patch(
    home: Path,
    *,
    run_id: str,
    story_dir: str,
    content: bytes = b"diff --git a/x b/x\n@@ -0,0 +1 @@\n+x\n",
) -> Path:
    """A real on-disk ``.bmad-loop/runs/<run_id>/failed/<story_dir>/
    changes.patch`` -- bmad-loop's own on-disk shape (external to this repo)
    for a session-timeout-killed story's preserved diff."""
    patch_dir = home / ".bmad-loop" / "runs" / run_id / "failed" / story_dir
    patch_dir.mkdir(parents=True)
    patch_path = patch_dir / "changes.patch"
    patch_path.write_bytes(content)
    return patch_path


class TestFailedPatches:
    def test_no_patches_anywhere_is_silent(self, tmp_path, capsys, monkeypatch):
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
        row = payload["data"]["homes"][0]
        assert row["failed_patches"] == []
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-010" not in codes
        assert "MRS-STATUS-011" not in codes
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_landed_patch_is_spent_and_confirmed_no_finding(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        patch_path = _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(_merged_subject("4.11"),),
        )

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
        # A POSITIVE `merged_story_keys` match IS proof (`core/status.py`'s
        # own `CONFIDENCE_CONFIRMED`) -- the one direction that may be
        # asserted.
        assert row["failed_patches"] == [
            {
                "story_key": "4.11",
                "run_id": "20260809-231524-abb9",
                "path": str(patch_path),
                "size_bytes": patch_path.stat().st_size,
                "done": True,
                "confidence": status.CONFIDENCE_CONFIRMED,
            }
        ]
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-010" not in codes
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_two_digit_epic_story_dir_parses_and_classifies(self, tmp_path, capsys, monkeypatch):
        """A two-digit epic (`12-1-...`, live on `pyforge-atlas`) must
        normalize to `12.1`, never to `1.2` or the raw dir name."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"atlas": None})
        home = tmp_path / "loop-homes" / "atlas"
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_TWO_DIGIT_EPIC_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/atlas"),),
            commit_subjects_value=(_merged_subject("12.1", project_slug="atlas"),),
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        entry = payload["data"]["homes"][0]["failed_patches"][0]
        assert entry["story_key"] == "12.1"
        assert entry["done"] is True
        assert entry["confidence"] == status.CONFIDENCE_CONFIRMED
        assert [f["code"] for f in payload["findings"]] == []
        assert exit_code == 0

    def test_unlanded_patch_warns_as_unconfirmed_naming_the_run(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 2, the finding that reverted this
        story's first implementation): the ABSENCE of a `merged_story_keys`
        match proves nothing (`core/status.py`'s own `CONFIDENCE_UNCONFIRMED`
        block: squash-merge prose and `land/<station>-<epic>-<seq>` merge
        subjects are both unparseable -- 2 of 3 live WARNs were false), so
        the entry carries `confidence: unconfirmed` and the finding must NOT
        assert "has not landed" as established fact. It also names `run_id`
        (live: `pyforge-steward` carries three run dirs, otherwise
        distinguishable only by a long absolute path)."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

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
        entry = row["failed_patches"][0]
        assert entry["story_key"] == "4.11"
        assert entry["done"] is False
        assert entry["confidence"] == status.CONFIDENCE_UNCONFIRMED
        codes = [f["code"] for f in payload["findings"]]
        assert codes.count("MRS-STATUS-010") == 1
        message = next(f["message"] for f in payload["findings"] if f["code"] == "MRS-STATUS-010")
        # States the UNCONFIRMED direction and why -- never the flat
        # assertion the reverted implementation emitted.
        assert "UNCONFIRMED" in message
        assert "has not landed" not in message
        assert "no confirming durable merge" in message
        assert "20260809-231524-abb9" in message
        assert "4.11" in message
        # WARN tier only -- never this command's exit code (the story's own
        # Boundary).
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_git_read_failure_degrades_every_patch_and_warns_once(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None})
        home_a = tmp_path / "loop-homes" / "acme"
        home_b = tmp_path / "loop-homes" / "beta"
        _seed_failed_patch(home_a, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        _seed_failed_patch(home_b, run_id="20260810-004512-c31f", story_dir=_TWO_DIGIT_EPIC_DIR)
        vcs = _FakeVcs(
            worktrees=(
                WorktreeEntry(path=home_a, branch="loop/acme"),
                WorktreeEntry(path=home_b, branch="loop/beta"),
            ),
            commit_subjects_raises=True,
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        homes_by_slug = {row["slug"]: row for row in payload["data"]["homes"]}
        for slug in ("acme", "beta"):
            entry = homes_by_slug[slug]["failed_patches"][0]
            assert entry["done"] is None
            # `null` is never fabricated as either landed or unlanded -- and
            # it is certainly not `confirmed`.
            assert entry["confidence"] == status.CONFIDENCE_UNCONFIRMED
        codes = [f["code"] for f in payload["findings"]]
        assert codes.count("MRS-STATUS-011") == 1
        assert "MRS-STATUS-010" not in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_unparseable_story_dir_name_treated_as_pending(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir="not-a-story-name")
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

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
        entry = row["failed_patches"][0]
        assert entry["story_key"] == "not-a-story-name"
        assert entry["done"] is False
        assert entry["confidence"] == status.CONFIDENCE_UNCONFIRMED
        codes = [f["code"] for f in payload["findings"]]
        assert codes.count("MRS-STATUS-010") == 1
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_malformed_project_policy_degrades_to_warn_not_error(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 1, Blind Hunter): a malformed
        project policy for `slug` -- entirely unrelated to this durability
        check -- used to inject `_merged_keys_for_slug`'s raw `PolicyIOError`
        finding (`MRS-POLICY-004`, `Verdict.ERROR`) straight into the DEFAULT
        `marshal status` sweep, changing its exit code (WARN is 0, ERROR is
        4) over a patch this story's own Boundaries say must be WARN-tier
        at worst. It must now degrade to `done: null` plus a single
        `MRS-STATUS-011` WARN, exactly like an unreadable `main`."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        bad_policy = tmp_path / "bad-policy.toml"
        bad_policy.write_text("not [ valid toml", encoding="utf-8")
        monkeypatch.setattr(status_cli, "conventional_project_policy_path", lambda slug: bad_policy)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

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
        assert row["failed_patches"][0]["done"] is None
        assert row["failed_patches"][0]["confidence"] == status.CONFIDENCE_UNCONFIRMED
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-POLICY-004" not in codes
        assert "MRS-STATUS-010" not in codes
        assert codes.count("MRS-STATUS-011") == 1
        # The per-slug arm's message is scoped to THIS project (never "every
        # patch found this sweep", review finding pass 2) and NAMES the
        # patches it degraded rather than merely counting them (review
        # finding pass 3: the intent contract's Always bullet requires a
        # patch whose landed-status could not be determined to be raised by
        # "exactly one WARN naming it").
        message = next(f["message"] for f in payload["findings"] if f["code"] == "MRS-STATUS-011")
        assert "acme" in message
        assert "this project's own merge-subject policy" in message
        assert "every patch found this sweep" not in message
        assert "4.11" in message
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_one_bad_policy_never_suppresses_the_other_home(self, tmp_path, capsys, monkeypatch):
        """Acceptance Criterion (previously untested, review finding pass 2):
        with two homes where only ONE slug's policy is malformed, the other
        home must still classify its own patches normally and still surface
        its own real finding -- this command's established "one bad row never
        blocks the sweep" precedent, applied to the exact branch pass 1
        introduced."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None})
        home_a = tmp_path / "loop-homes" / "acme"
        home_b = tmp_path / "loop-homes" / "beta"
        _seed_failed_patch(home_a, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        _seed_failed_patch(home_b, run_id="20260810-004512-c31f", story_dir=_TWO_DIGIT_EPIC_DIR)
        bad_policy = tmp_path / "bad-policy.toml"
        bad_policy.write_text("not [ valid toml", encoding="utf-8")
        good_policy = tmp_path / "missing-policy.toml"

        monkeypatch.setattr(
            status_cli,
            "conventional_project_policy_path",
            lambda slug: bad_policy if slug == "acme" else good_policy,
        )
        vcs = _FakeVcs(
            worktrees=(
                WorktreeEntry(path=home_a, branch="loop/acme"),
                WorktreeEntry(path=home_b, branch="loop/beta"),
            ),
            commit_subjects_value=(),
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        homes_by_slug = {row["slug"]: row for row in payload["data"]["homes"]}
        # acme degraded (its own policy is unreadable) ...
        assert homes_by_slug["acme"]["failed_patches"][0]["done"] is None
        # ... while beta still classified normally and still warns.
        beta_entry = homes_by_slug["beta"]["failed_patches"][0]
        assert beta_entry["done"] is False
        assert beta_entry["story_key"] == "12.1"
        codes = [f["code"] for f in payload["findings"]]
        assert codes.count("MRS-STATUS-011") == 1
        assert codes.count("MRS-STATUS-010") == 1
        assert "MRS-POLICY-004" not in codes
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_project_scoping_only_scans_that_project(self, tmp_path, capsys, monkeypatch):
        """Acceptance Criterion (previously untested, review finding pass 2):
        `--project SLUG` scopes the failed-patch scan to that project's own
        loop home -- the other home's patches are neither reported nor
        warned about, consistent with this command's existing fleet-scoping
        behavior."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None})
        home_a = tmp_path / "loop-homes" / "acme"
        home_b = tmp_path / "loop-homes" / "beta"
        _seed_failed_patch(home_a, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        _seed_failed_patch(home_b, run_id="20260810-004512-c31f", story_dir=_TWO_DIGIT_EPIC_DIR)
        vcs = _FakeVcs(
            worktrees=(
                WorktreeEntry(path=home_a, branch="loop/acme"),
                WorktreeEntry(path=home_b, branch="loop/beta"),
            ),
            commit_subjects_value=(),
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
        rows = payload["data"]["homes"]
        assert [row["slug"] for row in rows] == ["beta"]
        assert rows[0]["failed_patches"][0]["story_key"] == "12.1"
        codes = [f["code"] for f in payload["findings"]]
        # Exactly ONE MRS-STATUS-010 -- acme's patch was never scanned.
        assert codes.count("MRS-STATUS-010") == 1
        message = next(f["message"] for f in payload["findings"] if f["code"] == "MRS-STATUS-010")
        assert message.startswith("beta:")
        assert exit_code == 0

    def test_directory_named_changes_patch_is_not_reported(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, Edge Case Hunter): `Path.glob` does
        not distinguish file kind, and `.stat()` on a directory succeeds
        rather than raising -- a directory literally named `changes.patch`
        must not be fabricated into a reported entry. Pass 2: the filter
        lives INSIDE `_gather_failed_patches`, so such a directory must not
        even open the `if patch_paths:` gate -- no `main` read is paid for
        and no orphaned `MRS-STATUS-011` can be emitted (asserted here by
        making that read RAISE: a gate that opened would warn)."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        patch_dir = home / ".bmad-loop" / "runs" / "20260809-231524-abb9" / "failed" / _REAL_STORY_DIR
        (patch_dir / "changes.patch").mkdir(parents=True)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_raises=True,
        )

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
        assert row["failed_patches"] == []
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-010" not in codes
        assert "MRS-STATUS-011" not in codes
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_zero_byte_patch_is_not_reported(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 2): a zero-byte `changes.patch`
        -- a kill BEFORE any diff was written -- preserved nothing to
        recover, so a WARN would direct an operator at an empty file.
        Skipped entirely: no entry, no finding."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(
            home,
            run_id="20260809-231524-abb9",
            story_dir=_REAL_STORY_DIR,
            content=b"",
        )
        _seed_failed_patch(home, run_id="20260810-004512-c31f", story_dir=_TWO_DIGIT_EPIC_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        entries = payload["data"]["homes"][0]["failed_patches"]
        assert [entry["story_key"] for entry in entries] == ["12.1"]
        codes = [f["code"] for f in payload["findings"]]
        assert codes.count("MRS-STATUS-010") == 1
        assert exit_code == 0

    def test_only_unreportable_patches_never_emits_an_orphaned_finding(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 3, reproduced live): every
        reportability test belongs INSIDE `_gather_failed_patches`, not at
        the caller's per-entry loop. A home whose ONLY glob match is
        unreportable (here: zero-byte) used to still open the caller's `if
        patch_paths:` gate, pay for the `main` read, and -- when that read
        failed -- emit an ORPHANED `MRS-STATUS-011` naming a patch count
        while every row correctly reported `failed_patches: []`, flipping
        the verdict `clean -> warn` with nothing to show for it."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(
            home,
            run_id="20260809-231524-abb9",
            story_dir=_REAL_STORY_DIR,
            content=b"",
        )
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_raises=True,
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        assert payload["data"]["homes"][0]["failed_patches"] == []
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-011" not in codes
        assert "MRS-STATUS-010" not in codes
        assert payload["verdict"] == "clean"
        assert exit_code == 0

    def test_unreadable_main_warn_names_every_degraded_patch(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 3): the intent contract's Always
        bullet requires a patch whose landed-status "could not be
        determined" to raise "exactly one WARN naming it". The single
        sweep-wide `MRS-STATUS-011` must therefore NAME the patches it
        degraded, across every home, not just count them -- which is why it
        is emitted after the per-home loop rather than at the point the git
        read fails (where the later homes are not yet known)."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None})
        home_a = tmp_path / "loop-homes" / "acme"
        home_b = tmp_path / "loop-homes" / "beta"
        _seed_failed_patch(home_a, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        _seed_failed_patch(home_b, run_id="20260810-004512-c31f", story_dir=_TWO_DIGIT_EPIC_DIR)
        vcs = _FakeVcs(
            worktrees=(
                WorktreeEntry(path=home_a, branch="loop/acme"),
                WorktreeEntry(path=home_b, branch="loop/beta"),
            ),
            commit_subjects_raises=True,
        )

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
        assert codes.count("MRS-STATUS-011") == 1
        message = next(f["message"] for f in payload["findings"] if f["code"] == "MRS-STATUS-011")
        # Both homes' patches named in the ONE sweep-wide WARN.
        assert "4.11" in message
        assert "12.1" in message
        assert "2 patch(es)" in message
        assert exit_code == 0

    def test_journal_unreadable_row_still_reports_failed_patches(self, tmp_path, capsys, monkeypatch):
        """`build_fleet_row`'s degraded (`journal_unreadable`) shape carries
        `failed_patches` verbatim rather than hardcoding it away the way it
        does `unpushed_work` -- this is an independent filesystem signal, so
        a malformed journal must not suppress it. Mirrors
        `TestUnpushedWork::test_journal_unreadable_row_still_surfaces_real_
        unpushed_work`'s own precedent for the sibling signal."""
        home = tmp_path / "loop-homes" / "acme"
        run_dir = home / ".bmad-loop" / "runs" / "20260809-231524-abb9"
        run_dir.mkdir(parents=True)
        (run_dir / "journal.jsonl").write_text("{not json\n", encoding="utf-8")
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

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
        assert row["failed_patches"][0]["story_key"] == "4.11"
        codes = [f["code"] for f in payload["findings"]]
        assert codes.count("MRS-STATUS-010") == 1
        assert exit_code == 0

    def test_text_format_renders_the_full_tri_state(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        _seed_failed_patch(home, run_id="20260810-004512-c31f", story_dir=_TWO_DIGIT_EPIC_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(_merged_subject("4.11"),),
        )

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        assert "FAILED_PATCHES n=2 pending=1 unknown=0" in out
        assert exit_code == 0

    def test_text_format_shows_unknown_when_main_is_unreadable(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 2): counting only `pending`
        rendered an all-`null` sweep as `FAILED_PATCHES n=2 pending=0` --
        byte-identical to all-landed, fabricating unknown as clean. The
        `unknown=` count is what makes the two distinguishable, and this is
        the test whose absence let that false-green ship."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        _seed_failed_patch(home, run_id="20260810-004512-c31f", story_dir=_TWO_DIGIT_EPIC_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_raises=True,
        )

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        assert "FAILED_PATCHES n=2 pending=0 unknown=2" in out
        assert exit_code == 0

    def test_main_is_read_exactly_once_no_matter_how_many_homes(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 4): KEEP instruction #3 -- the
        `main` commit-subject read is lazy and cached ONCE for the whole
        sweep -- was asserted at four doc sites and observed by nothing.
        `_FakeVcs` recorded no call count, so removing the
        `main_subjects_attempted` guard (turning one `git log`-scale walk
        per invocation into one per patch-carrying home) kept the suite
        green. Three patch-carrying homes, exactly one read."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None, "gamma": None})
        homes = []
        for slug, story_dir in (
            ("acme", _REAL_STORY_DIR),
            ("beta", _TWO_DIGIT_EPIC_DIR),
            ("gamma", _REAL_STORY_DIR),
        ):
            home = tmp_path / "loop-homes" / slug
            _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=story_dir)
            homes.append(WorktreeEntry(path=home, branch=f"loop/{slug}"))
        vcs = _FakeVcs(worktrees=tuple(homes), commit_subjects_value=(_merged_subject("4.11"),))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        assert [ref for _, ref in vcs.commit_subjects_calls] == ["main"]
        assert exit_code == 0

    def test_main_is_never_read_when_no_home_carries_a_patch(self, tmp_path, capsys, monkeypatch):
        """The other half of the same invariant: the read is LAZY, so a
        genuinely patch-free fleet never pays for it at all."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        home.mkdir(parents=True)
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        assert vcs.commit_subjects_calls == []
        assert exit_code == 0

    def test_sweep_wide_warn_qualifies_a_repeated_story_key_by_home(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 4): the sweep-wide
        `MRS-STATUS-011` named patches by BARE story key, and story numbers
        repeat across stations by construction -- live, `pyforge-doctor` and
        `pyforge-warden` both carry a `6-9-*` patch, so the one WARN read
        `... (6.9, 6.9)` and located neither. Each patch is now named
        `<slug>/<story_key>`."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None})
        shared_dir = "6-9-the-scripts-shims-retire"
        homes = []
        for slug in ("acme", "beta"):
            home = tmp_path / "loop-homes" / slug
            _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=shared_dir)
            homes.append(WorktreeEntry(path=home, branch=f"loop/{slug}"))
        vcs = _FakeVcs(worktrees=tuple(homes), commit_subjects_raises=True)

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        message = next(f["message"] for f in payload["findings"] if f["code"] == "MRS-STATUS-011")
        assert "acme/6.9" in message
        assert "beta/6.9" in message
        assert exit_code == 0

    def test_unknown_policy_key_warn_names_the_withheld_code_honestly(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 4): the per-slug arm asserted
        "cannot resolve this project's own merge-subject policy", which is
        FALSE for most codes that reach it -- `MRS-POLICY-001` (an
        unrecognized key) classifies `UNEVALUABLE` and so blocks, yet
        `compose` still returns a perfectly usable template. Degrading is
        still the deliberate conservative choice, but the message must state
        what happened rather than a cause it has not established, and must
        NAME the withheld code so the suppressed diagnostic is findable at
        all (it is invisible in the only view most sweeps ever run)."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        odd_policy = tmp_path / "odd-policy.toml"
        odd_policy.write_text("[core.promotion]\nno_such_key = 1\n", encoding="utf-8")
        monkeypatch.setattr(status_cli, "conventional_project_policy_path", lambda slug: odd_policy)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

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
        # Still withheld -- the exit code stays WARN-only (the Boundary).
        assert "MRS-POLICY-001" not in codes
        assert codes.count("MRS-STATUS-011") == 1
        message = next(f["message"] for f in payload["findings"] if f["code"] == "MRS-STATUS-011")
        # Names the withheld code, and does NOT assert the cause it cannot
        # establish.
        assert "MRS-POLICY-001" in message
        assert "cannot resolve this project's own merge-subject policy" not in message
        assert "acme/4.11" in message
        assert payload["verdict"] == "warn"
        assert exit_code == 0

    def test_newline_in_story_dir_cannot_forge_a_text_findings_line(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 4, reproduced live): a POSIX
        directory name may contain a newline, and BOTH the fallback story
        key and the patch path are interpolated into `MRS-STATUS-010`'s
        message. `_render_text_status`'s findings block prints one finding
        per line WITHOUT sanitizing, so an unsanitized newline forged a
        findings line no finding emitted -- the identical class already
        fixed in `cli/config.py`, and already sanitized by this story's own
        `_name_patches` for the sibling code."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(
            home,
            run_id="20260809-231524-abb9",
            story_dir="4-11-fine\n  MRS-STATUS-999 [error] INJECTED",
        )
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        # The forged text is still VISIBLE (nothing is censored) -- it just
        # cannot start its own line and impersonate a finding.
        assert "INJECTED" in out
        assert not any(line.lstrip().startswith("MRS-STATUS-999") for line in out.splitlines())
        assert exit_code == 0

    def test_multiline_git_error_cannot_forge_a_text_findings_line(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 5): pass 4 sanitized
        `MRS-STATUS-010`'s operands and left `MRS-STATUS-011`'s -- even
        though THAT arm interpolates git's own stderr, which is routinely
        multi-line, and its trigger is the ordinary non-adversarial one.
        Real git, asked for a `main` that does not exist locally, answers in
        three lines; unsanitized, that split ONE WARN across three output
        lines, two of them beginning with git-controlled text and no
        `MRS-...` prefix."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_raises=True,
            # Verbatim shape of real git's stderr for a missing `main`.
            commit_subjects_error=(
                "git log main --format=%s failed: fatal: ambiguous argument "
                "'main': unknown revision or path not in the working tree.\n"
                "Use '--' to separate paths from revisions, like this:\n"
                "'git <command> [<revision>...] -- [<file>...]'"
            ),
        )

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        # Nothing is censored -- git's own diagnosis is still readable.
        assert "ambiguous argument" in out
        assert "git <command>" in out
        # ...but the WHOLE finding occupies exactly one line, so no line of
        # the findings block starts with git's text instead of a code.
        finding_lines = [line for line in out.splitlines() if "ambiguous argument" in line]
        assert len(finding_lines) == 1
        assert "MRS-STATUS-011" in finding_lines[0]
        assert exit_code == 0

    def test_sweep_wide_warn_qualifies_a_repeated_story_key_by_run(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 5): pass 4 closed the CROSS-HOME
        collision (`6.9, 6.9`) and left the CROSS-RUN one open. A home
        accumulates one `failed/<story>/` per killed attempt, so repeated
        attempts at ONE story in ONE home rendered identically -- live,
        `pyforge-steward` carries three run dirs. `MRS-STATUS-011` is the
        only report a `done: null` patch ever gets (`010` fires solely for
        `done is False`), so an unlocatable name is the whole signal."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        for run_id in ("20260809-231524-abb9", "20260810-004512-c31f"):
            _seed_failed_patch(home, run_id=run_id, story_dir=_REAL_STORY_DIR)
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_raises=True,
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        message = next(f["message"] for f in payload["findings"] if f["code"] == "MRS-STATUS-011")
        assert "2 patch(es)" in message
        # Both attempts named, and DISTINGUISHABLE -- the run id is the only
        # thing that differs between them.
        assert "acme/4.11@20260809-231524-abb9" in message
        assert "acme/4.11@20260810-004512-c31f" in message
        assert exit_code == 0

    def test_non_newline_line_breaks_cannot_forge_a_text_findings_line(self, tmp_path, capsys, monkeypatch):
        """Review finding (2026-08-10, pass 5): `_one_line` collapsed only
        `\\n` and `\\r`, too narrow for its OWN stated threat model. If a
        `failed/<story>/` name may legally carry a newline it may equally
        carry `\\v`, `\\f`, `\\x85`, `\\u2028` or `\\u2029` -- all legal in a
        POSIX/UTF-8 filename, and all split by `str.splitlines`, which is
        the very method the sibling forged-line test asserts with."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        _seed_failed_patch(
            home,
            run_id="20260809-231524-abb9",
            story_dir="4-11-fine\v  MRS-STATUS-998 [error] INJECTED X",
        )
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        out = capsys.readouterr().out
        assert "INJECTED" in out
        assert not any(line.lstrip().startswith("MRS-STATUS-998") for line in out.splitlines())
        assert exit_code == 0

    def test_repeated_sweep_is_identical_and_never_mutates_a_patch(self, tmp_path, capsys, monkeypatch):
        """Acceptance Criterion: the same fleet swept twice with no change in
        patches or merge history reports identical `failed_patches` data and
        finding counts -- a pure read that never clears, moves, or truncates
        a patch."""
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        home = tmp_path / "loop-homes" / "acme"
        patch_path = _seed_failed_patch(home, run_id="20260809-231524-abb9", story_dir=_REAL_STORY_DIR)
        before = patch_path.read_bytes()
        vcs = _FakeVcs(
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
            commit_subjects_value=(),
        )

        payloads = []
        for _ in range(2):
            exit_code = status_cli.run_status(
                _args(),
                vcs=vcs,
                fs=LocalFs(),
                harness=_FakeHarness(),
                process=_FakeProcess(),
                clock=_FakeClock(now=_FIXED_NOW),
            )
            assert exit_code == 0
            payloads.append(_payload(capsys))

        first, second = payloads
        assert first["data"]["homes"] == second["data"]["homes"]
        assert [f["code"] for f in first["findings"]] == [f["code"] for f in second["findings"]]
        assert patch_path.is_file()
        assert patch_path.read_bytes() == before


# =============================================================================
# Story 25.5 (CAP-5): the 0.11 status vocabulary's TEXT projections -- pure
# render-level tests over the SAME envelope dicts the JSON path emits
# (NFR-12: the text view is a projection, never a second derivation), plus
# one end-to-end parked-run sweep through `run_status` itself.
# =============================================================================


def _fleet_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "slug": "acme",
        "branch": "loop/acme",
        "state": "idle",
        "current_story": None,
        "elapsed_seconds": None,
        "budget_consumed": None,
        "escalation_reason": None,
        "escalation_artifact": None,
        "escalation_preserve_ref": None,
        "parked_stories": (),
        "unpushed_work": None,
        "failed_patches": (),
    }
    row.update(overrides)
    return row


class TestAwaitingOperatorTextProjections:
    def test_parked_state_renders_the_remedy_suffix_and_parked_list(self):
        text = status_cli._render_text_status(
            {
                "project": None,
                "homes": [
                    _fleet_row(
                        state="awaiting-operator",
                        current_story="25-2-parked",
                        parked_stories=("25-2-parked",),
                    )
                ],
            },
            (),
        )
        assert "awaiting-operator (run bmad-loop confirm)" in text
        assert "parked=25-2-parked" in text
        for banned in ("stalled", "dead", "unsupervised", "running"):
            assert banned not in text

    def test_remedy_spelling_is_the_single_core_constant(self):
        """The one spelling rule: renders compose the suffix from
        `core.status.AWAITING_OPERATOR_REMEDY`, so the projection can
        never drift from the constant the spec pins."""
        assert status.AWAITING_OPERATOR_REMEDY == "run bmad-loop confirm"

    def test_missing_spec_remedy_projects_the_spec_glob_in_text(self):
        """Story 28.19: text status names the expected spec glob, not confirm."""
        spec_glob = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-39-4-*.md"
        remedy = f"missing tracked spec: author {spec_glob}"
        text = status_cli._render_text_status(
            {
                "project": None,
                "homes": [
                    _fleet_row(
                        state="awaiting-operator",
                        current_story="39.4",
                        awaiting_operator_remedy=remedy,
                    )
                ],
            },
            (),
        )
        assert f"awaiting-operator ({remedy})" in text
        assert "spec-39-4-*.md" in text
        assert "run bmad-loop confirm" not in text

    def test_non_parked_states_render_without_a_suffix_or_parked_list(self):
        text = status_cli._render_text_status({"project": None, "homes": [_fleet_row(state="running")]}, ())
        assert "running" in text
        assert "bmad-loop confirm" not in text
        assert "parked=" not in text

    def test_escalated_row_appends_preserve_ref_only_when_present(self):
        base = _fleet_row(
            state="paused-on-escalation",
            escalation_reason="needs a human decision",
            escalation_artifact="spec-1.2.md",
        )
        without = status_cli._render_text_status({"project": None, "homes": [base]}, ())
        assert "preserve_ref=" not in without

        with_ref = status_cli._render_text_status(
            {
                "project": None,
                "homes": [
                    _fleet_row(
                        state="paused-on-escalation",
                        escalation_reason="needs a human decision",
                        escalation_artifact="spec-1.2.md",
                        escalation_preserve_ref="attempt-preserve/run1-abc123",
                    )
                ],
            },
            (),
        )
        assert "preserve_ref=attempt-preserve/run1-abc123" in with_ref

    def test_scope_advisory_renders_a_one_line_projection(self):
        """Story 28.15 (CAP-17), AC4: a `warn`-mode scope-violation
        advisory is visible in `marshal status`'s TEXT view too, not just
        `--format json` -- a pure projection of the SAME
        `dispatch_verification_scope_advisories` field (NFR-12)."""
        text = status_cli._render_text_status(
            {
                "project": None,
                "homes": [
                    _fleet_row(
                        dispatch_verification_scope_advisories=[
                            {
                                "code": "MRS-GATE-012",
                                "message": "...",
                                "path": "src/leak.py",
                            }
                        ],
                    )
                ],
            },
            (),
        )
        assert "SCOPE_ADVISORY n=1 codes=MRS-GATE-012" in text

    def test_no_scope_advisory_renders_no_scope_advisory_marker(self):
        text = status_cli._render_text_status({"project": None, "homes": [_fleet_row()]}, ())
        assert "SCOPE_ADVISORY" not in text

    def _detail(self, **overrides: object) -> dict[str, object]:
        data: dict[str, object] = {
            "project": "acme",
            "run_id": "acme-run1",
            "found": True,
            "state_readable": True,
            "finished": False,
            "paused_stage": None,
            "paused_story_key": None,
            "paused_reason": None,
            "escalated_spec_file": None,
            "escalated_task_phase": None,
            "sweeps_refused": {},
            "stories": [],
            "deferred": [],
            "open_intents": [],
        }
        data.update(overrides)
        return data

    def test_run_detail_renders_sweeps_refused_triggers_and_hint(self):
        text = status_cli._render_text_run_detail(
            self._detail(sweeps_refused={"epic-1": "dirty", "run-end": "failed"}),
            (),
        )
        assert "sweeps_refused: epic-1 (dirty), run-end (failed)" in text
        assert "deferred work is untouched" in text

    def test_run_detail_renders_empty_and_null_sweeps_refused_distinctly(self):
        clean = status_cli._render_text_run_detail(self._detail(sweeps_refused={}), ())
        assert "sweeps_refused: (none)" in clean

        unreadable = status_cli._render_text_run_detail(self._detail(state_readable=False, sweeps_refused=None), ())
        assert "sweeps_refused: None" in unreadable

    def test_run_detail_story_and_deferred_lines_append_preserve_ref_when_set(self):
        text = status_cli._render_text_run_detail(
            self._detail(
                stories=[
                    {
                        "story_key": "1.4",
                        "phase": "escalated",
                        "commit_sha": None,
                        "branch": "",
                        "preserve_ref": "attempt-preserve/run1-abc123",
                        "gate_verdict": None,
                        "budget_consumed": None,
                    },
                    {
                        "story_key": "1.5",
                        "phase": "done",
                        "commit_sha": "cafe123",
                        "branch": "",
                        "preserve_ref": None,
                        "gate_verdict": None,
                        "budget_consumed": None,
                    },
                ],
                deferred=[
                    {
                        "story_key": "1.2",
                        "reason": "verify exhausted",
                        "attempt": 2,
                        "branch": "",
                        "worktree_path": "",
                        "spec_file": None,
                        "preserve_ref": "refs/attempt-preserve-dirty/run1-def456",
                    }
                ],
            ),
            (),
        )
        assert "1.4" in text
        assert "preserve_ref=attempt-preserve/run1-abc123" in text
        assert "preserve_ref=refs/attempt-preserve-dirty/run1-def456" in text
        # The absent case renders NO suffix -- one occurrence per set ref.
        assert text.count("preserve_ref=") == 2

    def test_end_to_end_parked_run_reports_awaiting_operator_in_json_and_text(self, tmp_path, capsys, monkeypatch):
        """AC 1 at the command level: a parked run sweeps through
        `run_status` as `awaiting-operator` (bare token in JSON, remedy
        suffix in text) with the parked story as current -- never
        stalled/dead/unsupervised/running."""
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
                    finished=False,
                    tasks=(
                        _task(story_key="25.1", phase="done"),
                        _task(story_key="25.2", phase="awaiting-operator"),
                    ),
                )
            }
        )
        # Both processes dead -- the parked state must still never read
        # `unsupervised` (the DW's "never mislabeled dead").
        process = _FakeProcess(alive_pids=frozenset())

        exit_code = status_cli.run_status(
            _args(format="json"),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert exit_code == 0
        assert row["state"] == "awaiting-operator"
        assert row["current_story"] == "25.2"
        assert row["parked_stories"] == ["25.2"]

        exit_code = status_cli.run_status(
            _args(format="text"),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=process,
            clock=_FakeClock(now=_FIXED_NOW),
        )
        text_out = capsys.readouterr().out
        assert exit_code == 0
        assert "awaiting-operator (run bmad-loop confirm)" in text_out
        assert "parked=25.2" in text_out
        assert "unsupervised" not in text_out


class TestRetiredRunState:
    """DW-STATUS-2026-09-08-1: a retired/cleaned run must not read `unknown`.

    pyforge-steward read `unknown` from 2026-08-22 to 2026-09-08 because its
    runs were retired (`.bmad-loop/runs/.retired-*`) while `latest_run_dir`
    kept selecting one, whose harness snapshot no longer resolved. That is not
    an unreadable journal -- the journal read fine -- so the row now reports
    the home as free, with a WARN naming the unresolvable run.
    """

    def test_retired_run_reports_idle_not_unknown(self):
        facts = status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=True, run_state_retired=True)
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "idle"
        assert finding is not None
        assert finding.code == "MRS-STATUS-012"
        assert finding.severity is status.Severity.WARN

    def test_retired_run_is_not_confused_with_an_unreadable_journal(self):
        """The two flags are distinct: an unreadable journal recovered NOTHING,
        so `unknown` stays correct there."""
        unreadable, _ = status.build_fleet_row(
            status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=True, journal_unreadable=True)
        )
        retired, _ = status.build_fleet_row(
            status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=True, run_state_retired=True)
        )
        assert unreadable["state"] == "unknown"
        assert retired["state"] == "idle"

    def test_retired_run_keeps_independently_gathered_evidence(self):
        """`unpushed_work` comes from a git probe, not the missing snapshot --
        it must survive, the same rule the unreadable-journal row already has."""
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            run_state_retired=True,
            unpushed_work="3 commits",
        )
        row, _ = status.build_fleet_row(facts)
        assert row["unpushed_work"] == "3 commits"

    def test_retired_run_is_conservatively_live_for_destructive_guards(self):
        """`is_run_live` deliberately DISAGREES with the row above: the row says
        what an operator should see, this says whether a branch may be deleted.
        A retired run's state is gone, so a clean finish cannot be proven."""
        facts = status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=True, run_state_retired=True)
        assert status.is_run_live(facts) is True


class TestHarnessNativeTerminalRun:
    """Story 5.11 (FR-196): a bmad-loop-direct run reads as finished, not
    `unknown`, when Marshal's journal never recorded a launch pid."""

    def test_harness_native_terminal_reports_stopped_with_warn(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            harness_native_terminal=True,
            finished=True,
            supervisor_alive=False,
            engine_alive=False,
        )
        row, finding = status.build_fleet_row(facts)
        assert row["state"] == "stopped"
        assert finding is not None
        assert finding.code == "MRS-STATUS-013"
        assert finding.severity is Severity.WARN
        assert "marshal launch pid" in finding.message

    def test_harness_native_terminal_is_not_confused_with_unreadable_journal(self):
        unreadable, _ = status.build_fleet_row(
            status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=True, journal_unreadable=True)
        )
        native, _ = status.build_fleet_row(
            status.FleetHomeFacts(
                slug="acme",
                branch="loop/acme",
                has_run=True,
                harness_native_terminal=True,
                finished=True,
            )
        )
        assert unreadable["state"] == "unknown"
        assert native["state"] == "stopped"

    def test_finished_harness_native_terminal_is_not_live(self):
        facts = status.FleetHomeFacts(
            slug="acme",
            branch="loop/acme",
            has_run=True,
            harness_native_terminal=True,
            finished=True,
        )
        assert status.is_run_live(facts) is False

    def test_harness_native_terminal_end_to_end(self, tmp_path, capsys, monkeypatch):
        """Marshal journal readable but launch-pid-less; bmad-loop state says
        finished -- row must be `stopped` with MRS-STATUS-013, not `unknown`."""
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[_budget_usage_line("acme-run1", cost_estimate=99)],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        harness_run_id = "20260820-140536-988f"
        bmad_run_dir = home / ".bmad-loop" / "runs" / harness_run_id
        bmad_run_dir.mkdir(parents=True)
        (bmad_run_dir / "state.json").write_text(
            json.dumps(
                {
                    "run_id": harness_run_id,
                    "project": str(home),
                    "started_at": "2026-08-20T14:05:36Z",
                    "paused_stage": None,
                    "paused_story_key": None,
                    "paused_reason": None,
                    "finished": True,
                    "tasks": {},
                }
            ),
            encoding="utf-8",
        )
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            terminal_verdicts={(str(home), harness_run_id): "terminal"},
            snapshots={
                (str(home), harness_run_id): _snapshot(finished=True),
            },
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["state"] == "stopped"
        codes = [f["code"] for f in payload["findings"]]
        assert "MRS-STATUS-013" in codes
        assert "MRS-STATUS-002" not in codes
        assert harness.terminal_verdict_calls == [(str(home), harness_run_id)]
        assert exit_code == 0

    def test_non_terminal_verdict_stays_unknown(self, tmp_path, capsys, monkeypatch):
        run_dir = _seed_run_journal(
            tmp_path,
            run_id="acme-run1",
            lines=[_budget_usage_line("acme-run1", cost_estimate=99)],
        )
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": run_dir})
        home = tmp_path / "loop-homes" / "acme"
        harness_run_id = "20260820-140536-988f"
        bmad_run_dir = home / ".bmad-loop" / "runs" / harness_run_id
        bmad_run_dir.mkdir(parents=True)
        (bmad_run_dir / "state.json").write_text("{}", encoding="utf-8")
        vcs = _FakeVcs(worktrees=(WorktreeEntry(path=home, branch="loop/acme"),))
        harness = _FakeHarness(
            terminal_verdicts={(str(home), harness_run_id): "non_terminal"},
        )

        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=harness,
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )

        payload = _payload(capsys)
        row = payload["data"]["homes"][0]
        assert row["state"] == "unknown"
        assert "MRS-STATUS-002" in [f["code"] for f in payload["findings"]]
        assert status.is_run_live(
            status.FleetHomeFacts(slug="acme", branch="loop/acme", has_run=True, journal_unreadable=True)
        )
        assert exit_code == 0


class TestLatestBmadLoopRunId:
    def test_returns_none_when_runs_dir_missing(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir()
        assert status_cli._latest_bmad_loop_run_id(home) is None

    def test_skips_retired_and_dirs_without_state(self, tmp_path):
        home = tmp_path / "home"
        runs = home / ".bmad-loop" / "runs"
        (runs / ".retired-old").mkdir(parents=True)
        (runs / ".retired-old" / "state.json").write_text("{}", encoding="utf-8")
        (runs / "20260820-120000-aaaa").mkdir()
        newer = runs / "20260820-140536-988f"
        newer.mkdir()
        (newer / "state.json").write_text("{}", encoding="utf-8")
        assert status_cli._latest_bmad_loop_run_id(home) == "20260820-140536-988f"


class TestDispatchOnlyCheckoutRows:
    """Story 51.12 (spec-pyforge-marshal CAP-259): a checkout with NO
    ``loop/<slug>`` worktree but a dispatch run in its own Tier-3 -- the
    one-station-per-clone pattern (MRS-DISP-041) -- still yields a fleet row
    for that station, carried by the dispatch overlay. Before this story the
    worktree sweep produced no row, the overlay had nothing to land on, and
    the marshal and steward clones reported ``homes: []`` while their
    dispatch sessions ran (2026-09-20 00:47Z)."""

    def test_dispatch_only_station_gets_a_row_from_its_tier3_run(self, tmp_path, capsys, monkeypatch):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None})
        vcs = _FakeVcs(repo_root_value=tmp_path, worktrees=())
        _write_dispatch_run_journal(
            tmp_path,
            "acme",
            "acme-20260920T000000000Z-deadbeef",
            harness_profile="claude",
            layer_savings={},
        )
        # The real launch shape names the story on the intent entry
        # (`gather_dispatch_journal_facts` reads `story_key` from it); the
        # 46.5 fixture above writes only the outcome + a budget row.
        journal = (
            tmp_path
            / "_bmad-output/projects/acme/implementation-artifacts/dispatch-runs"
            / "acme-20260920T000000000Z-deadbeef"
            / "journal.jsonl"
        )
        journal.write_text(
            json.dumps(
                {
                    "id": {"writer_id": "test", "counter": 1},
                    "ts": "2026-09-20T00:00:00.000Z",
                    "run_id": "acme-20260920T000000000Z-deadbeef",
                    "kind": "dispatch-launch",
                    "phase": "intent",
                    "payload": {"harness_profile": "claude", "story_key": "1.1"},
                }
            )
            + "\n"
            + journal.read_text(),
            encoding="utf-8",
        )
        exit_code = status_cli.run_status(
            _args(project="acme"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        homes = payload["data"]["homes"]
        assert [h["slug"] for h in homes] == ["acme"]
        assert homes[0]["dispatch_run_id"] == "acme-20260920T000000000Z-deadbeef"
        assert homes[0]["branch"] == "loop/acme"
        assert exit_code == 0

    def test_dispatch_only_station_is_scoped_by_project_and_never_duplicates_a_loop_home(
        self, tmp_path, capsys, monkeypatch
    ):
        _stub_latest_run_dir(monkeypatch, run_dir_map={"acme": None, "beta": None})
        home = tmp_path / "loop-homes" / "acme"
        vcs = _FakeVcs(
            repo_root_value=tmp_path,
            worktrees=(WorktreeEntry(path=home, branch="loop/acme"),),
        )
        for slug in ("acme", "beta"):
            _write_dispatch_run_journal(tmp_path, slug, f"{slug}-run", harness_profile="claude", layer_savings={})
        # Fleet sweep: the loop-home station appears once (overlaid, not
        # duplicated by its own Tier-3 run); the dispatch-only sibling appears too.
        exit_code = status_cli.run_status(
            _args(),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert sorted(h["slug"] for h in payload["data"]["homes"]) == ["acme", "beta"]
        assert exit_code == 0
        # `--project` still scopes a dispatch-only station like any other.
        capsys.readouterr()
        status_cli.run_status(
            _args(project="beta"),
            vcs=vcs,
            fs=LocalFs(),
            harness=_FakeHarness(),
            process=_FakeProcess(),
            clock=_FakeClock(now=_FIXED_NOW),
        )
        payload = _payload(capsys)
        assert [h["slug"] for h in payload["data"]["homes"]] == ["beta"]

    def test_checkout_without_projects_dir_yields_no_dispatch_only_rows(self, tmp_path):
        assert status_cli._dispatch_only_slugs(tmp_path) == ()
