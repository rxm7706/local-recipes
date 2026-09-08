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
  - 'test-design-architecture.md'
---

# Test Design for QA: pyforge-marshal (system-level)

**Purpose:** Test execution recipe for QA. Defines what to test, how to test it, and what QA
needs from other teams.

**Date:** 2026-09-07
**Author:** Master Test Architect (bmad-testarch-test-design)
**Status:** Draft
**Project:** pyforge-marshal

**Related:** See `test-design-architecture.md` for testability concerns and architectural
blockers (B-1, B-2, B-3).

---

## Executive Summary

**Scope:** Risk-driven test planning for pyforge-marshal's existing + near-term surfaces (loop
homes, run supervision, gates, landing, fleet status, adapter portability, policy composition,
`marshal seed`, `pyforge-core`). This is a **gap-closing** plan layered on top of an existing
181-file test suite, not a from-zero plan.

**Risk Summary:**

- Total Risks: 13 (5 high-priority score ≥6, 5 medium, 3 low)
- Critical Categories: TECH (region engine, landing grammar), OPS (verdict projection, poll
  interval, supervisor independence), DATA (journal/teardown durability)

**Coverage Summary:**

- P0 tests: ~5 scenario families (map 1:1 to the 5 high-priority risks)
- P1 tests: ~5 scenario families (medium risks)
- P2 tests: ~3 scenario families (low/accepted risks — monitoring only)
- P3 tests: ~2 scenario families (exploratory: harness-era canary, generator-heuristic audit)
- **Total**: ~15 scenario families (~25-40 individual test cases once broken down) — see
  per-priority tables below. This is additive to the existing 181 test files, not a replacement.

---

## Not in Scope

**Components or systems explicitly excluded from this test plan:**

| Item | Reasoning | Mitigation |
|---|---|---|
| **The wrapped `bmad-loop` engine's own internals** | Marshal wraps, never absorbs (AD-1/AD-2) — testing `bmad-loop`'s own correctness is upstream's responsibility | Covered by Marshal's harness-contract tests (NFR-9, AD-78) which assert Marshal's *assumptions about* the wrapped engine, not the engine's own logic |
| **Any browser/E2E layer** | `detected_stack = backend`; no `page.goto`/`page.locator`, no `playwright.config.*` at the project or repo root | N/A — correctly out of scope, not a gap |
| **Pact.js consumer-driven contract tests** | `tests/contract/` exists but tests internal Port/Adapter conformance, not an external HTTP provider relationship; fleet-wide `tea_use_pactjs_utils=true` does not make this relevant here | Re-confirm per-station before any future TEA run assumes Pact applies |
| **The other 7 stations' test estates** (atlas, doctor, herald, mason, scribe, steward, warden) | This run is scoped to the ACTIVE project `pyforge-marshal` only | Each of the other 7 stations received its own separate system-level TEA run under Story 31.1 (see `planning-artifacts/reviews/tea-equivalence-2026-09-07.md` for the fleet-wide equivalence comparison) |
| **`marshal seed`'s generated-repo runtime behavior** | Part II ships a model *installer*; the installed repo's own tests are that repo's responsibility, not Marshal's | Covered by Marshal's own idempotence/plan-correctness tests (AD-60), not by testing arbitrary consumer repos |

**Note:** Items listed here have not yet been reviewed and accepted as out-of-scope by an actual
QA/Dev/PM triad — this is this run's own scoping judgment, to be confirmed.

---

## Dependencies & Test Blockers

**CRITICAL:** QA cannot treat the following as resolved without confirmation from other teams.

### Backend/Architecture Dependencies (Pre-Implementation)

**Source:** See `test-design-architecture.md` "Quick Guide" for detailed mitigation plans.

1. **B-1 (generator baseline validity)** - Marshal/Dev - before Epic 31.1 executes
   - QA needs: a decision on whether 31.1's equivalence report is measured against the current
     (nearly empty) generator baseline or a repaired one.
   - Why it blocks testing: without this, "TEA output covers everything the generator covered"
     is true almost by default (207/208 rows already say "none observed"), which would make the
     equivalence gate meaningless rather than a real check.

2. **B-2 (no per-story matrix in TEA templates)** - Marshal - before Epic 31.2 deletes the
   generator
   - QA needs: confirmation that a per-story test-file inventory (if still wanted after cutover)
     will come from `bmad-testarch-trace`, not from re-purposing `test-design`.
   - Why it blocks testing: `test-design`'s own templates (this document included) have no slot
     for a 208-row story enumeration; committing to one here would mean hand-inventing a section
     the workflow itself doesn't define.

