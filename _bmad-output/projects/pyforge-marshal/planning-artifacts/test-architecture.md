---
title: "Test Architecture — pyforge-marshal"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: marshal
source_fingerprint: 01e91fcb9f255b41
story_count: 436
test_file_count: 240
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Marshal

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-marshal`
- **Stories parsed:** 436
- **Epics parsed:** 85
- **Test files inventoried:** 240 under `src/shared/packages/pyforge-marshal/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `01e91fcb9f255b41`

## Risk Assessment

### High-risk epics

- Epic 2: Gates you can run
- Epic 20: The loop cannot lose work, and a landing is always recognizable
- Epic 50: The landing self-drives — what the first autonomous drain still needed a human for (spec-pyforge-marshal CAP-244..248)
- Epic 51: The landing self-drives, second round — what the second autonomous drain still needed a human for (spec-pyforge-marshal CAP-249..256)

### Medium-risk epics

- Epic 1: Provisioned, verified loop homes
- Epic 3: Supervised unattended runs
- Epic 4: Landing with a durable paper trail
- Epic 5: Fleet visibility
- Epic 6: Portability proven
- Epic 7: Foundation & the Write Guard
- Epic 8: The Managed-Region Engine
- Epic 9: Detect & Plan
- Epic 10: Materialize & the Core Verbs
- Epic 12: Packaging, Oracle & Hardening
- Epic 13: Surface drift reconciliation — a gate that can be cleared, a signal that can be trusted
- Epic 14: The shared floor — pyforge-core
- Epic 15: Fleet operations run themselves
- Epic 16: The board derives truth
- Epic 17: Instruments verified, chains regenerable
- Epic 18: The governed tool surface
- Epic 19: The testing charter, enforced
- Epic 21: The planning chain regenerates itself, and audits whether it's coherent
- Epic 22: Single-story dispatch is a marshal verb, not a session's discipline
- Epic 23: Velocity captures hand-driven work
- Epic 26: Loop/runner hook spec
- Epic 27: Marshal owns its skill, persona, and one portal job
- Epic 29: A harness halt of `done` ends the session, not the review
- Epic 31: TEA replaces the generator, and marshal's own estate is cutover-ready
- Epic 33: Token economy in effect
- Epic 34: Launch-environment integrity — no silent-success failure and no orphaned worktree
- Epic 35: The templated merge-subject shape never masquerades as a same-numbered story from another project
- Epic 37: The chain audited against the code (spec-artifact-chain-reconciliation CAP-1..8)
- Epic 39: `marshal status` recovers from a poisoned harness run id (spec-marshal-status-harness-run-id-poisoning CAP-1..2)
- Epic 40: The genesis-installer name retires completely (spec-genesis-installer-name-retirement CAP-1..8)
- Epic 41: Every planning tree tells the truth about itself (spec-bmad-output-hygiene CAP-1..12)
- Epic 42: spec-surface tolerates governed overlap (spec-surface-overlap-tolerance CAP-1..2)
- Epic 43: The citation detector shows everything it knows (spec-fleet-consistency-standard CAP-6, fix)
- Epic 44: The operator stops re-pasting the status prompt — marshal watches its own runs (spec-marshal-run-watch CAP-1..5)
- Epic 45: BMAD from inside Cursor's own chat (spec-bmad-cursor-interactive-routing CAP-2..4)
- Epic 47: The review bot remembers the correction you gave two weeks ago (spec-marshal-recall-in-the-loop CAP-1..4)
- Epic 52: The shared floor is enforced where the build happens (spec-pyforge-core CAP-8..9)
- Epic 53: The dispatch landing pays its own surface tax (spec-pyforge-marshal CAP-261)
- Epic 54: The hand ledger sync repairs its own feed drift (spec-pyforge-marshal CAP-265)
- Epic 55: Wire and structure-graph roll out fleet-wide, finishing 28.32's deferred scope (token-economy CAP-3)
- Epic 56: A landing refusal outlives the landing — status reports it superseded (spec-pyforge-marshal CAP-266)
- Epic 57: A loop-home refresh does not pay a preflight for `main`'s own commits (spec-pyforge-marshal CAP-267)
- Epic 58: The landing heal sees the conflicts it was built to heal (spec-pyforge-marshal CAP-268)
- Epic 59: The ledger union heal merges the base, so the merge it retries is clean (spec-pyforge-marshal CAP-269)
- Epic 60: Marshal names the remote's branch, never a name something local can wear (spec-pyforge-marshal CAP-270)
- Epic 61: Marshal names its own branches too, never a name a tag can wear (spec-pyforge-marshal CAP-271)
- Epic 62: The shared test kit's branch guards diff against the remote (spec-pyforge-marshal CAP-272)
- Epic 63: The station-tests lane picks suites from the remote-tracking ref (spec-pyforge-core CAP-10)
- Epic 64: A dispatch carries its own scope, never the shared marker (spec-pyforge-marshal CAP-273)
- Epic 65: A drain can be asked what it would dispatch before it launches anything (spec-pyforge-marshal CAP-274)
- Epic 66: A follow-up review a landing recommends is carried, never dropped (spec-pyforge-marshal CAP-275)
- Epic 67: A landed dispatch reads completed whatever state the primary checkout is in (spec-pyforge-marshal CAP-276)
- Epic 68: A landing's ledger promotion reaches origin/main, and a failed one is never silent (spec-pyforge-marshal CAP-277)
- Epic 70: Seed check judges the paths the manifest means (spec-pyforge-marshal CAP-279)
- Epic 71: The front door names the environment a roster station runs in (spec-pyforge-core CAP-11)
- Epic 72: The dispatch supervisor judges merge facts from origin/main (spec-pyforge-marshal CAP-280)
- Epic 73: A drain runs the follow-up review a landed story recommended (spec-pyforge-marshal CAP-281)
- Epic 74: Every capability ships behind a flag — the fixture, the dispatch refusal and the mandate (spec-feature-flag-governance CAP-4, CAP-3, CAP-6)
- Epic 75: The console keeps archived Dreams and their Spec owners when Dreams move to the archive (spec-one-chain-per-station CAP-11)
- Epic 76: The drift script's legacy --specs report retires with its tier (spec-one-chain-per-station CAP-11)
- Epic 77: Every dispatch session opens on the shared codegraph index (spec-pyforge-marshal CAP-282)
- Epic 78: A landing unions append-only memlogs instead of refusing (spec-pyforge-marshal CAP-283)
- Epic 79: A landing leaves nothing for the operator to finish (spec-pyforge-marshal CAP-229, CAP-277, CAP-261 (a))
- Epic 80: A dispatch landing waits for its PR's checks (spec-pyforge-marshal CAP-284)
- Epic 81: A drain says why it dispatched nothing, and reads a park only where one is written
- Epic 82: Phase 2 of the deferral burn-down: marshal's critical and high deferrals
- Epic 83: Phase 2 landing defects: dispatch liveness, whole-tree checks, the landing heal and campaign holds
- Epic 84: Every harness's model list refreshes from its own live source (spec-pyforge-marshal CAP-285)
- Epic 85: A verification refusal goes back to the session that wrote the change (spec-pyforge-marshal CAP-286)
- Epic 87: Preserved work is a protected tag, and no cleanup destroys it (spec-pyforge-marshal CAP-287)

