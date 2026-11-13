# Proof map — Warden

Companion to `SPEC.md` (CAP-28, FR-45; Story 26.2 of the 2026-11-10 cutover readiness plan), beside `contract.md`.
CHAIN-STANDARD § 2 (operator ruling 2026-11-01) says a success clause names the test that proves it; the second root
rebuilds each capability with this repository's tests as its oracle. This file names, per capability `SPEC.md`
defines, the test modules that fail when its success clause is false, the lane they run in and the command that runs
that lane. A clause no module proves is a row under *Gaps*, with its deferred-work ledger row; it is never a
`SPEC.md` re-word and never a new product test here. When a re-derive writes these commands into `SPEC.md`'s success
clauses (DW-warden-cutover-2026-11-10-11), this file keeps the lanes and the gaps.

The guard is `tests/meta/test_capability_proof_map.py` (live-tree lane). It reads only the table rows under the three
headings below, *Lanes*, *Proof map* and *Gaps*, which must stay exact, and it fails when a capability
`SPEC.md` defines has no row or a row names one `SPEC.md` does not define; when a cited module does not exist; when a
row's lane is not the lane its module runs in, or its command is not that lane's command from *Lanes*; and when a
*Gaps* row names no ledger id, or one with no `### <id>:` row in warden's `deferred-work-ledger.md`.

How to read a row. A cell names test modules and nothing finer: no test function, no clause-by-clause split. A path
starting `tests/` is under `src/shared/packages/pyforge-warden/`; a path starting `src/` is from the repository root.
A capability whose modules run in two lanes takes one row per lane. Every command runs from the repository root.

## Lanes

A module's lane follows from the module itself, in this order: `slow` when its module-level `pytestmark` carries
`slow` (whatever else it carries: the live-tree half is `live_tree and not slow`, Story 27.1); else `live-tree` when it
carries `live_tree`; else `platform` when its path starts `src/platform/`; else `package`.

