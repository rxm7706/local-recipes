"""``dagster-dryrun`` gate (Story C1, FR-6, AC-5) — DEFINITIONS LOAD ONLY.

This is a STRUCTURAL, OFFLINE gate: it imports the glue module, builds the
Dagster ``Definitions``, and asserts the Story C1 acceptance criteria hold —
schedules enumerate, jobs resolve, every op carries its OWN timeout, Phase P is
admin-only, and the profile precedence rule holds. It performs **NO live
execution** — no Dagster daemon, no ``dagster dev``, no scheduled run. Building
``Definitions`` from :class:`kedro_dagster.KedroProjectTranslator` does no
network IO (the Wave-B catalog datasets take injected fetchers that default to
offline; the ``local`` env resolves only placeholder credentials).

The attended live schedule bring-up (real daemon + credentialed scheduled runs)
is DEFERRED — see ``implementation-artifacts/deferred-work.md`` (DW-C1).
"""

from __future__ import annotations

import re

import dagster as dg
import pytest

from pyforge.atlas.orchestration import definitions as D

MAX_RUNTIME_TAG = "dagster/max_runtime"
_CRON_RE = re.compile(r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+$")


@pytest.fixture(scope="module")
def defs() -> dg.Definitions:
    """The built definitions (module-level ``D.defs`` — built offline at import)."""
    assert isinstance(D.defs, dg.Definitions)
    return D.defs


# --------------------------------------------------------------------------- #
# AC-5 (a) — definitions load, schedules enumerate, jobs resolve.
# --------------------------------------------------------------------------- #


def test_definitions_are_loadable(defs):
    """The full offline dryrun: Dagster's own loadability check passes with no
    live instance."""
    dg.Definitions.validate_loadable(defs)


def test_jobs_resolve(defs):
    names = {j.name for j in defs.jobs}
    expected = (
        {D.BOOTSTRAP_JOB_NAME, D.PHASE_P_JOB_NAME}
        | {job_name for job_name, *_ in D.SCHEDULED_JOBS}
    )
    assert expected <= names, f"missing jobs: {expected - names}"
    # each job actually resolves into a graph of ops (not empty).
    for job in defs.jobs:
        assert list(job.graph.nodes), f"job {job.name} resolved to zero ops"


def test_schedules_enumerate(defs):
    sched_names = {s.name for s in defs.schedules}
    # bootstrap + every cadence entry has a schedule.
    assert f"{D.BOOTSTRAP_JOB_NAME}_schedule" in sched_names
    for job_name, *_ in D.SCHEDULED_JOBS:
        assert f"{job_name}_schedule" in sched_names, f"no schedule for {job_name}"
    # Phase P is the only job WITHOUT a schedule.
    scheduled_jobs = {s.job_name for s in defs.schedules}
    assert scheduled_jobs == {D.BOOTSTRAP_JOB_NAME} | {
        j for j, *_ in D.SCHEDULED_JOBS
    }


def test_all_cron_strings_are_well_formed(defs):
    for s in defs.schedules:
        assert _CRON_RE.match(s.cron_schedule), f"malformed cron on {s.name}: {s.cron_schedule!r}"


def test_cadence_table_is_encoded(defs):
    """Every row of guides/atlas-operations.md cron cadence table is present at
    the right cadence (AC-1)."""
    by_job = {job_name: (ops, cron, cadence) for job_name, ops, cron, cadence, _ in D.SCHEDULED_JOBS}
    # weekly bootstrap "everything"
    boot_sched = next(s for s in defs.schedules if s.job_name == D.BOOTSTRAP_JOB_NAME)
    assert boot_sched.cron_schedule == "0 2 * * 0"  # weekly
    # cadence -> expected cron prefix pattern
    expected_cadence = {
        "phase_f_anaconda_downloads": "daily",
        "phase_h_pypi_versions": "daily",
        "phase_g_vdb_summary": "daily",
        "phase_e5_archived_feedstocks": "daily",
        "phase_k_vcs_upstream": "daily",
        "phase_l_registries": "daily",
        "phase_ejm_cfgraph": "6h",
        "phase_n_live_health": "hourly",
        "refresh_assets": "weekly",
    }
    assert set(by_job) == set(expected_cadence), "cadence job set drifted from the table"
    for job_name, cadence in expected_cadence.items():
        _ops, cron, actual_cadence = by_job[job_name]
        assert actual_cadence == cadence
        if cadence == "6h":
            assert cron == "0 */6 * * *"
        elif cadence == "hourly":
            assert cron == "0 * * * *"
        elif cadence == "weekly":
            assert cron.endswith("* * 0"), f"{job_name} weekly cron not Sunday: {cron}"
        elif cadence == "daily":
            # daily = fires once per day (no */N in the day-of-month field).
            assert cron.split()[2] == "*" and cron.split()[4] == "*", cron


# --------------------------------------------------------------------------- #
# AC-4 — per-node timeouts: each op its OWN budget, NOT one monolith.
# --------------------------------------------------------------------------- #


def test_every_op_has_its_own_timeout(defs):
    """Each op in every job carries an independent ``dagster/max_runtime`` tag."""
    for job in defs.jobs:
        for node in job.graph.nodes:
            assert node.tags.get(MAX_RUNTIME_TAG), (
                f"op {node.name} in job {job.name} has no independent timeout"
            )


def test_timeouts_are_not_a_single_monolith(defs):
    """The legacy 1800s cf_atlas_core monolith is retired: timeouts vary per op
    and live on the OPS, never as one job-level timeout wrapping the DAG."""
    values = {
        node.tags[MAX_RUNTIME_TAG]
        for job in defs.jobs
        for node in job.graph.nodes
    }
    assert len(values) > 1, "all ops share one timeout — monolith not retired"
    # no job-level monolithic timeout tag.
    for job in defs.jobs:
        assert MAX_RUNTIME_TAG not in job.tags, (
            f"job {job.name} carries a monolithic job-level timeout"
        )


def test_phase_r_overrun_cannot_abort_phase_f_k_n(defs):
    """The whole point of AC-4: Phase R's big budget is ITS OWN; Phase F/K/N
    each carry a smaller, independent budget so an R overrun cannot abort them."""
    budgets = {
        node.name: int(node.tags[MAX_RUNTIME_TAG])
        for job in defs.jobs
        for node in job.graph.nodes
    }
    r_budget = budgets["enrich_pypi_intelligence"]  # Phase R cold pull
    for phase_op in ("compute_downloads", "track_upstream_versions", "fetch_live_health"):
        assert budgets[phase_op] < r_budget, (
            f"{phase_op} shares/exceeds Phase R's budget — not independent"
        )
    # every migrated node is mapped explicitly (no silent shared default).
    assert set(D.NODE_TIMEOUTS), "NODE_TIMEOUTS is empty"


# --------------------------------------------------------------------------- #
# AC-6 — Phase P is admin-config-only, never on a default schedule.
# --------------------------------------------------------------------------- #


def test_phase_p_job_exists_but_is_unscheduled(defs):
    job_names = {j.name for j in defs.jobs}
    assert D.PHASE_P_JOB_NAME in job_names  # reachable via admin config
    scheduled_jobs = {s.job_name for s in defs.schedules}
    assert D.PHASE_P_JOB_NAME not in scheduled_jobs


def test_phase_p_op_is_in_no_scheduled_job(defs):
    """No SCHEDULED job's graph contains the Phase P op — including the weekly
    'everything' bootstrap, which excludes it by construction."""
    scheduled_job_names = {s.job_name for s in defs.schedules}
    for job in defs.jobs:
        if job.name not in scheduled_job_names:
            continue
        ops = {n.name for n in job.graph.nodes}
        assert "fetch_pypi_downloads" not in ops, (
            f"Phase P leaked into scheduled job {job.name}"
        )


def test_phase_p_reachable_only_via_admin_profile():
    assert D.PROFILES["admin"]["phase_p"] == "enabled"
    assert D.PROFILES["maintainer"]["phase_p"] == "disabled"
    assert D.PROFILES["consumer"]["phase_p"] == "disabled"


# --------------------------------------------------------------------------- #
# AC-2 — three bootstrap profiles + override precedence.
# --------------------------------------------------------------------------- #


def test_three_named_profiles_exist():
    assert set(D.PROFILES) == {"maintainer", "admin", "consumer"}
    # per-phase scoping per the guide.
    assert D.PROFILES["maintainer"]["phase_e"] == "auto-scoped"
    assert D.PROFILES["maintainer"]["phase_n"] == "auto-scoped"
    assert D.PROFILES["admin"]["scope"] == "channel-wide"
    assert D.PROFILES["consumer"]["read_only"] == "true"
    assert D.PROFILES["consumer"]["phase_n"] == "disabled"


def test_profile_default_used_when_no_env_no_override():
    cfg = D.resolve_profile_config("maintainer", env={}, overrides=None)
    assert cfg["scope"] == "maintainer"


def test_explicit_env_beats_profile_default():
    cfg = D.resolve_profile_config("maintainer", env={"PYFORGE_ATLAS_SCOPE": "env-scope"})
    assert cfg["scope"] == "env-scope"


def test_explicit_run_config_beats_env_and_profile():
    cfg = D.resolve_profile_config(
        "maintainer",
        env={"PYFORGE_ATLAS_SCOPE": "env-scope"},
        overrides={"scope": "explicit"},
    )
    assert cfg["scope"] == "explicit"  # explicit run-config wins


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        D.resolve_profile_config("nope", env={})


# --------------------------------------------------------------------------- #
# AC-3 / AD-23 — retries + one execution plane.
# --------------------------------------------------------------------------- #


def test_ops_carry_retry_policy_for_observability(defs):
    for job in defs.jobs:
        for node in job.graph.nodes:
            assert node.retry_policy is not None, (
                f"op {node.name} in {job.name} has no retry policy"
            )


def test_jobs_carry_phase_state_observability_tags(defs):
    for job in defs.jobs:
        assert job.tags.get("pyforge/phase_state") == "observable"


def test_single_execution_plane_kedro_run_resource(defs):
    """AD-23 — the one execution plane is KedroSession.run, surfaced as the
    ``kedro_run`` resource from the translator; the glue never adds a second."""
    assert "kedro_run" in defs.resources
