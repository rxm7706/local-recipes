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
  - 'sprint-status-ledger.yaml'
---

# Test Design for Architecture: pyforge-herald (Moments 1–4 + Canopy Surface)

**Purpose:** Architectural concerns, testability gaps, and NFR requirements for review by the
Herald maintainer / factory Architecture reviewers. Serves as a contract on what must be
addressed before further test-automation investment in this station.

**Date:** 2026-09-07
**Author:** rxm7706 (git/repo identity — no `user_name` resolves anywhere in this repo's
`_bmad/config*.toml` layers; see progress checkpoint step 1)
**Status:** Architecture Review Pending
**Project:** pyforge-herald
**PRD Reference:** `planning-artifacts/prds/prd-pyforge-herald-2026-08-01/prd.md`
**ADR Reference:** `planning-artifacts/architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md` (AD-1..AD-20 + 2026-08-26 Canopy/as-built reconciliation)

---

## Executive Summary

**Scope:** Herald's four Moments of Proclamation — Pitch (deck family, Epics 1–5, 14–17),
Progress/Success/Operations (Moments 2–4, Epics 6–13), plus the not-yet-built Epic 18 relay
to the bmad-suite-lifecycle studio/comms/slides capabilities. 18 epics, 50 stories per
`epics.md`'s own frontmatter; 47 done (Epics 1–17), 3 cross-station-`blocked` (Epic 18).

**Business Context** (from PRD): Herald is the factory's voice and visibility layer — a
deck-authoring pipeline (Moment 1) plus a shipping-transparency/evidence/notice system
(Moments 2–4) so no work ships silently. No revenue metric; internal-developer-portal-class
tool. GA already shipped for Epics 1–17; Epic 18 is additive.

**Architecture** (from ADR): Etagged Design↔Code pull (AD-1/AD-2); SQLite-backed Progress/
Claims with git-tracked Notice archive (AD-13/AD-17, resolved from the original
PostgreSQL assumption); HMAC-verified webhook dispatch mounted on Steward's shared trust
boundary, not a bespoke perimeter (AD-14); operator-role write gate delegated to
`pyforge.steward.dashboard`, not owned by Herald (AD-16).

**Expected Scale:** 100+ notices/month, 1000+ claims/year, 10+ concurrent operators (PRD
NFR) — none of these volumes are exercised by the current test suite (see NFR table).

**Risk Summary:**

- **Total risks:** 7
- **High-priority (≥6):** 2 risks requiring attention before further test investment
- **Test effort:** ~21 planned scenarios (~1–2 weeks for 1 QA/dev, see companion QA doc)

---

## Quick Guide

### 🚨 BLOCKERS - Team Must Decide

1. **R-001: Story↔test traceability is mechanically broken** — the generated
   `test-architecture.md` baseline reports "none observed" linked test files for all 64 of
   its enumerated story rows, despite 45 real test files existing and several of them
   (`test_performance_epic11.py`, `test_reliability_epic11.py`, `test_integration_epic11.py`)
   naming their exact story in the module docstring already. Fix belongs in the shared
   `_bmad/scripts/bmad_tea_playwright.py` generator (cross-station tool, not Herald-owned
   code) — recommended owner: whichever station/Marshal owns that script.
2. **R-002: The `<2s` web-tab-load NFR has zero automated verification, by explicit design**
   — `test_performance_epic11.py`'s own docstring states this was left "honestly untested
   rather than inventing a fake proxy" since the dashboard is a static Vite bundle with no
   server/browser in the test suite. Team must decide: build a real harness, or formally
   reclassify the NFR now that the surface is static (recommended owner: Herald web
   maintainer).

**What we need from team:** A decision on both items before claiming this station's test
coverage is complete against its own documented NFRs.

---

### ⚠️ HIGH PRIORITY - Team Should Validate

1. **R-003: Default CI never exercises the real ASGI socket** — the only real-socket proof
   (`test_webhook_live_smoke.py`) is opt-in (`HERALD_LIVE_WEBHOOK=1`), deliberately excluded
   from `pyforge-herald-test`'s `deny_network` gate. Production confidence rests on the
   separate `.github/workflows/herald-live-demo.yml`. Recommendation: reference this
   explicitly in the operator runbook so its absence from the default gate isn't mistaken for
   a gap (implementation phase, Herald maintainer approves).
