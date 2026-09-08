---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/test-design-architecture.md (companion, same run)'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md'
  - 'src/shared/packages/pyforge-steward/tests/{unit,conformance,meta}/*.py (test inventory, read directly — 67 files)'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/test-priorities-matrix.md'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/test-levels-framework.md'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/test-quality.md'
---

# Test Design for QA: pyforge-steward (system-level)

**Purpose:** Test execution recipe for QA team. Defines what to test, how to test it, and what QA needs from other teams.

**Date:** 2026-09-07
**Author:** BMad TEA Agent (autonomous run, headless)
**Status:** Draft
**Project:** pyforge-steward

**Related:** See Architecture doc (`test-design-architecture.md`) for testability concerns and architectural blockers (R-1..R-19).

---

## Executive Summary

**Scope:** Test coverage plan for `pyforge-steward`'s package (18 duty modules, 67 existing test files across `unit`/`conformance`/`meta`) at the risk level, not the individual-story level. This document organizes coverage around the 18 risks identified in the companion architecture document, not around a full enumeration of the 190 stories in `epics.md` — see § Not in Scope.

**Risk Summary:**

- Total Risks: 18 (8 high-priority score ≥6, 7 medium, 3 low)
- Critical Categories: TECH (4 risks), SEC (3), DATA (3), OPS (2), PERF (1), BUS (2)

**Coverage Summary:**

