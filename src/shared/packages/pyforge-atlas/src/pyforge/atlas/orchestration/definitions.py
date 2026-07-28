"""Dagster ``Definitions`` for the migrated cf_atlas orchestrator (Story C1, FR-6).

This module (``pyforge.atlas.orchestration.definitions``) is the **replaceable
orchestration glue** (AD-1 / AD-6): it is the only module in ``pyforge.atlas``
permitted to import ``dagster`` / ``kedro_dagster``. The subpackage is named
``orchestration`` (not ``dagster``) to avoid shadowing the top-level
``dagster`` dependency. It compiles the Kedro project into Dagster via
:class:`kedro_dagster.KedroProjectTranslator` and layers on the four things
kedro-dagster does not provide natively but Story C1 requires:

1. **Schedules** encoding the ``guides/atlas-operations.md`` cadence table
   (:data:`SCHEDULED_JOBS` + :data:`BOOTSTRAP`), each targeting a node-subset
   job of the migrated DAG.
2. **Three bootstrap profiles** (maintainer / admin / consumer) as named run
   configs with the guide's override precedence — explicit run-config/env beats
   profile defaults (:func:`resolve_profile_config`).
3. **Retry policy + observability tags** so runs/retries surface in the UI.
4. **Per-node timeouts** — every op carries its OWN ``dagster/max_runtime``
   budget (:data:`NODE_TIMEOUTS`), structurally retiring the legacy single
   ``1800s`` ``cf_atlas_core`` monolithic timeout that silently dropped phases.

AD-23 — ONE execution plane: the ops are kedro-dagster's translated ops, which
run each Kedro node through the ``kedro_run`` resource (``KedroSession.run``);
this glue only *wraps* that plane (subset, tag, schedule) — it never adds a
second one. The base job uses the ``in_process`` executor declared in
``conf/base/dagster.yml``, which serializes ops *within* a single run. It is
**NOT** cross-run admission: two concurrent triggers of the same dataset set are
not serialized, rejected, or queued (``DW-AD23-1``; audit ``AUD-ATLAS-046``).
This comment previously claimed "run admission serializes per dataset set" — it
does not. Do not rely on single-writer safety here.

**Offline / dryrun**: building these definitions performs NO network IO — the
Kedro catalog datasets take injected fetchers that default to offline (Wave B),
and the ``local`` env resolves only placeholder credentials. The
``dagster-dryrun`` gate (``tests/orchestration/test_definitions_dryrun.py``) imports
this module, builds :data:`defs`, and asserts schedules enumerate + jobs
resolve + each op has an independent timeout — with NO live execution.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

import dagster as dg
from kedro_dagster import KedroProjectTranslator

from pyforge.atlas.factory.crews import CompileCrew, LintCrew
from pyforge.atlas.factory.wiki import WikiLayout, scaffold_wiki
from pyforge.atlas.orchestration.event_source import (
    EventSource,
    evaluate_events,
    offline_event_source,
)
from pyforge.atlas.orchestration.wiki_events import (
    WikiScanDecision,
    evaluate_raw_scan,
    scan_raw_docs,
)

# --------------------------------------------------------------------------- #
# Kedro project location (this package's project root — has conf/, settings.py,
# pipeline_registry.py). Resolved from THIS file so it is cwd-independent.
# --------------------------------------------------------------------------- #
PROJECT_PATH = Path(__file__).resolve().parents[4]

# The Kedro env used to translate. ``local`` layers conf/local/credentials.yml
# (placeholder stubs) on top of ``base`` so credential-scoped catalog entries
# resolve offline; overridable via KEDRO_ENV for real deployments.
DEFAULT_ENV = os.environ.get("KEDRO_ENV", "local")

# --------------------------------------------------------------------------- #
# Phase -> node(-op) mapping.
#
# kedro-dagster names each op after its Kedro node (``format_node_name`` is the
# identity for these already-valid names). Phases span pipelines; a cadence job
# is an op-subset of the single migrated ``__default__`` DAG, so cross-pipeline
# phases (E+J+M) compose without a procedural driver (FR-2 / AD-3).
# --------------------------------------------------------------------------- #

# Phase P (PyPI monthly downloads via BigQuery) — admin-config-only, NEVER on a
# default schedule (AC-6). Credentialed + attended (NFR-2). It is reachable
# ONLY through the :data:`PHASE_P_JOB_NAME` job under the ``admin`` profile;
# the weekly ``bootstrap_data`` job EXCLUDES it by construction.
PHASE_P_OPS: tuple[str, ...] = ("fetch_pypi_downloads",)
PHASE_P_JOB_NAME = "phase_p_pypi_downloads"

# Cadence schedules encoding guides/atlas-operations.md § "Cron schedules".
# Each entry: (job_name, [ops], cron, cadence_label, phase_label).
SCHEDULED_JOBS: tuple[tuple[str, list[str], str, str, str], ...] = (
    # daily
    (
        "phase_f_anaconda_downloads",
        ["compute_downloads", "compute_version_download_history"],
        "0 3 * * *",
        "daily",
        "Phase F (anaconda.org download counts)",
    ),
    (
        "phase_h_pypi_versions",
        ["fetch_pypi_current_versions", "snapshot_pypi_serials"],
        "0 3 * * *",
        "daily",
        "Phase H (PyPI current versions / behind-upstream)",
    ),
    (
        "phase_g_vdb_summary",
        ["summarize_vdb_vulns"],
        "0 4 * * *",
        "daily",
        "Phase G (vdb risk summary — runs after vdb-refresh)",
    ),
    (
        "phase_e5_archived_feedstocks",
        ["detect_archived_feedstocks"],
        "0 3 * * *",
        "daily",
        "Phase E.5 (archived feedstocks via GraphQL)",
    ),
    (
        "phase_k_vcs_upstream",
        ["track_upstream_versions"],
        "0 3 * * *",
        "daily",
        "Phase K (VCS upstream — GitHub/GitLab/Codeberg)",
    ),
    (
        "phase_l_registries",
        ["track_registry_versions"],
        "0 3 * * *",
        "daily",
        "Phase L (npm/CRAN/CPAN/LuaRocks/crates/RubyGems/NuGet/Maven)",
    ),
    # every 6h
    (
        "phase_ejm_cfgraph",
        ["enrich_maintainers", "build_dependency_graph", "compute_feedstock_health"],
        "0 */6 * * *",
        "6h",
        "Phase E + J + M (cf-graph cached pull: maintainers, dep graph, health)",
    ),
    # hourly
    (
        "phase_n_live_health",
        ["fetch_live_health"],
        "0 * * * *",
        "hourly",
        "Phase N (live GitHub CI / issues / PRs — per maintainer)",
    ),
    # weekly refresh assets
    (
        "refresh_assets",
        ["refresh_vdb_store", "refresh_osv_offline_store", "export_pypi_conda_map"],
        "0 1 * * 0",
        "weekly",
        "refresh assets (vdb-refresh / update-cve-db / update-mapping-cache)",
    ),
)

# Weekly "everything" bootstrap = the whole migrated DAG EXCEPT Phase P.
BOOTSTRAP_JOB_NAME = "bootstrap_data"
BOOTSTRAP_CRON = "0 2 * * 0"  # weekly, Sunday 02:00

# --------------------------------------------------------------------------- #
# Per-node timeouts (seconds) — each op's OWN budget (AC-4).
#
# This DICT is the structural retirement of the legacy 1800s ``cf_atlas_core``
# monolithic timeout. Two things replace the monolith, and it matters which does
# what (Reviewer-A F2 — do not overclaim runtime enforcement):
#
#  1. STRUCTURAL (here): instead of ONE timeout wrapping every phase, each node
#     carries an INDEPENDENT ``dagster/max_runtime`` tag — there is no single
#     job/run-level timeout anywhere (``test_timeouts_are_not_a_single_monolith``).
#     NB: ``dagster/max_runtime`` is Dagster's run-monitoring tag, enforced by the
#     daemon at LIVE bring-up (DW-C1) — at dryrun it is a structural budget, not a
#     runtime guard. Per-op *runtime* capping is deferred with the bring-up.
#  2. OPERATIVE ISOLATION (schedules): a cold Phase-R overrun cannot abort Phase
#     F/K/N because those run as SEPARATE scheduled jobs (see SCHEDULES) — Phase R
#     (``enrich_pypi_intelligence``) has no schedule and rides only the weekly
#     ``bootstrap_data`` run. That job separation, not the tag, is what guarantees
#     F/K/N are untouched by an R overrun today.
#
# Values are grounded in the atlas-operations.md warm/cold cost notes (Phase R's
# cold 5,000-candidate JSON pull is ~15 min -> its own 1800s; the cheap
# ingest/report nodes are ~30s-5m). Every migrated node appears here explicitly so
# "each op has its own timeout" is true by construction, not by a shared default.
# --------------------------------------------------------------------------- #
NODE_TIMEOUTS: dict[str, int] = {
    # -- core -------------------------------------------------------------- #
    "enumerate_conda_packages": 600,
    "attribute_feedstocks": 300,
    "detect_latest_status": 300,
    "compute_downloads": 600,  # Phase F
    "compute_version_download_history": 600,  # Phase I (rides F fetch)
    "build_dependency_graph": 600,  # Phase J
    "compute_feedstock_health": 300,  # Phase M
    # -- pypi_intelligence ------------------------------------------------- #
    "map_pypi_conda": 300,  # Phase C
    "match_source_urls": 600,  # Phase C.5
    "enumerate_pypi_universe": 900,  # Phase D
    "fetch_pypi_current_versions": 900,  # Phase H
    "snapshot_pypi_serials": 300,  # Phase D serial snapshot
    "fetch_pypi_downloads": 1800,  # Phase P (BigQuery, admin-only)
    "flag_cross_channel": 300,  # Phase Q
    "enrich_pypi_intelligence": 1800,  # Phase R (cold ~15m — its OWN budget)
    "score_pypi_readiness": 600,  # Phase R scoring
    "export_pypi_conda_map": 120,  # update-mapping-cache export shim
    # -- vulnerability ----------------------------------------------------- #
    "refresh_vdb_store": 1200,  # vdb-refresh (~5-10m)
    "refresh_osv_offline_store": 600,  # update-cve-db
    "ingest_cisa_kev": 300,
    "ingest_epss": 300,
    "ingest_cwe_catalog": 300,
    "summarize_vdb_vulns": 300,  # Phase G
    "per_version_vulns": 900,  # Phase G'
    "ingest_basilisk_advisories": 600,  # FR-19
    "fetch_basilisk_details": 600,  # FR-19
    # -- vcs_health -------------------------------------------------------- #
    "enrich_maintainers": 300,  # Phase E
    "detect_archived_feedstocks": 300,  # Phase E.5
    "track_upstream_versions": 900,  # Phase K
    "track_registry_versions": 900,  # Phase L
    "fetch_live_health": 600,  # Phase N
    "derive_release_velocity": 300,  # FR-20
    "classify_migration_readiness": 300,  # FR-21
    # -- universal_sbom ---------------------------------------------------- #
    "normalize_intake_to_cyclonedx": 300,
    "match_against_universe": 900,
    # -- derived_artifacts ------------------------------------------------- #
    "build_universe_sbom": 900,
    # -- seed_gaps (read-only suggesters) ---------------------------------- #
    "report_lts_registry_gap": 120,
    "report_cwe_seed_gap": 120,
    "report_spdx_schema_gap": 120,
    "report_license_map_gap": 120,
}

# Fallback for kedro-dagster's synthetic pipeline-run hook ops (they are cheap
# instrumentation, but still get their OWN budget — never a shared monolith).
HOOK_OP_TIMEOUT = 120
# Any not-explicitly-mapped op (defensive; every real node IS mapped above).
DEFAULT_TIMEOUT = 600

# Default per-op retry policy (AC-3 — retries surface in the UI). Applied per
# NodeInvocation so retries are observable per op, not once for the whole run.
DEFAULT_RETRY = dg.RetryPolicy(max_retries=2, delay=5, backoff=dg.Backoff.EXPONENTIAL)

# Job-level observability tags (AC-3 — phase state observable in the UI).
JOB_TAGS = {"pyforge/orchestrator": "cf_atlas", "pyforge/phase_state": "observable"}

# --------------------------------------------------------------------------- #
# Event-driven sensors (Story G3, FR-6, § 5.9).
#
# Each entry maps an upstream RSS/poll feed to an EXISTING C1 job (AD-23 — the
# sensor yields a RunRequest for that job; it defines NO second execution plane)
# whose datasets are TTL-gated ``IncrementalParquetDataset`` (AD-5 — the sensor
# only TRIGGERS; the incremental re-fetch-only-stale-rows is the dataset's job,
# never a re-fetch-everything). The two feeds chosen are exactly the two upstream
# job surfaces whose catalog entries A3 flipped to the incremental dataset:
#   Phase H (``pypi_version_fetched_at``) and Phase K (``github_version_fetched_at``).
#
# Each: (sensor_name, target_job_name, run_key_prefix, description).
# --------------------------------------------------------------------------- #
UPSTREAM_SENSORS: tuple[tuple[str, str, str, str], ...] = (
    (
        "pypi_release_sensor",
        "phase_h_pypi_versions",
        "pypi",
        "PyPI new-release feed (RSS/poll) → incremental Phase H "
        "(fetch_pypi_current_versions; re-fetch is TTL-gated by the dataset, AD-5).",
    ),
    (
        "vcs_release_sensor",
        "phase_k_vcs_upstream",
        "vcs",
        "VCS upstream-release feed (GitHub/GitLab/Codeberg releases.atom) → "
        "incremental Phase K (track_upstream_versions; TTL-gated re-fetch, AD-5).",
    ),
)

# Sensors ship STOPPED (never auto-start) — mirrors the schedules' no-auto-start
# stance (DW-C1-1). Turning them RUNNING against a live feed is the attended
# daemon bring-up (DW-G3).
SENSOR_DEFAULT_STATUS = dg.DefaultSensorStatus.STOPPED

# --------------------------------------------------------------------------- #
# Wave-H factory layer (Story H4, FR-22(d)/FR-6): the agno wiki crews run on the
# SAME Dagster plane as the data pipeline (AD-6/AD-23 — one execution plane, no
# second scheduler). Crew ASSETS enumerate under one group; a SENSOR fires the
# compile crew on a new raw doc; a weekly SCHEDULE fires the lint crew (§ 7.2).
# The crews write ONLY the wiki tree (AD-22) — never an atlas dataset.
# --------------------------------------------------------------------------- #
# The wiki root is resolved from env (host-agnostic, AD-2), defaulting to a
# ``wiki/`` dir beside the project. The crews are offline; the live wiki lives
# wherever DW-H1 provisions it.
WIKI_ROOT_ENV = "ATLAS_WIKI_ROOT"
WIKI_ASSET_GROUP = "factory_wiki"
WIKI_COMPILE_JOB_NAME = "wiki_compile_job"
WIKI_LINT_JOB_NAME = "wiki_lint_job"
WIKI_RAW_SENSOR_NAME = "wiki_raw_file_sensor"
# Weekly linting cron (§ 7.2: "Weekly Schedule to fire the Linter/QA agents").
WIKI_LINT_CRON = "0 6 * * 1"


def resolve_wiki_root(env: Mapping[str, str] | None = None) -> Path:
    """The wiki root (``ATLAS_WIKI_ROOT`` or ``<project>/wiki``) — env-driven, no host baked in."""
    env_map: Mapping[str, str] = os.environ if env is None else env
    override = (env_map.get(WIKI_ROOT_ENV) or "").strip()
    return Path(override) if override else (PROJECT_PATH / "wiki")


def _wiki_layout() -> WikiLayout:
    # scaffold_wiki is idempotent + non-destructive — ensures the raw/compiled/outputs tree
    # exists so a crew never fails on a missing dir (AD-22: only ever creates under the root).
    return scaffold_wiki(resolve_wiki_root())

# --------------------------------------------------------------------------- #
# Bootstrap profiles (AC-2) — named run configs with the guide's override
# precedence. The profiles set per-phase scoping; the BINDING contract the gate
# checks is the precedence: explicit run-config/env beats profile defaults.
# --------------------------------------------------------------------------- #
PROFILES: dict[str, dict[str, str]] = {
    # recommended default — Phase E + N auto-scoped to the maintainer's own
    # feedstocks; Phase P disabled.
    "maintainer": {
        "scope": "maintainer",
        "phase_e": "auto-scoped",
        "phase_n": "auto-scoped",
        "phase_p": "disabled",
        "read_only": "false",
    },
    # channel-wide; Phase P reachable (credentialed, attended).
    "admin": {
        "scope": "channel-wide",
        "phase_e": "channel-wide",
        "phase_n": "channel-wide",
        "phase_p": "enabled",
        "read_only": "false",
    },
    # air-gapped / read-only; no Phase N, no Phase P, Phase F via S3 parquet.
    "consumer": {
        "scope": "consumer",
        "phase_e": "cached",
        "phase_n": "disabled",
        "phase_p": "disabled",
        "read_only": "true",
    },
}

# env-override prefix for profile keys (explicit env beats profile default).
_PROFILE_ENV_PREFIX = "PYFORGE_ATLAS_"


def resolve_profile_config(
    profile: str,
    *,
    env: Mapping[str, str] | None = None,
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Resolve a bootstrap profile's config with the guide's precedence.

    Precedence (lowest -> highest), matching the ``bootstrap-data --profile``
    override rule in ``guides/atlas-operations.md``:

    1. profile defaults (:data:`PROFILES`);
    2. environment (``PYFORGE_ATLAS_<KEY>``) — explicit env beats the default;
    3. explicit run-config ``overrides`` — beats both.

    Parameters
    ----------
    profile:
        One of ``maintainer`` / ``admin`` / ``consumer``.
    env:
        Environment mapping (defaults to ``os.environ``). A key
        ``PYFORGE_ATLAS_SCOPE`` overrides the ``scope`` profile default, etc.
    overrides:
        Explicit run-config values; highest precedence.

    Returns
    -------
    dict[str, str]
        The resolved config for the profile.
    """
    if profile not in PROFILES:
        raise KeyError(f"unknown profile {profile!r}; expected one of {sorted(PROFILES)}")
    env_map: Mapping[str, str] = os.environ if env is None else env
    resolved = dict(PROFILES[profile])  # layer 1: profile defaults
    for key in list(resolved):  # layer 2: explicit env beats profile default
        env_val = env_map.get(f"{_PROFILE_ENV_PREFIX}{key.upper()}")
        if env_val:
            resolved[key] = env_val
    if overrides:  # layer 3: explicit run-config beats env + profile
        resolved.update(overrides)
    return resolved


