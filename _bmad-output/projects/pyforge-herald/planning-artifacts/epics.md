---
epics_role: canonical
# The single canonical story source for this station: every `### Story` heading here maps
# 1:1 to a sprint-status-ledger.yaml story key. Exactly one `canonical` per station (AD-72).
project_name: pyforge-herald
epicCount: 12
storyCount: 47
status: complete
---

# pyforge-herald — Epic Breakdown

Rebuilt 2026-08-08 from `sprint-status-ledger.yaml`. The previous file was a
planning-workflow scratch document ("REQUIREMENTS EXTRACTED & VERIFIED", "READY FOR NEXT
STEP", "APPROVED EPIC STRUCTURE (Step 2 Complete)") that listed stories as **bullets**
rather than `### Story` headings and covered only Epics 6-12 — so it declared **zero**
stories in the shape every other station uses, against a 47-story ledger. `INV-D` in
`chain_completeness_check.py` exists because of it, and now fails on that shape.

The prior content is preserved at `epics-planning-scratch-2026-08-08.md`.

## Epic List

| Epic | Title | Stories | Done |
|---|---|---|---|
| **E1** | Foundation — package spine & transport | 6 | 6 |
| **E2** | Deck pull — prototype, marp, bundle | 4 | 4 |
| **E3** | Deck status & stale-mirror detection | 2 | 2 |
| **E4** | Watch — poll, backoff, halt | 3 | 3 |
| **E5** | Export push-back | 2 | 2 |
| **E6** | Foundation — CLI architecture & shared infrastructure | 5 | 5 |
| **E7** | Foundation — web surface | 2 | 2 |
| **E8** | Moment 2 — progress visibility | 4 | 4 |
| **E9** | Moment 3 — success proclamation | 5 | 5 |
| **E10** | Moment 4 — operations notices | 6 | 6 |
| **E11** | Integration testing & automation reliability | 4 | 4 |
| **E12** | Documentation & operator experience | 4 | 4 |
| **Total** | | **47** | **47** |


---

## Epic 1: Foundation — package spine & transport

### Story 1.1: Package scaffold for pyforge herald

**Status:** done  ·  **Ledger key:** `1-1-package-scaffold-for-pyforge-herald`

### Story 1.2: Transport port primary mcp client adapter the transport spike

**Status:** done  ·  **Ledger key:** `1-2-transport-port-primary-mcp-client-adapter-the-transport-spike`

### Story 1.3: Fallback transport adapter

**Status:** done  ·  **Ledger key:** `1-3-fallback-transport-adapter`

### Story 1.4: Bridge core skeleton state errors determinism boundary

**Status:** done  ·  **Ledger key:** `1-4-bridge-core-skeleton-state-errors-determinism-boundary`

### Story 1.5: Registry module readme design project

**Status:** done  ·  **Ledger key:** `1-5-registry-module-readme-design-project`

### Story 1.6: Herald deck seed slug

**Status:** done  ·  **Ledger key:** `1-6-herald-deck-seed-slug`


---

## Epic 2: Deck pull — prototype, marp, bundle

### Story 2.1: Herald deck pull slug prototype pull with etag short circuit

**Status:** done  ·  **Ledger key:** `2-1-herald-deck-pull-slug-prototype-pull-with-etag-short-circuit`

### Story 2.2: Commit opt in

**Status:** done  ·  **Ledger key:** `2-2-commit-opt-in`

### Story 2.3: Marp source pull

**Status:** done  ·  **Ledger key:** `2-3-marp-source-pull`

### Story 2.4: Standalone bundle pull

**Status:** done  ·  **Ledger key:** `2-4-standalone-bundle-pull`


---

## Epic 3: Deck status & stale-mirror detection

### Story 3.1: Herald deck status slug

**Status:** done  ·  **Ledger key:** `3-1-herald-deck-status-slug`

### Story 3.2: Stale hand mirror detection

**Status:** done  ·  **Ledger key:** `3-2-stale-hand-mirror-detection`


---

## Epic 4: Watch — poll, backoff, halt

### Story 4.1: Poll loop with quiescence debounce

**Status:** done  ·  **Ledger key:** `4-1-poll-loop-with-quiescence-debounce`

### Story 4.2: Idle backoff

**Status:** done  ·  **Ledger key:** `4-2-idle-backoff`

### Story 4.3: Halt on auth error

**Status:** done  ·  **Ledger key:** `4-3-halt-on-auth-error`


---

## Epic 5: Export push-back

### Story 5.1: Push regenerated exports with etag guard

**Status:** done  ·  **Ledger key:** `5-1-push-regenerated-exports-with-etag-guard`

### Story 5.2: Conflict refusal on export push

**Status:** done  ·  **Ledger key:** `5-2-conflict-refusal-on-export-push`


---

## Epic 6: Foundation — CLI architecture & shared infrastructure

### Story 6.1: Implement Herald CLI Dispatcher

**Status:** done  ·  **Ledger key:** `6-1-implement-herald-cli-dispatcher`

### Story 6.2: Implement Shared Argument Conventions

**Status:** done  ·  **Ledger key:** `6-2-implement-shared-argument-conventions`

### Story 6.3: Implement CLI Authentication & Authorization

**Status:** done  ·  **Ledger key:** `6-3-implement-cli-authentication-and-authorization`

### Story 6.4: Implement Evidence Link Validation Protocol (Shared Infrastructure)

**Status:** done  ·  **Ledger key:** `6-4-implement-evidence-link-validation-protocol-shared-infrastructure`

### Story 6.5: CLI Help & First-Day Usability (Inline)

**Status:** done  ·  **Ledger key:** `6-5-cli-help-and-first-day-usability`


---

## Epic 7: Foundation — web surface

### Story 7.1: Design & Implement Web Layout (Header, Tabs, Sidebar, Responsive)

**Status:** done  ·  **Ledger key:** `7-1-design-and-implement-web-layout-header-tabs-sidebar-responsive`

### Story 7.2: Implement Web Tooltips & Inline Help

**Status:** done  ·  **Ledger key:** `7-2-implement-web-tooltips-and-inline-help`


---

## Epic 8: Moment 2 — progress visibility

### Story 8.1: Implement Progress Data Model & Database Schema

**Status:** done  ·  **Ledger key:** `8-1-implement-progress-data-model-and-database-schema`

### Story 8.2: Implement On-Ship Webhook & Weekly Cron Automation

**Status:** done  ·  **Ledger key:** `8-2-implement-on-ship-webhook-and-weekly-cron-automation`

### Story 8.3: Implement Progress CLI (`herald progress` subcommand)

**Status:** done  ·  **Ledger key:** `8-3-implement-progress-cli`

### Story 8.4: Implement Progress Web Tab

**Status:** done  ·  **Ledger key:** `8-4-implement-progress-web-tab`


---

## Epic 9: Moment 3 — success proclamation

### Story 9.1: Implement Claim Data Model & Database Schema

**Status:** done  ·  **Ledger key:** `9-1-implement-claim-data-model-and-database-schema`

### Story 9.2: Implement Auto-Extract & Operator Review Gate

**Status:** done  ·  **Ledger key:** `9-2-implement-auto-extract-and-operator-review-gate`

### Story 9.3: Implement Success CLI

**Status:** done  ·  **Ledger key:** `9-3-implement-success-cli`

### Story 9.4: Implement Success Web Archive

**Status:** done  ·  **Ledger key:** `9-4-implement-success-web-archive`

### Story 9.5: Implement Evidence Validation (Sync + Async)

**Status:** done  ·  **Ledger key:** `9-5-implement-evidence-validation-sync-and-async`


---

## Epic 10: Moment 4 — operations notices

### Story 10.1: Notice Data Model & Archive Storage

**Status:** done  ·  **Ledger key:** `10-1-notice-data-model-and-archive-storage`

### Story 10.2: Notice Authoring Workflow (CLI)

**Status:** done  ·  **Ledger key:** `10-2-notice-authoring-workflow-cli`

### Story 10.3: Notice Archive & Redirects

**Status:** done  ·  **Ledger key:** `10-3-notice-archive-and-redirects`

### Story 10.4: Notice CLI

**Status:** done  ·  **Ledger key:** `10-4-notice-cli`

### Story 10.5: Operations Web Tab

**Status:** done  ·  **Ledger key:** `10-5-operations-web-tab`

### Story 10.6: Notice Lifecycle

**Status:** done  ·  **Ledger key:** `10-6-notice-lifecycle`


---

## Epic 11: Integration testing & automation reliability

### Story 11.1: Integration Testing (CLI + Web + Automation)

**Status:** done  ·  **Ledger key:** `11-1-integration-testing-cli-web-and-automation`

### Story 11.2: Automation Reliability

**Status:** done  ·  **Ledger key:** `11-2-automation-reliability`

### Story 11.3: Evidence Linking (Cross-Moment)

**Status:** done  ·  **Ledger key:** `11-3-evidence-linking-cross-moment`

### Story 11.4: Performance Testing

**Status:** done  ·  **Ledger key:** `11-4-performance-testing`


---

## Epic 12: Documentation & operator experience

### Story 12.1: CLI Runbooks & Troubleshooting

**Status:** done  ·  **Ledger key:** `12-1-cli-runbooks-and-troubleshooting`

### Story 12.2: Web Surface UX Guide

**Status:** done  ·  **Ledger key:** `12-2-web-surface-ux-guide`

### Story 12.3: Operator Runbook

**Status:** done  ·  **Ledger key:** `12-3-operator-runbook`

### Story 12.4: Automation Troubleshooting Guide

**Status:** done  ·  **Ledger key:** `12-4-automation-troubleshooting-guide`

