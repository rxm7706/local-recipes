---
title: "Test Architecture — pyforge-steward"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.0.0
status: generated
station: steward
source_fingerprint: f1dddf2ae5b925b5
story_count: 80
test_file_count: 46
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Steward

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.0.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-steward`
- **Stories parsed:** 80
- **Epics parsed:** 21
- **Test files inventoried:** 46 under `src/shared/packages/pyforge-steward/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `f1dddf2ae5b925b5`

## Risk Assessment

### High-risk epics

- Epic 1: Keys — Credential Lifecycle
- Epic 7: The one-container Guild
- Epic 9: Secure live dashboards
- Epic 16: The platform host earns its 15 factors
- Epic 1: Keys — Credential Lifecycle

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
- Epic 2: Deploy — Reconciled Dashboard Publishing
- Epic 3: Provision — Environment & Runner Access
- Epic 4: Budget — Declared Resource Ceilings

### Low-risk epics

- Epic 10: python-agent-platform — the host takes root
- Epic 12: Deploy anywhere, including nowhere-connected

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-steward/tests/conformance/test_budget_check.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_budget_set.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_budget_show.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_build.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_dry_run.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_ledger_refusal.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_perimeter.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_reconcile.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_static.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_status.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_duty_protocol.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_keys_audit_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_keys_audit_drift.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_keys_encrypt_decrypt.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_keys_host_scoping.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_keys_list.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_keys_plaintext_secret_scan.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_keys_revoke.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_keys_rotate.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_provision_env.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_provision_list.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_provision_list_modules.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_provision_module.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_provision_runner.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_provision_verify.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_sync_config.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_sync_duty.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` | meta | none observed |
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
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_apply.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_pin_fan_out.py` | unit | none observed |
| `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_preflight.py` | unit | none observed |
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

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-steward
python _bmad/scripts/bmad_tea_playwright.py --all
```