# --------------------------------------------------------------------------- #
# Definitions builder.
# --------------------------------------------------------------------------- #


# kedro-dagster synthesizes the pipeline-run hooks as ops named
# ``{before,after}_pipeline_run_hook___default__``. Match on the STABLE prefix,
# not the fragile ``_hook_`` infix — the infix matched only because the
# ``___default__`` pipeline suffix happened to supply a trailing underscore, so a
# hook op emitted without that suffix would silently fall through (Reviewer-B F2).
_HOOK_OP_PREFIXES = ("before_pipeline_run_hook", "after_pipeline_run_hook")


def _is_hook_op(op_name: str) -> bool:
    return op_name.startswith(_HOOK_OP_PREFIXES)


def _timeout_for(op_name: str) -> int:
    if op_name in NODE_TIMEOUTS:
        return NODE_TIMEOUTS[op_name]
    if _is_hook_op(op_name):  # kedro-dagster before/after pipeline-run hook ops
        return HOOK_OP_TIMEOUT
    return DEFAULT_TIMEOUT


def _with_per_op_budgets(graph: dg.GraphDefinition) -> dg.GraphDefinition:
    """Rebuild ``graph`` attaching each op its OWN ``dagster/max_runtime`` tag
    and the default retry policy — per NodeInvocation, so no single monolithic
    timeout wraps the DAG (AC-4). Dependency structure is preserved verbatim."""
    rekeyed: dict[dg.NodeInvocation, object] = {}
    for inv, dep in graph.dependencies.items():
        budget = _timeout_for(inv.name)
        new_inv = dg.NodeInvocation(
            name=inv.name,
            alias=inv.alias,
            tags={**(inv.tags or {}), "dagster/max_runtime": str(budget)},
            hook_defs=inv.hook_defs,
            retry_policy=DEFAULT_RETRY,
        )
        rekeyed[new_inv] = dep
    return dg.GraphDefinition(
        name=graph.name,
        node_defs=graph.node_defs,
        dependencies=rekeyed,
        input_mappings=graph.input_mappings,
        output_mappings=graph.output_mappings,
        config=graph.config_mapping,
    )