### QA Infrastructure Setup (Pre-Implementation)

1. **Test Data / Fixtures** - already present: `tests/fixtures/`, `tests/support/` under
   `src/shared/packages/pyforge-marshal/tests/`. No new factory infrastructure is needed for the
   scenarios below; they extend existing fixture patterns (journal fixtures, policy fixtures).
2. **Test Environments**
   - Local: `pixi run -e pyforge-marshal pyforge-marshal-test`
   - CI: `detectors-ci` / the station's own CI task (not independently re-verified in this pass)
   - No staging environment applies — this is a CLI tool, not a deployed service.

**Adversarial-fixture pattern (for R-2, unevaluable-is-failure):**

```python
# Illustrative shape only — follow the project's existing fixture conventions under
# tests/support/ and tests/fixtures/ rather than introducing a new pattern.
def test_crashing_verify_command_resolves_to_fail(tmp_path, fake_verify_command_that_crashes):
    verdict = evaluate_gate(fake_verify_command_that_crashes)
    assert verdict.status == "FAIL"  # never PASS-by-default, per AD-8 / NFR-3


def test_timeout_verify_command_resolves_to_fail(tmp_path, fake_verify_command_that_hangs):
    verdict = evaluate_gate(fake_verify_command_that_hangs, timeout_s=1)
    assert verdict.status == "FAIL"
```

---

## Risk Assessment

**Note:** Full risk details in `test-design-architecture.md`. This section summarizes risks
relevant to QA test planning.

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Score | QA Test Coverage |
|---------|----------|--------------|-------|-------------------|
| **R-1** | TECH | Managed-region engine corrupts a tracked file | **6** | Adversarial region-engine cases: double-matching anchor, overlapping byte-span, concurrent-edit simulation |
| **R-2** | OPS | Crash/timeout/ambiguous verify-command misread as PASS | **6** | The two fixtures above, plus a garbage-exit-code case |
| **R-5** | DATA | Journal/state desync at teardown or mid-run kill | **6** | Kill-mid-run fixture asserting promoted artifacts survive (regression for the lived incident) |
| **R-6** | TECH | Landing-evidence grammar misses a legitimate merge shape | **6** | Fixture reproducing the lived "orphaned follow-up-review commit" merge-subject shape |
| **R-8** | PERF/OPS | Supervisor poll interval may exceed the harness's actual cache TTL | **6** | Timed test deriving the poll interval from the installed `bmad-loop`'s documented TTL, not a hardcoded 60s |

### Medium/Low-Priority Risks

| Risk ID | Category | Description | Score | QA Test Coverage |
|---------|----------|--------------|-------|-------------------|
| R-3 | SEC | Secret leak into journal/gate-record/PR body | 3 | Redaction meta-test scanning written artifacts for secret-shaped strings |
| R-4 | OPS | Supervisor trusts session self-report | 4 | Assert supervisor verdict is unaffected when a fake session reports a false "done" status |
| R-7 | OPS | Policy layer widens scope it doesn't own | 3 | Policy-composition test asserting a lower layer cannot widen an allowlist a higher layer narrowed |
| R-9 | DATA | `marshal seed` manifest vs. repo reality diverge | 3 | Idempotence re-run test (apply plan twice, assert second run is a no-op) |
| R-10 | SEC | Managed-region write escapes the guard | 3 | AST-based meta-test (already referenced as existing, P-01) — confirm it is current |
| R-11 | TECH | Copier API assumption drift | 2 | Range-pin sync test (already exists per architecture doc) — monitor only |
| R-12 | OPS | Stale seed plan applied to changed repo | 2 | `repo_fingerprint` refusal test — confirm it exists |
| R-13 | BUS | Template/package release coupling | 2 | Accepted risk — no new test owed |

---

## NFR Test Coverage Plan

**Purpose:** Map NFR requirements to planned validation work. Does not assign final PASS/
CONCERNS/FAIL status.

| NFR Category | Requirement / Threshold | Planned Validation | Tool / Level | Evidence Artifact | Priority |
|---|---|---|---|---|---|
| Security | NFR-11: no secret reaches a written artifact | Scan every artifact-writing code path's output for secret-shaped strings | Unit/meta (pytest) | Redaction meta-test report | P0 |
| Performance | NFR-14: poll interval ≤ harness cache TTL | Derive TTL from installed `bmad-loop`, assert poll interval respects it | Integration (pytest, timed) | Timing assertion output | P0 |
| Reliability | NFR-3/NFR-7: never-false-green + idempotence | Adversarial verdict fixtures (R-2) + re-run-is-no-op tests for `init`/`deploy`/`adapters sync`/policy composition | Unit + integration (pytest) | Test suite pass/fail | P0 |
| Maintainability | NFR-9: harness-drift tests fail loudly | Re-run vocabulary-pin tests against next `bmad-loop` minor release as a canary | CI (pytest, scheduled) | CI run report | P1 |

