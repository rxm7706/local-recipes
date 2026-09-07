---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-09-07'
workflowType: 'testarch-test-design'
inputDocuments:
  - 'prds/prd-pyforge-herald-2026-08-01/prd.md'
  - 'architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md'
  - 'epics.md'
  - 'test-design-architecture.md'
---

# Test Design for QA: pyforge-herald (Moments 1–4 + Canopy Surface)

**Purpose:** Test execution recipe. Defines what to test, how to test it, and what QA needs
from other teams.

**Date:** 2026-09-07
**Author:** rxm7706
**Status:** Draft
**Project:** pyforge-herald

**Related:** See `test-design-architecture.md` for testability concerns, the full risk
register, and architectural blockers (R-001..R-007).

---

## Executive Summary

**Scope:** This is a **post-ship, system-level regression test design** for a station that
is 47/50 stories `done` (Epics 1–17) with 45 existing pytest/Vitest files, not a
pre-implementation acceptance-criteria plan. The goal is confidence that the shipped
architecture's invariants (etag safety, write-gate consistency, concurrency safety, evidence
integrity) stay defended as the station grows, plus visibility into the 3 genuine
verification gaps found (R-001, R-002, and the untested Epic 18 surface). It intentionally
does **not** reproduce a story-by-story test matrix — the existing generated
`test-architecture.md` already attempts that shape (and its own linkage column reads "none
observed" for all 64 rows, which is itself R-001); this document instead organizes coverage
by architectural risk and priority.

**Risk Summary:**

- Total Risks: 7 (2 high-priority score ≥6, 3 medium, 2 low)
- Critical Categories: TECH (traceability, KPI instrumentation), PERF (web-load NFR)

**Coverage Summary:**

- P0 tests: ~6 (etag safety, write-gate, webhook auth, concurrency, evidence-required-to-publish, live-ship proof)
- P1 tests: ~8 (deck pull/stale-mirror/watch, notice lifecycle, evidence revalidation, deck-QA gate, PPTX editability, exporter-plugin boundary)
- P2 tests: ~4 (CLI argument conventions, web panel rendering, portal slice, redirects)
- P3 tests: ~3 (CLI help UX, perf-trend benchmark, i18n exploratory)
- **Total**: ~21 scenarios (~1–2 weeks for 1 QA/dev to audit/backfill against the existing suite; most scenarios already have a home in the 45 existing test files — see Test Coverage Plan for the mapping)

---

## Not in Scope

| Item                                                                                   | Reasoning                                                                                                                                          | Mitigation                                                                                          |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| **Epic 18: Manticore studio relay, `bmad-os-changelog`/`-social` routing, `slides-generator`** | Zero implementation exists (confirmed: no "narration" reference anywhere in `src/` or `tests/`); all 3 stories are cross-station-`blocked` on Steward 46.2/46.5/46.6 | Re-run an **epic-level** test design for Epic 18 once Steward unblocks it; tracked in `deferred-work-ledger.md` |
| **Full-text search (Moment 4 archive)**                                                | Explicitly out of scope per PRD; simple date/category indexing only                                                                                | Revisit if a future PRD adds it                                                                     |
| **Multi-region Herald surfaces / real-time Design↔Code sync**                          | Explicit PRD non-goals; single unified service, pull model only                                                                                    | N/A                                                                                                  |
| **Live 99% uptime SLA measurement**                                                     | No production hosting/monitoring baseline yet; SLA itself is "tbd with ops" in the architecture doc                                                | Owned by Steward's dashboard hosting layer, not Herald                                              |
| **i18n / non-English `document_output_language` path**                                 | Satellite Deferred Decision 6: "assume English-first for now"                                                                                       | Exploratory only (P3-003) until a real requirement lands                                            |

**Note:** Items above have been reviewed and are accepted as out-of-scope for this pass.

---

## Dependencies & Test Blockers

### Backend/Architecture Dependencies (Pre-Implementation)

**Source:** See Architecture doc "Quick Guide" for detailed mitigation plans.

1. **R-001 generator fix** — shared-script owner — no fixed timeline
   - QA needs a working story↔test link before trusting any future coverage-completeness claim from `bmad_tea_playwright.py --check`.
   - Blocks: confident automated coverage-drift detection for new stories (not blocking today's manual audit).

2. **R-002 web-load NFR decision** — Herald web maintainer — next sprint
   - QA needs a decision (build a harness, or reclassify the NFR) before P3-002 can move to P1.
   - Blocks: closing out the PRD's `<2s web tab load` success criterion with real evidence.

3. **Epic 18 unblock** — Steward 46.2/46.5/46.6 — cross-station, no fixed timeline
   - QA cannot design further scenarios for the Manticore/comms/slides relay until code exists.

### QA Infrastructure Setup (Already in Place)

1. **Isolation fixtures** — `tmp_path`-based `.herald/` directory isolation is already the
   convention across the existing 45 test files (e.g. `test_claims.py`, `test_notices.py`);
   no new fixture work needed for regression coverage of Epics 1–17.
2. **Egress control** — an autouse `deny_network`-style fixture keeps the default
   `pyforge-herald-test` gate offline; two explicit opt-in markers exist for the exceptions:

```python
# pyproject.toml [tool.pytest.ini_options] — already registered, real markers:
#   live: reaches the real claude-design MCP endpoint (opt in with HERALD_LIVE_DESIGN=1)
#   live_webhook: starts a real daphne subprocess over a real loopback socket
#                 (opt in with HERALD_LIVE_WEBHOOK=1)
```

3. **Stub pattern for network-adjacent seeding** — the project's own idiom for bypassing an
   expensive/networked side effect during setup (not `page.route`, not a raw `unittest.mock`
   ad hoc call — a scoped `monkeypatch` on the real seam):

```python
# Real pattern from test_performance_epic11.py — the local equivalent of the
# playwright-utils mandate's "no ad-hoc network interception" rule, applied to
# a pytest-only stack instead of a browser-fixture one.
@pytest.fixture(autouse=True)
def _stub_evidence_validation(monkeypatch):
    """Seeding N published claims runs every evidence link through
    claims.publish's validation loop -- stub it so seeding never reaches
    the network-deny boundary."""
    monkeypatch.setattr(evidence, "validate_for_publish", lambda url, **_k: None)
```

**Deviation note:** `tea_use_playwright_utils=true` / `tea_use_pactjs_utils=true` in the
substituted config target the `@seontechnologies/playwright-utils` and Pact.js **npm**
packages. Neither fits this Python-first station (Vitest, not Playwright/Cypress, covers the
React panels; no Pact broker or `.pacttest.ts` files exist anywhere). Code examples below
follow the *intent* of those mandates (fixtures over ad-hoc calls, no hard waits, no raw
network calls in a test that should be isolated) using the project's real idioms instead.

---

## Risk Assessment

**Note:** Full risk details in Architecture doc. This section summarizes risks relevant to QA test planning.

### High-Priority Risks (Score ≥6)

| Risk ID   | Category | Description                                          | Score | QA Test Coverage                                                            |
| --------- | -------- | ------------------------------------------------------- | ----- | -------------------------------------------------------------------------- |
| **R-001** | TECH     | Story↔test matrix mechanically empty (0-for-64)        | **6** | Not QA-testable directly — generator fix, then `--check` re-run as the proof |
| **R-002** | PERF     | `<2s` web-tab NFR has zero automated verification       | **6** | P3-002 → promote to P1 once a harness/decision exists (see Dependencies)   |

### Medium/Low-Priority Risks

| Risk ID | Category | Description                                                  | Score | QA Test Coverage                                                     |
| ------- | -------- | ---------------------------------------------------------------- | ----- | ---------------------------------------------------------------------- |
| R-003   | OPS      | Default gate never exercises a real ASGI socket                 | 4     | P0-006 (opt-in `live_webhook` marker) documents the real proof exists  |
| R-004   | OPS      | Webhook schema drift vs. real GitHub Actions producer untested  | 4     | Not directly QA-testable — a static CI check, not a pytest scenario   |
| R-005   | TECH     | Satellite KPIs have no instrumentation to query                 | 4     | Out of scope for this pass — see Not in Scope                         |
| R-006   | DATA     | Notice-versioning depth is an open deferred decision             | 2     | Monitor only                                                          |
| R-007   | TECH     | i18n path untested                                                | 1     | P3-003 (exploratory)                                                  |

---

## NFR Test Coverage Plan

| NFR Category    | Requirement / Threshold                          | Planned Validation                                                        | Tool / Level          | Evidence Artifact                             | Priority |
| --------------- | --------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------ | -------------------------------------------------- | -------- |
| Security        | Operator-role write gate; HMAC-SHA256 webhook auth  | Cross-cutting gate check across all 6 write commands; signature-mismatch rejection | pytest (unit)           | `test_reliability_epic11.py`, `test_webhook.py`   | P0       |
| Performance     | CLI <1s p95                                          | In-process timed run over 100 seeded records per Moment                        | pytest (unit)           | `test_performance_epic11.py`                       | P1       |
| Performance     | Web tab <2s load                                     | **Not yet planned** — pending R-002 decision                                   | TBD                       | TBD                                                | P3 (until unblocked) |
| Reliability     | Webhook retry: exponential backoff, max 3 retries    | Retry-exhaustion + backoff-timing assertions                                    | pytest (unit)           | `webhook.py` test coverage                         | P1       |
| Reliability     | Second-writer safety (concurrent progress/claim writes) | Lock-contention + transaction-isolation checks                                | pytest (unit/integration) | `test_locking.py`, `test_db.py`                    | P0       |
| Data Integrity  | ≥1 evidence link required to publish a claim         | Publish attempt with zero evidence links must fail                             | pytest (unit)           | `test_claims.py`, `test_evidence.py`               | P0       |
| Data Integrity  | Weekly evidence revalidation flags newly-stale links | Direct call to `scheduler.run_evidence_revalidation` over a mixed fresh/stale set | pytest (unit)           | `test_scheduler.py`, `test_evidence.py`            | P1       |
| Maintainability | Unit ≥80% / integration ≥70% coverage                | Coverage report from the station's own test task                               | pytest-cov / CI          | `pixi run -e pyforge-herald pyforge-herald-test`   | P2       |

**Missing thresholds or evidence sources:** Web-tab load-time NFR (R-002, needs a
stakeholder/architecture decision before a tool can even be chosen); uptime SLA (still "tbd
with ops," not a QA-owned gap).

---

## Entry Criteria

- [ ] R-001 (generator fix) and R-002 (web-load NFR decision) reviewed by the team (need not
      be *resolved* to start regression testing — they gate specific scenarios, not the whole plan)
- [ ] Existing 45-file pytest/Vitest suite passes locally (`pixi run -e pyforge-herald pyforge-herald-test`)
- [ ] `.herald/` isolation fixtures confirmed working on a clean `tmp_path`
- [ ] `HERALD_LIVE_WEBHOOK` / `HERALD_LIVE_DESIGN` opt-in tests run at least once per release cycle, not just on-demand

## Exit Criteria

- [ ] All P0 tests passing (etag safety, write-gate, webhook auth, concurrency, evidence-required, live-ship proof)
- [ ] All P1 tests passing or failures triaged and accepted
- [ ] No open high-priority bugs against R-001–R-004
- [ ] Coverage percentage independently confirmed (not just assumed from the generator baseline's stale ≥80%/≥70% targets)
- [ ] Epic 18 explicitly deferred (not silently dropped) pending Steward unblock

---

## Test Coverage Plan

**IMPORTANT:** P0/P1/P2/P3 = **priority and risk level**, NOT execution timing. See
"Execution Strategy" for when tests run.

### P0 (Critical)

**Criteria:** Blocks a core invariant + high risk + no workaround.

| Test ID    | Requirement                                                                 | Test Level          | Risk Link | Notes                                                                                   |
| ---------- | ------------------------------------------------------------------------------ | ---------------------- | --------- | ---------------------------------------------------------------------------------------- |
| **P0-001** | Etag mismatch on Design↔Code pull is rejected, never silently overwrites (AD-2) | Unit/Integration     | —         | Existing coverage in Epic 2's pull tests                                               |
| **P0-002** | Operator-role write gate blocks all 6 write commands consistently               | Unit (cross-cutting) | —         | `test_reliability_epic11.py` already provides the structural guard                     |
| **P0-003** | Webhook HMAC signature verification rejects unsigned/mis-signed payloads       | Unit                  | R-004     | `test_webhook.py`                                                                        |
| **P0-004** | Concurrent `herald progress --update` calls never corrupt or lose data          | Unit/Integration     | —         | `test_locking.py`, `test_db.py` (Stories 13.1/13.3)                                     |
| **P0-005** | Success claim cannot publish with zero evidence links (AD-15)                   | Unit                  | —         | `test_claims.py`, `test_evidence.py`                                                    |
| **P0-006** | A real merge event creates a progress record + success-claim draft, end to end  | Integration/live-smoke | R-003   | Story 13.6; `test_webhook_live_smoke.py` (opt-in, `HERALD_LIVE_WEBHOOK=1`) + `test_cli_epic13.py` |

**Total P0:** ~6 tests

---

### P1 (High)

**Criteria:** Important shipped feature + medium/high risk + workaround exists but difficult.

| Test ID    | Requirement                                                                                 | Test Level  | Risk Link | Notes                                                             |
| ---------- | ------------------------------------------------------------------------------------------------ | ------------- | --------- | -------------------------------------------------------------------- |
| **P1-001** | Deck-pull etag short-circuit avoids redundant re-pull when unchanged (Story 2.1)                | Unit          | —         | Existing coverage                                                 |
| **P1-002** | Stale hand-mirror detection flags a manually edited derived artifact (Story 3.2)                | Unit          | —         | Existing coverage                                                 |
| **P1-003** | Watch-loop backoff and halt-on-auth-error behave correctly (Epic 4)                              | Unit          | —         | Existing coverage                                                 |
| **P1-004** | Notice lifecycle Draft→Published→Closed + redirect-rule generation on rename (Epic 10)           | Unit          | —         | `test_notices.py`                                                 |
| **P1-005** | Weekly evidence revalidation flags newly-stale links                                             | Unit          | —         | `test_scheduler.py`, `scheduler.run_evidence_revalidation`        |
| **P1-006** | Headless-Chromium deck-QA render gate catches a broken slide (Story 14.2)                        | Integration (real browser) | —       | `test_deck_qa.py`, `playwright-python`-backed                     |
| **P1-007** | PPTX template-parse-then-fill produces editable text runs, not background-image slides (Story 15.1) | Unit         | —         | The documented regression this pipeline was built to fix (`test_pptx_pipeline.py`) |
| **P1-008** | Exporter hook plugins register correctly; export failure never surfaces as a PR gate verdict (Epic 16) | Unit         | —         | `test_export_plugins.py`, `SecondVerdictError` boundary            |

**Total P1:** ~8 tests

---

### P2 (Medium)

**Criteria:** Secondary flow + low/medium risk + acceptable workaround.

| Test ID    | Requirement                                                                          | Test Level  | Risk Link | Notes                                     |
| ---------- | ----------------------------------------------------------------------------------------- | ------------- | --------- | -------------------------------------------- |
| **P2-001** | Shared CLI argument conventions (`--json`, `--date-range`, `--station`) behave consistently across subcommands (Story 6.2) | Unit          | —         | `test_cli_dispatch.py`                    |
| **P2-002** | Web panel components render from the static JSON snapshot without error                 | Component (Vitest) | —      | `ProgressPanel.test.jsx`, `SuccessPanel.test.jsx`, `OperationsPanel.test.jsx` |
| **P2-003** | Portal slice (`/stations/herald/`) renders one slug's deck status via PortalClient only, no raw HTTP (Story 17.2) | Integration   | —         | `test_portal_deck_status.py`              |
| **P2-004** | Redirect rules resolve old notice URLs to the new archive location (FR-5.5)              | Unit          | —         | `test_notices.py`                         |

**Total P2:** ~4 tests

---

### P3 (Low)

**Criteria:** Nice-to-have, exploratory, or blocked-pending-decision.

| Test ID    | Requirement                                                                    | Test Level   | Notes                                                                        |
| ---------- | ----------------------------------------------------------------------------------- | -------------- | -------------------------------------------------------------------------------- |
| **P3-001** | CLI help-text discoverability / first-day usability (Story 6.5)                    | Exploratory    | Manual review                                                                 |
| **P3-002** | Web-tab load-time benchmark, once R-002 is decided                                 | TBD            | Currently blocked on the architecture decision, not a QA scoping choice        |
| **P3-003** | Non-English `document_output_language` path (i18n)                                 | Exploratory    | No requirement exists yet (Deferred Decision 6); do not build real coverage until one does |

**Total P3:** ~3 tests

---

## Execution Strategy

**Philosophy:** Run everything in PRs unless there's significant infrastructure overhead.

### Every PR: pytest + Vitest (~5–10 min)

**All functional tests** (P0–P2, ~18 of the ~21 scenarios): the existing
`pixi run -e pyforge-herald pyforge-herald-test` task plus the web package's `npm test`
(Vitest). No new infrastructure needed — these already run today.

### Nightly/Weekly: opt-in live markers

**`live` and `live_webhook`-marked tests** (P0-006's real-socket half, and the existing
`claude-design`-reaching spike): deliberately excluded from the default PR gate since they
open real sockets/subprocesses; run on a schedule (e.g., nightly) or before a release cut,
not on every commit.

**Manual/exploratory** (excluded from automation): P3-001 CLI-help review; P3-003 i18n
exploration once a real requirement exists.

---

## QA Effort Estimate

**QA test-development effort only** (this is an audit-and-backfill pass over a mostly-shipped
suite, not new-feature test authoring):

| Priority  | Count | Effort Range     | Notes                                                                 |
| --------- | ----- | ------------------ | ------------------------------------------------------------------------ |
| P0        | ~6    | ~4-8 hours         | Mostly confirming existing coverage maps cleanly to these 6 invariants |
| P1        | ~8    | ~8-16 hours        | Mostly existing coverage; verification pass, not new authoring         |
| P2        | ~4    | ~4-8 hours         | Mostly existing coverage                                                |
| P3        | ~3    | ~2-4 hours         | One is blocked on an architecture decision (P3-002)                    |
| **Total** | ~21   | **~18-36 hours**   | **Well under 1 QA-week; this is a verification pass, not a build**    |

**Assumptions:**

- Excludes fixing R-001 (generator) and R-002 (harness/decision) themselves — those are
  tracked as architecture-owned follow-ups, not QA test-authoring hours.
- Assumes the existing 45-file suite continues to pass as the baseline.

---

## Implementation Planning Handoff (Optional)

| Work Item                                           | Owner                          | Target Milestone       | Dependencies/Notes                                  |
| ------------------------------------------------------ | --------------------------------- | ------------------------- | -------------------------------------------------------- |
| Fix generator story↔test linkage (R-001)              | `bmad_tea_playwright.py` owner    | next generator cycle    | Docstrings already carry the needed data              |
| Decide web-load NFR harness vs. reclassification (R-002) | Herald web maintainer            | next sprint              | Blocks P3-002 → P1 promotion                            |
| Static webhook schema-drift check (R-004)             | Herald maintainer                 | implementation phase     | No new runtime dependency needed                        |
| Re-run epic-level test design for Epic 18             | QA / Herald                       | after Steward 46.2/46.5/46.6 land | Zero code exists yet — nothing to test today             |

---

## Interworking & Regression

| Service/Component                    | Impact                                                        | Regression Scope                                            | Validation Steps                                         |
| ---------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------- |
| **`pyforge.steward.dashboard`**        | Owns the operator-role auth model Herald's write gate delegates to | Steward's own auth test suite must pass                            | Cross-team: confirm before any Steward auth refactor          |
| **Canopy host ASGI**                   | Hosts Herald's webhook mount + `/stations/herald/mcp` + portal slice | Host-level routing/mount tests                                     | Cross-team: confirm Herald's mount survives host changes      |
| **GitHub Actions (`on-ship`/`on-pr-close` producers)** | Real payload shape Herald's webhook trusts                          | R-004's proposed schema-diff check                                  | Add before next producer-side workflow edit                   |

**Regression test strategy:** Existing `pyforge-herald-test` + web `npm test` cover Epics
1–17's shipped surface; no cross-team staging environment is required for this pass.

---

## Appendix A: Code Examples & Tagging

**pytest markers for selective execution** (already registered, real, in
`src/shared/packages/pyforge-herald/pyproject.toml`):

```python
# P0 concurrency test (existing idiom, not a fabricated example)
def test_concurrent_progress_update_does_not_corrupt(tmp_path, monkeypatch):
    """R-... / P0-004: two concurrent writers must not lose or corrupt data."""
    # arrange: seed .herald/ under tmp_path, two writer threads/processes
    # act: fire both writers at the same record
    # assert: final state matches one complete write, never a partial merge
    ...
```

```bash
# Run only the opt-in live-socket proof (P0-006's real-socket half)
HERALD_LIVE_WEBHOOK=1 pixi run -e pyforge-herald pytest \
    src/shared/packages/pyforge-herald/tests/test_webhook_live_smoke.py -v

# Run only the opt-in claude-design spike
HERALD_LIVE_DESIGN=1 pixi run -e pyforge-herald pytest \
    src/shared/packages/pyforge-herald/tests/test_live_design_spike.py -v

# Default gate (both live markers excluded automatically via their own skipif)
pixi run -e pyforge-herald pyforge-herald-test
```

**Real stub pattern** (the project's actual idiom for isolating a networked side effect
during setup — see Dependencies & Test Blockers above for the full example from
`test_performance_epic11.py`).

---

## Appendix B: Knowledge Base References

- **Risk Governance**: `risk-governance.md` - Risk scoring methodology
- **Test Priorities Matrix**: `test-priorities-matrix.md` - P0-P3 criteria
- **Test Levels Framework**: `test-levels-framework.md` - E2E vs API vs Unit selection
- **Test Quality**: `test-quality.md` - Definition of Done
- **Contract Testing**: `contract-testing.md` - applied conceptually for R-004 (no Pact.js
  tooling introduced into this Python station; see the deviation note above)

---

**Generated by:** BMad TEA Agent (Master Test Architect)
**Workflow:** `bmad-testarch-test-design`
**Version:** 5.0 (Step-File Architecture)
