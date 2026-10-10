---
title: "Test Architecture — pyforge-steward"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: steward
source_fingerprint: db25f01fc96932b5
story_count: 339
test_file_count: 109
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Steward

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-steward`
- **Stories parsed:** 339
- **Epics parsed:** 86
- **Test files inventoried:** 109 under `src/shared/packages/pyforge-steward/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `db25f01fc96932b5`

## Risk Assessment

### High-risk epics

- Epic 1: Keys — Credential Lifecycle
- Epic 7: The one-container Guild
- Epic 9: Secure live dashboards
- Epic 16: The platform host earns its 15 factors
- Epic 42: Agent and bus containment (CAP-4 / CAP-8 / CAP-11 / CAP-12)
- Epic 52: The last two suite skips become an authoring path and an isolated sidecar
- Epic 71: The preflight answers in under a minute (spec-pyforge-steward CAP-159)
- Epic 78: Two platform auth controls stop failing open (security hotfix)

### Medium-risk epics

- Epic 2: Deploy — Reconciled Dashboard Publishing
- Epic 3: Provision — Environment & Runner Access
- Epic 4: Budget — Declared Resource Ceilings
- Epic 5: The Marshal seam — obligations from the 2026-08-08 seam ratification
- Epic 6: Module provisioning
- Epic 8: Two boards, one truth
- Epic 11: The engines join as pluggable apps
- Epic 13: Scratch worktrees become one command
- Epic 14: The BMAD core upgrades repeatably
- Epic 15: The bmad-suite channel is a governed product
- Epic 17: A fresh machine reaches validate-fast through steward verbs
- Epic 18: Chrome and the trusted client
- Epic 19: Eight portals, one prefix
- Epic 20: The published front door
- Epic 21: Agents survive; run state is a service
- Epic 22: One command grammar
- Epic 23: Boards show only your rows
- Epic 24: Stations tell each other things
- Epic 25: Failure stays contained
- Epic 26: Access, secrets, and flags
- Epic 27: Schema change is governed
- Epic 28: Scribe's graph outlives a file
- Epic 29: Every 03 station is five tiers
- Epic 30: The old console is gone
- Epic 31: Non-module suite pieces install by class
- Epic 32: One plugin API for eight stations
- Epic 33: Steward owns its skill, persona, and one portal job
- Epic 34: One query plane (CAP-19)
- Epic 35: Cluster requires mcp-host (spec-mcp-era-isolation CAP-4)
- Epic 36: Lane 3 Vizro over the estate cache
- Epic 37: Five-tier roster drain
- Epic 38: Factory stdio MCP translator (spec-mcp-factory-stdio-translator)
- Epic 39: The bmad-suite metapackage (spec-bmad-suite-metapackage)
- Epic 40: Red-team CRITICALs — verified mint, durable broker (spec-pyforge-unifying-strategy CAP-6 / CAP-11)
- Epic 41: Data safety (CAP-9 / CAP-10 / CAP-19)
- Epic 43: Contracts and the document (CAP-6 / CAP-10 / Dream)
- Epic 45: eval-quality joins the suite and the reviewer gets measured (spec-bmad-eval-quality CAP-1 CAP-2)
- Epic 46: The bmad-suite is wielded by the fleet (spec-bmad-suite-lifecycle CAP-1..145)
- Epic 47: The BMAD estate is cutover-ready (spec-bmad-suite-lifecycle CAP-9)
- Epic 48: The chain tells the truth (spec-pyforge-unifying-strategy Residual 2026-09-09)
- Epic 49: Shipped becomes in effect (spec-pyforge-unifying-strategy — the realization gate)
- Epic 50: Object storage is consumable, without pyforge operating it (spec-platform-object-storage-kind)
- Epic 51: PostgreSQL and Redis become consumable, without pyforge mandating self-hosting
- Epic 53: Intelligence Hub realization (spec-intelligence-hub hub:CAP-1..145)
- Epic 54: Foundry kernel regenerate (spec-foundry-regenerate-not-fold fnr:CAP-1..145 / fnd:CAP-11)
- Epic 55: Foundry capability ledger (spec-foundry-capability-ledger fcl:CAP-1..145)
- Epic 56: platform-dev boots the local leaf (spec-platform-dev-boots-local pdl:CAP-1)
- Epic 58: The mcp-host sidecar hosts real station tools (spec-mcp-host-real-station-tools)
- Epic 59: One name, one job (spec-vocabulary-one-name-one-job CAP-1..145)
- Epic 60: Estate BMAD catalog (spec-self-hosted-bmad-marketplace CAP-1..145)
- Epic 61: Work passports and dated extracts (spec-work-passports-dated-extracts CAP-1..145)
- Epic 62: Published measure catalog (spec-build-league-scorecard CAP-1..145)
- Epic 63: The Guild environment — `pyforge-guild` is the default for every agent (spec-pyforge-steward CAP-5)
- Epic 65: The estate sprint-ledger query engine (spec-pyforge-steward CAP-146..149; partially CAP-140)
- Epic 66: Lint, types and the pre-push gate are checks, not prose (spec-pyforge-steward CAP-153..154)
- Epic 67: The estate consolidates — one laptop SBOM, one control plane, one instruction surface (spec-python-foundry-cutover fnd:CAP-12..15)
- Epic 68: Housekeeping that does not leak, and a gate journal that names what was pushed (spec-pyforge-steward CAP-155..156)
- Epic 69: An archive only for work that has not landed (spec-pyforge-steward CAP-157)
- Epic 70: Steward reads `origin/main` and its own branches by their full refs (spec-pyforge-steward CAP-158)
- Epic 72: Mason's skill cell is two skills, and the Guild answers `pyforge mason` (spec-pyforge-steward CAP-160..161)
- Epic 73: The session check reads the seed check it asks (spec-pyforge-steward CAP-162)
- Epic 74: The object-storage seam gets its first consumer (spec-pyforge-steward CAP-163)
- Epic 75: `steward keys` reaches GitHub Enterprise with scoped identities (spec-pyforge-steward CAP-164)
- Epic 76: The one flag tree can say what the flag rule needs (spec-feature-flag-governance CAP-5)
- Epic 77: The console's specs and archived pages follow the retired tier and the archive (spec-one-chain-per-station CAP-11)
- Epic 79: The session check and the dispatch preamble read each other's real output
- Epic 80: The chart tests run in Platform CI (deferral burn-down inflow)
- Epic 81: The session check reads a declared-off kit layer as silent
- Epic 82: The session check's kit remedy applies the kit
- Epic 83: Phase 2 of the deferral burn-down: steward's high deferrals
- Epic 84: Phase 3 of the deferral burn-down: steward's ruled fixes
- Epic 85: The protected refs are declared once, and no session deletes what would orphan commits (spec-pyforge-steward CAP-165)
- Epic 86: `deploy perimeter` fronts the ASGI application it is given (fix under CAP-114)

