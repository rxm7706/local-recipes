# Oracle map — Steward

Companion to `SPEC.md` (CAP-181, ready 2026-11-10; FR-55). For each capability this Spec defines it names the steward
source modules that realize it, where its proof runs and the test files that prove it, so that someone rebuilding a
capability on a second root can tell which tests judge it, and which capabilities have no package test at all. A
second table names the capabilities of other Specs this package realizes; a third lists any steward test module no
capability claims, with the reason. Bootstrapped on 2026-11-12 from the test modules' docstrings (the Story ids they
cite), the Stories' FR/AD lines in `epics.md`, the provenance the `SPEC.md` headings carry for the absorbed Specs'
ids, and `contract.md` (verb to capability); then checked by hand against the tree.

The guard is `src/shared/packages/pyforge-steward/tests/meta/test_oracle_map.py` (a live-tree test). It judges the map
total and true to the tree, never whether a test is sufficient. It fails when a capability id `SPEC.md` defines has no
row (or two), when a row names a module, path or glob that matches no file of the checkout, when a row's proof values
disagree with the steward test modules it names, or when a steward test module under `tests/unit`, `tests/meta` or
`tests/integration` is named by no row and is not under *Unmapped*.

How to read a row:

- **Capability:** one id, or a contiguous range written `CAP-n..CAP-m` whose capabilities share every other cell. In
  the second table each id is qualified, `spec-<x>:CAP-n`.
- **Source modules:** the modules under `src/shared/packages/pyforge-steward/src/pyforge/steward/` that realize it,
  as paths relative to that directory (`keys.py`, `dashboard/audit.py`), globs allowed; `—` when no steward module
  does (the capability lives in the host, a chart, a recipe, a script or another station). This is the allowed set a
  module's capability citations are held to.