**Missing thresholds or evidence sources:** NFR-14's numeric targets remain `[ASSUMPTION]` per
the PRD itself — flagged for stakeholder clarification before `nfr-assess` can issue a final
verdict on performance.

---

## Entry Criteria

**QA testing cannot begin until ALL of the following are met:**

- [ ] B-1 (generator-baseline validity) is decided one way or the other
- [ ] Real owners are assigned to the 5 high-priority risks (this pass could not assign them)
- [ ] Existing `pixi run -e pyforge-marshal pyforge-marshal-test` is confirmed green as a baseline
      before adding adversarial fixtures on top of it
- [ ] Adversarial-fixture conventions (tmux/subprocess simulation for crash/timeout cases) are
      agreed with whoever owns `tests/support/`

## Exit Criteria

**Testing phase is complete when ALL of the following are met:**

- [ ] All P0 tests passing (the 5 high-priority-risk fixtures)
- [ ] All P1 tests passing or explicitly triaged
- [ ] No open high-priority bug tied to R-1/R-2/R-5/R-6/R-8
- [ ] Coverage target unchanged from the generator's own declared targets (unit ≥80%, integration
      ≥70%) still holds after new fixtures are added
- [ ] B-1/B-2 resolved before Epic 31.2 is allowed to delete the generator

---

## Project Team (Optional)

*Omitted — no roles/names were available for this pass; assign before adoption.*

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = priority and risk level, not execution timing.

### P0 (Critical)

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---------|-------------|------------|-----------|-------|
| **P0-001** | Crash/hang/garbage-exit verify-command resolves to FAIL | Unit | R-2 | AD-8/NFR-3 |
| **P0-002** | Region-engine double-anchor / overlapping-span case does not corrupt the file | Unit | R-1 | AD-53/AD-56 |
| **P0-003** | Kill mid-run leaves promoted artifacts durable | Integration | R-5 | AD-13/AD-29 |
| **P0-004** | Lived orphan-merge-subject shape is still recognized by the landing grammar | Contract | R-6 | AD-73; extend `test_landing_evidence_conformance.py` if not already covered |
| **P0-005** | Supervisor poll interval is derived from (not merely under) the harness's actual cache TTL | Integration | R-8 | NFR-14 |

**Total P0:** ~5 tests (may decompose into more individual cases per fixture)

### P1 (High)

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---------|-------------|------------|-----------|-------|
| **P1-001** | No secret-shaped string reaches a written journal/gate-record/PR body | Unit/meta | R-3 | NFR-11 |
| **P1-002** | Supervisor verdict unaffected by a fake session self-reporting "done" | Unit | R-4 | AD-9/NFR-4 |
| **P1-003** | A lower policy layer cannot widen an allowlist a higher layer narrowed | Unit | R-7 | AD-27 |
| **P1-004** | Applying a `marshal seed` plan twice is a no-op (idempotence) | Integration | R-9 | AD-60 |
| **P1-005** | Managed-region write outside the allowed path set is rejected | Unit/meta | R-10 | AD-61/P-01 — confirm existing AST meta-test still covers this |

**Total P1:** ~5 tests

### P2 (Medium)

| Test ID | Requirement | Test Level | Risk Link | Notes |
|---------|-------------|------------|-----------|-------|
| **P2-001** | Copier range-pin sync test still passes against current Copier release | Unit | R-11 | Monitor only |
| **P2-002** | Stale seed plan (changed `repo_fingerprint`) is refused | Unit | R-12 | Confirm existing coverage |
| **P2-003** | Region-unit-test share of the suite has not shrunk relative to total suite growth | Meta (suite-composition check) | R-1 (secondary) | Early-warning signal, not a correctness test |

**Total P2:** ~3 tests

### P3 (Low)

| Test ID | Requirement | Test Level | Notes |
|---------|-------------|------------|-------|
| **P3-001** | Harness vocabulary-pin canary against the next `bmad-loop` minor release | Contract (scheduled) | NFR-9/AD-78; run opportunistically, not every PR |
| **P3-002** | Audit: does the generator's story→test linkage heuristic ever match beyond Story 27.2's naming pattern? | Exploratory/meta | Informs B-1 — not a pass/fail gate, an investigation |

**Total P3:** ~2 tests

