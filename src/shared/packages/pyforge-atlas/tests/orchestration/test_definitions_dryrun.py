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


# The Wave-H factory crew jobs are ASSET jobs (define_asset_job), a different KIND of job from the
# kedro op-graph jobs the C1/G3 invariants below govern (per-op timeouts, phase_state tags, Phase-P
# scheduling). Scope those invariants to the kedro op-jobs so the factory jobs — which legitimately
# carry neither kedro ops nor those tags — don't trip them (Story H4).
FACTORY_JOB_NAMES = {D.WIKI_COMPILE_JOB_NAME, D.WIKI_LINT_JOB_NAME}


def _kedro_jobs(defs):
    """The op-graph kedro jobs (excludes the Wave-H factory asset jobs)."""
    return [j for j in defs.jobs if j.name not in FACTORY_JOB_NAMES]


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
    # each kedro op-job actually resolves into a graph of ops (not empty).
    for job in _kedro_jobs(defs):
        assert list(job.graph.nodes), f"job {job.name} resolved to zero ops"


def test_schedules_enumerate(defs):
    sched_names = {s.name for s in defs.schedules}
    # bootstrap + every cadence entry has a schedule.
    assert f"{D.BOOTSTRAP_JOB_NAME}_schedule" in sched_names
    for job_name, *_ in D.SCHEDULED_JOBS:
        assert f"{job_name}_schedule" in sched_names, f"no schedule for {job_name}"
    # Phase P is the only KEDRO job WITHOUT a schedule (the Wave-H factory adds the weekly
    # wiki_lint_schedule → wiki_lint_job, which is NOT a kedro data-pipeline job).
    scheduled_jobs = {s.job_name for s in defs.schedules}
    assert scheduled_jobs == {D.BOOTSTRAP_JOB_NAME} | {
        j for j, *_ in D.SCHEDULED_JOBS
    } | {D.WIKI_LINT_JOB_NAME}


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
    """Each op in every kedro job carries an independent ``dagster/max_runtime`` tag."""
    for job in _kedro_jobs(defs):
        for node in job.graph.nodes:
            assert node.tags.get(MAX_RUNTIME_TAG), (
                f"op {node.name} in job {job.name} has no independent timeout"
            )


def test_timeouts_are_not_a_single_monolith(defs):
    """The legacy 1800s cf_atlas_core monolith is retired: timeouts vary per op
    and live on the OPS, never as one job-level timeout wrapping the DAG."""
    values = {
        node.tags[MAX_RUNTIME_TAG]
        for job in _kedro_jobs(defs)
        for node in job.graph.nodes
    }
    assert len(values) > 1, "all ops share one timeout — monolith not retired"
    # no job-level monolithic timeout tag.
    for job in _kedro_jobs(defs):
        assert MAX_RUNTIME_TAG not in job.tags, (
            f"job {job.name} carries a monolithic job-level timeout"
        )


