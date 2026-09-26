---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - 'prds/prd-pyforge-marshal-2026-07-25/prd.md'
  - 'architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
  - 'epics.md'
  - 'test-architecture.md'
---

# Test Design for Architecture: pyforge-marshal (system-level)

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by the
Architecture/Dev side of the Marshal station. Serves as a contract between QA and Engineering on
what must be addressed before further test development proceeds.

**Date:** 2026-09-07
**Author:** Master Test Architect (bmad-testarch-test-design)
**Status:** Architecture Review Pending
**Project:** pyforge-marshal
**PRD Reference:** `prds/prd-pyforge-marshal-2026-07-25/prd.md` (FR-1..FR-195)
**ADR Reference:** `architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md` (AD-1..AD-80)

---

## Executive Summary

**Scope:** System-level test architecture for pyforge-marshal — the deterministic, LLM-free
orchestration CLI that wraps `bmad-loop` (loop-home provisioning, run supervision, gate
evaluation, landing/deploy, fleet status, adapter portability, policy composition) plus the
`marshal seed` model-installer satellite (Part II of the architecture) and the `pyforge-core`
shared floor (Part III). 37 epics / 208 stories are already decomposed and largely shipped
(the station's own `test-architecture.md` reports 208 stories parsed, 181 test files inventoried).

**Business Context** (from PRD):

- **Problem:** every BMAD-loop run today depends on conversational discipline inside the agent
  session (budget ceilings, escalation, no destructive git ops) — discipline that "does not
  survive context compaction" per the PRD's own grounding note. Marshal exists to make those
  limits structural instead of conversational (NFR-5).
- **Revenue/Impact:** not a revenue system; the metric that matters is fleet trust — whether an
  unattended run's PASS verdict, durability claim, and landing can be believed without re-reading
  the transcript.
- **GA Launch:** no fixed date; the station is iterating past its original MVP into Epics 25-31
  (BMAD-era alignment, token economy, TEA cutover).

**Architecture** (from AD-1..AD-80):

- **Key Decision 1 (AD-1/AD-2):** Marshal is a harness, never a skill — it wraps `bmad-loop`
  rather than absorbing or forking it.
- **Key Decision 2 (AD-5/AD-6):** the run journal is the single source of run truth, and every
  mutating action is write-before-act.
- **Key Decision 3 (AD-9):** the supervisor observes from *outside* the agent session and never
  trusts self-report — the load-bearing trust boundary this whole design exists to defend.
- **Stack:** Python `>=3.12`, argparse CLI, `bmad-loop>=0.11.0,<0.12` as a declared run
  dependency (never vendored), `pyforge-core` as an enforced leaf dependency, `copier>=9.17,<10`
  for the seed engine, `tmux>=3.7b` for the default multiplexer backend.

**Expected Scale** (from architecture / PRD):

- Single-operator fleet scale (this repo's own 8 `pyforge-*` stations + siblings), not
  internet-facing multi-tenant scale. No RPS target; the operative scale variable is *run count
  and duration* (unattended runs can span hours), not request volume.

**Risk Summary:**

- **Total risks identified**: 13 (8 carried forward from the architecture doc's own AR-1..AR-8
  register, re-scored; 5 derived from cross-cutting NFRs/ADs during this review)
- **High-priority (≥6)**: 5 risks requiring immediate/ongoing mitigation attention
- **Test effort**: see companion QA doc (`test-design-qa.md`) for the coverage matrix and
  estimate; this is a brownfield system with 181 existing test files, so the estimate there is
  framed as *gap-closing* effort, not from-zero effort.

---

## Quick Guide

### 🚨 BLOCKERS - Team Must Decide (Can't Proceed Without)

**Pre-Implementation Critical Path** for Epic 31 (TEA replaces the generator):

1. **B-1: The generator's own story→test linkage is not a valid equivalence baseline** — Story
   31.1's acceptance criteria require the TEA equivalence report to show "every story id and
   every live test path the generator emitted present in the TEA output." Inspection of the
   *current* `test-architecture.md` Story Coverage Matrix shows 207 of 208 rows read `none
   observed`; only Story 27.2 has a linked test file. If 31.1 is executed literally against this
   baseline, the bar is nearly vacuous (recommended owner: Marshal/Dev, before 31.1 executes —
   either fix the generator's linkage heuristic first so the baseline is meaningful, or record
   explicitly in 31.1's equivalence report that the comparison set is 1 story, not 208).
2. **B-2: This workflow's templates do not natively produce a per-story matrix** — neither
   `test-design-architecture-template.md`, `test-design-qa-template.md`, nor
   `test-design-handoff-template.md` contains a story-by-story enumeration; the closest construct
   is the handoff doc's *risk-driven* Risk-to-Story Mapping table (populated only for identified
   risks, not every story). If Epic 31 needs an artifact that lists all 208 stories with their
   test files as a drop-in replacement for the generator's Story Coverage Matrix, that is new
   scope for `bmad-testarch-trace` (mentioned in this skill's knowledge base as the coverage-
   completeness workflow), not for `test-design` (recommended owner: Marshal, decide before
   31.2 deletes the generator).
3. **B-3: Contract-testing config is configured but not relevant here** — `tea_use_pactjs_utils`
   and `tea_pact_mcp="mcp"` are enabled fleet-wide in `_bmad/custom/config.toml`, but
   `pyforge-marshal`'s `tests/contract/` directory holds Port/Adapter conformance tests
   (`test_landing_evidence_conformance.py`), not consumer-driven Pact contracts against an
   external HTTP provider. No action needed for Marshal itself, but the fleet-wide default
   should not be read as "Marshal needs Pact" (recommended owner: whoever runs TEA for the next
   station — confirm relevance per-station, not by inheriting this default).

**What we need from team:** Resolve B-1/B-2 before treating Story 31.1's equivalence report as
meaningful; B-3 is informational only.

---

### ⚠️ HIGH PRIORITY - Team Should Validate (We Provide Recommendation, You Approve)

1. **R-2: "Unevaluable is failure" (AD-8) has no negative-path test evidence found in this pass**
   — recommend a dedicated meta-test asserting that a verify-command crash/timeout/ambiguous-exit
   resolves to a FAIL verdict, never PASS-by-default (implementation phase; owner: whoever owns
   `pyforge-marshal/src/.../core` verdict projection, per AD-7 "one owner of the verdict→exit-code
   projection").
2. **R-5: Durability at teardown (AD-13 "promote before teardown", AD-29)** — recommend the
   existing `feedback_stuck_orchestrator_baseline_bug` class of incident (already in this repo's
   own memory) be turned into a standing regression fixture: simulate a kill mid-run and assert
   the journal/promoted artifacts survive, rather than relying on it having been caught once by a
   human (implementation phase; owner: Marshal core).
3. **R-6: Landing-evidence-grammar recognizability (AD-73)** — recommend the real, already-lived
   incident class ("Follow-up-review commits orphan after merge" — see this repo's team memory)
   be encoded as a fixture/regression test (a merge subject that a naive grep would miss but the
   grammar should still recognize), rather than only guarded by code review (implementation
   phase; owner: Marshal core / `marshal land`).

**What we need from team:** Review recommendations and approve (or supply the actual owning
engineer/timeline — this pass could not assign real people).

---

### 📋 INFO ONLY - Solutions Provided (Review, No Decisions Needed)

1. **Test strategy**: Unit + Integration + Meta-test heavy (matches
   `tests/{unit,integration,meta,contract,oracle}/`); no E2E/Playwright layer — this is a CLI/
   library surface, not a UI (`detected_stack = backend`).
2. **Tooling**: pytest is the de-facto framework already in use (`pyforge-marshal-test` pixi
   task); Playwright/Pact utils configured fleet-wide but not exercised for this station.
3. **Tiered CI/CD**: PR (`pyforge-marshal-test`, `detectors-ci`) / Nightly-or-none (no long-
   running perf/chaos suite currently exists for Marshal) — see QA doc Execution Strategy.
4. **Coverage**: 13 risk-driven scenario families prioritized P0-P3 (QA doc), layered on top of
   181 already-existing test files rather than replacing them.
5. **Quality gates**: P0 = 100% pass, high-risk (≥6) mitigations verified before Epic 31's
   generator deletion (31.2), coverage target unchanged from the existing generator's own
   declared targets (unit ≥80%, integration ≥70%, per `test-architecture.md` frontmatter).

**What we need from team:** Just review and acknowledge (we already have the solution).

---

## For Architects and Devs - Open Topics 👷

### Risk Assessment

**Total risks identified**: 13 (5 high-priority score ≥6, 5 medium, 3 low)

#### High-Priority Risks (Score ≥6) - IMMEDIATE ATTENTION

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
|---------|----------|--------------|-----------|--------|-------|------------|-------|----------|
| **R-1** (=AR-1) | **TECH** | Managed-region engine (Epic 8) corrupts a tracked file during a byte-span substitution write | 2 | 3 | **6** | P-06 byte-span substitution + AD-56 conservative anchoring + AD-53 nesting rejection (already designed-in); region unit tests are architecture's own "largest test group" — verify that claim still holds as the suite grows | Marshal core | Ongoing (region engine is Epic 8, already built) |
| **R-2** | **OPS** | A verify-command that crashes, times out, or exits ambiguously is misread as PASS instead of FAIL, violating NFR-3/AD-8 ("unevaluable is failure") | 2 | 3 | **6** | AD-8 is a stated invariant; recommend an explicit adversarial meta-test (crash/timeout/garbage-exit fixtures) rather than trusting normal-path tests to exercise it | Marshal core (verdict projection, AD-7) | Before Epic 31.2 deletes the generator (verdict logic is load-bearing for TEA equivalence too) |
| **R-5** (=AR-6, extended) | **DATA** | State/journal desync at teardown or mid-run kill — "the stuck-orchestrator-baseline bug" already lived once (this repo's own project memory) | 2 | 3 | **6** | AD-13 promote-before-teardown, AD-29 (promotion complete only when durable off the disposable ref), P-08 atomic last-write | Marshal core | Regression fixture recommended before next fleet-wide loop-home refresh (Epic 15/31.5) |
| **R-6** | **TECH** | Landing evidence grammar (AD-73) fails to recognize a legitimate merge, producing ledger drift — already lived once ("Follow-up-review commits orphan after merge") | 2 | 3 | **6** | AD-73's grammar is documented as "one grammar with two consumers"; recommend the lived incident become a permanent fixture, not folklore | `marshal land` owner | Before the next batched-PR landing cadence |
| **R-8** | **PERF/OPS** | Supervisor poll interval exceeds the prompt-cache TTL, converting cheap cache reads into full cache writes — NFR-14 names this explicitly as "the documented mechanism behind the largest circulated cost overrun" | 2 | 3 | **6** | NFR-14 states the target (`poll ≤ 60s`) but marks it `[ASSUMPTION: not independently verified]` | Marshal core | Verify against the harness's actual cache TTL before the assumption is retired |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
|---------|----------|--------------|-----------|--------|-------|------------|-------|
| R-3 | SEC | A credential/token leaks into a journal, gate record, probe record, or PR body (NFR-11) | 1 | 3 | 3 | AD-34 "redaction is a port-boundary property" — centralizes the guard at one seam rather than per-caller discipline | Marshal core |
| R-4 | OPS | The supervisor's outside-observation independence (AD-9/NFR-4) is compromised by something the session itself can influence (e.g. a self-reported status field trusted without cross-check) | 2 | 2 | 4 | AD-9 is explicit that the supervisor "never trusts self-report"; verify no code path re-introduces a trust-the-session shortcut | Marshal core |
| R-7 | OPS | The allowlist-narrowing invariant (AD-27: "an allowlist may only be narrowed by the party it constrains") is violated by a policy layer widening scope it doesn't own | 1 | 3 | 3 | AD-27 + the 4-layer policy composition model (`feedback_policy_composition_four_layer`) | Marshal core / policy layer |
| R-9 (=AR-3) | DATA | The `marshal seed` manifest and repository reality diverge (Part II, Copier-based) | 1 | 3 | 3 | AD-60 idempotence-as-plan-emptiness + SC-02 oracle check in the seeded repo's own CI | Marshal seed owner |
| R-10 (=AR-4) | SEC | A managed-region write escapes the never-write guard | 1 | 3 | 3 | AD-61 symlink-resolved path matching + a dedicated AST meta-test (P-01) | Marshal core |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
|---------|----------|--------------|-----------|--------|-------|--------|
| R-11 (=AR-2) | TECH | Copier API assumptions turn out wrong | 1 | 2 | 2 | Already mitigated pre-build by Spike-0 (`spike-0-copier-api-fit-report.md`) and a single import-site constraint (A-04); residual risk is upstream Copier releases drifting — monitor via the existing range-pin sync test |
| R-12 (=AR-5) | OPS | A stale `marshal seed` plan is applied to a repo that changed underneath it | 1 | 2 | 2 | AD-57 `repo_fingerprint` refusal — monitor |
| R-13 (=AR-8) | BUS | In-package templates couple model releases to package releases | 1 | 2 | 2 | Accepted risk per the architecture doc itself; `--template` (FR-119) is the stated escape valve — monitor, no action owed here |

#### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

### NFR Testability Requirements

**Purpose:** Capture what architecture must provide so NFR validation can be automated later.
Source: PRD § 10 Cross-Cutting Non-Functional Requirements (NFR-1..NFR-14). This is planning
guidance, not final evidence assessment.

| NFR Category | Threshold / Requirement | Current Design Support | Gap / Decision Needed | Planned Evidence |
|---|---|---|---|---|
| Security | NFR-11: no credential/token/key written to journal, gate record, probe output, PR body; redaction at egress | Supported by design (AD-34 redaction at port boundary) | Confirm redaction is enforced at the single seam for *every* egress path, not per-caller | Meta-test asserting no secret-shaped string reaches a written artifact (existing pattern: redaction meta-tests already referenced in team memory) |
| Performance | NFR-14: `init`/`status` complete in seconds; supervisor poll interval never exceeds the harness's prompt-cache TTL | Partial — target stated but marked `[ASSUMPTION: not independently verified]` | Confirm actual cache TTL from the harness and assert poll interval ≤ it, not just ≤ 60s | Timed integration test + a documented TTL cross-check against the installed `bmad-loop` version |
| Reliability | NFR-3 (never false-green) + NFR-7 (idempotence of `init`/`deploy`/`adapters sync`/policy composition) | Supported by design (AD-8 unevaluable-is-failure; AD-21 mutating commands reconcile-then-act) | No adversarial (crash/timeout) test evidence found for NFR-3 in this pass (see R-2) | Adversarial meta-tests for the verdict projection; idempotence re-run tests for each mutating command |
| Maintainability | NFR-9: harness contract tests fail loudly on upstream drift rather than misparsing silently | Supported (AD-78 "the harness era is pinned by installed-package vocabulary tests") | Confirm the vocabulary-pin tests actually fail *loudly* (distinct error, not a swallowed exception) on the next `bmad-loop` minor bump | Contract test suite re-run against the next installed `bmad-loop` release as a canary |

**Unknown thresholds:** NFR-14's `poll ≤ 60s` ceiling and `init/status < 10s` are both marked
`[ASSUMPTION]` in the PRD itself — not guessed here, carried forward as an open item (folded into
R-8 above rather than invented as a hard threshold).

**Assessment boundary:** Final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after
implementation evidence exists — none of the above is a final verdict.

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS - Architecture Team Must Address**

#### 1. Blockers to Fast Feedback (WHAT WE NEED FROM ARCHITECTURE)

| Concern | Impact | What Architecture Must Provide | Owner | Timeline |
|---|---|---|---|---|
| **No adversarial fixture for AD-8 (unevaluable-is-failure)** | Cannot prove the single most load-bearing trust property by test alone | A documented fixture harness that can simulate a crashing/hanging/ambiguous-exit verify-command deterministically | Marshal core | Pre-Epic-31.2 |
| **Generator's own story↔test linkage heuristic (currently non-functional, 207/208 "none observed")** | Blocks a meaningful TEA-vs-generator equivalence check (Epic 31.1) | Either fix the naming-convention match, or explicitly re-scope 31.1's equivalence bar | Marshal / whoever runs 31.1 | Before 31.1 executes |

#### 2. Architectural Improvements Needed (WHAT SHOULD BE CHANGED)

1. **Cache-TTL cross-check for NFR-14**
   - **Current problem**: the poll-interval ceiling is a hardcoded assumption (`≤ 60s`), not
     derived from the installed harness's actual cache TTL.
   - **Required change**: read the TTL from the harness (or its docs/version) and assert the
     poll interval is derived from it, not a fixed constant.
   - **Impact if not fixed**: a harness upgrade that shortens its cache TTL silently reintroduces
     the cost-overrun failure mode NFR-14 exists to prevent.
   - **Owner**: Marshal core.
   - **Timeline**: next harness-era alignment pass (Epic 25/30 pattern).

---

### Testability Assessment Summary

**📊 CURRENT STATE - FYI**

#### What Works Well

- ✅ **AD-5/AD-6** (journal is single source of truth + write-before-act) gives every test a
  single, inspectable ground truth to assert against instead of reconstructing state from
  scattered side effects.
- ✅ **AD-14** (one response envelope for every command) means coverage can be written generically
  against the envelope shape rather than per-command ad hoc parsing.
- ✅ 181 test files already exist across `unit/integration/meta/contract/oracle` — this is a
  brownfield system with real regression coverage already in place, not a green-field testability
  problem.

#### Accepted Trade-offs (No Action Required)

- **AR-8 / R-13 (template-package coupling)** — accepted per the architecture doc itself;
  `--template` is the stated escape valve. No action owed here.
- **No E2E/browser test layer** — correct for a CLI/library surface with no UI; not a gap.

---

### Risk Mitigation Plans (High-Priority Risks ≥6)

#### R-1: Managed-region engine corrupts a tracked file (Score: 6) - HIGH

**Mitigation Strategy:**
1. Confirm region unit tests remain architecture's largest test group as the suite grows (a
   shrinking share would itself be a regression signal).
2. Add or confirm an adversarial case: an anchor that matches twice (AD-53 nesting rejection)
   and a byte-span that overlaps a concurrent edit.
3. Track via the existing `AR-1` risk register entry rather than opening a duplicate.

**Owner:** Marshal core. **Timeline:** ongoing. **Status:** Design mitigations in place;
verification-test currency not independently re-confirmed in this pass.
**Verification:** region-engine test file count and adversarial-case presence, checked at next
retro.

#### R-2: "Unevaluable is failure" has no adversarial test evidence found (Score: 6) - HIGH

**Mitigation Strategy:**
1. Add a fixture that simulates a verify-command crash (non-zero from an unexpected signal).
2. Add a fixture that simulates a timeout.
3. Add a fixture that simulates an ambiguous/garbage exit that isn't cleanly 0 or non-zero.
4. Assert all three resolve to FAIL, never PASS-by-default.

**Owner:** Marshal core (verdict projection, AD-7). **Timeline:** before Epic 31.2 deletes the
generator (this property underpins TEA-equivalence too). **Status:** Not verified in this pass —
recommendation only. **Verification:** the three fixtures above, green.

#### R-5: Journal/state desync at teardown or mid-run kill (Score: 6) - HIGH

**Mitigation Strategy:**
1. Turn the lived "stuck-orchestrator-baseline" incident into a permanent regression fixture
   (kill mid-run, assert promoted artifacts survive).
2. Re-verify AD-29 ("promotion complete only when durable off the disposable ref") against that
   fixture specifically, not just against the happy path.

**Owner:** Marshal core. **Timeline:** before the next fleet-wide loop-home refresh.
**Status:** Incident occurred once and was manually recovered; not yet a standing test.
**Verification:** the kill-mid-run fixture, green, on every future `pyforge-marshal-test` run.

#### R-6: Landing-evidence-grammar recognition gap (Score: 6) - HIGH

**Mitigation Strategy:**
1. Encode the lived "Follow-up-review commits orphan after merge" incident as a fixture: a merge
   subject shaped exactly like that incident's, asserted still recognized by AD-73's grammar.
2. Confirm `tests/contract/test_landing_evidence_conformance.py` already covers this shape; if
   not, extend it rather than opening a new file.

**Owner:** `marshal land` owner. **Timeline:** before next batched-PR landing cadence.
**Status:** Not independently confirmed in this pass whether the existing conformance test
already covers this exact incident shape.
**Verification:** the fixture, green, plus a manual read of `test_landing_evidence_conformance.py`
to confirm no duplicate is being created.

#### R-8: Supervisor poll interval vs. cache TTL (Score: 6) - HIGH

**Mitigation Strategy:**
1. Retire the `[ASSUMPTION]` in NFR-14 by reading the harness's actual cache TTL rather than
   hardcoding 60s.
2. Add a test asserting the configured poll interval is derived from (not merely less than a
   constant approximating) that TTL.

**Owner:** Marshal core. **Timeline:** next harness-era alignment pass.
**Status:** Assumption stands, unverified.
**Verification:** the derived-poll-interval test, green, against the currently pinned
`bmad-loop>=0.11.0,<0.13`.

---

### Assumptions and Dependencies

#### Assumptions

1. This review treats the marshal-specific PRD/architecture (`prds/prd-pyforge-marshal-2026-07-25/`,
   `architecture/architecture-pyforge-marshal-2026-07-25/`) as the system-level source of truth
   for pyforge-marshal, not the umbrella `PRD.md`/`architecture.md` at the planning-artifacts
   root (which cover the whole 5-part `local-recipes` rebuild and predate the per-project split).
2. NFR-14's numeric targets (`<10s`, `≤60s`) are carried as stated assumptions, not independently
   re-measured in this pass.
3. `test_stack_type` was auto-detected as `backend`; no manual override was supplied.

#### Dependencies

1. Steward Story 46.3 (TEA provisioning) — required before this workflow could run at all; already
   satisfied (this run is evidence of that).
2. Epic 31's equivalence-report work (31.1) depends on either fixing or re-scoping the generator's
   story↔test linkage heuristic (see B-1) before its acceptance criteria can be met meaningfully.

#### Risks to Plan

- **Risk**: This run skimmed the knowledge-base fragments for headings/rubric rather than reading
  them end-to-end, and executed sequentially rather than via subagents/an agent-team for parallel
  drafting.
  - **Impact**: Depth is representative, not exhaustive — coverage of all 37 epics/208 stories was
    not attempted; only the highest-signal risks were carried through to full mitigation plans.
  - **Contingency**: A future re-run of this workflow against Marshal should re-derive risks
    against the full knowledge base for broader coverage; the current risk register and mitigation
    plans stand as this pass's real output in the meantime.

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Review Quick Guide (🚨/⚠️/📋) and prioritize B-1/B-2/B-3.
2. Assign real owners and timelines for the 5 high-priority risks (≥6) — this pass could not
   assign actual engineers.
3. Validate assumptions and dependencies (especially assumption 1: which PRD/architecture is
   authoritative for Marshal).
4. Provide feedback to QA on testability gaps (adversarial fixtures for AD-8, AD-73).

**Next Steps for QA Team:**

1. Wait for B-1/B-2 to be resolved before treating any TEA/generator equivalence claim as final.
2. Refer to companion QA doc (`test-design-qa.md`) for the coverage matrix and test scenarios.
3. Begin test infrastructure setup only where gaps were identified above — most infrastructure
   (181 test files, pytest, `pyforge-marshal-test` pixi task) already exists.