def build_upstream_sensor(
    *,
    name: str,
    job: dg.JobDefinition,
    run_key_prefix: str,
    description: str,
    event_source: EventSource = offline_event_source,
) -> dg.SensorDefinition:
    """Build one upstream-event sensor over an EXISTING C1 ``job`` (Story G3).

    The sensor polls ``event_source`` (an RSS/poll feed snapshot — offline no-op
    by default, injectable for the gate), dedupes against the Dagster cursor, and:

    * yields ONE :class:`dagster.RunRequest` for ``job`` when there are new events
      (AD-23 — it triggers the SAME job machinery C1 built; it never defines a
      second execution plane), advancing the cursor;
    * yields a :class:`dagster.SkipReason` when there are no new events, a
      duplicate tick, only malformed payloads, or the source itself raises
      (degrade — a flaky feed must NOT crash the sensor daemon).

    Incrementality is the target job's ``IncrementalParquetDataset`` (AD-5): the
    sensor only triggers; the run re-fetches solely the TTL-stale rows.
    """

    @dg.sensor(
        name=name,
        job=job,
        description=description,
        default_status=SENSOR_DEFAULT_STATUS,
    )
    def _sensor(context: dg.SensorEvaluationContext):
        try:
            raw = list(event_source())
            decision = evaluate_events(raw, context.cursor, run_key_prefix=run_key_prefix)
        except Exception as exc:  # noqa: BLE001 — degrade, never crash the daemon
            yield dg.SkipReason(f"sensor evaluation error: {type(exc).__name__}: {exc}")
            return
        if decision.run:
            context.update_cursor(decision.new_cursor)
            yield dg.RunRequest(
                run_key=decision.run_key,
                tags={
                    "pyforge/trigger": "sensor",
                    "pyforge/event_count": str(len(decision.events)),
                    "pyforge/sensor": name,
                },
            )
        else:
            # Leave the cursor exactly as-is on a skip (nothing advanced).
            yield dg.SkipReason(decision.skip_reason)

    return _sensor