def test_phase_r_overrun_cannot_abort_phase_f_k_n(defs):
    """The whole point of AC-4: Phase R's big budget is ITS OWN; Phase F/K/N
    each carry a smaller, independent budget so an R overrun cannot abort them."""
    budgets = {
        node.name: int(node.tags[MAX_RUNTIME_TAG])
        for job in _kedro_jobs(defs)
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
    for job in _kedro_jobs(defs):
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
    for job in _kedro_jobs(defs):
        for node in job.graph.nodes:
            assert node.retry_policy is not None, (
                f"op {node.name} in {job.name} has no retry policy"
            )


def test_jobs_carry_phase_state_observability_tags(defs):
    for job in _kedro_jobs(defs):
        assert job.tags.get("pyforge/phase_state") == "observable"


def test_single_execution_plane_kedro_run_resource(defs):
    """AD-23 — the one execution plane is KedroSession.run, surfaced as the
    ``kedro_run`` resource from the translator; the glue never adds a second."""
    assert "kedro_run" in defs.resources


# --------------------------------------------------------------------------- #
# Story G3 (FR-6, § 5.9) — event-driven sensors.
#
# (a) sensors ENUMERATE in the Definitions + each targets a REAL existing job
#     (AD-23 — the sensor rides the SAME job machinery C1 built, never a second
#     execution plane); (b) a SIMULATED upstream event (injected offline source +
#     ``build_sensor_context``) → a ``RunRequest`` for the right incremental job;
#     a no-event tick → ``SkipReason``. No network anywhere (the source is a
#     fixture callable). The LIVE sensor daemon is deferred (DW-G3).
# --------------------------------------------------------------------------- #


def test_sensors_enumerate_in_definitions(defs):
    """The G3 sensors are declared in ``defs`` (else they do nothing at all)."""
    sensor_names = {s.name for s in defs.sensors}
    expected = {name for name, *_ in D.UPSTREAM_SENSORS}
    assert expected <= sensor_names, f"missing sensors: {expected - sensor_names}"


def test_each_sensor_targets_a_real_existing_job(defs):
    """AD-23 — every sensor targets a job that actually exists in ``defs`` (it
    rides an existing C1 job; it defines no second execution plane)."""
    job_names = {j.name for j in defs.jobs}
    for _name, target_job, *_ in D.UPSTREAM_SENSORS:
        assert target_job in job_names, f"sensor target {target_job} is not a real job"
    # and each SensorDefinition in defs resolves to a job present in defs.
    for sensor in defs.sensors:
        assert sensor.job_name in job_names, (
            f"sensor {sensor.name} targets non-existent job {sensor.job_name}"
        )


def test_sensor_targets_are_the_incremental_upstream_jobs(defs):
    """Pins the sensor targets to the two upstream jobs whose datasets A3 flipped
    to ``IncrementalParquetDataset`` (Phase H PyPI versions + Phase K VCS upstream)
    — a drift-guard so a sensor can't be re-pointed at a non-incremental job. The
    AD-5 dataset coupling itself is proven by the A2/A3 catalog gate, not here."""
    targets = {target for _n, target, *_ in D.UPSTREAM_SENSORS}
    assert targets == {"phase_h_pypi_versions", "phase_k_vcs_upstream"}


def test_sensors_ship_stopped(defs):
    """Sensors never auto-start (mirrors the schedules' no-auto-start stance) —
    turning them RUNNING against a live feed is the attended bring-up (DW-G3)."""
    import dagster as dg  # local — the gate may import dagster freely (not scanned)

    for sensor in defs.sensors:
        assert sensor.default_status == dg.DefaultSensorStatus.STOPPED


def _sim_source(*events):
    """A fixture RSS/poll feed snapshot (no network) — a zero-arg callable."""
    payload = list(events)
    return lambda: payload


def _pypi_job(defs):
    return next(j for j in defs.jobs if j.name == "phase_h_pypi_versions")


def test_simulated_event_yields_run_request_for_the_right_job(defs):
    """AC (G3): a simulated upstream event → exactly ONE ``RunRequest`` for the
    correct incremental job, and the cursor advances to the event's seq."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_sim_source({"seq": 7, "id": "requests"}),
    )
    ctx = dg.build_sensor_context()
    results = list(sensor(ctx))
    run_requests = [r for r in results if isinstance(r, dg.RunRequest)]
    assert len(run_requests) == 1, results
    assert run_requests[0].run_key == "pypi:7"
    assert sensor.job_name == "phase_h_pypi_versions"
    assert ctx.cursor == "7"  # advanced


def test_no_event_yields_skip_reason(defs):
    """A no-new-event tick yields ``SkipReason`` (never a spurious run), and the
    cursor is left untouched."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=D.offline_event_source,  # returns []
    )
    ctx = dg.build_sensor_context(cursor="3")
    results = list(sensor(ctx))
    assert results and all(isinstance(r, dg.SkipReason) for r in results)
    assert ctx.cursor == "3"  # untouched