2. **R-004: Webhook payload-shape drift has no contract test** — `webhook.py`'s
   `_problem_unknown_fields` already rejects unknown fields loudly (good defense-in-depth),
   but nothing verifies the *real* GitHub Actions producer still matches that known-fields set
   over time; drift surfaces only as a live 400. Recommendation: a static schema-diff check
   against `.github/workflows/*.yml`, not a new Pact/JS dependency (implementation phase,
   approve or counter-propose).

**What we need from team:** Review recommendations and approve (or suggest changes).

---

### 📋 INFO ONLY - Solutions Provided

1. **Test strategy**: risk-tiered P0–P3 coverage plan, organized by architectural invariant
   (etag safety, write-gate consistency, concurrency, evidence integrity) rather than a
   story-by-story matrix — the station is fully shipped, so the goal is regression confidence,
   not first-build acceptance criteria.
2. **Tooling**: pytest (unit/integration/meta), Vitest (React component tests),
   `playwright-python` (headless-Chromium deck-QA gate only — not a JS Playwright fixture
   stack; see deviation note below).
3. **Tiered CI/CD**: PR / Nightly / Weekly model (see companion QA doc).
4. **Coverage**: ~21 scenarios prioritized P0–P3.
5. **Quality gates**: see companion QA doc.

**What we need from team:** Just review and acknowledge.

---

## For Architects and Devs - Open Topics 👷

### Risk Assessment

**Total risks identified**: 7 (2 high-priority score ≥6, 3 medium, 2 low)

#### High-Priority Risks (Score ≥6) - IMMEDIATE ATTENTION

| Risk ID   | Category | Description                                                                                                          | Probability | Impact | Score | Mitigation                                                                          | Owner                          | Timeline        |
| --------- | -------- | ---------------------------------------------------------------------------------------------------------------------- | ------------ | ------ | ----- | ------------------------------------------------------------------------------------ | ------------------------------- | --------------- |
| **R-001** | TECH     | Story↔test traceability matrix is 0-for-64 despite 45 real test files; several already name their story in-docstring | 2            | 3      | **6** | Fix generator's story-matching logic to parse existing docstrings; re-run `--check`  | `bmad_tea_playwright.py` owner  | next gen. cycle |
| **R-002** | PERF     | `<2s` web-tab NFR has zero automated verification, by the test suite's own documented decision                        | 2            | 3      | **6** | Build a load-time harness or formally reclassify NFR given the static-bundle surface | Herald web maintainer           | next sprint     |

#### Medium-Priority Risks (Score 3-5)

| Risk ID | Category | Description                                                                                                                | Probability | Impact | Score | Mitigation                                                                                  | Owner            |
| ------- | -------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------ | ------ | ----- | ---------------------------------------------------------------------------------------------- | ---------------- |
| R-003   | OPS      | Default gate never exercises a real ASGI socket; the opt-in `live_webhook` test + separate `herald-live-demo.yml` cover it | 2            | 2      | 4     | Document in operator runbook; consider a loopback-only smoke test in the default gate later    | Herald maintainer |
| R-004   | OPS      | Webhook payload-shape drift vs. the real GitHub Actions producer has no contract/schema-diff check                         | 2            | 2      | 4     | Add a static schema check against `.github/workflows/*.yml`, not a new runtime dependency      | Herald maintainer |
| R-005   | TECH     | Satellite PRD's adoption/engagement KPIs (≥80% trigger rate, ≥90% claims-within-7-days, …) have no instrumentation to query | 2            | 2      | 4     | A lightweight metrics query over existing SQLite tables would answer most of these             | Herald + Atlas    |

#### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description                                                                                          | Probability | Impact | Score | Action  |
| ------- | -------- | -------------------------------------------------------------------------------------------------------- | ------------ | ------ | ----- | ------- |
| R-006   | DATA     | Notice-versioning depth (full history vs. current+audit log) is an open deferred decision, untested either way | 1            | 2      | 2     | Monitor — revisit if a notice edit-history dispute occurs |
| R-007   | TECH     | i18n / `document_output_language` non-English path: satellite Deferred Decision 6, still "assume English-first" | 1            | 1      | 1     | Monitor — no action until a non-English requirement surfaces |