# --------------------------------------------------------------------------- #
# Wave-H crew assets + factory sensor (Story H4).
# --------------------------------------------------------------------------- #


@dg.asset(
    name="compiled_wiki",
    group_name=WIKI_ASSET_GROUP,
    description="Run the Compiler+Linker crew: wiki/raw/*.md -> wiki/compiled/*.md, forwarding "
    "source staleness (AD-13/AD-22). Writes ONLY the wiki tree.",
)
def compiled_wiki_asset(context) -> list[str]:
    result = CompileCrew().run(_wiki_layout())
    context.add_output_metadata(
        {
            "compiled": len(result.compiled),
            "stale_forwarded": len(result.stale_forwarded),
            "failed": len(result.failed),
        }
    )
    return result.compiled


@dg.asset(
    name="wiki_lint_report",
    deps=[compiled_wiki_asset],
    group_name=WIKI_ASSET_GROUP,
    description="Run the Linter/QA crew over wiki/compiled/, reporting violations "
    "(missing-frontmatter / broken-link / laundered-staleness / …). Read-only over the wiki.",
)
def wiki_lint_report_asset(context) -> list[dict]:
    report = LintCrew().run(_wiki_layout())
    context.add_output_metadata({"violations": len(report.violations)})
    return [{"doc": v.doc, "rule": v.rule, "detail": v.detail} for v in report.violations]