### Low-risk epics

- Epic 10: python-agent-platform — the host takes root
- Epic 12: Deploy anywhere, including nowhere-connected
- Epic 44: Cutover to python-foundry (spec-python-foundry-cutover fnd:CAP-1 fnd:CAP-2 fnd:CAP-3 fnd:CAP-4 fnd:CAP-5 fnd:CAP-6 fnd:CAP-7 fnd:CAP-8 fnd:CAP-9 fnd:CAP-10)
- Epic 57: One pixi env for the platform image (spec-platform-image-one-pixi-env)
- Epic 64: Frame draft re-grounding at frame-spec#28 `d7213c1` / #29 `4596579` (spec-pyforge-steward CAP-6)

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_first_portal_slice_provision_list.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_guild_environment_stations.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_no_station_assumes_local_recipes.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_object_store_seam_boundaries.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_release_cadence_runbook.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_session_check_entry_points.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_skf_domain_skills.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_skf_steward_skill.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_station_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_steward_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_steward_single_flag_tree.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_remedies.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_setup.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_setup_flow.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_budget_check.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_budget_set.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_budget_show.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_catalog.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_corridor.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_cutover.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_admin_and_htmx.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_audit.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_cache.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_declarations.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_export.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_filtering.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_isolation_proof.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_middleware.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_navigation.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_views.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deck_drift_duty.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_build.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_dry_run.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_ledger_refusal.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_perimeter.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_reconcile.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_static.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_status.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_duty_protocol.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_events_stream_consumer.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_frame_preflight.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_glass.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_guards.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_audit_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_audit_drift.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_encrypt_decrypt.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_ghe_credentials.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_host_scoping.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_http_bridge.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_list.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_plaintext_secret_scan.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_revoke.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_rotate.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_measures.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_passport_mint.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_preflight.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_preflight_budget.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_preflight_suite_reduction.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_preflight_workers.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_env.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_install_class_playbook.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_list.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_list_modules.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_module.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_module_installers.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_plugin.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_runner.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_verify.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_quarantine.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_revoke_duty.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_session.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sprint_ledger_query.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_story_52_1_consume_sidecar.py` | unit | 52.1 |
| `src/shared/packages/pyforge-steward/tests/unit/test_suite_advance.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_suite_fetchers_fail_open.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_suite_pipeline_truth.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_suite_wired_class_predicates.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sync_config.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sync_duty.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sync_github_only_marker.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sync_reconcile_propagation.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sync_retry.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_track.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_native_path_spot_checks.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_next_rehearsal.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_pin_fan_out.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_preflight.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_reconcile.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_workspace.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_workspace_clean_delete.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_workspace_edges.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_workspace_full_refs.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_workspace_repo_set.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_workspace_repo_set_status_teardown.py` | unit | none observed |

## Story Coverage Matrix

| Story | Title | Linked test files |
|-------|-------|-------------------|
| 1.1 | Steward exists as an installable CLI | none observed |
| 1.2 | Credentials never attach outside their declared host, and the JFrog leak can ... | none observed |
| 1.3 | Secrets Steward stores live encrypted in Git, never as plaintext | none observed |
| 1.4 | Rotating a key never breaks what already trusted it | none observed |
| 1.5 | The operator can see every credential Steward knows about, never a secret value | none observed |
| 1.6 | The operator can ask "is anything host-unscoped right now?" and get a real an... | none observed |
| 1.7 | Retiring a credential leaves a record, not a silent gap | none observed |
| 2.1 | The dashboard builds through Steward, not a bare pixi task the operator has t... | none observed |
| 2.2 | Nothing happens unless something actually changed | none observed |
| 2.3 | The operator can see what would change before it changes | none observed |
| 2.4 | The operator can ask "when did the dashboard last actually deploy?" | none observed |
| 3.1 | Any named pixi environment materializes with one command | none observed |
| 3.2 | A bmad-loop runner and its environment materialize together | none observed |
| 3.3 | The operator can see every environment that exists, before picking one | none observed |
| 3.4 | The environment.yaml sync gate is one command away, not a remembered incantation | none observed |
| 4.1 | A ceiling can be declared, machine-readably | none observed |
| 4.2 | The declared ceiling is one command away | none observed |
| 4.3 | Asking "am I under budget?" never lies | none observed |
| 5.1 | Retire `provision --runner bmad-loop` in favour of `marshal init` | none observed |
| 5.2 | Consume the sprint ledger; never derive story status | none observed |
| 6.1 | `provision --module <name>` | none observed |
| 6.2 | `provision --list-modules` | none observed |
| 6.3 | Partial install is a named failure | none observed |
| 7.1 | One build, whole Guild | none observed |
| 7.2 | The repo at a fixed short path | none observed |
| 7.3 | Credentials never enter image layers | none observed |
| 7.4 | State outlives the container | none observed |
| 7.5 | The image proves itself at build time | none observed |
| 8.1 | Bidirectional propagation | none observed |
| 8.2 | Zero-loop guarantee | none observed |
| 8.3 | Idempotent update processing | none observed |
| 8.4 | The schedule trigger enumerates real candidates | none observed |
| 8.5 | Fail loud, fail alone | none observed |
| 8.6 | Explicit status-vocabulary translation | none observed |
| 8.7 | Assignee and identity-link propagation | none observed |
| 9.1 | Identity at the boundary, declared isolation, and the cache invariant | none observed |
| 9.2 | An unauthorized page is absent, not hidden | none observed |
| 9.3 | The audit trail records what was seen | none observed |
| 9.4 | Export gated server-side | none observed |
| 9.5 | The perimeter ships with the pattern | none observed |
| 9.6 | Isolation proven by tests that cannot pass vacuously | none observed |
| 9.7 | Hosted or static, no fork | none observed |
| 10.1 | The host renders into src/platform | none observed |
| 10.2 | One factory-sourced environment | none observed |
| 10.3 | One image, both engines | none observed |
| 10.4 | The bcrypt pin stops blocking 3.14 | none observed |
| 10.5 | The DB-GPT sidecar image + docker-compose wiring | none observed |
| 11.1 | Langflow joins as a pluggable app | none observed |
| 11.2 | DB-GPT joins via its configured integration pattern | none observed |
| 11.3 | Async work never blocks Django | none observed |
| 11.4 | Isolation and statelessness proven | none observed |
| 12.1 | The vanilla chart with an OCP overlay | none observed |
| 12.2 | GKE as a portability profile | none observed |
| 12.3 | Air-gap parity is a failing check | none observed |
| 12.4 | The cluster bring-up is documented, reproducible, and key-disciplined | none observed |
| 12.5 | The DB-GPT sidecar joins the chart | none observed |
| 12.6 | Redis is hardened, still ephemeral | none observed |
| 12.7 | The 12.1 Tier-3 items are verified on the live cluster | none observed |
| 12.8 | GitHub Projects V2 lands in github_metrics via dlt | none observed |
| 12.9 | OCP as a portability profile | none observed |
| 13.1 | Workspace verbs over git worktree | none observed |
| 13.2 | Status and the feed-mirror decision | none observed |
| 13.3 | A repo set opens as one workspace | none observed |
| 13.4 | The set reports and tears down safely | none observed |
| 13.5 | `workspace clean --delete` removes a gone or landed workspace without a promp... | none observed |
| 14.1 | The pre-flight diff retrodicts a real upgrade | none observed |
| 14.2 | Apply is deliberate, branched, and never clobbers custom | none observed |
| 14.3 | Clobbered custom surfaces are caught and re-applied | none observed |
| 14.4 | The pin fan-out is enumerated, not discovered by red tests | none observed |
| 14.5 | One command proves the upgrade landed | none observed |
| 14.6 | The installer is driven on purpose, and a no-op apply is a refusal | none observed |
| 14.7 | Custom modules survive the core apply | none observed |
| 14.8 | Local edits to installer-owned files are found before and re-applied after | none observed |
| 14.9 | The apply retires deprecation shims on purpose (`--no-shims`) | none observed |
| 14.10 | The `@next` rehearsal exercises CAP-6's fallback and CAP-8's conflict path, r... | none observed |
| 15.1 | One command reports the whole pipeline's truth | none observed |
| 15.2 | One command advances a stale package end-to-end | none observed |
| 15.3 | Five modules wire through the provisioning verb | none observed |
| 15.4 | The upgrade gate spot-checks one native path per class | none observed |
| 16.1 | Dependencies are pixi-sourced, single-authority | none observed |
| 16.2 | Startup refuses misconfiguration, two-stage and named | none observed |
| 16.3 | Every process speaks structlog + OTel | none observed |
| 16.4 | Policy is a test suite | none observed |
| 16.5 | Identity is OIDC-delegated, no local passwords | none observed |
| 17.1 | steward init/shell-init detect and prepare the machine | none observed |
| 17.2 | steward setup/initrepo take the machine to green | none observed |
| 18.1 | django-pyforge is the only chrome | none observed |
| 18.2 | The switcher shows only what the user may reach | none observed |
| 18.3 | Two clients, one RS256 assertion | none observed |
| 19.1 | Warden moves and is renamed | none observed |
| 19.2 | Seven more portal shells under the prefix | none observed |
| 20.1 | Wagtail publishes without a deploy | none observed |
| 20.2 | Media, renditions, and a cache that cannot eat the queue | none observed |
| 21.1 | Supervisor tables in public | none observed |
| 21.2 | Atlas MCP on the host, dual-era | none observed |
| 21.3 | start/get survives disconnect | none observed |
| 21.4 | The other seven MCP faces | none observed |
| 21.5 | Front door queries the supervisor | none observed |
| 22.1 | pyforge dispatches without reimplementing | none observed |
| 23.1 | Same URL, different rows | none observed |
| 24.1 | CloudEvents on redis-broker | none observed |
| 24.2 | Cascades halt; adapters validate | none observed |
| 25.1 | Circuits trip on async too | none observed |
| 25.2 | One DuckDB writer | none observed |
| 25.3 | Validation errors render inline | none observed |
| 25.4 | Restarts reconcile | none observed |
| 26.1 | Revoke takes effect on the next request | none observed |
| 26.2 | Manifests carry secret references only | none observed |
| 26.3 | OpenFeature packages on the channel (operator gate) | none observed |
| 26.4 | One flag flips three surfaces without a redeploy | none observed |
| 26.5 | The flag provider follows langflow onto protobuf 7 | none observed |
| 27.1 | Liquibase on the channel (operator gate) | none observed |
| 27.2 | Pre-upgrade Job and DML-only app role | none observed |
| 27.3 | Stale extraction fails CI | none observed |
| 27.4 | Test databases still migrate | none observed |
| 27.5 | The JDBC driver ships under its own name | none observed |
| 27.6 | The Liquibase Job runs on an empty database and reports nothing home | none observed |
| 28.1 | PostgreSQL driver behind the existing port | none observed |
| 28.2 | Semantic recall | none observed |
| 29.1 | SKF domain skills from station packages | none observed |
| 29.2 | Personas act only through grammar and MCP | none observed |
| 29.3 | Five-tier check | none observed |
| 30.1 | Remaining console surfaces have a home | none observed |
| 30.2 | Delete the generator and its inbound refs | none observed |
| 31.1 | Class-keyed playbook is the operator path | none observed |
| 31.2 | wired-or-not is class-correct | none observed |
| 31.3 | Fresh clone class-path is proven | none observed |
| 32.1 | Shared hook-spec and plugin registration in pyforge-core | none observed |
| 32.2 | Steward deploy-profile adapters are plugins | none observed |
| 33.1 | SKF domain skill and BMAD persona for steward | none observed |
| 33.2 | First portal slice — provision inventory | none observed |
| 34.1 | Read-only live attach | none observed |
| 34.2 | Kedro writes the Parquet cache | none observed |
| 34.3 | Vectors persist on the plane | none observed |
| 34.4 | Agents cannot reach OLTP | none observed |
| 34.5 | Scribe semantic recall uses the plane | none observed |
| 35.1 | Cluster requires mcp-host | none observed |
| 36.1 | Lane 3 BSL reads the estate cache | none observed |
| 36.2 | Estate cache Vizro page | none observed |
| 37.1 | Declare eight stations five-tier complete | none observed |
| 38.1 | The translator wraps a factory tool over stdio and never claims to be the CRC... | none observed |
| 39.1 | Canonical suite manifest | none observed |
| 39.2 | Metapackage recipe | none observed |
| 39.3 | Generator and batch build | none observed |
| 39.4 | Optional pixi feature bundle (suite:CAP-4) | none observed |
| 40.1 | IdP bearer is verified before mint | none observed |
| 40.2 | redis-broker is durable and bounded | none observed |
| 41.1 | DR contract and PostgreSQL backup | none observed |
| 41.2 | Query-plane process boundary | none observed |
| 41.3 | Scribe DDL moves into the changelog | none observed |
| 41.4 | Broker TLS is verified | none observed |
| 42.1 | MCP transport authorization and a streaming proxy | none observed |
| 42.2 | Agent rate limits and run bounds | none observed |
| 42.3 | Bus delivery semantics and a deployed consumer | none observed |
| 42.4 | Celery hardening and the builds pool | none observed |
| 42.5 | Role namespaces and the tenant claim | none observed |
| 42.6 | The real-Redis backoff test accepts the server's millisecond clock | none observed |
| 43.1 | Split the Dream into living and archive | none observed |
| 43.2 | Station API contract and the /api/v1 collision | none observed |
| 43.3 | In-process station port, no self-call | none observed |
| 43.4 | Golden Path CD by digest | none observed |
| 43.5 | One interpreter story | none observed |
| 43.6 | Platform image moves to Python 3.14 | none observed |
| 43.7 | Sidecar runtime validation on Python 3.14 | none observed |
| 44.1 | The capability ledger and the move-list manifest | none observed |
| 44.2 | The red-team document fixes | none observed |
| 44.3 | Open the foundry | none observed |
| 44.4 | Fold the packages | none observed |
| 44.5 | Move the estate | none observed |
| 44.6 | CFE comes home | none observed |
| 44.7 | The factory island | none observed |
| 44.8 | The working set | none observed |
| 44.9 | Mason submits to conda-forge | none observed |
| 44.10 | Archive local-recipes | none observed |
| 44.11 | Windows-native estate | none observed |
| 44.12 | Cutover flag and replay harness | none observed |
| 44.13 | Memlog fidelity | none observed |
| 44.14 | Rebuild harness and oracle gate | none observed |
| 44.15 | Actions-minutes metering | none observed |
| 45.1 | eval-quality joins the suite | none observed |
| 45.2 | The reviewer is measured against a planted defect | none observed |
| 46.1 | The adoption register governs wiring | none observed |
| 46.2 | utility-skills is provisioned and its ten skills have wielders | none observed |
| 46.3 | TEA is provisioned and `tea-test-review` is a pixi task | none observed |
| 46.4 | bmad-builder is provisioned beside skf, with the cleanup-legacy guard proven | none observed |
| 46.5 | labs-skills arrive by name and by consent | none observed |
| 46.6 | Herald's manticore studio has a root and a proven native path | none observed |
| 46.7 | skf is pinned to `v2.1.0` and suite:CAP-7 is exercised live | none observed |
| 46.8 | CIS is re-provisioned to the packaged revision | none observed |
| 46.9 | pipeline-truth's installed stage reads the applied core, and `wired` is a dec... | none observed |
| 46.10 | The release cadence is one verified runbook | none observed |
| 47.1 | The readiness checklist is live and the pre-flight is its P7 signal | none observed |
| 47.2 | `skf-export` is proven to accept the foundry skills root | none observed |
| 47.3 | `_bmad/**` joins Epic 44's surface and `PROJECTS.md` carries the cutover layout | none observed |
| 47.4 | The foundry stack carries a `bmad-*` floor row | none observed |
| 47.5 | Epic 44 depends on the era tail, and 44.13's scope names the spines | none observed |
| 48.1 | The ledger syncer guards blocked and missing keys | none observed |
| 48.2 | R-18 sizing rewrite | none observed |
| 48.3 | R-19 network baseline | none observed |
| 48.4 | R-20 secrets profile | none observed |
| 48.5 | R-21 observability contract | none observed |
| 48.6 | R-22 live browser streaming, or the pillar deleted | none observed |
| 48.7 | The CAP-axis namespace pass | none observed |
| 48.8 | The Single-Spec merge | none observed |
| 48.9 | OIDC default profile — Keycloak in-cluster, BYO seam kept | none observed |
| 48.10 | The one-container Guild proves itself at build time — CI builds the root Cont... | none observed |
| 48.11 | The platform image can import the warden engine it calls | none observed |
| 49.1 | The verified column on every capability | none observed |
| 49.2 | The capability effect check | none observed |
| 49.3 | CAP-4 in effect — start and get on all eight, with a real disconnect | none observed |
| 49.4 | CAP-7 in effect — the real board, or the criterion says fixture | none observed |
| 49.5 | CAP-11 in effect — the eviction test | none observed |
| 49.6 | CAP-12 in effect — revocation on the next request | none observed |
| 49.7 | CAP-14 in effect — real semantic recall, or the criterion says lexical | none observed |
| 49.8 | CAP-17 in effect — marshal publishes run state to the supervisor | none observed |
| 49.9 | Index — marshal realization-gate effect stories | none observed |
| 49.10 | Index — atlas realization-gate effect stories | none observed |
| 49.11 | Index — herald realization-gate effect stories | none observed |
| 49.12 | Index — mason realization-gate effect stories | none observed |
| 49.13 | Index — scribe realization-gate effect stories | none observed |
| 49.14 | CAP-10 in effect — the resilience primitives get a real caller, or the criter... | none observed |
| 50.1 | The Silo conda-forge recipe exists and is pixi-installable | none observed |
| 50.2 | Local-dev object storage — Silo default, Garage alternative, pixi-provisioned | none observed |
| 50.3 | A minimal S3-client seam proves the exception end-to-end | none observed |
| 51.1 | A BYO-external-PostgreSQL deployment overlay exists, additive to the self-hos... | none observed |
| 51.2 | A BYO-external-Redis deployment overlay exists, additive to the self-hosted d... | none observed |
| 51.3 | The backup/PITR handoff is explicit when the BYO-PostgreSQL overlay is active | none observed |
| 52.1 | Module-template is authoring-only and mybmad is an isolated sidecar never the... | `src/shared/packages/pyforge-steward/tests/unit/test_story_52_1_consume_sidecar.py` |
| 53.1 | The Charter carries the Hub vocabulary map | none observed |
| 53.2 | Company and eight station Frames pass in-repo preflight | none observed |
| 53.3 | One tracked track.json per run | none observed |
| 53.4 | Guards as a library without a second verdict | none observed |
| 53.5 | Adopt the frame-spec v0.3 working draft | none observed |
| 53.6 | Frame identity is the qualified-ref identifier, not the name | none observed |
| 54.1 | Thin oracle for the foundry kernel | none observed |
| 54.2 | Rebuild pyforge-core in foundry | none observed |
| 54.3 | Rebuild steward in foundry | none observed |
| 54.4 | Rebuild marshal in foundry | none observed |
| 54.5 | A/B protocol and pin on foundry | none observed |
| 55.1 | Tracked capability ledger | none observed |
| 55.2 | Extract detector in detectors-ci | none observed |
| 55.3 | verified-in-foundry joins the case list | none observed |
| 56.1 | django-debug-toolbar on platform-dev only | none observed |
| 57.1 | One frozen env replaces the pip `--no-deps` layer | none observed |
| 57.2 | Containerfile drops the pip installer entirely | none observed |
| 57.3 | pixitainer-docker re-evaluated, hand-rolled Containerfile kept | none observed |
| 58.1 | A station's real MCP tool is reachable through a deployed cluster | none observed |
| 58.2 | A station with no real app keeps the slice-1 stub, unchanged | none observed |
| 58.3 | The one unproven run-state row flips to PASS | none observed |
| 59.1 | The Spec ladder is declared and the Charter states the rule | none observed |
| 59.2 | Detectors read one declaration; in-progress is grandfathered | none observed |
| 59.3 | The Charter carries the BMAD cross-walk and pitched stays optional | none observed |
| 59.4 | Design teaching is named; the pull cannot silently rot | none observed |
| 59.5 | One mint-time slugify and two DW families | none observed |
| 59.6 | Shape hygiene — roster, S-N.N, commits, status comments | none observed |
| 59.7 | atlas check= is a finding code only | none observed |
| 60.1 | The catalog config names backends and sources | none observed |
| 60.2 | Publish uses tools we wield; steward records the review | none observed |
| 60.3 | Ship backends — conda channel default | none observed |
| 60.4 | Frame index and a thin browse list | none observed |
| 61.1 | Corridor transports — upload default | none observed |
| 61.2 | Work passport and core schema | none observed |
| 61.3 | As-of glass and mailed query | none observed |
| 61.4 | Signed outbound slice | none observed |
| 61.5 | Quarantine — mint then reject | none observed |
| 62.1 | The catalog names eight measures and their states | none observed |
| 62.2 | Add, switch, and archive without a rewrite | none observed |
| 62.3 | Consumers cite `on` rows only | none observed |
| 63.1 | The `pyforge-guild` feature and environment exist and the Guild tasks live in it | none observed |
| 63.2 | Every agent surface names `pyforge-guild` as the session default | none observed |
| 63.3 | One deny list, one hook — the Guild session guardrails are enforced, not asse... | none observed |
| 63.4 | `steward session check` — one verdict for the session preconditions, run from... | none observed |
| 63.5 | `pyforge-foundry-full` — the fleet's whole dependency closure is one locked a... | none observed |
| 63.6 | No station code assumes the `local-recipes` environment at runtime | none observed |
| 63.7 | Two `platform-ci-local` runs at once never share services or a work dir | none observed |
| 64.1 | The nine Frames go bare `type: frame` and the README pins the upstream heads | none observed |
| 64.2 | PyForge publishes its Frame conformance profile | none observed |
| 65.1 | Reusable, pluggable, feature-flagged estate sprint ledger query module & BMAD... | none observed |
| 65.2 | The ledger query answers done / running / next in one call | none observed |
| 66.1 | Lint and types gate the ten packages, locally and on the runners alike | none observed |
| 66.2 | The pre-commit set — attribution lines and un-preflighted pushes are refused ... | none observed |
| 67.1 | The SBOM composes the laptop bill of materials on three platforms, with Postg... | none observed |
| 67.2 | One laptop gate proves the laptop needs nothing beyond the SBOM | none observed |
| 67.3 | Every gap and every fat-only pin has a disposition and an owner | none observed |
| 67.4 | Upstream to-dos are tracked in the repo, and only the operator files, tracks ... | none observed |
| 67.5 | The estate points at the SBOM | none observed |
| 67.6 | Index — herald's dossier states the cutover's control plane (herald 26.1) | none observed |
| 67.7 | Index — scribe's instruction surface names the estate first (scribe 21.1) | none observed |
| 67.8 | The cutover spine drops the archive | none observed |
| 67.9 | The conda-recipe-manager click notes state the cap as it stands | none observed |
| 68.1 | A workspace archive holds the work, not the environments, and one bad record ... | none observed |
| 68.2 | The pre-push gate skips a push that carries nothing new, and its journal name... | none observed |
| 69.1 | `workspace clean` keeps a note, not a tarball, for a worktree already on its ... | none observed |
| 70.1 | Steward reads the workspace source and branch, and `origin/main`, by their fu... | none observed |
| 71.1 | Every preflight run journals each lane's wall time and exit code | none observed |
| 71.2 | The preflight runs the lanes CI would run for the diff, read from the workflo... | none observed |
| 71.3 | Selected lanes run concurrently and share no mutable state | none observed |
| 71.4 | A station's coverage gate reuses its own suite's run | none observed |
| 71.5 | The two lanes every branch runs fit the budget | none observed |
| 71.6 | The large suites run under pytest-xdist, locally and in CI alike | none observed |
| 71.7 | The one-minute budget is a check that reads the journal | none observed |
| 71.8 | A preflight lane's scratch lives outside the checkout | none observed |
| 71.9 | A reduced suite lane never fails on a segment that selects no tests | none observed |
| 71.10 | A stopped lane is journaled cancelled, and the lane that stopped the run red | none observed |
| 71.11 | No lane process outlives a stop, and a reduced lane cut short is never ok | none observed |
| 72.1 | The Guild environment answers pyforge mason | none observed |
| 72.2 | Mason's five-tier skill cell requires its station skill and conda-forge-expert | none observed |
| 73.1 | `steward session check` reads `marshal seed check`'s envelope, whatever its e... | none observed |
| 74.1 | A station streams bytes to object storage by sha256 key — herald's deck expor... | none observed |
| 74.2 | The chart names the bucket and prefix per environment and reaches only the co... | none observed |
| 75.1 | `steward keys` resolves the GitHub Enterprise host with a read identity and a... | none observed |
| 76.1 | The one flag tree carries per-environment values, so off in production is a v... | none observed |
| 76.2 | Every flag in the tree carries its owner, story and cleanup clock in flagd me... | none observed |
| 76.3 | The ledger query's flags fold into the one tree and evaluate through OpenFeature | none observed |
| 76.4 | The pyforge.three_surfaces demo flag leaves the tree | none observed |
| 77.1 | The console lists Tier-2 Specs and the archived Dreams | none observed |
| 78.1 | The platform refuses Langflow auto-login and honours an IdP revocation on the... | none observed |
| 79.1 | The session check and the dispatch preamble read each other's real output | none observed |
| 80.1 | The Platform CI `test` job runs the chart tests, and a skipped one fails there | none observed |
| 81.1 | The session check reads a declared-off kit layer as silent | none observed |
| 82.1 | The session check's kit remedy applies the kit | none observed |
| 83.1 | `steward keys` resolves its `_http` bridge on first use and reports a missing... | none observed |
| 83.2 | Login works on the plain-HTTP local stack, and `sync` retries rate limits and... | none observed |
| 83.3 | The platform chart and the compose stack run a Postgres image that carries pg... | none observed |
| 84.1 | An audit purge records itself, and the audit table is append-only by privilege | none observed |
| 84.2 | An audit read records its scope, and the perimeter refuses an over-long identity | none observed |
| 84.3 | Trusted ingress addresses are IP networks | none observed |
| 84.4 | Sync skips a board item marked GitHub-only | none observed |
| 84.5 | The GitHub-only marker tests can fail, and config refuses half declarations | none observed |
| 85.1 | The session hook refuses deleting protected branches and loop homes | none observed |
| 85.2 | The protected-ref list is declared once and the live rulesets are proven to m... | none observed |
| 85.3 | The pre-push gate skips a push it can prove carries only preserve or archive ... | none observed |
| 85.4 | The hook denies every protected-ref deletion and any deletion that orphans co... | none observed |
| 85.5 | Workspace clean parks unlanded commits as a preserve tag before removing the ... | none observed |
| 85.6 | Every command a session denial names as the sanctioned form exists | none observed |
| 85.7 | The session-denial form check never stamps the real spec-surface baseline | none observed |
| 85.8 | An agent session never writes outside this repository | none observed |
| 85.9 | The session hook reads its denial roster from its own tree | none observed |
| 86.1 | Deploy perimeter renders the ASGI application it is given | none observed |

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
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-steward
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-steward --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
