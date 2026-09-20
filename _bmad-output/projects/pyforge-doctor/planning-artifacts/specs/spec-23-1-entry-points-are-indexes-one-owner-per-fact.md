---
title: '23.1: Entry points are indexes; one owner per fact'
type: 'fix'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Operational procedures are still restated in entry-point files after Epic 22.

**Approach:** Each duplicated procedure becomes a pointer into docs/. No operational procedure is copied verbatim across an entry point and a quadrant file without one side being a pointer. SKILL.md files keep wielding notes that name CLI grammar only.

## Boundaries & Constraints

**Always:**
- Entry points point; they do not restate operational procedures.
- SKILL.md wielding notes name CLI grammar only.

**Never:**
- Do not leave a verbatim copy of a procedure in both an entry point and a quadrant file.
- Do not reopen Epic 22.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| duplicated procedure | same steps in README and docs/ | one side is a pointer | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-1`.
Surface: docs/MAP.md, README.md, CLAUDE.md, AGENTS.md..
Ledger key: `23-1-entry-points-are-indexes-one-owner-per-fact`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-1-entry-points-are-indexes-one-owner-per-fact.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9348c8d01f` (2026-09-18, "Merge pull request #1437 from rxm7706/dispatch/pyforge-doctor/23.1"). Ledger row `23-1-entry-points-are-indexes-one-owner-per-fact: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `CLAUDE.md`, `docs/reference/github-workflows.md`, `docs/reference/judgement-vocabulary.md`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready` → `done` (ledger row `23-1-entry-points-are-indexes-one-owner-per-fact: done`).
- `## Auto Run Result` reconstructed from git (none survived).