def test_duplicate_event_is_deduped_by_cursor(defs):
    """A duplicate tick (cursor already past the event's seq) → ``SkipReason`` —
    no double-trigger."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_sim_source({"seq": 2, "id": "a"}),
    )
    ctx = dg.build_sensor_context(cursor="2")  # already processed seq 2
    results = list(sensor(ctx))
    assert all(isinstance(r, dg.SkipReason) for r in results)


def test_multiple_events_one_tick_coalesce_to_one_run(defs):
    """Multiple new events in one tick → ONE coalesced ``RunRequest`` (the job is
    incremental — one run drains all stale rows), cursor advances to the max seq."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_sim_source(
            {"seq": 4, "id": "a"}, {"seq": 6, "id": "b"}, {"seq": 5, "id": "c"}
        ),
    )
    ctx = dg.build_sensor_context()
    run_requests = [r for r in sensor(ctx) if isinstance(r, dg.RunRequest)]
    assert len(run_requests) == 1
    assert run_requests[0].run_key == "pypi:6"  # keyed by the max seq
    assert run_requests[0].tags["pyforge/event_count"] == "3"
    assert ctx.cursor == "6"


def test_malformed_event_payload_does_not_crash(defs):
    """A malformed payload (missing/garbage fields) is dropped — a feed of only
    malformed items yields ``SkipReason``, never an exception."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_sim_source({"nope": 1}, {"seq": "x", "id": "a"}, {"seq": -1, "id": "b"}),
    )
    results = list(sensor(dg.build_sensor_context()))
    assert all(isinstance(r, dg.SkipReason) for r in results)


def test_event_source_that_raises_degrades_not_crashes(defs):
    """A source that raises must degrade to ``SkipReason`` — a flaky feed must not
    crash the sensor daemon (Reviewer-B)."""
    import dagster as dg

    def _raising():
        raise RuntimeError("feed unreachable")

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_raising,
    )
    results = list(sensor(dg.build_sensor_context()))
    assert len(results) == 1 and isinstance(results[0], dg.SkipReason)
    assert "feed unreachable" in results[0].skip_message


def test_cursor_advances_across_successive_ticks(defs):
    """The cursor advances monotonically across evals: a new event past the
    persisted cursor fires; a later tick with only already-seen events skips."""
    import dagster as dg

    job = _pypi_job(defs)
    # tick 1: cursor at 5, a seq-8 event fires and advances to 8.
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_sim_source({"seq": 8, "id": "a"}),
    )
    ctx = dg.build_sensor_context(cursor="5")
    assert any(isinstance(r, dg.RunRequest) for r in sensor(ctx))
    assert ctx.cursor == "8"
    # tick 2: same event, cursor now 8 → deduped.
    ctx2 = dg.build_sensor_context(cursor="8")
    assert all(isinstance(r, dg.SkipReason) for r in sensor(ctx2))


def test_built_defs_sensors_are_offline_and_only_skip(defs):
    """The sensors actually WIRED into ``defs`` ship the offline no-op source
    (DW-G3): driving each one with a fresh context yields ONLY ``SkipReason`` and
    fires no run — proving no network/live source leaked into the built
    definitions (a sensor accidentally wired with a live source would fire or
    error here)."""
    import dagster as dg

    for sensor in defs.sensors:
        results = list(sensor(dg.build_sensor_context()))
        assert results and all(isinstance(r, dg.SkipReason) for r in results), (
            f"sensor {sensor.name} did not skip on the offline default: {results}"
        )


def test_offline_event_source_returns_empty(defs):
    """The offline default source is a pure no-op (returns ``[]``, no network)."""
    assert D.offline_event_source() == []


def test_garbage_or_empty_cursor_is_treated_as_cold(defs):
    """An empty-string or non-numeric cursor means "nothing processed yet" (cold),
    so a first event still fires — a corrupt cursor must not silently swallow
    events or raise."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_sim_source({"seq": 1, "id": "a"}),
    )
    for bad_cursor in ("", "abc"):
        ctx = dg.build_sensor_context(cursor=bad_cursor)
        run_requests = [r for r in sensor(ctx) if isinstance(r, dg.RunRequest)]
        assert len(run_requests) == 1, f"cold cursor {bad_cursor!r} did not fire"
        assert ctx.cursor == "1"