#### Risk Category Legend

- **TECH**: Technical/Architecture · **SEC**: Security · **PERF**: Performance · **DATA**:
  Data Integrity · **BUS**: Business Impact · **OPS**: Operations

---

### NFR Testability Requirements

**Purpose:** Capture what architecture must provide so NFR validation can be automated later.

| NFR Category    | Threshold / Requirement                                                                 | Current Design Support                                    | Gap / Decision Needed                                                              | Planned Evidence                                        |
| --------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Security        | Write ops require operator role (AD-16); webhook HMAC-SHA256 (`hmac.compare_digest`)   | Supported — role model delegated to `pyforge.steward.dashboard`; write-gate consistency has a cross-cutting structural test | None herald-owned; steward owns the auth model                                          | `test_auth.py`, `test_reliability_epic11.py`, `test_webhook.py` |
| Performance     | CLI <1s p95, web tab <2s, progress widget <500ms (PRD FR)                              | Partial — CLI verified in-process (avoids process-spawn skew); web load explicitly left untested | R-002: decide harness vs. NFR reclassification for the static-bundle surface           | `test_performance_epic11.py` (CLI only); none for web        |
| Reliability     | ≥99% uptime (SLA tbd with ops); webhook exponential-backoff + max-3-retry; isolated cron queue | Supported — retry/backoff shipped in `webhook.py`; scheduler isolated from web requests    | No measured uptime baseline exists; SLA itself still "tbd with ops" per the ADR         | `webhook.py` retry tests, `test_scheduler.py`                |
| Maintainability | Unit ≥80% / integration ≥70% coverage targets (referenced by the generator baseline)    | UNKNOWN — not independently re-measured in this pass                                        | Confirm actual % via `pixi run -e pyforge-herald pyforge-herald-test --cov` before `nfr-assess` | Coverage report from the station's own test task            |

