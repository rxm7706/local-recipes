---
title: "Test Architecture — pyforge-steward"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: steward
source_fingerprint: 43d1115a8be18c1e
story_count: 190
test_file_count: 69
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Steward

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-steward`
- **Stories parsed:** 190
- **Epics parsed:** 46
- **Test files inventoried:** 69 under `src/shared/packages/pyforge-steward/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `43d1115a8be18c1e`

## Risk Assessment

### High-risk epics

- Epic 1: Keys — Credential Lifecycle
- Epic 7: The one-container Guild
- Epic 9: Secure live dashboards
- Epic 16: The platform host earns its 15 factors
- Epic 42: Agent and bus containment (CAP-4 / CAP-8 / CAP-11 / CAP-12)

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
- Epic 46: The bmad-suite is wielded by the fleet (spec-bmad-suite-lifecycle CAP-1..8)
- Epic 47: The BMAD estate is cutover-ready (spec-bmad-suite-lifecycle CAP-9)

### Low-risk epics

- Epic 10: python-agent-platform — the host takes root
- Epic 12: Deploy anywhere, including nowhere-connected
- Epic 44: Cutover to python-foundry (spec-python-foundry-cutover fnd:CAP-1 fnd:CAP-2 fnd:CAP-3 fnd:CAP-4 fnd:CAP-5 fnd:CAP-6 fnd:CAP-7 fnd:CAP-8 fnd:CAP-9 fnd:CAP-10)

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_first_portal_slice_provision_list.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_skf_domain_skills.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_skf_steward_skill.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_station_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_steward_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py` | meta | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_setup.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_bootstrap_setup_flow.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_budget_check.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_budget_set.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_budget_show.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_audit.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_cache.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_declarations.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_export.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_filtering.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_isolation_proof.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_middleware.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_navigation.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_views.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_build.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_dry_run.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_ledger_refusal.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_perimeter.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_reconcile.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_static.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_deploy_status.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_duty_protocol.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_audit_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_audit_drift.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_encrypt_decrypt.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_host_scoping.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_list.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_plaintext_secret_scan.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_revoke.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_keys_rotate.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_env.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_install_class_playbook.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_list.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_list_modules.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_module.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_module_installers.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_plugin.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_runner.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_provision_verify.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_revoke_duty.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_suite_advance.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_suite_pipeline_truth.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_suite_wired_class_predicates.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sync_config.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sync_duty.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_sync_reconcile_propagation.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_native_path_spot_checks.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_pin_fan_out.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_preflight.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_reconcile.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_workspace.py` | unit | none observed |
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
| 27.1 | Liquibase on the channel (operator gate) | none observed |
| 27.2 | Pre-upgrade Job and DML-only app role | none observed |
| 27.3 | Stale extraction fails CI | none observed |
| 27.4 | Test databases still migrate | none observed |
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
| 39.4 | Optional pixi feature bundle (CAP-4) | none observed |
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
| 43.1 | Split the Dream into living and archive | none observed |
| 43.2 | Station API contract and the /api/v1 collision | none observed |
| 43.3 | In-process station port, no self-call | none observed |
| 43.4 | Golden Path CD by digest | none observed |
| 43.5 | One interpreter story | none observed |
| 43.6 | Platform image moves to Python 3.14 | none observed |
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
| 46.7 | skf is pinned to `v2.1.0` and CAP-7 is exercised live | none observed |
| 46.8 | CIS is re-provisioned to the packaged revision | none observed |
| 46.9 | pipeline-truth's installed stage reads the applied core, and `wired` is a dec... | none observed |
| 46.10 | The release cadence is one verified runbook | none observed |
| 47.1 | The readiness checklist is live and the pre-flight is its P7 signal | none observed |
| 47.2 | `skf-export` is proven to accept the foundry skills root | none observed |
| 47.3 | `_bmad/**` joins Epic 44's surface and `PROJECTS.md` carries the cutover layout | none observed |
| 47.4 | The foundry stack carries a `bmad-*` floor row | none observed |
| 47.5 | Epic 44 depends on the era tail, and 44.13's scope names the spines | none observed |

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | canopy:FR-132 |
| Story-id coverage drift | every epic story id in matrix | `--check` (CAP-5 / Story 19.4) |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-steward
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-steward --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