| lane | what runs there | command |
| --- | --- | --- |
| package | warden's unit, meta and integration modules that read nothing outside the package: the half that passes from an export of the package alone (Story 27.1) | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| live-tree | warden's modules marked `live_tree`: they read this repository outside the package (the planning tree, `.claude/skills`, the root `pixi.toml` and `pixi.lock`, other packages) and fail, never skip, when it is absent | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "live_tree and not slow"` |
| slow | the corpus-oracle task, `-m slow`: the extraction oracle, the corpus determinism proof, the strace egress counter and the real-pixi solver. No workflow runs it (DW-5-2-5, owner steward); `pyforge-warden-test` excludes it | `pixi run --frozen -e pyforge-warden pyforge-warden-test-corpus-oracle` |
| platform | `src/platform/tests`: the portal and golden-path modules for CAP-16, CAP-17, CAP-19..CAP-22 and CAP-29. They run in the platform suite (Platform CI's test job; this command is its local twin), not in warden's job | `pixi run -e pyforge-guild platform-ci-local -- --test` |

## Proof map

| CAP | lane | test modules | command |
| --- | --- | --- | --- |
| CAP-1 | package | `tests/unit/test_verdict.py`, `tests/meta/test_verdict_sole_ownership.py`, `tests/unit/test_smoke.py`, `tests/unit/test_cli_bypass.py`, `tests/integration/test_scan_harness.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-2 | package | `tests/unit/test_discovery_extract_cli.py`, `tests/unit/test_pixi_extractor.py`, `tests/unit/test_environment_yml_extractor.py`, `tests/unit/test_meta_v0_extractor.py`, `tests/unit/test_recipe_v1_extractor.py`, `tests/unit/test_lockfiles_extractor.py`, `tests/unit/test_identity.py`, `tests/meta/test_extract_no_execution.py`, `tests/integration/test_corpus_regression.py`, `tests/integration/test_lockfile_oracle.py`, `tests/integration/test_scan_harness.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-2 | slow | `tests/integration/test_extraction_oracle.py` | `pixi run --frozen -e pyforge-warden pyforge-warden-test-corpus-oracle` |
| CAP-3 | package | `tests/unit/test_discovery_extract_cli.py`, `tests/unit/test_report.py`, `tests/unit/test_inventory.py`, `tests/unit/test_interfaces_and_null_engine.py`, `tests/unit/test_models.py`, `tests/integration/test_scan_harness.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-4 | package | `tests/unit/test_hygiene.py`, `tests/unit/test_vuln.py`, `tests/unit/test_license.py`, `tests/unit/test_currency.py`, `tests/unit/test_verdict.py`, `tests/unit/test_report.py`, `tests/integration/test_axis_producer_ceiling.py`, `tests/integration/test_scan_harness.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-5 | package | `tests/unit/test_config.py`, `tests/unit/test_engine_env_deptry.py`, `tests/unit/test_report.py`, `tests/integration/test_scan_harness.py`, `tests/integration/test_kev_enrichment.py`, `tests/integration/test_epss_enrichment.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-6 | package | `tests/unit/test_waiver.py`, `tests/unit/test_cli_bypass.py`, `tests/integration/test_baseline_grandfathering.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-7 | package | `tests/unit/test_report.py`, `tests/unit/test_sbom.py`, `tests/unit/test_cli_sbom.py`, `tests/integration/test_report_schema.py`, `tests/integration/test_sbom_schema.py`, `tests/integration/test_scan_harness.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-8 | package | `tests/unit/test_models.py`, `tests/unit/test_engine_env_deptry.py`, `tests/unit/test_osv_engine_exit_codes.py`, `tests/unit/test_cli_doctor.py`, `tests/integration/test_doctor.py`, `tests/integration/test_osv_engine.py`, `tests/integration/test_scan_harness.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-9 | package | `tests/unit/test_report.py`, `tests/unit/test_waiver.py`, `tests/integration/test_baseline_grandfathering.py`, `tests/integration/test_scan_harness.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-10 | package | `tests/integration/test_scan_harness.py`, `tests/unit/test_engine_env_deptry.py`, `tests/unit/test_feeds.py`, `tests/integration/test_engine_parallelism.py`, `tests/integration/test_perf_overhead.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-10 | slow | `tests/integration/test_corpus_determinism.py` | `pixi run --frozen -e pyforge-warden pyforge-warden-test-corpus-oracle` |
| CAP-11 | package | `tests/meta/test_socket_deny_alive.py`, `tests/meta/test_subprocess_sole_site.py`, `tests/unit/test_vuln.py`, `tests/unit/test_feeds.py`, `tests/unit/test_currency.py`, `tests/unit/test_refresh_kev_feed.py`, `tests/unit/test_refresh_epss_feed.py`, `tests/unit/test_refresh_endoflife_feed.py`, `tests/integration/test_osv_engine.py`, `tests/integration/test_osv_offline_db_spike.py`, `tests/integration/test_kev_enrichment.py`, `tests/integration/test_epss_enrichment.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-11 | slow | `tests/integration/test_corpus_egress_counter.py` | `pixi run --frozen -e pyforge-warden pyforge-warden-test-corpus-oracle` |
| CAP-12 | package | `tests/unit/test_actuator.py`, `tests/unit/test_actuator_github_client.py`, `tests/integration/test_fix_pr_actuator.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-13 | package | `tests/unit/test_sources.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-14 | package | `tests/unit/test_eligibility.py`, `tests/unit/test_eligibility_rederive.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-15 | package | `tests/unit/test_eligibility_sbom.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-16 | platform | `src/platform/tests/test_warden_fabric_phases.py`, `src/platform/tests/test_warden_fabric_rename.py` | `pixi run -e pyforge-guild platform-ci-local -- --test` |
| CAP-17 | platform | `src/platform/tests/test_warden_fabric_phases.py` | `pixi run -e pyforge-guild platform-ci-local -- --test` |
| CAP-18 | package | `tests/unit/test_lockfiles_extractor.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-18 | live-tree | `tests/integration/test_pixi_lock_environment_scope.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "live_tree and not slow"` |
| CAP-19 | platform | `src/platform/tests/test_golden_path_promotion_closure.py` | `pixi run -e pyforge-guild platform-ci-local -- --test` |
| CAP-20 | platform | `src/platform/tests/test_golden_path_promotion_osv_db.py`, `src/platform/tests/test_golden_path_promotion_verdict.py` | `pixi run -e pyforge-guild platform-ci-local -- --test` |
| CAP-21 | platform | `src/platform/tests/test_golden_path_promotion_verdict.py` | `pixi run -e pyforge-guild platform-ci-local -- --test` |
| CAP-22 | platform | `src/platform/tests/test_deploy_verify_promotion_clean_only.py`, `src/platform/tests/test_deploy_gates_on_promotion_verdict.py` | `pixi run -e pyforge-guild platform-ci-local -- --test` |
| CAP-23 | package | `tests/unit/test_tea_advisory.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-24 | package | `tests/unit/test_fix_target_resolution.py`, `tests/unit/test_fix_solver_seam.py`, `tests/unit/test_manifest_edit.py`, `tests/unit/test_manifest_fixup.py`, `tests/unit/test_manifest_locations.py`, `tests/unit/test_actuator_draft_pr_estate.py`, `tests/unit/test_actuator_require_manifest_fix.py`, `tests/unit/test_cli_fix_target_candidates.py`, `tests/integration/test_fix_pr_actuator.py`, `tests/meta/test_engine_version_range_sync.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-24 | live-tree | `tests/meta/test_pixi_range_floor_matches_workspace.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "live_tree and not slow"` |
| CAP-24 | slow | `tests/integration/test_fix_solver_real_pixi.py` | `pixi run --frozen -e pyforge-warden pyforge-warden-test-corpus-oracle` |
| CAP-25 | package | `tests/unit/test_sast_opengrep.py`, `tests/unit/test_default_warden_without_checkmarx.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-26 | package | `tests/unit/test_fleet_github_rest.py`, `tests/unit/test_fleet_github_graphql.py`, `tests/unit/test_non_python_lockfiles.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-27 | package | `tests/unit/test_hooks.py`, `tests/unit/test_scanner_plugins.py`, `tests/unit/test_default_warden_without_checkmarx.py`, `tests/unit/test_advisory_lenses.py`, `tests/meta/test_pr_gate_plugin_registration.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "not slow and not live_tree"` |
| CAP-28 | live-tree | `tests/meta/test_public_contract.py`, `tests/meta/test_contract_surface.py`, `tests/meta/test_capability_proof_map.py` | `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests -q -m "live_tree and not slow"` |
| CAP-29 | platform | `src/platform/tests/test_warden_fleet_inventory.py`, `src/platform/tests/test_warden_fleet_project_items.py`, `src/platform/tests/test_warden_fleet_run.py`, `src/platform/tests/test_warden_fleet_proposals.py`, `src/platform/tests/test_golden_path_promotion_osv_db.py` | `pixi run -e pyforge-guild platform-ci-local -- --test` |

## Gaps

A clause no module proves, quoted short, and the deferred-work row that carries it. Each row closes when a test that
proves the clause lands and its module joins the capability's row above.

| CAP | clause (quoted short) | deferral |
| --- | --- | --- |
| CAP-16 | "an uploaded pixi.lock returns a job id and completes against the real engines" | `DW-warden-cutover-2026-11-10-12` |
| CAP-17 | "reports match the CLI engines byte-for-byte on the same input" | `DW-warden-cutover-2026-11-10-13` |