def test_mix_of_new_and_already_seen_events_counts_only_the_new(defs):
    """A snapshot mixing already-seen (seq <= cursor) and new (seq > cursor) events
    triggers on the NEW ones only; run_key + cursor land on the max NEW seq and the
    event_count excludes the already-seen items."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        # seq 3,4,5 already seen (cursor 5); 6,7 are new.
        event_source=_sim_source(
            {"seq": 3, "id": "a"}, {"seq": 5, "id": "b"},
            {"seq": 6, "id": "c"}, {"seq": 7, "id": "d"},
        ),
    )
    ctx = dg.build_sensor_context(cursor="5")
    run_requests = [r for r in sensor(ctx) if isinstance(r, dg.RunRequest)]
    assert len(run_requests) == 1
    assert run_requests[0].run_key == "pypi:7"
    assert run_requests[0].tags["pyforge/event_count"] == "2"  # only 6 and 7
    assert ctx.cursor == "7"


def test_duplicate_seq_within_one_snapshot_counts_once(defs):
    """Two feed items sharing a ``seq`` collapse to one distinct change — the
    coalesced run fires once and ``event_count`` reflects distinct seqs."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_sim_source({"seq": 6, "id": "a"}, {"seq": 6, "id": "a-dup"}),
    )
    ctx = dg.build_sensor_context()
    run_requests = [r for r in sensor(ctx) if isinstance(r, dg.RunRequest)]
    assert len(run_requests) == 1
    assert run_requests[0].tags["pyforge/event_count"] == "1"
    assert ctx.cursor == "6"


def test_none_and_none_id_items_are_dropped(defs):
    """A ``None`` snapshot item and an item with ``id=None`` are dropped (not
    crashed, not kept with a ``"None"`` identifier) — a feed of only such items
    skips."""
    import dagster as dg

    job = _pypi_job(defs)
    sensor = D.build_upstream_sensor(
        name="pypi_release_sensor",
        job=job,
        run_key_prefix="pypi",
        description="test",
        event_source=_sim_source(None, {"seq": 9, "id": None}),
    )
    results = list(sensor(dg.build_sensor_context()))
    assert all(isinstance(r, dg.SkipReason) for r in results)


# --------------------------------------------------------------------------- #
# Story H4 (FR-22(d)/FR-6, § 7.2) — orchestrate the Wave-H crews via Dagster.
#
# (a) the crew ASSETS enumerate; (b) the crew asset-jobs resolve; (c) a weekly
#     LINT schedule fires the lint job; (d) a SIMULATED new-raw-file event →
#     a ``RunRequest`` for the compile job (via an injected raw lister +
#     ``build_sensor_context``); a no-new-file tick → ``SkipReason``. All on the
#     SAME Dagster plane (AD-6/AD-23). No network. Live wiki store bring-up is
#     deferred (DW-H4).
# --------------------------------------------------------------------------- #


def test_crew_assets_enumerate(defs):
    """AC (H4): an asset dry-run enumerates the crew assets."""
    keys = {s.key.to_user_string() for s in defs.resolve_all_asset_specs()}
    assert {"compiled_wiki", "wiki_lint_report"} <= keys, f"missing crew assets: {keys}"


def test_crew_asset_jobs_resolve(defs):
    job_names = {j.name for j in defs.jobs}
    assert {D.WIKI_COMPILE_JOB_NAME, D.WIKI_LINT_JOB_NAME} <= job_names


def test_weekly_lint_schedule_fires_the_lint_job(defs):
    sched = next(s for s in defs.schedules if s.name == "wiki_lint_schedule")
    assert sched.job_name == D.WIKI_LINT_JOB_NAME
    assert sched.cron_schedule == D.WIKI_LINT_CRON
    # weekly = a specific day-of-week field (not '*').
    assert sched.cron_schedule.split()[4] != "*"


