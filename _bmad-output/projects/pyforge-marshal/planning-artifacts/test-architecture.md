---
title: "Test Architecture — pyforge-marshal"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.0.0
status: generated
station: marshal
source_fingerprint: ae8187aa03934241
story_count: 162
test_file_count: 129
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Marshal

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.0.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-marshal`
- **Stories parsed:** 162
- **Epics parsed:** 31
- **Test files inventoried:** 129 under `src/shared/packages/pyforge-marshal/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `ae8187aa03934241`

## Risk Assessment

### High-risk epics

- Epic 2: Gates you can run
- Epic 20: The loop cannot lose work, and a landing is always recognizable
- Epic 2: Gates you can run

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
- Epic 1: Provisioned, verified loop homes
- Epic 3: Supervised unattended runs
- Epic 4: Landing with a durable paper trail
- Epic 5: Fleet visibility
- Epic 6: Portability proven

### Low-risk epics

- Epic 11: Derive, Migrate & Update
- Epic 24: Liveness is one command
- Epic 25: Aligned to the installed BMAD era

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-marshal/tests/integration/test_cli_contract.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_idempotence_harness.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_init_worktree.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_performance_gates.py` | integration | none observed |
| `src/shared/packages/pyforge-marshal/tests/integration/test_seed_egress_counter.py` | integration | none observed |
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
| `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_engine_version_range_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_finding_remedy_reference_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_manifest_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_p01_write_primitives_only_in_fs.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_p02_copier_sole_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_p03_detect_is_pure.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_p07_no_hash_comparison_in_apply.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_probe_json_contract.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_regions_no_manifest_import.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_rendered_policy_untracked.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_sc08_never_write_update_proof.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_seed_layer_import_rules.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_seed_no_bare_exception.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_skill_projection_manifest_untracked.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_supervisor_run_path_agreement.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_tea_architecture_generator.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/meta/test_tool_surface_coverage.py` | meta | none observed |
| `src/shared/packages/pyforge-marshal/tests/oracle/test_local_recipes_empty_plan.py` | oracle | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_adapters_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_bmad_loop_status_vocabulary.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_chain_regen.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_check.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_clock_system.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_conformance.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_conformance_schema.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_context.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_deferred_work.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_durability.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_egress.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_fold.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_forge_gh.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_fs_local.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_gate.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_preflight.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_probe.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_run_status_snapshot.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_smoke.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_spin.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_stop_resume.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_usage_snapshot.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_identity.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_init.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_journal.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_land.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_landing.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_mcp_registration.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_mcp_tools.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_model.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_notify_file_desktop.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_observer_mux.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_policy.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_refresh.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_retire.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_scope.py` | unit | none observed |
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
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_skips.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_update.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_version.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_skill_projection.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spec_binding.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spec_difficulty.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spec_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_supervise.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_supervisor.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_upstream.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_upstream_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git.py` | unit | none observed |
| `src/shared/packages/pyforge-marshal/tests/unit/test_verdict.py` | unit | none observed |

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

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-marshal
python _bmad/scripts/bmad_tea_playwright.py --all
```