### Low-risk epics

- Epic 11: Derive, Migrate & Update
- Epic 24: Liveness is one command
- Epic 25: Aligned to the installed BMAD era
- Epic 28: Token economy — the loop reads less, says less, and re-learns nothing
- Epic 30: Aligned to BMAD 6.12 — the second era round
- Epic 32: The operating model matches its own instruments
- Epic 36: The library catalog can't see a station's own build manifest
- Epic 38: bmad-loop cannot dispatch a story whose dependency is still ahead of it (spec-bmad-loop-forward-dependency-blindness CAP-1..4)
- Epic 46: The session path — one substrate, silent saves, every harness (spec-marshal-token-economy CAP-19..24)
- Epic 69: The switch script runs where it is documented to run (spec-pyforge-marshal CAP-278)
- Epic 86: Phase 3 of the deferral burn-down: marshal's ruled fixes

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-marshal/tests/integration/test_cli_contract.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_dispatch_structure_graph_real.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_idempotence_harness.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_init_worktree.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_local_recipes_empty_plan.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_login_pkce_live_keycloak.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_performance_gates.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_seed_egress_counter.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_27_2_portal_loop_homes.py` | meta | 27.2 |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad11_write_boundary.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad19_no_adapter_branch.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad23_inline_key_format_guard.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad26_seed_field_access_guard.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad31_conformance_check_can_genuinely_fail.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad34_egress_registry_completeness.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad36_projection_mechanism_table.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad39_envelope_consistency.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad3_ad4_import_linter.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad51_no_typer_rich.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad65_default_template_never_remote.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad65_lean_env_conda_forge.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad65_no_network_stack_imports.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad7_verdict_sole_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_ad9_supervisor_no_control_channel.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_cap8_compression_ladder_seam.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_commit_text_is_redacted_at_every_call_site.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_derived_context_skill_contract.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_dispatch_supervisor_main_coverage_floor.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_engine_version_range_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_finding_remedy_reference_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_attention_dispatch_refused.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_landing_findings.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_missing_spec.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_fleet_picture_stranded_work.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_followup_review_carried.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_gate_record_write_path.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_kit_artifacts_ignored_not_the_tracked_skills.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_local_branch_refs_are_full_refnames.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_manifest_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_no_engine_or_scribe_internals_import.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_no_loop_home_run_state_read.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_p01_write_primitives_only_in_fs.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_p02_copier_sole_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_p03_detect_is_pure.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_p07_no_hash_comparison_in_apply.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_planning_graph_skill_contract.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_probe_json_contract.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_publisher_single_importer.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_regions_no_manifest_import.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_remote_refs_are_full_refnames.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_rendered_policy_untracked.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_sc08_never_write_update_proof.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_seed_layer_import_rules.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_seed_no_bare_exception.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_skf_domain_skill.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_skill_projection_manifest_untracked.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_spec_surface_stamp.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_station_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_supervisor_run_path_agreement.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_drift.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_generator.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_tool_surface_coverage.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_wire_store_ignored_not_the_seed_namespace.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_adapters_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_bmad_loop_status_vocabulary.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_chain_regen.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_check.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_checkpoint_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_cli_benchmark.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_cli_context.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_cli_context_bootstrap.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_cli_context_retrieve.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_clock_system.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_conformance.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_conformance_schema.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_context.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_context_bundle.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_cursor_launch_config.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_deferred_work.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_deploy_renderers.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_derived_context.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_cfe_commit.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_completion.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_flag_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_harness_done.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_hotfix.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_heal.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_output_layer.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_prelaunch.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_push.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_re_preflight.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_retry.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_retry_83_10.py` | unit | 83.10 |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_ruff_format.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_station_guard.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_stop_retry.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_structure_graph.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_blocked_halt.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_finalize.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_main_loop.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_spec_block.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_state.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_verify_fix.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_survival.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_commands.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_fix.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verify_merge_tree.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_wave_status.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_drain_plan.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_durability.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_egress.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_fold.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_forge_gh.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_fs_local.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_gate_record.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadbuild.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_engine_liveness.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_preflight.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_probe.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_run_status_snapshot.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_run_terminal_verdict.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_smoke.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_spin.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_stop_resume.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_usage_snapshot.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_wire.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_profile.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_identity.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_index_freshness.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_init.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_intent_gap_preserve.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_journal.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_land.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_land_epic_rollups.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_landing.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_landing_checks.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_landing_evidence_conformance.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_layer_savings_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_local_branch_refs.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_login.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_loop_runner_hook.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_mcp_registration.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_mcp_tools.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_model.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_model_cost.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_model_list_cli_transport.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_model_list_http.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_model_list_live_adapter.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_model_list_refresh.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_notify_file_desktop.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_observer_mux.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_oidc_pkce.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_pkce.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_planning_graph.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_policy.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_published_plane.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_publisher.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_refresh.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_refs.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_repo_root.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_retire.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_savings_telemetry.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_scope.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_scribe_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_apply_run.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_adopt.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_check.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_init.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_cli_seed_update.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_derive_adapters.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_derive_projects_index.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_findings.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_hashes.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_inventory.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_optout.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_referenced_deps.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_engine_copier.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_errors.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_fs.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_integration_adopt_prd_j2.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_kit.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_migrate_registry.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_model_artifact.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_model_manifest.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_model_version.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_plan_build.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_plan_types.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_apply.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_markers.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_regions_parse.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_scaffold.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_state_store.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_adopt.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_check.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_explain.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_init.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_preconditions.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_region_opt_out.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_skips.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_update.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_version.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_skill_projection.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spec_binding.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spec_deps.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spec_difficulty.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spec_low_risk.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spec_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_status_landing_superseded.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_structure_graph_dispatch_benchmark.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_substrate.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_substrate_store.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_supervise.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_supervisor.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_testing_kit_reexport.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_tier_routing.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_token_economy_benchmark.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_upstream.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_upstream_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_verdict.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_verify_scope.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_watch.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_wave_scheduler.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_worktree_checkpoint.py` | unit | none observed |

## Story Coverage Matrix

| Story | Title | Linked test files |
|-------|-------|-------------------|
| 1.1 | Package spine, verdict lattice, findings registry, and the meta-tests that en... | none observed |
| 1.2 | Story identity, merge-subject rendering, and feed completeness | none observed |
| 1.3 | Layered policy composition with provenance and validation | none observed |
| 1.4 | Provision a loop home | none observed |
| 1.5 | Single-sourced Tier-3 store via backlink | none observed |
| 1.6 | Isolation verification and home enumeration | none observed |
| 1.7 | Preflight, adapter config seeding, and first-run acknowledgement | none observed |
| 1.8 | Teardown that refuses to destroy work | none observed |
| 1.9 | Packaging, distribution, and version reporting | none observed |
| 1.10 | Render the harness policy from the canonical EffectivePolicy | none observed |
| 1.11 | A loop agent cannot mutate repo-wide git state *(added 2026-08-09 — FR-178)* | none observed |
| 1.12 | A stale loop home cannot be spun *(added 2026-08-09 — FR-180)* | none observed |
| 2.1 | Standalone verify-command runner, project-scoped | none observed |
| 2.2 | Verdict aggregation that never false-greens | none observed |
| 2.3 | Frozen-surface scope check, narrowing only | none observed |
| 2.4 | Doc-only story classification | none observed |
| 2.5 | Gate mode ladder with autonomy labels | none observed |
| 2.6 | Gate evidence record with redaction at egress | none observed |
| 2.7 | A gate binds to the spec's Success signal *(added 2026-08-01 — FR-64 / AD-49)* | none observed |
| 2.8 | A low-risk story's review runs lighter, never absent *(added 2026-08-11 — FR-... | none observed |
| 3.1 | Run identity and the journal writer | none observed |
| 3.2 | The journal fold — one producer for accumulating run state | none observed |
| 3.3 | Detached launch with scoped story selection | none observed |
| 3.4 | Supervisor process lifecycle | none observed |
| 3.5 | Idle-strand detection | none observed |
| 3.6 | Budget ceilings and the heaviest-story advisory | none observed |
| 3.7 | Escalation, deferral, and resume | none observed |
| 3.8 | Stage-bound durability, and fleet-launch wiring *(added 2026-08-01 — FR-61 / ... | none observed |
| 3.9 | A retired story branch is not a push failure | none observed |
| 3.10 | Unpushed work is measured by tip, never by name | none observed |
| 3.11 | A story's declared difficulty actually picks its model *(added 2026-08-11 — F... | none observed |
| 3.12 | A struggling retry runs under a stronger model *(added 2026-08-11 — FR-183)* | none observed |
| 3.13 | The parallel-fan-out clamp is surfaced, not silent *(added 2026-08-11 — FR-184)* | none observed |
| 4.1 | Story-spec promotion with a durability predicate | none observed |
| 4.2 | Teardown reachability and spec-recovery assistance | none observed |
| 4.3 | Merge-subject conformance and review-cap landing | none observed |
| 4.4 | Batch pull request with hygiene preflight | none observed |
| 4.5 | Feed refresh with truth partitioned by domain | none observed |
| 4.6 | Deploy idempotence and reconciliation of open intents | none observed |
| 4.7 | Landing rules as declared policy *(added 2026-08-01 — FR-59 / CAP-9)* | none observed |
| 4.8 | `marshal land` — the last mile lands itself *(added 2026-08-01 — FR-60 / CAP-9)* | none observed |
| 4.9 | Derived surfaces regenerate on main; the shared store takes a lock *(added 20... | none observed |
| 4.10 | Fleet-wide branch retirement *(added 2026-08-01 — FR-63 / AD-47)* | none observed |
| 4.11 | `marshal land` refuses while a run is in flight *(added 2026-08-09 — FR-172)* | none observed |
| 4.12 | A landing leaves the loop home current with `main` *(added 2026-08-09 — FR-173)* | none observed |
| 4.13 | The loop's deferred work reaches the tracked ledger *(added 2026-08-09 — FR-1... | none observed |
| 4.14 | The failed-story safety net is reported *(added 2026-08-09 — FR-176)* | none observed |
| 4.15 | One pusher, not two *(added 2026-08-09 — FR-177)* | none observed |
| 5.1 | Fleet view | none observed |
| 5.2 | Per-run detail | none observed |
| 5.3 | Escalation queue | none observed |
| 5.4 | Ledger-vs-git reconciliation and the versioned status contract | none observed |
| 5.5 | Durability as a reported fleet-status dimension *(added 2026-08-01 — FR-62 / ... | none observed |
| 5.6 | `marshal check` — the detector registry through the front door *(added 2026-0... | none observed |
| 5.7 | The board answers "how much is left" *(added 2026-08-09 — FR-179)* | none observed |
| 5.8 | A dead supervisor sidecar doesn't hide a live engine *(added 2026-08-11 — FR-... | none observed |
| 5.9 | A story finished by hand isn't invisible to the ledger *(added 2026-08-11 — F... | none observed |
| 5.10 | `marshal land` renders a detectable merge subject *(added 2026-08-12 — FR-187... | none observed |
| 5.11 | A harness-native terminal run reads as finished, not `unknown` *(added 2026-0... | none observed |
| 6.1 | Profile-driven adapter selection, project-scoped | none observed |
| 6.2 | Skill-tree projection | none observed |
| 6.3 | Projection drift detection that can actually fail | none observed |
| 6.4 | Adapter probe with a machine-scoped record | none observed |
| 6.5 | Conformance smoke in an ephemeral home | none observed |
| 6.6 | The conformance matrix | none observed |
| 6.7 | Entry-file family drift check, detect-only | none observed |
| 6.8 | Upstream contribution register | none observed |
| 6.9 | Tool-surface rendering and preflight probe *(added 2026-08-01 — AD-43 / the Q... | none observed |
| 7.1 | The seed module tree inside pyforge-marshal | none observed |
| 7.2 | Error taxonomy and exit codes | none observed |
| 7.3 | The `fs` write primitive and the never-write guard | none observed |
| 7.4 | Manifest schema, loader, and model-version ranges | none observed |
| 7.5 | The V1 extraction manifest (the model, as data) | none observed |
| 7.6 | Spike-0 — Copier API fit (CRITICAL GATE) | none observed |
| 8.1 | Marker grammar and the per-format registry | none observed |
| 8.2 | Region parser — span discovery, nesting rejection, fence awareness | none observed |
| 8.3 | Span substitution — the update primitive | none observed |
| 8.4 | Anchor resolution and region insertion | none observed |
| 8.5 | Marker deletion as a sanctioned opt-out | none observed |
| 9.1 | Findings model — severity, types, remedies | none observed |
| 9.2 | Repo inventory walker and artifact classification | none observed |
| 9.3 | Content hashing for managed files and regions | none observed |
| 9.4 | Legacy convention detection | none observed |
| 9.5 | Manifest coverage check | none observed |
| 9.6 | Plan and Action types, repo fingerprint, and the plan builder | none observed |
| 10.1 | Copier engine wrapper — the single seam | none observed |
| 10.2 | State schema and the atomic store | none observed |
| 10.3 | The apply runner — transactional, guarded | none observed |
| 10.4 | Preconditions, refusals, and skips | none observed |
| 10.5 | `marshal seed check` | none observed |
| 10.6 | `marshal seed adopt` | none observed |
| 10.7 | `marshal seed init` | none observed |
| 10.8 | Manifest-declared writable artifacts are exempt from their own never-write co... | none observed |
| 11.1 | Neutral contract and agent-adapter fan-out | none observed |
| 11.2 | `PROJECTS.md` index and artifact-symlink derivation | none observed |
| 11.3 | Migration registry and runner | none observed |
| 11.4 | `marshal seed update` — two-phase | none observed |
| 11.5 | Referenced-dependency verification and Doctor delegation | none observed |
| 11.6 | `marshal seed explain` and `marshal seed version` | none observed |
| 12.1 | Full pixi wiring, distribution, and repo-gate compliance | none observed |
| 12.2 | The `local-recipes` empty-plan oracle (CRITICAL) | none observed |
| 12.3 | Offline operation and the egress counter | none observed |
| 12.4 | Pattern meta-tests and the never-write proof | none observed |
| 12.5 | CLI contract, idempotence harness, and performance gates | none observed |
| 12.6 | README, adoption guide, and the finding→remedy reference | none observed |
| 13.1 | A baseline can be stamped for one spec | none observed |
| 13.2 | A moved contract reconciles only the paths it names | none observed |
| 13.3 | The no-baseline, ungoverned and stale-allowlist findings are cleared | none observed |
| 13.4 | The 34 drift findings are reconciled or recorded | none observed |
| 13.5 | A Spec cannot declare a surface it has no contract for | none observed |
| 13.6 | The presumed set is worked down by measurement | none observed |
| 13.7 | The producer reconciles the surface it drifts *(added 2026-08-09 — FR-174)* | none observed |
| 14.1 | The leaf exists and is provably a leaf | none observed |
| 14.2 | Atomic write has one implementation | none observed |
| 14.3 | One lattice, one envelope, one exception root | none observed |
| 14.4 | The subprocess seam is reconciled and sole ownership is gated | none observed |
| 15.1 | One command refreshes the fleet's homes | none observed |
| 15.2 | Landing promotes the ledger, and staleness is its own check | none observed |
| 16.1 | One resolver, derived sources, loud failures | none observed |
| 17.1 | The detectors' remaining blind spots are fixture-pinned, with an incident log | none observed |
| 17.2 | The dreams hygiene mode exists | none observed |
| 17.3 | Chain-completeness audit mode reports layers | none observed |
| 17.4 | Orchestrated regeneration that cannot lose code status | none observed |
| 18.1 | Marshal's capabilities become named, typed tools | none observed |
| 18.2 | Parity and coverage are gated numbers | none observed |
| 19.1 | One generator produces every station's test architecture | none observed |
| 19.2 | The shared test-support kit | none observed |
| 19.3 | Coverage gates that name the module | none observed |
| 19.4 | Test architecture stays current as stories land | none observed |
| 19.5 | The testing kit's own suite runs in CI | none observed |
| 20.1 | Baseline-drift detector at the seam | none observed |
| 20.2 | Baseline-drift defers get loud | none observed |
| 20.3 | The gated upstream filing | none observed |
| 20.4 | Intent-gap attempts are preserved | none observed |
| 20.5 | Missing-preserve detector | none observed |
| 20.6 | The verify_scope primitive | none observed |
| 20.7 | Both guards hard-fail on drift | none observed |
| 20.8 | The landing-evidence grammar | none observed |
| 20.9 | Doctor consumes the grammar | none observed |
| 20.10 | Marshal consumes the grammar | none observed |
| 20.11 | Doctor's own adoption gap closes — the branch-name fallback and a loose last ... | none observed |
| 20.12 | fleet-picture names a stale primary checkout, not just stale loop homes | none observed |
| 21.1 | Chain-completeness audit mode extends layer-presence into full CAP-3 coverage | none observed |
| 21.2 | Orchestrated chain regeneration | none observed |
| 21.3 | Code-status preservation | none observed |
| 21.4 | Orphan detection with review-gated cleanup | none observed |
| 21.5 | Configurable per-project invocation | none observed |
| 22.1 | The dispatch verb launches one governed, isolated story session | none observed |
| 22.2 | Completion is judged from git and process facts, and a zombie is never redisp... | none observed |
| 22.3 | Verification is the product — no landing on a self-report | none observed |
| 22.4 | A verified story lands through the existing machinery, classified marshal-native | none observed |
| 22.5 | One story in flight per station; stations in parallel; overlap is loud | none observed |
| 22.6 | The dispatched run survives its operator, and its journal carries the timing ... | none observed |
| 22.7 | Fleet-wide drain is a marshal-orchestrated mode | none observed |
| 22.8 | The session harness is profile-driven across agent CLIs | none observed |
| 22.9 | A dispatch branch names its station | none observed |
| 22.10 | `branch_merged` requires real divergence, not just ancestry | none observed |
| 22.11 | Station-scoped drain and an explicit story sequence | none observed |
| 22.12 | A shared-surface diff also clears its own full suite, not just the station's ... | none observed |
| 22.13 | A landing sets the story's epics status to match the ledger | none observed |
| 22.14 | The cross-surface gate runs each touched surface's own check | none observed |
| 22.15 | A landing matches the epics status even when the spec is already done | none observed |
| 22.16 | A launch without the env on PATH never wastes a finished session | none observed |
| 22.17 | A land-only refusal names the gate that refused it | none observed |
| 22.18 | A landing heals a spec-surface baseline conflict by re-stamping on main's bas... | none observed |
| 22.19 | A landing unions the flag registry when two flag stories land in turn | none observed |
| 23.1 | Wall-clock fallback derivation from promoted-spec revision fields | none observed |
| 23.2 | Wall-clock is never blended with active-compute | none observed |
| 23.3 | The coverage caption partitions by true reason | none observed |
| 24.1 | Marshal gains the missing liveness primitive | none observed |
| 24.2 | The operator answer is one documented command | none observed |
| 24.3 | An UNSUPERVISED row has a cheap, documented double-check | none observed |
| 25.1 | Retired skill IDs are purged and guarded | none observed |
| 25.2 | bmad-loop's repo skills match the installed package | none observed |
| 25.3 | Every spec folder accepts a 6.11 bmad-spec update | none observed |
| 25.4 | The 0.10/0.11 policy knobs are governable | none observed |
| 25.5 | Marshal speaks the 0.11 status vocabulary | none observed |
| 25.6 | A hand-driven run's deferrals reach the ledger unaided | none observed |
| 25.7 | The factory's living docs are re-grounded, with a named owner | none observed |
| 26.1 | Extract the loop/runner hook | none observed |
| 27.1 | SKF domain skill and BMAD persona for marshal | none observed |
| 27.2 | First portal slice — list loop homes | `src/shared/packages/pyforge-marshal/tests/meta/test_27_2_portal_loop_homes.py` |
| 28.1 | The context policy block, rendered once for both engines | none observed |
| 28.2 | Wire compression at the harness seam | none observed |
| 28.3 | Genesis seeds the token-economy kit | none observed |
| 28.4 | Savings telemetry in journals and status | none observed |
| 28.5 | The pinned wrapped-vs-unwrapped benchmark | none observed |
| 28.6 | The graduated compression ladder | none observed |
| 28.7 | Index freshness is an advisory finding | none observed |
| 28.8 | Derived context recomputes only on source change | none observed |
| 28.9 | Planning-graph retrieval behind the Scribe seam | none observed |
| 28.10 | The model-cost catalog makes spend legible in dollars | none observed |
| 28.11 | Difficulty tiers route across providers and pools | none observed |
| 28.12 | Dependency-derived dispatch ordering | none observed |
| 28.13 | Sanctioned retry after an operator-initiated stop | none observed |
| 28.14 | Auto-derived effective surface, no manual per-story widening | none observed |
| 28.15 | Scope-violation enforcement mode, policy-declared, default warn | none observed |
| 28.16 | Parallel dispatch fan-out when deps and surfaces are disjoint | none observed |
| 28.17 | Verify-fail terminalization and transient auto-redispatch | none observed |
| 28.18 | Re-preflight when the refuse predicate can change | none observed |
| 28.19 | Missing-spec escalates, never idle-with-backlog | none observed |
| 28.20 | CAP-4 land heals mechanical and DIRTY PRs | none observed |
| 28.21 | Push the dispatch branch before verify can strand it | none observed |
| 28.22 | Verify blast radius is pre-existing-gate, not story-refuse | none observed |
| 28.23 | Stranded-work signal after terminal verify-fail | none observed |
| 28.24 | Supervisor finalizes when the harness cannot run shell | none observed |
| 28.25 | Finalize escalations self-clear past a later success | none observed |
| 28.26 | CAP-4's own feed-sync guards missing keys too, not just regressions | none observed |
| 28.27 | Planning-graph is proven live for dispatch — extend the win fleet-wide | none observed |
| 28.28 | Scribe exposes caller-declared derived-context refresh, closing the CAP-5/CAP... | none observed |
| 28.29 | Wire is dead for cursor specifically — copilot is a real but uncertain altern... | none observed |
| 28.30 | Output (caveman) compresses dispatch sessions too, not just spin | none observed |
| 28.31 | Structure-graph (codegraph) for dispatch — provisioning cost weighed against ... | none observed |
| 28.32 | Derived-context and output roll out fleet-wide | none observed |
| 28.33 | The structure-graph reference is wired for spin, unblocking the already-built... | none observed |
| 29.1 | A done spec HALTs unless follow-up is true | none observed |
| 29.2 | Harness `done` is CAP-4 only — never another session | none observed |
| 30.1 | The retired-ID guard follows the 6.12 shim roster | none observed |
| 30.2 | The project-context surface follows 6.12 (D1) | none observed |
| 30.3 | Documentation pointers follow 6.12 | none observed |
| 30.4 | bmad-loop's repo skills match the installed package — by test | none observed |
| 30.5 | Every live caller follows the shim retirement | none observed |
| 31.1 | TEA's workflows produce every station's test architecture | none observed |
| 31.2 | The generator, its meta-tests and its pixi tasks retire behind the equivalenc... | none observed |
| 31.3 | `tea-test-review` is a marshal review lens | none observed |
| 31.4 | Every in-place-edited installer-owned file is governed by a marshal spec surface | none observed |
| 31.5 | Loop-home readiness is defined for the cutover flip | none observed |
| 31.6 | `bmad-os-gh-triage` and `multi-repo-git-ops` are marshal-wielded | none observed |
| 32.1 | The operating-model standard is 6.12-accurate and derives what it can | none observed |
| 32.2 | Declared Python floor equals the tested floor | none observed |
| 32.3 | Dated planning artifacts are machine-classifiable | none observed |
| 32.4 | No artifact survives that the toolchain no longer produces | none observed |
| 32.5 | One test-suite vocabulary across the fleet | none observed |
| 32.6 | Governance documents cannot go stale silently | none observed |
| 32.7 | Coverage is measured on all eight stations before any floor is enforced | none observed |
| 32.8 | Every caller and CI lane follows the convergence | none observed |
| 33.1 | Measurement first — the benchmark artifact, with real savings getters | none observed |
| 33.2 | The layers are enabled on `factory dispatch` | none observed |
| 33.3 | The layers are enabled on `factory spin`, or spin is declared a two-layer engine | none observed |
| 33.4 | CAP-18 — one publisher: run state and savings telemetry reach the supervisor | none observed |
| 33.5 | Risk-tiered review depth gets a producer and a caller | none observed |
| 33.6 | Adaptive tiering is fed on all eight stations, and the floor-raise reaches di... | none observed |
| 33.7 | The two Epic-20 watchdogs observe the plane the estate actually runs | none observed |
| 33.8 | The first live fan-out wave, on a real `dispatch.max_parallel` key | none observed |
| 33.9 | `verify_scope` guards `marshal factory dispatch` | none observed |
| 33.10 | The CFE pin is derived, never stamped | none observed |
| 33.11 | Attribution becomes unforgeable before the Track serves a second principal | none observed |
| 33.12 | CAP-1/2/4/5 in effect — held runs, publisher identity, and the loop-home read... | none observed |
| 33.13 | CAP-3's mechanism tier — the automated proof `platform-ci-local` gates on | none observed |
| 33.14 | CAP-5's deployed profile — a real device-code/PKCE `pyforge login` | none observed |
| 33.15 | The tier map names Cursor models before any unattended drain | none observed |
| 34.1 | `factory spin` refuses a second launch against a live loop home | none observed |
| 34.2 | A dispatch/spin session's worktree is checkpointed before it can be lost to a... | none observed |
| 34.3 | `factory drain` tells a crashed session apart from a genuinely failed one | none observed |
| 34.4 | The ATTENTION-block's own refused-verdict check gets the same test coverage i... | none observed |
| 35.1 | A templated-form merge subject is corroborated against the querying project's... | none observed |
| 36.1 | Root pixi.toml and the catalog document every station's already-shipped, undo... | none observed |
| 36.2 | `llms-full-check` reads every station's own nested manifest, not just root pi... | none observed |
| 37.1 | Phase 0 — mechanical debt to zero before any semantic audit | none observed |
| 37.2 | Phase 1 — every remaining story gets a cited verdict | none observed |
| 37.3 | Phase 2 — the five completed stations audited at equal rigor | none observed |
| 37.4 | Phase 2b — all 61 Dreams dispositioned | none observed |
| 37.5 | Phase 3 — decomposition only behind a landed gate report | none observed |
| 37.6 | Phase 4 — the operator resumes on measured artifacts | none observed |
| 38.1 | Every station's epics doc is swept for forward-epic dependencies | none observed |
| 38.2 | A forward-dependent story is structurally non-actionable | none observed |
| 38.3 | A permanent detector prevents recurrence | none observed |
| 38.4 | An unparseable epics format is reported honestly, never silently clean | none observed |
| 39.1 | A null harness run id recovers by filesystem discovery | none observed |
| 39.2 | A genuinely unrecoverable run still degrades honestly | none observed |
| 40.1 | One canonical epics.md, with landed story identity preserved | none observed |
| 40.2 | One contiguous FR space, and every installer-only namespace decided | none observed |
| 40.3 | Both CLI contradictions are decided, not flagged | none observed |
| 40.4 | No document still frames it as a separate thing | none observed |
| 40.5 | One dashboard row, and no code reference to the retired name | none observed |
| 41.1 | Dead scaffolding is archived, never deleted | none observed |
| 41.2 | Templated fiction is replaced with real content | none observed |
| 41.3 | Stale pointers and off-convention layouts are corrected | none observed |
| 41.4 | The currency detector is fixed before its data is caught up | none observed |
| 42.1 | A co-governed file is clean when any one of its governing specs reconciled it | none observed |
| 42.2 | Overlap tolerance narrows a false positive without widening what counts as re... | none observed |
| 43.1 | The citation detector shows everything it knows | none observed |
| 44.1 | `marshal watch` ports the operator's ritual into a real CLI verb | none observed |
| 44.2 | `marshal watch` is reachable over MCP | none observed |
| 44.3 | The Marshal persona can offer "watch a run" as a menu action | none observed |
| 44.4 | `marshal watch`'s report is viewable in the portal | none observed |
| 45.1 | A pixi task generates `.mdc` from `SKILL.md` | none observed |
| 45.2 | A drift detector fails a stale generated `.mdc` | none observed |
| 45.3 | The pilot pair uses Task when available and HALTs when it is not | none observed |
| 46.1 | A bare clone bootstraps the substrate | none observed |
| 46.2 | The canonical context bundle is digest-pinned | none observed |
| 46.3 | `scribe capture` is the blessed session-close ritual | none observed |
| 46.4 | Wire auto resolves against the declared wrapper | none observed |
| 46.5 | The journal splits silent saves from configured layers, and the rollup speaks... | none observed |
| 46.6 | An interactive session whose layers lapse gets a persistence advisory | none observed |
| 46.7 | The docs name marshal dispatch and spin the execution front door | none observed |
| 46.8 | The interactive Claude session path is one documented invocation | none observed |
| 46.9 | Benchmark legs run per layer with cache-hit rates | none observed |
| 46.10 | The matrix tells the truth, copilot wrapper, gemini probe, per-currency cells | none observed |
| 46.11 | The dispatched Claude session is launched with the instruction-file mode pinned | none observed |
| 46.12 | Marshal's shell-outs name the Guild env | none observed |
| 47.1 | A bmad-loop dev pass automatically receives relevant scribe feedback before i... | none observed |
| 47.2 | A bmad-loop review pass sees the same scoped feedback the dev pass saw | none observed |
| 47.3 | The recall-injection layer composes with the existing [context] pipeline | none observed |
| 47.4 | A genuine recall miss injects nothing, never a fabricated confidence claim | none observed |
| 50.1 | A landing never re-dispatches the story it just landed | none observed |
| 50.2 | A harness's own usage-wall wording is a transient outcome | none observed |
| 50.3 | `--harness` outranks a dead tier-map harness | none observed |
| 50.4 | Landing evidence carries the station in every shape | none observed |
| 50.5 | The promoter reads a spec through its banner | none observed |
| 51.1 | Verification sees the merge result | none observed |
| 51.2 | The landing record follows the session's write, not the primary's directory | none observed |
| 51.3 | The campaign reads the ledger it just promoted | none observed |
| 51.4 | A blocked outcome never lands | none observed |
| 51.5 | MRS-DISP-043 speaks for an uncatalogued model | none observed |
| 51.6 | `marshal watch` follows the engine that is actually driving the station | none observed |
| 51.7 | Landing evidence is intent-scoped, not just station-scoped | none observed |
| 51.8 | The banner-skip family is complete | none observed |
| 51.9 | The campaign reads the ledger it just promoted (re-mint of 51.3) | none observed |
| 51.10 | The watch's marshal-status probe is executable and proven against the real in... | none observed |
| 51.11 | A session that halts blocked with its verdict uncommitted is a blocked outcom... | none observed |
| 51.12 | A dispatch-only checkout still has fleet rows | none observed |
| 51.13 | The watch reads the dispatch verdict in the supervisor's own vocabulary | none observed |
| 52.1 | The six accumulated violations are cleared | none observed |
| 52.2 | The conformance suite is a PR gate | none observed |
| 53.1 | The dispatched session is told and gated like a loop session | none observed |
| 53.2 | The landing reconciles from git facts and runs intake | none observed |
| 53.3 | The supervisor entrypoint reaches the floor | none observed |
| 53.4 | A dispatch landing leaves every Spec it touched stampable | none observed |
| 54.1 | The hand ledger sync repairs unrelated feed drift instead of refusing | none observed |
| 55.1 | The 7 non-marshal stations stop overriding `[context]` and inherit the clean ... | none observed |
| 56.1 | A refused landing whose story has since landed reads as superseded | none observed |
| 57.1 | A refresh pushes its own fast-forward to `main` with the journaled preflight ... | none observed |
| 58.1 | `merge_tree_conflict_paths` reads git's own conflicted-file list | none observed |
| 59.1 | A ledger-only conflict is healed by a merge of `origin/main`, not a union commit | none observed |
| 60.1 | Every remote-tracking read names the full ref | none observed |
| 61.1 | Every local-branch read names the full ref | none observed |
| 62.1 | The kit's branch guards default to the remote-tracking ref | none observed |
| 63.1 | The station-tests lane picks suites from the remote-tracking ref | none observed |
| 64.1 | The dispatch worktree carries its own scope, never the shared marker | none observed |
| 65.1 | A drain plan reports every refusal it can decide before launch | none observed |
| 65.2 | A story whose spec cannot bind is refused before a session is spent | none observed |
| 66.1 | Finalize carries a recommended follow-up review into the deferred-work ledger | none observed |
| 66.2 | Every landed follow-up recommendation is backfilled and held by a meta test | none observed |
| 67.1 | A landed dispatch reads completed when the primary checkout cannot be fast-fo... | none observed |
| 68.1 | A landing's ledger promotion reaches origin/main, and a failed one is never s... | none observed |
| 69.1 | The switch script runs where it is documented to run | none observed |
| 70.1 | Seed check judges the paths the manifest means, never its placeholders | none observed |
| 70.2 | Seed check honours recorded skips, and every verb records directory entries | none observed |
| 71.1 | The front door names the environment a roster station runs in | none observed |
| 72.1 | The dispatch supervisor reads merge facts from origin/main | none observed |
| 73.1 | A follow-up review run is judged and landed by its own branch | none observed |
| 73.2 | A drain schedules the follow-up review a landed story recommended | none observed |
| 74.1 | The testing kit runs a story in both flag states through one fixture | none observed |
| 74.2 | Dispatch refuses a story the flag gate would red, before any session starts | none observed |
| 74.3 | bmad-spec, bmad-build and bmad-tea carry the flag mandate in their overrides | none observed |
| 75.1 | fleet_scan reads archived Dreams from the archive | none observed |
| 76.1 | bmad_drift_check.py's --specs mode retires | none observed |
| 77.1 | Dispatch seeds each worktree's codegraph index from the shared base and syncs it | none observed |
| 78.1 | A landing unions append-only memlogs instead of refusing | none observed |
| 79.1 | A landing promotes the story's Tier-3 feed row and its tracked spec, not only... | none observed |
| 79.2 | Dispatch verification runs `lint-types`, and the "stopgap" surfaces stop call... | none observed |
| 80.1 | A dispatch landing waits for its PR's checks and refuses on a red one | none observed |
| 81.1 | A drain cycle whose wave holds every story reports held instead of crashing | none observed |
| 81.2 | The drain plan reads a prose park only where one is written, never in a story... | none observed |
| 81.3 | The campaign supervisor keeps --retry-environment-blocks across its cycles | none observed |
| 82.1 | Gate evaluate finds the real repository under an installed package and never ... | none observed |
| 82.2 | Marshal land keeps a live run's branch and home while its engine is alive, ev... | none observed |
| 82.3 | A landing claims only committed promotions, rejects a malformed merge templat... | none observed |
| 82.4 | The supervisor attaches despite a quarantined launch, journals its spawn and ... | none observed |
| 82.5 | Budget and idle signals judge staleness monotonically, keep a story's breach ... | none observed |
| 82.6 | A resumed run escalates against the ceilings it launched under and journals b... | none observed |
| 82.7 | Factory spin refuses a second live run and reports a child that dies before i... | none observed |
| 82.8 | Status reads landings the way deploy does and filters findings with rows, and... | none observed |
| 82.9 | VCS commit text is declared egress and gate evaluate writes a redacted gate r... | none observed |
| 82.10 | A parallel wave journals each member's own outcome and refuse predicate | none observed |
| 82.11 | Seed apply refuses an escaping manifest path per entry and guards never-write... | none observed |
| 82.12 | Seed apply binds a plan to its repository, refuses a directory target with a ... | none observed |
| 82.13 | A marker opt-out is representable for every artifact, accepted by preconditio... | none observed |
| 83.1 | Dispatch liveness proves a pid is the session it launched | none observed |
| 83.2 | Every station's dispatch verification runs the checks that read the whole tree | none observed |
| 83.3 | The landing heal unions appended deferred-work rows the way it unions memlog ... | none observed |
| 83.4 | A serial campaign holds the next overlapping story while a refused story is u... | none observed |
| 83.5 | A campaign supervisor keeps ticking through fleet-lock contention | none observed |
| 83.6 | Dispatch resyncs a stale codegraph index before it launches a session | none observed |
| 83.7 | A re-dispatch after a refused landing lands the existing branch without a new... | none observed |
| 83.8 | Dispatch hands a session a story status bmad-build-auto recognizes | none observed |
| 83.9 | Dispatch applies ruff format to a story's files before it verifies | none observed |
| 83.10 | A verification refusal never relaunches a fresh session or raises the model | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_retry_83_10.py` |
| 83.11 | The landing heal unions appended team-memory index lines | none observed |
| 83.12 | Dispatch verification runs the coverage gate of every station the story touches | none observed |
| 83.13 | The landing heal keeps the team-memory index's blank lines | none observed |
| 83.14 | A manual merge mid-dispatch never strands the session's fixes | none observed |
| 83.15 | Dispatch applies ruff's safe fixes before it verifies | none observed |
| 83.16 | Dispatch finalize commits paths with spaces | none observed |
| 83.17 | Dispatch refuses a commit that carries an attribution trailer | none observed |
| 83.18 | A re-dispatched send-back waits for its landing review | none observed |
| 83.19 | Dispatch never commits the CFE surface outside a sanctioned retro | none observed |
| 83.20 | Landing finalize never promotes a Tier-3 spec the ledger does not list | none observed |
| 83.21 | Landing finalize writes the epic roll-ups the sync writes | none observed |
| 83.22 | The landing's ledger guard judges the twin it overwrites | none observed |
| 83.23 | Dispatch verification runs the cross-station meta-tests that read the story's... | none observed |
| 83.24 | A rename out of the CFE surface is caught, and the station guards read the on... | none observed |
| 83.25 | A Cursor dispatch session never attributes its commits to the agent | none observed |
| 84.1 | An operator-run refresh reads every harness's live model list and reports drift | none observed |
| 84.2 | The model-list refresh tests can fail, and a partial listing is never complete | none observed |
| 85.1 | A verification refusal goes back to the session that wrote the change for one... | none observed |
| 85.2 | A fix turn that turns verification green lands, and survives a supervisor res... | none observed |
| 85.3 | The fix turn is safe to switch on in dev and staging | none observed |
| 85.4 | The fix turn's redaction never hangs the supervisor or hides what the fix needs | none observed |
| 85.5 | The verify fix turn's edits get the spec-surface reconcile before re-verifica... | none observed |
| 85.6 | A fix turn re-runs only the failing commands and knows the flag checklist | none observed |
| 86.1 | Seed honours recorded skips, refuses shared manifest paths, and pins director... | none observed |
| 86.2 | local-recipes is genesis-adopted so the seed-adopt oracle goes green | none observed |
| 86.3 | Spin and the journal clean up a failed launch and record what they ran | none observed |
| 86.4 | Status, the drain plan and the ledger publish read the station as it is | none observed |
| 86.5 | The chain tooling sheds its retired and noisy paths | none observed |
| 86.6 | The test-coverage matrices are regenerated and their check blocks drift | none observed |
| 86.7 | The session-close docs name the context advisory and the retired-id guard sca... | none observed |
| 86.8 | Path-form spec cites count as missing, and the retired chain verb leaves no t... | none observed |
| 87.1 | The sweeper reaches remote branches and never deletes a protected ref | none observed |
| 87.2 | The unpushed-work detector fails closed and never prints a tag-minting remedy | none observed |
| 87.3 | Preserved work has one grammar and one verb | none observed |
| 87.4 | Spin parks every attempt as a preserve tag before bmad-loop can prune it | none observed |
| 87.5 | Dispatch and drain preserve a stopped story's work as a tag on origin | none observed |
| 87.6 | Land, retire and the station branch never fight the protected list | none observed |
| 87.7 | Teardown refuses to remove a loop home that holds unpreserved work | none observed |
| 87.8 | The sweeper preserves to tags and retires promoted engine scratch | none observed |
| 87.9 | Every preserve reader sees preserve tags and origin | none observed |
| 87.10 | Merged-check objects never enter the object store | none observed |
| 87.11 | The build skills and recovery recipes preserve before they revert or rebuild | none observed |
| 87.12 | Legacy refs are promoted and attempt-preserve leaves the protected list | none observed |
| 87.13 | Nothing in a loop home prunes a preserve or rewrites a station branch | none observed |
| 87.14 | The sweeper reports stale-locked agent worktrees and orphan directories | none observed |
| 87.15 | A preserve reaches origin only through the content gate | none observed |
| 87.16 | The orphaned tips are re-preserved as local archive tags | none observed |

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |
| Story-id coverage drift | every epic story id in matrix | `--check` (CAP-5 / Story 19.4) |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