- P0 tests: ~9 (the 8 high-priority risks' verification tests, plus the dispatcher-level protocol conformance test that already exists)
- P1 tests: ~11 (medium-risk mitigations + existing high-value regressions to keep green)
- P2 tests: ~9 (low-priority risks + testability-gap closures that are useful but not release-blocking)
- P3 tests: ~5 (monitoring/documentation-only items)
- **Total**: ~34 scenarios (mix of already-existing tests to keep green + newly-recommended tests from the architecture doc's mitigation plans)

---

## Not in Scope

**Components or systems explicitly excluded from this test plan:**

| Item | Reasoning | Mitigation |
| --- | --- | --- |
| **A full story-by-story (190-row) coverage matrix mapping every `epics.md` story ID to its test file(s)** | That is `test-architecture.md`'s job — a separate, deterministic, mechanically-generated document produced by `_bmad/scripts/bmad_tea_playwright.py` and enforced by the `tea-playwright-check` pixi task (drift-checks every story ID against the on-disk matrix). Duplicating it here would create two sources of truth for the same fact. | Covered by the existing generator + CI gate; this document instead organizes by risk tier (P0-P3), citing specific story IDs only where a risk's mitigation is scoped to that story. |
| **The shared `pyforge-core` MCP-transport containment test suite (Epic 42)** | Owned and tested outside this package (per the plugin-seam note in Story 32.2); this package only registers duty adapters against that shared contract. | R-16 in the architecture doc flags the cross-station gap; closure is tracked there, not duplicated as a Steward-owned test here. |
| **The estate PostgreSQL DR/backup drill itself (Epic 41 Story 41.1)** | The database substrate is estate-shared infrastructure, not a Steward-owned duty; Steward's own durable state (`.steward/*.yaml`, `.age` files) is Git-tracked, not database-backed. | Flagged as an open question in the architecture doc (whether `.steward/` is in scope for 41.1's contract) rather than assumed covered. |
| **Full per-epic epic-level test-design documents for all 47 epics** | This system-level document sets the risk-tiered shape; any epic wanting a deeper, story-level drill-down (e.g., Epic 44's cutover, given R-14's severity) should run this same TEA workflow in Epic-Level mode for that specific epic. | Recommended as a follow-up for Epic 44 specifically, given R-14's score and the historical incident it echoes. |

**Note:** Items listed here have been reviewed and are excluded by design, not by oversight — each has an existing or explicitly-flagged coverage mechanism elsewhere.

---

## Dependencies & Test Blockers

**CRITICAL:** QA cannot fully close the high-priority risks without these items from other teams.

### Backend/Architecture Dependencies (Pre-Implementation)

**Source:** See Architecture doc "Quick Guide" for detailed mitigation plans

1. **Query-plane staleness/latency SLO (R-7)** - Architecture - Before Epic 34/36 declared complete
   - QA needs a concrete threshold (e.g., "cache staleness ≤ N minutes") to write a passing/failing k6-or-equivalent probe against.
   - Without it, Performance NFR validation for the estate query plane stays at CONCERNS indefinitely (no threshold = no PASS possible per `nfr-criteria.md`'s own default rule).

2. **Container/Helm manifest secret-reference scan tooling (R-6)** - Dev - Before next container-build story
   - QA needs the built image + rendered manifest artifact paths to point a new `tests/meta` scan at; this is a Dev-side build-output dependency, not a QA-authored mechanism.

### QA Infrastructure Setup (Pre-Implementation)

1. **Rehearsal clone for the Epic 44 cutover drill (R-14)** - QA/Steward
   - A throwaway clone of the current repo state, isolated from the real cutover flag, to rehearse the fnd:AD-21 archive-restore path before Story 44.3 executes.

2. **Test Environments**
   - Local: existing `pixi run -e pyforge-steward pyforge-steward-test` (unit/conformance/meta, no live network by default).
   - CI: existing platform-ci-local replay path (per repo convention, `pixi run -e local-recipes platform-ci-local`).
   - Staging: not applicable — Steward is single-operator tooling; "staging" for the estate-facing epics (9, 34, 42) is whatever the Canopy host's own environment tier provides, outside this package's ownership.

**Example: the repo's own existing invariant-test pattern (to model new meta tests on, per R-6/R-15)**

```python
# tests/meta/test_keys_plaintext_secret_scan.py (existing pattern this design
# recommends mirroring for R-6's container/manifest scan and R-15's base-install
# isolation check)

import subprocess
import sys


def test_keys_list_never_prints_raw_secret_value(tmp_path, monkeypatch):
    """NFR-7: `steward keys list`/`audit` output never contains a raw secret
    value under any flag combination."""
    # Arrange: seed a known secret value into the fixture inventory
    known_secret = "sk-test-CANARY-VALUE-DO-NOT-LEAK"
    # ... fixture setup wiring known_secret into an age-encrypted payload ...

    # Act
    result = subprocess.run(
        [sys.executable, "-m", "pyforge.steward", "keys", "list", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Assert: the canary never appears in any form (stdout, stderr)
    assert known_secret not in result.stdout
    assert known_secret not in result.stderr
```

**Recommended new test skeleton for R-15 (base-install import isolation):**

```python
# tests/meta/test_dashboard_extra_not_imported_at_module_level.py (NEW —
# recommended by R-15; models a subprocess import-isolation check)

import subprocess
import sys


def test_cli_imports_cleanly_without_dashboard_extra():
    """AD-4 (unified-container): dashboard imports may not be unconditional
    at module level. Import the CLI entrypoint in a subprocess and assert
    Django is never pulled into sys.modules when [dashboard] is absent."""
    probe = (
        "import sys; import pyforge.steward.cli; "
        "assert 'django' not in sys.modules, sys.modules.keys()"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
```

---

## Risk Assessment

**Note:** Full risk details in Architecture doc. This section summarizes risks relevant to QA test planning.

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Score | QA Test Coverage |
| --- | --- | --- | --- | --- |
| **R-1** | TECH | Dispatcher blast radius across 18 duties | **6** | Keep `test_duty_protocol.py` + `test_cli.py` in the required-pass set for every duty-touching PR |
| **R-3** | TECH | Dashboard isolation proof suite could go vacuous | **6** | Confirm `test_dashboard_isolation_proof.py` contains a real mutation-failure case (canary run: manually disable isolation, confirm the suite fails) |
| **R-6** | SEC | Secret material could enter image layers/Pod specs | **6** | NEW: `tests/meta` container/manifest secret-reference scan (see Dependencies above) |
| **R-9** | DATA | Jira↔GitHub zero-loop guard under baseline drift | **6** | Extend `test_sync_reconcile_propagation.py` with a baseline-drift scenario |
| **R-10** | BUS | bmad-suite readiness gate could false-positive | **6** | NEW: negative-path test injecting a known-broken suite member into the readiness checklist |
| **R-13** | OPS | BMAD-core upgrade shim-retirement (14.9/14.10) coverage unconfirmed | **6** | Confirm/extend `test_upgrade_*.py` suite for shim-retirement |
| **R-14** | DATA | python-foundry cutover repeats a known artifact-loss failure mode | **6** | NEW: rehearsal restore drill against a throwaway clone (manual/QA-run, not a pytest case) |
| **R-16** | SEC | MCP transport authorization is cross-station | **6** | Confirm a Steward-specific case exists in the shared `pyforge-core` containment suite (owned elsewhere) |

### Medium/Low-Priority Risks

| Risk ID | Category | Description | Score | QA Test Coverage |
| --- | --- | --- | --- | --- |
| R-2 | TECH | AD-5 cross-station import boundary is convention-only | 3 | NEW: `tests/meta` import-boundary assertion (`pyforge.steward` never imports `pyforge.marshal`) |
| R-4 | SEC | FR-7 JFrog regression — low probability, critical if regressed | 3 | Keep `test_keys_host_scoping.py` + `fixtures/ungated_jfrog_auth.py` green in every CI matrix cell |
| R-5 | SEC | NFR-7 plaintext-secret invariant — same shape as R-4 | 3 | Keep `test_keys_plaintext_secret_scan.py` green in every CI matrix cell |
| R-7 | PERF | Query-plane SLO undeclared | 4 | Blocked on Architecture threshold (Dependencies above); no test until then |
| R-8 | OPS | Fresh-clone path only unit-tested, not proven on a real fresh machine | 4 | Recommend a CI job on an ephemeral (no-cache) runner exercising the real `steward` fresh-clone verb |
| R-12 | DATA | Cache≠broker conflation risk (Redis) | 4 | Confirm estate Redis deployment separates cache vs. CloudEvents-stream instances (Architecture-owned confirmation, not a Steward test) |
| R-15 | TECH | Base-install dashboard-import isolation unverified | 4 | NEW: `test_dashboard_extra_not_imported_at_module_level.py` (skeleton above) |
| R-17 | BUS | Budget honest-stub could be misread | 2 | Confirm `test_budget_check.py` distinguishes all three exit codes explicitly |
| R-18 | OPS | `age` narrow version pin | 2 | Monitor only — no new test |
| R-19 | TECH | `age` `(devel)` version-string workaround | 2 | Monitor only — no new test |

---

## NFR Test Coverage Plan

**Purpose:** Map NFR requirements to planned validation work. This section defines what evidence QA should create or collect; it does not assign final PASS/CONCERNS/FAIL status.

| NFR Category | Requirement / Threshold | Planned Validation | Tool / Level | Evidence Artifact | Priority |
| --- | --- | --- | --- | --- | --- |
| Security | NFR-7 (no plaintext secret ever printed); AD-2 (host-scoped credential resolution); canopy:AD-19 (secret references only in Pod specs) | Existing conformance/meta suite + NEW manifest-scan meta test (R-6) | pytest (`conformance`/`meta` tiers) | `pytest` CI run output; new meta-test result | P0 |
| Performance | Query-plane staleness/latency — **UNKNOWN threshold** (R-7) | Blocked until Architecture declares a threshold | k6 or equivalent, once threshold exists | k6 summary report (future) | P2 (blocked, not droppable) |
| Reliability | NFR-1..NFR-6 (no standing services, sole exit-code ownership, lean deps, inherited routing); DR contract scope question (Epic 41) | Existing `unit`/`conformance` suite for NFR-1..6; DR-contract scope confirmation is a documentation task, not a test | pytest + a written confirmation from Architecture | `pytest` CI run output; a one-line spine amendment confirming `.steward/` scope | P1 |
| Maintainability | AD-1 (wrap, never reimplement); 3-tier test layout; `bmad-drift-check` currency | Existing `bmad-drift-check` pixi task + this package's own 67-file suite | CI (`pixi run -e local-recipes bmad-drift-check`) + pytest | Drift-check report; pytest CI run output | P1 |

**Missing thresholds or evidence sources:** Query-plane staleness/latency (R-7) — needs stakeholder (Architecture) clarification before `nfr-assess` can run; whether `.steward/` is in the Epic 41 DR-contract scope — needs a documentation confirmation, not a new test.

---

## Entry Criteria

**QA testing cannot begin until ALL of the following are met:**

- [ ] This test design and its companion architecture doc are reviewed by Architecture/Dev (Quick Guide blockers acknowledged)
- [ ] `pixi run -e pyforge-steward pyforge-steward-test` passes locally as a baseline (confirms the 67 existing tests this design builds on are actually green before new tests are added on top)
- [ ] The four NEW test skeletons recommended above (R-2, R-6, R-10, R-15) have an assigned owner and are not silently dropped
- [ ] Architecture has declared (or explicitly deferred with a tracked ticket) the query-plane SLO (R-7)

## Exit Criteria

**Testing phase is complete when ALL of the following are met:**

- [ ] All P0 tests passing (the 8 high-priority-risk verifications + dispatcher protocol conformance)
- [ ] All P1 tests passing or explicitly triaged with an owner and timeline
- [ ] No OPEN score-9 risk (none found this pass; re-confirm if new epics land)
- [ ] The Epic 44 rehearsal restore drill (R-14) has run at least once against a throwaway clone with a documented result, before Story 44.3 executes for real
- [ ] `bmad-drift-check` reports no new drift attributable to this test-design pass

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = **priority and risk level** (what to focus on if time-constrained), NOT execution timing. See "Execution Strategy" for when tests run.

### P0 (Critical)

**Criteria:** Blocks core functionality + High risk (≥6) + No workaround + Affects majority of the estate

| Test ID | Requirement | Test Level | Risk Link | Notes |
| --- | --- | --- | --- | --- |
| **P0-001** | Dispatcher never lets a duty call `sys.exit` directly (AD-8) | Unit (existing: `test_cli.py`, `test_duty_protocol.py`) | R-1 | Keep in required-pass set for every duty-touching PR |
| **P0-002** | Dashboard isolation proof suite fails when isolation is manually disabled (canary run) | Meta/Unit (existing: `test_dashboard_isolation_proof.py`) | R-3 | Confirm non-vacuousness, don't just re-read the file |
| **P0-003** | No literal secret value in built container image layers or rendered Helm/OCP manifests | Meta (NEW) | R-6 | Blocked on Dev providing build-artifact paths |
| **P0-004** | Jira↔GitHub zero-loop guard holds under a drifted baseline | Conformance (extend existing `test_sync_reconcile_propagation.py`) | R-9 | Before Epic 8's 8.4/8.5 unblock |
| **P0-005** | bmad-suite readiness gate reports NOT-READY for a known-broken suite member | Unit/Meta (NEW) | R-10 | Before Epic 44's cutover flag flips |
| **P0-006** | BMAD-core upgrade shim retirement (14.9/14.10) is proven landed, not merely attempted | Unit (extend existing `test_upgrade_*.py` family) | R-13 | Confirm coverage exists for the two newest stories specifically |
| **P0-007** | Epic 44 archive-restore rehearsal produces a reconciled tree from a throwaway clone | Manual/QA-run drill (not a pytest case) | R-14 | Must run before Story 44.3 executes for real |
| **P0-008** | Steward's registered duty adapters pass the shared MCP-transport containment contract | Conformance (owned outside this package — confirm a Steward-specific case exists) | R-16 | Cross-station dependency; Architecture-owned confirmation |
| **P0-009** | FR-7 JFrog cross-host leak pattern stays regression-closed | Conformance (existing: `test_keys_host_scoping.py` + `fixtures/ungated_jfrog_auth.py`) | R-4 (kept at P0 despite Score 3, because it is FR-7 / SM-1's named success metric) | Confirm this runs in every CI matrix cell |

**Total P0:** ~9 tests (5 already exist and must stay green; 4 are new or need extension)

---

### P1 (High)

**Criteria:** Important features + Medium risk (3-4) + Common workflows + Workaround exists but difficult

| Test ID | Requirement | Test Level | Risk Link | Notes |
| --- | --- | --- | --- | --- |
| **P1-001** | `keys list`/`audit` output never contains a raw secret value | Meta (existing: `test_keys_plaintext_secret_scan.py`) | R-5 | NFR-7; confirm every CI matrix cell |
| **P1-002** | `pyforge.steward` never imports `pyforge.marshal` or another station's internals | Meta (NEW) | R-2 | Models AD-5's boundary as an enforced invariant |
| **P1-003** | `steward budget check` returns three distinct, correctly-differentiated exit codes | Conformance (existing: `test_budget_check.py` — confirm assertion depth) | R-17 | Not-configured vs. under vs. over must be distinguishable programmatically |
| **P1-004** | Fresh-clone verb reaches validate-fast on a real (no prior cache) machine, not only in a unit-level simulation | CI job on ephemeral runner (NEW, infra-level) | R-8 | Existing `test_fresh_clone_class_path.py` stays as the unit-level companion, not a replacement |
| **P1-005** | Estate Redis deployment separates cache instance from CloudEvents-broker instance | Architecture confirmation + config review (not a pytest case) | R-12 | Documentation/config-review task |
| **P1-006** | BMAD-core upgrade preflight, apply, reconcile, pin-fan-out, native-path spot-check, and prove-landed all stay green | Unit (existing: six `test_upgrade_*.py` modules) | R-13 (baseline) | Keep as regression floor beneath the P0-006 extension |
| **P1-007** | `steward provision --verify` / sync-gate check stays accurate as pixi.toml evolves | Conformance (existing: `test_provision_verify.py`, `test_sync_config.py`) | (NFR-3 general reliability) | Regression floor, not risk-specific |
| **P1-008** | `steward deploy dashboard` reconciled push performs zero commits on a no-diff run | Conformance (existing: `test_deploy_dry_run.py`, `test_deploy_reconcile.py`) | (AD-4's testable consequence, FR-9/SM-2) | Regression floor |
| **P1-009** | `steward keys rotate` re-encrypts affected secrets and retires the old identity cleanly | Conformance (existing: `test_keys_rotate.py`) | (FR-3) | Regression floor |
| **P1-010** | Suite-pipeline truth and wired-class predicates hold across the 18-module roster | Unit (existing: `test_suite_pipeline_truth.py`, `test_suite_wired_class_predicates.py`) | (feeds R-10's readiness gate) | Regression floor underneath P0-005 |
| **P1-011** | Adoption register / first-portal-slice provisioning stays correct | Meta (existing: `test_adoption_register.py`, `test_first_portal_slice_provision_list.py`) | (Epic 31/32 general reliability) | Regression floor |

**Total P1:** ~11 tests (9 already exist as regression floor; 2 are new)

---

### P2 (Medium)

**Criteria:** Secondary features + Low risk (1-2) + Edge cases + Regression prevention

| Test ID | Requirement | Test Level | Risk Link | Notes |
| --- | --- | --- | --- | --- |
| **P2-001** | Base install (`[dashboard]` extra absent) never imports Django at module level | Meta (NEW, skeleton above) | R-15 | |
| **P2-002** | `age` version pin stays within the declared `>=1.3.1,<1.4` range and the `(devel)` version-string workaround still holds | Manual/monitoring (no new pytest case) | R-18, R-19 | Revisit only on upstream `age` release |
| **P2-003** | Query-plane read path meets a staleness/latency budget | k6 or equivalent (blocked on R-7's Architecture dependency) | R-7 | Cannot be written until a threshold exists |
| **P2-004** | Deploy status accurately reports last successful dashboard deploy from Git history | Conformance (existing: `test_deploy_status.py`) | (FR-11) | Regression floor |
| **P2-005** | Environment/module provisioning inventory and partial-install-is-named-failure behavior | Conformance (existing: `test_provision_list.py`, `test_provision_list_modules.py`, `test_provision_module.py`, `test_provision_module_installers.py`) | (FR-14, FR-19..21) | Regression floor |
| **P2-006** | Five-tier roster check and skf domain-skill/persona invariants hold | Meta (existing: `test_five_tier_check.py`, `test_skf_domain_skills.py`, `test_skf_steward_skill.py`, `test_station_persona.py`, `test_steward_persona.py`) | (Epic 29/33 general reliability) | Regression floor |
| **P2-007** | Workspace repo-set status/teardown reports and tears down safely | Unit (existing: `test_workspace_repo_set_status_teardown.py`) | (Epic 13, Story 13.4) | Regression floor |
| **P2-008** | Restore and revoke duties behave per their documented contract | Unit (existing: `test_restore_duty.py`, `test_revoke_duty.py`) | (FR-6, general reliability) | Regression floor |
| **P2-009** | Deploy-profile plugin registration (CAP-18 plugin seam, Story 32.2) resolves correctly | Unit (existing: `test_deploy_profile_plugins.py`) | (Epic 32 general reliability) | Regression floor |

**Total P2:** ~9 tests (8 already exist as regression floor; 1 blocked-new)

---

### P3 (Low)

**Criteria:** Nice-to-have + Exploratory + Performance benchmarks + Documentation validation

| Test ID | Requirement | Test Level | Notes |
| --- | --- | --- | --- |
| **P3-001** | Bootstrap/setup flow completes end-to-end on a clean checkout | Conformance/Unit (existing: `test_bootstrap_setup_flow.py`, `test_bootstrap.py`, `test_bootstrap_setup.py`) | Exploratory regression floor |
| **P3-002** | Deploy static/perimeter and ledger-refusal edge cases | Conformance (existing: `test_deploy_static.py`, `test_deploy_perimeter.py`, `test_deploy_ledger_refusal.py`) | Edge-case regression floor |
| **P3-003** | Dashboard audit/cache/navigation/export/filtering/middleware/views unit coverage stays green | Unit (existing: 7 `test_dashboard_*.py` modules not otherwise cited above) | Broad regression floor for the `[dashboard]` extra |
| **P3-004** | Provision install-class playbook and fresh-clone class-path stay correct as new install classes are added | Unit (existing: `test_provision_install_class_playbook.py`, `test_fresh_clone_class_path.py`) | Documentation-adjacent — class-path correctness is largely a naming/registration concern |
| **P3-005** | `age`/PyYAML dependency floors stay pinned and byte-identical between `pyproject.toml` and root `pixi.toml`'s `[feature.pyforge-steward.dependencies]` | Meta (existing, per the spine's own pin-sync test note in `pyproject.toml`'s comments — likely `test_invariants.py`) | Confirm this specific pin-sync assertion is present in `test_invariants.py` |

**Total P3:** ~5 tests (all already exist as regression floor)

---

## Execution Strategy

**Philosophy:** This package's existing suite already runs fast and offline (`pixi run -e pyforge-steward pyforge-steward-test`, no live network by default). Run everything in PRs; nothing here needs nightly/weekly deferral at current scale.

### Every PR: pytest (`unit` + `conformance` + `meta`)

**All functional tests** (from any priority level):

- All 67 existing tests plus the ~5 newly-recommended tests (R-2, R-6, R-10, R-15, and the extended R-9/R-13 cases), run via `pixi run -e pyforge-steward pyforge-steward-test`.
- Total: ~72 tests once the new ones land (includes P0, P1, P2, P3).

**Why run in PRs:** The suite is already fast, offline, and CI-integrated; no expensive infrastructure is implicated by anything in this package's own test tier.

### Manual/Periodic: The Two Drill-Shaped Items

- **R-14's Epic 44 archive-restore rehearsal** — not a pytest case; a scheduled drill against a throwaway clone, run once before Story 44.3 executes, and re-run if the archive mechanism changes.
- **R-3's dashboard isolation canary run** — a deliberate manual mutation (temporarily disable isolation, confirm the suite fails) run once per new `[dashboard]` adopter, not on every PR.

**Why defer these two:** Both are one-time or adopter-triggered validations of a *mechanism's own correctness*, not regression tests of ongoing behavior — running them on every PR would be wasted effort; running them never would leave R-3 and R-14 unverified in practice.

### Blocked, Not Scheduled: R-7's Performance Probe

- No k6-or-equivalent test exists yet because no threshold exists to test against. Once Architecture declares a query-plane SLO, this becomes a nightly (not per-PR) job given the likely need for a live estate-cache read.

---

## QA Effort Estimate

**QA test development effort only** (excludes DevOps, Backend, Data Eng work already reflected in the architecture doc's mitigation owners):

| Priority | Count | Effort Range | Notes |
| --- | --- | --- | --- |
| P0 | ~9 (4 new/extended) | ~8-14 hours | Mostly extending existing, well-structured test modules; R-14's drill is a rehearsal, not code |
| P1 | ~11 (2 new) | ~4-8 hours | One new meta test (import boundary) + one new CI-infra job (fresh-clone ephemeral runner) |
| P2 | ~9 (1 new, 1 blocked) | ~2-4 hours | Mostly confirming existing regression floor stays green |
| P3 | ~5 (0 new) | ~1-2 hours | Confirmation-only pass over existing tests |
| **Total** | ~34 | **~15-28 hours** | **Substantially smaller than a from-scratch suite — 67 of ~72 target tests already exist** |

**Assumptions:**

- Excludes the Epic 34/36 performance probe (R-7), which cannot be estimated until Architecture declares a threshold.
- Excludes ongoing maintenance (~10% effort, per convention).
- Assumes the existing `pyforge-steward-test` pixi task remains the CI entrypoint (no new test-runner infrastructure needed).

**Dependencies from other teams:**

- See "Dependencies & Test Blockers" section for what QA needs from Architecture (query-plane SLO) and Dev (container/manifest artifact paths for R-6).

---

## Implementation Planning Handoff

| Work Item | Owner | Target Milestone | Dependencies/Notes |
| --- | --- | --- | --- |
| R-6 container/manifest secret-reference scan | Dev | Before next container-build story | Needs build-artifact path from Dev |
| R-2 cross-station import-boundary meta test | Dev | Next provisioning-adjacent story | Self-contained, no external dependency |
| R-9 baseline-drift sync scenario | Dev/QA | Before Epic 8 resumes (8.4/8.5) | Extend existing `test_sync_reconcile_propagation.py` |
| R-10 readiness-gate negative-path test | QA | Before Epic 44 cutover flag flips | Self-contained |
| R-13 shim-retirement coverage confirmation/extension | Dev | Story 14.9/14.10 | Confirm first before assuming a gap |
| R-14 archive-restore rehearsal drill | Steward/Marshal | Before Story 44.3 executes | One-time drill, not a pytest case |
| R-15 base-install isolation meta test | Dev | Before next unified-container story | Self-contained, skeleton provided above |
| R-8 ephemeral-runner fresh-clone CI job | QA/DevOps | Opportunistic | Infra-level, needs a no-cache runner |

---

## Interworking & Regression

**Services and components impacted by this feature:**

| Service/Component | Impact | Regression Scope | Validation Steps |
| --- | --- | --- | --- |
| **`pyforge-core` (shared hook-spec/plugin registration, CAP-18)** | Steward's deploy-profile adapters and suite-install duties register against it | `test_deploy_profile_plugins.py`, `test_suite_wired_class_predicates.py` must stay green | Run alongside `pyforge-core`'s own conformance suite when either changes |
| **The Canopy host (`src/platform/`) / secure-dashboard pattern (Epic 9)** | Steward's `[dashboard]` extra is the adopter surface for Atlas's Vizro board | `test_dashboard_*.py` (11 modules) | Re-run the full dashboard unit suite whenever the Canopy host's ASGI/Channels stack changes |
| **Marshal's worktree/loop machinery** | Steward's `provision --runner bmad-loop` reports (never delegates) to `marshal init` | `test_provision_runner.py` | Confirm the reporting-not-delegating boundary (R-2) whenever Marshal's own `marshal init` contract changes |
| **The estate PostgreSQL substrate (Epic 41)** | DR/backup contract scope question (is `.steward/` included?) | None currently — open question | Resolve the scope question, then add coverage if `.steward/` is in-contract |

**Regression test strategy:**

- The existing 67-file `unit`/`conformance`/`meta` suite is the regression floor; every P0-P3 test above either extends it or confirms it.
- Cross-team coordination needed: `pyforge-core` and the Canopy host's own release cadence should trigger a re-run of Steward's plugin-seam and dashboard-extra tests respectively, per the table above.

---

## Tooling & Access

| Tool or Service | Purpose | Access Required | Status |
| --- | --- | --- | --- |
| `pixi run -e pyforge-steward pyforge-steward-test` | Existing test runner (unit/conformance/meta) | None (local) | Ready |
| `pixi run -e local-recipes bmad-drift-check` | Confirms this test-design pass doesn't introduce architecture-doc drift | None (local) | Ready |
| A throwaway clone environment for the Epic 44 rehearsal drill (R-14) | Rehearse archive-restore before real cutover | Local disk + Git, no special access | Pending (schedule the drill) |
| Container/Helm manifest build artifacts (R-6) | Input to the new secret-reference scan | Dev must expose build output path | Pending |

**Access requests needed:**

- [ ] Confirm the container/Helm build pipeline exposes an inspectable artifact path for R-6's scan test.

---

## Appendix A: Code Examples & Tagging

**Stack note:** `pyforge-steward` is a Python CLI + backend package (pytest, not Playwright/TypeScript) — the workflow's default Playwright-tagged examples do not fit this codebase. The one real Playwright surface in the estate is the Canopy dashboard's own e2e/ARIA suite (`pixi run -e local-recipes dashboard-dryrun`), which is owned by the dashboard host, not this package. Examples below use pytest markers, matching the actual `unit`/`conformance`/`meta` tier convention already in the codebase.

**pytest markers for selective execution (recommended, matching existing `slow` marker convention noted in the architecture spine):**

```python
import pytest

# P0 critical test — mirrors the existing conformance-tier convention
@pytest.mark.p0
def test_jfrog_cross_host_leak_stays_closed(ungated_jfrog_auth_fixture):
    """FR-7 regression: a credential attached for host A must never attach
    to a request bound for host B."""
    result = ungated_jfrog_auth_fixture.attempt_cross_host_attach()
    assert result.attached is False
    assert result.reason == "host-scope-mismatch"


# P1 test — extends the existing sync reconciliation suite (R-9)
@pytest.mark.p1
def test_zero_loop_guard_holds_under_baseline_drift(sync_fixture):
    """AD-5 (jira-github spine): the zero-loop guard compares values
    against a baseline, not the live conflict rule — verify it still
    prevents a loop when the baseline itself has drifted."""
    sync_fixture.seed_drifted_baseline()
    result = sync_fixture.run_reconcile_cycle()
    assert result.loop_detected is False
    assert result.propagation_count == 1
```

**Run specific tiers/markers:**

```bash
# Run the full existing suite (unit + conformance + meta)
pixi run -e pyforge-steward pyforge-steward-test

# Run only P0-marked tests, once markers are adopted
pixi run -e pyforge-steward python -m pytest -m p0 src/shared/packages/pyforge-steward/tests/

# Run only the CLI-contract tests (FR-level behavioral contracts).
# These were tests/conformance/ until 2026-09-07; that tier folded into tests/unit/
# under marshal Story 32.5 (spec-fleet-consistency-standard CAP-2) because this
# station's own test-architecture.md already classified them as unit level and the
# fleet coverage gate recognised no tier by that name -- so none of the 32 was measured.
pixi run -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/
```

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` - Risk scoring methodology
- **Test Priorities Matrix**: `test-priorities-matrix.md` - P0-P3 criteria
- **Test Levels Framework**: `test-levels-framework.md` - Unit vs. Conformance vs. Meta selection (this package's own tier convention, mapped onto the generic E2E/API/Unit framework)
- **Test Quality**: `test-quality.md` - Definition of Done (no hard waits, isolation, green criteria)
- **ADR Quality Readiness Checklist**: `adr-quality-readiness-checklist.md` - 8-category testability/NFR audit frame used in the companion architecture document's Testability Concerns section

---

**Generated by:** BMad TEA Agent
**Workflow:** `bmad-testarch-test-design`
**Version:** 4.0 (BMad v6)
