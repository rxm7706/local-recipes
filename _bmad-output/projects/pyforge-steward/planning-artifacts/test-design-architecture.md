---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-secure-live-dashboards-2026-08-09/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-jira-github-projects-sync-2026-08-09/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-unified-container-2026-08-09/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-python-foundry-cutover-2026-09-04/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-bmad-suite-lifecycle-2026-09-06/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/*.py (module inventory, read directly)'
  - 'src/shared/packages/pyforge-steward/tests/{unit,conformance,meta}/*.py (test inventory, read directly)'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/risk-governance.md'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/probability-impact.md'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/nfr-criteria.md'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/adr-quality-readiness-checklist.md'
  - '.claude/skills/bmad-testarch-test-design/resources/knowledge/test-levels-framework.md'
---

# Test Design for Architecture: pyforge-steward (system-level)

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by Architecture/Dev teams. Serves as a contract between QA and Engineering on what must be addressed before test development begins.

**Date:** 2026-09-07
**Author:** BMad TEA Agent (autonomous run, headless — no human elicitation; Rxm7706's `communication_language`/`document_output_language` = English carried from `_bmad/custom/config.toml` `[core]`)
**Status:** Architecture Review Pending
**Project:** pyforge-steward
**PRD Reference:** `_bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md` (FR-1..FR-31, NFR-1..NFR-7) — plus `prd-pyforge-unifying-strategy-2026-08-24` and `prd-bmad-suite-lifecycle-2026-09-06` for the Canopy/estate epics Steward's package now also carries (see § Scope below)
**ADR Reference:** `architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` (AD-1..AD-9, CLI-package authoritative spine) plus six companion spines (§ Executive Summary)

---

## Executive Summary

**Scope:** `pyforge-steward` began as a four-duty CLI (`keys` / `deploy` / `provision` / `budget`, FR-1..18) but its package (`src/shared/packages/pyforge-steward/`) has since absorbed the wielding surface for the entire estate: 47 epics / 190 stories in `epics.md`, and an as-built module roster that grew from 4 duty adapters to **18** (`bootstrap`, `budget`, `cli`, `deploy`, `deploy_profiles`, `five_tier`, `fresh_clone`, `interfaces`, `keys`, `provision`, `restore`, `revoke`, `suite`, `suite_advance`, `sync`, `upgrade`, `workspace`, plus the `dashboard/` optional-extra subpackage). This test design covers the package as a system: the original CLI-package spine (AD-1..AD-9) remains authoritative for the dispatcher/duty-protocol shape, and six companion spines govern the epics layered on top (secure live dashboards, jira-github sync, unified container, the pyforge-unifying-strategy Canopy, the python-foundry cutover, and the bmad-suite lifecycle).

**Business Context** (from PRD):

- **Problem:** Two dated real incidents motivate the CLI's existence — a `JFROG_API_KEY` cross-host credential leak (FR-7) and a wholly manual `dashboard-gen` + push workflow (FR-8..11). The station is now also the sole writer of suite-installed BMAD skills and the readiness gate for the estate's own cutover (Epics 46/47).
- **Revenue/Impact:** No live cloud spend exists to meter yet (PRD §5 non-goal) — `budget` is a declared-not-enforced honest signal, not a cost-control system. Operational impact is instead measured in incident-recurrence prevention (SM-1) and manual-process elimination (SM-2/SM-3).
- **GA Launch:** No fixed date; delivery is continuous per-epic (sprint-status-ledger.yaml tracks 190 stories across 47 epics, most `done`).

**Architecture** (from ADR):

- **Key Decision 1:** Hexagonal ports-and-adapters — `cli.py` is the sole driving adapter and sole exit-code owner (AD-7/AD-8); every duty **wraps** an existing external tool rather than reimplementing it (AD-1) — `_http.py`/`age` for keys, `git`/(retired)`dashboard-gen` for deploy, `pixi` for provision, a tracked config file for budget.
- **Key Decision 2:** No standing service anywhere in scope — no secrets-manager server (AD-3), no GitOps controller (AD-4), no automated budget enforcer (AD-6). Steward is a CLI, not a platform daemon, even as its duty count has quadrupled.
- **Key Decision 3:** Cross-station coupling is refused by design (AD-5, AD-9) — Steward reports what another station (Marshal) owns rather than wrapping it, and any new outbound HTTP call is one new row in `_http.py`'s existing override table, never a parallel config mechanism.

**Expected Scale** (from ADR + epics.md):

- Single operator, no multi-tenant surface (PRD §2.2) for the CLI-package core; the estate-facing epics (9, 26, 34, 41, 42) scale to multi-role dashboard viewers and multi-agent MCP callers, governed by the Canopy spine's AD-1..AD-23.
- 18 duty modules, 67 test files (`tests/unit` + `tests/conformance` + `tests/meta`), 190 stories across 47 epics as of this run.

**Risk Summary:**

- **Total risks identified**: 18 (§ Risk Assessment)
- **High-priority (≥6)**: 8 risks requiring documented mitigation before further estate-facing epics land
- **Test effort**: see companion QA document (`test-design-qa.md`) for the coverage plan and estimate

---

## Quick Guide

### 🚨 BLOCKERS - Team Must Decide (Can't Proceed Without)

**Pre-Implementation Critical Path** — these must be resolved (or explicitly accepted) before further estate-facing work builds on top of the affected surfaces:

1. **R-3: Secure-dashboard isolation proofs must stay non-vacuous** — Story 9.6's own acceptance criterion ("a suite that cannot fail is a failing suite") is a testability obligation, not a shipped guarantee; a future duty reusing the dashboard extra must re-run the mutation-proof case, not assume it still holds. (recommended owner: Architecture/QA jointly — the mutation-proof pattern itself needs a periodic re-run trigger, not a one-time pass)
2. **R-9: Jira↔GitHub zero-loop guard is a baseline comparison, not the conflict rule (AD-5, jira-github spine)** — bidirectional sync systems regress into infinite loops when the baseline drifts from the control-plane state; the architecture spine already names this distinction explicitly, meaning the authors anticipated the failure mode but its regression coverage should be confirmed live before Epic 8's remaining stories (8.4/8.5, currently blocked NEEDS-RESPEC) resume. (recommended owner: Backend/Steward)
3. **R-14: python-foundry cutover (Epic 44) repeats a known artifact-loss failure mode** — this repo's own team memory records a near-total loss (13/31 story specs, later fully recovered) during an earlier cross-worktree migration of this exact shape; Epic 44's stories (44.1 capability ledger, 44.12 cutover flag/replay harness, 44.13 memlog fidelity, 44.14 rebuild harness + oracle gate) are the controls, but they are themselves unexercised until the cutover actually runs. (recommended owner: Steward/Marshal — the archive-is-oracle AD-21 needs a rehearsed restore path proven before the flag flips)

**What we need from team:** Confirm each of the three above has a scheduled or already-passing regression before treating the corresponding epic as safe to build further on.

---

### ⚠️ HIGH PRIORITY - Team Should Validate (We Provide Recommendation, You Approve)

1. **R-1: Package scope sprawl raises AD-8's blast radius** — `cli.py` is still the sole exit-code owner across all 18 duties (up from the 4 the AD was written for); recommend a dedicated dispatcher-level test asserting no duty module calls `sys.exit` directly, run once per new duty rather than only at Epic-1 time (implementation phase, owner: Dev).
2. **R-6: Pod specs / image layers must never carry secret values (AD-19 unifying, AD-24 uc:AD-3)** — recommend a `tests/meta` invariant scanning the container build manifest and any Helm/OCP overlay for literal secret material, mirroring the existing `test_keys_plaintext_secret_scan.py` pattern for `keys list` output (implementation phase, owner: Dev/Steward).
3. **R-7: Estate query-plane (Epic 34) and Vizro estate-cache (Epic 36) NFR thresholds are undeclared** — no latency/staleness SLO is written down for the read-only live-attach path (Story 34.1) or the Parquet cache write path (34.2); recommend the architecture team set an explicit staleness budget so `nfr-assess` has something to validate against later (implementation phase, owner: Architecture).

**What we need from team:** Review recommendations and approve (or suggest changes).

---

### 📋 INFO ONLY - Solutions Provided (Review, No Decisions Needed)

1. **Test strategy**: `unit` / `conformance` / `meta` three-tier split (Warden-aligned convention), already populated with 67 test files across 18 duty modules — this design layers a risk-tiered read on top, it does not propose a new tier.
2. **Tooling**: `pytest` (existing), plus the repo's own `bmad_tea_playwright.py` / `tea-playwright-check` pixi task, which independently maintains a mechanical Story Coverage Matrix in `test-architecture.md` — **out of scope for this document** (see Not in Scope, companion QA doc).
3. **Existing regression coverage confirmed present**: FR-7's JFROG_API_KEY pattern (`tests/conformance/fixtures/ungated_jfrog_auth.py` + `test_keys_host_scoping.py`), NFR-7's no-plaintext-secret invariant (`tests/meta/test_keys_plaintext_secret_scan.py`), and all six BMAD-core-upgrade stories (14.1–14.8) each have a dedicated `tests/unit/test_upgrade_*.py` module.
4. **Coverage**: ~34 test scenarios prioritized P0-P3 with risk-based classification (companion QA doc).
5. **Quality gates**: P0 100% / P1 ≥95% pass rate; no OPEN score-9 risk at merge (none identified this pass — highest score found is 6).

**What we need from team:** Just review and acknowledge (we already have the solution).

---

## For Architects and Devs - Open Topics 👷

### Risk Assessment

**Total risks identified**: 18 (0 critical score=9, 8 high-priority score≥6, 7 medium score 3-5, 3 low score 1-2)

#### High-Priority Risks (Score ≥6) - IMMEDIATE ATTENTION

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **R-1** | **TECH** | Package scope sprawl: one CLI dispatcher (`cli.py`) now owns 18 duty adapters spanning secrets, deploy, provisioning, budget, container build, board sync, secure dashboards, platform hosting, multi-repo workspaces, BMAD-core upgrade, and estate lifecycle governance — a single dispatcher regression has estate-wide blast radius (AD-7/AD-8's own 2026-08-26 currency note: "scaled far past the four duties they were written for and held"). | 2 | 3 | **6** | Keep AD-7/AD-8's protocol-conformance test at the dispatcher level, not per-duty; re-run it on every new duty module addition. | Dev | Next duty module added |
| **R-3** | **TECH** | Secure-dashboard isolation proofs (Story 9.6, AD-11/AD-12) are explicitly designed to "fail loudly if isolation is removed" — but a proof suite's non-vacuousness is a property of the suite's own mutation coverage, not a one-time-verified fact; it can silently rot as the dashboard extra is reused by new adopters (Atlas's Vizro board is only the first). | 2 | 3 | **6** | Re-run the mutation-proof case (a deliberate isolation removal must fail the suite) whenever a new adopter integrates the `[dashboard]` extra. | QA | Each new dashboard adopter |
| **R-6** | **SEC** | Secret material could enter image layers or Pod env values directly instead of references — Epic 7 Story 7.3 ("Credentials never enter image layers") and unifying-strategy canopy:AD-19 ("Pod specs carry secret references, never secret values") both name this as a hard invariant, but no `tests/meta` scan of the actual built container/Helm manifest was found in the 67-file test inventory (only `test_dashboard_*` unit tests, which test code paths, not build artifacts). | 2 | 3 | **6** | Add a `tests/meta` invariant scanning the container image's layer history and any rendered Helm/OCP manifest for literal secret values, mirroring `test_keys_plaintext_secret_scan.py`'s pattern. | Dev | Before next container-build story lands |
| **R-9** | **DATA** | Jira↔GitHub Projects bidirectional sync (Epic 8, jira-github spine AD-5) — the zero-loop guard "compares values against a baseline; it is not the conflict rule" (the spine's own wording, meaning the authors deliberately separated the two to avoid a classic bidirectional-sync infinite-loop bug class). Epic 8 is only 1/5 done (8-1 shipped; 8-4/8-5 blocked NEEDS-RESPEC), so the guard's live behavior under baseline drift is unproven at scale. | 2 | 3 | **6** | Confirm `test_sync_reconcile_propagation.py` (present) exercises a baseline-drift scenario, not only a first-sync scenario, before 8.4/8.5 unblock. | Dev/QA | Before Epic 8 resumes |
| **R-10** | **BUS** | bmad-suite lifecycle readiness gate (Epic 46/47, spine AD-8: "readiness is a gate with owners") — a false-positive readiness verdict would greenlight the python-foundry cutover (Epic 44) against a broken suite roster; Story 47.1 names the readiness checklist as "live" but the checklist's own test coverage against a deliberately-broken roster was not found in the test inventory. | 2 | 3 | **6** | Add a negative-path test: readiness gate must FAIL when a known-broken suite member is injected. | QA | Before Epic 44 flag flips |
| **R-13** | **OPS** | BMAD-core upgrade "clobbered custom surfaces" risk (Epic 14, Story 14.3) — the upgrade apply path can silently overwrite team/user customizations; six of eight Epic 14 stories have a dedicated `test_upgrade_*.py` module (preflight, apply, reconcile, pin-fan-out, native-path spot-check, prove-landed), which is strong existing coverage, but 14.9/14.10 (deprecation-shim retirement) postdate this test inventory snapshot and should confirm the same pattern. | 1 | 3 | **3→6*** | Extend the existing `test_upgrade_*` suite to cover 14.9/14.10's shim-retirement path before it ships. *Scored at the higher bound because the existing tests, while strong, do not yet cover the newest two stories. | Dev | Story 14.9/14.10 |
| **R-14** | **DATA** | python-foundry cutover (Epic 44) repeats the shape of a previously-realized incident: this repo's own team memory (`feedback_...` / `project_...` entries) records pyforge-warden losing 13 of 31 story specs during an earlier cross-worktree migration, fully recovered only because session transcripts happened to survive. Epic 44's AD-21 ("the archive is the oracle") and 44.13 ("memlog fidelity") are direct responses to that lesson, but the cutover itself (44.3 "open the foundry" through 44.10 "archive local-recipes") has not yet executed. | 2 | 3 | **6** | Rehearse the restore path (AD-21) against a throwaway clone before the real cutover flag (AD-17, "cutover is a flag, not a date") flips. | Steward/Marshal | Before 44.3 executes |
| **R-16** | **SEC** | MCP transport authorization / agent containment (Epic 42, Stories 42.1 "MCP transport authorization and a streaming proxy," 42.2 "agent rate limits and run bounds") governs every station's exposure surface, including Steward's own `/stations/steward/mcp` — a gap here is a cross-station risk, not a Steward-local one, and its test evidence lives outside this package's own 67-file inventory (in the shared `pyforge-core` hook-spec layer, per Story 32.2's plugin-seam note). | 2 | 3 | **6** | Confirm the shared containment test suite (owned by whichever station hosts `pyforge-core`'s conformance tests) actually exercises Steward's registered duty adapters, not only a generic contract. | Architecture | Before Epic 42 is declared done |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-2 | TECH | AD-5's "report, not delegate" boundary (Steward never imports `pyforge.marshal`) could regress if a future provisioning story reintroduces coupling under time pressure. | 1 | 3 | 3 | A `tests/meta` import-boundary test asserting `pyforge.steward` never imports `pyforge.marshal` (or any other station's internals) would make the boundary self-enforcing rather than convention-only. | Dev |
| R-4 | SEC | FR-7's JFrog cross-host leak pattern is closed by a named regression test — probability is now low precisely because the test exists, but the impact of a silent regression (the test being weakened or deleted) remains critical. | 1 | 3 | 3 | Keep `test_keys_host_scoping.py` + `fixtures/ungated_jfrog_auth.py` in the `conformance/` tier (not `unit/`), which this repo's own convention treats as FR-level and harder to quietly delete. | QA |
| R-5 | SEC | NFR-7 ("credential values never printed") is enforced by `test_keys_plaintext_secret_scan.py`; same low-probability-but-critical-impact shape as R-4. | 1 | 3 | 3 | No new action — confirm this meta test runs in every CI matrix cell, not only the default one. | QA |
| R-7 | PERF | Estate query-plane (Epic 34) and Lane-3 Vizro-over-estate-cache (Epic 36) carry no declared latency/staleness SLO in the epics.md text reviewed — "read-only live attach" (34.1) and "Kedro writes the Parquet cache" (34.2) describe mechanism, not a threshold. | 2 | 2 | 4 | Convert to an explicit NFR once Architecture declares a threshold (see NFR table, Performance row — marked UNKNOWN). | Architecture |
| R-8 | OPS | Fresh-machine "validate-fast" path (Epic 17) is tested by `test_fresh_clone_class_path.py` at the unit level only — a unit test can assert the *logic* that classifies a fresh clone but cannot prove a truly fresh machine reaches green, which is the story's actual promise. | 2 | 2 | 4 | A CI job on an ephemeral runner (no cache reuse) exercising the real `steward` fresh-clone verb would close this testability gap; short of that, document the unit-test's scope limitation explicitly. | QA |
| R-12 | DATA | AD-6 (unifying spine) "Cache ≠ broker" — conflating Redis-as-cache with Redis-as-broker semantics is a well-known distributed-systems failure mode (dropped events under memory pressure, e.g. eviction of a message meant for delivery). | 2 | 2 | 4 | Confirm the estate's Redis deployment uses separate logical instances/DBs for cache vs. CloudEvents-on-Redis-Streams (AD-8 unifying), not one shared instance with one eviction policy. | Architecture |
| R-15 | TECH | Container-build AD-4 (unified-container: "Dashboard imports may not be unconditional at module level") has no explicit test found asserting the base (non-`[dashboard]`) install path never imports Django/Channels at module import time — only functional `test_dashboard_*` unit tests exist, which run inside an environment where the extra IS installed. | 2 | 2 | 4 | Add a `tests/meta` test that imports `pyforge.steward.cli` in a subprocess with the `[dashboard]` extra absent and asserts no ImportError and no Django import in `sys.modules`. | Dev |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
| --- | --- | --- | --- | --- | --- | --- |
| R-17 | BUS | Budget's honest-stub design (AD-6) risks an operator misreading "not configured" as "under budget" if the CLI's three exit codes aren't consulted programmatically. | 1 | 2 | 2 | Monitor — `test_budget_check.py` already exists; confirm its assertions distinguish all three exit codes, not just configured-vs-not. |
| R-18 | OPS | `age` version range (`>=1.3.1,<1.4`) is a narrow range pinned per Warden's NFR-C1 precedent; an upstream `age` 1.4 release would need a deliberate re-pin, not silent drift. | 1 | 2 | 2 | Monitor — this is a Deferred-item-turned-pin, already tracked in the spine's currency reconciliation log. |
| R-19 | TECH | `age` reports version as `(devel)` upstream, so the conda package version is the only pinnable surface — a packaging-tool change could break this workaround silently. | 1 | 2 | 2 | Monitor — already documented in-file per the spine; no new test needed unless the workaround breaks. |

#### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

### NFR Testability Requirements

**Purpose:** Capture what architecture must provide so NFR validation can be automated later. This is planning guidance, not final evidence assessment.

| NFR Category | Threshold / Requirement | Current Design Support | Gap / Decision Needed | Planned Evidence |
| --- | --- | --- | --- | --- |
| Security | NFR-7: credential values never printed under any flag combination; AD-2/AD-9: HTTP credential attachment is host-scoped, routed only through `_http.py`'s existing table; canopy:AD-19 (unifying): Pod specs carry secret *references* only | Supported — `test_keys_plaintext_secret_scan.py` (NFR-7), `test_keys_host_scoping.py` (AD-2); Pod-spec reference-only rule has no found test (R-6) | Gap: no `tests/meta` scan of built container/Helm manifests for literal secret values | Security tests (existing conformance/meta suite) + a new manifest-scan meta test |
| Performance | No explicit SLO found for the estate query-plane (Epic 34) or Vizro estate-cache (Epic 36); Steward's own CLI duties have no stated latency budget (single-operator, interactive-use tool per PRD §2.2) | Partial/unknown — mechanism is described (read-only live attach, Parquet cache write), no threshold | Architecture must declare a staleness/latency budget for the query plane before `nfr-assess` can validate it | k6 or equivalent load probe against the query-plane read path, once a threshold exists |
| Reliability | NFR-1..NFR-6 (no standing secrets service, no standing GitOps controller, provision never invokes pixi at import time, lean deps, sole exit-code ownership, inherited enterprise routing); DR contract (Epic 41 Story 41.1: "DR contract and PostgreSQL backup") | Supported for NFR-1..6 (architectural rules, largely test-covered per module); DR contract's own test evidence is outside this package's 67-file inventory (owned by whichever station hosts the shared PostgreSQL substrate) | Confirm Steward's own duty state (`.steward/*.yaml`, `*.age` files) is included in whatever DR/backup contract 41.1 defines — it is repo-tracked Git content, not a database row, so the DR contract may not currently name it | Backup/restore drill covering `.steward/` alongside the PostgreSQL-backed estate state |
| Maintainability | AD-1 (wrap, never reimplement) as the primary maintainability control; 3-tier test layout (`unit`/`conformance`/`meta`) already established and populated (67 files across 18 modules) | Supported — the tier split is real and load-bearing (FR-7 and NFR-7 both live in the tier the convention intends) | None identified this pass — the drift-detector (`bmad-drift-check`) already tracks pin/count staleness for this station's own architecture docs | Existing `bmad-drift-check` + this package's own pytest suite as CI evidence |

**Unknown thresholds:** Estate query-plane latency/staleness (R-7, converted to a risk above pending an Architecture decision); whether Steward's own `.steward/` dotdir content is in scope for the Epic 41 DR contract.

**Assessment boundary:** Final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after implementation evidence exists.

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS - Architecture Team Must Address**

#### 1. Blockers to Fast Feedback (WHAT WE NEED FROM ARCHITECTURE)

| Concern | Impact | What Architecture Must Provide | Owner | Timeline |
| --- | --- | --- | --- | --- |
| **No declared query-plane latency/staleness SLO** (Epic 34) | `nfr-assess` cannot later validate Performance because no threshold exists to check against (R-7) | A stated staleness budget for the read-only live-attach path and the Parquet-cache write path | Architecture | Before Epic 34/36 is declared complete |
| **Container/Pod secret-reference invariant is unverified by test** (R-6) | A regression here would leak secret material into a durable image layer or manifest — silent until manually audited | A `tests/meta` scan of the actual built container image + rendered Helm/OCP manifest | Dev | Before next container-build story |
| **Isolation proof suites (Story 9.6) need a re-run trigger, not a one-time pass** (R-3) | New dashboard adopters (beyond Atlas's Vizro board) could integrate the `[dashboard]` extra without re-proving isolation holds for their own role model | A documented "new adopter" checklist item: re-run the mutation-proof case | QA | Each new dashboard adopter |

#### 2. Architectural Improvements Needed (WHAT SHOULD BE CHANGED)

1. **Cross-station import boundary is convention-only, not enforced**
   - **Current problem**: AD-5's "report, don't delegate" rule (Steward never imports `pyforge.marshal`) is documented but not asserted by a test; a future story under time pressure could quietly violate it.
   - **Required change**: A `tests/meta` import-boundary test.
   - **Impact if not fixed**: The exact coupling failure mode AD-5 was written to prevent recurs silently.
   - **Owner**: Dev
   - **Timeline**: Next provisioning-adjacent story

2. **Base-install import isolation for the dashboard extra is unverified**
   - **Current problem**: AD-4 (unified-container) requires that Django/Channels imports never happen unconditionally at module level, but the existing `test_dashboard_*` tests all run with the extra installed — none prove the *base* install path stays clean.
   - **Required change**: A subprocess-based `tests/meta` test importing `pyforge.steward.cli` with the extra absent.
   - **Impact if not fixed**: The lean-image tier (uc:AD-2) silently regresses to always requiring the ASGI stack.
   - **Owner**: Dev
   - **Timeline**: Before the next unified-container story

---

### Testability Assessment Summary

**📊 CURRENT STATE - FYI**

#### What Works Well

- ✅ **The `Duty` protocol + sole exit-code ownership (AD-7/AD-8) is real and tested** — `test_duty_protocol.py` and `test_cli.py` exist, and the pattern has held across a 4.5x growth in duty-module count without a documented dispatcher-level regression.
- ✅ **The 3-tier test layout (`unit`/`conformance`/`meta`) is populated, not aspirational** — 67 test files across 18 modules, with the two highest-stakes invariants (FR-7's JFrog regression, NFR-7's no-plaintext-secret rule) both living in the tier the architecture convention intends (`conformance/` and `meta/` respectively).
- ✅ **BMAD-core upgrade risk (a historically painful class of bug — "clobbered custom surfaces") already has dedicated regression coverage**: six `test_upgrade_*.py` modules covering preflight, apply, reconcile, pin-fan-out, native-path spot-checks, and prove-landed.
- ✅ **The architecture spines are self-auditing** — each spine carries dated "Currency reconciliation" sections that re-check the as-built code against the AD text on every cascade pass (e.g., the 2026-08-26 note that caught AD-7/AD-8's scale-past-original-scope on its own, before this test design had to find it independently).

#### Accepted Trade-offs (No Action Required)

For pyforge-steward's current phase, the following trade-offs are acceptable:

- **No automated budget enforcement (AD-6)** — this is a deliberate non-goal (PRD §5); the honest-stub design is the correct answer until real cloud spend exists to meter.
- **`age` version range left narrow, not floor-only** — Deferred-item-turned-pin per Warden's NFR-C1 precedent; revisit only if upstream `age` releases 1.4.
- **CLI command-tree stays flat (no lazy-loading/entry-point plugin architecture)** — the spine's own 2026-08-26 note re-confirms this trigger "has now genuinely fired" for the lazy-loading question at 18 modules, but reports "no problem observed yet" — this is monitored technical debt (folded into R-1 above), not an unaddressed gap.

This is deliberate architectural discipline (the wrap-don't-reimplement doctrine, AD-1) rather than acceptable Phase-1 debt, and should be maintained as-is rather than revisited absent a concrete failure.

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

**Purpose**: Detailed mitigation strategies for all 8 high-priority risks (score ≥6). These risks should be addressed before the corresponding epic is treated as fully hardened.

#### R-1: Package scope sprawl raises AD-8's blast radius (Score: 6) - HIGH

**Mitigation Strategy:**
1. Keep the dispatcher-level `Duty`-protocol-conformance test (already present as `test_duty_protocol.py`) in the required-pass set for every PR touching any duty module, not only `cli.py` itself.
2. Add a lightweight checklist item to the "new duty module" convention: run `test_duty_protocol.py` + `test_cli.py` explicitly and confirm the new module's `run()` never calls `sys.exit`.
3. Revisit the Deferred lazy-loading/entry-point question only if a second dispatcher-level regression is observed (evidence-driven, per the spine's own stated policy).

**Owner:** Dev
**Timeline:** Ongoing (next duty module addition)
**Status:** Planned
**Verification:** `test_duty_protocol.py` and `test_cli.py` both green on every duty-module PR.

---

#### R-3: Secure-dashboard isolation proofs need a re-run trigger (Score: 6) - HIGH

**Mitigation Strategy:**
1. Document, in the secure-live-dashboards spine or its adopter checklist, that Story 9.6's mutation-proof case must be re-run (not merely re-read) whenever a new adopter integrates `[dashboard]`.
2. Confirm `test_dashboard_isolation_proof.py` (present in the unit tier) actually contains a deliberate isolation-removal mutation, not only a positive-path assertion.
3. Track adopters in one place (currently: Atlas's Vizro board) so "each new adopter" has a concrete trigger list.

**Owner:** QA
**Timeline:** Each new dashboard adopter (immediate: confirm for Atlas)
**Status:** Planned
**Verification:** `test_dashboard_isolation_proof.py` fails when the isolation check is manually disabled (a canary run), confirming the suite is not vacuous.

---

#### R-6: Secret material could enter image layers or Pod specs (Score: 6) - HIGH

**Mitigation Strategy:**
1. Add a `tests/meta` test that builds (or inspects a cached build of) the container image and scans layer history for literal secret-shaped strings.
2. Add a parallel check for any rendered Helm/OCP manifest (Epic 12) asserting only `secretKeyRef`/reference-shaped fields, never inline values.
3. Model the new test after `test_keys_plaintext_secret_scan.py`'s existing pattern rather than inventing a new scanning approach.

**Owner:** Dev
**Timeline:** Before the next container-build or Helm-chart story lands
**Status:** Planned
**Verification:** New meta test fails when a canary secret value is deliberately injected into a manifest fixture.

---

#### R-9: Jira↔GitHub zero-loop guard under baseline drift (Score: 6) - HIGH

**Mitigation Strategy:**
1. Review `test_sync_reconcile_propagation.py`'s existing scenarios; confirm at least one exercises a baseline that has drifted from current control-plane state (not only first-sync/no-baseline).
2. If absent, add a baseline-drift scenario before Epic 8's blocked stories (8.4/8.5) are unblocked.
3. Cross-check against AD-6 ("unmapped values fail loud; unlinked items fail alone") to ensure the drift scenario doesn't silently swallow an unmapped-value case.

**Owner:** Dev/QA
**Timeline:** Before Epic 8 resumes (8.4/8.5 currently NEEDS-RESPEC)
**Status:** Planned
**Verification:** A new/confirmed test demonstrates the guard prevents a loop even when the baseline is stale relative to both synced systems.

---

#### R-10: bmad-suite readiness gate could false-positive (Score: 6) - HIGH

**Mitigation Strategy:**
1. Add a negative-path test to the readiness-checklist suite: inject a known-broken suite member (e.g., a missing pin or an unwired install class) and assert the gate reports NOT-READY.
2. Confirm Story 47.1's "live" readiness checklist is exercised by this negative test, not only demonstrated positively against the current (healthy) roster.

**Owner:** QA
**Timeline:** Before Epic 44's cutover flag flips
**Status:** Planned
**Verification:** Readiness gate returns a failing verdict against the injected-broken fixture.

---

#### R-13: BMAD-core upgrade shim-retirement path (Stories 14.9/14.10) lacks confirmed coverage (Score: 3→6\*) - HIGH

**Mitigation Strategy:**
1. Confirm whether `test_upgrade_*.py`'s existing six modules already cover 14.9/14.10's shim-retirement behavior (this test design's file-listing pass found the six modules but did not open each one to confirm story-level coverage).
2. If not covered, extend the existing suite rather than starting a new one — the pattern (preflight → apply → reconcile → prove-landed) already fits shim retirement.

**Owner:** Dev
**Timeline:** Story 14.9/14.10 (per epics.md, these exist as of this run)
**Status:** Planned
**Verification:** A new or extended `test_upgrade_*` case demonstrates a stale shim is removed on apply and the removal is proven, not merely attempted.

---

#### R-14: python-foundry cutover repeats a known artifact-loss failure mode (Score: 6) - HIGH

**Mitigation Strategy:**
1. Rehearse the AD-21 "archive is the oracle" restore path against a throwaway clone before Epic 44's cutover flag (AD-17) flips for real.
2. Confirm Story 44.13 ("memlog fidelity") and 44.14 ("rebuild harness and oracle gate") both have passing evidence *before* 44.3 ("open the foundry") executes, not concurrently with it.
3. Cross-reference this repo's own recorded incident (pyforge-warden's 13/31 story-spec loss, recovered via session transcripts) as the concrete failure mode the rehearsal must rule out.

**Owner:** Steward/Marshal
**Timeline:** Before Story 44.3 executes
**Status:** Planned
**Verification:** A rehearsal restore from the archive produces byte-identical (or explicitly reconciled) content versus the pre-cutover tree.

---

#### R-16: MCP transport authorization is a cross-station surface (Score: 6) - HIGH

**Mitigation Strategy:**
1. Identify which station's test suite actually exercises Epic 42's shared containment contract against Steward's own registered duty adapters (likely `pyforge-core`'s conformance tests, per the Story 32.2 plugin-seam note).
2. Confirm that suite includes at least one Steward-specific case, not only a generic cross-station contract test.
3. If no Steward-specific case exists, this is an Architecture-level gap to close before Epic 42 is declared done, not a Steward-local fix.

**Owner:** Architecture
**Timeline:** Before Epic 42 is declared done
**Status:** Planned
**Verification:** A Steward-specific MCP-transport-authorization test exists and is green in whichever suite owns it.

---

### Assumptions and Dependencies

#### Assumptions

1. The `test-architecture.md` baseline (mechanically generated by `_bmad/scripts/bmad_tea_playwright.py`, wired to the `tea-playwright-check` pixi task) is a separate, deterministic artifact serving a different purpose (a story-ID-to-test-file drift check) and is not superseded or duplicated by this document.
2. `epics.md`'s "done" markers in `sprint-status-ledger.yaml` are trusted as of this run's read; no live CI status was independently re-verified.
3. Story 46.3 (TEA's own provisioning, the story this test-design run implements) is itself out of scope for self-assessment in this document — it produced the workflow being executed, not a risk subject of it.

#### Dependencies

1. Epic 42's shared MCP-containment test suite (owned outside this package) — required to close R-16.
2. Architecture's declaration of a query-plane staleness/latency threshold — required to close R-7.
3. A rehearsed Epic 44 restore drill — required to close R-14 before the real cutover.

#### Risks to Plan

- **Risk**: This document's risk register, built from a single read-through of 47 epics' headers plus 8 architecture spines' AD inventories, may have missed a risk that only a full per-story AC read would surface.
  - **Impact**: A real risk ships unassessed.
  - **Contingency**: The companion QA document's coverage plan defers full P2/P3 scenario enumeration to implementation time, when each story's own AC is read in full; this document's job is the system-level shape, not exhaustive story coverage (that remains `test-architecture.md`'s mechanical job, and the epic-level mode of this same TEA workflow, run per-epic, for anything needing deeper drill-down).

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Review Quick Guide (🚨/⚠️/📋) and prioritize the three blockers.
2. Assign owners and timelines for the eight high-priority risks (≥6).
3. Validate assumptions and dependencies.
4. Provide feedback to QA on testability gaps (R-3's re-run trigger and R-15's base-install isolation test in particular).

**Next Steps for QA Team:**

1. Refer to the companion QA doc (`test-design-qa.md`) for the P0-P3 test scenario breakdown.
2. Confirm the five "existing coverage found" claims in this document (FR-7, NFR-7, Epic 14 upgrade suite, Duty protocol, dashboard isolation) by running the named test files, not only trusting the file listing.
3. Begin closing the three testability gaps this document could not resolve by inspection alone (R-6's manifest scan, R-15's base-install isolation test, R-2's import-boundary test).