**Unknown thresholds:** current unit/integration coverage percentage (not re-measured here —
deferred to `nfr-assess`, per this workflow's own boundary); uptime SLA (explicitly "tbd with
ops" in the architecture doc itself, not guessed here).

**Assessment boundary:** Final PASS/CONCERNS/FAIL status belongs in `nfr-assess` after
implementation evidence exists.

---

### Testability Concerns and Architectural Gaps

**🚨 ACTIONABLE CONCERNS**

#### 1. Blockers to Fast Feedback

| Concern                                             | Impact                                              | What Must Be Provided                                                          | Owner                    | Timeline    |
| ---------------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------- | ----------- |
| **No mechanical story↔test link (R-001)**          | Coverage claims for future stories can't be trusted automatically | Generator fix reading existing docstring story-tags                             | shared-script owner      | next cycle  |
| **No web-load-time harness (R-002)**                | A regression in the static bundle's load time would ship undetected | Either a lightweight timing harness, or a recorded NFR reclassification decision | Herald web maintainer     | next sprint |

#### 2. Architectural Improvements Needed

1. **Webhook schema-drift check (R-004)**
   - **Current problem**: `_problem_unknown_fields` catches drift only at live-delivery time.
   - **Required change**: a CI-time static diff between the known-fields set in `webhook.py`
     and the payload shape the actual `.github/workflows/*.yml` jobs produce.
   - **Impact if not fixed**: an upstream workflow edit silently starts 400ing production
     webhooks with no warning until an operator notices.
   - **Owner**: Herald maintainer. **Timeline**: implementation phase.
2. **Promote (or document) the real-socket proof (R-003)**
   - **Current problem**: `test_webhook_live_smoke.py` is opt-in only; default CI has a
     genuine blind spot on the real ASGI path, covered today only by a separate GitHub
     Actions workflow most contributors won't think to check.
   - **Required change**: either fold a loopback-only smoke test into the default gate, or
     add an explicit pointer in the operator runbook.
   - **Impact if not fixed**: a contributor could reasonably (and wrongly) believe
     `pyforge-herald-test` alone proves the live webhook path.
   - **Owner**: Herald maintainer. **Timeline**: next sprint.

---

### Testability Assessment Summary

**📊 CURRENT STATE - FYI**

#### What Works Well

- ✅ **Operator-role write gate is structurally enforced across all six write commands**, not
  spot-checked one at a time — `test_reliability_epic11.py` adds a cross-cutting guard that
  also catches a future write command silently forgetting the gate.
- ✅ **Producer-side schema defense is strict by default** — `webhook.py`'s
  `_problem_unknown_fields` rejects any unrecognized field with a loud 400, explicitly
  designed (per its own docstring) to prevent a typo in the one hand-written, schema-less
  GitHub Actions producer from silently zeroing a day's recorded data.
- ✅ **The second-writer concurrency risk was closed proactively**, before any second writer
  existed: Story 13.1 (stdlib `fcntl`/`msvcrt` advisory locking) landed first, Story 13.3
  (SQLite transactional locking) then subsumed it, and Story 13.6 proved the whole composed
  path live — a real merge creates a progress record and a success-claim draft with no human
  action, CI-contained.
- ✅ **Evidence-link integrity has both sync and async validation, both implemented**:
  publish-time 404 detection plus `scheduler.py::run_evidence_revalidation` (a real weekly
  `claims.revalidate_all` wrapper), not just the AD-15 design intent.
- ✅ **Test authors document real coverage boundaries honestly** rather than fabricating
  proxies for untestable claims (`test_performance_epic11.py` explicitly declines to fake a
  browser/network stack for the web-load NFR) — this is a genuine asset for trusting the
  suite's other claims.

#### Accepted Trade-offs (No Action Required)

- **CLI timing is measured in-process, not via subprocess spawns** — deliberately avoids
  conflating process-spawn overhead with actual command latency; consistent with how the rest
  of the CLI suite already measures. Acceptable as-is.
- **Epic 18 (Manticore studio relay, release-comms routing, slides-generator) has zero
  implementation and zero test coverage** — confirmed by grep: no "narration" reference
  exists anywhere in `src/` or `tests/`. This is not a defect: all three Epic 18 stories are
  cross-station-`blocked` on Steward 46.2/46.5/46.6 in `sprint-status-ledger.yaml` (AD-10).
  Test design for it is deferred; see companion QA doc's "Not in Scope" table rather than a
  scored risk here, since there is nothing yet to test.

---

### Assumptions and Dependencies

#### Assumptions

1. `test_stack_type` auto-detected as `fullstack` (Python `pyproject.toml` + React
   `package.json`) is correct — no contradicting signal found.
2. The `tea_use_playwright_utils` / `tea_use_pactjs_utils` config defaults target a
   TypeScript/Node test stack that does not exist in this station; this document and its QA
   companion apply the *intent* of those mandates (fixtures over raw calls, no ad-hoc
   waits/logging) using the project's real pytest idioms instead of introducing new JS
   tooling. Recorded as a deviation, not silently ignored.
3. `nfr_threshold` for uptime SLA and current test-coverage percentage are genuinely unset in
   the source documents — left `UNKNOWN` rather than guessed, per this workflow's own rule.

#### Dependencies

1. Epic 18 unblocking — Required by: Steward stories 46.2, 46.5, 46.6 landing first.
2. Generator fix for R-001 — Required by: whoever owns `_bmad/scripts/bmad_tea_playwright.py`
   (a shared cross-station script, not Herald-scoped code).

#### Risks to Plan

- **Risk**: This document's risk register (7 risks) is materially smaller than a from-scratch
  system with no shipped code would produce, because 47 of 50 stories are already `done` and
  well-tested.
  - **Impact**: A reviewer expecting a pre-implementation-style register (many open TECH/SEC
    risks) may perceive this as under-scoped.
  - **Contingency**: This is by design for a post-ship system-level review — see companion QA
    doc's Executive Summary for the explicit framing (regression confidence, not first-build
    acceptance criteria).

---

**End of Architecture Document**

**Next Steps for Architecture Team:**

1. Review Quick Guide (🚨/⚠️/📋) and decide on R-001/R-002.
2. Assign owners and timelines for R-003/R-004.
3. Validate assumptions and dependencies above.

**Next Steps for QA Team:**

1. Refer to companion QA doc (`test-design-qa.md`) for the full test scenario list.
2. Track Epic 18 as a future epic-level test-design run once Steward unblocks it.