WIKI_CREW_ASSETS = [compiled_wiki_asset, wiki_lint_report_asset]

#: A raw-doc lister returns the current ``wiki/raw/`` doc names — the injectable seam for the
#: compile sensor (mirrors G3's ``EventSource``). Default scans the resolved wiki root offline.
RawLister = "Callable[[], Sequence[str]]"  # documented alias (typed loosely to avoid a new import)


def _default_raw_lister() -> tuple[str, ...]:
    return scan_raw_docs(resolve_wiki_root() / "raw")


def build_wiki_compile_sensor(
    *,
    job: dg.JobDefinition,
    raw_lister=_default_raw_lister,
) -> dg.SensorDefinition:
    """Build the new-raw-file sensor that fires the compile crew (Story H4, § 7.2, FR-6).

    Each tick lists the raw docs (via the injectable ``raw_lister`` — offline scan by default),
    dedupes against the Dagster cursor (:func:`evaluate_raw_scan`), and yields ONE
    :class:`dagster.RunRequest` for ``job`` (the compile-asset job — SAME plane, AD-23) when a NEW
    raw doc appeared, advancing the cursor; otherwise a :class:`dagster.SkipReason`. A failing
    lister degrades to a skip (never crashes the daemon). Ships STOPPED — turning it RUNNING against
    the live wiki store is the attended bring-up (DW-H4)."""

    @dg.sensor(
        name=WIKI_RAW_SENSOR_NAME,
        job=job,
        description="New raw wiki doc detected -> run the compile crew (compiled_wiki asset).",
        default_status=SENSOR_DEFAULT_STATUS,
    )
    def _sensor(context: dg.SensorEvaluationContext):
        try:
            current = list(raw_lister())
        except Exception as exc:  # noqa: BLE001 — degrade, never crash the daemon
            yield dg.SkipReason(f"raw-doc lister error: {type(exc).__name__}: {exc}")
            return
        decision: WikiScanDecision = evaluate_raw_scan(current, context.cursor)
        if decision.run:
            context.update_cursor(decision.new_cursor)
            yield dg.RunRequest(
                run_key=decision.run_key,
                tags={
                    "pyforge/trigger": "sensor",
                    "pyforge/sensor": WIKI_RAW_SENSOR_NAME,
                    "pyforge/new_docs": str(len(decision.new_docs)),
                },
            )
        else:
            yield dg.SkipReason(decision.skip_reason)

    return _sensor