---

## Execution Strategy

**Philosophy:** This is a CLI/library test estate (pytest, no browser). Run functional tests in
every PR; defer only the genuinely slow/canary items.

### Every PR: pytest suite (existing + new P0/P1)

- All unit/integration/meta/contract tests, including the new P0-001..005 and P1-001..005
  fixtures once written
- Existing task: `pixi run -e pyforge-marshal pyforge-marshal-test`

**Why run in PRs:** the whole suite is fast (no browser, no k6); no infrastructure reason to
defer functional correctness tests.

### Nightly/Weekly: none currently identified

- No load/chaos/multi-hour suite exists for Marshal today, and none of the 13 risks in this pass
  require one (P3-001's harness-canary is opportunistic/scheduled against upstream releases, not
  a nightly job in the traditional sense).

**Manual/out-of-band:**

- P3-002 (generator-heuristic audit) is an investigation, not an automated test — resolve B-1
  first.

---

## QA Effort Estimate

**QA test development effort only:**

| Priority | Count | Effort Range | Notes |
|----------|-------|---------------|-------|
| P0 | ~5 | ~15-25 hours | Two of five (R-2, R-5) need new fixture harnesses (crash/timeout simulation, kill-mid-run simulation) — not trivial |
| P1 | ~5 | ~10-20 hours | Mostly extends existing fixture/policy test patterns |
| P2 | ~3 | ~1-3 days | Confirm-existing-coverage checks, plus one meta suite-composition check |
| P3 | ~2 | ~4-8 hours | One scheduled canary, one investigation (not a repeatable automated test) |
| **Total** | ~15 | **~4-6 days (1 QA/dev)** | Additive to the existing 181-file suite; assumes fixture conventions in `tests/support/` are reusable |

**Assumptions:**

- Includes test design→implementation→debugging→CI integration for the new fixtures only.
- Excludes ongoing maintenance and excludes any work needed to resolve B-1/B-2 themselves (those
  are decisions, not test-writing effort).

---

## Implementation Planning Handoff (Optional)

| Work Item | Owner | Target Milestone | Dependencies/Notes |
|-----------|-------|-------------------|---------------------|
| Resolve B-1 (generator baseline validity) | Marshal/Dev | Before Epic 31.1 executes | Blocks a meaningful equivalence report |
| Resolve B-2 (per-story matrix scope) | Marshal | Before Epic 31.2 | Decide whether `bmad-testarch-trace` inherits this need |
| Write P0-001..005 fixtures | Marshal core | Before Epic 31.2 (verdict/durability/landing properties underpin TEA-equivalence too) | See adversarial-fixture pattern above |

---

## Tooling & Access

*Omitted — no non-standard tools or access requests identified; pytest + the existing pixi
environment cover everything in this plan.*

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope | Validation Steps |
|---|---|---|---|
| **`bmad-loop` (wrapped harness)** | A minor/major release can shift observable CLI surface Marshal depends on | Harness-contract/vocabulary-pin tests (AD-78) | Re-run the full `pyforge-marshal-test` suite against the newly pinned range before bumping `pyproject.toml` |
| **The other 7 stations sharing `pyforge-core`** | A `pyforge-core` change (Part III shared floor) could ripple into every station | Each station's own suite | Out of scope for this Marshal-scoped run — flagged for cross-station awareness only |
| **The generator (`bmad_tea_playwright.py`)** | Epic 31 plans its deletion behind an equivalence check | This document itself | See B-1; do not delete until the equivalence bar is meaningful |

**Regression test strategy:** the existing `pyforge-marshal-test` / `detectors-ci` gates already
cover general regression; the additions in this plan are new coverage for previously-untested
adversarial paths, not a new regression suite.

---

## Appendix A: Code Examples & Tagging

No Playwright layer applies (backend/CLI stack). Use pytest markers instead of `@P0`-style
Playwright tags, matching this repo's existing convention (`-m network` for opt-in network tests,
per `CLAUDE.md`'s CFE test guidance) — e.g. `@pytest.mark.p0` if the project adopts priority
markers; not independently confirmed whether `pyforge-marshal` already has such a marker
convention in `pyproject.toml`.

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` — risk scoring methodology
- **Test Priorities Matrix**: `test-priorities-matrix.md` — P0-P3 criteria
- **Test Levels Framework**: `test-levels-framework.md` — E2E vs API vs Unit selection
- **Test Quality**: `test-quality.md` — Definition of Done

---

**Generated by:** BMad TEA Agent
**Workflow:** `bmad-testarch-test-design`
**Version:** 5.0 (Step-File Architecture)