- **Proof:** where the proof runs, one or more of `package` (steward's package half, `pyforge-steward-test`),
  `live-tree` (steward's live-tree half, `pyforge-steward-live-test`), `platform` (`src/platform` tests, Platform
  CI), `other-station` (another station's or the conda-forge-expert skill's suite), `script` (a repo-root test under
  `tests/`, an eval, or a recipe's own test), `attended` (an operator's run: the NKP probes, a live cluster or board,
  a recorded verification), or `none`, alone, with its reason in *Notes*. For the steward test modules a row names,
  the test derives the value from the module: under `tests/integration` it is `attended` (the NKP probes run only in
  `pyforge-steward-nkp-probes`); under `tests/unit` or `tests/meta` it is `live-tree` when the module carries
  `pytestmark = pytest.mark.live_tree` and `package` when it does not. The row's `package` and `live-tree` values must
  equal what its steward modules derive.
- **Tests:** the files or globs that prove it. A path that starts with `unit/`, `meta/` or `integration/` is relative
  to `src/shared/packages/pyforge-steward/tests/`; every other path is relative to the repository root.
- **Notes:** prose, not read by the test, except that a `none` row must carry its reason here.

Keep a `|` out of a table cell. A story that adds a steward test module adds it to a row (or to *Unmapped*) in the
same change.

## Capabilities

| Capability | Source modules | Proof | Tests | Notes |
|---|---|---|---|---|
| CAP-1 | `keys.py`, `cli.py` | package, live-tree | `unit/test_keys_audit_cli.py`, `unit/test_keys_audit_drift.py`, `unit/test_keys_encrypt_decrypt.py`, `unit/test_keys_host_scoping.py`, `unit/test_keys_list.py`, `unit/test_keys_plaintext_secret_scan.py`, `unit/test_keys_revoke.py`, `unit/test_keys_rotate.py`, `unit/test_keys_http_bridge.py`, `meta/test_invariants.py` | The host-gating regression is `test_keys_host_scoping.py`; the never-a-secret and no-rotation-scheduler invariants are in `test_invariants.py`. |
| CAP-2 | — | live-tree | `meta/test_public_contract.py` | Retired 2026-10-15, superseded by CAP-168: Story 102.3 removed `steward deploy dashboard` and `deploy status`; the contract's *Retired verbs* table, held by `test_public_contract.py`, keeps them out of the parser. |
| CAP-3 | `provision.py`, `cli.py` | package | `unit/test_provision_env.py`, `unit/test_provision_list.py`, `unit/test_provision_verify.py`, `unit/test_provision_runner.py` | `test_provision_runner.py` proves the `--runner bmad-loop` wrap is gone (Story 5.1). |
| CAP-4 | `budget.py`, `cli.py` | package, live-tree | `unit/test_budget_set.py`, `unit/test_budget_show.py`, `unit/test_budget_check.py`, `meta/test_invariants.py` | The no-cost-SDK clause is `test_invariants.py`. |
| CAP-5 | `session.py`, `cli.py` | live-tree | `unit/test_session.py`, `meta/test_session_check_entry_points.py`, `meta/test_marp_in_guild_env_story_63_8.py` | The Guild environment itself is `pixi.toml`; its size bound is measured by hand. |
| CAP-6 | `frames.py` | live-tree | `unit/test_frame_preflight.py` | The opt-in `frame-upstream-check` task's own run against the pinned SHAs needs the network and is the operator's. |
| CAP-7 | — | script | `recipes/bmad-eval-quality/recipe.yaml` | The recipe's test asserts `eval-quality --version` equals the recipe version. |
| CAP-8 | — | script, attended | `evals/review-catches-planted-defect/test_driver.py` | A live `--trials N` twin run costs API spend and is the operator's. |
| CAP-9 | `upgrade.py`, `cli.py`, `data/bmad_core_releases/*.yaml` | live-tree | `unit/test_upgrade_preflight.py` | |
| CAP-10 | `upgrade.py`, `cli.py` | live-tree | `unit/test_upgrade_apply.py` | |
| CAP-11 | `upgrade.py`, `cli.py` | live-tree | `unit/test_upgrade_reconcile.py` | |
| CAP-12 | `upgrade.py`, `cli.py` | package | `unit/test_upgrade_pin_fan_out.py` | |
| CAP-13 | `upgrade.py`, `cli.py` | package | `unit/test_upgrade_prove_landed.py` | |
| CAP-14 | `upgrade.py`, `cli.py` | live-tree | `unit/test_upgrade_apply.py`, `unit/test_upgrade_next_rehearsal.py` | |
| CAP-15 | `upgrade.py`, `cli.py`, `data/bmad_core_releases/*.yaml` | live-tree | `unit/test_upgrade_preflight.py`, `unit/test_upgrade_apply.py`, `unit/test_upgrade_next_rehearsal.py` | |
| CAP-16 | `upgrade.py`, `cli.py` | live-tree | `unit/test_upgrade_preflight.py`, `unit/test_upgrade_reconcile.py`, `unit/test_upgrade_next_rehearsal.py` | |
| CAP-17 | `upgrade.py`, `cli.py` | live-tree | `unit/test_upgrade_preflight.py`, `unit/test_upgrade_apply.py` | |
| CAP-18..CAP-20 | `provision.py`, `cli.py` | package | `unit/test_provision_module.py`, `unit/test_provision_list_modules.py` | |
| CAP-21 | `suite.py`, `cli.py` | package | `unit/test_suite_pipeline_truth.py`, `unit/test_suite_fetchers_fail_open.py` | |
| CAP-22 | `suite_advance.py`, `suite.py`, `cli.py` | package | `unit/test_suite_advance.py` | `anaconda upload` stays the operator's step by design. |
| CAP-23 | `provision.py` | live-tree | `unit/test_provision_module_installers.py` | |
| CAP-24 | `upgrade.py` | package | `unit/test_upgrade_native_path_spot_checks.py` | The matrix itself is the companion `install-matrix.md`. |
| CAP-25 | — | other-station | `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` | Doctor's suite-drift surfaces. |
| CAP-26 | — | script, other-station | `recipes/bmad-suite/recipe.yaml`, `tests/packaging/test_bmad_suite_full_feature.py`, `.claude/skills/conda-forge-expert/tests/unit/test_bmad_suite_metapackage_rewrite.py` | Detailed by CAP-40..CAP-43. |
| CAP-27 | `provision.py` | live-tree | `unit/test_provision_install_class_playbook.py` | |
| CAP-28 | `suite.py` | live-tree | `unit/test_suite_wired_class_predicates.py` | |
| CAP-29 | `fresh_clone.py`, `provision.py`, `cli.py` | live-tree | `unit/test_fresh_clone_class_path.py` | |
| CAP-30 | `suite.py`, `provision.py` | live-tree | `meta/test_adoption_register.py` | |
| CAP-31 | `provision.py` | live-tree | `unit/test_provision_module_installers.py` | |
| CAP-32 | — | live-tree | `meta/test_adoption_register.py` | The routing lives in the persona skills and `adoption-register.md`. |
| CAP-33 | — | other-station | `src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py` | The Warden advisory finding and Marshal's review lens. |
| CAP-34 | `suite.py` | live-tree, attended | `unit/test_suite_wired_class_predicates.py` | The studio-root predicate is tested; rendering one station video is the operator's run. |
| CAP-35 | `provision.py`, `cli.py` | package, live-tree | `unit/test_provision_plugin.py`, `meta/test_adoption_register.py` | |
| CAP-36 | — | script, attended | `evals/review-catches-planted-defect/test_driver.py` | The one-trial live citation is the operator's run. |
| CAP-37 | `upgrade.py` | live-tree | `meta/test_release_cadence_runbook.py`, `unit/test_upgrade_next_rehearsal.py` | |
| CAP-38 | `upgrade.py` | live-tree, attended | `unit/test_upgrade_preflight.py` | The readiness checklist is the archived `cutover-readiness.md`; its live pre-flight run is recorded by hand. |
| CAP-39 | `upgrade.py`, `cli.py` | live-tree | `unit/test_upgrade_preflight.py`, `unit/test_upgrade_apply.py` | |
| CAP-40 | `suite.py` | package, other-station | `unit/test_suite_pipeline_truth.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` | The manifest is `recipes/bmad-suite/suite-members.yaml`. |
| CAP-41 | — | script | `recipes/bmad-suite/recipe.yaml` | |
| CAP-42 | — | other-station | `.claude/skills/conda-forge-expert/tests/unit/test_bmad_suite_metapackage_rewrite.py`, `.claude/skills/conda-forge-expert/tests/unit/test_bmad_suite_metapackage_batch.py` | The generator is a conda-forge-expert script. |
| CAP-43 | — | script | `tests/packaging/test_bmad_suite_full_feature.py` | |
| CAP-44..CAP-45 | `measures.py`, `cli.py` | package | `unit/test_measures.py` | |
| CAP-46 | — | other-station | `src/shared/packages/pyforge-core/tests/unit/test_league_measure.py`, `src/shared/packages/pyforge-core/tests/unit/test_league_measure_reads_the_tracked_catalog.py` | The validator lives in pyforge-core. |
| CAP-47 | — | none | — | A declared slot: v1 implements no board. |
| CAP-48 | `bootstrap.py`, `cli.py` | package, live-tree | `unit/test_bootstrap.py`, `unit/test_bootstrap_remedies.py`, `unit/test_bootstrap_setup.py`, `unit/test_bootstrap_setup_flow.py` | |
| CAP-49 | `keys.py` | live-tree, other-station | `unit/test_keys_http_bridge.py`, `.claude/skills/conda-forge-expert/tests/unit/test_http_resolvers.py`, `.claude/skills/conda-forge-expert/tests/unit/test_http_skip_auth.py`, `.claude/skills/conda-forge-expert/tests/unit/test_http_jfrog_host_gate.py` | The chokepoint is the conda-forge-expert `_http.py`. |
| CAP-50 | — | other-station | `.claude/skills/conda-forge-expert/tests/unit/test_atlas_clis_smoke.py`, `.claude/skills/conda-forge-expert/tests/unit/test_detail_cf_atlas.py` | |
| CAP-51 | — | none | — | No test runs a pipeline phase against a mirror; the claim rests on its 2026-09-09 shipped marker. |
| CAP-52 | — | none | — | A recorded document, `vocabulary-map.md`; no test reads it. |
| CAP-53 | `frames.py` | live-tree | `unit/test_frame_preflight.py` | |
| CAP-54 | `track.py`, `cli.py`, `data/track.schema.json` | live-tree | `unit/test_track.py` | |
| CAP-55 | `guards.py`, `cli.py` | live-tree | `unit/test_guards.py` | |
| CAP-56 | — | script | `recipes/nebari-infrastructure-core/recipe.yaml` | A green local build ends the task. |
| CAP-57..CAP-61 | `sync.py`, `cli.py` | package, live-tree, attended | `unit/test_sync_config.py`, `unit/test_sync_duty.py`, `unit/test_sync_reconcile_propagation.py`, `unit/test_sync_retry.py`, `unit/test_sync_github_only_marker.py` | CAP-57's run against a live board and a live Jira project is the operator's. |
| CAP-62 | — | attended | — | A documented bring-up, recorded in `cluster-bringup-facts.md`. |
| CAP-63..CAP-64 | — | platform | `src/platform/tests/test_chart_invariants.py` | |
| CAP-65 | — | attended | — | A dated verification record on the live cluster. |
| CAP-66 | — | script | `src/platform/ingest/github_projects/test_github_metrics_dlt.py` | Run by the `github-metrics-dlt-test` task, not Platform CI's test job, which ignores it. |
| CAP-67..CAP-70 | — | platform, script | `src/platform/tests/test_mcp_host_sidecar.py`, `src/platform/tests/test_atlas_mcp_host.py`, `src/platform/tests/test_chart_invariants.py`, `tests/packaging/test_mcp_era_isolation.py` | |
| CAP-71..CAP-72 | — | script | `tests/scripts/test_mcp_factory_stdio_translator.py` | |
| CAP-73..CAP-75 | — | platform, attended | `src/platform/tests/test_mcp_host_sidecar.py`, `src/platform/tests/test_seven_mcp_faces.py` | CAP-75's deployed proof is an attended cluster run. |
| CAP-76 | `workspace.py`, `cli.py` | package | `unit/test_workspace_repo_set.py` | |
| CAP-77 | `workspace.py`, `cli.py` | package | `unit/test_workspace_repo_set_status_teardown.py` | |
| CAP-78..CAP-80 | — | attended | `.github/workflows/platform-ci.yml` | The `ocp-portability-smoke` job, default off; a dispatch with `PLATFORM_CI_OCP_PORTABILITY_SMOKE=true` runs it. |
| CAP-81 | — | none | — | A Spec amendment: the exception bullet dated 2026-09-11 in the Constraints of `spec-pyforge-unifying-strategy`; no code. |
| CAP-82..CAP-84 | — | platform | `src/platform/tests/test_chart_invariants.py` | |
| CAP-85 | — | platform | `src/platform/tests/policy/test_platform_dev_local_leaf.py` | |
| CAP-86 | — | platform | `src/platform/tests/test_oidc_identity.py` | |
| CAP-87 | — | platform | `src/platform/tests/test_structlog_otel_correlation.py`, `src/platform/tests/test_telemetry_otlp_gate.py` | |
| CAP-88 | — | platform | `src/platform/tests/test_startup_required_settings.py`, `src/platform/tests/test_startup_stage_two.py`, `src/platform/tests/test_startup_locality.py` | |
| CAP-89 | — | platform | `src/platform/tests/policy/test_coverage_policy.py`, `src/platform/tests/policy/test_credential_surface.py`, `src/platform/tests/policy/test_dependency_policy.py`, `src/platform/tests/policy/test_typing_policy.py` | |
| CAP-90 | — | platform, script | `src/platform/tests/policy/test_dependency_policy.py`, `tests/scripts/test_platform_ci_test_requirements_check.py` | |
| CAP-91..CAP-92 | — | script | `tests/packaging/test_platform_image_one_pixi_env.py` | |
| CAP-93 | — | attended | — | A dated Design Note, the archived `pixitainer-eval.md`. |
| CAP-94 | — | none | — | A Spec amendment: the exception bullet dated 2026-09-10 in the Constraints of `spec-pyforge-unifying-strategy`; no code. |
| CAP-95 | — | script | `recipes/silo/recipe.yaml` | |
| CAP-96 | — | attended | — | The `platform-object-storage-up`, `-down` and `-status` tasks; no test runs them. |
| CAP-97 | — | platform | `src/platform/tests/test_object_storage_client.py` | |
| CAP-98 | — | platform | `src/platform/tests/test_health_endpoint.py`, `src/platform/tests/test_asgi_seam.py` | |
| CAP-99 | — | platform | `src/platform/tests/test_langflow_mount.py`, `src/platform/tests/test_langflow_auth_posture.py`, `src/platform/tests/test_isolation_and_statelessness.py` | |
| CAP-100 | — | platform | `src/platform/tests/test_engine_patterns.py`, `src/platform/tests/test_isolation_and_statelessness.py` | |
| CAP-101 | — | platform | `src/platform/tests/test_celery_hardening_and_builds_pool.py` | |
| CAP-102 | — | platform | `src/platform/tests/policy/test_dependency_policy.py` | |
| CAP-103 | — | script | `tests/scripts/test_build_pixi_mirror.py` | |
| CAP-104..CAP-108 | `workspace.py`, `cli.py` | package | `unit/test_workspace.py`, `unit/test_workspace_edges.py`, `unit/test_workspace_clean_delete.py` | |
| CAP-109 | `dashboard/middleware.py`, `dashboard/declarations.py` | package | `unit/test_dashboard_middleware.py`, `unit/test_dashboard_declarations.py` | |
| CAP-110 | `dashboard/declarations.py`, `dashboard/filtering.py`, `dashboard/cache.py` | package | `unit/test_dashboard_filtering.py`, `unit/test_dashboard_cache.py`, `unit/test_dashboard_declarations.py` | |
| CAP-111 | `dashboard/navigation.py`, `dashboard/views.py` | package | `unit/test_dashboard_navigation.py`, `unit/test_dashboard_views.py` | |
| CAP-112 | `dashboard/audit.py`, `dashboard/models.py`, `dashboard/admin.py`, `dashboard/apps.py`, `dashboard/__init__.py`, `dashboard/migrations/0001_initial.py`, `dashboard/migrations/0006_auditaction_purge.py`, `dashboard/migrations/0007_auditentry_scope.py` | package | `unit/test_dashboard_audit.py` | |
| CAP-113 | `dashboard/export.py`, `keys.py` | package | `unit/test_dashboard_export.py` | |
| CAP-114 | `deploy.py`, `cli.py` | package | `unit/test_deploy_perimeter.py` | |
| CAP-115 | `dashboard/filtering.py`, `dashboard/views.py`, `dashboard/navigation.py`, `dashboard/export.py`, `dashboard/cache.py` | package | `unit/test_dashboard_isolation_proof.py` | |
| CAP-116 | `deploy.py`, `cli.py` | package | `unit/test_deploy_static.py` | |
| CAP-117..CAP-121 | `catalog.py`, `cli.py` | live-tree | `unit/test_catalog.py` | CAP-121 is the `skillsctl` slot, declared `off` in config. |
| CAP-122 | — | none | — | Not implemented by this Spec: Hub `later-caps.md` LC-3 keeps it. |
| CAP-123 | `catalog.py`, `frames.py`, `cli.py` | live-tree | `unit/test_catalog.py` | |
| CAP-124 | `provision.py` | live-tree | `unit/test_story_52_1_consume_sidecar.py` | |
| CAP-125..CAP-126 | — | live-tree, platform | `unit/test_story_52_1_consume_sidecar.py`, `src/platform/tests/test_story_52_1_mybmad_sidecar.py` | |
| CAP-127 | `provision.py` | script | `tests/packaging/test_containerfile_base_layer_convention.py` | |
| CAP-128 | — | script | `tests/packaging/test_containerfile_checkout_path.py` | |
| CAP-129 | `keys.py` | script | `tests/scripts/test_container_gates.py` | |
| CAP-130 | — | script | `tests/scripts/test_container_volumes_roundtrip.py` | |
| CAP-131 | `provision.py` | script | `tests/scripts/test_container_cli_smoke.py` | |
| CAP-132 | — | script | `tests/scripts/test_spec_ladder_is_declared.py` | |
| CAP-133 | — | script | `tests/scripts/test_bmad_cross_walk_is_declared.py` | |
| CAP-134 | — | none | — | A vocabulary ruling only; it minted no story and no code. |
| CAP-135 | `deck_integrity.py`, `cli.py` | package | `unit/test_deck_drift_duty.py` | |
| CAP-136 | — | script, other-station | `tests/scripts/test_deferred_work_promote.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` | |
| CAP-137 | `five_tier.py` | script | `tests/scripts/test_commit_msg_hook.py` | |
| CAP-138 | — | other-station | `src/shared/packages/pyforge-doctor/tests/unit/test_sources_atlas.py` | |
| CAP-139 | `corridor.py`, `dashboard/corridor_load.py`, `dashboard/models.py`, `dashboard/migrations/0003_corridorload.py`, `cli.py` | package | `unit/test_corridor.py` | |
| CAP-140 | `passport.py`, `dashboard/passport_mint.py`, `dashboard/passport_sync.py`, `dashboard/models.py`, `dashboard/admin.py`, `dashboard/migrations/0002_workpassport.py`, `dashboard/migrations/0004_workpassport_vendor_id.py`, `cli.py` | package, live-tree | `unit/test_passport_mint.py`, `unit/test_dashboard_admin_and_htmx.py` | |
| CAP-141 | `glass.py`, `dashboard/glass_query.py`, `dashboard/views_htmx.py`, `cli.py` | package | `unit/test_glass.py` | |
| CAP-142 | `corridor.py`, `dashboard/corridor_load.py`, `dashboard/migrations/0005_corridorload_signer_corridorload_slice_name.py` | package | `unit/test_corridor.py` | |
| CAP-143 | `quarantine.py`, `dashboard/quarantine_admit.py`, `dashboard/views_htmx.py`, `dashboard/migrations/0008_quarantineshelfrow.py` | package | `unit/test_quarantine.py` | |
| CAP-144..CAP-145 | — | none | — | Declared slots: v1 runs no live collector and no outbound projection. |
| CAP-146..CAP-149 | `sprint_ledger_query.py`, `data/sprint-ledger-query.schema.json`, `dashboard/views_htmx.py`, `cli.py` | live-tree | `unit/test_sprint_ledger_query.py`, `unit/test_dashboard_admin_and_htmx.py` | |
| CAP-150 | `sprint_ledger_query.py`, `cli.py` | live-tree | `unit/test_sprint_ledger_query.py` | |
| CAP-151 | — | script | `tests/scripts/test_sbom_laptop_gate.py` | The `pyforge-foundry-full` environment itself is `pixi.toml`. |
| CAP-152 | `provision.py`, `upgrade.py`, `suite.py`, `bootstrap.py` | package, live-tree | `meta/test_no_station_assumes_local_recipes.py`, `unit/test_platform_ci_local_concurrency.py`, `unit/test_platform_ci_local_env_sync.py`, `unit/test_platform_ci_local_killed_holder.py` | |
| CAP-153 | — | live-tree, script | `meta/test_lint_types_django_tables.py`, `unit/test_lint_types_not_yet_clean.py`, `unit/test_target_version_check_surfaces.py`, `tests/scripts/test_lint_types_gate.py` | The gate is `scripts/lint_types.py`. |
| CAP-154 | `bootstrap.py`, `cli.py` | live-tree, script | `unit/test_bootstrap_setup.py`, `tests/scripts/test_commit_msg_hook.py`, `tests/scripts/test_lint_types_gate.py` | |
| CAP-155 | `workspace.py` | package | `unit/test_workspace.py` | |
| CAP-156 | `workspace.py` | package, script | `unit/test_workspace.py`, `tests/scripts/test_lint_types_gate.py` | The journal is written by `scripts/pre_push_preflight.sh`. |
| CAP-157 | `workspace.py` | package | `unit/test_workspace.py`, `unit/test_workspace_delete_tier3.py`, `unit/test_workspace_stacked_landing.py` | |
| CAP-158 | `workspace.py`, `cli.py` | package | `unit/test_workspace_full_refs.py`, `unit/test_workspace_stacked_landing.py` | |
| CAP-159 | `preflight.py`, `preflight_ci.py`, `preflight_budget.py`, `preflight_suite_reduction.py`, `preflight_verify.py`, `preflight_xdist.py`, `cli.py` | package, live-tree | `unit/test_preflight.py`, `unit/test_preflight_budget.py`, `unit/test_preflight_concurrency.py`, `unit/test_preflight_docs_site_mutex.py`, `unit/test_preflight_inherited_pytest_addopts.py`, `unit/test_preflight_lane_identity.py`, `unit/test_preflight_scope.py`, `unit/test_preflight_scratch.py`, `unit/test_preflight_selection.py`, `unit/test_preflight_stranded_lane.py`, `unit/test_preflight_suite_reduction.py`, `unit/test_preflight_verify_deferred.py`, `unit/test_preflight_workers.py`, `unit/test_lint_types_mypy_cache.py`, `meta/test_station_tests_trigger_map.py`, `meta/test_preflight_docs_site_lanes.py`, `meta/test_pr_preflight_lanes_resolve_under_pixi.py`, `meta/test_cfe_regression_net_paths.py`, `meta/test_lint_types_mypy_cache_per_environment.py`, `meta/test_workflow_path_filters_match.py` | The fixes under CAP-159 (Epics 88, 90, 98, 104 to 107) prove here too. |
| CAP-160 | `five_tier.py` | live-tree | `meta/test_five_tier_check.py` | |
| CAP-161 | — | live-tree | `meta/test_guild_environment_stations.py` | |
| CAP-162 | `session.py` | live-tree | `unit/test_session.py` | |
| CAP-163 | — | live-tree, platform | `meta/test_object_store_seam_boundaries.py`, `src/platform/tests/test_object_store_seam.py` | The contract lives in `django_pyforge.object_store`. |
| CAP-164 | `keys.py`, `cli.py` | live-tree | `unit/test_keys_ghe_credentials.py` | |
| CAP-165 | `workspace.py` | package, script, other-station | `unit/test_workspace_preserve_tag.py`, `tests/scripts/test_protected_refs_ruleset_check.py`, `tests/scripts/test_pre_shell_hook.py`, `tests/scripts/test_session_denial_forms.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_protected_refs.py` | |
| CAP-166 | `ci.py`, `preflight_ci.py`, `cli.py`, `data/ci-status-schema.json` | live-tree, script | `unit/test_ci_status.py`, `unit/test_ci_pause.py`, `unit/test_preflight_ci.py`, `tests/scripts/test_ci_surface_gates.py`, `tests/scripts/test_ci_pause_twin_banners.py` | |
| CAP-167 | `estate.py`, `estate_realize.py`, `estate_reconcile.py`, `estate_verify.py`, `preflight_ci.py`, `cli.py`, `data/estate-journal-schema.json` | package, live-tree, script | `unit/test_estate.py`, `unit/test_estate_realize.py`, `unit/test_estate_reconcile.py`, `unit/test_estate_verify.py`, `tests/scripts/test_pin_policy_check.py`, `tests/scripts/test_pin_policy_restore.py`, `tests/scripts/test_realization_register_check.py` | |
| CAP-168 | `pages.py`, `pages_duty.py`, `deploy.py`, `cli.py` | package, live-tree | `meta/test_pages_workflow.py`, `unit/test_pages.py`, `unit/test_pages_duty.py`, `unit/test_pages_duty_flag_states.py`, `unit/test_pages_export.py`, `unit/test_pages_export_flag_states.py`, `unit/test_pages_flag_states.py`, `unit/test_pages_release.py`, `unit/test_pages_release_flag_states.py` | |
| CAP-169 | — | none | — | A planning contract: the station Dream and the marketplace brief record it; CAP-170 and CAP-171 carry the code. |
| CAP-170 | — | live-tree | `unit/test_pilot_skills.py` | The pilot skills live under `docs/foundry/marketplace/skills/`. |
| CAP-171 | `marketplace_pages.py`, `catalog.py`, `cli.py` | package, live-tree | `unit/test_marketplace_flag_env.py`, `unit/test_marketplace_listing.py`, `unit/test_marketplace_manifests.py`, `unit/test_marketplace_markdown.py`, `unit/test_marketplace_pages.py` | |
| CAP-172..CAP-173 | — | none | — | Ready, not built: Story 109.4 ships no `bmp` and Story 109.5 automates nothing until the desk test and the pilot pass. |
| CAP-174 | — | platform | `src/platform/tests/test_herald_portal_deck_viewer.py` | The budget is the Platform CI `test` job's own; this browser check must pass there, not skip. |
| CAP-175 | `preflight.py`, `preflight_budget.py`, `preflight_xdist.py`, `ci.py` | package, live-tree | `unit/test_preflight_budget.py`, `unit/test_preflight_critical_path.py`, `unit/test_preflight_workers.py`, `meta/test_pull_request_exempt_surfaces.py`, `meta/test_workflows_have_no_duplicate_keys.py` | |
| CAP-176 | `deploy_nic.py`, `cli.py` | package | `unit/test_deploy_nic.py` | A Hetzner up is attended and operator-gated. |
| CAP-177 | `deploy_nic_packs.py`, `deploy_nic.py`, `cli.py` | package, attended | `unit/test_deploy_nic_packs.py`, `integration/test_nkp_hub_spawn.py`, `integration/test_nkp_landing_cards.py`, `integration/test_nkp_landing_signin.py`, `integration/test_nkp_probes_offline.py` | The probes run in `pyforge-steward-nkp-probes`, attended. |
| CAP-178 | `deploy_nic.py`, `deploy_nic_packs.py`, `cli.py` | package | `unit/test_deploy_nic.py`, `unit/test_deploy_nic_packs.py` | The `gitops/**` ruleset is proven by CAP-165's ruleset check. |
| CAP-179 | `cli.py` | live-tree | `meta/test_public_contract.py` | The contract is the companion `contract.md`. |
| CAP-180 | `restore.py`, `revoke.py`, `cli.py` | package | `unit/test_restore_duty.py`, `unit/test_revoke_duty.py` | |
| CAP-181 | — | live-tree | `meta/test_oracle_map.py` | This companion. |
| CAP-182 | `root_layout.py`, `bootstrap.py`, `catalog.py`, `ci.py`, `corridor.py`, `marketplace_pages.py`, `measures.py`, `preflight_ci.py`, `sync.py`, `upgrade.py` | package | `meta/test_portability.py` | `root_layout.py` names the layout and the repository; the others derive from it. |

## Capabilities of other Specs this package realizes

| Capability | Source modules | Proof | Tests | Notes |
|---|---|---|---|---|
| spec-python-foundry-cutover:CAP-8, spec-python-foundry-cutover:CAP-9, spec-foundry-capability-ledger:CAP-1, spec-foundry-capability-ledger:CAP-2, spec-foundry-regenerate-not-fold:CAP-1 | `cutover.py`, `cutover_ledger.py`, `cutover_ledger_check.py`, `cli.py` | package, live-tree | `unit/test_cutover.py`, `unit/test_cutover_ledger.py`, `unit/test_cutover_ledger_check.py`, `meta/test_capability_ledger_live.py`, `meta/test_cutover_case_list.py` | The `cutover` duty (control-plane Stories 120.5, 121.1, 121.2, 121.6 and 121.7). |
| spec-pyforge-unifying-strategy:CAP-5 | `cli.py`, `interfaces.py`, `__main__.py`, `__init__.py` | package, live-tree | `unit/test_cli.py`, `unit/test_duty_protocol.py`, `meta/test_invariants.py` | One command grammar: the `steward` program, the Duty protocol, and `main()` as the sole owner of the exit code (canopy:AD-7, canopy:AD-8). |
| spec-pyforge-unifying-strategy:CAP-3, spec-pyforge-unifying-strategy:CAP-6 | `provision.py` | package, live-tree, platform | `meta/test_first_portal_slice_provision_list.py`, `meta/test_stations_index_boundaries.py`, `src/platform/tests/test_stations_index.py` | Steward's portal slice and the stations index (Stories 33.2 and 91.1). |
| spec-pyforge-unifying-strategy:CAP-8 | `dashboard/consumers.py`, `dashboard/routing.py`, `dashboard/asgi.py` | live-tree, platform | `unit/test_events_stream_consumer.py`, `src/platform/tests/test_ws_events.py` | The events stream (Story 48.6). |
| spec-pyforge-unifying-strategy:CAP-15, spec-pyforge-unifying-strategy:CAP-16 | `five_tier.py` | live-tree | `meta/test_five_tier_check.py`, `meta/test_skf_domain_skills.py`, `meta/test_skf_steward_skill.py`, `meta/test_station_persona.py`, `meta/test_steward_persona.py` | Domain skills, personas and the five-tier check (canopy:FR-37, canopy:FR-38, canopy:FR-39). |
| spec-pyforge-unifying-strategy:CAP-18 | `deploy_profiles.py` | live-tree | `unit/test_deploy_profile_plugins.py` | Deploy-profile adapters as plugins (Story 32.2, canopy:FR-45). |
| spec-feature-flag-governance:CAP-5 | `sprint_ledger_query.py` | package | `meta/test_steward_single_flag_tree.py` | Steward reads flags from the one tree (Story 76.3, canopy:AD-11). |
| spec-feature-flag-governance:CAP-7 | `cli.py` | package | `unit/test_retrofit_flags.py` | The retrofit kill switches (Epic 114). |

## Unmapped

Every steward test module under `tests/unit`, `tests/meta` and `tests/integration` is named by a row above. A module
no capability claims is listed here, one row each, with the reason:

| Test module | Reason |
|---|---|