def build_definitions(
    env: str = DEFAULT_ENV,
    project_path: Path | None = None,
    event_sources: Mapping[str, EventSource] | None = None,
    wiki_raw_lister=None,
) -> dg.Definitions:
    """Compile the Kedro project into Dagster ``Definitions`` (offline).

    Builds the base job via :class:`~kedro_dagster.KedroProjectTranslator`
    (the single execution plane — ops run through ``KedroSession.run`` via the
    ``kedro_run`` resource), injects per-op timeouts + retry, and derives the
    cadence + bootstrap + Phase-P jobs as op-subsets, each with its own
    schedule (Phase P deliberately gets none — AC-6).

    Story G3 layers on **event-driven sensors** (:data:`UPSTREAM_SENSORS`): each
    targets an existing incremental job by reference (AD-23) and fires a
    ``RunRequest`` on a simulated/real upstream feed event. ``event_sources`` maps
    a sensor name to an injected :data:`EventSource` (defaults to the offline
    no-op — the live feed poller is the deferred daemon bring-up, DW-G3).
    """
    translator = KedroProjectTranslator(
        env=env, project_path=project_path or PROJECT_PATH
    )
    translator.initialize_kedro()
    code_location = translator.to_dagster()

    # The single base job is the translated ``__default__`` (whole migrated DAG);
    # kedro-dagster prefixes it with the env (e.g. ``local____default__``). Select
    # it explicitly rather than by insertion order so an added dagster.yml job can
    # never silently swap the base out from under the cadence derivation.
    base_candidates = [
        job for name, job in code_location.named_jobs.items() if name.endswith("__default__")
    ]
    if len(base_candidates) != 1:
        raise RuntimeError(
            "expected exactly one translated '__default__' base job, got "
            f"{sorted(code_location.named_jobs)}"
        )
    base_job = base_candidates[0]
    resource_defs = dict(base_job.resource_defs)
    executor_def = base_job.executor_def
    budgeted_graph = _with_per_op_budgets(base_job.graph)

    # ops in the migrated DAG (excluding kedro-dagster's synthetic hook ops).
    all_ops = {n.name for n in base_job.graph.nodes}
    node_ops = {n for n in all_ops if not _is_hook_op(n)}

    def _make_job(name: str, op_selection: list[str]) -> dg.JobDefinition:
        return budgeted_graph.to_job(
            name=name,
            op_selection=sorted(op_selection),
            resource_defs=resource_defs,
            executor_def=executor_def,
            tags={**JOB_TAGS, "pyforge/job": name},
        )

    jobs: list[dg.JobDefinition] = []
    schedules: list[dg.ScheduleDefinition] = []

    # weekly bootstrap "everything" — the whole DAG EXCEPT Phase P (AC-6).
    bootstrap_ops = sorted(node_ops - set(PHASE_P_OPS))
    bootstrap_job = _make_job(BOOTSTRAP_JOB_NAME, bootstrap_ops)
    jobs.append(bootstrap_job)
    schedules.append(
        dg.ScheduleDefinition(
            name=f"{BOOTSTRAP_JOB_NAME}_schedule",
            job=bootstrap_job,
            cron_schedule=BOOTSTRAP_CRON,
            execution_timezone="UTC",
            description="Weekly complete refresh of every phase except Phase P (admin-only).",
        )
    )

    # per-cadence phase jobs + schedules.
    for job_name, ops, cron, cadence, phase_label in SCHEDULED_JOBS:
        job = _make_job(job_name, ops)
        jobs.append(job)
        schedules.append(
            dg.ScheduleDefinition(
                name=f"{job_name}_schedule",
                job=job,
                cron_schedule=cron,
                execution_timezone="UTC",
                description=f"{cadence}: {phase_label}",
            )
        )

    # Phase P job — admin-config-only, NO schedule (AC-6).
    jobs.append(_make_job(PHASE_P_JOB_NAME, list(PHASE_P_OPS)))

    # Event-driven sensors (Story G3) — each targets an EXISTING job above by
    # object reference (AD-23: same execution plane; the sensor only triggers).
    # The event source is injectable (``event_sources[name]``); it defaults to the
    # offline no-op (DW-G3 — the live feed poller is the attended daemon bring-up).
    jobs_by_name = {j.name: j for j in jobs}
    sources = event_sources or {}
    sensors: list[dg.SensorDefinition] = []
    for sensor_name, target_job, run_key_prefix, description in UPSTREAM_SENSORS:
        if target_job not in jobs_by_name:
            raise RuntimeError(
                f"sensor {sensor_name!r} targets unknown job {target_job!r}; "
                f"known jobs: {sorted(jobs_by_name)}"
            )
        sensors.append(
            build_upstream_sensor(
                name=sensor_name,
                job=jobs_by_name[target_job],
                run_key_prefix=run_key_prefix,
                description=description,
                event_source=sources.get(sensor_name) or offline_event_source,
            )
        )

    # Wave-H factory layer (Story H4): the crew ASSETS + their asset-jobs, a weekly LINT schedule,
    # and the new-raw-file compile SENSOR — all on this same Dagster plane (AD-6/AD-23).
    wiki_compile_job = dg.define_asset_job(
        WIKI_COMPILE_JOB_NAME, selection=[compiled_wiki_asset]
    )
    wiki_lint_job = dg.define_asset_job(WIKI_LINT_JOB_NAME, selection=[wiki_lint_report_asset])
    schedules.append(
        dg.ScheduleDefinition(
            name="wiki_lint_schedule",
            job=wiki_lint_job,
            cron_schedule=WIKI_LINT_CRON,
            execution_timezone="UTC",
            description="Weekly: fire the Linter/QA crew over the compiled wiki (§ 7.2).",
        )
    )
    sensors.append(
        build_wiki_compile_sensor(
            job=wiki_compile_job,
            raw_lister=wiki_raw_lister or _default_raw_lister,
        )
    )

    return dg.Definitions(
        assets=WIKI_CREW_ASSETS,
        jobs=jobs + [wiki_compile_job, wiki_lint_job],
        schedules=schedules,
        sensors=sensors,
        resources=resource_defs,
    )


# Top-level Dagster object (``dagster dev -m pyforge.atlas.orchestration.definitions``
# / ``dagster definitions validate``). Built at import time — this is the
# offline dryrun surface; NO live execution occurs from building it.
defs = build_definitions()