def test_compile_sensor_enumerates_and_targets_the_compile_job(defs):
    names = {s.name for s in defs.sensors}
    assert D.WIKI_RAW_SENSOR_NAME in names
    sensor = next(s for s in defs.sensors if s.name == D.WIKI_RAW_SENSOR_NAME)
    assert sensor.job_name == D.WIKI_COMPILE_JOB_NAME  # AD-23: SAME plane, existing job


def _compile_job(defs):
    return next(j for j in defs.jobs if j.name == D.WIKI_COMPILE_JOB_NAME)


def test_simulated_new_raw_file_triggers_the_compile_crew(defs):
    """AC (H4): a simulated new-raw-file event triggers the compile crew via the sensor."""
    import dagster as dg

    sensor = D.build_wiki_compile_sensor(
        job=_compile_job(defs),
        raw_lister=lambda: ["duckdb.md", "kedro.md"],  # two raw docs appear
    )
    ctx = dg.build_sensor_context()
    results = list(sensor(ctx))
    run_requests = [r for r in results if isinstance(r, dg.RunRequest)]
    assert len(run_requests) == 1, results
    assert run_requests[0].tags["pyforge/new_docs"] == "2"
    assert sensor.job_name == D.WIKI_COMPILE_JOB_NAME
    assert ctx.cursor  # advanced to the seen-set


def test_no_new_raw_file_yields_skip(defs):
    import dagster as dg

    sensor = D.build_wiki_compile_sensor(job=_compile_job(defs), raw_lister=lambda: [])
    results = list(sensor(dg.build_sensor_context(cursor="[]")))
    assert results and all(isinstance(r, dg.SkipReason) for r in results)


def test_already_seen_raw_files_are_deduped(defs):
    import dagster as dg
    import json as _json

    sensor = D.build_wiki_compile_sensor(
        job=_compile_job(defs), raw_lister=lambda: ["a.md"]
    )
    # cursor already records a.md as seen -> no re-trigger.
    ctx = dg.build_sensor_context(cursor=_json.dumps(["a.md"]))
    results = list(sensor(ctx))
    assert all(isinstance(r, dg.SkipReason) for r in results)


def test_raw_lister_error_degrades_to_skip(defs):
    """A failing lister must NOT crash the sensor daemon — it degrades to a skip."""
    import dagster as dg

    def _boom():
        raise RuntimeError("wiki store unreachable")

    sensor = D.build_wiki_compile_sensor(job=_compile_job(defs), raw_lister=_boom)
    results = list(sensor(dg.build_sensor_context()))
    assert results and all(isinstance(r, dg.SkipReason) for r in results)


def test_compile_sensor_ships_stopped(defs):
    import dagster as dg

    sensor = next(s for s in defs.sensors if s.name == D.WIKI_RAW_SENSOR_NAME)
    assert sensor.default_status == dg.DefaultSensorStatus.STOPPED


# --- wiki_events unit tests (dagster-free decision logic) ------------------------------


def test_evaluate_raw_scan_new_docs_trigger_run():
    from pyforge.atlas.orchestration.wiki_events import evaluate_raw_scan

    d = evaluate_raw_scan(["a.md", "b.md"], None)
    assert d.run and d.new_docs == ("a.md", "b.md") and d.run_key
    # a second scan against the advanced cursor with nothing new -> no run.
    d2 = evaluate_raw_scan(["a.md", "b.md"], d.new_cursor)
    assert not d2.run and d2.new_cursor == d.new_cursor  # cursor unchanged on skip


def test_evaluate_raw_scan_run_key_is_deterministic():
    from pyforge.atlas.orchestration.wiki_events import evaluate_raw_scan

    a = evaluate_raw_scan(["x.md"], None)
    b = evaluate_raw_scan(["x.md"], None)
    assert a.run_key == b.run_key  # same new set -> same key (Dagster idempotency)


def test_scan_raw_docs_missing_dir_is_empty(tmp_path):
    from pyforge.atlas.orchestration.wiki_events import scan_raw_docs

    assert scan_raw_docs(tmp_path / "nope") == ()
